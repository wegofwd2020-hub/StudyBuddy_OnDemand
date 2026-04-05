"""
backend/src/private_teacher/service.py

Business logic for private teacher subscriptions and student-teacher access.
"""

from __future__ import annotations

import json
import uuid

import asyncpg
from config import settings
from src.utils.logger import get_logger

log = get_logger("private_teacher")

_ENT_TEACHER_ACCESS_KEY = "ent:teacher_access:{student_id}"
_ENT_TEACHER_ACCESS_TTL = 300


# ── Teacher CRUD ──────────────────────────────────────────────────────────────


async def register_private_teacher(
    conn: asyncpg.Connection,
    email: str,
    name: str,
    password_hash: str,
) -> dict:
    """Insert a new private_teacher row. Raises ValueError('email_taken') on duplicate."""
    try:
        row = await conn.fetchrow(
            """
            INSERT INTO private_teachers (email, name, password_hash)
            VALUES ($1, $2, $3)
            RETURNING teacher_id::text, email, name, account_status::text,
                      created_at
            """,
            email,
            name,
            password_hash,
        )
    except asyncpg.UniqueViolationError:
        raise ValueError("email_taken")

    return dict(row)


async def get_private_teacher_by_email(
    conn: asyncpg.Connection,
    email: str,
) -> dict | None:
    row = await conn.fetchrow(
        """
        SELECT teacher_id::text, email, name, password_hash, account_status::text,
               created_at
        FROM private_teachers
        WHERE email = $1
        """,
        email,
    )
    return dict(row) if row else None


async def get_private_teacher_by_id(
    conn: asyncpg.Connection,
    teacher_id: str,
) -> dict | None:
    row = await conn.fetchrow(
        """
        SELECT teacher_id::text, email, name, account_status::text, created_at
        FROM private_teachers
        WHERE teacher_id = $1
        """,
        uuid.UUID(teacher_id),
    )
    return dict(row) if row else None


# ── Subscription helpers ──────────────────────────────────────────────────────


def _teacher_plan_limits(plan: str) -> dict:
    if plan == "pro":
        return {
            "pipeline_quota_monthly": settings.PRIVATE_TEACHER_PLAN_PRO_PIPELINE_QUOTA,
            "max_students": settings.PRIVATE_TEACHER_PLAN_PRO_MAX_STUDENTS,
        }
    # default to basic
    return {
        "pipeline_quota_monthly": settings.PRIVATE_TEACHER_PLAN_BASIC_PIPELINE_QUOTA,
        "max_students": settings.PRIVATE_TEACHER_PLAN_BASIC_MAX_STUDENTS,
    }


async def get_teacher_subscription_status(
    conn: asyncpg.Connection,
    teacher_id: str,
) -> dict:
    row = await conn.fetchrow(
        """
        SELECT plan, status, pipeline_quota_monthly, pipeline_runs_this_month,
               pipeline_resets_at, current_period_end
        FROM teacher_subscriptions
        WHERE teacher_id = $1
        """,
        uuid.UUID(teacher_id),
    )
    if not row:
        return {
            "plan": None,
            "status": None,
            "pipeline_quota_monthly": 0,
            "pipeline_runs_this_month": 0,
            "pipeline_resets_at": None,
            "max_students": 0,
            "current_period_end": None,
        }

    limits = _teacher_plan_limits(row["plan"])
    return {
        "plan": row["plan"],
        "status": row["status"],
        "pipeline_quota_monthly": row["pipeline_quota_monthly"],
        "pipeline_runs_this_month": row["pipeline_runs_this_month"],
        "pipeline_resets_at": (
            row["pipeline_resets_at"].isoformat() if row["pipeline_resets_at"] else None
        ),
        "max_students": limits["max_students"],
        "current_period_end": (
            row["current_period_end"].isoformat() if row["current_period_end"] else None
        ),
    }


async def create_teacher_checkout_session(
    teacher_id: str,
    plan: str,
    success_url: str,
    cancel_url: str,
) -> str:
    """Create a Stripe Checkout Session for teacher subscription. Returns checkout_url."""
    if not settings.STRIPE_SECRET_KEY:
        raise RuntimeError("Stripe not configured")

    price_id = (
        settings.STRIPE_PRIVATE_TEACHER_PRICE_PRO_ID
        if plan == "pro"
        else settings.STRIPE_PRIVATE_TEACHER_PRICE_BASIC_ID
    )
    if not price_id:
        raise RuntimeError(f"Stripe price ID for plan '{plan}' not configured")

    try:
        import stripe  # type: ignore
    except ImportError:
        raise RuntimeError("stripe package not installed")

    stripe.api_key = settings.STRIPE_SECRET_KEY
    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{"price": price_id, "quantity": 1}],
        mode="subscription",
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={"teacher_id": teacher_id, "plan": plan},
    )
    return session["url"]


async def activate_teacher_subscription(
    conn: asyncpg.Connection,
    redis,
    teacher_id: str,
    plan: str,
    stripe_customer_id: str,
    stripe_subscription_id: str,
    current_period_end,
) -> None:
    limits = _teacher_plan_limits(plan)
    await conn.execute(
        """
        INSERT INTO teacher_subscriptions
            (teacher_id, plan, status, stripe_customer_id, stripe_subscription_id,
             pipeline_quota_monthly, current_period_end)
        VALUES ($1, $2, 'active', $3, $4, $5, $6)
        ON CONFLICT (teacher_id) DO UPDATE
            SET plan                   = EXCLUDED.plan,
                status                 = 'active',
                stripe_customer_id     = EXCLUDED.stripe_customer_id,
                stripe_subscription_id = EXCLUDED.stripe_subscription_id,
                pipeline_quota_monthly = EXCLUDED.pipeline_quota_monthly,
                current_period_end     = EXCLUDED.current_period_end,
                updated_at             = NOW()
        """,
        uuid.UUID(teacher_id),
        plan,
        stripe_customer_id,
        stripe_subscription_id,
        limits["pipeline_quota_monthly"],
        current_period_end,
    )
    # Expire entitlement caches for all students linked to this teacher
    await _expire_student_caches_for_teacher(conn, redis, teacher_id)
    log.info("teacher_subscription_activated", teacher_id=teacher_id, plan=plan)


async def update_teacher_subscription_status(
    conn: asyncpg.Connection,
    redis,
    stripe_subscription_id: str,
    status: str,
    current_period_end,
) -> None:
    row = await conn.fetchrow(
        """
        UPDATE teacher_subscriptions
        SET status = $2, current_period_end = $3, updated_at = NOW()
        WHERE stripe_subscription_id = $1
        RETURNING teacher_id::text
        """,
        stripe_subscription_id,
        status,
        current_period_end,
    )
    if row:
        await _expire_student_caches_for_teacher(conn, redis, row["teacher_id"])


async def cancel_teacher_subscription_db(
    conn: asyncpg.Connection,
    redis,
    stripe_subscription_id: str,
) -> None:
    row = await conn.fetchrow(
        """
        UPDATE teacher_subscriptions
        SET status = 'cancelled', updated_at = NOW()
        WHERE stripe_subscription_id = $1
        RETURNING teacher_id::text
        """,
        stripe_subscription_id,
    )
    if row:
        await _expire_student_caches_for_teacher(conn, redis, row["teacher_id"])


async def handle_teacher_payment_failed(
    conn: asyncpg.Connection,
    redis,
    stripe_subscription_id: str,
) -> None:
    row = await conn.fetchrow(
        """
        UPDATE teacher_subscriptions
        SET status = 'past_due', updated_at = NOW()
        WHERE stripe_subscription_id = $1
        RETURNING teacher_id::text
        """,
        stripe_subscription_id,
    )
    if row:
        await _expire_student_caches_for_teacher(conn, redis, row["teacher_id"])


async def _expire_student_caches_for_teacher(
    conn: asyncpg.Connection,
    redis,
    teacher_id: str,
) -> None:
    """Expire ent:teacher_access:{student_id} and cur:{student_id} for all linked students."""
    rows = await conn.fetch(
        """
        SELECT student_id::text FROM student_teacher_access
        WHERE teacher_id = $1
        """,
        uuid.UUID(teacher_id),
    )
    for row in rows:
        sid = row["student_id"]
        await redis.delete(f"ent:teacher_access:{sid}")
        await redis.delete(f"cur:{sid}")


# ── Entitlement check for students ───────────────────────────────────────────


async def get_teacher_entitlement_for_student(
    student_id: str,
    pool: asyncpg.Pool,
    redis,
) -> dict | None:
    """
    Return entitlement dict if the student has active teacher access, else None.

    Checks Redis cache first (key: ent:teacher_access:{student_id}).
    """
    cache_key = f"ent:teacher_access:{student_id}"
    raw = await redis.get(cache_key)
    if raw is not None:
        data = json.loads(raw.decode() if isinstance(raw, bytes) else raw)
        return data if data.get("active") else None

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT sta.valid_until, ts.plan
            FROM student_teacher_access sta
            JOIN teacher_subscriptions ts ON ts.teacher_id = sta.teacher_id
            WHERE sta.student_id = $1
              AND sta.status = 'active'
              AND ts.status IN ('active', 'trialing', 'past_due')
            LIMIT 1
            """,
            uuid.UUID(student_id),
        )

    if not row:
        await redis.setex(
            cache_key, _ENT_TEACHER_ACCESS_TTL, json.dumps({"active": False})
        )
        return None

    result = {
        "active": True,
        "plan": "teacher_access",
        "lessons_accessed": 0,
        "valid_until": row["valid_until"].isoformat() if row["valid_until"] else None,
    }
    await redis.setex(cache_key, _ENT_TEACHER_ACCESS_TTL, json.dumps(result))
    return result


# ── Available teachers (student discovery) ────────────────────────────────────


async def get_available_teachers(conn: asyncpg.Connection) -> list[dict]:
    rows = await conn.fetch(
        """
        SELECT pt.teacher_id::text,
               pt.name AS teacher_name,
               COUNT(c.curriculum_id) AS curricula_count
        FROM private_teachers pt
        JOIN teacher_subscriptions ts
            ON ts.teacher_id = pt.teacher_id
           AND ts.status IN ('active', 'trialing')
        LEFT JOIN curricula c
            ON c.owner_type = 'teacher'
           AND c.owner_id = pt.teacher_id
           AND c.status = 'active'
        WHERE pt.account_status = 'active'
        GROUP BY pt.teacher_id, pt.name
        ORDER BY pt.name
        """
    )
    return [dict(r) for r in rows]


# ── Student-teacher access ────────────────────────────────────────────────────


async def get_student_teacher_access_status(
    conn: asyncpg.Connection,
    student_id: str,
    teacher_id: str,
) -> dict | None:
    row = await conn.fetchrow(
        """
        SELECT access_id::text, student_id::text, teacher_id::text,
               status, stripe_customer_id, stripe_subscription_id,
               valid_until, created_at, updated_at
        FROM student_teacher_access
        WHERE student_id = $1 AND teacher_id = $2
        """,
        uuid.UUID(student_id),
        uuid.UUID(teacher_id),
    )
    return dict(row) if row else None


async def create_student_teacher_access_checkout(
    student_id: str,
    teacher_id: str,
    success_url: str,
    cancel_url: str,
) -> str:
    """Create a Stripe Checkout Session for student-teacher access. Returns checkout_url."""
    if not settings.STRIPE_SECRET_KEY:
        raise RuntimeError("Stripe not configured")

    price_id = settings.STRIPE_STUDENT_TEACHER_ACCESS_PRICE_ID
    if not price_id:
        raise RuntimeError("STRIPE_STUDENT_TEACHER_ACCESS_PRICE_ID not configured")

    try:
        import stripe  # type: ignore
    except ImportError:
        raise RuntimeError("stripe package not installed")

    stripe.api_key = settings.STRIPE_SECRET_KEY
    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{"price": price_id, "quantity": 1}],
        mode="subscription",
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={
            "student_id": student_id,
            "teacher_id": teacher_id,
            "access_type": "teacher_access",
        },
    )
    return session["url"]


async def activate_student_teacher_access(
    conn: asyncpg.Connection,
    redis,
    student_id: str,
    teacher_id: str,
    stripe_customer_id: str,
    stripe_subscription_id: str,
    valid_until,
) -> None:
    await conn.execute(
        """
        INSERT INTO student_teacher_access
            (student_id, teacher_id, status, stripe_customer_id,
             stripe_subscription_id, valid_until)
        VALUES ($1, $2, 'active', $3, $4, $5)
        ON CONFLICT (student_id, teacher_id) DO UPDATE
            SET status                 = 'active',
                stripe_customer_id     = EXCLUDED.stripe_customer_id,
                stripe_subscription_id = EXCLUDED.stripe_subscription_id,
                valid_until            = EXCLUDED.valid_until,
                updated_at             = NOW()
        """,
        uuid.UUID(student_id),
        uuid.UUID(teacher_id),
        stripe_customer_id,
        stripe_subscription_id,
        valid_until,
    )
    await redis.delete(f"ent:teacher_access:{student_id}")
    await redis.delete(f"cur:{student_id}")
    log.info("student_teacher_access_activated", student_id=student_id, teacher_id=teacher_id)


async def cancel_student_teacher_access_db(
    conn: asyncpg.Connection,
    redis,
    stripe_subscription_id: str,
) -> None:
    row = await conn.fetchrow(
        """
        UPDATE student_teacher_access
        SET status = 'cancelled', updated_at = NOW()
        WHERE stripe_subscription_id = $1
        RETURNING student_id::text, teacher_id::text
        """,
        stripe_subscription_id,
    )
    if row:
        sid = row["student_id"]
        await redis.delete(f"ent:teacher_access:{sid}")
        await redis.delete(f"cur:{sid}")


# ── Admin listing ─────────────────────────────────────────────────────────────


async def list_admin_private_teachers(
    conn: asyncpg.Connection,
    page: int,
    page_size: int,
    search: str | None,
) -> dict:
    offset = (page - 1) * page_size

    if search:
        search_pattern = f"%{search}%"
        rows = await conn.fetch(
            """
            SELECT pt.teacher_id::text, pt.email, pt.name,
                   pt.account_status::text, pt.created_at,
                   ts.plan, ts.status AS subscription_status,
                   COALESCE(
                       (SELECT COUNT(*) FROM curricula c
                        WHERE c.owner_type = 'teacher' AND c.owner_id = pt.teacher_id),
                       0
                   ) AS curricula_count
            FROM private_teachers pt
            LEFT JOIN teacher_subscriptions ts ON ts.teacher_id = pt.teacher_id
            WHERE pt.email ILIKE $1 OR pt.name ILIKE $1
            ORDER BY pt.created_at DESC
            LIMIT $2 OFFSET $3
            """,
            search_pattern,
            page_size,
            offset,
        )
        total_row = await conn.fetchrow(
            """
            SELECT COUNT(*) AS total FROM private_teachers
            WHERE email ILIKE $1 OR name ILIKE $1
            """,
            search_pattern,
        )
    else:
        rows = await conn.fetch(
            """
            SELECT pt.teacher_id::text, pt.email, pt.name,
                   pt.account_status::text, pt.created_at,
                   ts.plan, ts.status AS subscription_status,
                   COALESCE(
                       (SELECT COUNT(*) FROM curricula c
                        WHERE c.owner_type = 'teacher' AND c.owner_id = pt.teacher_id),
                       0
                   ) AS curricula_count
            FROM private_teachers pt
            LEFT JOIN teacher_subscriptions ts ON ts.teacher_id = pt.teacher_id
            ORDER BY pt.created_at DESC
            LIMIT $1 OFFSET $2
            """,
            page_size,
            offset,
        )
        total_row = await conn.fetchrow(
            "SELECT COUNT(*) AS total FROM private_teachers"
        )

    teachers = [
        {
            "teacher_id": r["teacher_id"],
            "email": r["email"],
            "name": r["name"],
            "account_status": r["account_status"],
            "created_at": r["created_at"].isoformat(),
            "plan": r["plan"],
            "subscription_status": r["subscription_status"],
            "curricula_count": r["curricula_count"],
        }
        for r in rows
    ]
    return {"teachers": teachers, "total": total_row["total"]}
