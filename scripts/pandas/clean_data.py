"""Pandas cleaning pipeline for movies_main.csv / movie_extended.csv / ratings.json.

Run: python -m scripts.pandas.clean_data
"""

import pandas as pd
from pathlib import Path

RAW_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "raw"
PROCESSED_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "processed"


def load_movies(raw_dir: Path = RAW_DIR) -> pd.DataFrame:
    # TODO: pd.read_csv(raw_dir / "movies_main.csv")
    raise NotImplementedError


def load_ratings(raw_dir: Path = RAW_DIR) -> pd.DataFrame:
    # TODO: pd.read_json — flatten the nested rating summaries into columns
    # (pd.json_normalize may help).
    raise NotImplementedError


def load_extended(raw_dir: Path = RAW_DIR) -> pd.DataFrame:
    # TODO: pd.read_csv(raw_dir / "movie_extended.csv") — handle the
    # multi-valued genre/country columns.
    raise NotImplementedError


def remove_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    # TODO: drop_duplicates, deciding what counts as a duplicate key.
    raise NotImplementedError


def fix_dates(df: pd.DataFrame, column: str = "release_date") -> pd.DataFrame:
    # TODO: standardize the mixed date formats with pd.to_datetime.
    raise NotImplementedError


def fix_missing_budget(df: pd.DataFrame) -> pd.DataFrame:
    # TODO: decide a strategy for missing budgets (drop, impute, flag) and
    # justify it in your write-up.
    raise NotImplementedError


def main():
    # TODO: orchestrate load -> clean -> merge -> write to
    # data/processed/movies_clean.csv
    raise NotImplementedError


if __name__ == "__main__":
    main()
