# SQL Implementation

## Tasks

### 1. Database Design & Implementation
Expand `schema.sql` beyond the starter `movies` table to cover the full
dataset: movies, ratings, genres, production companies, countries — with
appropriate primary/foreign keys and relationships.

### 2. Advanced Queries
Fill in the stub files under `queries/`:

- `01_lag_lead_revenue.sql` — use `LAG`/`LEAD` to analyze monthly revenue
  changes, sequential movie performance, and year-over-year comparisons.
- `02_row_number_rankings.sql` — use `ROW_NUMBER` for movie rankings by
  genre, top performers by year, and director success rates.
- `03_aggregations_joins.sql` — complex aggregations and joins across the
  schema.

## Grading focus (SQL — 25% of the rubric)
- Database schema design (5%)
- Table relationships (5%)
- Advanced SQL — LAG/LEAD, window functions (10%)
- Query optimization (5%)

See [docs/EVALUATION.md](../../docs/EVALUATION.md) for the full rubric.
