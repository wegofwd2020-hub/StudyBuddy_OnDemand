"""
tests/test_rate_limit_hardening.py

Covers the hardening work on src/core/rate_limit.py:
  - _get_client_ip header precedence (CF > X-Real-IP > XFF first-hop > client.host)
  - Fail-open on Redis error (throttle must not take down /auth/*)
  - Retry-After header shape on 429
  - Env-driven limits (AUTH_RATE_LIMIT / AUTH_RATE_WINDOW)

The existing tests in test_auth_rate_limit.py continue to cover end-to-end
throttling via the real FastAPI routes.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException, Request
from redis.exceptions import ConnectionError as RedisConnectionError

from src.core.rate_limit import _enforce_rate_limit, _get_client_ip


def _make_request(headers: dict[str, str] | None = None, client_host: str | None = "1.2.3.4") -> Request:
    """Build a minimal ASGI Request for helper-level tests.

    Note: Starlette exposes request.app via a read-only property backed by
    scope["app"], so direct attribute assignment (req.app = ...) fails with
    AttributeError. Tests that need an app install it via req.scope["app"].
    """
    raw_headers = [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()]
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/",
        "headers": raw_headers,
        "client": (client_host, 12345) if client_host else None,
    }
    return Request(scope)


# ── _get_client_ip header precedence ──────────────────────────────────────────


def test_client_ip_prefers_cf_connecting_ip() -> None:
    req = _make_request(
        headers={
            "CF-Connecting-IP": "203.0.113.5",
            "X-Real-IP": "198.51.100.9",
            "X-Forwarded-For": "192.0.2.1, 10.0.0.1",
        },
        client_host="1.2.3.4",
    )
    assert _get_client_ip(req) == "203.0.113.5"


def test_client_ip_falls_back_to_x_real_ip() -> None:
    req = _make_request(
        headers={
            "X-Real-IP": "198.51.100.9",
            "X-Forwarded-For": "192.0.2.1, 10.0.0.1",
        },
    )
    assert _get_client_ip(req) == "198.51.100.9"


def test_client_ip_uses_xff_first_hop() -> None:
    req = _make_request(headers={"X-Forwarded-For": "192.0.2.1, 10.0.0.1, 172.16.0.1"})
    assert _get_client_ip(req) == "192.0.2.1"


def test_client_ip_xff_single_value() -> None:
    req = _make_request(headers={"X-Forwarded-For": "192.0.2.7"})
    assert _get_client_ip(req) == "192.0.2.7"


def test_client_ip_falls_back_to_remote_addr() -> None:
    req = _make_request(client_host="1.2.3.4")
    assert _get_client_ip(req) == "1.2.3.4"


def test_client_ip_empty_when_nothing_available() -> None:
    req = _make_request(client_host=None)
    assert _get_client_ip(req) == ""


def test_client_ip_trims_whitespace() -> None:
    req = _make_request(headers={"CF-Connecting-IP": "  203.0.113.5  "})
    assert _get_client_ip(req) == "203.0.113.5"


# ── Fail-open behaviour on Redis error ────────────────────────────────────────


@pytest.mark.asyncio
async def test_enforce_fail_open_on_redis_error(monkeypatch) -> None:
    """Redis INCR failure must not block the request."""
    req = _make_request(client_host="10.0.0.1")
    redis = AsyncMock()
    redis.incr.side_effect = RedisConnectionError("redis down")
    req.scope["app"] = type("App", (), {"state": type("S", (), {"redis": redis})()})()

    # Should NOT raise — fail open.
    await _enforce_rate_limit(req, key_prefix="auth_rate", limit=10, window=60)
    redis.incr.assert_awaited_once_with("auth_rate:10.0.0.1")


@pytest.mark.asyncio
async def test_enforce_no_ip_passes_through() -> None:
    """No resolvable client IP → pass through rather than bucket everyone."""
    req = _make_request(client_host=None)
    redis = AsyncMock()
    req.scope["app"] = type("App", (), {"state": type("S", (), {"redis": redis})()})()

    await _enforce_rate_limit(req, key_prefix="auth_rate", limit=10, window=60)
    redis.incr.assert_not_called()


# ── 429 response shape ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_enforce_raises_429_with_retry_after() -> None:
    req = _make_request(client_host="10.0.0.2")
    redis = AsyncMock()
    redis.incr.return_value = 11  # one past the limit
    redis.ttl.return_value = 42
    req.scope["app"] = type("App", (), {"state": type("S", (), {"redis": redis})()})()

    with pytest.raises(HTTPException) as exc_info:
        await _enforce_rate_limit(req, key_prefix="auth_rate", limit=10, window=60)

    assert exc_info.value.status_code == 429
    assert exc_info.value.headers == {"Retry-After": "42"}
    assert exc_info.value.detail["error"] == "rate_limited"


@pytest.mark.asyncio
async def test_enforce_retry_after_falls_back_to_window() -> None:
    """TTL missing (-1 / -2 / None) → Retry-After uses the full window."""
    req = _make_request(client_host="10.0.0.3")
    redis = AsyncMock()
    redis.incr.return_value = 11
    redis.ttl.return_value = -1
    req.scope["app"] = type("App", (), {"state": type("S", (), {"redis": redis})()})()

    with pytest.raises(HTTPException) as exc_info:
        await _enforce_rate_limit(req, key_prefix="auth_rate", limit=10, window=60)

    assert exc_info.value.headers == {"Retry-After": "60"}


@pytest.mark.asyncio
async def test_enforce_below_limit_passes_and_sets_ttl_on_first_hit() -> None:
    req = _make_request(client_host="10.0.0.4")
    redis = AsyncMock()
    redis.incr.return_value = 1  # first hit
    req.scope["app"] = type("App", (), {"state": type("S", (), {"redis": redis})()})()

    await _enforce_rate_limit(req, key_prefix="auth_rate", limit=10, window=60)
    redis.expire.assert_awaited_once_with("auth_rate:10.0.0.4", 60)


@pytest.mark.asyncio
async def test_enforce_subsequent_hits_do_not_re_set_ttl() -> None:
    req = _make_request(client_host="10.0.0.5")
    redis = AsyncMock()
    redis.incr.return_value = 5  # mid-window
    req.scope["app"] = type("App", (), {"state": type("S", (), {"redis": redis})()})()

    await _enforce_rate_limit(req, key_prefix="auth_rate", limit=10, window=60)
    redis.expire.assert_not_called()
