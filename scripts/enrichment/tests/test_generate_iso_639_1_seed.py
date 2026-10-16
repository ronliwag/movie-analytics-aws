"""Tests for generate_iso_639_1_seed.py -- pure lookup/CSV-writing logic,
no network involved (pycountry's data is bundled locally).

Run with: pytest scripts/enrichment/tests/test_generate_iso_639_1_seed.py -v
"""

import csv

import pytest

from scripts.enrichment.generate_iso_639_1_seed import (
    CODES,
    MANUAL_OVERRIDES,
    build_rows,
    main,
)


def test_build_rows_resolves_every_code():
    rows = build_rows()
    assert set(rows) == set(CODES)
    assert all(name for name in rows.values())


def test_build_rows_uses_manual_overrides():
    rows = build_rows()
    for code, name in MANUAL_OVERRIDES.items():
        assert rows[code] == name


def test_build_rows_prefers_pycountry_over_guessing():
    rows = build_rows()
    # Spot-check a few codes against pycountry's canonical wording rather
    # than a plausible-sounding but unverified name.
    assert rows["fr"] == "French"
    assert rows["ky"] == "Kirghiz"  # not "Kyrgyz" -- pycountry's exact term
    assert rows["ps"] == "Pushto"  # not "Pashto"


def test_tmdb_specific_codes_are_not_in_the_iso_seed():
    # cn (Cantonese) and xx (TMDB's "no language" placeholder) aren't real
    # ISO 639-1 codes -- dim_language.sql names them explicitly instead of
    # looking them up here.
    assert "cn" not in CODES
    assert "xx" not in CODES


def test_build_rows_raises_on_an_unresolvable_code(monkeypatch):
    monkeypatch.setattr(
        "scripts.enrichment.generate_iso_639_1_seed.CODES", ["en", "zz"]
    )
    with pytest.raises(RuntimeError, match="zz"):
        build_rows()


def test_main_writes_a_sorted_deduplicated_csv(tmp_path, monkeypatch):
    seed_path = tmp_path / "iso_639_1.csv"
    monkeypatch.setattr(
        "scripts.enrichment.generate_iso_639_1_seed.SEED_PATH", seed_path
    )

    main()

    with open(seed_path, newline="") as f:
        reader = csv.reader(f)
        header = next(reader)
        rows = list(reader)

    assert header == ["code", "name"]
    assert len(rows) == len(CODES)
    codes_written = [row[0] for row in rows]
    assert codes_written == sorted(codes_written)
    assert codes_written == sorted(set(CODES))
