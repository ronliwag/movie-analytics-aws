"""Direct unit tests for scripts/pandas/clean_data.py's cleaning functions
-- see scripts/pandas/CLEANING.md for the decisions/evidence behind each
rule. Uses small hand-built DataFrames, not the real CSVs, so it's fast
and deterministic.

Run with: pytest scripts/pandas/test_clean_data.py -v
"""

import numpy as np
import pandas as pd

from scripts.pandas.clean_data import (
    _listcols_to_str,
    _parse_codes_and_names,
    _split_list,
    fix_dates,
    fix_missing_budget,
    remove_duplicates,
)


def test_split_list_trims_and_splits():
    assert _split_list("Animation,Comedy, Family") == ["Animation", "Comedy", "Family"]


def test_split_list_handles_null_and_empty():
    assert _split_list(np.nan) == []
    assert _split_list("") == []


def test_parse_codes_and_names_single_pass():
    raw = (
        "[{'iso_3166_1': 'US', 'name': 'United States of America'}, "
        "{'iso_3166_1': 'FR', 'name': 'France'}]"
    )
    codes, names = _parse_codes_and_names(raw, "iso_3166_1")
    assert codes == ["US", "FR"]
    assert names == ["United States of America", "France"]


def test_parse_codes_and_names_malformed_returns_empty():
    codes, names = _parse_codes_and_names("not a valid literal", "iso_3166_1")
    assert codes == []
    assert names == []


def test_parse_codes_and_names_null_returns_empty():
    codes, names = _parse_codes_and_names(np.nan, "iso_3166_1")
    assert codes == []
    assert names == []


def test_fix_dates_parses_all_three_formats():
    df = pd.DataFrame({"release_date": ["2012-03-22", "10/30/1995", "15-12-1995", "garbage"]})
    result = fix_dates(df)
    parsed = result["release_date"]
    assert parsed[0].strftime("%Y-%m-%d") == "2012-03-22"
    assert parsed[1].strftime("%Y-%m-%d") == "1995-10-30"
    assert parsed[2].strftime("%Y-%m-%d") == "1995-12-15"
    assert pd.isna(parsed[3])


def test_fix_missing_budget_converts_zero_to_null():
    df = pd.DataFrame({"budget": [0, 500.0], "revenue": [0, 900.0]})
    result = fix_missing_budget(df)
    assert pd.isna(result["budget"][0])
    assert result["budget"][1] == 500.0
    assert pd.isna(result["revenue"][0])
    assert result["revenue"][1] == 900.0


def test_remove_duplicates_collapses_formatting_noise():
    # Same movie, same date, once normalized -- should collapse to one row
    # without needing the completeness tiebreak.
    df = pd.DataFrame(
        {
            "id": [1, 1],
            "title": ["A Place at the Table", "A Place at the Table"],
            "release_date": [pd.Timestamp("2012-03-22"), pd.Timestamp("2012-03-22")],
            "budget": [np.nan, np.nan],
            "revenue": [np.nan, np.nan],
        }
    )
    result = remove_duplicates(df)
    assert len(result) == 1


def test_remove_duplicates_keeps_most_complete_row_on_genuine_conflict():
    # Identical except budget -- one copy has it, the other doesn't.
    df = pd.DataFrame(
        {
            "id": [1, 1],
            "title": ["Movie", "Movie"],
            "release_date": [pd.Timestamp("2020-01-01"), pd.Timestamp("2020-01-01")],
            "budget": [3.0e7, np.nan],
            "revenue": [3.3e7, 3.3e7],
        }
    )
    result = remove_duplicates(df)
    assert len(result) == 1
    assert result.iloc[0]["budget"] == 3.0e7


def test_remove_duplicates_handles_list_columns():
    # movie_extended-shaped input -- list columns aren't hashable, so this
    # exercises the tuple-cast comparison path.
    df = pd.DataFrame(
        {
            "id": [1, 1],
            "genres": [["Drama"], ["Drama"]],
            "production_companies": [[], ["Studio A"]],
        }
    )
    result = remove_duplicates(df)
    assert len(result) == 1
    assert result.iloc[0]["production_companies"] == ["Studio A"]


def test_listcols_to_str_comma_joins():
    df = pd.DataFrame({"genres": [["Drama", "Crime"]], "id": [1]})
    result = _listcols_to_str(df)
    assert result.iloc[0]["genres"] == "Drama,Crime"
