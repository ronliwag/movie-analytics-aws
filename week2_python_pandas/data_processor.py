"""Dictionary-based data processing utilities.

Practice: dictionaries, datetime parsing, casting, for loops, lambdas,
JSON handling, and file handling with proper error handling.
"""

import json
from datetime import datetime
from pathlib import Path


def load_json(path: Path) -> dict:
    # TODO: proper file handling — open with a context manager, handle
    # FileNotFoundError / json.JSONDecodeError.
    raise NotImplementedError


def standardize_date(raw_date: str) -> datetime | None:
    """Parse a release date that may arrive in multiple formats.

    e.g. "2021-05-14", "05/14/2021", "May 14, 2021".
    """
    # TODO: try known formats in order, return None if all fail.
    raise NotImplementedError


def index_by_movie_id(records: list[dict]) -> dict:
    """Build a {movie_id: record} lookup dict for batch joins."""
    # TODO: use a for loop (or dict comprehension) to index records.
    raise NotImplementedError


def apply_transform(records: list[dict], transform) -> list[dict]:
    """Apply a lambda/callable transform to each record."""
    # TODO: use map()/lambda or a list comprehension.
    raise NotImplementedError
