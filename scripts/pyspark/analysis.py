"""PySpark analytical views and statistical summaries.

Builds on the cleaned DataFrame(s) produced in transform.py.
"""

from scripts.pyspark.transform import get_spark


def build_views(spark, movies_df):
    # TODO: movies_df.createOrReplaceTempView("movies") and any additional
    # views needed for downstream SQL analysis.
    raise NotImplementedError


def revenue_by_genre(spark):
    # TODO: spark.sql("SELECT ... FROM movies ...") aggregating revenue/
    # rating by genre.
    raise NotImplementedError


def yearly_summary(spark):
    # TODO: statistical summary (count, avg budget/revenue, avg rating) per
    # release year.
    raise NotImplementedError


def main():
    spark = get_spark()
    # TODO: orchestrate view creation + analysis, show()/write results.
    spark.stop()


if __name__ == "__main__":
    main()
