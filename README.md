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

## Business Angles

Your Power BI dashboard is scored on **data storytelling**, not just charts
(see the rubric). A story needs a stakeholder, a decision at stake, and a
recommendation — not just an insight. Structure: *who's asking → what
decision hangs on it → what the data reveals → what you'd tell them to do.*

Pick one of these, mix two, or invent your own — just make sure your
dashboard answers "so what should we do," not only "here's a chart."

**Investment & greenlighting**

1. *The studio CFO* is deciding next year's slate — we can only fund 8
   films: which genre/budget bets have paid off, and which should we walk
   away from?

2. *The head of acquisitions* found a low-budget film with a suspiciously
   high rating — is this a hidden gem we underfunded, or a fluke?

3. *The board* wants to know why last year's tentpole flopped — what do
   our failed high-budget bets have in common?

4. *A producer* is choosing a director for a new project — who's a safe
   bet vs. a high-variance gamble?

**Content strategy (streaming lens)**

5. *The content chief* has a fixed licensing budget — which titles give
   the most engagement per dollar?

6. *The catalog team* is trimming the library — which long-tail titles
   are dead weight vs. worth re-promoting?

7. *Product* is redesigning subscription tiers — how do we split the
   catalog into premium/standard/kids so each tier feels justified?

8. *Marketing* has a fixed spend — where are we over-hyping mediocre
   titles, and under-marketing great ones?

**Timing & market strategy**

9. *Release planning* is scheduling next year's calendar — what's the
   ideal release window per genre?

10. *Strategy* is planning a 5-year slate — which genres are rising,
    which are dying?

11. *International expansion* wants a new market — which countries/
    languages are underserved relative to what audiences already like?

12. *Business development* is picking a co-production partner — which
    studio partnerships actually outperform solo productions?

**Talent & franchise angles**

13. *Franchise strategy* is deciding whether to greenlight a sequel — do
    sequels historically outperform or cannibalize the original?

14. *The prestige/awards team* wants a campaign pick — what do our rare
    low-budget, high-acclaim outliers share, and can we find the next one?

15. *Portfolio risk* — the board is worried about overexposure — is our
    slate dangerously concentrated in one genre or budget tier?

**Risk & legacy**

16. *Underwriting* insures film productions against box-office failure —
    which budget/genre/studio profiles should raise the premium?

17. *Legacy/merchandising* — which older titles still have durable
    engagement and deserve an anniversary re-release or merchandise push?

18. *A festival programmer* is curating a retrospective on a fixed
    budget — which films give the best prestige-per-dollar?

**Meta / trust angle**

19. *The new head of data* has to convince leadership the numbers are
    trustworthy before anyone acts on them — here's what's broken in this
    dataset, here's what I fixed, here's what you can now safely decide
    on. (This is literally the story of what you did in Weeks 1–4.)

20. *You just became CEO.* Five minutes, one board meeting, one killer
    insight from this dataset — what is it, why does it matter, and what
    should the company do next?

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
