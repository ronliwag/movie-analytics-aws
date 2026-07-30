"""Core data model classes for the movie analytics pipeline.

Implement Movie and Rating as plain Python classes (not dataclasses) to
practice constructors, instance methods, and type casting explicitly.
"""

from datetime import date


class Movie:
    def __init__(self, movie_id, title, release_date, budget, revenue):
        # TODO: store attributes, casting/parsing as needed (e.g. release_date
        # may arrive as a string in mixed formats — see week2 date parsing task).
        raise NotImplementedError

    @classmethod
    def from_dict(cls, data: dict) -> "Movie":
        # TODO: build a Movie from a raw dict row (e.g. from a CSV reader).
        raise NotImplementedError

    def profit(self) -> float:
        # TODO: revenue - budget, handling missing budget data.
        raise NotImplementedError


class Rating:
    def __init__(self, movie_id, source, metrics: dict):
        # TODO: `metrics` holds nested per-source rating summaries, e.g.
        # {"average": 7.2, "count": 1500, "breakdown": {...}}.
        raise NotImplementedError

    @classmethod
    def from_dict(cls, data: dict) -> "Rating":
        # TODO: build a Rating from a parsed ratings.json entry.
        raise NotImplementedError
