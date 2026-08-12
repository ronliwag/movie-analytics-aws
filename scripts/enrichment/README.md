# Enrichment

Three separate, standalone scripts:

- **`fill_missing.py`** (TMDB API) — fills missing `budget`/`revenue`
  (and empty genre/company/country/language metadata) in the raw dataset,
  plus adds 4 brand-new columns to `movie_extended.csv` that don't exist
  in the raw source at all (`original_title`, `original_language`,
  `director`, `cast`). Writes enriched copies to `data/enriched/`. Never
  overwrites a value that's already present.
- **`validate_records.py`** (TMDB API) — for values that are already
  *present* (not missing), compares them against TMDB and **overwrites**
  `data/enriched/movies_main.csv` in place with TMDB's version wherever
  they disagree (TMDB is more current), across `budget`/`revenue`/
  `release_date`/`title`. Also writes `data/enriched/validation_report.csv`
  as a change log of every value it corrected, for audit purposes — but
  the correction itself already happened by the time you read the report.
  `title` is checked against both TMDB's display title and its
  `original_title` before being flagged, so a dataset that already stores
  the original-language title isn't overwritten with a translated release
  title just because the strings differ. Must run **after**
  `fill_missing.py` — it corrects `data/enriched/movies_main.csv`, not
  `data/raw/`, so `fill_missing.py`'s gap-filling isn't skipped or
  clobbered.
- **`movielens_ratings.py`** (local MovieLens dump, no API) — two
  operations against `ratings.json`, mirroring the fill/correct split
  above: `resolve_ratings()` corrects *existing* records against a fresh
  MovieLens computation for the same movie (our full dump is a larger,
  more current ratings pool than whatever originally produced the
  existing ~20% coverage), and `fill_missing_ratings()` appends records
  for movie ids with no existing entry at all. Both join to our TMDB-based
  ids via MovieLens's own `links.csv`. Not TMDB, because TMDB's own
  `vote_average` is a different rating system (0–10 scale) from this
  dataset's 0.5–5.0 MovieLens-style scale — see the script's docstring for
  the full reasoning. **Writes data** (both `ratings.json` and a
  `ratings_validation_report.csv` change log). Rejects a correction
  ENTIRELY (not per-field) if it would decrease `total_ratings` — MovieLens
  ratings accumulate over time and are never removed, so a real recount of
  the same movie should only ever grow. A decrease reliably signals a
  `links.csv` id mismatch (this movie's MovieLens `movieId` resolved to a
  different movie than whatever originally produced the existing record),
  not a genuine update. Applying only some fields from a mismatched record
  would leave it internally inconsistent, which is why the whole
  correction is skipped rather than just the one field. See `RESULTS.md`.

See `RESULTS.md` for the actual before/after numbers from the last full run
of all three.

**All three are deliberately outside the ingestion/cleaning pipeline.**
Run them once, manually, *before* `scripts/pyspark/transform.py` or
`scripts/pandas/clean_data.py`. None of those import from here or call
this automatically.

Run `fill_missing.py` before `validate_records.py`: besides the ordering
requirement above (`validate_records.py` needs `fill_missing.py`'s output
file to exist), they share the same TMDB response cache, so ids
`fill_missing` already fetched don't cost a second API call when
`validate_records` runs afterward. `movielens_ratings.py` is independent
of both (different data source, different output file) and can run in any
order relative to them.

## Why this is safe to bolt on without touching ingestion/cleaning

Output has the exact same filenames and columns as `data/raw/` (plus the 4
new `movie_extended.csv` columns) — `movies_main.csv` stays
`id,title,release_date,budget,revenue`, `movie_extended.csv`'s original 4
raw columns keep their format (countries/languages written back in the
same Python-repr list-of-dicts string the source already uses),
`ratings.json`'s existing records keep their exact shape. Ingestion code
doesn't know or care whether a value came from the raw download,
`fill_missing.py`, or a `validate_records.py` correction, so the only
change needed anywhere else is pointing `RAW_DIR` at `data/enriched/`
instead of `data/raw/` once these have been run.

Neither script dedupes, drops corrupt rows, or standardizes dates — those
stay cleaning's job, run afterward, unchanged.

## Why id-based lookup, not title search

The dataset's own shape indicates it's a TMDB extract already: the 3
corrupt rows found during cleaning contain TMDB poster-path strings
(`/ff9qCepilowshEtG2GYWwzt2bs4.jpg`), and `production_countries`/
`spoken_languages` use TMDB's exact `iso_3166_1`/`iso_639_1` response
schema. So `movies_main.id` is assumed to already be a TMDB movie id —
enrichment is a direct `GET /movie/{id}` lookup, not a fuzzy title match.
`RESULTS.md` has the confirming evidence (a ~1.1% 404 rate across the
full catalog, and coherent results at scale, not random noise).

## Running it

```
export TMDB_API_KEY=...          # or set it in .env
python -m scripts.enrichment.fill_missing              # fills gaps, full run
python -m scripts.enrichment.fill_missing --limit 50    # test on a subset first
python -m scripts.enrichment.validate_records           # corrects mismatches, full run
python -m scripts.enrichment.validate_records --limit 50

# Setup for movielens_ratings.py: download a full dataset (ml-25m or newer)
# from https://grouplens.org/datasets/movielens/ and unzip to
# data/external/movielens/ (needs links.csv and ratings.csv). No API key.
python -m scripts.enrichment.movielens_ratings
```

`fill_missing`/`validate_records` need `TMDB_API_KEY` (see `.env.example`)
for any id not already cached — not required to run any of the test
suites, which mock the HTTP layer (or use small synthetic CSVs, for
`movielens_ratings`) entirely.

TMDB responses are cached to `data/enriched/tmdb_cache/{id}.json` (shared
by both TMDB-backed scripts), so an interrupted run is resumable —
re-running skips every id already fetched, and a cache entry from before
`credits` was added to the request is detected as stale and automatically
refetched rather than requiring a manual cache wipe. In practice, a full
run of `fill_missing.py` against the ~45K-movie catalog took about 40
minutes at the default concurrency (`--workers`, default 10); `--limit` is
still worth using to validate against a small batch first, since some ids
inevitably come back `404` (not every id is guaranteed to still exist on
TMDB) and it's cheaper to catch a config mistake on 50 movies than 45,000.
`movielens_ratings.py` has no such concern — it's a local join over an
already-downloaded file, done in minutes.
