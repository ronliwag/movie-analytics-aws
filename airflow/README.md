# Airflow Orchestration

Orchestrates the full pipeline end to end: PySpark extraction/transform ->
dbt run/test -> (Power BI refresh is manual/scheduled separately).

## Local setup

Use the official Airflow quick-start via Docker Compose rather than a bare
`pip install apache-airflow` — the base pip install doesn't pin
dependencies correctly for most environments.

```
curl -LfO 'https://airflow.apache.org/docs/apache-airflow/stable/docker-compose.yaml'
mkdir -p ./logs ./plugins
echo -e "AIRFLOW_UID=$(id -u)" > .env
docker compose up airflow-init
docker compose up
```

Then drop `dags/movie_analytics_dag.py` into the `dags/` folder the
compose file mounts (or symlink this repo's `airflow/dags/` into it).

## Tasks
- Build a DAG that runs: PySpark job -> dbt run -> dbt test, in that order
- Schedule it (e.g. daily)
- Give every task retries and a sane `retry_delay`
- Use task dependencies (`>>`) to enforce the order — a broken PySpark run
  should not let dbt build on stale data

## Grading focus (dbt / Airflow — 25% of the rubric)
- `source()`/`ref()` and Airflow orchestration — DAG runs the pipeline
  end to end, scheduled, with retries on every task (5%)

See [../docs/EVALUATION.md](../docs/EVALUATION.md) for the full rubric.
