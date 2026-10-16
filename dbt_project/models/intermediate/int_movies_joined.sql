with movies as (

    select * from {{ ref('stg_movies') }}

),

ratings as (

    select * from {{ ref('stg_ratings') }}

),

extended as (

    select movie_id, original_title, original_language_code
    from {{ ref('stg_movie_extended') }}

),

-- Sourced from the intermediate exploder models, not the marts bridge
-- tables (movie_country/movie_language) -- an intermediate model ref()ing
-- a marts model would invert the staging -> intermediate -> marts
-- dependency direction. int_movie_countries/int_movie_languages already
-- hold the same cleaned, deduped-per-movie pairs the bridges expose.
country_reach as (

    select movie_id, count(distinct country_code) as reach_country_count
    from {{ ref('int_movie_countries') }}
    group by movie_id

),

language_reach as (

    select movie_id, count(distinct language_code) as reach_language_count
    from {{ ref('int_movie_languages') }}
    group by movie_id

)

select
    movies.movie_id,
    movies.title,
    extended.original_title,
    extended.original_language_code,
    movies.release_date,
    movies.budget,
    movies.revenue,
    -- Never imputed -- null unless both budget and revenue are disclosed.
    case
        when movies.budget is not null and movies.revenue is not null
        then movies.revenue - movies.budget
    end as profit,
    ratings.avg_rating,
    ratings.total_ratings,
    ratings.std_dev,
    ratings.last_rated,
    coalesce(country_reach.reach_country_count, 0) as reach_country_count,
    coalesce(language_reach.reach_language_count, 0) as reach_language_count
from movies
left join ratings on movies.movie_id = ratings.movie_id
left join extended on movies.movie_id = extended.movie_id
left join country_reach on movies.movie_id = country_reach.movie_id
left join language_reach on movies.movie_id = language_reach.movie_id
