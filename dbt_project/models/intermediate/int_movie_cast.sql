with extended as (

    select movie_id, cast_members
    from {{ ref('stg_movie_extended') }}
    where cast_members is not null

)

select distinct
    movie_id,
    trim(person_name) as person_name
from extended,
    unnest(string_to_array(cast_members, ',')) as person_name
where trim(person_name) != ''
