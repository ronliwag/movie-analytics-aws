-- fct_movie_performance.reach_country_count is precomputed in
-- int_movies_joined.sql from a distinct count over int_movie_countries.
-- This cross-checks it against movie_country, the bridge table Power BI
-- actually joins against -- if the two ever disagree, either the bridge or
-- the fact table's precomputed reach signal is wrong.

select
    f.movie_id,
    f.reach_country_count as fact_count,
    coalesce(bridge.actual_count, 0) as bridge_count
from {{ ref('fct_movie_performance') }} as f
left join (
    select movie_id, count(distinct iso_3166_1_code) as actual_count
    from {{ ref('movie_country') }}
    group by movie_id
) as bridge
    on f.movie_id = bridge.movie_id
where f.reach_country_count != coalesce(bridge.actual_count, 0)
