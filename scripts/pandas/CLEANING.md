# Cleaning

Implements the rules from `notebooks/README.md`'s data quality findings
(Task 5 input). `clean_data.py` reads the three raw sources and writes
three CSVs mirroring them (`data/processed/movies_main_clean.csv`,
`movie_extended_clean.csv`, `ratings_clean.csv`) -- not merged into one
file, so `transform.py`'s `clean()` can load each straight into
`clean.movies_main` / `movie_extended` / `ratings` in Postgres. 

## Attribute format: raw → cleaned

### `movies_main`

| Attribute | Raw format | Cleaned format |
|---|---|---|
| `id` | INTEGER, some NULL (corrupt rows) | INTEGER, NOT NULL |
| `title` | TEXT, inconsistent leading/trailing whitespace | TEXT, trimmed |
| `release_date` | TEXT — 3 mixed formats (ISO / `MM/DD/YYYY` / `DD-MM-YYYY`) + NULLs | Parsed `datetime` |
| `budget` | DOUBLE — `0` used as a "not reported" placeholder | DOUBLE, `0 → NULL` |
| `revenue` | DOUBLE — `0` used as a "not reported" placeholder | DOUBLE, `0 → NULL` |

### `movie_extended`

| Attribute | Raw format | Cleaned format |
|---|---|---|
| `id` | INTEGER, some NULL (corrupt rows) | INTEGER, NOT NULL |
| `genres` | TEXT, comma-separated (e.g. `"Animation,Comedy,Family"`) | Comma-joined, trimmed |
| `production_companies` | TEXT, comma-separated | Comma-joined, trimmed |
| `production_countries` | TEXT, Python-repr list of dicts (not valid JSON): `[{'iso_3166_1': 'US', 'name': 'United States of America'}]` | Split into `production_country_codes` + `production_country_names` (both comma-joined), parsed via `ast.literal_eval` |
| `spoken_languages` | TEXT, same Python-repr shape (`iso_639_1` code) | Split into `spoken_language_codes` + `spoken_language_names`, same parsing |

### `ratings`

| Attribute | Raw format | Cleaned format |
|---|---|---|
| `movie_id` | INTEGER | Unchanged |
| `avg_rating` | DOUBLE | Unchanged — no anomalies found |
| `total_ratings` | INTEGER | Unchanged — no anomalies found |
| `std_dev` | DOUBLE — `NaN` when `total_ratings = 1` (undefined statistic) | DOUBLE, `NaN → NULL` |
| `last_rated` | Unix epoch seconds (int) in source JSON | `datetime` (converted in `load_ratings()`) |

## Cleaning decisions

### Corrupted rows
3 rows in `movies_main.csv` (and the same 3 ids in `movie_extended.csv`)
have shifted/garbage columns, not just missing values — e.g. a date string
sitting in the `id` column and a TMDB poster image path sitting in the
`budget` column. This is source-level corruption (confirmed identical
across both files), not a parsing artifact, and there's no id to recover.
**Decision: drop outright** (`main()` drops rows where `id` failed to
coerce to numeric, before anything else runs). `movie_extended`'s copies
of these same 3 rows are removed as a side effect of the cross-table
filter (`extended["id"].isin(movies["id"])`), since a dropped id can't
match anything.

### Duplicates
`movies_main` had 50 duplicate-`id` rows, `movie_extended` had 30 — but
most weren't real conflicts, just formatting noise (the same date written
two different ways, or a stray trailing space in a title). **Decision:
normalize first (trim strings, parse dates), then dedupe** — this collapses
rows that are now identical without needing a tiebreak rule
(`remove_duplicates()` compares full rows via a tuple-cast view, since
pandas can't directly compare columns containing lists). Any id still
duplicated after that is a genuine conflict — resolved by ranking each
id's rows by non-null/non-empty field count and keeping the most complete
one. Same two-step approach applies to `movie_extended`.

### Date formats
Three formats coexist with zero stray/unrecognized values: ISO
`YYYY-MM-DD` (15,194 rows), `MM/DD/YYYY` slash-delimited (15,067),
`DD-MM-YYYY` dash-delimited (15,135), plus 90 NULL. Per-row this looks
ambiguous (e.g. `07-09-1995` could be Jul 9 or Sep 7), but the delimiter
itself deterministically signals the convention — verified zero
slash-dates have a month component > 12, and zero dash-dates have a
*second* component > 12 (while 8,344 have a first component > 12, only
possible if day-first). **Decision: `standardize_date()`
(`scripts/pandas/data_processor.py`) tries each format in turn** via
`fix_dates()` — a single blind `pd.to_datetime` auto-parse would silently
mis-parse a chunk of rows; the 90 NULLs stay NULL (unrecoverable).

### Missing budget/revenue (`0` vs `NULL`)
`budget = 0` for 74.5% of rows, `revenue = 0` for 83.7% — implausible as
literal zero at that rate for a commercial film dataset, almost certainly
this source's "not reported" convention (distinct from the much smaller
true-NULL counts: 9.8% and ~0.01% respectively). **Decision: convert
`0 → NULL`** (`fix_missing_budget()`) so "unknown" has one consistent
representation. Filling these gaps is deferred to the external validation
step (Task 6), not attempted here.

### `NaN` std_dev
33.8% of `ratings` rows (3,063) have `std_dev = NaN`, always where
`total_ratings = 1` — standard deviation of a single value is
mathematically undefined. `NaN` behaves inconsistently in SQL (e.g. it
silently wins `MAX()`). **Decision: convert `NaN → NULL`** in
`load_ratings()`.

### ISO codes
`production_countries`/`spoken_languages` carry both an ISO code
(`iso_3166_1`/`iso_639_1`) and a display `name` per entry. An earlier pass
only kept `name` and discarded the code — but the eventual normalized
`countries`/`language` tables use the code as their primary key, so
dropping it would force a fragile name-based re-match later (e.g. is it
"United States of America" or "USA"?). **Decision: keep both, as parallel
columns** (`production_country_codes`/`production_country_names`,
`spoken_language_codes`/`spoken_language_names`), via `_parse_field()`.

### Comma vs semicolon for joined list columns
Cleaned list-valued columns (`genres`, `production_companies`, the
code/name columns above) are comma-joined for the CSV output, matching the
raw source's own convention for `genres`/`production_companies`. Verified
first that no individual value in this dataset contains a literal comma
(0 across genres, companies, country names, and language names) — so
joining this way doesn't create ambiguity when split back apart later.
Pandas quotes any comma-containing field automatically on `to_csv`, and
Spark's CSV reader (used by `transform.py`'s `clean()`) parses that
quoting correctly on the way back in.

## Data summary

| Table | Raw rows | Cleaned rows | What changed |
|---|---|---|---|
| `movies_main` | 45,486 | 45,433 | −3 corrupt rows, −50 duplicate rows collapsed to unique ids |
| `movie_extended` | 45,466 | 45,433 | −3 corrupt rows (via cross-table filter), −30 duplicate rows collapsed to unique ids |
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
