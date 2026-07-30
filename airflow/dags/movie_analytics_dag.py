"""Orchestrates the movie analytics pipeline: PySpark -> dbt run -> dbt test.

See ../README.md for local Airflow setup instructions.
"""

from datetime import timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.utils.dates import days_ago

default_args = {
    "owner": "trainee",
    "retries": 3,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="movie_analytics_pipeline",
    default_args=default_args,
    schedule_interval="@daily",
    start_date=days_ago(1),
    catchup=False,
    tags=["movie-analytics-capstone"],
) as dag:

    # TODO: replace with a real BashOperator/PythonOperator call into
    # scripts/pyspark/transform.py (spark-submit or python -m).
    run_pyspark = BashOperator(
        task_id="run_pyspark_transform",
        bash_command="echo 'TODO: spark-submit scripts/pyspark/transform.py'",
    )

    # TODO: point --project-dir/--profiles-dir at dbt_project/
    dbt_run = BashOperator(
        task_id="dbt_run",
        bash_command="echo 'TODO: dbt run --project-dir dbt_project'",
    )

    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command="echo 'TODO: dbt test --project-dir dbt_project'",
    )

    run_pyspark >> dbt_run >> dbt_test
