"""
backend/src/auth/tasks.py

Celery tasks for async auth operations.

Tasks:
  sync_auth0_suspension      — block/unblock user on Auth0
  cascade_school_suspension  — suspend all teachers + students for a school
  gdpr_delete_account        — anonymise student record + delete from Auth0
  write_audit_log_task       — write a row to the audit_log table
"""

from __future__ import annotations

import asyncio
import json
import uuid
from typing import Optional

from celery import Celery

from config import settings

celery_app = Celery(
    "studybuddy",
    broker=settings.effective_celery_broker_url,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_routes={
        "src.auth.tasks.write_audit_log_task": {"queue": "io"},
        "src.auth.tasks.cascade_school_suspension": {"queue": "io"},
        "src.auth.tasks.gdpr_delete_account": {"queue": "io"},
        "src.auth.tasks.sync_auth0_suspension": {"queue": "io"},
        "src.auth.tasks.poll_infra_metrics": {"queue": "default"},
        "src.auth.tasks.write_progress_answer_task": {"queue": "io"},
        "src.auth.tasks.update_streak_task": {"queue": "io"},
        "src.auth.tasks.refresh_progress_view_task": {"queue": "io"},
    },
    beat_schedule={
        # Poll DB pool state + Celery queue depth every 30 seconds.
        "poll-infra-metrics-30s": {
            "task": "src.auth.tasks.poll_infra_metrics",
            "schedule": 30.0,
        },
    },
)


def _run_async(coro):
    """Run an async coroutine from a sync Celery task."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(name="src.auth.tasks.sync_auth0_suspension", bind=True, max_retries=3)
def sync_auth0_suspension(self, auth0_sub: str, action: str) -> None:
    """
    Block or unblock a user on Auth0.

    action: "block" | "unblock"
    """
    from src.auth.service import block_auth0_user

    try:
        blocked = action == "block"
        _run_async(block_auth0_user(auth0_sub, blocked=blocked))
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)


@celery_app.task(name="src.auth.tasks.cascade_school_suspension", bind=True, max_retries=3)
def cascade_school_suspension(self, school_id: str, new_status: str) -> None:
    """
    When a school is suspended, add Redis suspended:{id} for all its members.
    When a school is reactivated, this task does NOT reactivate members
    (per PHASE1_SETUP.md section 10.6 — each must be explicitly reactivated).
    """
    import asyncpg
    from config import settings as cfg

    if new_status != "suspended":
        # Reactivation of school does not cascade to members.
        return

    async def _cascade():
        pool = await asyncpg.create_pool(cfg.DATABASE_URL, min_size=1, max_size=3)
        import redis.asyncio as aioredis_mod

        redis = await aioredis_mod.from_url(cfg.REDIS_URL)
        try:
            # Fetch all active teachers and students in the school.
            teachers = await pool.fetch(
                "SELECT teacher_id FROM teachers WHERE school_id = $1 AND account_status != 'deleted'",
                uuid.UUID(school_id),
            )
            students = await pool.fetch(
                "SELECT student_id FROM students WHERE school_id = $1 AND account_status != 'deleted'",
                uuid.UUID(school_id),
            )

            pipeline = redis.pipeline()
            for t in teachers:
                pipeline.set(f"suspended:{t['teacher_id']}", "1")
            for s in students:
                pipeline.set(f"suspended:{s['student_id']}", "1")
            await pipeline.execute()

            # Update account_status in DB.
            await pool.execute(
                "UPDATE teachers SET account_status = 'suspended' WHERE school_id = $1",
                uuid.UUID(school_id),
            )
            await pool.execute(
                "UPDATE students SET account_status = 'suspended' WHERE school_id = $1",
                uuid.UUID(school_id),
            )
        finally:
            await redis.aclose()
            await pool.close()

    try:
        _run_async(_cascade())
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)


@celery_app.task(name="src.auth.tasks.gdpr_delete_account", bind=True, max_retries=3)
def gdpr_delete_account(self, student_id: str, auth0_sub: str) -> None:
    """
    GDPR account erasure:
    1. Anonymise student PII in PostgreSQL (name, email → redacted).
    2. Set account_status = 'deleted'.
    3. Delete user from Auth0.
    """
    import asyncpg
    from config import settings as cfg
    from src.auth.service import delete_auth0_user

    async def _delete():
        pool = await asyncpg.create_pool(cfg.DATABASE_URL, min_size=1, max_size=2)
        try:
            anon_name = f"deleted-{student_id[:8]}"
            anon_email = f"deleted-{student_id}@deleted.invalid"
            await pool.execute(
                """
                UPDATE students
                SET name = $1, email = $2, account_status = 'deleted'
                WHERE student_id = $3
                """,
                anon_name,
                anon_email,
                uuid.UUID(student_id),
            )
        finally:
            await pool.close()

        await delete_auth0_user(auth0_sub)

    try:
        _run_async(_delete())
    except Exception as exc:
        raise self.retry(exc=exc, countdown=300)


@celery_app.task(name="src.auth.tasks.write_audit_log_task", bind=True, max_retries=3)
def write_audit_log_task(
    self,
    event_type: str,
    actor_type: str,
    actor_id: Optional[str],
    target_type: Optional[str],
    target_id: Optional[str],
    metadata: Optional[dict],
    ip_address: Optional[str],
    correlation_id: Optional[str],
) -> None:
    """Write a single row to the audit_log table."""
    import asyncpg
    from config import settings as cfg

    async def _write():
        pool = await asyncpg.create_pool(cfg.DATABASE_URL, min_size=1, max_size=2)
        try:
            await pool.execute(
                """
                INSERT INTO audit_log
                    (event_type, actor_type, actor_id, target_type, target_id,
                     metadata, ip_address, correlation_id)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """,
                event_type,
                actor_type,
                uuid.UUID(actor_id) if actor_id else None,
                target_type,
                uuid.UUID(target_id) if target_id else None,
                json.dumps(metadata) if metadata else None,
                ip_address,
                correlation_id,
            )
        finally:
            await pool.close()

    try:
        _run_async(_write())
    except Exception as exc:
        raise self.retry(exc=exc, countdown=30)


@celery_app.task(name="src.auth.tasks.write_progress_answer_task", bind=True, max_retries=3)
def write_progress_answer_task(
    self,
    session_id: str,
    question_id: str,
    student_answer: int,
    correct_answer: int,
    correct: bool,
    ms_taken: int,
    event_id: Optional[str],
) -> None:
    """
    Fire-and-forget task: write a progress answer to PostgreSQL.

    Uses ON CONFLICT DO NOTHING on event_id for mobile offline deduplication.
    """
    import asyncpg
    from config import settings as cfg
    from src.progress.service import record_answer_sync

    async def _write():
        pool = await asyncpg.create_pool(cfg.DATABASE_URL, min_size=1, max_size=2)
        try:
            async with pool.acquire() as conn:
                await record_answer_sync(
                    conn,
                    session_id=session_id,
                    question_id=question_id,
                    student_answer=student_answer,
                    correct_answer=correct_answer,
                    correct=correct,
                    ms_taken=ms_taken,
                    event_id=event_id,
                )
        finally:
            await pool.close()

    try:
        _run_async(_write())
    except Exception as exc:
        raise self.retry(exc=exc, countdown=10)


@celery_app.task(name="src.auth.tasks.update_streak_task", bind=True, max_retries=3)
def update_streak_task(self, student_id: str, activity_date: str) -> None:
    """
    Update the streak counter in Redis for a student's activity date.

    Idempotent: if already counted today, does nothing.
    """
    import redis as redis_sync
    from config import settings as cfg

    try:
        r = redis_sync.from_url(cfg.REDIS_URL)
        raw = r.get(f"streak:{student_id}")
        streak = json.loads(raw) if raw else {"current": 0, "longest": 0, "last_active_date": None}

        last = streak.get("last_active_date")
        if last == activity_date:
            r.close()
            return

        from datetime import date as _date
        current = streak.get("current", 0)
        longest = streak.get("longest", 0)

        if last is not None:
            try:
                delta = (_date.fromisoformat(activity_date) - _date.fromisoformat(last)).days
                current = current + 1 if delta == 1 else 1
            except ValueError:
                current = 1
        else:
            current = 1

        if current > longest:
            longest = current

        streak = {"current": current, "longest": longest, "last_active_date": activity_date}
        r.setex(f"streak:{student_id}", 60 * 60 * 24 * 90, json.dumps(streak))
        r.close()
    except Exception as exc:
        raise self.retry(exc=exc, countdown=15)


@celery_app.task(name="src.auth.tasks.refresh_progress_view_task", bind=True, max_retries=2)
def refresh_progress_view_task(self, student_id: str) -> None:
    """
    Refresh mv_student_curriculum_progress for a single student.

    Uses REFRESH MATERIALIZED VIEW CONCURRENTLY so reads are not blocked.
    Also invalidates the dashboard Redis cache for this student.
    """
    import asyncpg
    from config import settings as cfg
    import redis as redis_sync

    async def _refresh():
        pool = await asyncpg.create_pool(cfg.DATABASE_URL, min_size=1, max_size=2)
        try:
            async with pool.acquire() as conn:
                await conn.execute(
                    "REFRESH MATERIALIZED VIEW CONCURRENTLY mv_student_curriculum_progress"
                )
        finally:
            await pool.close()

    try:
        _run_async(_refresh())

        # Invalidate L2 dashboard cache
        r = redis_sync.from_url(cfg.REDIS_URL)
        r.delete(f"dashboard:{student_id}")
        r.close()
    except Exception as exc:
        raise self.retry(exc=exc, countdown=30)


@celery_app.task(name="src.auth.tasks.poll_infra_metrics")
def poll_infra_metrics() -> None:
    """
    Celery Beat task — runs every 30 seconds.

    Polls:
    - asyncpg DB pool state (size, free, min, max) → Prometheus Gauges
    - Celery queue depths for 'io' and 'default' queues → Prometheus Gauges

    Metrics are exposed on GET /metrics by the FastAPI observability router.
    This task reads live Redis queue lengths using LLEN on the Celery queue keys.
    """
    import redis as redis_sync

    from config import settings as cfg
    from src.core.observability import db_pool_connections

    try:
        from prometheus_client import Gauge

        celery_queue_depth = Gauge(
            "sb_celery_queue_depth",
            "Number of tasks waiting in each Celery queue",
            ["queue"],
        )

        # ── Queue depth via Redis LLEN ─────────────────────────────────────────
        r = redis_sync.from_url(cfg.REDIS_URL)
        try:
            for queue_name in ("io", "default", "pipeline"):
                depth = r.llen(queue_name) or 0
                celery_queue_depth.labels(queue=queue_name).set(depth)
        finally:
            r.close()

    except Exception as exc:
        # Non-fatal — metrics are best-effort.
        import logging
        logging.getLogger("tasks.poll_infra_metrics").warning("metrics_poll_failed: %s", exc)
