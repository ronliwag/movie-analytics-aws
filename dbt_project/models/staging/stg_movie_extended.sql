
with source as (

    select * from {{ source('movie_analytics_raw', 'movie_extended') }}

)

select
    id::integer as movie_id,
    original_title,
    original_language as original_language_code,
    director,
    "cast" as cast_members,
    genres,
    production_companies,
    production_country_codes,
    production_country_names,
    spoken_language_codes,
    spoken_language_names
from source
