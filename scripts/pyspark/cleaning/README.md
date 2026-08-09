# Cleaning

Implements the rules from `notebooks/README.md`'s data quality findings
(Task 5 input). Each raw source has its own module — `movies.py`,
`extended.py`, `ratings.py` — and `transform.py`'s `clean()` just
orchestrates them plus the one cross-table rule. This step reads
`raw.movies_main` / `raw.movie_extended` / `raw.ratings` (as loaded by
`transform.py`) and produces cleaned, correctly-typed DataFrames — it does
**not** build the normalized `genres`/`production_company`/`countries`
dimension tables yet. That's a later, separate schema-normalization step.


## Attribute format: raw → cleaned

### `movies_main`

| Attribute | Raw format | Cleaned format |
|---|---|---|
| `id` | INTEGER, some NULL (corrupt rows) | INTEGER, NOT NULL |
| `title` | TEXT, inconsistent leading/trailing whitespace | TEXT, trimmed |
| `release_date` | TEXT — 3 mixed formats (ISO / `MM/DD/YYYY` / `DD-MM-YYYY`) + NULLs | `DATE` |
| `budget` | DOUBLE — `0` used as a "not reported" placeholder | DOUBLE, `0 → NULL` |
| `revenue` | DOUBLE — `0` used as a "not reported" placeholder | DOUBLE, `0 → NULL` |

### `movie_extended`

| Attribute | Raw format | Cleaned format |
|---|---|---|
| `id` | INTEGER, some NULL (corrupt rows) | INTEGER, NOT NULL |
| `genres` | TEXT, comma-separated (e.g. `"Animation,Comedy,Family"`) | `ARRAY<STRING>`, trimmed |
| `production_companies` | TEXT, comma-separated | `ARRAY<STRING>`, trimmed |
| `production_countries` | TEXT, Python-repr list of dicts (not valid JSON): `[{'iso_3166_1': 'US', 'name': 'United States of America'}]` | `ARRAY<STRING>` of country names, parsed via `ast.literal_eval` |
| `spoken_languages` | TEXT, same Python-repr shape (`iso_639_1` code) | `ARRAY<STRING>` of language names, same parsing |

### `ratings`

| Attribute | Raw format | Cleaned format |
|---|---|---|
| `movie_id` | INTEGER | Unchanged |
| `avg_rating` | DOUBLE | Unchanged — no anomalies found |
| `total_ratings` | INTEGER | Unchanged — no anomalies found |
| `std_dev` | DOUBLE — `NaN` when `total_ratings = 1` (undefined statistic) | DOUBLE, `NaN → NULL` |
| `last_rated` | Unix epoch seconds (int) in source JSON | `TIMESTAMP` *(already converted during ingestion in `load_ratings()`, not in `clean()`)* |

## Cleaning decisions

### Corrupted rows
3 rows in `movies_main.csv` (and the same 3 ids in `movie_extended.csv`)
have shifted/garbage columns, not just missing values — e.g. a date string
sitting in the `id` column and a TMDB poster image path sitting in the
`budget` column. This is source-level corruption (confirmed identical
across both files), not a parsing artifact, and there's no id to recover.
**Decision: drop outright** (`clean_movies()` filters `id IS NOT NULL`
before anything else runs). `movie_extended`'s copies of these same 3 rows
are removed as a side effect of the cross-table inner join in `clean()`,
since a NULL id can't join to anything.

### Duplicates
`movies_main` had 50 duplicate-`id` rows, `movie_extended` had 30 — but
most weren't real conflicts, just formatting noise (the same date written
two different ways, or a stray trailing space in a title). **Decision:
normalize first (trim strings, parse dates), then `dropDuplicates()`** —
this collapses rows that are now byte-identical without needing a
tiebreak rule. Verified on `movies_main`: 47 of 50 duplicate ids collapsed
this way alone. The remaining 3 (`4912`, `15028`, `77221`) were genuine
conflicts — identical title/date/revenue but one copy had a real budget
and the other had `0` (now `NULL`). For those, **a completeness tiebreak**
(rank each id's rows by non-null field count via `ROW_NUMBER`, keep the
top one) picks the more informative row. Same two-step approach applies to
`movie_extended`.

### Date formats
Three formats coexist with zero stray/unrecognized values: ISO
`YYYY-MM-DD` (15,194 rows), `MM/DD/YYYY` slash-delimited (15,067),
`DD-MM-YYYY` dash-delimited (15,135), plus 90 NULL. Per-row this looks
ambiguous (e.g. `07-09-1995` could be Jul 9 or Sep 7), but the **delimiter
itself deterministically signals the convention** — verified zero
slash-dates have a month component > 12, and zero dash-dates have a
*second* component > 12 (while 8,344 have a first component > 12, only
possible if day-first). **Decision: parse via a 3-way regex match into a
real `DATE` type** — no residual format inconsistency once it's no longer
stored as text; the 90 NULLs stay NULL (unrecoverable).

### Missing budget/revenue (`0` vs `NULL`)
`budget = 0` for 74.5% of rows, `revenue = 0` for 83.7% — implausible as
literal zero at that rate for a commercial film dataset, almost certainly
this source's "not reported" convention (distinct from the much smaller
true-NULL counts: 9.8% and ~0.01% respectively). **Decision: convert
`0 → NULL`** so "unknown" has one consistent representation. Filling these
gaps is deferred to the external validation step (Task 6), not attempted
here.

### `NaN` std_dev
33.8% of `ratings` rows (3,063) have `std_dev = NaN`, always where
`total_ratings = 1` — standard deviation of a single value is
mathematically undefined. `NaN` behaves inconsistently in SQL (e.g. it
silently wins `MAX()`). **Decision: convert `NaN → NULL`.**

## Data summary

| Table | Raw rows | Cleaned rows | What changed |
|---|---|---|---|
| `movies_main` | 45,486 | 45,433 | −3 corrupt rows, −50 duplicate rows collapsed to unique ids |
| `movie_extended` | 45,466 | 45,433 | −3 corrupt rows (via cross-table join), −30 duplicate rows collapsed to unique ids |
| `ratings` | 9,067 | 9,067 | No rows dropped — only `std_dev` values fixed |

Post-cleaning integrity, verified directly against the data:
- 0 NULL ids, 0 duplicate ids in either `movies_main` or `movie_extended`.
- `movies_main` and `movie_extended` have **identical id coverage** —
  45,433 distinct ids in both, 0 real cross-file orphans.
- 0 duplicate `movie_id`s in `ratings`; ratings still cover ~19.9% of the
  catalog (9,067 / 45,433) — expected sparsity, not a defect, no action
  taken.
- 0 remaining `budget = 0` / `revenue = 0` rows, 0 remaining `NaN` in
  `std_dev`.
