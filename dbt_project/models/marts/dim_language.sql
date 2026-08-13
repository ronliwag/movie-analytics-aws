-- Deduped language catalog, keyed by its natural ISO 639-1 code. Codes come
-- from two sources -- spoken languages (int_movie_languages) and each
-- movie's original_language_code, since 1,487 movies (checked live against
-- analytics.stg_movie_extended) have an original_language_code not present
-- in their own spoken_language_codes list. Without this union,
-- movies.original_language_code (wired up in Task 4) would have
-- thousands of orphaned FKs.
--
-- `name` is looked up from the iso_639_1 seed (ISO 639-1 standard English
-- names) rather than taken from TMDB's spoken_language_names. TMDB's own
-- raw export leaves `name` blank for 19 of these codes even at the source
-- (spot-checked in data/raw/movie_extended.csv, e.g. `to`:
-- [{'iso_639_1': 'to', 'name': ''}]) -- there's no native-language value to
-- recover for them from anywhere in this pipeline. Sourcing every code's
-- name from one authoritative external reference keeps the column
-- consistent instead of mixing TMDB's native-script names with an English
-- fallback for just the gaps. `cn` (Cantonese) and `xx` (TMDB's "no
-- language" placeholder) aren't real ISO 639-1 codes -- TMDB-specific
-- conventions -- so they're named explicitly rather than looked up.

with codes as (

    select language_code
    from {{ ref('int_movie_languages') }}

    union

    -- The `~ '^[a-z]{2}$'` guard is defensive -- it used to exclude ~11
    -- corrupted original_language_code values from the same CSV
    -- column-shift bug fixed in scripts/pyspark/transform.py (see
    -- docs/DATA_MODEL.md known limitations); kept in case of future data
    -- issues, but shouldn't filter anything out anymore.
    select original_language_code as language_code
    from {{ ref('stg_movie_extended') }}
    where original_language_code ~ '^[a-z]{2}$'

)

select
    codes.language_code as iso_639_1_code,
    coalesce(
        iso.name,
        case codes.language_code
            when 'cn' then 'Cantonese'
            when 'xx' then 'No Language'
        end
    ) as name
from codes
left join {{ ref('iso_639_1') }} as iso
    on codes.language_code = iso.code
