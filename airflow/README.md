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

## Grading focus

Airflow is a required technical deliverable per the capstone brief (DAG
orchestrates the full pipeline, scheduled, all tasks have retries). It is
not a separately-weighted line in the scored rubric, but a working DAG
is what demonstrates the pipeline is actually end-to-end. See
[../docs/EVALUATION.md](../docs/EVALUATION.md) for the scored rubric.
