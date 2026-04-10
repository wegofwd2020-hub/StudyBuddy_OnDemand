"""
tests/test_auth0_client.py

Tests for src/auth/auth0_client.py:
  - get_management_token(): cache hit, cache miss, token stored with 23h TTL
  - block_auth0_user(): success (200/204), non-401 error logged, 401 evicts cache and retries
  - delete_auth0_user(): same 401 evict-and-retry coverage

All external HTTP calls are mocked via unittest.mock.  Redis is provided by
fakeredis so no real Redis process is required.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import fakeredis.aioredis as fakeredis
import pytest

from src.auth.auth0_client import (
    _MGMT_TOKEN_KEY,
    _MGMT_TOKEN_TTL,
    block_auth0_user,
    delete_auth0_user,
    get_management_token,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
async def redis():
    """In-process fake Redis — no external process needed."""
    client = fakeredis.FakeRedis()
    yield client
    await client.aclose()


def _mock_token_response(token: str = "fresh-mgmt-token") -> MagicMock:
    """Build an httpx-like POST response that returns an access_token."""
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json.return_value = {"access_token": token}
    return resp


def _mock_http_response(status_code: int) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    return resp


# ── get_management_token ──────────────────────────────────────────────────────


async def test_get_management_token_cache_miss_fetches_and_stores(redis):
    """On cache miss the token endpoint is called and the result is cached."""
    with patch("src.auth.auth0_client.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client.post.return_value = _mock_token_response("token-abc")

        token = await get_management_token(redis)

    assert token == "token-abc"
    mock_client.post.assert_awaited_once()
    # Token must be stored in Redis with the correct TTL.
    cached = await redis.get(_MGMT_TOKEN_KEY)
    assert cached == b"token-abc"
    ttl = await redis.ttl(_MGMT_TOKEN_KEY)
    assert 0 < ttl <= _MGMT_TOKEN_TTL


async def test_get_management_token_cache_hit_skips_http(redis):
    """On cache hit the token is returned directly without any HTTP call."""
    await redis.set(_MGMT_TOKEN_KEY, "cached-token", ex=_MGMT_TOKEN_TTL)

    with patch("src.auth.auth0_client.httpx.AsyncClient") as mock_client_cls:
        token = await get_management_token(redis)
        mock_client_cls.assert_not_called()

    assert token == "cached-token"


async def test_get_management_token_not_logged(redis):
    """The token value must never appear in log output (CODING_RULES §2)."""
    with patch("src.auth.auth0_client.httpx.AsyncClient") as mock_client_cls, \
         patch("src.auth.auth0_client.log") as mock_log:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client.post.return_value = _mock_token_response("secret-token-xyz")

        await get_management_token(redis)

    # Ensure the secret token value doesn't appear in any log call args.
    for call in mock_log.mock_calls:
        assert "secret-token-xyz" not in str(call)


# ── block_auth0_user ──────────────────────────────────────────────────────────


async def test_block_auth0_user_success_204(redis):
    """A 204 response is treated as success — no error logged."""
    await redis.set(_MGMT_TOKEN_KEY, "good-token", ex=_MGMT_TOKEN_TTL)

    with patch("src.auth.auth0_client.httpx.AsyncClient") as mock_client_cls, \
         patch("src.auth.auth0_client.log") as mock_log:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client.patch.return_value = _mock_http_response(204)

        await block_auth0_user("auth0|abc123", blocked=True, redis=redis)

    mock_log.error.assert_not_called()
    # Cache key must still be present (not evicted on success).
    assert await redis.get(_MGMT_TOKEN_KEY) is not None


async def test_block_auth0_user_non_401_error_logs_and_returns(redis):
    """A non-401 error status is logged but does not evict the cache or retry."""
    await redis.set(_MGMT_TOKEN_KEY, "good-token", ex=_MGMT_TOKEN_TTL)

    with patch("src.auth.auth0_client.httpx.AsyncClient") as mock_client_cls, \
         patch("src.auth.auth0_client.log") as mock_log:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client.patch.return_value = _mock_http_response(500)

        await block_auth0_user("auth0|abc123", blocked=True, redis=redis)

    mock_log.error.assert_called_once()
    # Only one HTTP attempt — no retry on non-401.
    assert mock_client.patch.await_count == 1


async def test_block_auth0_user_401_evicts_and_retries(redis):
    """
    A 401 response evicts the cached token and fetches a fresh one.
    The second attempt uses the new token.
    """
    await redis.set(_MGMT_TOKEN_KEY, "stale-token", ex=_MGMT_TOKEN_TTL)

    fresh_token_resp = _mock_token_response("fresh-token")

    with patch("src.auth.auth0_client.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        # First PATCH → 401; token POST → fresh token; second PATCH → 204.
        mock_client.patch.side_effect = [
            _mock_http_response(401),
            _mock_http_response(204),
        ]
        mock_client.post.return_value = fresh_token_resp

        await block_auth0_user("auth0|abc123", blocked=True, redis=redis)

    assert mock_client.patch.await_count == 2
    # The second PATCH must use the fresh token.
    second_call_headers = mock_client.patch.call_args_list[1].kwargs["headers"]
    assert second_call_headers["Authorization"] == "Bearer fresh-token"


async def test_block_auth0_user_encodes_pipe_in_sub(redis):
    """The `|` in an Auth0 sub must be percent-encoded in the URL."""
    await redis.set(_MGMT_TOKEN_KEY, "tok", ex=_MGMT_TOKEN_TTL)

    with patch("src.auth.auth0_client.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client.patch.return_value = _mock_http_response(200)

        await block_auth0_user("auth0|user123", blocked=False, redis=redis)

    url_called = mock_client.patch.call_args.args[0]
    assert "%7C" in url_called
    assert "|" not in url_called


# ── delete_auth0_user ─────────────────────────────────────────────────────────


async def test_delete_auth0_user_success_204(redis):
    await redis.set(_MGMT_TOKEN_KEY, "good-token", ex=_MGMT_TOKEN_TTL)

    with patch("src.auth.auth0_client.httpx.AsyncClient") as mock_client_cls, \
         patch("src.auth.auth0_client.log") as mock_log:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client.delete.return_value = _mock_http_response(204)

        await delete_auth0_user("auth0|del456", redis=redis)

    mock_log.error.assert_not_called()


async def test_delete_auth0_user_401_evicts_and_retries(redis):
    await redis.set(_MGMT_TOKEN_KEY, "stale", ex=_MGMT_TOKEN_TTL)

    with patch("src.auth.auth0_client.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client.delete.side_effect = [
            _mock_http_response(401),
            _mock_http_response(204),
        ]
        mock_client.post.return_value = _mock_token_response("new-token")

        await delete_auth0_user("auth0|del456", redis=redis)

    assert mock_client.delete.await_count == 2
    second_call_headers = mock_client.delete.call_args_list[1].kwargs["headers"]
    assert second_call_headers["Authorization"] == "Bearer new-token"
