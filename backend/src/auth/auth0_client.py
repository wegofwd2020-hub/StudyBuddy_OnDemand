"""
backend/src/auth/auth0_client.py

Auth0 Management API client with Redis-cached token.

The management token has a 24h default TTL from Auth0.  We cache it for 23h
(1h safety buffer) so the same token is reused across all management calls in a
deployment rather than paying a ~200ms round-trip per call.

If a management call returns 401 (e.g. token rotated ahead of schedule), the
caller must evict the cache key and obtain a fresh token.  The helpers in this
module handle that retry automatically.

Usage:
  from src.auth.auth0_client import block_auth0_user, delete_auth0_user

  # Inside a FastAPI route:
  await block_auth0_user(auth0_sub, blocked=True, redis=request.app.state.redis)

  # Inside a Celery task (create your own connection):
  import redis.asyncio as aioredis
  redis = await aioredis.from_url(settings.REDIS_URL)
  try:
      await block_auth0_user(auth0_sub, blocked=True, redis=redis)
  finally:
      await redis.aclose()
"""

from __future__ import annotations

import httpx
from config import settings

from src.utils.logger import get_logger

log = get_logger("auth.auth0_client")

_MGMT_TOKEN_KEY = "auth0:mgmt_token"
_MGMT_TOKEN_TTL = 23 * 3600  # seconds — 1h buffer before Auth0's 24h expiry


async def get_management_token(redis) -> str:
    """
    Return a valid Auth0 Management API access token.

    1. Check Redis cache (key ``auth0:mgmt_token``).
    2. On cache miss: POST to Auth0 token endpoint and cache for 23h.

    The token is never logged.
    """
    cached = await redis.get(_MGMT_TOKEN_KEY)
    if cached:
        return cached.decode() if isinstance(cached, bytes) else cached

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            f"https://{settings.AUTH0_DOMAIN}/oauth/token",
            json={
                "grant_type": "client_credentials",
                "client_id": settings.AUTH0_MGMT_CLIENT_ID,
                "client_secret": settings.AUTH0_MGMT_CLIENT_SECRET,
                "audience": settings.AUTH0_MGMT_API_URL + "/",
            },
        )
        resp.raise_for_status()
        token: str = resp.json()["access_token"]

    await redis.set(_MGMT_TOKEN_KEY, token, ex=_MGMT_TOKEN_TTL)
    log.info("auth0_mgmt_token_refreshed")
    return token


async def _evict_token(redis) -> None:
    """Remove the cached management token so the next call fetches a fresh one."""
    await redis.delete(_MGMT_TOKEN_KEY)


async def block_auth0_user(auth0_sub: str, blocked: bool, redis) -> None:
    """
    Block or unblock an Auth0 user via the Management API.

    On HTTP 401 (stale cached token), evicts the cache and retries once.
    """
    user_id = auth0_sub.replace("|", "%7C")
    url = f"{settings.AUTH0_MGMT_API_URL}/users/{user_id}"

    for attempt in range(2):
        token = await get_management_token(redis)
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.patch(
                url,
                headers={"Authorization": f"Bearer {token}"},
                json={"blocked": blocked},
            )

        if resp.status_code == 401 and attempt == 0:
            log.warning("auth0_mgmt_token_stale_evicting", attempt=attempt)
            await _evict_token(redis)
            continue

        if resp.status_code not in (200, 204):
            log.error(
                "auth0_block_failed",
                auth0_sub=auth0_sub,
                blocked=blocked,
                status=resp.status_code,
            )
        return


async def delete_auth0_user(auth0_sub: str, redis) -> None:
    """
    Delete an Auth0 user (GDPR erasure) via the Management API.

    On HTTP 401 (stale cached token), evicts the cache and retries once.
    """
    user_id = auth0_sub.replace("|", "%7C")
    url = f"{settings.AUTH0_MGMT_API_URL}/users/{user_id}"

    for attempt in range(2):
        token = await get_management_token(redis)
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.delete(
                url,
                headers={"Authorization": f"Bearer {token}"},
            )

        if resp.status_code == 401 and attempt == 0:
            log.warning("auth0_mgmt_token_stale_evicting", attempt=attempt)
            await _evict_token(redis)
            continue

        if resp.status_code not in (200, 204):
            log.error(
                "auth0_delete_failed",
                auth0_sub=auth0_sub,
                status=resp.status_code,
            )
        return
