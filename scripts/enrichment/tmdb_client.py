"""Thin, rate-limited, disk-cached client for TMDB's /movie/{id} endpoint.

The dataset's own shape (poster-path strings in the corrupt rows,
iso_3166_1/iso_639_1 codes matching TMDB's exact response schema) indicates
this movie ids in this dataset ARE TMDB movie ids -- so enrichment is a
direct id lookup, not a fuzzy title match.

Caching makes a 45K-movie run resumable: if interrupted, re-running skips
every id already fetched instead of re-hitting the API for it.

fetch_movies_concurrently() runs many lookups in parallel via a thread
pool -- safe because each worker's real bottleneck is waiting on network
I/O (Python releases the GIL during that wait), and because every worker
shares one RateLimiter instance, so the actual request rate against TMDB
stays capped at MIN_REQUEST_INTERVAL_SECONDS regardless of thread count.
Concurrency here hides network latency; it does not bypass the rate limit.
"""

import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests
from dotenv import load_dotenv

from scripts.config import ENRICHED_DIR

load_dotenv()

TMDB_BASE_URL = "https://api.themoviedb.org/3"
CACHE_DIR = ENRICHED_DIR / "tmdb_cache"

# Aggregate cap across ALL worker threads combined (~20 req/sec) -- backed
# by the 429 handling below as a safety net if this turns out to be too
# aggressive for a given API key/tier.
MIN_REQUEST_INTERVAL_SECONDS = 0.05
DEFAULT_MAX_WORKERS = 10


class TMDBError(Exception):
    pass


class RateLimiter:
    """Thread-safe: ensures at most one request starts every `min_interval`
    seconds, no matter how many threads are calling wait() concurrently."""

    def __init__(self, min_interval: float):
        self.min_interval = min_interval
        self._lock = threading.Lock()
        self._last_call = 0.0

    def wait(self) -> None:
        if self.min_interval <= 0:
            return
        with self._lock:
            remaining = self.min_interval - (time.monotonic() - self._last_call)
            if remaining > 0:
                time.sleep(remaining)
            self._last_call = time.monotonic()


_rate_limiter = RateLimiter(MIN_REQUEST_INTERVAL_SECONDS)


def _cache_path(movie_id: int) -> Path:
    return CACHE_DIR / f"{movie_id}.json"


def fetch_movie(
    movie_id: int,
    api_key: str | None = None,
    session: "requests.Session | None" = None,
) -> dict | None:
    """Fetches TMDB's /movie/{id} response (with credits appended), using a
    local cache.

    Returns None if TMDB has no record for this id (404) -- a valid,
    expected outcome (not every id in this dataset is guaranteed to still
    exist on TMDB), not treated as an error.
    """
    cache_path = _cache_path(movie_id)
    if cache_path.exists():
        cached = json.loads(cache_path.read_text(encoding="utf-8"))
        # A cache entry from before `credits` was added lacks that key --
        # treat it as stale and re-fetch rather than requiring a manual
        # cache wipe. A cached 404 (None) has nothing to be stale about.
        if cached is None or "credits" in cached:
            return cached

    resolved_key = api_key or os.environ.get("TMDB_API_KEY")
    if not resolved_key:
        raise TMDBError(
            f"TMDB_API_KEY not set and no (fresh) cache entry for movie {movie_id} -- "
            "set TMDB_API_KEY to do a live lookup."
        )

    session = session or requests.Session()
    _rate_limiter.wait()
    response = session.get(
        f"{TMDB_BASE_URL}/movie/{movie_id}",
        params={"api_key": resolved_key, "append_to_response": "credits"},
        timeout=10,
    )

    if response.status_code == 404:
        _write_cache(movie_id, None)
        return None
    if response.status_code == 429:
        retry_after = int(response.headers.get("Retry-After", 5))
        time.sleep(retry_after)
        return fetch_movie(movie_id, api_key=resolved_key, session=session)

    response.raise_for_status()
    data = response.json()
    _write_cache(movie_id, data)
    return data


def _write_cache(movie_id: int, data: dict | None) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    _cache_path(movie_id).write_text(json.dumps(data), encoding="utf-8")


def fetch_movies_concurrently(
    movie_ids: list[int],
    max_workers: int = DEFAULT_MAX_WORKERS,
    api_key: str | None = None,
) -> dict[int, dict | None]:
    """Fetches many movies in parallel. One shared requests.Session for
    connection reuse across threads (requests.Session is documented as
    thread-safe for concurrent use)."""
    session = requests.Session()
    results: dict[int, dict | None] = {}

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(fetch_movie, movie_id, api_key, session): movie_id
            for movie_id in movie_ids
        }
        completed = 0
        for future in as_completed(futures):
            movie_id = futures[future]
            results[movie_id] = future.result()
            completed += 1
            if completed % 500 == 0:
                print(f"  fetched {completed}/{len(movie_ids)}")

    return results
