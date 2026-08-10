"""Tests for the pure fill-logic in fill_missing.py -- no HTTP involved,
since fill_movie_row/fill_extended_row operate on plain dicts (a row plus
an already-fetched TMDB response).

Run with: pytest scripts/enrichment/tests/test_fill_missing.py -v
"""

import numpy as np
import pandas as pd

from scripts.enrichment.fill_missing import (
    enrich,
    fill_extended_row,
    fill_movie_row,
    needs_enrichment,
)

TMDB_RESPONSE = {
    "budget": 30000000,
    "revenue": 373554033,
    "genres": [{"id": 16, "name": "Animation"}, {"id": 35, "name": "Comedy"}],
    "production_companies": [{"id": 3, "name": "Pixar Animation Studios"}],
    "production_countries": [{"iso_3166_1": "US", "name": "United States of America"}],
    "spoken_languages": [{"iso_639_1": "en", "name": "English"}],
    "original_title": "Toy Story",
    "original_language": "en",
    "credits": {
        "crew": [
            {"name": "John Lasseter", "job": "Director"},
            {"name": "Joss Whedon", "job": "Writer"},
        ],
        "cast": [
            {"name": "Tom Hanks", "order": 0},
            {"name": "Tim Allen", "order": 1},
            {"name": "Don Rickles", "order": 2},
        ],
    },
}


def test_needs_enrichment_true_for_zero_or_missing():
    assert needs_enrichment({"budget": 0, "revenue": 500}) is True
    assert needs_enrichment({"budget": 500, "revenue": 0}) is True
    assert needs_enrichment({"budget": np.nan, "revenue": 500}) is True


def test_needs_enrichment_false_when_both_present():
    assert needs_enrichment({"budget": 500, "revenue": 900}) is False


def test_fill_movie_row_fills_missing_budget_and_revenue():
    row = {"id": 862, "title": "Toy Story", "budget": 0, "revenue": np.nan}
    result = fill_movie_row(row, TMDB_RESPONSE)
    assert result["budget"] == 30000000
    assert result["revenue"] == 373554033


def test_fill_movie_row_never_overwrites_existing_value():
    row = {"id": 862, "title": "Toy Story", "budget": 999, "revenue": 999}
    result = fill_movie_row(row, TMDB_RESPONSE)
    assert result["budget"] == 999
    assert result["revenue"] == 999


def test_fill_movie_row_handles_no_tmdb_data():
    row = {"id": 862, "budget": 0, "revenue": 0}
    result = fill_movie_row(row, None)
    assert result["budget"] == 0
    assert result["revenue"] == 0


def test_fill_extended_row_fills_empty_fields():
    row = {
        "id": 862,
        "genres": None,
        "production_companies": "",
        "production_countries": "[]",
        "spoken_languages": np.nan,
        "original_title": None,
        "original_language": None,
        "director": None,
        "cast": None,
    }
    result = fill_extended_row(row, TMDB_RESPONSE)
    assert result["genres"] == "Animation,Comedy"
    assert result["production_companies"] == "Pixar Animation Studios"
    assert result["production_countries"] == "[{'iso_3166_1': 'US', 'name': 'United States of America'}]"
    assert result["spoken_languages"] == "[{'iso_639_1': 'en', 'name': 'English'}]"
    assert result["original_title"] == "Toy Story"
    assert result["original_language"] == "en"
    assert result["director"] == "John Lasseter"
    assert result["cast"] == "Tom Hanks,Tim Allen,Don Rickles"


def test_fill_extended_row_director_excludes_non_director_crew():
    row = {"director": None}
    result = fill_extended_row(row, TMDB_RESPONSE)
    assert "Joss Whedon" not in result["director"]


def test_fill_extended_row_cast_limited_to_top_10_by_order():
    tmdb_data = {
        **TMDB_RESPONSE,
        "credits": {
            "crew": [],
            "cast": [{"name": f"Actor {i}", "order": i} for i in range(15)],
        },
    }
    result = fill_extended_row({"cast": None}, tmdb_data)
    names = result["cast"].split(",")
    assert len(names) == 10
    assert names[0] == "Actor 0"
    assert "Actor 14" not in names


def test_fill_extended_row_never_overwrites_existing_value():
    row = {
        "id": 862,
        "genres": "Family",
        "production_companies": "Some Studio",
        "production_countries": "[{'iso_3166_1': 'FR', 'name': 'France'}]",
        "spoken_languages": "Français",
        "original_title": "Le Jouet",
        "original_language": "fr",
        "director": "Someone Else",
        "cast": "Someone,Else Entirely",
    }
    result = fill_extended_row(row, TMDB_RESPONSE)
    assert result["genres"] == "Family"
    assert result["production_companies"] == "Some Studio"
    assert result["production_countries"] == "[{'iso_3166_1': 'FR', 'name': 'France'}]"
    assert result["spoken_languages"] == "Français"
    assert result["original_title"] == "Le Jouet"
    assert result["original_language"] == "fr"
    assert result["director"] == "Someone Else"
    assert result["cast"] == "Someone,Else Entirely"


def test_enrich_fills_gaps_skips_complete_rows_and_leaves_unmatched_alone(monkeypatch):
    movies = pd.DataFrame(
        {
            "id": [1, 2, 3],
            "title": ["Needs Enrichment", "Already Complete", "Orphan"],
            "budget": [0, 500.0, 0],
            "revenue": [np.nan, 900.0, np.nan],
        }
    )
    extended = pd.DataFrame(
        {
            "id": [1, 2],  # id 3 has no extended row, same as the real corrupt-row shape
            "genres": [None, "Comedy"],
            # id 2 is genuinely complete in every dimension checked for
            # candidacy now, not just budget/revenue -- otherwise it'd be
            # re-fetched just for its missing director/original_title.
            "original_title": [None, "Already Complete"],
            "director": [None, "Some Director"],
        }
    )

    fetched_ids = []

    def fake_fetch(movie_id, api_key=None, session=None):
        fetched_ids.append(movie_id)
        if movie_id == 1:
            return {"budget": 1000, "revenue": 2000, "genres": [{"name": "Drama"}]}
        return None  # id 3: not found on TMDB

    # enrich() fetches via tmdb_client.fetch_movies_concurrently(), which
    # calls tmdb_client's own module-local fetch_movie -- patch it there,
    # not the (no longer imported) name in fill_missing's namespace.
    monkeypatch.setattr("scripts.enrichment.tmdb_client.fetch_movie", fake_fetch)

    result_movies, result_extended = enrich(movies, extended)

    # Only the 2 rows needing enrichment triggered a lookup -- id 2 was skipped.
    assert sorted(fetched_ids) == [1, 3]

    assert result_movies.loc[result_movies["id"] == 1, "budget"].iloc[0] == 1000
    assert result_movies.loc[result_movies["id"] == 1, "revenue"].iloc[0] == 2000
    assert result_extended.loc[result_extended["id"] == 1, "genres"].iloc[0] == "Drama"

    # Already-complete row untouched.
    assert result_movies.loc[result_movies["id"] == 2, "budget"].iloc[0] == 500.0

    # id 3 needed enrichment but has no extended row and no TMDB match --
    # should not raise, movies row stays as-is.
    assert result_movies.loc[result_movies["id"] == 3, "budget"].iloc[0] == 0


def test_enrich_refetches_rows_missing_only_director_or_original_title(monkeypatch):
    # budget/revenue already complete, but director/original_title are new
    # columns nothing has yet -- should still be treated as a candidate.
    movies = pd.DataFrame({"id": [1], "title": ["Complete Budget"], "budget": [500.0], "revenue": [900.0]})
    extended = pd.DataFrame({"id": [1], "genres": ["Comedy"]})

    monkeypatch.setattr(
        "scripts.enrichment.tmdb_client.fetch_movie",
        lambda movie_id, api_key=None, session=None: {
            "original_title": "Original", "credits": {"crew": [{"name": "Dir", "job": "Director"}], "cast": []}
        },
    )

    _, result_extended = enrich(movies, extended)
    assert result_extended.loc[result_extended["id"] == 1, "original_title"].iloc[0] == "Original"
    assert result_extended.loc[result_extended["id"] == 1, "director"].iloc[0] == "Dir"


def test_enrich_updates_extended_row_when_id_column_is_string_dtype(monkeypatch):
    # Regression test: movie_extended.csv's real `id` column loads as a
    # string dtype ('862' not 862), same corrupt-row cause as movies_main's
    # `id`/`budget`. Every extended.at[] write was previously a silent
    # no-op because extended_by_id was keyed by strings while movie_id
    # (from the numeric-coerced movies frame) is a plain int -- '862' != 862
    # as dict keys, so ext_idx was always None. This must not regress.
    movies = pd.DataFrame({"id": [862], "title": ["Toy Story"], "budget": [0], "revenue": [0]})
    extended = pd.DataFrame({"id": ["862"], "genres": [None]}).astype({"id": "string"})

    monkeypatch.setattr(
        "scripts.enrichment.tmdb_client.fetch_movie",
        lambda movie_id, api_key=None, session=None: {
            "budget": 30000000,
            "genres": [{"name": "Animation"}],
        },
    )

    result_movies, result_extended = enrich(movies, extended)
    assert result_movies.loc[0, "budget"] == 30000000
    assert result_extended.loc[0, "genres"] == "Animation"
