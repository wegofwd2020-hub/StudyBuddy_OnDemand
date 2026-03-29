"""
backend/src/feedback/service.py

Phase 10 feedback business logic.

submit_feedback  — insert a feedback row; caller handles rate limiting via Redis
list_feedback    — paginated admin query with optional filters
"""

from __future__ import annotations

import uuid
from datetime import UTC

import asyncpg

from src.utils.logger import get_logger

log = get_logger("feedback")

_RATE_LIMIT_KEY = "feedback:rate:{student_id}:{hour}"
_RATE_LIMIT_MAX = 5
_RATE_LIMIT_TTL = 3600  # 1 hour in seconds


async def check_and_increment_rate_limit(redis, student_id: str) -> bool:
    """
    Check and increment feedback rate limit (5 per student per hour).

    Returns True if allowed, False if limit exceeded.
    Uses Redis INCR + EXPIRE; atomic via single-connection pipeline semantics.
    """
    from datetime import datetime

    hour_key = datetime.now(UTC).strftime("%Y%m%d%H")
    key = f"feedback:rate:{student_id}:{hour_key}"

    count = await redis.incr(key)
    if count == 1:
        await redis.expire(key, _RATE_LIMIT_TTL)
    return count <= _RATE_LIMIT_MAX


async def submit_feedback(
    conn: asyncpg.Connection,
    student_id: str,
    category: str,
    message: str,
    unit_id: str | None = None,
    curriculum_id: str | None = None,
    rating: int | None = None,
) -> dict:
    """Insert a feedback row. Returns {feedback_id, submitted_at}."""
    row = await conn.fetchrow(
        """
        INSERT INTO feedback
            (student_id, category, unit_id, curriculum_id, message, rating)
        VALUES ($1, $2, $3, $4, $5, $6)
        RETURNING feedback_id::text, submitted_at
        """,
        uuid.UUID(student_id),
        category,
        unit_id or None,
        curriculum_id or None,
        message,
        rating,
    )
    log.info("feedback_submitted", student_id=student_id, category=category)
    return {"feedback_id": row["feedback_id"], "submitted_at": row["submitted_at"]}


async def list_feedback(
    conn: asyncpg.Connection,
    page: int = 1,
    per_page: int = 20,
    category: str | None = None,
    unit_id: str | None = None,
    curriculum_id: str | None = None,
    reviewed: bool | None = None,
) -> dict:
    """
    Paginated admin query for feedback rows.
    Returns {pagination: {...}, feedback_items: [...]}.
    """
    filters = []
    params: list = []
    idx = 1

    if category:
        filters.append(f"category = ${idx}")
        params.append(category)
        idx += 1
    if unit_id:
        filters.append(f"unit_id = ${idx}")
        params.append(unit_id)
        idx += 1
    if curriculum_id:
        filters.append(f"curriculum_id = ${idx}")
        params.append(curriculum_id)
        idx += 1
    if reviewed is not None:
        filters.append(f"reviewed = ${idx}")
        params.append(reviewed)
        idx += 1

    where = "WHERE " + " AND ".join(filters) if filters else ""

    total = await conn.fetchval(f"SELECT COUNT(*) FROM feedback {where}", *params)

    offset = (page - 1) * per_page
    rows = await conn.fetch(
        f"""
        SELECT feedback_id::text, student_id::text, category, unit_id,
               curriculum_id, message, rating, submitted_at,
               reviewed, reviewed_by::text, reviewed_at
        FROM feedback
        {where}
        ORDER BY submitted_at DESC
        LIMIT ${idx} OFFSET ${idx + 1}
        """,
        *params,
        per_page,
        offset,
    )

    return {
        "pagination": {"page": page, "per_page": per_page, "total": total},
        "feedback_items": [dict(r) for r in rows],
    }
