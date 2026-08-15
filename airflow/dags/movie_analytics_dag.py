"""See ../README.md for what this DAG does, how, and why."""

import logging
import os
from datetime import timedelta
from pathlib import Path

import pendulum
from airflow import DAG
from airflow.operators.bash import BashOperator

log = logging.getLogger(__name__)

PROJECT_ROOT = Path(
    os.environ.get("MOVIE_ANALYTICS_PROJECT_ROOT", str(Path(__file__).resolve().parents[2]))
)
VENV_BIN = PROJECT_ROOT / "venv" / "bin"
PYTHON_BIN = os.environ.get("MOVIE_ANALYTICS_PYTHON_BIN", str(VENV_BIN / "python"))
DBT_BIN = os.environ.get("MOVIE_ANALYTICS_DBT_BIN", str(VENV_BIN / "dbt"))
DBT_PROJECT_DIR = PROJECT_ROOT / "dbt_project"
ENV_FILE = PROJECT_ROOT / ".env"


def _preamble() -> str:
    return (
        "set -euo pipefail\n"
        f'cd "{PROJECT_ROOT}"\n'
        "set -a\n"
        f'source "{ENV_FILE}"\n'
        'if [ -n "${MOVIE_ANALYTICS_DB_HOST_OVERRIDE:-}" ]; then '
        'DB_HOST="$MOVIE_ANALYTICS_DB_HOST_OVERRIDE"; fi\n'
        "set +a\n"
    )


def alert_on_failure(context):
    ti = context["task_instance"]
    log.error(
        "[movie_analytics_pipeline] task failed | dag=%s task=%s run_id=%s "
        "try=%s | exception=%r",
        ti.dag_id,
        ti.task_id,
        context.get("run_id"),
        ti.try_number,
        context.get("exception"),
    )


default_args = {
    "owner": "trainee",
    "retries": 3,
    "retry_delay": timedelta(minutes=5),
    "retry_exponential_backoff": True,
    "max_retry_delay": timedelta(minutes=30),
    "email_on_failure": False,
    "email_on_retry": False,
    "on_failure_callback": alert_on_failure,
}

with DAG(
    dag_id="movie_analytics_pipeline",
    default_args=default_args,
    schedule="@daily",
    start_date=pendulum.datetime(2024, 1, 1, tz="UTC"),
    catchup=False,
    max_active_runs=1,
    dagrun_timeout=timedelta(hours=2),
    tags=["movie-analytics-capstone"],
) as dag:

    run_pandas_clean = BashOperator(
        task_id="run_pandas_clean",
        bash_command=_preamble() + f'"{PYTHON_BIN}" -m scripts.pandas.clean_data',
    )

    run_pyspark_transform = BashOperator(
        task_id="run_pyspark_transform",
        bash_command=_preamble() + f'"{PYTHON_BIN}" scripts/pyspark/transform.py',
    )

    dbt_run = BashOperator(
        task_id="dbt_run",
        bash_command=_preamble()
        + (
            f'"{DBT_BIN}" deps --project-dir "{DBT_PROJECT_DIR}"\n'
            f'"{DBT_BIN}" run --project-dir "{DBT_PROJECT_DIR}"'
        ),
    )

    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command=_preamble() + f'"{DBT_BIN}" test --project-dir "{DBT_PROJECT_DIR}"',
    )

    run_pandas_clean >> run_pyspark_transform >> dbt_run >> dbt_test
