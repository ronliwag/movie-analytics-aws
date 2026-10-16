-- Splits stg_movie_extended.director (comma-packed) into one row per
-- (movie_id, person_name). Grain: movie x director.

with extended as (

    select movie_id, director
    from {{ ref('stg_movie_extended') }}
    where director is not null

)

select distinct
    movie_id,
    trim(person_name) as person_name
from extended,
    unnest(string_to_array(director, ',')) as person_name
where trim(person_name) != ''
