-- Same cross-check as assert_reach_country_count_matches_movie_country.sql,
-- for reach_language_count against the movie_language bridge.

select
    f.movie_id,
    f.reach_language_count as fact_count,
    coalesce(bridge.actual_count, 0) as bridge_count
from {{ ref('fct_movie_performance') }} as f
left join (
    select movie_id, count(distinct iso_639_1_code) as actual_count
    from {{ ref('movie_language') }}
    group by movie_id
) as bridge
    on f.movie_id = bridge.movie_id
where f.reach_language_count != coalesce(bridge.actual_count, 0)
