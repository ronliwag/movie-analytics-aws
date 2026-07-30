# Week 4 — Power BI Dashboard

Following the Power BI training modules. This week's deliverable is a
`.pbix` file, not code — add it to `week4_powerbi/` when you submit
(gitignored by default in most templates; make sure to explicitly commit
your `.pbix`).

## Tasks

### Data Preparation
- Import the cleaned dataset from Week 2/3 (`data/processed/`)
- Transform data in Power Query as needed
- Create data model relationships (movies ↔ ratings ↔ genres ↔ production
  companies ↔ countries)
- Implement a proper data refresh setup

### Report Development
- Build a movie performance dashboard
- Implement DAX aggregation measures
- Add time intelligence functions (YoY, rolling averages, etc.)
- Design interactive filters/slicers

## Suggested visuals
- Revenue and rating trends over time
- Top movies/genres/directors by revenue and rating
- Budget vs. revenue scatter, with profitability highlighted
- Country/production-company breakdown

## Submission
Place your final `.pbix` file in this folder as `movie_analytics_dashboard.pbix`
and include a short write-up of your data model and key measures in
`DATA_MODEL.md`.

## Grading focus
- Data model design (5%)
- Calculations and measures (10%)
- Visualization design (5%)
- Dashboard interactivity (5%)
