"""Tests for the TMDB client's caching, 404, and rate-limit/retry behavior.
Mocks the HTTP layer entirely -- no real network calls, no real API key
needed to run these.

Run with: pytest scripts/enrichment/tests/test_tmdb_client.py -v
"""

import json
import time
from unittest.mock import MagicMock

import pytest

from scripts.enrichment import tmdb_client


@pytest.fixture(autouse=True)
def isolated_cache(tmp_path, monkeypatch):
    # Every test gets its own empty cache dir instead of touching
    # data/enriched/tmdb_cache.
    monkeypatch.setattr(tmdb_client, "CACHE_DIR", tmp_path)
    # Disable rate limiting -- it's a shared module-level instance, so
    # without this, tests would incur real (if small) sleeps and could
    # interact with each other's timing.
    monkeypatch.setattr(tmdb_client, "_rate_limiter", tmdb_client.RateLimiter(0))


def _mock_session(status_code=200, json_data=None, headers=None):
    session = MagicMock()
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = json_data or {}
    response.headers = headers or {}
    response.raise_for_status = MagicMock()
    session.get.return_value = response
    return session


def test_fetch_movie_returns_data_on_success():
    session = _mock_session(200, {"id": 862, "budget": 30000000})
    result = tmdb_client.fetch_movie(862, api_key="fake-key", session=session)
    assert result == {"id": 862, "budget": 30000000}
    session.get.assert_called_once()


def test_fetch_movie_caches_result_to_disk(tmp_path):
    session = _mock_session(200, {"id": 862, "budget": 30000000})
    tmdb_client.fetch_movie(862, api_key="fake-key", session=session)
    cache_file = tmp_path / "862.json"
    assert cache_file.exists()
    assert json.loads(cache_file.read_text()) == {"id": 862, "budget": 30000000}


def test_fetch_movie_uses_cache_without_hitting_session():
    cache_path = tmdb_client.CACHE_DIR / "862.json"
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    # Must include "credits" -- a fresh cache entry, not a stale pre-credits
    # one (see test_fetch_movie_refetches_stale_cache_entry_without_credits).
    cache_path.write_text(json.dumps({"id": 862, "budget": 999, "credits": {}}))

    session = _mock_session()
    result = tmdb_client.fetch_movie(862, api_key="fake-key", session=session)
    assert result == {"id": 862, "budget": 999, "credits": {}}
    session.get.assert_not_called()


def test_fetch_movie_refetches_stale_cache_entry_without_credits():
    # A cache entry from before `credits` was added -- should be treated as
    # stale and re-fetched, not requiring a manual cache wipe.
    cache_path = tmdb_client.CACHE_DIR / "862.json"
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps({"id": 862, "budget": 999}))

    session = _mock_session(200, {"id": 862, "budget": 999, "credits": {"cast": []}})
    result = tmdb_client.fetch_movie(862, api_key="fake-key", session=session)

    session.get.assert_called_once()
    assert result == {"id": 862, "budget": 999, "credits": {"cast": []}}
    assert json.loads(cache_path.read_text()) == {"id": 862, "budget": 999, "credits": {"cast": []}}


def test_fetch_movie_cached_404_is_not_treated_as_stale():
    # A cached None (404) has nothing to be stale about -- must not
    # trigger a re-fetch attempt.
    cache_path = tmdb_client.CACHE_DIR / "999999.json"
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(None))

    session = _mock_session()
    result = tmdb_client.fetch_movie(999999, api_key="fake-key", session=session)
    assert result is None
    session.get.assert_not_called()


def test_fetch_movie_requests_credits_via_append_to_response():
    session = _mock_session(200, {"id": 862, "credits": {}})
    tmdb_client.fetch_movie(862, api_key="fake-key", session=session)
    _, kwargs = session.get.call_args
    assert kwargs["params"]["append_to_response"] == "credits"


def test_fetch_movie_returns_none_and_caches_on_404():
    session = _mock_session(404)
    result = tmdb_client.fetch_movie(999999, api_key="fake-key", session=session)
    assert result is None
    cache_file = tmdb_client.CACHE_DIR / "999999.json"
    assert cache_file.exists()
    assert json.loads(cache_file.read_text()) is None


def test_fetch_movie_retries_after_429():
    response_429 = MagicMock(status_code=429, headers={"Retry-After": "0"})
    response_200 = MagicMock(status_code=200, headers={})
    response_200.json.return_value = {"id": 862, "budget": 1}
    session = MagicMock()
    session.get.side_effect = [response_429, response_200]

    result = tmdb_client.fetch_movie(862, api_key="fake-key", session=session)
    assert result == {"id": 862, "budget": 1}
    assert session.get.call_count == 2


def test_fetch_movie_raises_without_api_key_on_cache_miss(monkeypatch):
    # Explicitly clear it -- the real .env may have a real key loaded into
    # the environment by the time the full suite runs (other modules call
    # load_dotenv() at import time), which would mask this fallback path.
    monkeypatch.delenv("TMDB_API_KEY", raising=False)
    with pytest.raises(tmdb_client.TMDBError):
        tmdb_client.fetch_movie(862, api_key=None, session=_mock_session())


def test_rate_limiter_spaces_out_calls():
    limiter = tmdb_client.RateLimiter(min_interval=0.05)
    start = time.monotonic()
    limiter.wait()
    limiter.wait()
    limiter.wait()
    elapsed = time.monotonic() - start
    # 3 calls, 2 gaps of ~0.05s each -- allow generous slack for CI jitter.
    assert elapsed >= 0.08


def test_rate_limiter_disabled_when_zero():
    limiter = tmdb_client.RateLimiter(min_interval=0)
    start = time.monotonic()
    for _ in range(50):
        limiter.wait()
    assert time.monotonic() - start < 0.05


def test_fetch_movies_concurrently_fetches_all_ids(monkeypatch):
    def fake_fetch(movie_id, api_key=None, session=None):
        return {"id": movie_id, "budget": movie_id * 10}

    monkeypatch.setattr(tmdb_client, "fetch_movie", fake_fetch)

    results = tmdb_client.fetch_movies_concurrently([1, 2, 3], max_workers=3)

    assert results == {1: {"id": 1, "budget": 10}, 2: {"id": 2, "budget": 20}, 3: {"id": 3, "budget": 30}}


def test_fetch_movies_concurrently_preserves_none_results(monkeypatch):
    monkeypatch.setattr(tmdb_client, "fetch_movie", lambda movie_id, api_key=None, session=None: None)

    results = tmdb_client.fetch_movies_concurrently([1, 2], max_workers=2)

    assert results == {1: None, 2: None}
