-- Business rule from int_movies_joined.sql: profit is never imputed --
-- it must be revenue - budget exactly when both are disclosed, and null
-- whenever either one is missing. Fails (returns rows) on any drift
-- between the two.

select
    movie_id,
    budget,
    revenue,
    profit
from {{ ref('fct_movie_performance') }}
where
    (budget is not null and revenue is not null and profit is distinct from (revenue - budget))
    or ((budget is null or revenue is null) and profit is not null)
