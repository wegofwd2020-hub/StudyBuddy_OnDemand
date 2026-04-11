"""
backend/src/school/limits_service.py

School limits resolution and override management.

Resolution order (per-field):
  1. school_plan_overrides row (nullable — NULL means "use plan default")
  2. Plan defaults from settings env vars

The school's active plan is read from school_subscriptions; if no subscription
exists, 'starter' is used as the fallback plan.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import asyncpg

from src.utils.logger import get_logger

log = get_logger("school.limits")


def _plan_defaults(plan: str) -> dict:
    """Return plan-level limit defaults using settings env vars."""
    from config import settings

    mapping = {
        "starter": {
            "max_students": settings.school_seats_starter_students,
            "max_teachers": settings.school_seats_starter_teachers,
            "pipeline_quota": settings.SCHOOL_PIPELINE_QUOTA_STARTER,
        },
        "professional": {
            "max_students": settings.school_seats_professional_students,
            "max_teachers": settings.school_seats_professional_teachers,
            "pipeline_quota": settings.SCHOOL_PIPELINE_QUOTA_PROFESSIONAL,
        },
        "enterprise": {
            "max_students": settings.school_seats_enterprise_students,
            "max_teachers": settings.school_seats_enterprise_teachers,
            "pipeline_quota": settings.SCHOOL_PIPELINE_QUOTA_ENTERPRISE,
        },
    }
    return mapping.get(plan, mapping["starter"])


async def resolve_school_limits(
    conn: asyncpg.Connection,
    school_id: str,
    plan: str,
) -> dict:
    """
    Return {max_students, max_teachers, pipeline_quota} for a school.

    Checks school_plan_overrides first; falls back per-field to plan defaults.
    """
    override = await conn.fetchrow(
        "SELECT max_students, max_teachers, pipeline_quota FROM school_plan_overrides WHERE school_id = $1",
        uuid.UUID(school_id),
    )
    defaults = _plan_defaults(plan)

    return {
        "max_students": (
            override["max_students"]
            if override and override["max_students"] is not None
            else defaults["max_students"]
        ),
        "max_teachers": (
            override["max_teachers"]
            if override and override["max_teachers"] is not None
            else defaults["max_teachers"]
        ),
        "pipeline_quota": (
            override["pipeline_quota"]
            if override and override["pipeline_quota"] is not None
            else defaults["pipeline_quota"]
        ),
    }


async def get_school_plan(conn: asyncpg.Connection, school_id: str) -> str:
    """Return the school's active subscription plan, defaulting to 'starter'."""
    row = await conn.fetchrow(
        """
        SELECT plan FROM school_subscriptions
        WHERE school_id = $1 AND status IN ('active', 'trialing', 'past_due')
        """,
        uuid.UUID(school_id),
    )
    return row["plan"] if row else "starter"


async def get_pipeline_runs_this_month(conn: asyncpg.Connection, school_id: str) -> int:
    """Count pipeline jobs triggered for a school in the current calendar month."""
    count = await conn.fetchval(
        """
        SELECT COUNT(*) FROM pipeline_jobs
        WHERE school_id = $1
          AND triggered_at >= date_trunc('month', NOW())
        """,
        uuid.UUID(school_id),
    )
    return int(count or 0)


def _pipeline_resets_at() -> str:
    """Return ISO timestamp for the first instant of next month (UTC)."""
    now = datetime.now(UTC)
    if now.month == 12:
        reset = now.replace(year=now.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        reset = now.replace(month=now.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0)
    return reset.isoformat()


async def get_school_limits_view(
    conn: asyncpg.Connection,
    school_id: str,
    include_override_detail: bool = False,
) -> dict:
    """
    Build the full limits view for a school.

    include_override_detail=True adds the raw override row for admin endpoints.
    """
    plan = await get_school_plan(conn, school_id)
    limits = await resolve_school_limits(conn, school_id, plan)
    pipeline_runs = await get_pipeline_runs_this_month(conn, school_id)

    student_count = await conn.fetchval(
        "SELECT COUNT(*) FROM school_enrolments WHERE school_id = $1 AND status = 'active'",
        uuid.UUID(school_id),
    )
    teacher_count = await conn.fetchval(
        "SELECT COUNT(*) FROM teachers WHERE school_id = $1 AND account_status = 'active'",
        uuid.UUID(school_id),
    )

    override_row = await conn.fetchrow(
        """
        SELECT max_students, max_teachers, pipeline_quota, override_reason,
               set_by_admin_id::text, set_at
        FROM school_plan_overrides
        WHERE school_id = $1
        """,
        uuid.UUID(school_id),
    )
    has_override = override_row is not None

    result: dict = {
        "plan": plan,
        "max_students": limits["max_students"],
        "max_teachers": limits["max_teachers"],
        "pipeline_quota_monthly": limits["pipeline_quota"],
        "pipeline_runs_this_month": pipeline_runs,
        "pipeline_resets_at": _pipeline_resets_at(),
        "seats_used_students": int(student_count or 0),
        "seats_used_teachers": int(teacher_count or 0),
        "has_override": has_override,
    }

    if include_override_detail:
        result["override"] = (
            {
                "max_students": override_row["max_students"],
                "max_teachers": override_row["max_teachers"],
                "pipeline_quota": override_row["pipeline_quota"],
                "override_reason": override_row["override_reason"],
                "set_by_admin_id": override_row["set_by_admin_id"],
                "set_at": override_row["set_at"].isoformat() if override_row["set_at"] else None,
            }
            if override_row
            else None
        )

    return result


async def set_school_limits_override(
    conn: asyncpg.Connection,
    school_id: str,
    admin_id: str,
    max_students: int | None,
    max_teachers: int | None,
    pipeline_quota: int | None,
    override_reason: str,
) -> dict:
    """
    Upsert school_plan_overrides for a school.

    Returns {old_override, new_override} for audit log.
    """
    old_row = await conn.fetchrow(
        "SELECT max_students, max_teachers, pipeline_quota, override_reason FROM school_plan_overrides WHERE school_id = $1",
        uuid.UUID(school_id),
    )
    old_override = dict(old_row) if old_row else None

    await conn.execute(
        """
        INSERT INTO school_plan_overrides
            (school_id, max_students, max_teachers, pipeline_quota, override_reason, set_by_admin_id, set_at)
        VALUES ($1, $2, $3, $4, $5, $6, NOW())
        ON CONFLICT (school_id) DO UPDATE SET
            max_students    = EXCLUDED.max_students,
            max_teachers    = EXCLUDED.max_teachers,
            pipeline_quota  = EXCLUDED.pipeline_quota,
            override_reason = EXCLUDED.override_reason,
            set_by_admin_id = EXCLUDED.set_by_admin_id,
            set_at          = NOW()
        """,
        uuid.UUID(school_id),
        max_students,
        max_teachers,
        pipeline_quota,
        override_reason,
        uuid.UUID(admin_id),
    )

    log.info(
        "school_limits_override_set school_id=%s admin_id=%s", school_id, admin_id
    )
    return {
        "old_override": old_override,
        "new_override": {
            "max_students": max_students,
            "max_teachers": max_teachers,
            "pipeline_quota": pipeline_quota,
            "override_reason": override_reason,
        },
    }


async def clear_school_limits_override(
    conn: asyncpg.Connection,
    school_id: str,
    admin_id: str,
) -> dict | None:
    """
    Delete school_plan_overrides row for a school.

    Returns the cleared override for audit log, or None if nothing was cleared.
    """
    old_row = await conn.fetchrow(
        "SELECT max_students, max_teachers, pipeline_quota, override_reason FROM school_plan_overrides WHERE school_id = $1",
        uuid.UUID(school_id),
    )
    if old_row is None:
        return None

    await conn.execute(
        "DELETE FROM school_plan_overrides WHERE school_id = $1",
        uuid.UUID(school_id),
    )

    log.info(
        "school_limits_override_cleared school_id=%s admin_id=%s", school_id, admin_id
    )
    return dict(old_row)
