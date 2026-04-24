"""
backend/src/core/rate_limit.py

FastAPI `Depends()` dependencies for IP-based rate limiting via Redis.

Implemented as dependencies (not slowapi decorators) to avoid the known
FastAPI + slowapi + Pydantic v2 incompatibility where @limiter.limit breaks
body parameter introspection on async handlers.

State lives in shared Redis so limits are enforced across all workers.

Posture:
  - Client IP is resolved via the standard reverse-proxy header chain
    (CF-Connecting-IP → X-Real-IP → X-Forwarded-For → request.client.host).
    Behind Cloudflare this keeps per-user throttling intact; without a
    trusted proxy header the whole fleet would bucket under the edge IP.
  - Redis errors fail *open* — the limiter is a safety net, not an auth
    layer. A Redis hiccup must not take down /auth/*. The limiter logs
    and lets the request through.
  - Windows and limits are env-driven so ops can tighten credential-stuffing
    defences at the edge without a code change.
"""

from __future__ import annotations

from config import settings
from fastapi import HTTPException, Request
from redis.exceptions import RedisError

from src.core.redis_client import get_redis
from src.utils.logger import get_logger

log = get_logger("rate_limit")


def _get_client_ip(request: Request) -> str:
    """Resolve the client IP from proxy headers with direct-connection fallback.

    Order matters: CF-Connecting-IP is overwritten by Cloudflare per request
    and cannot be spoofed by the client; the other headers can be, so they're
    only trusted as a best-effort fallback when CF isn't fronting.
    """
    cf = request.headers.get("cf-connecting-ip")
    if cf:
        return cf.strip()
    xri = request.headers.get("x-real-ip")
    if xri:
        return xri.strip()
    xff = request.headers.get("x-forwarded-for")
    if xff:
        # XFF is "client, proxy1, proxy2" — first hop is the originating client.
        first = xff.split(",", 1)[0].strip()
        if first:
            return first
    if request.client and request.client.host:
        return request.client.host
    return ""


async def _enforce_rate_limit(
    request: Request,
    *,
    key_prefix: str,
    limit: int,
    window: int,
) -> None:
    """Shared Redis fixed-window counter enforcement.

    Raises HTTP 429 (with Retry-After) once count exceeds `limit` within
    `window` seconds. On Redis error: logs and returns (fail open).
    """
    ip = _get_client_ip(request)
    if not ip:
        # No usable IP — throttling would bucket every misconfigured request
        # into one noisy key. Better to pass through than to take the site
        # down for anyone behind a broken proxy.
        return

    redis = get_redis(request)
    key = f"{key_prefix}:{ip}"

    try:
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, window)
    except RedisError as exc:
        log.warning("rate_limit_redis_error", key=key, error=str(exc))
        return

    if count > limit:
        try:
            ttl = await redis.ttl(key)
            retry_after = ttl if isinstance(ttl, int) and ttl > 0 else window
        except RedisError:
            retry_after = window
        raise HTTPException(
            status_code=429,
            detail={
                "error": "rate_limited",
                "detail": "Too many requests. Please try again later.",
            },
            headers={"Retry-After": str(retry_after)},
        )


async def ip_help_rate_limit(request: Request) -> None:
    """FastAPI dependency: throttle help-ask endpoint by client IP.

    Usage::

        @router.post("/help/ask")
        async def handler(
            request: Request,
            body: HelpAskRequest,
            _: None = Depends(ip_help_rate_limit),
        ): ...
    """
    await _enforce_rate_limit(
        request,
        key_prefix="help_rate",
        limit=settings.HELP_RATE_LIMIT,
        window=settings.HELP_RATE_WINDOW,
    )


async def ip_auth_rate_limit(request: Request) -> None:
    """FastAPI dependency: throttle auth endpoints by client IP.

    The counter is keyed by resolved client IP so it is shared across auth
    endpoints and enforced per-IP (not per-endpoint).

    Usage::

        @router.post("/auth/exchange")
        async def handler(
            body: ...,
            request: Request,
            _: None = Depends(ip_auth_rate_limit),
        ): ...
    """
    await _enforce_rate_limit(
        request,
        key_prefix="auth_rate",
        limit=settings.AUTH_RATE_LIMIT,
        window=settings.AUTH_RATE_WINDOW,
    )
