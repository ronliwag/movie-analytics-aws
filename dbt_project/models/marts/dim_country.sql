-- Deduped country catalog, keyed by its natural ISO 3166-1 code (no
-- surrogate key needed). Uses mode() rather than min() to pick the display
-- name -- a couple of codes have a rare mismatched (code, name) pairing
-- from noisy source rows (see docs/DATA_MODEL.md known limitations), and
-- min() would let a single alphabetically-early outlier win over the
-- overwhelmingly common correct name; mode() picks whichever name most
-- movies actually agree on.

with countries as (

    select country_code, country_name
    from {{ ref('int_movie_countries') }}

)

select
    country_code as iso_3166_1_code,
    mode() within group (order by country_name) as name
from countries
group by country_code
