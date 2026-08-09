"""Cleaning rules for raw.movies_main.

Findings this is based on (profiled against the real data, see the
capstone's data quality review):
  - 50 ids appear more than once in the raw source, but almost all are
    formatting noise (same date in a different format, or a stray trailing
    space in the title) rather than real conflicts -- normalizing those
    fields first collapses nearly all of them into true duplicates.
  - release_date mixes three formats with no stray/unrecognized values:
    ISO YYYY-MM-DD, MM/DD/YYYY (slash), DD-MM-YYYY (dash). The delimiter
    deterministically signals the convention (verified: no slash-date has a
    month > 12, no dash-date has a "month" component > 12).
  - budget/revenue are 0 for 74.5%/83.7% of rows -- implausible as literal
    zero at that rate, almost certainly this source's "not reported"
    convention. Treated as NULL so "unknown" has one representation.
  - 3 rows in the source CSV are genuinely corrupt, not just incomplete --
    their columns are shifted/wrong entirely (e.g. a date string sitting in
    the id column, an image file path sitting in the budget column). These
    have no recoverable id and are dropped outright.
"""

from pyspark.sql import DataFrame
from pyspark.sql import functions as F
from pyspark.sql.window import Window

ISO_DATE = r"^\d{4}-\d{2}-\d{2}$"
SLASH_DATE = r"^\d{1,2}/\d{1,2}/\d{4}$"
DASH_DATE = r"^\d{1,2}-\d{1,2}-\d{4}$"


def _parse_release_date(col: str = "release_date"):
    c = F.col(col)
    return (
        F.when(c.rlike(ISO_DATE), F.to_date(c, "yyyy-MM-dd"))
        .when(c.rlike(SLASH_DATE), F.to_date(c, "M/d/yyyy"))
        .when(c.rlike(DASH_DATE), F.to_date(c, "d-M-yyyy"))
        .otherwise(F.lit(None).cast("date"))
    )


def _zero_to_null(col: str):
    return F.when(F.col(col) == 0, F.lit(None)).otherwise(F.col(col))


def clean_movies(df: DataFrame) -> DataFrame:
    # Corrupt rows with shifted/garbage columns have no recoverable id.
    df = df.filter(F.col("id").isNotNull())

    df = (
        df.withColumn("title", F.trim(F.col("title")))
        .withColumn("release_date", _parse_release_date())
        .withColumn("budget", _zero_to_null("budget"))
        .withColumn("revenue", _zero_to_null("revenue"))
    )

    # Collapse duplicates that only differed by whitespace/date-format noise
    # now that both are normalized.
    df = df.dropDuplicates()

    # Any id still duplicated at this point is a real conflict (different
    # budget/revenue for the same movie) -- keep the most complete row.
    completeness = (
        F.col("title").isNotNull().cast("int")
        + F.col("release_date").isNotNull().cast("int")
        + F.col("budget").isNotNull().cast("int")
        + F.col("revenue").isNotNull().cast("int")
    )
    window = Window.partitionBy("id").orderBy(completeness.desc())
    df = (
        df.withColumn("_rank", F.row_number().over(window))
        .filter(F.col("_rank") == 1)
        .drop("_rank")
    )

    return df
