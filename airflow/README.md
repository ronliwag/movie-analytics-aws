# Airflow Orchestration

Orchestrates the full pipeline end to end: pandas cleaning -> PySpark
ingest/load -> dbt run/test -> (Power BI refresh is manual/scheduled
separately). The DAG has 4 tasks, not 3 -- `scripts/pyspark/transform.py`'s
`clean()` step reads `data/processed/*_clean.csv`, which only
`scripts/pandas/clean_data.py` produces, so that has to run first. See the
module docstring in `dags/movie_analytics_dag.py` for the full reasoning.
`scripts/enrichment/*` stays out of the DAG -- it's a one-time/manual step,
not part of the repeatable scheduled batch (see its own README).

## Local setup

This directory's `docker-compose.yaml` is the official Airflow Celery
quick-start, customized with a `Dockerfile` (see below) rather than the
vanilla `apache/airflow` image -- a bare `pip install apache-airflow` isn't
used at all, on the host or in the image, since the base pip install
doesn't pin dependencies correctly for most environments.

```
docker compose build   # builds the custom image (Dockerfile) -- first time, and after Dockerfile/requirements-pipeline.txt changes
docker compose up -d
```

Airflow UI: [http://localhost:8080](http://localhost:8080) (default
login `airflow`/`airflow`, set via `_AIRFLOW_WWW_USER_USERNAME`/
`_PASSWORD` in `.env` if you want to change it).

## Tasks
- Build a DAG that runs: pandas clean -> PySpark job -> dbt run -> dbt test,
  in that order
- Schedule it (e.g. daily)
- Give every task retries and a sane `retry_delay`
- Use task dependencies (`>>`) to enforce the order — a broken upstream task
  should not let dbt build on stale data

## Why a custom image (`Dockerfile` + `requirements-pipeline.txt`)

The stock Airflow image has neither a JVM (PySpark needs one) nor this
project's Python dependencies, and installing them isn't as simple as
`pip install -r requirements.txt` into Airflow's own environment:

- **pandas/pyspark/psycopg2-binary/python-dotenv/dbt-postgres** go into a
  separate `/opt/pipeline-venv`, not Airflow's own site-packages --
  `dbt-common` (a `dbt-postgres` dependency) requires `pathspec<1.1`, while
  Airflow 3.3.1's own constraints file pins `pathspec==1.1.1`. That's a
  real conflict (confirmed by trying: `pip` reports
  `ResolutionImpossible`), not just a style preference. `PYTHON_BIN`/
  `DBT_BIN` in the DAG point at this venv's binaries directly.
- Exact versions are pinned in `requirements-pipeline.txt` rather than
  loose `>=` bounds -- pyspark ships no prebuilt wheel (a ~450MB
  source-only sdist), so an unpinned resolver backtracking through
  candidate versions means repeated ~450MB downloads. One exact pin
  downloads it once.
- The `/opt/pipeline-venv` build step runs as root (`/opt` is root-owned)
  -- harmless, since `docker-compose.yaml` overrides the runtime user via
  `user: "${AIRFLOW_UID:-50000}:0"` on every service regardless of what
  user the image ends on, and the venv's files stay world-readable/
  executable (standard umask) so that runtime user can still run its
  binaries.

## Prerequisites for the DAG's tasks to succeed

`dags/movie_analytics_dag.py` resolves `PROJECT_ROOT`/`PYTHON_BIN`/`DBT_BIN`
from `MOVIE_ANALYTICS_*` env vars (see `docker-compose.yaml`'s
`airflow-common-env`), falling back to this file's own on-disk location and
`PROJECT_ROOT/venv/bin/*` when those aren't set (i.e. running Airflow
directly on this host/checkout instead of the Docker Compose setup above).
Whichever way it runs, it needs:

- The full repo readable (and, for `data/processed/`, `dbt_project/target/`
  etc., writable) at `PROJECT_ROOT` -- `docker-compose.yaml` bind-mounts the
  whole repo (`..`) to `/opt/project` for this; a host-direct run already
  has it since `PROJECT_ROOT` just resolves to the checkout itself.
- A real `.env` (not just `.env.example`) with `DB_HOST`/`DB_PORT`/
  `DB_NAME`/`DB_USER`/`DB_PASSWORD` at the repo root. In the Docker Compose
  setup, `.env`'s `DB_HOST=localhost` is overridden to `host.docker.internal`
  (`MOVIE_ANALYTICS_DB_HOST_OVERRIDE` + `extra_hosts: host-gateway`) since
  `localhost` inside a container isn't the host.
- `~/.dbt/profiles.yml` (the `movie_analytics` profile — see
  [../dbt_project/README.md](../dbt_project/README.md)). In the Docker
  Compose setup this is bind-mounted read-only from the host
  (`HOST_DBT_PROFILES_DIR` in `.env`) to `/home/airflow/.dbt`; a host-direct
  run already has it at its normal location.

## How each task's shell command is built

Every `BashOperator`'s `bash_command` starts with the same preamble
(`_preamble()` in the DAG file): `set -euo pipefail`, `cd` into
`PROJECT_ROOT` (so `python -m scripts...` module imports resolve), then
`source .env` to turn `DB_HOST`/`PORT`/`NAME`/`USER`/`PASSWORD` into real OS
environment variables. That last part matters specifically for
`dbt_run`/`dbt_test`: dbt's `env_var()` Jinja calls read `os.environ`
directly and dbt never loads a `.env` file itself, unlike
`scripts/pyspark/transform.py`, which calls `load_dotenv()` for itself.
Applied to all four tasks uniformly rather than special-casing the two dbt
ones.

If `MOVIE_ANALYTICS_DB_HOST_OVERRIDE` is set in the task's own environment,
`DB_HOST` is re-applied *after* `source .env` -- otherwise sourcing would
clobber it back to `.env`'s literal `DB_HOST=localhost`, which doesn't
resolve to the dev Postgres from inside a container (see the Docker Compose
setup above).

## Retries and failure handling

- `retries=3` with exponential backoff (`retry_delay=5min`,
  `max_retry_delay=30min`) on every task via `default_args` -- sane,
  easily-tunable defaults, not precisely calibrated. Adjust once real
  failure-mode data exists.
- `max_active_runs=1` on the DAG: `transform.py` writes Postgres tables
  with `mode="overwrite"`, so two overlapping runs would race/corrupt the
  `raw.*`/`clean.*` tables.
- `on_failure_callback=alert_on_failure` (in the DAG file) is a minimal,
  dependency-free failure hook -- no Slack webhook or SMTP credentials
  exist anywhere in this repo, so it just emits one structured `ERROR` log
  line (dag/task/run_id/try_number/exception) rather than inventing alert
  infra that doesn't exist. `email_on_failure`/`email_on_retry` are
  explicitly `False` for the same reason (no SMTP configured). Swap
  `alert_on_failure`'s body for a real Slack/email/pager call once
  credentials are provisioned -- the `default_args` wiring won't need to
  change.

## Airflow 3.x notes

Two APIs commonly seen in older Airflow tutorials don't exist in 3.3.1
(the version this project's `docker-compose.yaml`/`Dockerfile` pin):
`airflow.utils.dates.days_ago` was removed (the DAG uses a fixed
`pendulum.datetime(...)` `start_date` instead -- also just a better
pattern than a relative date, which would shift on every DAG parse), and
`DAG(schedule_interval=...)` was renamed to `DAG(schedule=...)`.

## Grading focus (dbt / Airflow — 25% of the rubric)
- `source()`/`ref()` and Airflow orchestration — DAG runs the pipeline
  end to end, scheduled, with retries on every task (5%)

See [../docs/EVALUATION.md](../docs/EVALUATION.md) for the full rubric.
