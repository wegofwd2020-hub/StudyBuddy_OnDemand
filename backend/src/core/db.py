"""
backend/src/core/db.py

Database connection helper.

Provides get_db() context manager that acquires a connection from app.state.pool
(asyncpg connection pool). Pool is created once per worker in the FastAPI lifespan.

Layer rule: every service module imports from here — never creates its own pool.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import asyncpg
from fastapi import Request


@asynccontextmanager
async def get_db(request: Request) -> AsyncGenerator[asyncpg.Connection, None]:
    """
    Acquire a connection from the asyncpg pool on app.state.

    Usage:
        async with get_db(request) as conn:
            row = await conn.fetchrow("SELECT ...")
    """
    async with request.app.state.pool.acquire() as conn:
        yield conn
