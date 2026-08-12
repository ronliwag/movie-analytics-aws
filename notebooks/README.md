# Notebooks

Exploratory analysis notebooks — use this folder for one-off exploration
(profiling the raw data, sketching a query before it goes into
`scripts/sql/`, checking a dbt model's output) that doesn't belong in the
pipeline code itself.

Not graded directly, but useful evidence of your process if you want to
reference it during the Week 12 presentation.

## Findings from `data_exploration.ipynb`

Profiling results for `movies_main.csv`, `ratings.json`, and
`movie_extended.csv`. This is the input to Task 5 (cleaning) and Task 6
(external validation) — treat it as a punch list, not just notes.

### `movies_main.csv` (45,486 rows)

- **3 corrupt rows** — `id` holds a date string (e.g. `1997-08-20`) instead
  of a movie id, and the rest of the row is shifted: `title`/`release_date`
  are empty and `budget` holds a TMDB poster path. Source-level corruption,
  not a parsing artifact — same 3 ids are corrupt in `movie_extended.csv`
  too. Drop or manually re-align in Task 5, don't null-fill.
- **Duplicates** — 6 exact-duplicate rows, 50 duplicate-`id` rows. Dedup key
  should be `title` + `release_date` (13 real pairs), not `title` alone
  (3,188 matches, but mostly legitimate shared titles across remakes/shorts).
  Duplicate rows don't always agree on every field (e.g. one copy of a title
  has `budget=NaN`, the other has a real value) — dedup logic needs a
  tiebreak rule (e.g. keep the row with more non-null fields), not a blind
  `drop_duplicates()`.
- **Date formats** — three formats in near-equal thirds: `YYYY-MM-DD`
  (15,194), `DD-MM-YYYY` (15,135), `MM/DD/YYYY` (15,067), plus 90 nulls.
  `DD-MM` and `MM-DD` are ambiguous for day/month ≤ 12, so a single
  `pd.to_datetime` auto-parse will silently mis-parse a chunk of rows —
  needs explicit per-format detection first.
- **Budget** — 9.8% (4,437) are true nulls, but **74.5% (33,887) are
  literal `0`**, clearly a missing-data placeholder rather than a real $0
  budget. **84.3% combined is unusable as-is** — the single biggest
  data-quality issue in the dataset, and it should drive the Task 5
  cleaning strategy (treat 0 as null; budget-dependent analysis needs to
  account for this).

### `ratings.json` (9,067 records)

- Flat list of one dict per movie (not per rating event):
  `{movie_id, ratings_summary: {avg_rating, total_ratings, std_dev}, last_rated}`.
  `last_rated` is a Unix timestamp. All 9,067 `movie_id`s are unique.
- **Join-key verified, not just assumed**: `movies_main.id` is a string,
  `ratings.json`'s `movie_id` is a native int — different types. Compared
  both with a type-normalized cast (not string coercion) and got the same
  result both ways: 0 orphaned ratings, no leading zeros/whitespace on
  either side. The coverage gap below is real, not a type-mismatch bug.
- **80% of the catalog (36,366 of 45,433 valid movies) has no ratings entry
  in this dataset.** Ratings only cover ~20% of the catalog (9,067 movies).
  Spot-checked 5 "missing" ids (e.g. *Four Rooms*, *Ariel*) — they're
  well-formed catalog rows, genuinely just absent from this file, not
  corrupted. Note the phrasing: this confirms absence *from this extract*,
  not that these movies have zero ratings anywhere — Task 6's external
  TMDB spot-check is what would confirm that distinction.
- **Design/pipeline consequence**: model movies↔ratings as an optional
  relationship in Task 3's schema (not a mandatory FK), and use a **left
  join** from movies to ratings in dbt — an inner join would silently
  shrink the catalog from ~45K to ~9K. Any ratings-driven KPI in Task 7
  (e.g. "top rated," "hidden gem") should carry an explicit caveat that
  it's only computable for the rated ~20% of the catalog.

### `movie_extended.csv` (45,466 rows)

- `genres` and `production_companies` — plain comma-separated strings, no
  semicolons found. Straightforward `str.split(",")` into a junction table.
- `production_countries` and `spoken_languages` — stringified **Python
  literals** (single-quoted keys), not valid JSON: `json.loads` fails on
  these, use `ast.literal_eval`. Each is a list of `{iso_code, name}`
  dicts, so each needs its own junction table.
- Nulls: `production_companies` 12,365 (27%), `genres` 2,442 (5%),
  `spoken_languages` 6. `production_countries` has no true nulls, but 6,290
  rows (14%) have an empty `[]` list — functionally missing, treat as such.
- Same 3 corrupt ids as `movies_main.csv` (see above), confirming the
  corruption happened at the source, not during a later join.

### Cross-file

- `movies_main.csv` and `movie_extended.csv` have **identical id
  coverage** — 45,436 unique ids in both, 0 ids missing from either side.
  The row-count difference between the two files (45,486 vs 45,466) is
  **not** missing/orphaned records — it's that `movies_main.csv` has 50
  duplicate-id rows vs. `movie_extended.csv`'s 30. Both files need
  deduping down to the same canonical id list; don't pick one file's raw
  row count as "the" count.
- `ratings.json`'s `movie_id` is always a subset of `movies_main.id` (see
  above for coverage caveat).

### Shortlist for Task 6 external validation

Movies with a high rating (≥4.2 avg, ≥50 ratings) but missing/zero budget —
worth spot-checking against an external source (TMDB/IMDB) to tell "hidden
gem we underfunded" from "bad data." 30 candidates total meet the
threshold; top 5:

| id | title | budget | avg rating | # ratings |
|---|---|---|---|---|
| 1554 | Down by Law | $0 | 4.49 | 311 |
| 123505 | A Modern Affair | $0 | 4.42 | 50 |
| 41275 | Python | $0 | 4.39 | 62 |
| 112912 | Why We Fight: The Battle of Russia | $0 | 4.39 | 135 |
| 175027 | Double Harness | $0 | 4.37 | 201 |
