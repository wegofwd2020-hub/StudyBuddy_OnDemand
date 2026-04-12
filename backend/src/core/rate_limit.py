"""
backend/src/core/rate_limit.py

FastAPI `Depends()` dependencies for IP-based rate limiting via Redis.

Implemented as dependencies (not slowapi decorators) to avoid the known
FastAPI + slowapi + Pydantic v2 incompatibility where @limiter.limit breaks
body parameter introspection on async handlers.

State lives in shared Redis so limits are enforced across all workers.

Limits:
  AUTH_LIMIT  — 10 requests per 60 s per IP on all auth token/login endpoints.
"""
from __future__ import annotations

from fastapi import HTTPException, Request

from src.core.redis_client import get_redis

_AUTH_LIMIT = 10
_AUTH_WINDOW = 60  # seconds

_HELP_LIMIT = 10
_HELP_WINDOW = 60  # seconds


async def ip_help_rate_limit(request: Request) -> None:
    """
    FastAPI dependency: raise HTTP 429 if this IP has exceeded 10 help-ask
    requests within the past 60 seconds.

    Usage::

        @router.post("/help/ask")
        async def handler(
            request: Request,
            body: HelpAskRequest,
            _: None = Depends(ip_help_rate_limit),
        ): ...
    """
    redis = get_redis(request)
    ip = request.client.host if request.client else "unknown"
    key = f"help_rate:{ip}"

    count = await redis.incr(key)
    if count == 1:
        await redis.expire(key, _HELP_WINDOW)

    if count > _HELP_LIMIT:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "rate_limited",
                "detail": "Too many requests. Please try again later.",
            },
        )


async def ip_auth_rate_limit(request: Request) -> None:
    """
    FastAPI dependency: raise HTTP 429 if this IP has exceeded 10 auth
    requests within the past 60 seconds.

    Uses a Redis INCR + EXPIRE counter.  The counter is keyed by client IP so
    it is shared across requests but scoped per-IP (not per-endpoint).

    Usage::

        @router.post("/auth/exchange")
        async def handler(
            body: ...,
            request: Request,
            _: None = Depends(ip_auth_rate_limit),
        ): ...
    """
    redis = get_redis(request)
    ip = request.client.host if request.client else "unknown"
    key = f"auth_rate:{ip}"

    count = await redis.incr(key)
    if count == 1:
        # First request in this window — set the expiry.
        await redis.expire(key, _AUTH_WINDOW)

    if count > _AUTH_LIMIT:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "rate_limited",
                "detail": "Too many requests. Please try again later.",
            },
        )
