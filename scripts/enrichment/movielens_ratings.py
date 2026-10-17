"""Fills and corrects ratings.json using MovieLens ratings, joined to our
TMDB-based movie ids via MovieLens's own links.csv.

Why MovieLens, not TMDB: this dataset's avg_rating is on a 0.5-5.0 scale
(MovieLens' star-rating scale), not TMDB's 0-10 vote_average -- strong
evidence ratings.json was originally built this exact way (TMDB metadata
+ MovieLens ratings joined via links.csv), so re-deriving it the same way
is a format-exact match, not an approximation.

Deliberately separate from fill_missing.py: that script fills individual
missing fields via a live TMDB API; this one works from a static,
pre-downloaded MovieLens dump -- no API key, no rate limiting, just a
local join.

Two operations, mirroring fill_missing.py/validate_records.py's split for
TMDB:
  - resolve_ratings() corrects EXISTING records: our full MovieLens dump
    is a larger, more current ratings pool than whatever originally
    produced the existing ~20% of ratings.json, so a disagreement means
    "adopt the fresh computation," the same "trust the more current
    source" logic as validate_records.py's TMDB corrections.
  - fill_missing_ratings() appends entirely missing records -- movie ids
    with no ratings.json entry at all.

Setup: download a full MovieLens dataset (ml-25m or newer) from
https://grouplens.org/datasets/movielens/ and unzip it to
data/external/movielens/ (containing at least links.csv and ratings.csv).

Run: python -m scripts.enrichment.movielens_ratings
"""

import json
import math
from pathlib import Path

import pandas as pd

from scripts.config import ENRICHED_DIR, EXTERNAL_DIR, RAW_DIR

MOVIELENS_DIR = EXTERNAL_DIR / "movielens"


def load_links(links_path: Path) -> pd.DataFrame:
    """movieId -> tmdbId mapping. Drops rows with no tmdbId (a small
    fraction of MovieLens movies aren't linked to a TMDB entry)."""
    df = pd.read_csv(links_path, usecols=["movieId", "tmdbId"])
    df = df.dropna(subset=["tmdbId"])
    df["tmdbId"] = df["tmdbId"].astype(int)
    return df


def aggregate_ratings(ratings_path: Path) -> pd.DataFrame:
    """One row per movieId: avg_rating, total_ratings, std_dev, last_rated.

    ddof=1 (pandas' groupby .std() default) on a single-rating group
    produces NaN, which matches this dataset's own existing convention
    (33.8% of its current entries have std_dev = NaN for exactly this
    reason) -- not a special case to handle, just the natural consequence
    of using the same statistic.
    """
    ratings = pd.read_csv(ratings_path, usecols=["movieId", "rating", "timestamp"])
    grouped = ratings.groupby("movieId")["rating"]
    return pd.DataFrame(
        {
            "avg_rating": grouped.mean(),
            "total_ratings": grouped.count(),
            "std_dev": grouped.std(),
            "last_rated": ratings.groupby("movieId")["timestamp"].max(),
        }
    ).reset_index()


def build_movielens_index(links: pd.DataFrame, aggregated: pd.DataFrame) -> dict:
    """{tmdb_id: {avg_rating, total_ratings, std_dev, last_rated}}"""
    merged = aggregated.merge(links, on="movieId", how="inner")
    index = {}
    for _, row in merged.iterrows():
        index[int(row["tmdbId"])] = {
            "avg_rating": float(row["avg_rating"]),
            "total_ratings": int(row["total_ratings"]),
            "std_dev": float(row["std_dev"]) if pd.notna(row["std_dev"]) else float("nan"),
            "last_rated": int(row["last_rated"]),
        }
    return index


def _is_nan(value) -> bool:
    try:
        return math.isnan(value)
    except TypeError:
        return False


def resolve_existing_rating(record: dict, movielens_stats: dict | None) -> tuple[dict, list[dict]]:
    """Compares one EXISTING ratings.json record against a fresh MovieLens
    computation for the same movie and adopts MovieLens's version wherever
    they disagree.

    Rejects the correction ENTIRELY (not per-field) if it would decrease
    total_ratings -- MovieLens ratings accumulate over time and are never
    removed, so a real recount of the same movie should only ever stay the
    same or grow. A decrease reliably means links.csv mapped this TMDB id
    to a different MovieLens movieId than whatever originally produced the
    existing record, not a genuine update. Applying only some fields from
    a mismatched record would leave it internally inconsistent (e.g. an
    old total_ratings paired with an avg_rating freshly computed from a
    completely different, much smaller sample) -- worse than leaving it
    alone. Verified against a real run: ~22% of individual total_ratings
    corrections were decreases before this check existed.

    Returns (updated_record, changes) -- changes is a list of
    {field, existing, movielens} dicts, empty if nothing disagreed, there's
    no MovieLens data for this id, or the correction was rejected.
    """
    if movielens_stats is None:
        return record, []

    existing_total = record.get("ratings_summary", {}).get("total_ratings")
    new_total = movielens_stats.get("total_ratings")
    if existing_total is not None and new_total is not None and new_total < existing_total:
        return record, []

    record = dict(record)
    summary = dict(record.get("ratings_summary", {}))
    changes = []

    for field in ("avg_rating", "total_ratings", "std_dev"):
        existing_val = summary.get(field)
        new_val = movielens_stats.get(field)
        # NaN != NaN under normal comparison -- "undefined" on both sides
        # is not a disagreement.
        if _is_nan(existing_val) and _is_nan(new_val):
            continue
        if existing_val != new_val:
            changes.append({"field": field, "existing": existing_val, "movielens": new_val})
            summary[field] = new_val
    record["ratings_summary"] = summary

    if record.get("last_rated") != movielens_stats.get("last_rated"):
        changes.append(
            {
                "field": "last_rated",
                "existing": record.get("last_rated"),
                "movielens": movielens_stats.get("last_rated"),
            }
        )
        record["last_rated"] = movielens_stats["last_rated"]

    return record, changes


def resolve_ratings(existing_records: list[dict], movielens_by_tmdb_id: dict) -> tuple[list[dict], list[dict]]:
    """Runs resolve_existing_rating over every existing record. Does not
    add or remove records -- only corrects values that disagree. Returns
    (updated_records, change_log)."""
    updated = []
    all_changes = []
    for record in existing_records:
        movielens_stats = movielens_by_tmdb_id.get(record["movie_id"])
        new_record, changes = resolve_existing_rating(record, movielens_stats)
        updated.append(new_record)
        for change in changes:
            all_changes.append({"movie_id": record["movie_id"], **change})
    return updated, all_changes


def fill_missing_ratings(existing_records: list[dict], movielens_by_tmdb_id: dict) -> list[dict]:
    """Appends a new ratings.json-shaped record for every tmdb id that has
    MovieLens data but no existing record. Existing records are returned
    untouched -- this never overwrites or recomputes what's already there.
    """
    existing_ids = {r["movie_id"] for r in existing_records}
    filled = list(existing_records)
    for tmdb_id, stats in movielens_by_tmdb_id.items():
        if tmdb_id in existing_ids:
            continue
        filled.append(
            {
                "movie_id": tmdb_id,
                "ratings_summary": {
                    "avg_rating": stats["avg_rating"],
                    "total_ratings": stats["total_ratings"],
                    "std_dev": stats["std_dev"],
                },
                "last_rated": stats["last_rated"],
            }
        )
    return filled


def main():
    links = load_links(MOVIELENS_DIR / "links.csv")
    aggregated = aggregate_ratings(MOVIELENS_DIR / "ratings.csv")
    movielens_index = build_movielens_index(links, aggregated)

    # ml-32m's catalog is larger/newer than this dataset's -- restrict to
    # ids we actually have a movie for, so ratings.json doesn't fill up
    # with entries nothing will ever join against.
    our_movies = pd.read_csv(RAW_DIR / "movies_main.csv", usecols=["id"])
    our_ids = set(pd.to_numeric(our_movies["id"], errors="coerce").dropna().astype(int))
    movielens_index = {tmdb_id: v for tmdb_id, v in movielens_index.items() if tmdb_id in our_ids}

    with open(RAW_DIR / "ratings.json", "r", encoding="utf-8") as f:
        existing_records = json.load(f)

    resolved_records, changes = resolve_ratings(existing_records, movielens_index)
    changed_movies = len({c["movie_id"] for c in changes})
    print(f"{len(changes)} values corrected across {changed_movies} existing ratings")

    before = len(resolved_records)
    filled_records = fill_missing_ratings(resolved_records, movielens_index)
    print(
        f"{len(filled_records) - before} new ratings records added from MovieLens "
        f"({before} existing, {len(filled_records)} total)"
    )

    ENRICHED_DIR.mkdir(parents=True, exist_ok=True)
    out_path = ENRICHED_DIR / "ratings.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(filled_records, f, indent=2)
    print(f"Wrote {out_path}")

    if changes:
        report_path = ENRICHED_DIR / "ratings_validation_report.csv"
        pd.DataFrame(changes, columns=["movie_id", "field", "existing", "movielens"]).to_csv(
            report_path, index=False
        )
        print(f"Wrote change log to {report_path}")


if __name__ == "__main__":
    main()
