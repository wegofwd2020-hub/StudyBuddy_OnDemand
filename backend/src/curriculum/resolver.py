"""
backend/src/curriculum/resolver.py

Curriculum resolver dependency (Phase 9).

For every content request, resolves which curriculum_id to use for a student:

  1. Extract student_id, grade, school_id from JWT.
  2. Check L2 Redis cache: cur:{student_id} → curriculum_id (TTL 300 s).
  3. On cache miss, resolve from DB:
       a. If student has a school_id:
          - Look for an active curriculum for (school_id, grade, current_year).
          - If found and restrict_access=True: verify active enrolment; raise 403 if absent.
          - If found (or restrict_access=False): use school curriculum_id.
          - If not found: fall back to default.
       b. Otherwise: use default curriculum_id = default-{year}-g{grade}.
  4. Cache result in Redis (TTL 300 s).

Cache invalidated by:
  - PUT /curriculum/{curriculum_id}/activate  (school admin activates new curriculum)
  - Student school transfer
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import asyncpg
from fastapi import Depends, HTTPException, Request

from src.auth.dependencies import get_current_student
from src.core.cache_keys import cur_key, school_scan_pattern
from src.core.redis_client import get_redis
from src.utils.logger import get_logger

log = get_logger("curriculum.resolver")

_RESOLVER_TTL = 300  # 5 minutes


def _current_year() -> int:
    return datetime.now(UTC).year


def _default_curriculum_id(grade: int, year: int) -> str:
    return f"default-{year}-g{grade}"


async def _resolve_from_db(
    pool: asyncpg.Pool,
    student_id: str,
    grade: int,
    school_id: str | None,
) -> str:
    """Resolve curriculum_id from the database (no Redis)."""
    year = _current_year()

    # Path 1: school curriculum
    if school_id:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT curriculum_id, restrict_access
                FROM curricula
                WHERE school_id = $1 AND grade = $2 AND year = $3 AND status = 'active'
                ORDER BY activated_at DESC NULLS LAST
                LIMIT 1
                """,
                uuid.UUID(school_id),
                grade,
                year,
            )

            if not row:
                return _default_curriculum_id(grade, year)

            curriculum_id: str = row["curriculum_id"]
            restrict_access: bool = row["restrict_access"]

            if restrict_access:
                enrolment = await conn.fetchrow(
                    """
                    SELECT enrolment_id FROM school_enrolments
                    WHERE school_id = $1 AND student_id = $2 AND status = 'active'
                    """,
                    uuid.UUID(school_id),
                    uuid.UUID(student_id),
                )
                if not enrolment:
                    raise HTTPException(
                        status_code=403,
                        detail={
                            "error": "not_enrolled",
                            "detail": "Not enrolled in this school's curriculum.",
                        },
                    )

        return curriculum_id

    # Path 2: default platform curriculum
    return _default_curriculum_id(grade, year)


async def get_curriculum_id(
    request: Request,
    student: dict = Depends(get_current_student),
) -> str:
    """
    FastAPI dependency: resolves curriculum_id for the authenticated student.

    Returns a string curriculum_id.
    Raises 403 if the student is not enrolled in a restricted school curriculum.
    """
    student_id: str = str(student["student_id"])
    grade: int = student["grade"]
    school_id: str | None = student.get("school_id") and str(student["school_id"])

    redis = get_redis(request)
    cache_key = cur_key(student_id, school_id)

    raw = await redis.get(cache_key)
    if raw:
        return raw.decode() if isinstance(raw, bytes) else raw

    curriculum_id = await _resolve_from_db(request.app.state.pool, student_id, grade, school_id)

    await redis.setex(cache_key, _RESOLVER_TTL, curriculum_id)
    log.info(
        "curriculum_resolved", student_id=student_id, curriculum_id=curriculum_id, cached=False
    )
    return curriculum_id


async def invalidate_resolver_cache_for_school(
    redis,
    pool: asyncpg.Pool,
    school_id: str,
) -> int:
    """
    Invalidate all school:{school_id}:* Redis keys for a school.

    Uses the school-prefix SCAN (ADR-001 Decision 3) instead of enumerating
    enrolled students — faster and covers cur, ent, and any future school keys.

    Returns the count of invalidated keys.
    """
    pattern = school_scan_pattern(school_id)
    count = 0
    cursor = b"0"
    while True:
        cursor, keys = await redis.scan(cursor, match=pattern, count=200)
        if keys:
            await redis.delete(*keys)
            count += len(keys)
        if cursor == b"0" or cursor == 0:
            break

    log.info("resolver_cache_invalidated", school_id=school_id, keys_deleted=count)
    return count
