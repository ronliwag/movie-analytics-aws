"""Dictionary-based data processing utilities.

Practice: dictionaries, datetime parsing, casting, for loops, lambdas,
JSON handling, and file handling with proper error handling.
"""

import json
from datetime import datetime
from pathlib import Path

# release_date in movies_main.csv mixes three formats with no stray values
# (verified against the real data -- see scripts/pandas/CLEANING.md):
# ISO YYYY-MM-DD, MM/DD/YYYY, and DD-MM-YYYY. "%B %d, %Y" is kept as an extra
# fallback for the docstring's "May 14, 2021" example / other sources.
_KNOWN_DATE_FORMATS = ["%Y-%m-%d", "%m/%d/%Y", "%d-%m-%Y", "%B %d, %Y"]


def load_json(path: Path) -> dict | list:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"No such file: {path}") from None
    except json.JSONDecodeError as e:
        raise ValueError(f"Malformed JSON in {path}: {e}") from e


def standardize_date(raw_date: str) -> datetime | None:
    """Parse a release date that may arrive in multiple formats.

    e.g. "2021-05-14", "05/14/2021", "May 14, 2021".
    """
    if raw_date is None:
        return None
    raw_date = str(raw_date).strip()
    if not raw_date:
        return None

    for fmt in _KNOWN_DATE_FORMATS:
        try:
            return datetime.strptime(raw_date, fmt)
        except ValueError:
            continue
    return None


def index_by_movie_id(records: list[dict]) -> dict:
    """Build a {movie_id: record} lookup dict for batch joins."""
    index = {}
    for record in records:
        movie_id = record.get("movie_id", record.get("id"))
        index[movie_id] = record
    return index


def apply_transform(records: list[dict], transform) -> list[dict]:
    """Apply a lambda/callable transform to each record."""
    return [transform(record) for record in records]
