"""Cleaning rules for raw.ratings.

Finding this is based on: std_dev is NaN (not NULL) for 3,063 rows (33.8%
of the table), always when total_ratings = 1 -- standard deviation of a
single value is mathematically undefined. NaN behaves inconsistently in SQL
(e.g. it silently wins MAX()), so it's converted to NULL here.
"""

from pyspark.sql import DataFrame
from pyspark.sql import functions as F


def clean_ratings(df: DataFrame) -> DataFrame:
    return df.withColumn(
        "std_dev",
        F.when(F.isnan(F.col("std_dev")), F.lit(None)).otherwise(F.col("std_dev")),
    )
