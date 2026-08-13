with names as (

    select person_name from {{ ref('int_movie_directors') }}
    union
    select person_name from {{ ref('int_movie_cast') }}

),

keyed as (

    select
        {{ dbt_utils.generate_surrogate_key(['lower(person_name)']) }} as person_id,
        person_name
    from names

)

select
    person_id,
    min(person_name) as name
from keyed
group by person_id
