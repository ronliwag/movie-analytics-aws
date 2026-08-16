with names as (

    select movie_id, person_name from {{ ref('int_movie_directors') }}
    union
    select movie_id, person_name from {{ ref('int_movie_cast') }}

),

movies as (

    select movie_id, release_date from {{ ref('stg_movies') }}

),

joined as (

    select
        {{ dbt_utils.generate_surrogate_key(['lower(names.person_name)']) }} as person_id,
        names.person_name,
        names.movie_id,
        movies.release_date
    from names
    left join movies on names.movie_id = movies.movie_id

)

select
    person_id,
    min(person_name) as name,
    count(distinct movie_id) as filmography_count,
    min(release_date) as earliest_release_date,
    max(release_date) as latest_release_date,
    date_part('year', age(max(release_date), min(release_date)))::integer as career_span_years,
    date_part('year', age(max(release_date), min(release_date))) > 60 as possible_name_collision
from joined
group by person_id
