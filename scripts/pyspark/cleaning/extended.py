"""Cleaning rules for raw.movie_extended.

Turns the malformed source columns into proper typed columns. Does NOT
build genre/company/country dimension tables -- that's the later schema
normalization step, not cleaning.

Findings this is based on:
  - genres/production_companies are comma-separated strings (e.g.
    "Animation,Comedy,Family") -- split into trimmed arrays.
  - production_countries/spoken_languages are Python-repr lists of dicts
    (single-quoted, NOT valid JSON), e.g.
    "[{'iso_3166_1': 'US', 'name': 'United States of America'}]".
    ast.literal_eval parses 100% of the distinct non-empty values in this
    dataset with zero failures (verified), so it's used here via a UDF
    rather than a regex.
  - 30 ids in the raw source appear more than once; ties are broken by
    keeping whichever row has the most non-empty fields.
"""

import ast

from pyspark.sql import DataFrame
from pyspark.sql import functions as F
from pyspark.sql.types import ArrayType, StringType
from pyspark.sql.window import Window


def _split_trim(col: str):
    c = F.col(col)
    parts = F.transform(F.split(c, ","), lambda x: F.trim(x))
    return F.when(c.isNull() | (F.trim(c) == ""), F.array().cast("array<string>")).otherwise(parts)


def _extract_names(raw):
    if not raw:
        return []
    try:
        parsed = ast.literal_eval(raw)
    except (ValueError, SyntaxError):
        return []
    if not isinstance(parsed, list):
        return []
    return [d.get("name") for d in parsed if isinstance(d, dict) and d.get("name")]


_extract_names_udf = F.udf(_extract_names, ArrayType(StringType()))


def clean_extended(df: DataFrame) -> DataFrame:
    df = (
        df.withColumn("genres", _split_trim("genres"))
        .withColumn("production_companies", _split_trim("production_companies"))
        .withColumn("production_countries", _extract_names_udf(F.col("production_countries")))
        .withColumn("spoken_languages", _extract_names_udf(F.col("spoken_languages")))
    )

    df = df.dropDuplicates()

    completeness = (
        (F.size(F.col("genres")) > 0).cast("int")
        + (F.size(F.col("production_companies")) > 0).cast("int")
        + (F.size(F.col("production_countries")) > 0).cast("int")
        + (F.size(F.col("spoken_languages")) > 0).cast("int")
    )
    window = Window.partitionBy("id").orderBy(completeness.desc())
    df = (
        df.withColumn("_rank", F.row_number().over(window))
        .filter(F.col("_rank") == 1)
        .drop("_rank")
    )

    return df
