# Enrichment Results

Cross-analysis of `data/raw/` vs `data/enriched/` after running, in order:
`fill_missing.py` → `movielens_ratings.py` → `validate_records.py` (see
`README.md` for what each script does and why). All numbers below are
measured directly against the actual files, not estimated.

## What was done

1. **`fill_missing.py`** — for every movie, looked up its TMDB record (a
   direct id lookup — this dataset's `movies_main.id` IS the TMDB id) and
   filled in whatever was missing: `budget`/`revenue` in `movies_main.csv`,
   and `genres`/`production_companies`/`production_countries`/
   `spoken_languages` in `movie_extended.csv`. Also added 4 brand-new
   columns to `movie_extended.csv` that don't exist in the raw source at
   all: `original_title`, `original_language`, `director`, `cast` (top 10
   by billing order). Never overwrites a value that's already present.
2. **`movielens_ratings.py`** — two passes against `ratings.json`, by
   joining MovieLens's `ratings.csv` to our TMDB-based ids via MovieLens's
   own `links.csv` (restricted to ids actually in our catalog): first
   corrected every *existing* record against a fresh MovieLens computation
   for the same movie (rejecting the correction entirely, not per-field,
   whenever it would decrease `total_ratings` -- a reliable signal of a
   `links.csv` id mismatch rather than a genuine update), then filled in
   entries for movies with no rating record at all.
3. **`validate_records.py`** — for movies that already *had* a value,
   compared it against TMDB and adopted TMDB's version wherever they
   disagreed (TMDB is more current). `title` is checked against both
   TMDB's display title and its `original_title` before being flagged, so
   a dataset that already stores the original-language title (e.g.
   `"Le Bonheur"`) isn't overwritten with a translated release title
   (`"Happiness"`) just because the strings differ.

## Dataset currency — why we depend on TMDB and MovieLens

Every "trust the external source" decision above (`validate_records.py`
adopting TMDB's values, `movielens_ratings.py` adopting MovieLens's)
rests on one claim: those sources are more current than this project's
raw snapshot. Measured directly, not assumed:

| Dataset | Oldest | Newest | Coverage |
|---|---|---|---|
| Raw `movies_main.csv` (release date) | 1874-12-09 | **2020-12-16** | 45,396 / 45,486 parsed |
| TMDB (our cached lookups, release date) | 1874-12-09 | **2024-03-28** | 44,908 / 44,908 parsed |
| MovieLens `movies.csv` (full ml-32m catalog) | 1874 | **2023** | 87,585 movies |
| MovieLens `movies.csv` (restricted to our catalog) | 1874 | 2022 | 42,951 / 45,486 matched |

| Ratings | Oldest `last_rated` | Newest `last_rated` |
|---|---|---|
| Raw `ratings.json` | 1996-03-30 | **2016-10-16** |
| MovieLens `ratings.csv` (full ml-32m) | 1995-01-09 | **2023-10-13** |

**Reading it:** the raw snapshot's release dates stop at 2020 and its
ratings stop at 2016 — this project's data is at minimum several years
stale by the time this capstone runs. TMDB's release-date ceiling reaches
2024, confirming it's a live source relative to the raw snapshot. MovieLens's
ratings extend to October 2023 and its catalog to 2023 — both meaningfully
past the raw dataset's ceilings. This is the concrete basis for depending
on TMDB for movie metadata currency and MovieLens for rating currency,
rather than an assumption.

One curiosity worth noting, not a bug: all three sources agree the oldest
title is **"Passage of Venus"** (TMDB id 315946), dated 1874-12-09 —
predating cinema itself. It's a real, if unusual, TMDB catalog entry (an
early photographic record of the 1874 Transit of Venus), and its
consistent appearance across raw, TMDB, and MovieLens is itself a small
extra confirmation that the id-based linkage between all three sources is
sound.

## Release-date coverage: budget/revenue vs ratings

Currency of the *source* is one thing; how far each *type* of performance
data actually reaches back into the catalog is another. Measured by
joining back to each movie's release date:

| | Raw | Enriched |
|---|---|---|
| Has budget & revenue (both non-zero) | 1915-12-13 → 2017-08-04 (n=4,339) | 1913-11-24 → 2022-12-14 (n=8,900) |
| Has a rating | 1874-12-09 → 2018-11-07 (n=9,071) | 1874-12-09 → 2024-03-28 (n=43,144) |
| *(catalog overall, for reference)* | 1874-12-09 → 2020-12-16 (n=45,396) | — |

**Ratings cover the full historical range, financial data doesn't.**
Ratings coverage spans all the way back to 1874 (even the "Passage of
Venus" outlier has a rating) and forward past 2020, but budget/revenue
coverage only starts around 1913-1915 and stops at 2017-2022. This tracks
with the mechanics of each data type: a MovieLens user can rate *any*
cataloged film regardless of age or obscurity, but a budget/revenue figure
requires someone to have actually researched and verified real financial
numbers — which essentially never happened for the oldest, most obscure
titles.

**Ratings coverage is far broader than financial coverage, even after
enrichment**: 43,144 movies have a rating vs. only 8,900 have both budget
and revenue. Financial performance is the inherently sparser signal in
this dataset — enrichment roughly doubled it (4,339 → 8,900), while
ratings coverage more than quadrupled (9,067 → 43,167 per the coverage
table above) — but no amount of enrichment closes that structural gap,
since it reflects what TMDB's crowd-sourced budget/revenue tracking has
actually captured, concentrated on higher-profile releases, not a gap in
the enrichment logic itself.

## `movies_main.csv`

| Field | Raw missing/zero | Enriched missing/zero |
|---|---|---|
| `budget` | 38,324 (84.3%) | 32,940 (72.4%) |
| `revenue` | 38,074 (83.7%) | 32,988 (72.5%) |

Smaller improvement than the other fields, and worth being honest about
why: **TMDB itself often lacks budget/revenue for the same long tail of
obscure/older films this dataset lacks it for** — it's crowd-sourced data,
well-maintained for mainstream titles, sparse for the rest. This isn't a
gap in the enrichment logic; a 100-movie sample taken from early in the
file (mostly recognizable studio releases — Casino, GoldenEye, Clueless)
filled at a 35% rate, while the full, much-longer tail of the catalog
filled at ~12%. Both numbers are real; they just reflect where a given
movie sits on the fame spectrum.

## `movie_extended.csv`

| Field | Raw empty | Enriched empty |
|---|---|---|
| `genres` | 2,442 (5.4%) | 273 (0.6%) |
| `production_companies` | 12,365 (27.2%) | 4,079 (9.0%) |
| `production_countries` | 6,290 (13.8%) | 1,535 (3.4%) |
| `spoken_languages` | 3,835 (8.4%) | 991 (2.2%) |

New columns (didn't exist in the raw source at all):

| Column | Filled |
|---|---|
| `original_title` | 44,914 (98.8%) |
| `original_language` | 44,914 (98.8%) |
| `director` | 44,793 (98.5%) |
| `cast` | 43,891 (96.5%) |

These fields fill at a much higher rate than budget/revenue because
TMDB's metadata team actively curates genre/cast/crew data as part of
just cataloguing a movie exists — it doesn't depend on someone having
separately researched and entered financial figures.

## `ratings.json`

| | Coverage of the 45,433-movie catalog |
|---|---|
| Raw | 9,067 records (20.0%) |
| Enriched | 43,167 records (95.0%) |

Beyond coverage, `movielens_ratings.py` also corrected 6,734 of the 9,067
*existing* records (74.3%) against a fresh computation from the full
MovieLens dump — **26,296 values corrected**: `last_rated` (6,734),
`avg_rating` (6,643), `std_dev` (6,546), `total_ratings` (6,373).

**A first pass at this (documented in an earlier version of this file)
applied every disagreement unconditionally and found a real problem**: of
the `total_ratings` corrections, 78% (6,373) increased as expected from a
larger/more-current ratings pool, but 22% (1,802) actually *decreased* —
some sharply (e.g. one movie went from 247 ratings to 3). That pattern
doesn't look like "the data updated," it looks like a **MovieLens
`movieId` → TMDB id linkage mismatch** for a minority of movies (see
`README.md` for how `links.csv` bridges the two id spaces, and why a
mismatch there produces exactly this symptom).

**Fix:** `resolve_existing_rating()` now rejects a correction *entirely*
(not per-field) whenever it would decrease `total_ratings`, since
MovieLens ratings only accumulate over time — a real recount of the same
movie should never shrink. Applying only some fields from a mismatched
record would leave it internally inconsistent (an old `total_ratings`
paired with an `avg_rating` computed from a completely different, much
smaller sample), which is worse than leaving the record untouched. After
the fix: **zero remaining decreases**, and the 6,373 legitimate increases
(78% of the original set) went through exactly as expected — the numbers
above already reflect this corrected behavior.

## Corrections applied (`validate_records.py`)

15,443 values corrected across 13,884 movies, where an existing value
disagreed with TMDB:

| Field | Corrections |
|---|---|
| `release_date` | 10,408 |
| `revenue` | 2,610 |
| `title` | 1,882 |
| `budget` | 543 |

`title` dropped from 3,790 raw mismatches to 1,882 real corrections —
the other ~1,900 turned out to already match TMDB's `original_title`
(the original-language title) rather than its display title, and were
correctly left alone rather than being overwritten.

## Coverage ceiling

Across the full run, **519 of 45,433 ids (1.1%) got no TMDB match at all**
(a 404 — the movie no longer exists there, or never did under that id).
Those rows pass through enrichment/validation untouched, same as before.

## A bug this process caught

Midway through, we found that `movie_extended.csv`'s gap-filling had been
silently failing 100% of the time in an earlier run: its `id` column loads
as a string (`'862'`, not `862`) because of the same 3 corrupt rows that
affect `movies_main.csv`, while the lookup key built from the (numeric,
coerced) `movies_main` ids was a plain `int` — `'862' != 862` as dict
keys, so every `movie_extended` update was a no-op that raised no error.
Fixed by coercing `movie_extended`'s `id` column the same way
`movies_main`'s already was, and covered by a regression test
(`test_enrich_updates_extended_row_when_id_column_is_string_dtype`) so it
can't silently regress again.
