"""Tests for movielens_ratings.py -- uses small synthetic CSV fixtures,
not the real (multi-hundred-MB) MovieLens dump.

Run with: pytest scripts/enrichment/tests/test_movielens_ratings.py -v
"""

import math

import pandas as pd

from scripts.enrichment.movielens_ratings import (
    aggregate_ratings,
    build_movielens_index,
    fill_missing_ratings,
    load_links,
    resolve_existing_rating,
    resolve_ratings,
)


def test_load_links_drops_rows_with_no_tmdb_id(tmp_path):
    path = tmp_path / "links.csv"
    path.write_text("movieId,imdbId,tmdbId\n1,114709,862\n2,113497,\n")
    result = load_links(path)
    assert list(result["movieId"]) == [1]
    assert list(result["tmdbId"]) == [862]


def test_aggregate_ratings_computes_mean_count_std_max_timestamp(tmp_path):
    path = tmp_path / "ratings.csv"
    path.write_text(
        "userId,movieId,rating,timestamp\n"
        "1,1,4.0,1000\n"
        "2,1,5.0,2000\n"
        "3,2,3.0,1500\n"
    )
    result = aggregate_ratings(path).set_index("movieId")
    assert result.loc[1, "avg_rating"] == 4.5
    assert result.loc[1, "total_ratings"] == 2
    assert result.loc[1, "last_rated"] == 2000
    assert result.loc[2, "total_ratings"] == 1
    # Single rating -> undefined std, matching this dataset's own existing
    # convention for the same situation (see CLEANING.md's "NaN std_dev").
    assert math.isnan(result.loc[2, "std_dev"])


def test_build_movielens_index_maps_by_tmdb_id():
    links = pd.DataFrame({"movieId": [1, 2], "tmdbId": [862, 8844]})
    aggregated = pd.DataFrame(
        {
            "movieId": [1, 2],
            "avg_rating": [4.5, 3.0],
            "total_ratings": [2, 1],
            "std_dev": [0.707, float("nan")],
            "last_rated": [2000, 1500],
        }
    )
    index = build_movielens_index(links, aggregated)
    assert index[862]["avg_rating"] == 4.5
    assert index[862]["total_ratings"] == 2
    assert index[8844]["total_ratings"] == 1
    assert math.isnan(index[8844]["std_dev"])


def test_fill_missing_ratings_only_adds_ids_not_already_present():
    existing = [
        {
            "movie_id": 862,
            "ratings_summary": {"avg_rating": 9.9, "total_ratings": 1, "std_dev": None},
            "last_rated": 1,
        }
    ]
    movielens_index = {
        # Already exists -- must not be overwritten even though MovieLens
        # would compute a different value.
        862: {"avg_rating": 4.5, "total_ratings": 2, "std_dev": 0.7, "last_rated": 2000},
        # New -- no existing record for this id.
        8844: {"avg_rating": 3.0, "total_ratings": 1, "std_dev": float("nan"), "last_rated": 1500},
    }

    result = fill_missing_ratings(existing, movielens_index)

    assert len(result) == 2
    existing_862 = next(r for r in result if r["movie_id"] == 862)
    assert existing_862["ratings_summary"]["avg_rating"] == 9.9

    new_8844 = next(r for r in result if r["movie_id"] == 8844)
    assert new_8844["ratings_summary"]["avg_rating"] == 3.0
    assert new_8844["ratings_summary"]["total_ratings"] == 1
    assert new_8844["last_rated"] == 1500


def test_fill_missing_ratings_handles_no_new_ids():
    existing = [{"movie_id": 862, "ratings_summary": {}, "last_rated": 1}]
    result = fill_missing_ratings(existing, {})
    assert result == existing


def test_resolve_existing_rating_adopts_movielens_on_disagreement():
    record = {
        "movie_id": 862,
        "ratings_summary": {"avg_rating": 3.0, "total_ratings": 5, "std_dev": 0.5},
        "last_rated": 1000,
    }
    movielens_stats = {"avg_rating": 3.9, "total_ratings": 68997, "std_dev": 0.92, "last_rated": 1697144949}

    new_record, changes = resolve_existing_rating(record, movielens_stats)

    assert new_record["ratings_summary"] == {"avg_rating": 3.9, "total_ratings": 68997, "std_dev": 0.92}
    assert new_record["last_rated"] == 1697144949
    fields_changed = {c["field"] for c in changes}
    assert fields_changed == {"avg_rating", "total_ratings", "std_dev", "last_rated"}


def test_resolve_existing_rating_rejects_entire_correction_on_total_ratings_decrease():
    # Real pattern found in production: 247 -> 3 -- almost certainly a
    # links.csv movieId mismatch, not a genuine update. Must reject the
    # WHOLE record's correction, not just total_ratings, so it doesn't end
    # up with an old total_ratings paired with a freshly-computed
    # avg_rating from a different, much smaller sample.
    record = {
        "movie_id": 326305,
        "ratings_summary": {"avg_rating": 3.87, "total_ratings": 247, "std_dev": 0.96},
        "last_rated": 1475783711,
    }
    movielens_stats = {"avg_rating": 2.33, "total_ratings": 3, "std_dev": 0.76, "last_rated": 1570183000}

    new_record, changes = resolve_existing_rating(record, movielens_stats)

    assert changes == []
    assert new_record == record


def test_resolve_existing_rating_allows_correction_when_total_ratings_ties():
    record = {
        "movie_id": 862,
        "ratings_summary": {"avg_rating": 3.8, "total_ratings": 100, "std_dev": 0.9},
        "last_rated": 1000,
    }
    movielens_stats = {"avg_rating": 3.9, "total_ratings": 100, "std_dev": 0.92, "last_rated": 2000}

    new_record, changes = resolve_existing_rating(record, movielens_stats)

    assert new_record["ratings_summary"]["avg_rating"] == 3.9
    assert any(c["field"] == "avg_rating" for c in changes)


def test_resolve_existing_rating_allows_correction_when_existing_total_ratings_missing():
    # No baseline to compare against -- can't detect a "decrease", so the
    # correction should go through normally.
    record = {"movie_id": 862, "ratings_summary": {}, "last_rated": None}
    movielens_stats = {"avg_rating": 3.9, "total_ratings": 100, "std_dev": 0.5, "last_rated": 2000}

    new_record, changes = resolve_existing_rating(record, movielens_stats)

    assert new_record["ratings_summary"]["total_ratings"] == 100
    assert len(changes) > 0


def test_resolve_existing_rating_no_changes_when_values_agree():
    record = {
        "movie_id": 862,
        "ratings_summary": {"avg_rating": 3.9, "total_ratings": 100, "std_dev": 0.5},
        "last_rated": 1000,
    }
    movielens_stats = {"avg_rating": 3.9, "total_ratings": 100, "std_dev": 0.5, "last_rated": 1000}

    new_record, changes = resolve_existing_rating(record, movielens_stats)

    assert changes == []
    assert new_record == record


def test_resolve_existing_rating_nan_std_dev_on_both_sides_is_not_a_change():
    record = {
        "movie_id": 862,
        "ratings_summary": {"avg_rating": 5.0, "total_ratings": 1, "std_dev": float("nan")},
        "last_rated": 1000,
    }
    movielens_stats = {"avg_rating": 5.0, "total_ratings": 1, "std_dev": float("nan"), "last_rated": 1000}

    _, changes = resolve_existing_rating(record, movielens_stats)
    assert changes == []


def test_resolve_existing_rating_no_movielens_data_returns_record_unchanged():
    record = {"movie_id": 862, "ratings_summary": {"avg_rating": 3.9}, "last_rated": 1000}
    new_record, changes = resolve_existing_rating(record, None)
    assert changes == []
    assert new_record == record


def test_resolve_ratings_only_touches_records_with_movielens_data():
    existing = [
        {"movie_id": 1, "ratings_summary": {"avg_rating": 3.0, "total_ratings": 1, "std_dev": None}, "last_rated": 100},
        {"movie_id": 2, "ratings_summary": {"avg_rating": 4.0, "total_ratings": 1, "std_dev": None}, "last_rated": 200},
    ]
    movielens_index = {
        1: {"avg_rating": 3.9, "total_ratings": 500, "std_dev": 0.8, "last_rated": 999},
        # id 2 has no MovieLens match -- must stay untouched.
    }

    updated, changes = resolve_ratings(existing, movielens_index)

    assert updated[0]["ratings_summary"]["avg_rating"] == 3.9
    assert updated[1] == existing[1]
    assert all(c["movie_id"] == 1 for c in changes)
