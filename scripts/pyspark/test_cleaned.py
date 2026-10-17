"""Verifies transform.py's clean() correctly loads the three already-cleaned
CSVs produced by scripts/pandas/clean_data.py (movies_main_clean.csv,
movie_extended_clean.csv, ratings_clean.csv -- one per raw source). The
actual cleaning rules (dedup, date parsing, 0->NULL, NaN handling, etc.) are
implemented and owned by that pandas pipeline now, not here -- these tests
check the load/handoff into Spark, not the cleaning rules themselves.

Run with: pytest scripts/pyspark/test_cleaned.py -v
"""

import csv

import pytest

from scripts.config import PROCESSED_DIR as REAL_PROCESSED_DIR
from scripts.pyspark.transform import clean, get_spark


@pytest.fixture(scope="session")
def spark():
    session = get_spark()
    yield session
    session.stop()


def _write_csv(path, fieldnames, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


@pytest.fixture
def sample_processed_dir(tmp_path):
    """Small fixture mirroring clean_data.py's real three-file output shape."""
    _write_csv(
        tmp_path / "movies_main_clean.csv",
        ["id", "title", "release_date", "budget", "revenue"],
        [
            {"id": 1, "title": "Movie One", "release_date": "2020-01-01", "budget": 1000000, "revenue": 2000000},
            {"id": 2, "title": "Movie Two", "release_date": "2019-05-05", "budget": "", "revenue": ""},
        ],
    )
    _write_csv(
        tmp_path / "movie_extended_clean.csv",
        [
            "id", "genres", "production_companies",
            "production_country_codes", "production_country_names",
            "spoken_language_codes", "spoken_language_names",
        ],
        [
            {"id": 1, "genres": "Drama; Crime", "production_companies": "Studio A",
             "production_country_codes": "US", "production_country_names": "United States of America",
             "spoken_language_codes": "en", "spoken_language_names": "English"},
            {"id": 2, "genres": "Comedy", "production_companies": "Studio B",
             "production_country_codes": "FR", "production_country_names": "France",
             "spoken_language_codes": "fr", "spoken_language_names": "Français"},
        ],
    )
    _write_csv(
        tmp_path / "ratings_clean.csv",
        ["movie_id", "avg_rating", "total_ratings", "std_dev", "last_rated"],
        [{"movie_id": 1, "avg_rating": 4.2, "total_ratings": 10, "std_dev": 0.5, "last_rated": ""}],
    )
    return tmp_path


def test_clean_loads_all_three_tables(spark, sample_processed_dir):
    tables = clean(spark, processed_dir=sample_processed_dir)
    assert set(tables) == {"movies_main", "movie_extended", "ratings"}
    assert tables["movies_main"].count() == 2
    assert tables["movie_extended"].count() == 2
    assert tables["ratings"].count() == 1


def test_clean_movies_main_has_expected_columns(spark, sample_processed_dir):
    df = clean(spark, processed_dir=sample_processed_dir)["movies_main"]
    assert {"id", "title", "release_date", "budget", "revenue"}.issubset(set(df.columns))


def test_clean_preserves_unique_ids(spark, sample_processed_dir):
    tables = clean(spark, processed_dir=sample_processed_dir)
    for name in ("movies_main", "movie_extended"):
        df = tables[name]
        assert df.select("id").distinct().count() == df.count()


def test_clean_preserves_null_budget_as_null_not_zero(spark, sample_processed_dir):
    # clean_data.py already converts 0 -> NULL -- clean() must not reintroduce
    # 0 (e.g. via a careless fillna) while loading.
    df = clean(spark, processed_dir=sample_processed_dir)["movies_main"]
    assert df.filter("budget = 0").count() == 0
    assert df.filter("id = 2").collect()[0]["budget"] is None


def test_clean_defaults_to_the_real_processed_dir(spark, monkeypatch, sample_processed_dir):
    monkeypatch.setattr("scripts.pyspark.transform.DATA_DIR", sample_processed_dir.parent)
    (sample_processed_dir.parent / "processed").mkdir(exist_ok=True)
    for f in sample_processed_dir.iterdir():
        f.rename(sample_processed_dir.parent / "processed" / f.name)

    tables = clean(spark)
    assert tables["movies_main"].count() == 2


@pytest.mark.skipif(
    not (REAL_PROCESSED_DIR / "movies_main_clean.csv").exists(),
    reason="processed CSVs not generated yet -- run `python -m scripts.pandas.clean_data` first",
)
def test_clean_against_the_real_pandas_output(spark):
    tables = clean(spark, processed_dir=REAL_PROCESSED_DIR)
    movies, extended, ratings = tables["movies_main"], tables["movie_extended"], tables["ratings"]

    assert movies.count() > 0
    assert movies.filter("budget = 0").count() == 0
    assert movies.filter("revenue = 0").count() == 0
    assert movies.select("id").distinct().count() == movies.count()
    assert extended.select("id").distinct().count() == extended.count()
    assert ratings.select("movie_id").distinct().count() == ratings.count()
