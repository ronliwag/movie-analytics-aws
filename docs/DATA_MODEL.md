# Data Model & Dashboard Plan — Global Scouting Map

Blueprint for the dbt marts layer (Phase 2) and the Power BI dashboard, drawn
up while only `data/processed/*.csv` (the cleaned output of
`scripts/pandas/clean_data.py`) exists — no dbt models built yet. See
[BUSINESS_ANGLE.md](BUSINESS_ANGLE.md) for the business angle this serves.

Grounded in the actual cleaned columns:

```
movies_main_clean.csv:   id, title, release_date, budget, revenue
movie_extended_clean.csv: id, genres, production_companies, original_title,
                           original_language, director, cast,
                           production_country_codes, production_country_names,
                           spoken_language_codes, spoken_language_names
ratings_clean.csv:       movie_id, last_rated, avg_rating, total_ratings, std_dev
```

## 1. Source → target mapping

Some cells in the cleaned CSVs pack multiple values into one comma-joined
string (`genres`, `production_companies`, `director`, `cast`, and the
country/language code+name pairs). The normalized ERD needs one row per
value, not one cell per movie — so those columns need to be split
("unpivoted") into bridge-table rows during the dbt staging/intermediate
layer. Columns that are already single-valued (`title`, `release_date`,
`budget`, `revenue`, `original_title`, `original_language`, ratings fields)
map straight across with no splitting.

| Cleaned source column | Target | Needs splitting? |
|---|---|---|
| `movies_main_clean.id/title/release_date/budget/revenue` | `movies` | No |
| `movie_extended_clean.original_title/original_language` | `movies.original_title`, `movies.original_language_code` (FK) | No |
| `movie_extended_clean.genres` | `genres` + `movie_genre` | Yes — comma list |
| `movie_extended_clean.production_companies` | `production_company` + `movie_company` | Yes — comma list |
| `movie_extended_clean.production_country_codes` + `_names` | `countries` + `movie_country` | Yes — two parallel comma lists, zipped position-by-position |
| `movie_extended_clean.spoken_language_codes` + `_names` | `language` + `movie_language` | Yes — same zip pattern |
| `movie_extended_clean.director` | `person` + `movie_director` | Yes (usually 1 value, same split logic) |
| `movie_extended_clean.cast` | `person` + `movie_cast` | Yes — comma list |
| `ratings_clean.*` | `ratings` | No — already 1 row per `movie_id` |

### Worked example — one real movie, id `461257` ("Queerama")

Raw cleaned rows:

```
movies_main_clean:    id=461257, title=Queerama, release_date=2017-06-09, budget=(blank), revenue=(blank)
movie_extended_clean: genres="Music,Documentary", production_companies="ie ie productions",
                      original_title=Queerama, original_language=en, director="Daisy Asquith",
                      cast="Leigh Bowery,Quentin Crisp", production_country_codes=GB,
                      production_country_names="United Kingdom", spoken_language_codes=en,
                      spoken_language_names=English
ratings_clean:        movie_id=461257, avg_rating=3.83, total_ratings=3, std_dev=1.04, last_rated=2021-12-11
```

Becomes, after mapping:

- `movies`: 1 row (`461257, Queerama, en, 2017-06-09`)
- `ratings`: 1 row (`461257, 3.83, 3, 1.04`)
- `movie_genre`: **2 rows** — `genres="Music,Documentary"` splits into `Music` and `Documentary`, each pointing at its own (deduped, catalog-wide) `genre_id`
- `movie_company`: 1 row — `ie ie productions`
- `movie_country`: 1 row — `production_country_codes="GB"` paired with `production_country_names="United Kingdom"` at the same list position
- `movie_language`: 1 row — `en` / `English`, same pairing logic
- `movie_director`: 1 row — `Daisy Asquith`
- `movie_cast`: **2 rows** — `Leigh Bowery` and `Quentin Crisp`

One movie's 3 wide source rows explode into 1 + 1 + 2 + 1 + 1 + 1 + 1 + 2 = 10
normalized rows. Multiply across all ~45,000 movies — that's the entire job
of the dbt staging/intermediate layer: split each comma-packed cell and
write one row per value, reusing the same `genre_id`/`person_id`/etc.
whenever the same name recurs on a different movie.

## 2. Target schema

**Fact** — grain: one row per `movie_id`

```
fct_movie_performance
  movie_id PK, title, original_title, original_language_code FK,
  release_date, budget, revenue, profit (computed),
  avg_rating, total_ratings, std_dev, last_rated,
  reach_country_count (computed), reach_language_count (computed)
```

`profit` and the two `reach_*_count` columns are business logic, so they
belong in `int_movies_joined.sql` (per that model's own header comment:
"business logic... belongs here, not in staging or in the mart") —
`fct_movie_performance.sql` should stay a plain final `select *`.

**Dimensions**

```
language            (iso_639_1_code PK, name)   -- one table, reused for both roles (see §4)
countries            (iso_3166_1_code PK, name)
genres               (genre_id PK, name)
production_company   (production_company_id PK, name)
person               (person_id PK, name)
```

**Bridges** — grain: one row per movie × entity

```
movie_language   (movie_id PFK, iso_639_1_code PFK)   -- reach signal
movie_country    (movie_id PFK, iso_3166_1_code PFK)  -- reach signal, secondary origin view
movie_genre      (movie_id PFK, genre_id PFK)
movie_company    (movie_id PFK, production_company_id PFK)
movie_director   (movie_id PFK, person_id PFK)
movie_cast       (movie_id PFK, person_id PFK)
```

`language` stays **one** table at the dbt/SQL level. The role-playing split
(original vs. spoken) only happens later, at Power BI import (§4).

**Optional second mart** worth considering once Phase 2 starts, since the
dbt rubric line rewards real modeling logic over passthroughs:
`mart_market_scouting`, grain = one row per `original_language_code`,
pre-aggregating weighted avg rating, total ratings volume, avg reach, and
quality/reach percentiles in SQL. Not required to build the dashboard —
`fct_movie_performance` alone is enough — but a stronger dbt submission if
time allows.

## 3. Known limitations to carry into the write-up

- **`person` is name-based, not TMDB-id-based** — no person id survived
  cleaning, so two different real people sharing a name would incorrectly
  collapse into one `person` row. A known gap, not something to fix in
  Phase 2 unless re-enriching with TMDB person ids.
- **Financial coverage is ~19.6%** (8,900 of 45,433 movies have both budget
  and revenue) and skews toward mainstream titles — shown only as secondary,
  opportunistic context in the dashboard, never as a ranking requirement.
- **`production_country` is genuinely multi-valued** (co-productions) —
  used as a secondary origin view, not the primary market grain.
- **Country/language code↔name pairing relies on a positional zip**
  (`unnest(codes_arr, names_arr)`) that assumes the Nth code corresponds to
  the Nth name. Some rows have mismatched list lengths — a TMDB data gap (a
  code with no listed name), not a parsing bug — and a spot check found the
  unnamed code always trailing at the end of the list, which the zip
  resolves correctly (pads with `NULL`).
- **FIXED — 49 movies had a CSV column-shift bug**, traced to
  `movie_id 154399` (`production_companies` = `PRF "Zespoły Filmowe",
  Zespół Filmowy "Syrena"`, Polish studio names with an embedded literal
  quote). The CSVs themselves were fine (Python's `csv` module parses them
  correctly) — the bug was in `scripts/pyspark/transform.py`'s
  `spark.read.csv(...)` calls, which used Spark's default backslash
  escape instead of the RFC4180 doubled-quote escaping pandas' `to_csv()`
  writes, so any field with an embedded quote shifted every column after
  it left by one for that row (`director` would hold a language code,
  `cast` would hold the real director's name, etc.). Confirmed directly
  with a standalone PySpark read: without `.option("escape", "\"")` the
  corruption reproduces exactly; with it, every field lands correctly.
  Fixed in `transform.py` (all four `spark.read.csv` calls) and the
  pipeline re-run — `clean.movie_extended` is now correct for all 49
  movies, including `movie_director`/`movie_cast`, which couldn't be
  algorithmically cleaned at the dbt layer (a shifted-in value there is
  still a plausible person name, no format check catches it) and needed
  this root-cause fix. The `~ '^[A-Za-z]{2}$'`/`~ '^[a-z]{2}$'` guards in
  `int_movie_countries`/`int_movie_languages`/`dim_language` are kept as a
  defensive check, but no longer filter out anything.
- **`dim_country` picks its display name with `mode() within group (...)`,
  not `min()`** — deliberately: with `min()`, a single noisy/mismatched row
  (see above) can beat the overwhelmingly common correct name purely by
  string sort order (e.g. `ar` briefly resolved to `Français` instead of
  `العربية` because a French name happened to sort first, even though 361
  movies correctly paired `ar` with `العربية` and only 1 didn't). `mode()`
  picks whichever name most movies actually agree on. Very rare codes (a
  handful of total occurrences catalog-wide) can still resolve to an
  arbitrary tied name when the underlying data is itself too
  thin/noisy to have a real majority — an inherent data limitation, not an
  aggregation bug.
- **`dim_language` no longer derives its display name from TMDB's
  spoken_language_names at all** — it looks up the ISO 639-1 standard
  English name from the `iso_639_1` seed instead (`cn`/`xx` are named
  explicitly, since they're TMDB conventions, not real ISO 639-1 codes).
  19 of the 140 codes in this catalog have no native-language name
  anywhere in the pipeline: TMDB's own raw export leaves `name` blank for
  them even at the source (e.g. `to`: `[{'iso_639_1': 'to', 'name': ''}]`
  in `data/raw/movie_extended.csv`), so `mode()`-style voting over the
  per-movie pairings could never have recovered a value for those rows —
  there was nothing to vote on. Sourcing every code's name from one
  external reference keeps the column consistent rather than mixing
  TMDB's native-script names with an English fallback for just the gaps.
- **Comma-joined multi-valued columns can't distinguish an embedded comma
  in a single name from a delimiter between two names** (e.g. a
  production company literally named "X, Y & Z Productions" would
  incorrectly split into two rows). Inherited from Phase 1's cleaning
  encoding — not fixable at the dbt layer without re-fetching structured
  data from TMDB.

## 4. Measures

| Measure | Grain / source | Notes |
|---|---|---|
| Weighted Avg Rating | `fct_movie_performance`, grouped by `original_language_code` | `SUMX(Movies, avg_rating * total_ratings) / SUM(total_ratings)` |
| Total Ratings Volume | same | `SUM(total_ratings)` — confidence filter |
| Avg Rating Consistency | same | `AVERAGE(std_dev)` — risk filter, lower = more consistent |
| Reach Index | `reach_country_count` + `reach_language_count`, avg per market | Or live `COUNTROWS` on the bridges if not pre-computed |
| Quality Percentile | ranked across `original_language` | See §6 — use `ALLSELECTED`, not `ALL` |
| Reach Percentile | ranked across `original_language` | Same |
| **Distribution Gap Score** | `Quality Percentile − Reach Percentile` | The core scouting-priority output |
| Title Reach Count | `fct_movie_performance`, movie grain | `COUNTROWS(RELATEDTABLE(movie_country)) + COUNTROWS(RELATEDTABLE(movie_language))` |
| Confidence Flag | movie grain | Flags titles below the ratings-volume threshold as "Low sample" |
| Shortlist Rank | movie grain, within a selected market | `RANKX` filtered to the selected `original_language` |
| Financial Coverage % | shortlist subset | `DIVIDE(COUNTROWS(FILTER(Shortlist, NOT ISBLANK(budget))), COUNTROWS(Shortlist))` |
| Profit | movie grain | `IF(budget and revenue both present, revenue - budget, BLANK())` — never imputed |
| Financial Contradiction Flag | shortlist subset | Flags a shortlisted title with disclosed `Profit < 0` |

## 5. Power BI model notes

**Role-playing dimension (`language`)** — it's related to `movies` two
different ways: directly via `original_language_code` (single-valued,
"market" axis) and indirectly via the `movie_language` bridge
(multi-valued, "reach" signal). Power BI only allows one active relationship
between two tables, so import `language` **twice**: once as
`dim_original_language` (active relationship to `movies`), once as
`dim_spoken_language` (relationship to the `movie_language` bridge). Keeps
the underlying normalized ERD untouched — the duplication is Power
BI-side only.

**Many-to-many bridges** (`movie_genre`, `movie_country`,
`movie_language`↔`dim_spoken_language`, `movie_cast`, `movie_director`) —
set cross-filter direction to **Both** on these relationships, or slicers
on genre/country/language/person won't propagate to the fact table. Not
needed on `movies` ↔ `dim_original_language`, which is a normal
single-direction 1-to-many.

## 6. Slicers/filters

| Page | Slicer | Filters via |
|---|---|---|
| Page 1 (Market Map) | Min. Total Ratings threshold (confidence) | disconnected parameter table |
| Page 1 | Release-year range | `movies.release_date` |
| Page 1 | Genre | `movie_genre` bridge |
| Page 2 (Shortlist) | Market/language | carried from Page 1, or standalone `dim_original_language` slicer |
| Page 2 | Confidence flag (Reliable / Low sample) | `Confidence Flag` measure |
| Page 2 | Reach count range | `Title Reach Count` measure |
| Page 3 (Financial) | (inherits Page 1/2 selections) | — |

**Confidence threshold as a live slicer**, not a hardcoded number — add a
disconnected parameter table (`MinRatingsThreshold`, e.g. 0–5000 step 100):

```dax
Selected Threshold = SELECTEDVALUE('MinRatingsThreshold'[Value], 500)

Qualifies for Ranking =
IF([Total Ratings Volume] >= [Selected Threshold], 1, 0)
```

**Percentile/rank measures must use `ALLSELECTED`, not `ALL`** — `ALL` would
give a fixed global ranking no slicer can move; `ALLSELECTED` recalculates
the ranking within whatever the exec has currently sliced to (e.g. "just
2015–2024 releases," or "just Documentary genre"), while still ignoring the
visual's own row-level filters. Given this dashboard supports a live
planning conversation, `ALLSELECTED` is the intended default:

```dax
Quality Percentile =
VAR CurrentMarkets =
    FILTER(ALLSELECTED(dim_original_language), [Qualifies for Ranking] = 1)
VAR Rank = RANKX(CurrentMarkets, [Weighted Avg Rating])
VAR TotalCount = COUNTROWS(CurrentMarkets)
RETURN DIVIDE(Rank, TotalCount)
```

Same swap applies to `Reach Percentile`, and therefore to
`Distribution Gap Score`, which is built from the two.

## 7. Dashboard storyboard

Narrative spine: *"We're scouting on gut feel → here's where audience-validated
quality is outpacing distribution reach → here are the actual titles to call
about → here's the financial gut-check before anyone signs."*

### Page 0 — Executive Summary
- **Audience:** Head of Global Content Acquisition, first 15 seconds.
- **Shows:** catalog-wide framing (95% ratings coverage, 19.6% financial
  coverage) + a single headline finding: "Top 5 underexposed markets" as a
  callout, not a chart.
- **Recommended-action callout:** *"These 5 origin-language markets combine
  top-quartile audience quality with bottom-quartile international
  footprint — prioritize scouting trips here next cycle."*

### Page 1 — Market Scouting Map (Use Case 1)
- **Shows:** every `original_language` market plotted as quality vs. reach —
  this is the dashboard's thesis.
- **Visuals:** scatter (X = Reach Index, Y = Weighted Avg Rating, bubble
  size = Total Ratings Volume, color = Gap tier); ranked table/bar by
  Distribution Gap Score, filtered by the confidence threshold slicer.
- **Recommended-action callout:** *"[Language X]: rated Nth percentile on
  quality, only Mth percentile on reach — N titles qualify for a closer
  look."*

### Page 2 — Title-Level Shortlist (Use Case 2)
- **Audience:** Acquisitions/licensing negotiators — the working page.
- **Shows:** drills from a market selected on Page 1 down to titles passing
  a quality + confidence + low-reach filter simultaneously.
- **Visuals:** sortable table (title, language, avg_rating, total_ratings,
  std_dev, reach count, director, top cast); conditional formatting flags
  low-confidence titles.
- **Recommended-action callout:** *"12 titles from this market clear the
  quality-and-confidence bar with reach in the bottom 3 countries —
  shortlist for licensing outreach this quarter."*

### Page 3 — Financial Sanity Check (Use Case 3)
- **Audience:** Finance / greenlight committee.
- **Shows:** only the disclosed-financials subset of the shortlist, framed
  explicitly as supporting, not qualifying, evidence.
- **Visuals:** coverage banner ("X of Y shortlisted titles have disclosed
  financials"); budget-vs-revenue scatter for the disclosed subset only;
  contradiction callout if any shortlisted title shows a disclosed loss.
- **Recommended-action callout:** *"No financial red flags among disclosed
  titles — proceed on the ratings-driven shortlist."* (or a named
  exception, if one exists)
