"""
backend/src/core/db.py

Database connection helper.

Provides get_db() context manager that acquires a connection from app.state.pool
(asyncpg connection pool). Pool is created once per worker in the FastAPI lifespan.

Layer rule: every service module imports from here — never creates its own pool.

RLS tenant context
------------------
Before yielding the connection, get_db() stamps the PostgreSQL session variable
`app.current_school_id` so that Row-Level Security policies (migration 0028) can
scope every query to the correct school.

  request.state.rls_school_id  — set by get_current_teacher() after JWT verify
                                  (contains the teacher's school_id UUID string)

If rls_school_id is absent or None (student, admin, unauthenticated, webhook
paths) the value is set to 'bypass', which satisfies the RLS USING clause for
all rows and effectively disables the filter for that request.

On connection release the variable is reset to '' so stale values never leak
to the next borrower of the same pooled connection.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import asyncpg
from fastapi import Request


@asynccontextmanager
async def get_db(request: Request) -> AsyncGenerator[asyncpg.Connection, None]:
    """
    Acquire a connection from the asyncpg pool on app.state and stamp the
    RLS session variable before yielding.

    Usage:
        async with get_db(request) as conn:
            row = await conn.fetchrow("SELECT ...")
    """
    school_id: str = getattr(request.state, "rls_school_id", None) or "bypass"
    async with request.app.state.pool.acquire() as conn:
        await conn.execute(
            "SELECT set_config('app.current_school_id', $1, false)", school_id
        )
        try:
            yield conn
        finally:
            try:
                await conn.execute(
                    "SELECT set_config('app.current_school_id', '', false)"
                )
            except Exception:
                pass
