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

## Naming conventions
- `stg_*` — staging models
- `int_*` — intermediate models
- `fct_*` / `dim_*` — marts (fact tables vs. dimension tables)
- Primary key is always `movie_id` (staging renames the source `id` column
  on first contact).
- Money columns (`budget`, `revenue`) are cast to `numeric(15,2)` in
  staging, matching the `DECIMAL(15,2)` convention from
  `scripts/sql/schema.sql`.
- Staging models use an explicit column list, never `select *` — self
  documenting, and guards against silent schema drift from the `clean.*`
  source tables.

## Local setup

- **Warehouse:** Postgres (`dbt-postgres`), the same database
  `scripts/pyspark/transform.py` writes to over JDBC.
- **Profile:** `~/.dbt/profiles.yml` (outside the repo — never commit
  credentials there). Profile name `movie_analytics` must match
  `dbt_project.yml`'s `profile:` key. Uses `env_var()` to read
  `DB_HOST`/`DB_PORT`/`DB_USER`/`DB_PASSWORD`/`DB_NAME` from the shell
  environment, and builds into the `analytics` schema.
- **Sources:** `models/staging/sources.yml` points at the `clean` schema
  (Phase 1's pandas-cleaned output, loaded by `transform.py`'s `clean()`
  step) — not `raw`, which holds the unstandardized load.
- **Invocation:** since `profiles.yml` uses `env_var()`, `.env` needs to be
  loaded into the shell first. Use the `dotenv` CLI already in the venv:

```
dotenv run -- dbt deps --project-dir dbt_project
dotenv run -- dbt debug --project-dir dbt_project
dotenv run -- dbt run --project-dir dbt_project
dotenv run -- dbt test --project-dir dbt_project
dotenv run -- dbt docs generate --project-dir dbt_project && dbt docs serve --project-dir dbt_project
```

Always pass `--project-dir dbt_project` (rather than `cd`-ing into it) so
dbt's log file lands in the gitignored `dbt_project/logs/`, not a stray
`logs/` at the repo root.

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
