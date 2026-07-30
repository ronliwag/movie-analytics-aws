"""PySpark ingestion + transformation of the movie dataset."""

from pathlib import Path
from pyspark.sql import SparkSession

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"


def get_spark() -> SparkSession:
    return (
        SparkSession.builder.appName("movie-analytics-capstone")
        .master("local[*]")
        .getOrCreate()
    )


def load_movies(spark: SparkSession):
    # TODO: spark.read.csv(str(DATA_DIR / "raw" / "movies_main.csv"), header=True, inferSchema=True)
    raise NotImplementedError


def load_ratings(spark: SparkSession):
    # TODO: spark.read.json(str(DATA_DIR / "raw" / "ratings.json"))
    raise NotImplementedError


def load_extended(spark: SparkSession):
    # TODO: spark.read.csv(str(DATA_DIR / "raw" / "movie_extended.csv"), header=True, inferSchema=True)
    raise NotImplementedError


def clean(movies_df):
    # TODO: dedupe, standardize dates, handle missing budgets using Spark
    # SQL functions (pyspark.sql.functions).
    raise NotImplementedError


def main():
    spark = get_spark()
    # TODO: load, clean, join, and write out to data/processed/ (parquet).
    spark.stop()


if __name__ == "__main__":
    main()
