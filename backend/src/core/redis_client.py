"""
backend/src/core/redis_client.py

Redis connection helper.

get_redis() returns the aioredis pool stored on app.state.redis.
Pool is created once per worker in the FastAPI lifespan.
"""

from __future__ import annotations

from fastapi import Request
from redis.asyncio import Redis


def get_redis(request: Request) -> Redis:
    """
    Return the aioredis client stored on app.state.

    The client is thread-safe and manages its own connection pool.

    Usage:
        redis = get_redis(request)
        await redis.set("key", "value", ex=300)
    """
    return request.app.state.redis
