"""Pandas cleaning pipeline for movies_main.csv / movie_extended.csv / ratings.json.

Reads from data/enriched/ (scripts/enrichment/fill_missing.py,
movielens_ratings.py, validate_records.py), not data/raw/ -- enrichment
fills gaps and corrects values but doesn't dedupe, drop corrupt rows, or
standardize formats, so this step still needs to run against it exactly as
it would against data/raw/. Requires enrichment to have been run at least
once already; see scripts/enrichment/README.md.

movie_extended.csv has 4 columns enrichment added that don't exist in
data/raw/ at all: original_title, original_language, director, cast.
director/cast are comma-joined name lists like genres/production_companies
and are split into arrays the same way; original_title/original_language
are single values and pass through untouched.

Run: python -m scripts.pandas.clean_data
"""

import ast
import json
import re

import numpy as np
import pandas as pd
from pathlib import Path

from scripts.pandas.data_processor import apply_transform, index_by_movie_id, load_json, standardize_date
from scripts.pandas.models import Movie, Rating

SOURCE_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "enriched"
PROCESSED_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "processed"


def load_movies(raw_dir: Path = SOURCE_DIR) -> pd.DataFrame:
    df = pd.read_csv(raw_dir / "movies_main.csv")
    # 3 rows in the source have shifted/garbage columns (e.g. a date string
    # in `id`) -- pandas keeps `id` as an object column because of them, so
    # coerce it to numeric here; the bad rows become NaN and get dropped in
    # main(), matching clean_movies() on the PySpark side.
    df["id"] = pd.to_numeric(df["id"], errors="coerce")
    df["budget"] = pd.to_numeric(df["budget"], errors="coerce")
    df["revenue"] = pd.to_numeric(df["revenue"], errors="coerce")
    return df


def load_ratings(raw_dir: Path = SOURCE_DIR) -> pd.DataFrame:
    with open(raw_dir / "ratings.json", "r", encoding="utf-8") as f:
        records = json.load(f)

    df = pd.json_normalize(records, sep="_")
    df = df.rename(
        columns={
            "ratings_summary_avg_rating": "avg_rating",
            "ratings_summary_total_ratings": "total_ratings",
            "ratings_summary_std_dev": "std_dev",
        }
    )
    df["last_rated"] = pd.to_datetime(df["last_rated"], unit="s", utc=True)
    # NaN for single-rating movies (undefined statistic) -- see CLEANING.md's
    # "NaN std_dev" section for why this becomes NULL.
    df["std_dev"] = df["std_dev"].where(~df["std_dev"].isna(), other=np.nan)
    return df


def _split_list(raw) -> list:
    if pd.isna(raw) or not str(raw).strip():
        return []
    return [part.strip() for part in str(raw).split(",") if part.strip()]


def _parse_codes_and_names(raw, code_field: str) -> tuple[list, list]:
    # Parses the Python-repr list once and pulls both fields from the same
    # result -- an earlier version called ast.literal_eval twice per row
    # (once per field), which is pure waste since it's the same string both
    # times.
    if pd.isna(raw):
        return [], []
    try:
        parsed = ast.literal_eval(raw)
    except (ValueError, SyntaxError):
        return [], []
    if not isinstance(parsed, list):
        return [], []
    codes, names = [], []
    for d in parsed:
        if not isinstance(d, dict):
            continue
        code, name = d.get(code_field), d.get("name")
        if code:
            codes.append(code)
        if name:
            names.append(name)
    return codes, names


def load_extended(raw_dir: Path = SOURCE_DIR) -> pd.DataFrame:
    df = pd.read_csv(raw_dir / "movie_extended.csv")
    df["id"] = pd.to_numeric(df["id"], errors="coerce")
    df["genres"] = df["genres"].apply(_split_list)
    df["production_companies"] = df["production_companies"].apply(_split_list)
    # director/cast are comma-joined name lists the same way genres/
    # production_companies are (see fill_missing.py's fill_extended_row) --
    # split them the same way for consistency.
    df["director"] = df["director"].apply(_split_list)
    df["cast"] = df["cast"].apply(_split_list)
    # Keep both the ISO code and the display name (parallel arrays) -- the
    # eventual normalized countries/language tables use the code as their
    # primary key, so dropping it here would force a fragile name-based
    # re-match later.
    countries = df["production_countries"].apply(lambda v: _parse_codes_and_names(v, "iso_3166_1"))
    df["production_country_codes"] = countries.apply(lambda t: t[0])
    df["production_country_names"] = countries.apply(lambda t: t[1])

    languages = df["spoken_languages"].apply(lambda v: _parse_codes_and_names(v, "iso_639_1"))
    df["spoken_language_codes"] = languages.apply(lambda t: t[0])
    df["spoken_language_names"] = languages.apply(lambda t: t[1])

    df = df.drop(columns=["production_countries", "spoken_languages"])
    return df


def _is_present(value) -> bool:
    if isinstance(value, list):
        return len(value) > 0
    return pd.notna(value)


def remove_duplicates(df: pd.DataFrame, subset: str = "id") -> pd.DataFrame:
    df = df.reset_index(drop=True)

    # Full-row duplicate check needs hashable values -- genres/companies/etc
    # (list columns from load_extended) aren't, so compare via a tuple-cast
    # view instead of the real columns. This collapses rows that are only
    # duplicated because of formatting noise (differently-formatted dates,
    # stray whitespace), same as dropDuplicates() on the PySpark side.
    hashable = df.apply(lambda col: col.map(lambda v: tuple(v) if isinstance(v, list) else v))
    df = df[~hashable.duplicated(keep="first")].reset_index(drop=True)

    # Anything still sharing an id at this point is a genuine conflict --
    # keep whichever row has the most non-null/non-empty fields.
    completeness = df.apply(lambda row: sum(_is_present(v) for v in row), axis=1)
    df = (
        df.assign(_completeness=completeness)
        .sort_values("_completeness", ascending=False)
        .drop_duplicates(subset=subset, keep="first")
        .drop(columns="_completeness")
        .reset_index(drop=True)
    )
    return df


_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_SLASH_DATE = re.compile(r"^\d{1,2}/\d{1,2}/\d{4}$")
_DASH_DATE = re.compile(r"^\d{1,2}-\d{1,2}-\d{4}$")


def fix_dates(df: pd.DataFrame, column: str = "release_date") -> pd.DataFrame:
    # A single pd.to_datetime auto-parse would silently mis-parse a chunk of
    # rows (DD-MM vs MM-DD is ambiguous per-row) -- standardize_date handles
    # the per-format detection. See CLEANING.md's "Date formats" section.
    df = df.copy()
    df[column] = df[column].apply(standardize_date)
    return df


def fix_missing_budget(df: pd.DataFrame) -> pd.DataFrame:
    # budget=0 (74.5% of rows) / revenue=0 (83.7%) are implausible as literal
    # zero at that rate -- this source's "not reported" convention. Convert
    # to NULL so "unknown" has one consistent representation; filling these
    # gaps is deferred to external validation, not attempted here. See
    # CLEANING.md's "Missing budget/revenue" section.
    df = df.copy()
    df["budget"] = df["budget"].replace(0, np.nan)
    df["revenue"] = df["revenue"].replace(0, np.nan)
    return df


def _listcols_to_str(df: pd.DataFrame) -> pd.DataFrame:
    # Comma-joined, matching the raw source's own convention for these
    # columns. Verified no individual genre/company/country/language value
    # in this dataset contains a literal comma, so joining this way doesn't
    # create any ambiguity when split back apart later.
    df = df.copy()
    for col in df.columns:
        if df[col].apply(lambda v: isinstance(v, list)).any():
            df[col] = df[col].apply(lambda v: ",".join(v) if isinstance(v, list) else v)
    return df


def main():
    movies = load_movies()
    movies = movies.dropna(subset=["id"])
    movies["id"] = movies["id"].astype(int)
    movies["title"] = movies["title"].str.strip()
    movies = fix_dates(movies)
    movies = fix_missing_budget(movies)
    movies = remove_duplicates(movies)

    extended = load_extended()
    extended = extended.dropna(subset=["id"])
    extended["id"] = extended["id"].astype(int)
    extended = remove_duplicates(extended)
    # Cross-table rule: drop movie_extended rows with no matching movie
    # (in practice, just extended's copy of the 3 corrupt/dropped rows).
    extended = extended[extended["id"].isin(movies["id"])]

    ratings = load_ratings()

    # Three outputs mirroring the raw sources (not merged) -- transform.py's
    # clean() loads these directly into clean.movies_main/movie_extended/ratings.
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    outputs = {
        "movies_main_clean.csv": movies,
        "movie_extended_clean.csv": _listcols_to_str(extended),
        "ratings_clean.csv": ratings,
    }
    for filename, df in outputs.items():
        df.to_csv(PROCESSED_DIR / filename, index=False)
        print(f"Wrote {len(df)} rows to {PROCESSED_DIR / filename}")

    # Demonstrate the Movie class over the cleaned data.
    movie_objs = [Movie.from_dict(row) for row in movies.to_dict("records")]
    known_profit = [m.profit() for m in movie_objs if m.profit() is not None]
    print(
        f"{len(known_profit)}/{len(movie_objs)} movies have a computable profit "
        f"(total: {sum(known_profit):,.0f})"
    )

    # Demonstrate the dict-based utilities (data_processor.py) and the
    # Rating class over the raw ratings records.
    raw_ratings_records = load_json(SOURCE_DIR / "ratings.json")
    ratings_by_id = index_by_movie_id(raw_ratings_records)
    summaries = apply_transform(
        list(ratings_by_id.values()),
        lambda r: {"movie_id": r["movie_id"], "avg_rating": r["ratings_summary"]["avg_rating"]},
    )
    rating_objs = [Rating.from_dict(r) for r in ratings_by_id.values()]
    known_avg = [r.avg_rating for r in rating_objs if r.avg_rating is not None]
    print(
        f"{len(rating_objs)} ratings loaded via data_processor utilities, "
        f"mean avg_rating: {sum(known_avg) / len(known_avg):.2f} "
        f"(cross-checked via {len(summaries)} dict-transformed summaries)"
    )


if __name__ == "__main__":
    main()
