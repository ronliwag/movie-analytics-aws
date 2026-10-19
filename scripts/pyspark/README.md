# PySpark Data Processing

## Tasks

### PySpark Fundamentals (`transform.py`)
- Create and manipulate DataFrames from the cleaned Pandas output (or raw
  source files directly)
- Implement Spark SQL functions
- Work with different datasources (CSV, JSON)
- Use built-in functions for analysis
- Write the cleaned result to PostgreSQL or Parquet (batch processing,
  schema enforcement) — this output feeds `dbt_project/` as a source

### Analysis Tasks (`analysis.py`)
- Load and transform movie data at scale
- Perform complex aggregations
- Create analytical views (`createOrReplaceTempView`)
- Generate statistical summaries

## Run

From the repo root, as modules (`-m`), so `from scripts.config import ...`
resolves:

```
python -m scripts.pyspark.transform                    # --target lake (default)
python -m scripts.pyspark.transform --target postgres
python -m scripts.pyspark.analysis
```

`transform.py` loads the clean tables from `data/processed/` and writes them
to one of two targets:

- **`--target lake`** (default): one Parquet file per table to
  `s3a://<bucket>/lake/clean/<table>/`, overwriting the previous run. Athena
  queries them through the Glue tables in `scripts/sql/athena/`. Needs AWS
  credentials (`export AWS_PROFILE=movie-pipeline`). The first run downloads
  the `hadoop-aws` jar and the AWS SDK bundle (~674 MB) from Maven into
  `~/.ivy2*/`.
- **`--target postgres`**: JDBC into `raw.*` and `clean.*`, which dbt reads
  until Phase 4 (dbt-athena). The Airflow DAG uses this target.

## Grading focus (Python / Pandas / PySpark — 25% of the rubric)
- PySpark batch processing — schema enforcement, writes to Postgres/Parquet (5%)

Its output is also what dbt and Power BI build on — a broken PySpark job
blocks the rest of the pipeline regardless of its own score. See
[docs/EVALUATION.md](../../docs/EVALUATION.md) for the full rubric.
