"""Fills missing budget/revenue and empty genre/company/country/language
metadata in the raw dataset using the TMDB API, and adds original_title/
original_language/director/cast (new columns -- TMDB has no equivalent in
the raw source at all). Writes enriched copies to data/enriched/.

Deliberately NOT part of the ingestion/cleaning pipeline
(scripts/pyspark/transform.py, scripts/pandas/clean_data.py) -- this runs
once, manually, before either of those. Output has the exact same
filenames/columns as data/raw/ (plus the 4 new columns on movie_extended),
so ingestion needs no code changes -- just point RAW_DIR at data/enriched/
instead.

Only fills gaps -- never overwrites a value that's already present and
non-zero/non-empty. Does not dedupe, drop corrupt rows, or standardize
dates; that stays cleaning's job, unchanged, run afterward against
data/enriched/.

Run: python -m scripts.enrichment.fill_missing [--limit N]
"""

import argparse
import shutil

import pandas as pd

from scripts.config import ENRICHED_DIR, RAW_DIR
from scripts.enrichment.tmdb_client import DEFAULT_MAX_WORKERS, fetch_movies_concurrently

NEW_EXTENDED_COLUMNS = ["original_title", "original_language", "director", "cast"]


def _is_missing(value) -> bool:
    if value is None:
        return True
    try:
        return pd.isna(value) or float(value) == 0
    except (TypeError, ValueError):
        return True


def _is_missing_text(value) -> bool:
    return value is None or pd.isna(value) or not str(value).strip() or str(value).strip() == "[]"


def needs_enrichment(row: dict) -> bool:
    return _is_missing(row.get("budget")) or _is_missing(row.get("revenue"))


def fill_movie_row(row: dict, tmdb_data: dict | None) -> dict:
    """Returns a new movies_main row with budget/revenue filled from TMDB
    wherever they were missing/zero. Never overwrites an existing value."""
    row = dict(row)
    if tmdb_data is None:
        return row
    if _is_missing(row.get("budget")) and tmdb_data.get("budget"):
        row["budget"] = tmdb_data["budget"]
    if _is_missing(row.get("revenue")) and tmdb_data.get("revenue"):
        row["revenue"] = tmdb_data["revenue"]
    return row


def _format_iso_list(items: list[dict], code_field: str) -> str:
    # Matches the raw source's own Python-repr format exactly, so
    # ingestion's existing ast.literal_eval parsing needs no changes.
    return str([{code_field: item[code_field], "name": item["name"]} for item in items])


def fill_extended_row(row: dict, tmdb_data: dict | None) -> dict:
    """Returns a new movie_extended row with genres/companies/countries/
    languages filled from TMDB wherever they were empty, plus
    original_title/original_language/director/cast -- brand-new columns
    the raw source never had, so "never overwrite" here just means "don't
    refetch a row that's already been enriched." Never touches an existing
    non-empty value either way."""
    row = dict(row)
    if tmdb_data is None:
        return row

    if _is_missing_text(row.get("genres")) and tmdb_data.get("genres"):
        row["genres"] = ",".join(g["name"] for g in tmdb_data["genres"])

    if _is_missing_text(row.get("production_companies")) and tmdb_data.get("production_companies"):
        row["production_companies"] = ",".join(
            c["name"] for c in tmdb_data["production_companies"]
        )

    if _is_missing_text(row.get("production_countries")) and tmdb_data.get("production_countries"):
        row["production_countries"] = _format_iso_list(
            tmdb_data["production_countries"], "iso_3166_1"
        )

    if _is_missing_text(row.get("spoken_languages")) and tmdb_data.get("spoken_languages"):
        row["spoken_languages"] = _format_iso_list(tmdb_data["spoken_languages"], "iso_639_1")

    if _is_missing_text(row.get("original_title")) and tmdb_data.get("original_title"):
        row["original_title"] = tmdb_data["original_title"]

    if _is_missing_text(row.get("original_language")) and tmdb_data.get("original_language"):
        row["original_language"] = tmdb_data["original_language"]

    credits = tmdb_data.get("credits") or {}

    if _is_missing_text(row.get("director")) and credits.get("crew"):
        directors = [c["name"] for c in credits["crew"] if c.get("job") == "Director" and c.get("name")]
        if directors:
            row["director"] = ",".join(directors)

    if _is_missing_text(row.get("cast")) and credits.get("cast"):
        # Top 10 by billing order -- ensembles can run to 100+ credited
        # names, most of them bit parts not useful for analysis.
        top_cast = sorted(credits["cast"], key=lambda c: c.get("order", 999))[:10]
        names = [c["name"] for c in top_cast if c.get("name")]
        if names:
            row["cast"] = ",".join(names)

    return row


def _row_needs_enrichment(movie_row: dict, ext_row: dict | None) -> bool:
    if needs_enrichment(movie_row):
        return True
    if ext_row is None:
        # No extended row at all -- can't have original_title/director
        # either, so this id still needs a lookup.
        return True
    return _is_missing_text(ext_row.get("original_title")) or _is_missing_text(ext_row.get("director"))


def enrich(
    movies: pd.DataFrame,
    extended: pd.DataFrame,
    limit: int | None = None,
    max_workers: int = DEFAULT_MAX_WORKERS,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    movies = movies.copy()
    extended = extended.copy()
    for col in NEW_EXTENDED_COLUMNS:
        if col not in extended.columns:
            extended[col] = pd.NA
    # movie_extended.csv has the same 3 corrupt-row problem as movies_main
    # -- without coercion, pandas infers `id` as a string dtype ('862' not
    # 862), which silently breaks every extended_by_id.get(movie_id) below
    # (int 862 != str '862' as dict keys) -- this was failing 100% of the
    # time for every prior run, not just occasionally.
    extended["id"] = pd.to_numeric(extended["id"], errors="coerce")
    extended_by_id = {row["id"]: i for i, row in extended.iterrows()}

    candidate_ids = []
    for _, row in movies.iterrows():
        if pd.isna(row["id"]):
            continue
        movie_id = int(row["id"])
        ext_idx = extended_by_id.get(movie_id)
        ext_row = extended.loc[ext_idx].to_dict() if ext_idx is not None else None
        if _row_needs_enrichment(row.to_dict(), ext_row):
            candidate_ids.append(movie_id)

    total_candidates = len(candidate_ids)
    if limit is not None:
        candidate_ids = candidate_ids[:limit]

    print(f"{total_candidates} of {len(movies)} movies need enrichment" + (
        f" (processing first {len(candidate_ids)} due to --limit)" if limit is not None else ""
    ))

    # Fetch phase is fully parallel; DataFrame mutation happens afterward,
    # sequentially, since pandas isn't safe to write to from multiple
    # threads at once.
    tmdb_results = fetch_movies_concurrently(candidate_ids, max_workers=max_workers)

    for movie_id, tmdb_data in tmdb_results.items():
        movie_idx = movies.index[movies["id"] == movie_id][0]
        new_row = fill_movie_row(movies.loc[movie_idx].to_dict(), tmdb_data)
        # Per-column assignment, not `.loc[idx] = dict(...)` -- whole-row
        # dict assignment doesn't reliably align by column name against
        # this pandas version's stricter per-column dtypes (e.g. a
        # string-dtype `title` column rejecting a same-row int budget).
        for col, val in new_row.items():
            movies.at[movie_idx, col] = val

        ext_idx = extended_by_id.get(movie_id)
        if ext_idx is not None:
            new_ext_row = fill_extended_row(extended.loc[ext_idx].to_dict(), tmdb_data)
            for col, val in new_ext_row.items():
                extended.at[ext_idx, col] = val

    return movies, extended


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="only enrich the first N candidates")
    parser.add_argument("--workers", type=int, default=DEFAULT_MAX_WORKERS, help="concurrent TMDB requests")
    args = parser.parse_args()

    movies = pd.read_csv(RAW_DIR / "movies_main.csv")
    extended = pd.read_csv(RAW_DIR / "movie_extended.csv")
    # 3 rows have shifted/garbage columns (e.g. a date string in `id`, an
    # image path in `budget`) -- without coercion, pandas infers `budget`/
    # `revenue` as a strict string dtype (since not every value is
    # numeric), which then rejects a real int/float assignment later.
    # Coercing turns those garbage cells into NaN. Same fix as
    # clean_data.py's load_movies().
    movies["id"] = pd.to_numeric(movies["id"], errors="coerce")
    movies["budget"] = pd.to_numeric(movies["budget"], errors="coerce")
    movies["revenue"] = pd.to_numeric(movies["revenue"], errors="coerce")

    movies, extended = enrich(movies, extended, limit=args.limit, max_workers=args.workers)

    ENRICHED_DIR.mkdir(parents=True, exist_ok=True)
    movies.to_csv(ENRICHED_DIR / "movies_main.csv", index=False)
    extended.to_csv(ENRICHED_DIR / "movie_extended.csv", index=False)
    # This script doesn't touch ratings -- that's movielens_ratings.py's
    # job. Only copy the plain raw file if nothing's there yet, so a prior
    # movielens_ratings.py run (or a later one) is never clobbered.
    ratings_out = ENRICHED_DIR / "ratings.json"
    if not ratings_out.exists():
        shutil.copy(RAW_DIR / "ratings.json", ratings_out)
    print(f"Wrote enriched files to {ENRICHED_DIR}")


if __name__ == "__main__":
    main()
