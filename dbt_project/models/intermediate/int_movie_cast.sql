with extended as (

    select movie_id, cast_members
    from {{ ref('stg_movie_extended') }}
    where cast_members is not null

)

select
    movie_id,
    trim(person_name) as person_name,
    billing_order
from extended,
    unnest(string_to_array(cast_members, ',')) with ordinality as t(person_name, billing_order)
where trim(person_name) != ''
