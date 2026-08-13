{#
    Compiled model-level rationale, previously living as long header
    comments inside each .sql file. Referenced from schema.yml via
    {{ doc('model_name') }}, so it renders as the model's full description
    in `dbt docs generate` -- not just visible in a source-code tab.

    Only models whose header comment held real "why" content (design
    tradeoffs, historical bugs, non-obvious rationale) have a block here.
    Short, line-specific comments (e.g. "never imputed" sitting directly
    above the one CASE expression it explains) are left inline in the SQL
    -- they're tied to one exact line, not a general model overview, and
    moving them here would only make them harder to find while editing.
#}

{% docs int_movie_countries %}
One row per (movie_id, country_code, country_name), zipped from
stg_movie_extended's production_country_codes/_names pair. Grain: movie x
country.

47 movies used to have a CSV column-shift bug from an unescaped quote in
production_companies (e.g. movie_id 154399's `"PRF ""Zespoly Filmowe""`),
which pushed their entire director/cast/country/language block left by one
column. Root-caused and fixed in scripts/pyspark/transform.py (Spark's CSV
reader needed `.option("escape", "\"")` to match pandas' RFC4180
doubled-quote escaping) -- see docs/DATA_MODEL.md known limitations. The
`~ '^[A-Za-z]{2}$'` guard on country_code is kept as a defensive check but
shouldn't filter anything out anymore.
{% enddocs %}

{% docs int_movie_languages %}
One row per (movie_id, language_code, language_name), zipped from
stg_movie_extended's spoken_language_codes/_names pair. Grain: movie x
spoken language.

49 movies used to have a CSV column-shift bug from an unescaped quote in
production_companies (e.g. movie_id 154399's `"PRF ""Zespoly Filmowe""`),
which pushed their entire director/cast/country/language block left by one
column. Root-caused and fixed in scripts/pyspark/transform.py (Spark's CSV
reader needed `.option("escape", "\"")` to match pandas' RFC4180
doubled-quote escaping) -- see docs/DATA_MODEL.md known limitations. The
`~ '^[a-z]{2}$'` guard is kept as a defensive check but shouldn't filter
anything out anymore. Separately, mismatched code/name list lengths (a code
with no listed name -- a genuine TMDB data gap, unrelated to the shift bug)
still resolve correctly via the trailing-NULL-pad behavior of parallel
unnest.
{% enddocs %}

{% docs int_movies_joined %}
One row per movie_id, joining stg_movies to ratings and extended metadata,
plus computed profit and reach counts. Feeds fct_movie_performance directly
(a plain passthrough) and the Power BI DAX measures built on top of it.

Business logic (profit, reach counts) belongs here, not in staging or in
the mart -- fct_movie_performance.sql stays a plain final `select *`.

Scope note (see docs/DATA_MODEL.md sections 4 and 6): weighted avg rating,
reach index, quality/reach percentile, Distribution Gap Score, and the
ratings-volume confidence flag are all Power BI DAX measures computed live
off this fact table (several depend on ALLSELECTED / a user-adjustable
slicer, so they can't be precomputed as static columns here). This model
builds the movie-grain ingredients those measures consume, not the
measures themselves.

LEFT JOIN everywhere -- ratings coverage is 43,167/45,433 movies (2,266
have no rating row) and must not be dropped from the fact table.
{% enddocs %}

{% docs dim_language %}
Deduped language catalog, keyed by its natural ISO 639-1 code. Codes come
from two sources -- spoken languages (int_movie_languages) and each
movie's original_language_code, since 1,487 movies (checked live against
analytics.stg_movie_extended) have an original_language_code not present
in their own spoken_language_codes list. Without this union,
movies.original_language_code (wired up in Task 4) would have thousands of
orphaned FKs.

`name` is looked up from the iso_639_1 seed (ISO 639-1 standard English
names) rather than taken from TMDB's spoken_language_names. TMDB's own raw
export leaves `name` blank for 19 of these codes even at the source
(spot-checked in data/raw/movie_extended.csv, e.g. `to`:
[{'iso_639_1': 'to', 'name': ''}]) -- there's no native-language value to
recover for them from anywhere in this pipeline. Sourcing every code's name
from one authoritative external reference keeps the column consistent
instead of mixing TMDB's native-script names with an English fallback for
just the gaps. `cn` (Cantonese) and `xx` (TMDB's "no language" placeholder)
aren't real ISO 639-1 codes -- TMDB-specific conventions -- so they're
named explicitly rather than looked up.
{% enddocs %}

{% docs dim_country %}
Deduped country catalog, keyed by its natural ISO 3166-1 code (no
surrogate key needed).

Uses mode() rather than min() to pick the display name -- a couple of codes
have a rare mismatched (code, name) pairing from noisy source rows (see
docs/DATA_MODEL.md known limitations), and min() would let a single
alphabetically-early outlier win over the overwhelmingly common correct
name; mode() picks whichever name most movies actually agree on.
{% enddocs %}

{% docs dim_genre %}
Deduped genre catalog. genre_id is a surrogate key hashed from the
normalized (lower/trimmed) name -- movie_genre.sql computes the same hash
independently, so no join back to this table is needed to resolve the FK
at insert time.
{% enddocs %}

{% docs dim_production_company %}
Deduped production company catalog. production_company_id is a surrogate
key hashed from the normalized (lower/trimmed) name -- movie_company.sql
computes the same hash independently, so no join back to this table is
needed to resolve the FK at insert time.
{% enddocs %}

{% docs dim_person %}
Deduped person catalog, shared by movie_director and movie_cast. person_id
is a surrogate key hashed from the normalized (lower/trimmed) name -- both
bridge models compute the same hash independently, so no join back to this
table is needed to resolve the FK at insert time.

Known limitation (see docs/DATA_MODEL.md): name-based, not TMDB-id-based,
so two different real people sharing a name incorrectly collapse into one
row here.
{% enddocs %}
