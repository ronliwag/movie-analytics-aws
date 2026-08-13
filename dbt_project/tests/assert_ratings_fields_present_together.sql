-- A rating summary is all-or-nothing: stg_ratings.movie_id is a 1-row-per-
-- movie summary sourced from a single upstream computation, so
-- avg_rating/total_ratings/last_rated should never be partially populated
-- -- either every field is present (a real rating summary exists) or every
-- field is null (one of the ~2,266 movies with no rating data at all, per
-- fct_movie_performance's LEFT JOIN to ratings).
--
-- std_dev is the one exception, not a bug: standard deviation of a single
-- rating is mathematically undefined, so Postgres's own STDDEV() legitimately
-- returns null wherever total_ratings = 1 (2,336 rows) even though
-- avg_rating/total_ratings/last_rated are all present. Confirmed by
-- inspecting analytics.fct_movie_performance directly -- every std_dev-null,
-- avg_rating-not-null row has total_ratings = 1, no other value.

select
    movie_id,
    avg_rating,
    total_ratings,
    std_dev,
    last_rated
from {{ ref('fct_movie_performance') }}
where
    (avg_rating is null) != (total_ratings is null)
    or (avg_rating is null) != (last_rated is null)
    or (avg_rating is not null and std_dev is null and total_ratings != 1)
    or (avg_rating is null and std_dev is not null)
