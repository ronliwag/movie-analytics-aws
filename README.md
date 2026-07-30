# Movie Analytics Capstone

4-week capstone project for Data Engineering interns. You'll build a movie
analytics pipeline that progresses through SQL, Python/Pandas, PySpark, and
Power BI, working with a messy, realistic movie dataset.

## Duration

4 weeks

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
week1_sql/            SQL schema design + advanced queries
week2_python_pandas/  OOP data model + Pandas cleaning/processing
week3_pyspark/         PySpark transforms and analysis
week4_powerbi/         Power BI dashboard deliverable
docs/                  Evaluation rubric
```

Each week's folder has its own README with the specific tasks and stub files
to fill in.

## Weekly Breakdown

### Week 1 — SQL Implementation
Design the schema, load the dataset, and write advanced queries using
LAG/LEAD and ROW_NUMBER, plus complex aggregations and joins.

### Week 2 — Python & Pandas Processing
Build `Movie`/`Rating` classes, process the raw files with dictionaries,
loops, lambdas, and datetime/casting utilities, then clean and analyze the
data with Pandas.

### Week 3 — PySpark Data Processing
Reproduce and extend the analysis at scale with PySpark DataFrames, Spark
SQL functions, and analytical views/summaries.

### Week 4 — Power BI Dashboard
Build an interactive movie performance dashboard on top of the cleaned
dataset, with a proper data model, time intelligence, and filters.

## Evaluation

See [docs/EVALUATION.md](docs/EVALUATION.md) for the full grading rubric.
Passing grade: 70%.

## Setup

```
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```
