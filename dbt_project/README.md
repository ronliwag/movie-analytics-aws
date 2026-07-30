# dbt Project

Three-layer dbt project on top of the PySpark output (loaded into
PostgreSQL or read from Parquet via an external/staged source).

## Layers

- `models/staging/` — one staging model per source table, light renaming
  and type casting only. Declare sources in `sources.yml`, reference them
  with `source()`.
- `models/intermediate/` — joins and business logic that don't belong in a
  single staging model or a final mart (e.g. combining ratings from
  multiple sources, flattening genres).
- `models/marts/` — final, wide, analytics-ready tables that Power BI reads
  directly. Reference upstream models with `ref()`, never `source()`
  directly in a mart.

## Setup

```
cd dbt_project
dbt deps
dbt seed      # if you add seed files
dbt run
dbt test
dbt docs generate && dbt docs serve
```

## Tasks
- Declare `movies_main`, `ratings`, `movie_extended` (or your PySpark
  output tables) in `models/staging/sources.yml`
- Build `stg_movies`, `stg_ratings`, `stg_movie_extended`
- Build at least one intermediate model joining ratings + genres +
  production companies onto movies
- Build a marts fact table (e.g. `fct_movie_performance`) and any
  dimension tables Power BI needs
- Add generic tests (`unique`, `not_null`) and column/model descriptions
  to every model's `schema.yml`

## Grading focus (dbt / Airflow — 25% of the rubric)
- SQL and modelling logic — CTEs, modular and DRY (10%)
- Project structure — staging/intermediate/marts clearly separated (5%)
- Testing and documentation — generic tests + descriptions on all models (5%)
- Correct use of `source()`/`ref()`, shared with Airflow orchestration (5%)

See [../docs/EVALUATION.md](../docs/EVALUATION.md) for the full rubric.
