-- Zips stg_movie_extended.spoken_language_codes/_names (parallel
-- comma-packed lists) into one row per (movie_id, language_code,
-- language_name). Grain: movie x spoken language.
--
-- 49 movies used to have a CSV column-shift bug from an unescaped quote
-- in production_companies (e.g. movie_id 154399's `"PRF ""Zespoly
-- Filmowe""`), which pushed their entire director/cast/country/language
-- block left by one column. Root-caused and fixed in
-- scripts/pyspark/transform.py (Spark's CSV reader needed
-- `.option("escape", "\"")` to match pandas' RFC4180 doubled-quote
-- escaping) -- see docs/DATA_MODEL.md known limitations. The
-- `~ '^[a-z]{2}$'` guard is kept as a defensive check but shouldn't filter
-- anything out anymore. Separately, mismatched code/name list lengths (a
-- code with no listed name -- a genuine TMDB data gap, unrelated to the
-- shift bug) still resolve correctly via the trailing-NULL-pad behavior of
-- parallel unnest.

with extended as (

    select movie_id, spoken_language_codes, spoken_language_names
    from {{ ref('stg_movie_extended') }}
    where spoken_language_codes is not null

)

select distinct
    movie_id,
    trim(language_code) as language_code,
    nullif(trim(language_name), '') as language_name
from extended,
    unnest(
        string_to_array(spoken_language_codes, ','),
        string_to_array(spoken_language_names, ',')
    ) as t(language_code, language_name)
where trim(language_code) ~ '^[a-z]{2}$'
