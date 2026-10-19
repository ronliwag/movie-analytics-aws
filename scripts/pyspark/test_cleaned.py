"""Verifies transform.py's clean() correctly loads the three already-cleaned
Parquet tables produced by scripts/pandas/clean_data.py (processed/movies_main/,
movie_extended/, ratings/ -- one folder per raw source). The
actual cleaning rules (dedup, date parsing, 0->NULL, NaN handling, etc.) are
implemented and owned by that pandas pipeline now, not here -- these tests
check the load/handoff into Spark, not the cleaning rules themselves.

Run with: pytest scripts/pyspark/test_cleaned.py -v
"""

import pandas as pd
import pytest

from scripts.config import PROCESSED_DIR as REAL_PROCESSED_DIR
from scripts.pyspark.transform import clean, get_spark, write_lake


@pytest.fixture(scope="session")
def spark():
    session = get_spark()
    yield session
    session.stop()


def _write_parquet(path, df):
    # Same layout and options as clean_data.py's main().
    path.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path / "part-0.parquet", index=False, coerce_timestamps="us", allow_truncated_timestamps=True)


@pytest.fixture
def sample_processed_dir(tmp_path):
    """Small fixture mirroring clean_data.py's real three-table output shape."""
    _write_parquet(
        tmp_path / "movies_main",
        pd.DataFrame({
            "id": [1, 2],
            "title": ["Movie One", "Movie Two"],
            "release_date": pd.to_datetime(["2020-01-01", "2019-05-05"]),
            "budget": [1000000.0, None],
            "revenue": [2000000.0, None],
        }),
    )
    _write_parquet(
        tmp_path / "movie_extended",
        pd.DataFrame({
            "id": [1, 2],
            "genres": ["Drama,Crime", "Comedy"],
            "production_companies": ["Studio A", "Studio B"],
            "original_title": ["Movie One", "Film Deux"],
            "original_language": ["en", "fr"],
            "director": ["Director A", "Director B"],
            "cast": ["Actor A,Actor B", None],
            "production_country_codes": ["US", "FR"],
            "production_country_names": ["United States of America", "France"],
            "spoken_language_codes": ["en", "fr"],
            "spoken_language_names": ["English", "Français"],
        }),
    )
    _write_parquet(
        tmp_path / "ratings",
        pd.DataFrame({
            "movie_id": [1],
            "last_rated": pd.to_datetime([None], utc=True),
            "avg_rating": [4.2],
            "total_ratings": [10],
            "std_dev": [0.5],
        }),
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


def test_clean_matches_columns_by_name_not_position(spark, sample_processed_dir):
    # The CSV handoff applied the schema by position, so a reordered column
    # silently loaded into the wrong field. Parquet stores names, and clean()
    # selects by them.
    _write_parquet(
        sample_processed_dir / "movies_main",
        pd.DataFrame({
            "revenue": [2000000.0],
            "title": ["Movie One"],
            "budget": [1000000.0],
            "id": [1],
            "release_date": pd.to_datetime(["2020-01-01"]),
        }),
    )
    row = clean(spark, processed_dir=sample_processed_dir)["movies_main"].collect()[0]
    assert (row["id"], row["title"], row["budget"], row["revenue"]) == (1, "Movie One", 1000000.0, 2000000.0)


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
    not (REAL_PROCESSED_DIR / "movies_main").exists(),
    reason="processed Parquet not generated yet -- run `python -m scripts.pandas.clean_data` first",
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


def test_write_lake_round_trips_with_athena_friendly_types(spark, sample_processed_dir, tmp_path):
    # Same code path as the S3 run, but into a local folder, so no AWS needed.
    lake = tmp_path / "lake_clean"
    tables = clean(spark, processed_dir=sample_processed_dir)
    for _ in range(2):  # a second run must replace the data, not append to it
        for table, df in tables.items():
            write_lake(df, table, base_uri=lake.as_uri())

    movies = spark.read.parquet(str(lake / "movies_main"))
    assert movies.count() == 2
    # The Athena DDL declares these exact types; int vs bigint gives HIVE_BAD_DATA.
    assert dict(movies.dtypes) == {
        "id": "int", "title": "string", "release_date": "date", "budget": "double", "revenue": "double",
    }
    assert dict(spark.read.parquet(str(lake / "ratings")).dtypes)["last_rated"] == "timestamp"
    assert len(list((lake / "movies_main").glob("part-*.parquet"))) == 1  # coalesce(1)
