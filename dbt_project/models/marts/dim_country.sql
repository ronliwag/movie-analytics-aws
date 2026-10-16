with countries as (

    select country_code, country_name
    from {{ ref('int_movie_countries') }}

)

select
    country_code as iso_3166_1_code,
    mode() within group (order by country_name) as name
from countries
group by country_code
