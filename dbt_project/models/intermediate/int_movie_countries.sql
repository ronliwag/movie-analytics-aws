-- Zips stg_movie_extended.production_country_codes/_names (parallel
-- comma-packed lists) into one row per (movie_id, country_code,
-- country_name). Grain: movie x country.
--
-- 47 movies used to have a CSV column-shift bug from an unescaped quote
-- in production_companies (e.g. movie_id 154399's `"PRF ""Zespoly
-- Filmowe""`), which pushed their entire director/cast/country/language
-- block left by one column. Root-caused and fixed in
-- scripts/pyspark/transform.py (Spark's CSV reader needed
-- `.option("escape", "\"")` to match pandas' RFC4180 doubled-quote
-- escaping) -- see docs/DATA_MODEL.md known limitations. The
-- `~ '^[A-Za-z]{2}$'` guard is kept as a defensive check but shouldn't
-- filter anything out anymore.

with extended as (

    select movie_id, production_country_codes, production_country_names
    from {{ ref('stg_movie_extended') }}
    where production_country_codes is not null

)

select distinct
    movie_id,
    trim(country_code) as country_code,
    nullif(trim(country_name), '') as country_name
from extended,
    unnest(
        string_to_array(production_country_codes, ','),
        string_to_array(production_country_names, ',')
    ) as t(country_code, country_name)
where trim(country_code) ~ '^[A-Za-z]{2}$'
