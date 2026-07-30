-- Final, wide, analytics-ready table. This is what Power BI reads.

with movies as (
    select * from {{ ref('int_movies_joined') }}
)

-- TODO: add profit, rating rollups, genre/country breakouts — whatever
-- Power BI's dashboard needs as pre-aggregated columns.
select *
from movies
