# Evaluation

Mirrors the program's Capstone Evaluation Rubric — four technical areas at
25% each, plus professional criteria. Each technical criterion is scored
1–4 (Novice / Developing / Proficient / Advanced); Proficient (3) is the
target level.

## SQL — 25% (`scripts/sql/`)
- Database schema design — 5%
- Table relationships — 5%
- Advanced SQL (LAG, LEAD, window functions) — 10%
- Query optimization — 5%

## Python / Pandas / PySpark — 25% (`scripts/pandas/`, `scripts/pyspark/`)
- Python classes — 5%
- Data processing functions — 5%
- Pandas operations — 10%
- PySpark batch processing (schema enforcement, writes to Postgres/Parquet) — 5%

## dbt / Airflow — 25% (`dbt_project/`, `airflow/dags/`)
- SQL and modelling logic (CTEs, modular, DRY) — 10%
- Project structure (staging/intermediate/marts clearly separated) — 5%
- Testing and documentation (generic tests + descriptions on all models) — 5%
- `source()`/`ref()` and Airflow orchestration (DAG runs the pipeline
  end to end, scheduled, with retries on every task) — 5%

## Power BI — 25% (`powerbi/`)
- Data model design — 5%
- Calculations and measures — 10%
- Data storytelling — 10%

## Professional criteria
Communication, time management, professional tone, proactiveness,
curiosity, learning drive, and presentation skills — assessed throughout
the capstone, not just at the Week 12 presentation.

Passing grade: 70%.
