"""Core data model classes for the movie analytics pipeline.

Implement Movie and Rating as plain Python classes (not dataclasses) to
practice constructors, instance methods, and type casting explicitly.
"""

import math
from datetime import date, datetime, timezone

from scripts.pandas.data_processor import standardize_date


class Movie:
    def __init__(self, movie_id, title, release_date, budget, revenue):
        self.movie_id = int(movie_id)
        self.title = title.strip() if isinstance(title, str) else title
        self.release_date = self._parse_date(release_date)
        self.budget = self._parse_amount(budget)
        self.revenue = self._parse_amount(revenue)

    @staticmethod
    def _parse_date(value):
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        if isinstance(value, float) and math.isnan(value):
            return None
        parsed = standardize_date(str(value))
        return parsed.date() if parsed else None

    @staticmethod
    def _parse_amount(value):
        # 0 is this dataset's "not reported" convention, not a real $0 --
        # kept consistent with clean_data.py's fix_missing_budget() (see
        # CLEANING.md's "Missing budget/revenue" section).
        if value is None:
            return None
        try:
            value = float(value)
        except (TypeError, ValueError):
            return None
        if math.isnan(value) or value == 0:
            return None
        return value

    @classmethod
    def from_dict(cls, data: dict) -> "Movie":
        return cls(
            movie_id=data.get("id", data.get("movie_id")),
            title=data.get("title"),
            release_date=data.get("release_date"),
            budget=data.get("budget"),
            revenue=data.get("revenue"),
        )

    def profit(self) -> float | None:
        if self.budget is None or self.revenue is None:
            return None
        return self.revenue - self.budget


class Rating:
    def __init__(self, movie_id, source, metrics: dict):
        self.movie_id = int(movie_id)
        self.source = source
        self.metrics = dict(metrics)

    @classmethod
    def from_dict(cls, data: dict) -> "Rating":
        metrics = dict(data.get("ratings_summary", {}))
        if data.get("last_rated") is not None:
            metrics["last_rated"] = datetime.fromtimestamp(
                data["last_rated"], tz=timezone.utc
            )
        return cls(movie_id=data["movie_id"], source="ratings_summary", metrics=metrics)

    @property
    def avg_rating(self):
        return self.metrics.get("avg_rating")

    @property
    def total_ratings(self):
        return self.metrics.get("total_ratings")

    @property
    def std_dev(self):
        # NaN for single-rating movies (undefined statistic) -- same
        # NaN -> None decision as clean_data.py's load_ratings().
        value = self.metrics.get("std_dev")
        if isinstance(value, float) and math.isnan(value):
            return None
        return value
