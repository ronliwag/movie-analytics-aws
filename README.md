# Movie Analytics Capstone

Capstone project for Data Engineering interns (Weeks 8–12 of the
internship program). You'll build an end-to-end movie analytics
pipeline — SQL, Python/Pandas, PySpark, dbt, Airflow, and Power BI —
working with a messy, realistic movie dataset. You own this repository
end-to-end.

## Dataset

Download the dataset and unzip it into `data/raw/`:

```
curl -O https://cdn.stratpoint.io/data-training/project_data.zip
unzip project_data.zip -d data/raw/
```

The dataset ships with intentional data quality issues you're expected to
handle as part of the project:

| File | Contents | Known issues |
|---|---|---|
| `movies_main.csv` | Core movie records | Duplicate entries, mixed date formats, missing budget data |
| `ratings.json` | Rating summaries | Nested structures, multiple metrics per movie |
| `movie_extended.csv` | Extended metadata | Multiple genres per movie, production company info, country data |

`data/` is gitignored — do not commit the raw dataset to this repo.

## Structure

```
data/            Raw and processed datasets (gitignored)
notebooks/       Exploratory analysis notebooks
scripts/
  sql/           SQL schema design + advanced queries
  pandas/        OOP data model + Pandas cleaning/processing
  pyspark/       PySpark transforms, writes to Postgres/Parquet
dbt_project/     Staging -> intermediate -> marts dbt project
airflow/dags/    DAG orchestrating PySpark -> dbt run -> dbt test
powerbi/         Power BI dashboard deliverable (.pbix)
docs/            Evaluation rubric
```

Each folder has its own README with the specific tasks and stub files to
fill in.

## Pipeline

Data flows in this order: `scripts/pyspark/` cleans and lands the raw
files into Postgres/Parquet -> `dbt_project/` builds staging, intermediate,
and marts models on top -> `powerbi/` reads the marts layer -> `airflow/`
orchestrates the whole thing on a schedule. `scripts/sql/` is a standalone
schema-design and query exercise against the same dataset, not a step in
this pipeline.

## Technical Requirements

| Area | What to include |
|---|---|
| SQL | Normalized schema with keys/relationships. Advanced queries using LAG/LEAD and window functions. |
| Python + Pandas | Classes for data extraction and transformation. Modular, reusable functions. Proper error handling. |
| PySpark | Batch data processing. Schema enforcement. Write to PostgreSQL or Parquet. |
| dbt | Full three-layer project (staging, intermediate, marts). Tests and documentation. `source()` and `ref()` used correctly. |
| Airflow | DAG that orchestrates the full pipeline end to end. Scheduled. All tasks have retries. |
| Power BI | Star schema data model. 5+ DAX measures. Dashboard with clear data story and recommended actions. |

## Evaluation

See [docs/EVALUATION.md](docs/EVALUATION.md) for the full grading rubric.
Passing grade: 70%.

## Setup

```
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Airflow is not installed via `requirements.txt` — see
[airflow/README.md](airflow/README.md) for the Docker Compose setup.
