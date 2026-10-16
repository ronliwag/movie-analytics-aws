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
