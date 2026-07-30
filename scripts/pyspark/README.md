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

```
python scripts/pyspark/transform.py
python -m scripts.pyspark.analysis
```

## Grading focus

PySpark is a required technical deliverable per the capstone brief. It isn't
a separately-weighted rubric line, but its output is what dbt and Power BI
build on — a broken PySpark job blocks the rest of the pipeline. See
[docs/EVALUATION.md](../../docs/EVALUATION.md) for the scored rubric.
