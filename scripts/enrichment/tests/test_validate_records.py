"""Tests for validate_records.py's pure comparison/correction logic -- no
HTTP involved, since resolve_movie_row operates on plain dicts (a row plus
an already-fetched TMDB response).

Run with: pytest scripts/enrichment/tests/test_validate_records.py -v
"""

import pandas as pd

from scripts.enrichment.validate_records import resolve, resolve_movie_row

TMDB_RESPONSE = {
    "budget": 30000000,
    "revenue": 373554033,
    "title": "Toy Story",
    "original_title": "Toy Story",
    "release_date": "1995-11-22",
}


def test_no_changes_when_values_agree():
    row = {
        "budget": 30000000,
        "revenue": 373554033,
        "title": "Toy Story",
        "release_date": "1995-11-22",
    }
    new_row, changes = resolve_movie_row(row, TMDB_RESPONSE)
    assert changes == []
    assert new_row == row


def test_corrects_budget_mismatch():
    row = {"budget": 25000000, "revenue": 373554033, "title": "Toy Story", "release_date": "1995-11-22"}
    new_row, changes = resolve_movie_row(row, TMDB_RESPONSE)
    assert changes == [{"field": "budget", "existing": 25000000, "tmdb": 30000000}]
    assert new_row["budget"] == 30000000


def test_corrects_title_mismatch():
    row = {"budget": 30000000, "revenue": 373554033, "title": "Toy Story 2", "release_date": "1995-11-22"}
    new_row, changes = resolve_movie_row(row, TMDB_RESPONSE)
    assert any(c["field"] == "title" for c in changes)
    assert new_row["title"] == "Toy Story"


def test_does_not_correct_title_matching_original_title():
    # This dataset stores the original-language title; TMDB's `title` is a
    # later English release title -- should NOT be flagged/overwritten.
    row = {"budget": 30000000, "revenue": 373554033, "title": "Le Bonheur", "release_date": "1995-11-22"}
    tmdb_data = {**TMDB_RESPONSE, "title": "Happiness", "original_title": "Le Bonheur"}
    new_row, changes = resolve_movie_row(row, tmdb_data)
    assert not any(c["field"] == "title" for c in changes)
    assert new_row["title"] == "Le Bonheur"


def test_corrects_release_date_mismatch_across_formats():
    row = {"budget": 30000000, "revenue": 373554033, "title": "Toy Story", "release_date": "11/23/1995"}
    new_row, changes = resolve_movie_row(row, TMDB_RESPONSE)
    assert any(c["field"] == "release_date" for c in changes)
    assert new_row["release_date"] == "1995-11-22"


def test_does_not_correct_release_date_when_formats_differ_but_date_agrees():
    row = {"budget": 30000000, "revenue": 373554033, "title": "Toy Story", "release_date": "22-11-1995"}
    new_row, changes = resolve_movie_row(row, TMDB_RESPONSE)
    assert not any(c["field"] == "release_date" for c in changes)
    assert new_row["release_date"] == "22-11-1995"


def test_skips_field_missing_on_either_side():
    # revenue missing from the existing row, budget missing from TMDB --
    # neither should be touched since there's nothing to compare.
    row = {"budget": 30000000, "revenue": None, "title": "Toy Story", "release_date": "1995-11-22"}
    tmdb_data = {**TMDB_RESPONSE, "budget": 0}
    new_row, changes = resolve_movie_row(row, tmdb_data)
    assert not any(c["field"] in ("budget", "revenue") for c in changes)
    assert new_row["budget"] == 30000000
    assert new_row["revenue"] is None


def test_no_tmdb_data_returns_row_unchanged():
    row = {"budget": 30000000, "revenue": 373554033, "title": "Toy Story", "release_date": "1995-11-22"}
    new_row, changes = resolve_movie_row(row, None)
    assert changes == []
    assert new_row == row


def test_resolve_only_calls_tmdb_for_rows_with_an_id_and_writes_corrections(monkeypatch):
    movies = pd.DataFrame(
        {
            "id": [1, None, 3],
            "title": ["Movie One", None, "Movie Three"],
            "budget": [500, 0, 999],
            "revenue": [900, 0, 999],
            "release_date": ["2020-01-01", None, "2021-01-01"],
        }
    )

    fetched_ids = []

    def fake_fetch(movie_id, api_key=None, session=None):
        fetched_ids.append(movie_id)
        if movie_id == 1:
            return {"budget": 999, "revenue": 900, "title": "Movie One", "release_date": "2020-01-01"}
        return {"budget": 999, "revenue": 999, "title": "Movie Three", "release_date": "2021-01-01"}

    # resolve() fetches via tmdb_client.fetch_movies_concurrently(), which
    # calls tmdb_client's own module-local fetch_movie -- patch it there,
    # not the (no longer imported) name in validate_records's namespace.
    monkeypatch.setattr("scripts.enrichment.tmdb_client.fetch_movie", fake_fetch)

    updated_movies, report = resolve(movies)

    assert sorted(fetched_ids) == [1, 3]  # the NaN-id row was skipped
    assert list(report[report["id"] == 1]["field"]) == ["budget"]
    assert updated_movies.loc[updated_movies["id"] == 1, "budget"].iloc[0] == 999
    # id 3 had no mismatches -- no report rows, values unchanged.
    assert len(report[report["id"] == 3]) == 0
    assert updated_movies.loc[updated_movies["id"] == 3, "budget"].iloc[0] == 999
