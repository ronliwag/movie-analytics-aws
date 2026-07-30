# Evaluation

Mirrors the program's Capstone Evaluation Rubric — four technical areas at
25% each, plus professional criteria. Each
technical criterion is scored 1–4 (Novice / Developing / Proficient /
Advanced); Proficient (3) is the target level.

## SQL — 25% (`scripts/sql/`)
- Database schema design — 5%
- Table relationships — 5%
- Advanced SQL (LAG, LEAD, window functions) — 10%
- Query optimization — 5%

## Python/Pandas — 25% (`scripts/pandas/`)
- Python classes — 5%
- Data processing functions — 10%
- Pandas operations — 10%

## dbt — 25% (`dbt_project/`)
- SQL and modelling logic (CTEs, modular, DRY) — 10%
- Project structure (staging/intermediate/marts clearly separated) — 5%
- Testing and documentation (generic tests + descriptions on all models) — 5%
- Correct use of `source()` and `ref()` — 5%

## Power BI — 25% (`powerbi/`)
- Data model design — 5%
- Calculations and measures — 10%
- Data storytelling — 10%

## Not separately scored, but required
PySpark (`scripts/pyspark/`) and Airflow (`airflow/dags/`) are required
technical deliverables per the capstone brief — a working end-to-end
pipeline depends on them — but they aren't their own scored line item.
A broken PySpark job or DAG will show up as missing/stale data in the dbt
and Power BI scores instead.

## Professional criteria
Communication, time management, professional tone, proactiveness,
curiosity, learning drive, and presentation skills — assessed throughout
the capstone, not just at the Week 12 presentation.

Passing grade: 70%.
