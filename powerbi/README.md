# Power BI Dashboard

Deliverable is a `.pbix` file, not code — add it to this folder when you
submit.

## Tasks

### Data Preparation
- Import the marts-layer output from `dbt_project/models/marts/` (not the
  raw or staging tables)
- Transform data in Power Query as needed
- Create a star/snowflake data model (movies ↔ ratings ↔ genres ↔
  production companies ↔ countries)
- Implement a proper data refresh setup

### Report Development
- Build a movie performance dashboard
- Implement intermediate DAX measures (time intelligence, variables)
- Design dashboards with clear insights and a recommended action, not just
  charts — data storytelling is scored, not just visuals
- Add interactive filters/slicers

## Suggested visuals
- Revenue and rating trends over time
- Top movies/genres/directors by revenue and rating
- Budget vs. revenue scatter, with profitability highlighted
- Country/production-company breakdown

## Submission
Place your final `.pbix` file in this folder as `movie_analytics_dashboard.pbix`
and include a short write-up of your data model and key measures in
`DATA_MODEL.md`.

## Grading focus (Power BI — 25% of the rubric)
- Data model design (5%)
- Calculations and measures (10%)
- Data storytelling (10%)

See [docs/EVALUATION.md](../docs/EVALUATION.md) for the full rubric.
