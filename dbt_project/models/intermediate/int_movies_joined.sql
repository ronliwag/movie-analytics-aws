-- Join movies to ratings and extended metadata. Business logic (e.g.
-- picking a primary rating source, computing profit) belongs here, not in
-- staging or in the mart.

with movies as (
    select * from {{ ref('stg_movies') }}
),

ratings as (
    select * from {{ ref('stg_ratings') }}
),

extended as (
    select * from {{ ref('stg_movie_extended') }}
)

-- TODO: join the three CTEs on movie_id, resolve one row per movie.
select *
from movies
