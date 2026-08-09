"""Verifies each cleaning rule in scripts/pyspark/cleaning/ against small,
hand-built DataFrames covering the anomalies documented in
scripts/pyspark/cleaning/README.md -- doesn't touch the real CSVs/Postgres,
so it's fast and deterministic.

Run with: pytest scripts/pyspark/test_cleaned.py -v
"""

from datetime import datetime

import pytest
from pyspark.sql.types import (
    DoubleType,
    IntegerType,
    StringType,
    StructField,
    StructType,
    TimestampType,
)

from scripts.pyspark.cleaning.extended import clean_extended
from scripts.pyspark.cleaning.movies import clean_movies
from scripts.pyspark.cleaning.ratings import clean_ratings
from scripts.pyspark.transform import (
    MOVIE_EXTENDED_SCHEMA,
    MOVIES_MAIN_SCHEMA,
    clean,
    get_spark,
)

RATINGS_SCHEMA = StructType(
    [
        StructField("movie_id", IntegerType(), True),
        StructField("avg_rating", DoubleType(), True),
        StructField("total_ratings", IntegerType(), True),
        StructField("std_dev", DoubleType(), True),
        StructField("last_rated", TimestampType(), True),
    ]
)


@pytest.fixture(scope="session")
def spark():
    session = get_spark()
    yield session
    session.stop()


def rows_by_id(df, id_col="id"):
    return {r[id_col]: r.asDict() for r in df.collect()}


# --------------------------------------------------------------------------
# clean_movies
# --------------------------------------------------------------------------


def test_drops_corrupt_rows_with_null_id(spark):
    df = spark.createDataFrame(
        [
            (1, "Valid Movie", "2020-01-01", 1000.0, 2000.0),
            (None, None, None, 0.0, None),  # shifted/garbage row, no id
        ],
        schema=MOVIES_MAIN_SCHEMA,
    )
    cleaned = clean_movies(df)
    assert cleaned.filter("id is null").count() == 0
    assert cleaned.count() == 1


def test_trims_title_whitespace(spark):
    df = spark.createDataFrame(
        [(1, "The Movie ", "2020-01-01", None, None)], schema=MOVIES_MAIN_SCHEMA
    )
    result = clean_movies(df).collect()[0]
    assert result["title"] == "The Movie"


@pytest.mark.parametrize(
    "raw_date,expected",
    [
        ("2012-03-22", "2012-03-22"),  # ISO YYYY-MM-DD
        ("10/30/1995", "1995-10-30"),  # slash MM/DD/YYYY
        ("15-12-1995", "1995-12-15"),  # dash DD-MM-YYYY
    ],
)
def test_parses_all_three_date_formats(spark, raw_date, expected):
    df = spark.createDataFrame([(1, "T", raw_date, None, None)], schema=MOVIES_MAIN_SCHEMA)
    result = clean_movies(df).collect()[0]
    assert str(result["release_date"]) == expected


def test_unrecognized_date_format_becomes_null(spark):
    df = spark.createDataFrame(
        [(1, "T", "not-a-date", None, None)], schema=MOVIES_MAIN_SCHEMA
    )
    result = clean_movies(df).collect()[0]
    assert result["release_date"] is None


def test_budget_and_revenue_zero_become_null(spark):
    df = spark.createDataFrame([(1, "T", "2020-01-01", 0.0, 0.0)], schema=MOVIES_MAIN_SCHEMA)
    result = clean_movies(df).collect()[0]
    assert result["budget"] is None
    assert result["revenue"] is None


def test_nonzero_budget_and_revenue_untouched(spark):
    df = spark.createDataFrame(
        [(1, "T", "2020-01-01", 500.0, 900.0)], schema=MOVIES_MAIN_SCHEMA
    )
    result = clean_movies(df).collect()[0]
    assert result["budget"] == 500.0
    assert result["revenue"] == 900.0


def test_formatting_noise_duplicates_collapse_to_one_row(spark):
    # Same movie, same date, just written in two different raw formats.
    df = spark.createDataFrame(
        [
            (1, "A Place at the Table", "2012-03-22", None, None),
            (1, "A Place at the Table", "22-03-2012", None, None),
        ],
        schema=MOVIES_MAIN_SCHEMA,
    )
    cleaned = clean_movies(df)
    assert cleaned.count() == 1


def test_genuine_conflict_keeps_the_more_complete_row(spark):
    # Same movie, but one copy is missing the budget -- keep the one that has it.
    df = spark.createDataFrame(
        [
            (1, "Movie", "2020-01-01", 3.0e7, 3.3e7),
            (1, "Movie", "2020-01-01", 0.0, 3.3e7),  # budget -> NULL after cleaning
        ],
        schema=MOVIES_MAIN_SCHEMA,
    )
    cleaned = clean_movies(df)
    assert cleaned.count() == 1
    assert cleaned.collect()[0]["budget"] == 3.0e7


# --------------------------------------------------------------------------
# clean_extended
# --------------------------------------------------------------------------


def test_splits_genres_and_companies_into_trimmed_arrays(spark):
    df = spark.createDataFrame(
        [(1, "Animation, Comedy,Family", "Pixar, Disney ", "[]", "[]")],
        schema=MOVIE_EXTENDED_SCHEMA,
    )
    result = clean_extended(df).collect()[0]
    assert result["genres"] == ["Animation", "Comedy", "Family"]
    assert result["production_companies"] == ["Pixar", "Disney"]


def test_null_genres_becomes_empty_array(spark):
    df = spark.createDataFrame([(1, None, None, "[]", "[]")], schema=MOVIE_EXTENDED_SCHEMA)
    result = clean_extended(df).collect()[0]
    assert result["genres"] == []
    assert result["production_companies"] == []


def test_parses_production_countries_python_repr(spark):
    df = spark.createDataFrame(
        [
            (
                1,
                "Drama",
                "Studio",
                "[{'iso_3166_1': 'US', 'name': 'United States of America'}, "
                "{'iso_3166_1': 'FR', 'name': 'France'}]",
                "[{'iso_639_1': 'en', 'name': 'English'}]",
            )
        ],
        schema=MOVIE_EXTENDED_SCHEMA,
    )
    result = clean_extended(df).collect()[0]
    assert result["production_countries"] == ["United States of America", "France"]
    assert result["spoken_languages"] == ["English"]


def test_malformed_countries_string_becomes_empty_array(spark):
    df = spark.createDataFrame(
        [(1, "Drama", "Studio", "not a valid literal", "[]")], schema=MOVIE_EXTENDED_SCHEMA
    )
    result = clean_extended(df).collect()[0]
    assert result["production_countries"] == []


def test_duplicate_extended_keeps_most_complete_row(spark):
    df = spark.createDataFrame(
        [
            (1, "Drama", None, "[]", "[]"),
            (1, "Drama", "Studio A", "[]", "[]"),
        ],
        schema=MOVIE_EXTENDED_SCHEMA,
    )
    cleaned = clean_extended(df)
    assert cleaned.count() == 1
    assert cleaned.collect()[0]["production_companies"] == ["Studio A"]


# --------------------------------------------------------------------------
# clean_ratings
# --------------------------------------------------------------------------


def test_nan_std_dev_becomes_null(spark):
    df = spark.createDataFrame(
        [(1, 5.0, 1, float("nan"), datetime(2020, 1, 1))], schema=RATINGS_SCHEMA
    )
    result = clean_ratings(df).collect()[0]
    assert result["std_dev"] is None


def test_normal_std_dev_untouched(spark):
    df = spark.createDataFrame(
        [(1, 3.5, 20, 0.8, datetime(2020, 1, 1))], schema=RATINGS_SCHEMA
    )
    result = clean_ratings(df).collect()[0]
    assert result["std_dev"] == 0.8


def test_null_std_dev_stays_null(spark):
    df = spark.createDataFrame(
        [(1, 3.5, 20, None, datetime(2020, 1, 1))], schema=RATINGS_SCHEMA
    )
    result = clean_ratings(df).collect()[0]
    assert result["std_dev"] is None


# --------------------------------------------------------------------------
# clean() orchestrator -- cross-table rule
# --------------------------------------------------------------------------


def test_orchestrator_drops_movie_extended_orphans(spark):
    movies_df = spark.createDataFrame(
        [(1, "Movie One", "2020-01-01", None, None)], schema=MOVIES_MAIN_SCHEMA
    )
    extended_df = spark.createDataFrame(
        [
            (1, "Drama", "Studio", "[]", "[]"),
            (2, "Comedy", "Studio", "[]", "[]"),  # id 2 has no matching movie
        ],
        schema=MOVIE_EXTENDED_SCHEMA,
    )
    ratings_df = spark.createDataFrame([], schema=RATINGS_SCHEMA)

    result = clean(movies_df, extended_df, ratings_df)

    assert result["movie_extended"].count() == 1
    assert result["movie_extended"].collect()[0]["id"] == 1
