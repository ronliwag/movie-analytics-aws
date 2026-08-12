"""PySpark ingestion + transformation of the movie dataset.

Reads from data/enriched/ (scripts/enrichment/), not data/raw/ -- see
that package's README for what it fills/corrects and why. Enrichment
doesn't dedupe, drop corrupt rows, or standardize formats, so this file's
job is unchanged from when it read data/raw/ directly; only SOURCE_DIR
moved. Requires enrichment to have been run at least once already.
"""

import os
from pathlib import Path

import psycopg2
from dotenv import load_dotenv
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import (
    DateType,
    DoubleType,
    IntegerType,
    StringType,
    StructField,
    StructType,
    TimestampType,
)

load_dotenv()

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
SOURCE_DIR = DATA_DIR / "enriched"
JARS_DIR = Path(__file__).resolve().parent / "jars"

# `id` is DoubleType, not IntegerType, on purpose: scripts/enrichment/
# fill_missing.py coerces `id` to a nullable float (pd.to_numeric with
# errors="coerce", to hold NaN for the 3 corrupt rows) before writing CSV,
# so data/enriched/*.csv actually stores it as "862.0", not "862". Spark's
# CSV reader can't parse "862.0" as IntegerType (returns NULL, silently,
# for every row) but reads it fine as DoubleType -- load_movies()/
# load_extended() cast it to a real integer afterward via .withColumn().
MOVIES_MAIN_SCHEMA = StructType(
    [
        StructField("id", DoubleType(), True),
        StructField("title", StringType(), True),
        # Kept as text: the source mixes date formats (e.g. "10/30/1995" vs
        # "15-12-1995") -- casting to DATE here would silently misparse rows.
        # Standardizing this is part of clean(), not ingestion.
        StructField("release_date", StringType(), True),
        StructField("budget", DoubleType(), True),
        StructField("revenue", DoubleType(), True),
    ]
)

# Column order matches data/enriched/movie_extended.csv exactly -- Spark
# applies an explicit `schema` positionally, not by matching header names.
# original_title/original_language/director/cast are 4 columns
# scripts/enrichment/fill_missing.py adds that don't exist in data/raw/ at
# all.
MOVIE_EXTENDED_SCHEMA = StructType(
    [
        StructField("id", DoubleType(), True),  # see MOVIES_MAIN_SCHEMA's comment on `id`
        StructField("genres", StringType(), True),
        StructField("production_companies", StringType(), True),
        # Python-repr lists of dicts (single-quoted, not valid JSON) -- kept
        # raw, to be parsed properly in a later cleaning step.
        StructField("production_countries", StringType(), True),
        StructField("spoken_languages", StringType(), True),
        StructField("original_title", StringType(), True),
        StructField("original_language", StringType(), True),
        StructField("director", StringType(), True),
        StructField("cast", StringType(), True),
    ]
)

# Column order here must match the real CSV column order exactly -- Spark
# applies an explicit `schema` positionally, not by matching header names.
CLEAN_MOVIES_SCHEMA = StructType(
    [
        StructField("id", IntegerType(), True),
        StructField("title", StringType(), True),
        StructField("release_date", DateType(), True),
        StructField("budget", DoubleType(), True),
        StructField("revenue", DoubleType(), True),
    ]
)

CLEAN_EXTENDED_SCHEMA = StructType(
    [
        StructField("id", IntegerType(), True),
        StructField("genres", StringType(), True),
        StructField("production_companies", StringType(), True),
        StructField("original_title", StringType(), True),
        StructField("original_language", StringType(), True),
        StructField("director", StringType(), True),
        StructField("cast", StringType(), True),
        StructField("production_country_codes", StringType(), True),
        StructField("production_country_names", StringType(), True),
        StructField("spoken_language_codes", StringType(), True),
        StructField("spoken_language_names", StringType(), True),
    ]
)

CLEAN_RATINGS_SCHEMA = StructType(
    [
        StructField("movie_id", IntegerType(), True),
        StructField("last_rated", TimestampType(), True),
        StructField("avg_rating", DoubleType(), True),
        StructField("total_ratings", IntegerType(), True),
        StructField("std_dev", DoubleType(), True),
    ]
)


def get_spark() -> SparkSession:
    builder = SparkSession.builder.appName("movie-analytics-capstone").master("local[*]")

    jars = sorted(JARS_DIR.glob("postgresql-*.jar")) if JARS_DIR.exists() else []
    if jars:
        builder = builder.config("spark.jars", ",".join(str(j) for j in jars))

    return builder.getOrCreate()


def load_movies(spark: SparkSession) -> DataFrame:
    df = spark.read.csv(str(SOURCE_DIR / "movies_main.csv"), header=True, schema=MOVIES_MAIN_SCHEMA)
    return df.withColumn("id", F.col("id").cast(IntegerType()))


def load_extended(spark: SparkSession) -> DataFrame:
    df = spark.read.csv(
        str(SOURCE_DIR / "movie_extended.csv"), header=True, schema=MOVIE_EXTENDED_SCHEMA
    )
    return df.withColumn("id", F.col("id").cast(IntegerType()))


def load_ratings(spark: SparkSession) -> DataFrame:
    raw = spark.read.option("multiLine", True).json(str(SOURCE_DIR / "ratings.json"))
    return raw.select(
        F.col("movie_id").cast(IntegerType()).alias("movie_id"),
        F.col("ratings_summary.avg_rating").alias("avg_rating"),
        F.col("ratings_summary.total_ratings").cast(IntegerType()).alias("total_ratings"),
        F.col("ratings_summary.std_dev").alias("std_dev"),
        F.timestamp_seconds(F.col("last_rated")).alias("last_rated"),
    )


def clean(spark: SparkSession, processed_dir: Path | None = None) -> dict[str, DataFrame]:
    """Loads the already-cleaned CSVs produced by scripts/pandas/clean_data.py
    -- one per raw source, mirroring raw.movies_main/movie_extended/ratings."""
    
    base = processed_dir or (DATA_DIR / "processed")
    return {
        "movies_main": spark.read.csv(
            str(base / "movies_main_clean.csv"), header=True, schema=CLEAN_MOVIES_SCHEMA
        ),
        "movie_extended": spark.read.csv(
            str(base / "movie_extended_clean.csv"), header=True, schema=CLEAN_EXTENDED_SCHEMA
        ),
        "ratings": spark.read.csv(
            str(base / "ratings_clean.csv"), header=True, schema=CLEAN_RATINGS_SCHEMA
        ),
    }


def jdbc_url() -> str:
    return f"jdbc:postgresql://{os.environ['DB_HOST']}:{os.environ['DB_PORT']}/{os.environ['DB_NAME']}"


def jdbc_properties() -> dict:
    return {
        "user": os.environ["DB_USER"],
        "password": os.environ["DB_PASSWORD"],
        "driver": "org.postgresql.Driver",
    }


def ensure_schema(schema: str) -> None:
    conn = psycopg2.connect(
        host=os.environ["DB_HOST"],
        port=os.environ["DB_PORT"],
        dbname=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
    )
    try:
        with conn, conn.cursor() as cur:
            cur.execute(f"CREATE SCHEMA IF NOT EXISTS {schema};")
    finally:
        conn.close()


def write_table(df: DataFrame, schema: str, table: str) -> None:
    df.write.jdbc(
        url=jdbc_url(), table=f"{schema}.{table}", mode="overwrite", properties=jdbc_properties()
    )


def main():
    # Postgres schema is still named "raw" (meaning "pre-clean"), even
    # though its actual source is now data/enriched/, not data/raw/ -- see
    # SOURCE_DIR / the module docstring.
    ensure_schema("raw")
    ensure_schema("clean")

    spark = get_spark()
    try:
        raw_tables = {
            "movies_main": load_movies(spark),
            "movie_extended": load_extended(spark),
            "ratings": load_ratings(spark),
        }
        for table, df in raw_tables.items():
            write_table(df, "raw", table)
            print(f"raw.{table}: {df.count()} rows")

        cleaned_tables = clean(spark)
        for table, df in cleaned_tables.items():
            write_table(df, "clean", table)
            print(f"clean.{table}: {df.count()} rows")
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
