"""
backend/src/school/retention_service.py

Async lifecycle functions for the lesson retention service (Phase D).

Each function accepts a live asyncpg connection that already has
app.current_school_id set to 'bypass' (the caller is responsible for this).

These are plain async functions — not Celery tasks — so they can be:
  - Awaited directly in tests
  - Called via _run_async() inside Celery tasks in tasks.py
  - Composed into larger workflows

Email dispatch is stubbed: _queue_retention_email() emits a structured log
entry.  Phase E will replace this with real Celery email task dispatch.
"""

from __future__ import annotations

import asyncpg

from src.core.storage import StorageBackend
from src.utils.logger import get_logger

log = get_logger("school.retention_service")


def _queue_retention_email(
    school_id: str,
    curriculum_id: str,
    template: str,
    contact_email: str = "",
    grade: int = 0,
    curriculum_name: str = "",
    expires_at: str = "",
    grace_until: str = "",
    days_remaining: int = 0,
) -> None:
    """
    Dispatch a retention lifecycle email via Celery (io queue).

    grace_until is used as both grace_date and purge_date — for the
    purge_complete template the grace expiry date IS the purge date.

    Lazy import of celery_app avoids circular imports:
      retention_service → tasks → retention_service
    """
    # Lazy import to avoid circular dependency.
    from src.core.celery_app import celery_app  # noqa: PLC0415

    celery_app.send_task(
        "src.auth.tasks.send_retention_email_task",
        kwargs=dict(
            to_email=contact_email,
            template=template,
            grade=grade,
            curriculum_name=curriculum_name or curriculum_id,
            expires_date=expires_at,
            grace_date=grace_until,
            purge_date=grace_until,  # grace expiry == purge date for template 5
            days_remaining=days_remaining,
        ),
        queue="io",
    )
    log.info(
        "retention_email_queued school_id=%s curriculum_id=%s template=%s",
        school_id, curriculum_id, template,
    )


# ── Lifecycle function 1: 30-day pre-expiry warning ───────────────────────────


async def send_pre_expiry_warnings(conn: asyncpg.Connection) -> int:
    """
    Queue a pre-expiry warning email for every school curriculum that expires
    in exactly 30 days (matched by calendar date).

    Returns the number of curricula that received a warning.
    No DB state change — email only.
    """
    rows = await conn.fetch(
        """
        SELECT c.curriculum_id, c.grade, c.school_id::text AS school_id,
               c.expires_at, s.contact_email
        FROM curricula c
        JOIN schools s ON s.school_id = c.school_id
        WHERE c.retention_status = 'active'
          AND c.owner_type = 'school'
          AND c.expires_at IS NOT NULL
          AND c.expires_at::date = (NOW() + INTERVAL '30 days')::date
        """
    )
    for row in rows:
        _queue_retention_email(
            school_id=row["school_id"],
            curriculum_id=row["curriculum_id"],
            template="retention_pre_expiry_warning",
            grade=row["grade"],
            expires_at=row["expires_at"].isoformat(),
            contact_email=row["contact_email"],
        )
    log.info("retention_pre_expiry_check_complete count=%d", len(rows))
    return len(rows)


# ── Lifecycle function 2: expiry sweep (active → unavailable) ─────────────────


async def expire_active_curricula(conn: asyncpg.Connection) -> list[dict]:
    """
    Transition all school curricula from 'active' to 'unavailable' whose
    expires_at has passed.

    Sets grace_until = expires_at + 180 days and queues an expiry email.
    Returns a list of dicts for each transitioned curriculum.
    Idempotent: only rows with retention_status = 'active' are touched.
    """
    rows = await conn.fetch(
        """
        WITH updated AS (
            UPDATE curricula
            SET retention_status = 'unavailable',
                grace_until      = expires_at + INTERVAL '180 days'
            WHERE retention_status = 'active'
              AND owner_type = 'school'
              AND expires_at IS NOT NULL
              AND expires_at <= NOW()
            RETURNING curriculum_id, grade, school_id, expires_at, grace_until
        )
        SELECT u.curriculum_id, u.grade, u.school_id::text AS school_id,
               u.expires_at, u.grace_until, s.contact_email
        FROM updated u
        JOIN schools s ON s.school_id = u.school_id
        """
    )
    for row in rows:
        _queue_retention_email(
            school_id=row["school_id"],
            curriculum_id=row["curriculum_id"],
            template="retention_expiry_notification",
            contact_email=row["contact_email"],
            grade=row["grade"],
            expires_at=row["expires_at"].isoformat(),
            grace_until=row["grace_until"].isoformat(),
        )
    log.info("retention_expiry_sweep_complete transitioned=%d", len(rows))
    return [dict(r) for r in rows]


# ── Lifecycle function 3: 90-day grace reminder ───────────────────────────────


async def send_grace_90day_reminders(conn: asyncpg.Connection) -> int:
    """
    Queue a reminder email for curricula that entered the 90th day of their
    grace period today (grace_until - 90 days == today).

    No DB state change.
    """
    rows = await conn.fetch(
        """
        SELECT c.curriculum_id, c.grade, c.school_id::text AS school_id,
               c.expires_at, c.grace_until, s.contact_email
        FROM curricula c
        JOIN schools s ON s.school_id = c.school_id
        WHERE c.retention_status = 'unavailable'
          AND c.owner_type = 'school'
          AND c.grace_until IS NOT NULL
          AND (c.grace_until - INTERVAL '90 days')::date = NOW()::date
        """
    )
    for row in rows:
        _queue_retention_email(
            school_id=row["school_id"],
            curriculum_id=row["curriculum_id"],
            template="retention_grace_90day_reminder",
            contact_email=row["contact_email"],
            grade=row["grade"],
            grace_until=row["grace_until"].isoformat(),
            days_remaining=90,
        )
    log.info("retention_grace_reminder_complete count=%d", len(rows))
    return len(rows)


# ── Lifecycle function 4: 30-days-to-purge warning (day 150) ─────────────────


async def send_purge_30day_warnings(conn: asyncpg.Connection) -> int:
    """
    Queue an urgent warning for curricula with exactly 30 days until purge
    (grace_until - 30 days == today, i.e. day 150 of the 180-day grace).

    No DB state change.
    """
    rows = await conn.fetch(
        """
        SELECT c.curriculum_id, c.grade, c.school_id::text AS school_id,
               c.expires_at, c.grace_until, s.contact_email
        FROM curricula c
        JOIN schools s ON s.school_id = c.school_id
        WHERE c.retention_status = 'unavailable'
          AND c.owner_type = 'school'
          AND c.grace_until IS NOT NULL
          AND (c.grace_until - INTERVAL '30 days')::date = NOW()::date
        """
    )
    for row in rows:
        _queue_retention_email(
            school_id=row["school_id"],
            curriculum_id=row["curriculum_id"],
            template="retention_purge_warning_30day",
            contact_email=row["contact_email"],
            grade=row["grade"],
            grace_until=row["grace_until"].isoformat(),
            days_remaining=30,
        )
    log.info("retention_purge_warning_complete count=%d", len(rows))
    return len(rows)


# ── Lifecycle function 5: file purge (unavailable → purged) ──────────────────


async def purge_grace_expired(
    conn: asyncpg.Connection,
    storage: StorageBackend,
) -> list[dict]:
    """
    Permanently delete content files for curricula whose 180-day grace period
    has elapsed.

    Sequence:
      1. Mark retention_status = 'purged' in DB (before file deletion so
         subsequent requests get 'not found' even if deletion is slow).
      2. Delete curriculum directory via StorageBackend.delete_tree.
      3. Log CDN invalidation stub (Phase G will wire up CloudFront).
      4. Queue purge-complete notification to school_admin.

    FERPA: student progress records are NOT deleted — only content files
    and the curricula row's retention_status change.

    Returns a list of dicts for each purged curriculum.
    Idempotent: already-purged rows are not touched.
    """
    rows = await conn.fetch(
        """
        WITH purged AS (
            UPDATE curricula
            SET retention_status = 'purged'
            WHERE retention_status = 'unavailable'
              AND owner_type = 'school'
              AND grace_until IS NOT NULL
              AND grace_until <= NOW()
            RETURNING curriculum_id, grade, school_id, expires_at, grace_until
        )
        SELECT p.curriculum_id, p.grade, p.school_id::text AS school_id,
               p.expires_at, p.grace_until, s.contact_email
        FROM purged p
        JOIN schools s ON s.school_id = p.school_id
        """
    )

    if not rows:
        log.info("retention_purge_nothing_to_purge")
        return []

    for row in rows:
        cid = row["curriculum_id"]

        try:
            await storage.delete_tree(f"curricula/{cid}")
            log.info("retention_purge_files_deleted curriculum_id=%s", cid)
        except Exception as exc:
            log.warning(
                "retention_purge_file_delete_failed curriculum_id=%s err=%s",
                cid, exc,
            )

        # CDN invalidation stub — Phase G will call CloudFront here.
        log.info("retention_purge_cdn_invalidation_stub curriculum_id=%s", cid)

        _queue_retention_email(
            school_id=row["school_id"],
            curriculum_id=cid,
            template="retention_purge_complete",
            contact_email=row["contact_email"],
            grade=row["grade"],
            expires_at=row["expires_at"].isoformat(),
            grace_until=row["grace_until"].isoformat(),
        )

    log.info("retention_purge_complete count=%d", len(rows))
    return [dict(r) for r in rows]
