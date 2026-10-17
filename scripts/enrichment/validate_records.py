"""Corrects budget/revenue/release_date/title in data/enriched/movies_main.csv
against TMDB, since TMDB has the more current data. Writes the corrected
file back in place, plus a change log (validation_report.csv) documenting
every value that was overwritten.

Must run AFTER fill_missing.py -- it corrects data/enriched/movies_main.csv,
not data/raw/, so fill_missing.py's gap-filling isn't skipped or clobbered.
Both scripts share the same TMDB response cache (data/enriched/tmdb_cache/),
so ids fill_missing already fetched don't cost a second API call here.

title is compared against BOTH TMDB's display title and its original_title
(the untranslated title) before being flagged -- ~43% of raw title
"mismatches" turned out to be this dataset already storing the
original-language title while TMDB's default `title` is a later English
release title (e.g. "Le Bonheur" vs "Happiness"). Only overwritten if it
matches neither.

Run: python -m scripts.enrichment.validate_records [--limit N]
"""

import argparse
import re

import pandas as pd

from scripts.config import ENRICHED_DIR
from scripts.enrichment.tmdb_client import DEFAULT_MAX_WORKERS, fetch_movies_concurrently
from scripts.pandas.data_processor import standardize_date


def _has_value(value) -> bool:
    if value is None:
        return False
    try:
        return not pd.isna(value) and float(value) != 0
    except (TypeError, ValueError):
        return bool(str(value).strip())


def _normalize_title(s) -> str:
    s = str(s).lower().strip()
    s = re.sub(r"[^\w\s]", "", s)
    return re.sub(r"\s+", " ", s)


def _title_matches(existing_title, tmdb_data: dict) -> bool:
    existing_norm = _normalize_title(existing_title)
    candidates = [tmdb_data.get("title"), tmdb_data.get("original_title")]
    return any(existing_norm == _normalize_title(c) for c in candidates if c)


def resolve_movie_row(row: dict, tmdb_data: dict | None) -> tuple[dict, list[dict]]:
    """Compares one movies_main row's existing values against TMDB and
    adopts TMDB's value wherever they disagree.

    Only compares a field when BOTH sides actually have a value -- there's
    nothing to resolve against a field that's missing on either end (that
    case belongs to fill_missing.py, not here). Returns (updated_row,
    changes), where changes is a list of {field, existing, tmdb} dicts
    documenting every value that got overwritten.
    """
    row = dict(row)
    if tmdb_data is None:
        return row, []

    changes = []

    for field in ("budget", "revenue"):
        if _has_value(row.get(field)) and _has_value(tmdb_data.get(field)):
            if float(row[field]) != float(tmdb_data[field]):
                changes.append({"field": field, "existing": row[field], "tmdb": tmdb_data[field]})
                row[field] = tmdb_data[field]

    if _has_value(row.get("release_date")) and _has_value(tmdb_data.get("release_date")):
        existing_date = standardize_date(row["release_date"])
        tmdb_date = standardize_date(tmdb_data["release_date"])
        if existing_date and tmdb_date and existing_date.date() != tmdb_date.date():
            changes.append(
                {
                    "field": "release_date",
                    "existing": row["release_date"],
                    "tmdb": tmdb_data["release_date"],
                }
            )
            row["release_date"] = tmdb_data["release_date"]

    if _has_value(row.get("title")) and _has_value(tmdb_data.get("title")):
        if not _title_matches(row["title"], tmdb_data):
            changes.append({"field": "title", "existing": row["title"], "tmdb": tmdb_data["title"]})
            row["title"] = tmdb_data["title"]

    return row, changes


def resolve(
    movies: pd.DataFrame, limit: int | None = None, max_workers: int = DEFAULT_MAX_WORKERS
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Runs resolve_movie_row over every movie with an id. Returns
    (corrected_movies, change_log) -- change_log is empty if nothing
    disagreed with TMDB."""
    movies = movies.copy()
    ids = [int(row["id"]) for _, row in movies.iterrows() if pd.notna(row["id"])]
    if limit is not None:
        ids = ids[:limit]

    tmdb_results = fetch_movies_concurrently(ids, max_workers=max_workers)

    report_rows = []
    for movie_id, tmdb_data in tmdb_results.items():
        movie_idx = movies.index[movies["id"] == movie_id][0]
        row = movies.loc[movie_idx].to_dict()
        new_row, changes = resolve_movie_row(row, tmdb_data)

        for col, val in new_row.items():
            movies.at[movie_idx, col] = val
        for change in changes:
            report_rows.append({"id": movie_id, "title": row.get("title"), **change})

    report = pd.DataFrame(report_rows, columns=["id", "title", "field", "existing", "tmdb"])
    return movies, report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="only process the first N movies")
    parser.add_argument("--workers", type=int, default=DEFAULT_MAX_WORKERS, help="concurrent TMDB requests")
    args = parser.parse_args()

    movies_path = ENRICHED_DIR / "movies_main.csv"
    if not movies_path.exists():
        raise SystemExit(
            f"{movies_path} doesn't exist -- run `python -m scripts.enrichment.fill_missing` first."
        )

    movies = pd.read_csv(movies_path)
    movies["id"] = pd.to_numeric(movies["id"], errors="coerce")
    movies["budget"] = pd.to_numeric(movies["budget"], errors="coerce")
    movies["revenue"] = pd.to_numeric(movies["revenue"], errors="coerce")

    movies, report = resolve(movies, limit=args.limit, max_workers=args.workers)

    movies.to_csv(movies_path, index=False)
    out_path = ENRICHED_DIR / "validation_report.csv"
    report.to_csv(out_path, index=False)

    flagged_movies = report["id"].nunique() if len(report) else 0
    print(f"{len(report)} values updated across {flagged_movies} movies")
    print(f"Wrote corrected {movies_path}")
    print(f"Wrote change log to {out_path}")


if __name__ == "__main__":
    main()
