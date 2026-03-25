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
