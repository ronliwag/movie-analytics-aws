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
