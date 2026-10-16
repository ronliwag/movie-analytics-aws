# Data Model & Dashboard Plan — Global Scouting Map

Sections 1–3 describe the dbt marts layer (Phase 2) **as built** — table
names, grains, and known limitations all reflect what's actually in
`dbt_project/models/`, not the original plan. Originally drawn up while
only `data/processed/*.csv` existed and no dbt models were built yet; kept
updated since as the source of narrative/rationale ("why this shape"), not
of column-by-column truth -- for the authoritative, always-current column
list and lineage graph, run `dbt docs generate && dbt docs serve` from
`dbt_project/` instead of trusting this doc's tables to have kept up with
every schema.yml change.

Sections 4–7 are still a **plan**, not as-built — Phase 3 (Power BI) hasn't
started (`powerbi/` has no `.pbix` yet). This is the Phase 3 handoff: the
schema those sections plan against is now final, so the measures/model
notes/storyboard below can be built directly, not re-derived.

See [BUSINESS_ANGLE.md](BUSINESS_ANGLE.md) for the business angle this serves.

Grounded in the actual cleaned columns:

```
movies_main_clean.csv:   id, title, release_date, budget, revenue
movie_extended_clean.csv: id, genres, production_companies, original_title,
                           original_language, director, cast,
                           production_country_codes, production_country_names,
                           spoken_language_codes, spoken_language_names
ratings_clean.csv:       movie_id, last_rated, avg_rating, total_ratings, std_dev
```

`movies_main_clean.budget`/`.revenue` are listed above because they're
still physically present in the cleaned source CSV -- Phase 1 cleaning
didn't change. They're just no longer mapped into the target schema (see
§1) -- dropped from the business angle entirely (see
[BUSINESS_ANGLE.md](BUSINESS_ANGLE.md)) because only ~19.6% of the catalog
discloses both, skewed toward mainstream titles, working against this
project's "hidden markets" thesis rather than supporting it.

## 1. Source → target mapping

Some cells in the cleaned CSVs pack multiple values into one comma-joined
string (`genres`, `production_companies`, `director`, `cast`, and the
country/language code+name pairs). The normalized ERD needs one row per
value, not one cell per movie — so those columns need to be split
("unpivoted") into bridge-table rows during the dbt staging/intermediate
layer. Columns that are already single-valued (`title`, `release_date`,
`budget`, `revenue`, `original_title`, `original_language`, ratings fields)
map straight across with no splitting.

| Cleaned source column | Target (as built) | Needs splitting? |
|---|---|---|
| `movies_main_clean.id/title/release_date` | `fct_movie_performance` (via `stg_movies` → `int_movies_joined`) | No |
| `movies_main_clean.budget/revenue` | **Not mapped** -- dropped from the business angle (see note above) | No |
| `movie_extended_clean.original_title/original_language` | `fct_movie_performance.original_title`, `.original_language_code` (FK to `dim_language`) | No |
| `movie_extended_clean.genres` | `dim_genre` + `movie_genre` (via `int_movie_genres`) | Yes — comma list |
| `movie_extended_clean.production_companies` | `dim_production_company` + `movie_company` (via `int_movie_companies`) | Yes — comma list |
| `movie_extended_clean.production_country_codes` + `_names` | `dim_country` + `movie_country` (via `int_movie_countries`) | Yes — two parallel comma lists, zipped position-by-position |
| `movie_extended_clean.spoken_language_codes` + `_names` | `dim_language` + `movie_language` (via `int_movie_languages`) | Yes — same zip pattern; `dim_language.name` also draws on the `iso_639_1` seed, not just this column (see §3) |
| `movie_extended_clean.director` | `dim_person` (via `int_movie_directors` → `int_person_filmography`) + `movie_director` (via `int_movie_directors`) | Yes (usually 1 value, same split logic) |
| `movie_extended_clean.cast` | `dim_person` (via `int_movie_cast` → `int_person_filmography`) + `movie_cast` (via `int_movie_cast`, `WITH ORDINALITY` also captures `billing_order`) | Yes — comma list |
| `ratings_clean.*` | `fct_movie_performance` (via `stg_ratings` → `int_movies_joined`) | No — already 1 row per `movie_id` |

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

- `fct_movie_performance`: 1 row (`461257, Queerama, en, 2017-06-09, ...`)
- `movie_genre`: **2 rows** — `genres="Music,Documentary"` splits into `Music` and `Documentary`, each pointing at its own (deduped, catalog-wide) `genre_id` in `dim_genre`
- `movie_company`: 1 row — `ie ie productions`, pointing at `dim_production_company`
- `movie_country`: 1 row — `production_country_codes="GB"` paired with `production_country_names="United Kingdom"` at the same list position, pointing at `dim_country`
- `movie_language`: 1 row — `en` / `English`, same pairing logic, pointing at `dim_language` (whose display name for `en` actually comes from the `iso_639_1` seed, not this row's `English` — see §3)
- `movie_director`: 1 row — `Daisy Asquith`, pointing at `dim_person`
- `movie_cast`: **2 rows** — `Leigh Bowery` and `Quentin Crisp`, both pointing at `dim_person`, each carrying its `billing_order` (1 and 2 — position in the comma list)

One movie's 3 wide source rows explode into 1 fact row + 2 + 1 + 1 + 1 + 1 + 2
= 8 bridge/dimension-linking rows. Multiply across all ~45,000 movies —
that's the entire job of the dbt staging/intermediate layer: split each
comma-packed cell and write one row per value, reusing the same
`genre_id`/`person_id`/etc. whenever the same name recurs on a different
movie.

## 2. Target schema (as built)

**Fact** — `fct_movie_performance`, grain: one row per `movie_id`

```
fct_movie_performance
  movie_id PK, title, original_title, original_language_code FK,
  release_date,
  avg_rating, total_ratings, std_dev, last_rated,
  reach_country_count (computed), reach_language_count (computed)
```

The two `reach_*_count` columns are business logic, computed in
`int_movies_joined.sql` (per that model's own header comment: "business
logic... belongs here, not in staging or in the mart") —
`fct_movie_performance.sql` is a plain final `select *` on top of it.
`budget`/`revenue`/`profit` used to live here too -- dropped along with
the financial-sanity-check use case (see
[BUSINESS_ANGLE.md](BUSINESS_ANGLE.md)).

**Dimensions**

```
dim_language            (iso_639_1_code PK, name)   -- one table, reused for both roles (see §4)
dim_country             (iso_3166_1_code PK, name)
dim_genre               (genre_id PK, name)
dim_production_company  (production_company_id PK, name)
dim_person              (person_id PK, name,
                          filmography_count, earliest_release_date,
                          latest_release_date, career_span_years,
                          possible_name_collision (computed))
```

`dim_person`'s talent-layer columns are computed in
`int_person_filmography.sql` the same way `int_movies_joined.sql` computes
`fct_movie_performance`'s reach counts -- `dim_person.sql` is a plain
final `select *` on top of it. `possible_name_collision` flags
`career_span_years > 60` as a heuristic identity-risk mitigation for the
name-based `person_id` below (§3).

`dim_genre`/`dim_production_company`/`dim_person` key off a surrogate
`{{ dbt_utils.generate_surrogate_key(...) }}` hash of the normalized
(lower/trimmed) name — the bridges below compute the same hash
independently, so no join back to the dimension is needed to resolve the
FK at insert time. `dim_country`/`dim_language` key off their natural ISO
code instead (no surrogate key needed).

`dim_language.name` does **not** come from `movie_extended`'s
`spoken_language_names` (TMDB's own per-movie pairing) — it's looked up
from a new **seed**, `iso_639_1` (`code`, `name`; ISO 639-1 code → English
name), not present in the original plan. Added because TMDB's own raw
export leaves the name blank for ~19 codes even at the source — see §3.

**Bridges** — grain: one row per movie × entity

```
movie_language   (movie_id PFK, iso_639_1_code PFK)   -- reach signal
movie_country    (movie_id PFK, iso_3166_1_code PFK)  -- reach signal, secondary origin view
movie_genre      (movie_id PFK, genre_id PFK)
movie_company    (movie_id PFK, production_company_id PFK)
movie_director   (movie_id PFK, person_id PFK)
movie_cast       (movie_id PFK, person_id PFK, billing_order)
```

`movie_cast.billing_order` is TMDB's own cast `order` field, proxied via
position in `int_movie_cast`'s comma-split (see §3) -- lower is more
prominent, used to weight lead-billed cast over background credits in the
talent-layer measures (§4).

`dim_language` stays **one** table at the dbt/SQL level. The role-playing
split (original vs. spoken) only happens later, at Power BI import (§4).

**Not built**: `mart_market_scouting` (grain = one row per
`original_language_code`, pre-aggregating weighted avg rating, total
ratings volume, avg reach, and quality/reach percentiles in SQL) was
floated as an optional second mart if time allowed. Phase 2 wrapped
without it — `fct_movie_performance` alone was enough for the dashboard, and
every consumer of "as-built" (dbt docs, this doc, the tests) reflects only
what's actually in `dbt_project/models/`. Still worth reconsidering for
Phase 3 if a pre-aggregated market-grain table would simplify the DAX in
§4-§6.

## 3. Known limitations to carry into the write-up

- **`dim_person` is name-based, not TMDB-id-based** — no person id survived
  cleaning, so two different real people sharing a name would incorrectly
  collapse into one `dim_person` row. A known gap, not something to fix in
  Phase 2 unless re-enriching with TMDB person ids.
  `dim_person.possible_name_collision` (flags a 60+ year credited career
  span, computed in `int_person_filmography.sql`) is a heuristic mitigation
  surfaced on the talent shortlist, not a fix — verified against real data
  to catch this failure mode (e.g. "Georges Méliès," whose linked films
  span 1896–2011, almost certainly the 1900s film pioneer merged with a
  modern namesake), but it can't catch a collision between two people
  active in the same era. 421 of 164,955 people are currently flagged.
- **`movie_cast.billing_order` is a positional proxy for TMDB's cast
  `order` field, not the integer itself** (never persisted anywhere in the
  pipeline). `director`/`cast` didn't exist in the raw source at all --
  both are new columns added wholesale by
  `scripts/enrichment/fill_missing.py`, which sorts `credits["cast"]` by
  TMDB's own `order` before comma-joining
  (`sorted(credits["cast"], key=lambda c: c.get("order", 999))[:10]`), so
  there's no non-enriched cast population where position could have
  drifted from the real order -- the proxy is reliable across the whole
  populated cast, not just a backfilled subset. It's capped at the top 10
  credited names per movie (someone absent from `movie_cast` may simply be
  outside the top 10, not unbilled), and it's a proxy for role prominence,
  not screen time or impact -- a contractual/studio billing decision that
  correlates with but isn't identical to either. 80 movies show an 11th
  position, caused by an embedded comma inside one of the 10 real names
  (e.g. a "Last, Jr." suffix) splitting into an extra token -- the same
  comma-ambiguity limitation as `production_companies`/`genres` below, not
  an 11th real credited person.
- **Financial data (budget/revenue/profit) is dropped from the schema
  entirely**, not just deprioritized — only ~19.6% of the catalog (8,900
  of 45,433 movies) discloses both, skewed toward mainstream titles, which
  worked against rather than for the "hidden markets" thesis (see
  [BUSINESS_ANGLE.md](BUSINESS_ANGLE.md)). Still present in the cleaned
  source CSV and in `clean.movies_main` if a future angle needs it back --
  just not mapped past `stg_movies` anymore.
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
| Director/Cast Weighted Avg Rating | person grain, within a selected market | `RELATEDTABLE` over `movie_director`/`movie_cast` joined to `fct_movie_performance`, filtered to the market selected on Page 1 — same weighted-avg shape as the market-level measure, one level down |
| Director/Cast Rating Consistency | same | `AVERAGE(std_dev)` over the person's market-linked films — risk filter, same role as the market-level `std_dev` measure |
| Filmography Count (market-scoped) | same | `COUNTROWS(RELATEDTABLE(...))` filtered to the selected market — not a hard floor (see below) |
| Talent Confidence Flag | person grain, within a selected market | Reuses the `Confidence Flag` pattern above, keyed off Filmography Count instead of `total_ratings` — flags low-sample people instead of excluding them, so an emerging/crossover talent with few market-linked films still surfaces, just visibly flagged |
| Cast Billing Weight | movie_cast grain | `1 / billing_order` (or an equivalent inverse), weights lead-billed cast above background credits in any cast-level aggregate |
| Recency/Activity Flag | person grain | Flags "Inactive" when `latest_release_date` is more than N years before today — deprioritizes retired/inactive people from a "pursue" recommendation |
| Name Collision Flag | person grain | Directly from `dim_person.possible_name_collision` — surfaced as a visible warning on the talent shortlist, not filtered out silently |

## 5. Power BI model notes

**Role-playing dimension (`dim_language`)** — it's related to
`fct_movie_performance` two different ways: directly via
`original_language_code` (single-valued, "market" axis) and indirectly via
the `movie_language` bridge (multi-valued, "reach" signal). Power BI only
allows one active relationship between two tables, so import `dim_language`
**twice**: once as `dim_original_language` (active relationship to
`fct_movie_performance`), once as `dim_spoken_language` (relationship to
the `movie_language` bridge). Keeps the underlying normalized ERD
untouched — the duplication is Power BI-side only.

**Many-to-many bridges** (`movie_genre`, `movie_country`,
`movie_language`↔`dim_spoken_language`, `movie_cast`, `movie_director`) —
set cross-filter direction to **Both** on these relationships, or slicers
on genre/country/language/person won't propagate to the fact table. Not
needed on `fct_movie_performance` ↔ `dim_original_language`, which is a
normal single-direction 1-to-many.

## 6. Slicers/filters

| Page | Slicer | Filters via |
|---|---|---|
| Page 1 (Market Map) | Min. Total Ratings threshold (confidence) | disconnected parameter table |
| Page 1 | Release-year range | `movies.release_date` |
| Page 1 | Genre | `movie_genre` bridge |
| Page 2 (Shortlist) | Market/language | carried from Page 1, or standalone `dim_original_language` slicer |
| Page 2 | Confidence flag (Reliable / Low sample) | `Confidence Flag` measure |
| Page 2 | Reach count range | `Title Reach Count` measure |
| Page 3 (Talent) | Market (inherits Page 1/2 selections) | carried, or standalone `dim_original_language` slicer |
| Page 3 | Talent Confidence Flag (Reliable / Low sample) | `Talent Confidence Flag` measure |
| Page 3 | Recency/Activity Flag | `Recency/Activity Flag` measure |
| Page 3 | Name Collision warning (visible, not a filter) | `Name Collision Flag` measure |

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
about → here are the specific people worth pursuing once we act on a market."*

### Page 0 — Executive Summary
- **Audience:** Head of Global Content Acquisition, first 15 seconds.
- **Shows:** catalog-wide framing (95% ratings coverage, 98.6%/96.6%
  director/cast coverage) + a single headline finding: "Top 5 underexposed
  markets" as a callout, not a chart.
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

### Page 3 — Talent Scouting Layer (Use Case 3)
- **Audience:** Acquisitions/casting negotiators — the deal-making page.
- **Shows:** drills from a market selected on Page 1 down to directors/cast
  linked to that market's titles, ranked by weighted avg rating and
  consistency, weighted toward lead billing.
- **Visuals:** sortable table (name, role, market-linked filmography count,
  weighted avg rating, consistency, latest release date); Talent
  Confidence Flag and Recency/Activity Flag as conditional formatting;
  Name Collision Flag surfaced as a visible warning icon, never silently
  filtered.
- **Recommended-action callout:** *"[N] directors/cast from this market
  clear the quality bar with recent activity — shortlist for outreach this
  quarter. [M] flagged for identity verification before contacting."*
