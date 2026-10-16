-- Deduped language catalog, keyed by its natural ISO 639-1 code. Unions
-- two sources -- spoken languages (int_movie_languages) and each movie's
-- original_language_code, since 1,487 movies (checked live against
-- analytics.stg_movie_extended) have an original_language_code not present
-- in their own spoken_language_codes list. Without this union,
-- movies.original_language_code (wired up in Task 4) would have
-- thousands of orphaned FKs.
--
-- Uses mode() rather than min() to pick the display name per code -- see
-- dim_country.sql for why (a single noisy outlier row can otherwise beat
-- the overwhelmingly common correct name alphabetically).

with spoken as (

    select language_code, language_name
    from {{ ref('int_movie_languages') }}

),

original as (

    -- The `~ '^[a-z]{2}$'` guard is defensive -- it used to exclude ~11
    -- corrupted original_language_code values from the same CSV
    -- column-shift bug fixed in scripts/pyspark/transform.py (see
    -- docs/DATA_MODEL.md known limitations); kept in case of future data
    -- issues, but shouldn't filter anything out anymore.
    select distinct original_language_code as language_code
    from {{ ref('stg_movie_extended') }}
    where original_language_code ~ '^[a-z]{2}$'

),

all_codes as (

    -- UNION ALL, not UNION -- mode() below needs every movie's occurrence
    -- of (code, name) preserved to weigh by actual frequency. A plain
    -- UNION would collapse repeated (code, name) pairs down to one row
    -- each, flattening the frequency signal mode() depends on and making
    -- it pick an arbitrary tied name instead of the truly common one.
    select language_code, language_name from spoken
    union all
    select language_code, null as language_name from original

)

select
    language_code as iso_639_1_code,
    mode() within group (order by language_name) as name
from all_codes
group by language_code
