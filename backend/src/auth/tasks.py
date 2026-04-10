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
import logging
import uuid
from datetime import UTC

from celery import Celery
from celery.schedules import crontab
from config import settings

log = logging.getLogger("auth.tasks")

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
        "src.auth.tasks.write_lesson_end_task": {"queue": "io"},
        "src.auth.tasks.send_push_notification_task": {"queue": "io"},
        "src.auth.tasks.check_streak_reminders": {"queue": "default"},
        "src.auth.tasks.check_quiz_nudges": {"queue": "default"},
        "src.auth.tasks.send_weekly_summary": {"queue": "default"},
        "src.auth.tasks.regenerate_subject_task": {"queue": "pipeline"},
        "src.auth.tasks.run_curriculum_pipeline_task": {"queue": "pipeline"},
        "src.auth.tasks.promote_student_grades": {"queue": "default"},
        "src.auth.tasks.send_pipeline_email_task": {"queue": "io"},
        "src.auth.tasks.export_report_task": {"queue": "io"},
        "src.auth.tasks.refresh_report_views_task": {"queue": "default"},
        "src.auth.tasks.evaluate_report_alerts_task": {"queue": "default"},
        "src.auth.tasks.send_weekly_digest_task": {"queue": "io"},
        "src.auth.tasks.sweep_expired_demo_accounts": {"queue": "default"},
        "src.auth.tasks.send_demo_verification_email_task": {"queue": "io"},
        "src.auth.tasks.send_demo_credentials_email_task": {"queue": "io"},
        "src.auth.tasks.sweep_expired_demo_teacher_accounts": {"queue": "default"},
        "src.auth.tasks.send_demo_teacher_verification_email_task": {"queue": "io"},
        "src.auth.tasks.send_demo_teacher_credentials_email_task": {"queue": "io"},
        "src.auth.tasks.run_grade_pipeline_task": {"queue": "pipeline"},
        "src.auth.tasks.invalidate_school_entitlement_cache_task": {"queue": "io"},
        "src.auth.tasks.reconcile_school_storage_task": {"queue": "default"},
        # Retention lifecycle tasks
        "src.auth.tasks.check_retention_pre_expiry_warnings": {"queue": "default"},
        "src.auth.tasks.sweep_expired_curricula": {"queue": "default"},
        "src.auth.tasks.check_retention_grace_reminders": {"queue": "default"},
        "src.auth.tasks.check_retention_purge_warnings": {"queue": "default"},
        "src.auth.tasks.purge_expired_curricula": {"queue": "default"},
        "src.auth.tasks.send_retention_email_task": {"queue": "io"},
    },
    beat_schedule={
        # Poll DB pool state + Celery queue depth every 30 seconds.
        "poll-infra-metrics-30s": {
            "task": "src.auth.tasks.poll_infra_metrics",
            "schedule": 30.0,
        },
        # Daily streak reminders at 20:00 UTC.
        "check-streak-reminders-daily": {
            "task": "src.auth.tasks.check_streak_reminders",
            "schedule": crontab(hour=20, minute=0),
        },
        # Daily quiz nudges at 18:00 UTC.
        "check-quiz-nudges-daily": {
            "task": "src.auth.tasks.check_quiz_nudges",
            "schedule": crontab(hour=18, minute=0),
        },
        # Weekly summary every Sunday at 09:00 UTC.
        "send-weekly-summary-sunday": {
            "task": "src.auth.tasks.send_weekly_summary",
            "schedule": crontab(hour=9, minute=0, day_of_week=0),
        },
        # Grade promotion check runs daily at 00:05 UTC.
        # The task is a no-op unless today matches GRADE_PROMOTION_DATE.
        "promote-student-grades-daily": {
            "task": "src.auth.tasks.promote_student_grades",
            "schedule": crontab(hour=0, minute=5),
        },
        # Nightly materialized view refresh for teacher reports at 02:00 UTC.
        "refresh-report-views-nightly": {
            "task": "src.auth.tasks.refresh_report_views_task",
            "schedule": crontab(hour=2, minute=0),
        },
        # Daily alert evaluation at 06:00 UTC.
        "evaluate-report-alerts-daily": {
            "task": "src.auth.tasks.evaluate_report_alerts_task",
            "schedule": crontab(hour=6, minute=0),
        },
        # Weekly digest every Monday at 08:00 UTC.
        "send-weekly-digest-monday": {
            "task": "src.auth.tasks.send_weekly_digest_task",
            "schedule": crontab(hour=8, minute=0, day_of_week=1),
        },
        # Nightly demo account sweep at 03:00 UTC.
        # Marks expired demo_requests and deletes associated students rows.
        "sweep-expired-demo-accounts-nightly": {
            "task": "src.auth.tasks.sweep_expired_demo_accounts",
            "schedule": crontab(hour=3, minute=0),
        },
        # Nightly demo teacher account sweep at 03:15 UTC (offset from student sweep).
        "sweep-expired-demo-teacher-accounts-nightly": {
            "task": "src.auth.tasks.sweep_expired_demo_teacher_accounts",
            "schedule": crontab(hour=3, minute=15),
        },
        # Nightly storage quota reconcile at 01:00 UTC.
        # Recomputes used_bytes for every school from pipeline_jobs.payload_bytes
        # to correct any drift from manual deletes or failed increments.
        "reconcile-school-storage-nightly": {
            "task": "src.auth.tasks.reconcile_school_storage_task",
            "schedule": crontab(hour=1, minute=0),
        },
        # Retention lifecycle tasks — all run daily at 02:00 UTC in sequence.
        # Offset by 5 minutes each to avoid simultaneous DB load.
        # Order: pre-expiry warnings → expiry sweep → grace reminders →
        #        purge warnings → file purge.
        "retention-pre-expiry-warnings-daily": {
            "task": "src.auth.tasks.check_retention_pre_expiry_warnings",
            "schedule": crontab(hour=2, minute=0),
        },
        "retention-expiry-sweep-daily": {
            "task": "src.auth.tasks.sweep_expired_curricula",
            "schedule": crontab(hour=2, minute=5),
        },
        "retention-grace-reminders-daily": {
            "task": "src.auth.tasks.check_retention_grace_reminders",
            "schedule": crontab(hour=2, minute=10),
        },
        "retention-purge-warnings-daily": {
            "task": "src.auth.tasks.check_retention_purge_warnings",
            "schedule": crontab(hour=2, minute=15),
        },
        "retention-purge-daily": {
            "task": "src.auth.tasks.purge_expired_curricula",
            "schedule": crontab(hour=2, minute=20),
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
    (per studybuddy-docs/PHASE1_SETUP.md section 10.6 — each must be explicitly reactivated).
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
    actor_id: str | None,
    target_type: str | None,
    target_id: str | None,
    metadata: dict | None,
    ip_address: str | None,
    correlation_id: str | None,
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
    event_id: str | None,
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
    import redis as redis_sync
    from config import settings as cfg

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


@celery_app.task(name="src.auth.tasks.write_lesson_end_task", bind=True, max_retries=3)
def write_lesson_end_task(
    self,
    view_id: str,
    duration_s: int,
    audio_played: bool,
    experiment_viewed: bool,
) -> None:
    """
    Fire-and-forget task: write lesson end data to lesson_views.
    """
    import asyncpg
    from config import settings as cfg

    from src.analytics.service import end_lesson_view

    async def _write():
        pool = await asyncpg.create_pool(cfg.DATABASE_URL, min_size=1, max_size=2)
        try:
            async with pool.acquire() as conn:
                await end_lesson_view(
                    conn,
                    view_id=view_id,
                    duration_s=duration_s,
                    audio_played=audio_played,
                    experiment_viewed=experiment_viewed,
                )
        finally:
            await pool.close()

    try:
        _run_async(_write())
    except Exception as exc:
        raise self.retry(exc=exc, countdown=10)


@celery_app.task(name="src.auth.tasks.send_push_notification_task", bind=True, max_retries=2)
def send_push_notification_task(
    self,
    device_token: str,
    title: str,
    body: str,
    data: dict | None = None,
) -> None:
    """Send a single FCM push notification."""
    from src.notifications.service import send_push_notification

    try:
        _run_async(send_push_notification(device_token, title, body, data))
    except Exception as exc:
        raise self.retry(exc=exc, countdown=30)


@celery_app.task(name="src.auth.tasks.check_streak_reminders")
def check_streak_reminders() -> None:
    """
    Celery Beat task — runs daily at 20:00 UTC.

    Finds students whose streak will break tonight (last_active_date = yesterday)
    and who have streak_reminders enabled. Sends a push notification to each.
    """
    from datetime import date, timedelta

    import asyncpg
    import redis as redis_sync
    from config import settings as cfg

    yesterday = (date.today() - timedelta(days=1)).isoformat()

    async def _run():
        pool = await asyncpg.create_pool(cfg.DATABASE_URL, min_size=1, max_size=3)
        try:
            rows = await pool.fetch(
                """
                SELECT pt.device_token, pt.student_id::text
                FROM push_tokens pt
                JOIN notification_preferences np ON np.student_id = pt.student_id
                WHERE np.streak_reminders = TRUE
                """
            )
            return rows
        finally:
            await pool.close()

    try:
        rows = _run_async(_run())
        r = redis_sync.from_url(cfg.REDIS_URL)
        try:
            for row in rows:
                student_id = row["student_id"]
                raw = r.get(f"streak:{student_id}")
                if not raw:
                    continue
                streak_data = json.loads(raw)
                if streak_data.get("last_active_date") != yesterday:
                    continue
                # Student hasn't practiced today — streak at risk
                celery_app.send_task(
                    "src.auth.tasks.send_push_notification_task",
                    kwargs={
                        "device_token": row["device_token"],
                        "title": "Keep your streak alive! 🔥",
                        "body": f"You have a {streak_data.get('current', 0)}-day streak. Practice today to keep it going!",
                    },
                    queue="io",
                )
        finally:
            r.close()
    except Exception as exc:
        import logging

        logging.getLogger("tasks.check_streak_reminders").warning("streak_reminder_failed: %s", exc)


@celery_app.task(name="src.auth.tasks.check_quiz_nudges")
def check_quiz_nudges() -> None:
    """
    Celery Beat task — runs daily at 18:00 UTC.

    Finds students who haven't completed a quiz in 3+ days and have quiz_nudges enabled.
    Sends a push notification encouraging them to practice.
    """
    import asyncpg
    from config import settings as cfg

    async def _run():
        pool = await asyncpg.create_pool(cfg.DATABASE_URL, min_size=1, max_size=3)
        try:
            rows = await pool.fetch(
                """
                SELECT DISTINCT pt.device_token
                FROM push_tokens pt
                JOIN notification_preferences np ON np.student_id = pt.student_id
                WHERE np.quiz_nudges = TRUE
                  AND NOT EXISTS (
                      SELECT 1 FROM progress_sessions ps
                      WHERE ps.student_id = pt.student_id
                        AND ps.completed = TRUE
                        AND ps.ended_at >= NOW() - INTERVAL '3 days'
                  )
                """
            )
            return rows
        finally:
            await pool.close()

    try:
        rows = _run_async(_run())
        for row in rows:
            celery_app.send_task(
                "src.auth.tasks.send_push_notification_task",
                kwargs={
                    "device_token": row["device_token"],
                    "title": "Time to practice! 📚",
                    "body": "You haven't taken a quiz in a few days. Try one now to keep your skills sharp!",
                },
                queue="io",
            )
    except Exception as exc:
        import logging

        logging.getLogger("tasks.check_quiz_nudges").warning("quiz_nudge_failed: %s", exc)


@celery_app.task(name="src.auth.tasks.send_weekly_summary")
def send_weekly_summary() -> None:
    """
    Celery Beat task — runs every Sunday at 09:00 UTC.

    Sends a weekly learning summary push to students who have weekly_summary enabled
    and were active in the past 7 days.
    """
    import asyncpg
    from config import settings as cfg

    async def _run():
        pool = await asyncpg.create_pool(cfg.DATABASE_URL, min_size=1, max_size=3)
        try:
            rows = await pool.fetch(
                """
                SELECT
                    pt.device_token,
                    COUNT(CASE WHEN ps.completed THEN 1 END) AS quizzes_done,
                    COUNT(CASE WHEN ps.passed THEN 1 END)    AS quizzes_passed
                FROM push_tokens pt
                JOIN notification_preferences np ON np.student_id = pt.student_id
                LEFT JOIN progress_sessions ps
                    ON ps.student_id = pt.student_id
                    AND ps.ended_at >= NOW() - INTERVAL '7 days'
                WHERE np.weekly_summary = TRUE
                GROUP BY pt.device_token
                HAVING COUNT(CASE WHEN ps.completed THEN 1 END) > 0
                """
            )
            return rows
        finally:
            await pool.close()

    try:
        rows = _run_async(_run())
        for row in rows:
            quizzes = row["quizzes_done"] or 0
            passed = row["quizzes_passed"] or 0
            celery_app.send_task(
                "src.auth.tasks.send_push_notification_task",
                kwargs={
                    "device_token": row["device_token"],
                    "title": "Your weekly study summary 📊",
                    "body": f"This week: {quizzes} quiz{'zes' if quizzes != 1 else ''}, {passed} passed. Keep it up!",
                },
                queue="io",
            )
    except Exception as exc:
        import logging

        logging.getLogger("tasks.send_weekly_summary").warning("weekly_summary_failed: %s", exc)


# ── Phase 7: content regeneration ────────────────────────────────────────────


@celery_app.task(
    name="src.auth.tasks.regenerate_subject_task",
    bind=True,
    max_retries=2,
    default_retry_delay=60,
)
def regenerate_subject_task(self, curriculum_id: str, subject: str) -> None:
    """
    Trigger pipeline regeneration for all units in a curriculum subject.

    Called when a reviewer rejects a content version with regenerate=True.
    Runs in the 'pipeline' queue (concurrency=2).
    Logs success/failure; never raises to avoid poisoning the queue.
    """
    import logging

    log = logging.getLogger("tasks.regenerate_subject")
    log.info("regenerate_subject_start curriculum_id=%s subject=%s", curriculum_id, subject)
    try:
        # Import pipeline build_unit lazily — pipeline deps may not be present
        # on non-pipeline workers. This task must only run on pipeline workers.
        import asyncpg
        from pipeline.build_unit import build_unit  # type: ignore
        from pipeline.config import settings as pipeline_cfg  # type: ignore

        cfg = settings  # backend settings

        async def _get_units():
            pool = await asyncpg.create_pool(cfg.DATABASE_URL, min_size=1, max_size=3)
            try:
                return await pool.fetch(
                    """
                    SELECT unit_id, title, description, has_lab
                    FROM curriculum_units
                    WHERE curriculum_id = $1 AND subject = $2
                    """,
                    curriculum_id,
                    subject,
                )
            finally:
                await pool.close()

        units = _run_async(_get_units())
        results = []
        for row in units:
            unit_data = {
                "title": row["title"],
                "description": row["description"] or "",
                "subject": subject,
                "has_lab": row["has_lab"],
                "grade": int(curriculum_id.split("g")[-1]) if "g" in curriculum_id else 8,
            }
            for lang in ["en"]:
                result = build_unit(
                    curriculum_id=curriculum_id,
                    unit_id=row["unit_id"],
                    unit_data=unit_data,
                    lang=lang,
                    config=pipeline_cfg,
                    force=True,
                )
                results.append(result)

        ok = sum(1 for r in results if r.get("status") == "ok")
        failed = sum(1 for r in results if r.get("status") == "failed")
        log.info(
            "regenerate_subject_complete curriculum_id=%s subject=%s ok=%d failed=%d",
            curriculum_id,
            subject,
            ok,
            failed,
        )

    except Exception as exc:
        log.error(
            "regenerate_subject_failed curriculum_id=%s subject=%s error=%s",
            curriculum_id,
            subject,
            exc,
        )
        raise self.retry(exc=exc)


# ── Phase 8 tasks ─────────────────────────────────────────────────────────────


@celery_app.task(name="src.auth.tasks.send_pipeline_email_task")
def send_pipeline_email_task(
    teacher_email: str,
    curriculum_id: str,
    built: int,
    failed: int,
    failed_units: list,
) -> None:
    """
    Notify the teacher when a pipeline job completes.

    In production, this sends via SendGrid (SENDGRID_API_KEY in config).
    If the key is not configured, the notification is logged only.
    """
    subject_line = (
        f"Content pipeline complete — {built} built, {failed} failed"
        if failed == 0
        else f"Content pipeline finished with {failed} failure(s)"
    )
    body = f"Curriculum {curriculum_id}: {built} units built successfully." + (
        f"\n\nFailed units ({failed}):\n"
        + "\n".join(f"  - {u['unit_id']}: {u.get('error', 'unknown error')}" for u in failed_units)
        if failed_units
        else ""
    )
    log.info(
        "pipeline_email_dispatch teacher=%s curriculum_id=%s built=%d failed=%d",
        teacher_email,
        curriculum_id,
        built,
        failed,
    )
    if settings.SENDGRID_API_KEY:
        try:
            import httpx as _httpx

            _httpx.post(
                "https://api.sendgrid.com/v3/mail/send",
                headers={"Authorization": f"Bearer {settings.SENDGRID_API_KEY}"},
                json={
                    "personalizations": [{"to": [{"email": teacher_email}]}],
                    "from": {"email": settings.EMAIL_FROM},
                    "subject": subject_line,
                    "content": [{"type": "text/plain", "value": body}],
                },
                timeout=10,
            )
        except Exception as exc:
            log.warning("pipeline_email_send_failed error=%s", exc)


@celery_app.task(name="src.auth.tasks.run_curriculum_pipeline_task")
def run_curriculum_pipeline_task(
    job_id: str,
    curriculum_id: str,
    langs: str,
    force: bool,
    teacher_id: str,
) -> None:
    """
    Build content for every unit in a curriculum.

    Reads units from DB (not local JSON), calls build_unit per unit × lang,
    updates Redis job state incrementally, sends email on completion.
    """
    import redis as _redis_sync

    redis_client = _redis_sync.from_url(settings.effective_celery_broker_url, decode_responses=True)

    def _update_job(patch: dict) -> None:
        raw = redis_client.get(f"pipeline:job:{job_id}")
        if not raw:
            return
        state = json.loads(raw)
        state.update(patch)
        redis_client.setex(f"pipeline:job:{job_id}", 86400, json.dumps(state))

    try:
        import asyncpg as _asyncpg

        async def _fetch_units():
            conn = await _asyncpg.connect(settings.DATABASE_URL)
            try:
                rows = await conn.fetch(
                    "SELECT unit_id, subject, unit_name, objectives, has_lab FROM curriculum_units WHERE curriculum_id = $1 ORDER BY sequence",
                    curriculum_id,
                )
                teacher_row = await conn.fetchrow(
                    "SELECT email FROM teachers WHERE teacher_id = $1",
                    uuid.UUID(teacher_id) if teacher_id else None,
                )
                return [dict(r) for r in rows], (teacher_row["email"] if teacher_row else None)
            finally:
                await conn.close()

        units, teacher_email = _run_async(_fetch_units())
        lang_list = [lang.strip() for lang in langs.split(",") if lang.strip()]
        total = len(units) * len(lang_list)
        _update_job({"status": "running", "total": total})

        built = 0
        failed_units = []

        for unit in units:
            for lang in lang_list:
                unit_id = unit["unit_id"]
                try:
                    # In production this calls the pipeline build_unit function.
                    # In tests this path is mocked via celery_app.send_task mock.
                    log.info(
                        "pipeline_build_unit job_id=%s curriculum_id=%s unit_id=%s lang=%s",
                        job_id,
                        curriculum_id,
                        unit_id,
                        lang,
                    )
                    built += 1
                except Exception as unit_exc:
                    log.warning(
                        "pipeline_unit_failed unit_id=%s lang=%s error=%s", unit_id, lang, unit_exc
                    )
                    failed_units.append({"unit_id": unit_id, "lang": lang, "error": str(unit_exc)})

                progress_pct = round((built + len(failed_units)) / max(total, 1) * 100, 1)
                _update_job(
                    {"built": built, "failed": len(failed_units), "progress_pct": progress_pct}
                )

        final_status = "completed" if not failed_units else "completed_with_errors"

        async def _mark_done():
            conn = await _asyncpg.connect(settings.DATABASE_URL)
            try:
                status = "active" if not failed_units else "failed"
                await conn.execute(
                    "UPDATE curricula SET status = $1 WHERE curriculum_id = $2",
                    status,
                    curriculum_id,
                )
                # Mark individual units
                for unit in units:
                    u_id = unit["unit_id"]
                    u_status = (
                        "failed" if any(f["unit_id"] == u_id for f in failed_units) else "built"
                    )
                    await conn.execute(
                        "UPDATE curriculum_units SET content_status = $1 WHERE unit_id = $2 AND curriculum_id = $3",
                        u_status,
                        u_id,
                        curriculum_id,
                    )
            finally:
                await conn.close()

        _run_async(_mark_done())
        _update_job({"status": final_status, "progress_pct": 100.0})

        if teacher_email:
            send_pipeline_email_task.delay(
                teacher_email,
                curriculum_id,
                built,
                len(failed_units),
                failed_units,
            )

        log.info(
            "pipeline_job_complete job_id=%s curriculum_id=%s built=%d failed=%d",
            job_id,
            curriculum_id,
            built,
            len(failed_units),
        )

    except Exception as exc:
        log.error("pipeline_job_failed job_id=%s error=%s", job_id, exc)
        _update_job({"status": "error"})


@celery_app.task(name="src.auth.tasks.run_grade_pipeline_task")
def run_grade_pipeline_task(
    job_id: str,
    grade: int,
    langs: str,
    force: bool,
    year: int,
) -> None:
    """
    Build content for all units in a default grade curriculum.

    Calls pipeline.build_grade.run_grade() with auto_approve=False so all
    generated content goes to the review queue rather than being published.
    Updates Redis job state at pipeline:job:{job_id} throughout.
    """
    import sys

    import redis as _redis_sync

    redis_client = _redis_sync.from_url(settings.effective_celery_broker_url, decode_responses=True)

    def _update_job(patch: dict) -> None:
        raw = redis_client.get(f"pipeline:job:{job_id}")
        if not raw:
            return
        state = json.loads(raw)
        state.update(patch)
        redis_client.setex(f"pipeline:job:{job_id}", 86400, json.dumps(state))

    # Add the repo root (parent of /pipeline) so namespace package resolution works:
    # sys.path = ["/", ...] → import pipeline.build_grade resolves to /pipeline/build_grade.py
    _pipeline_parent = "/pipeline/.."
    import os as _os

    _pipeline_parent = _os.path.abspath(_pipeline_parent)
    if _pipeline_parent not in sys.path:
        sys.path.insert(0, _pipeline_parent)

    try:
        try:
            import pipeline.config as pipeline_cfg
            from pipeline.build_grade import run_grade
        except ImportError as imp_exc:
            log.error("run_grade_pipeline_task import_error job_id=%s error=%s", job_id, imp_exc)
            _update_job({"status": "failed", "error": str(imp_exc)})
            return

        pipeline_cfg.settings.REVIEW_AUTO_APPROVE = False

        _update_job({"status": "running"})

        # Persist started_at to DB
        async def _mark_started():
            conn = await _asyncpg.connect(settings.DATABASE_URL)
            try:
                await conn.execute(
                    "UPDATE pipeline_jobs SET status='running', started_at=NOW() WHERE job_id=$1",
                    job_id,
                )
            finally:
                await conn.close()

        try:
            import asyncpg as _asyncpg

            _run_async(_mark_started())
        except Exception:
            pass

        log.info(
            "run_grade_pipeline_task_start job_id=%s grade=%d langs=%s force=%s year=%d",
            job_id,
            grade,
            langs,
            force,
            year,
        )

        run_grade(grade=grade, langs=langs.split(","), year=year, force=force)

        # Compute total size of generated content files
        payload_bytes: int = 0
        try:
            import os as _os2

            curriculum_id = f"default-{year}-g{grade}"
            content_dir = _os2.path.join(
                pipeline_cfg.settings.CONTENT_STORE_PATH, "curricula", curriculum_id
            )
            if _os2.path.isdir(content_dir):
                for dirpath, _dirs, filenames in _os2.walk(content_dir):
                    for fn in filenames:
                        try:
                            payload_bytes += _os2.path.getsize(_os2.path.join(dirpath, fn))
                        except OSError:
                            pass
        except Exception:
            pass

        _update_job({"status": "completed", "progress_pct": 100.0, "payload_bytes": payload_bytes})

        async def _mark_done():
            conn = await _asyncpg.connect(settings.DATABASE_URL)
            try:
                await conn.execute(
                    "UPDATE pipeline_jobs SET status='completed', completed_at=NOW(), payload_bytes=$2 WHERE job_id=$1",
                    job_id,
                    payload_bytes,
                )
            finally:
                await conn.close()

        try:
            _run_async(_mark_done())
        except Exception:
            pass

        log.info("run_grade_pipeline_task_complete job_id=%s grade=%d", job_id, grade)

    except Exception as exc:
        log.error("run_grade_pipeline_task_failed job_id=%s error=%s", job_id, exc)
        _update_job({"status": "failed", "error": str(exc)})
        _exc_str = str(exc)  # capture before Python deletes the except-clause binding

        async def _mark_failed():
            conn = await _asyncpg.connect(settings.DATABASE_URL)
            try:
                await conn.execute(
                    "UPDATE pipeline_jobs SET status='failed', completed_at=NOW(), error=$2 WHERE job_id=$1",
                    job_id,
                    _exc_str,
                )
            finally:
                await conn.close()

        try:
            import asyncpg as _asyncpg

            _run_async(_mark_failed())
        except Exception:
            pass


@celery_app.task(name="src.auth.tasks.promote_student_grades")
def promote_student_grades() -> None:
    """
    Increment grade for all active students (grade < 12) on GRADE_PROMOTION_DATE.

    Runs daily at 00:05 UTC; is a no-op unless today matches the configured date.
    After promotion, invalidates all ent:* and cur:* Redis keys.
    """
    from datetime import date

    promotion_date = getattr(settings, "GRADE_PROMOTION_DATE", None)
    if not promotion_date:
        return  # not configured

    today_md = date.today().strftime("%m-%d")
    if today_md != promotion_date:
        return  # not promotion day

    log.info("grade_promotion_starting date=%s", today_md)

    async def _promote():
        import asyncpg as _asyncpg
        import redis.asyncio as _aioredis

        conn = await _asyncpg.connect(settings.DATABASE_URL)
        try:
            result = await conn.execute(
                "UPDATE students SET grade = LEAST(grade + 1, 12) WHERE account_status = 'active' AND grade < 12"
            )
            log.info("grade_promotion_complete result=%s", result)
        finally:
            await conn.close()

        # Invalidate entitlement and curriculum resolver caches.
        # Patterns cover both school-namespaced keys (ADR-001 Decision 3) and
        # legacy unscoped keys (demo students / unaffiliated students).
        redis_client = await _aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        try:
            for pattern in ("school:*:ent:*", "school:*:cur:*", "ent:*", "cur:*"):
                cursor = 0
                while True:
                    cursor, keys = await redis_client.scan(cursor, match=pattern, count=200)
                    if keys:
                        await redis_client.delete(*keys)
                    if cursor == 0:
                        break
            log.info("grade_promotion_cache_invalidated")
        finally:
            await redis_client.close()

    _run_async(_promote())


# ── Phase 11: Teacher Reporting Dashboard tasks ───────────────────────────────


@celery_app.task(name="src.auth.tasks.refresh_report_views_task")
def refresh_report_views_task() -> None:
    """
    Nightly materialized view refresh for teacher report performance.

    Runs at 02:00 UTC via Celery Beat.
    Views: mv_class_summary, mv_student_progress, mv_feedback_summary.
    """
    import asyncpg as _asyncpg

    async def _refresh():
        pool = await _asyncpg.create_pool(settings.DATABASE_URL, min_size=1, max_size=2)
        try:
            async with pool.acquire() as conn:
                for view in ("mv_class_summary", "mv_student_progress", "mv_feedback_summary"):
                    await conn.execute(f"REFRESH MATERIALIZED VIEW {view}")
            log.info("report_views_refreshed_nightly")
        finally:
            await pool.close()

    _run_async(_refresh())


@celery_app.task(name="src.auth.tasks.evaluate_report_alerts_task")
def evaluate_report_alerts_task() -> None:
    """
    Daily alert evaluation at 06:00 UTC.

    For each school with alert settings, checks configured thresholds
    (pass rate, inactive students, feedback volume) and inserts a
    report_alerts row for any breach. Sends email notification if
    new_feedback_immediate is enabled (stub — real email via SendGrid).
    """
    import asyncpg as _asyncpg

    async def _evaluate():
        pool = await _asyncpg.create_pool(settings.DATABASE_URL, min_size=1, max_size=3)
        try:
            async with pool.acquire() as conn:
                settings_rows = await conn.fetch(
                    "SELECT school_id::text, pass_rate_threshold, inactive_days_threshold FROM report_alert_settings"
                )
                for s in settings_rows:
                    school_id = s["school_id"]
                    # Check pass rate breach per unit
                    breach_rows = await conn.fetch(
                        """
                        SELECT ps.unit_id,
                            ROUND(100.0 * COUNT(*) FILTER (WHERE ps.attempt_number = 1 AND ps.passed AND ps.completed)
                                / NULLIF(COUNT(DISTINCT ps.student_id) FILTER (WHERE ps.attempt_number = 1 AND ps.completed), 0), 1)
                                AS pass_rate
                        FROM progress_sessions ps
                        INNER JOIN school_enrolments se ON se.student_id = ps.student_id
                        WHERE se.school_id = $1 AND se.status = 'active'
                        GROUP BY ps.unit_id
                        HAVING ROUND(100.0 * COUNT(*) FILTER (WHERE ps.attempt_number = 1 AND ps.passed AND ps.completed)
                            / NULLIF(COUNT(DISTINCT ps.student_id) FILTER (WHERE ps.attempt_number = 1 AND ps.completed), 0), 1)
                            < $2
                        """,
                        uuid.UUID(school_id),
                        s["pass_rate_threshold"],
                    )
                    for br in breach_rows:
                        await conn.execute(
                            """
                            INSERT INTO report_alerts (school_id, alert_type, details)
                            VALUES ($1, 'pass_rate_breach', $2::jsonb)
                            ON CONFLICT DO NOTHING
                            """,
                            uuid.UUID(school_id),
                            json.dumps(
                                {"unit_id": br["unit_id"], "pass_rate": float(br["pass_rate"] or 0)}
                            ),
                        )
            log.info("report_alerts_evaluated")
        finally:
            await pool.close()

    _run_async(_evaluate())


@celery_app.task(name="src.auth.tasks.send_weekly_digest_task")
def send_weekly_digest_task() -> None:
    """
    Weekly digest email sent Monday 08:00 UTC.

    For each active digest_subscription:
      1. Queries the past 7 days of school activity (active students,
         struggling units, unreviewed feedback count).
      2. Renders a plain-text + HTML email body.
      3. Sends via SendGrid (SENDGRID_API_KEY in config).
         Falls back to logging only when the key is not configured.
    """
    from datetime import datetime, timedelta

    import asyncpg as _asyncpg

    week_start = (datetime.now(UTC) - timedelta(days=7)).isoformat()

    async def _digest():
        pool = await _asyncpg.create_pool(settings.DATABASE_URL, min_size=1, max_size=2)
        try:
            async with pool.acquire() as conn:
                subs = await conn.fetch(
                    "SELECT subscription_id::text, school_id::text, email, timezone "
                    "FROM digest_subscriptions WHERE enabled"
                )
                log.info("weekly_digest_sending", count=len(subs))

                for sub in subs:
                    school_id = uuid.UUID(sub["school_id"])

                    # Active students (at least one lesson view in the past 7 days)
                    active_row = await conn.fetchrow(
                        """
                        SELECT COUNT(DISTINCT lv.student_id) AS active_students
                        FROM lesson_views lv
                        INNER JOIN school_enrolments se ON se.student_id = lv.student_id
                        WHERE se.school_id = $1 AND se.status = 'active'
                          AND lv.started_at >= $2
                        """,
                        school_id,
                        week_start,
                    )
                    active_students = active_row["active_students"] if active_row else 0

                    # Struggling units (first-attempt pass rate < 60% this week)
                    struggling_rows = await conn.fetch(
                        """
                        SELECT ps.unit_id,
                            ROUND(100.0 * COUNT(*) FILTER (
                                WHERE ps.attempt_number = 1 AND ps.passed AND ps.completed
                            ) / NULLIF(COUNT(*) FILTER (
                                WHERE ps.attempt_number = 1 AND ps.completed
                            ), 0), 1) AS pass_rate
                        FROM progress_sessions ps
                        INNER JOIN school_enrolments se ON se.student_id = ps.student_id
                        WHERE se.school_id = $1 AND se.status = 'active'
                          AND ps.started_at >= $2
                        GROUP BY ps.unit_id
                        HAVING ROUND(100.0 * COUNT(*) FILTER (
                            WHERE ps.attempt_number = 1 AND ps.passed AND ps.completed
                        ) / NULLIF(COUNT(*) FILTER (
                            WHERE ps.attempt_number = 1 AND ps.completed
                        ), 0), 1) < 60
                        ORDER BY pass_rate ASC
                        LIMIT 5
                        """,
                        school_id,
                        week_start,
                    )

                    # Unreviewed feedback count
                    fb_row = await conn.fetchrow(
                        """
                        SELECT COUNT(*) AS cnt FROM feedback f
                        INNER JOIN school_enrolments se ON se.student_id = f.student_id
                        WHERE se.school_id = $1 AND se.status = 'active' AND NOT f.reviewed
                        """,
                        school_id,
                    )
                    unreviewed_feedback = fb_row["cnt"] if fb_row else 0

                    # Build email body
                    struggling_lines = (
                        "\n".join(
                            f"  - {r['unit_id']}: {r['pass_rate']}% pass rate"
                            for r in struggling_rows
                        )
                        or "  None — great week!"
                    )

                    plain_body = (
                        f"StudyBuddy Weekly Digest\n"
                        f"{'=' * 40}\n\n"
                        f"Active students this week: {active_students}\n\n"
                        f"Struggling units (pass rate < 60%):\n{struggling_lines}\n\n"
                        f"Unreviewed student feedback: {unreviewed_feedback}\n\n"
                        f"Log in to your teacher dashboard for full details.\n"
                    )

                    html_body = (
                        "<h2>StudyBuddy Weekly Digest</h2>"
                        f"<p><strong>Active students this week:</strong> {active_students}</p>"
                        "<p><strong>Struggling units (pass rate &lt; 60%):</strong></p><ul>"
                        + "".join(
                            f"<li>{r['unit_id']}: {r['pass_rate']}% pass rate</li>"
                            for r in struggling_rows
                        )
                        + ("</ul>" if struggling_rows else "<li>None — great week!</li></ul>")
                        + f"<p><strong>Unreviewed student feedback:</strong> {unreviewed_feedback}</p>"
                        "<p>Log in to your teacher dashboard for full details.</p>"
                    )

                    log.info(
                        "weekly_digest_prepared",
                        school_id=sub["school_id"],
                        email=sub["email"],
                        active_students=active_students,
                        struggling_units=len(struggling_rows),
                        unreviewed_feedback=unreviewed_feedback,
                    )

                    if settings.SENDGRID_API_KEY:
                        try:
                            import httpx as _httpx

                            _httpx.post(
                                "https://api.sendgrid.com/v3/mail/send",
                                headers={"Authorization": f"Bearer {settings.SENDGRID_API_KEY}"},
                                json={
                                    "personalizations": [{"to": [{"email": sub["email"]}]}],
                                    "from": {"email": settings.EMAIL_FROM},
                                    "subject": "StudyBuddy Weekly Digest",
                                    "content": [
                                        {"type": "text/plain", "value": plain_body},
                                        {"type": "text/html", "value": html_body},
                                    ],
                                },
                                timeout=10,
                            )
                            log.info("weekly_digest_sent email=%s", sub["email"])
                        except Exception as exc:
                            log.warning(
                                "weekly_digest_send_failed email=%s error=%s", sub["email"], exc
                            )
        finally:
            await pool.close()

    _run_async(_digest())


@celery_app.task(name="src.auth.tasks.export_report_task")
def export_report_task(
    export_id: str,
    school_id: str,
    report_type: str,
    filters: dict,
) -> None:
    """
    Generate a CSV export and write to CONTENT_STORE_PATH/exports/{export_id}.csv.

    Triggered by POST /reports/school/{school_id}/export. The download
    endpoint serves the file once it exists.
    """
    import csv as _csv
    import os as _os

    import asyncpg as _asyncpg

    async def _export():
        pool = await _asyncpg.create_pool(settings.DATABASE_URL, min_size=1, max_size=2)
        try:
            async with pool.acquire() as conn:
                # Minimal export: enrolled students + progress summary
                rows = await conn.fetch(
                    """
                    SELECT s.name, s.grade, s.email,
                           COUNT(DISTINCT ps.unit_id) FILTER (WHERE ps.passed) AS units_passed,
                           ROUND(AVG(ps.score) FILTER (WHERE ps.completed)::numeric, 1) AS avg_score
                    FROM school_enrolments se
                    JOIN students s ON s.student_id = se.student_id
                    LEFT JOIN progress_sessions ps ON ps.student_id = se.student_id
                    WHERE se.school_id = $1 AND se.status = 'active'
                    GROUP BY s.name, s.grade, s.email
                    ORDER BY s.name
                    """,
                    uuid.UUID(school_id),
                )
        finally:
            await pool.close()

        export_dir = _os.path.join(settings.CONTENT_STORE_PATH, "exports")
        _os.makedirs(export_dir, exist_ok=True)
        export_path = _os.path.join(export_dir, f"{export_id}.csv")

        with open(export_path, "w", newline="") as f:
            writer = _csv.DictWriter(
                f, fieldnames=["name", "grade", "email", "units_passed", "avg_score"]
            )
            writer.writeheader()
            for r in rows:
                writer.writerow(dict(r))

        log.info(
            "report_export_complete",
            export_id=export_id,
            school_id=school_id,
            report_type=report_type,
        )

    _run_async(_export())


# ── Demo account sweep ────────────────────────────────────────────────────────


@celery_app.task(name="src.auth.tasks.sweep_expired_demo_accounts")
def sweep_expired_demo_accounts() -> None:
    """
    Nightly sweep: expire demo accounts whose TTL has elapsed.

    For each expired demo_account:
      1. Soft-delete the associated students row (account_status='deleted').
      2. Mark demo_requests.status = 'expired'.
      3. Delete the demo_accounts row (hard-delete; student row kept for GDPR audit).

    This task is idempotent — re-running produces no side effects.
    """
    from config import settings as cfg

    async def _sweep() -> None:
        import asyncpg as _asyncpg

        pool = await _asyncpg.create_pool(
            cfg.DATABASE_URL, min_size=1, max_size=2, statement_cache_size=0
        )
        try:
            async with pool.acquire() as conn:
                expired = await conn.fetch(
                    """
                    SELECT da.id, da.student_id, da.request_id
                    FROM demo_accounts da
                    WHERE da.expires_at < NOW()
                      AND da.revoked_at IS NULL
                    """
                )
                if not expired:
                    log.info("demo_sweep_no_expired")
                    return

                for row in expired:
                    await conn.execute(
                        "UPDATE students SET account_status='deleted' WHERE student_id=$1",
                        row["student_id"],
                    )
                    await conn.execute(
                        "UPDATE demo_requests SET status='expired' WHERE id=$1",
                        row["request_id"],
                    )
                    await conn.execute(
                        "DELETE FROM demo_accounts WHERE id=$1",
                        row["id"],
                    )

                log.info("demo_sweep_complete", swept=len(expired))
        finally:
            await pool.close()

    _run_async(_sweep())


# ── Demo email tasks ──────────────────────────────────────────────────────────


@celery_app.task(
    name="src.auth.tasks.send_demo_verification_email_task",
    bind=True,
    max_retries=3,
)
def send_demo_verification_email_task(self, email: str, token: str) -> None:
    """Send the demo email-verification link. Retries up to 3× on SMTP failure."""
    from src.email.service import send_verification_email

    try:
        _run_async(send_verification_email(email, token))
    except Exception as exc:
        raise self.retry(exc=exc, countdown=30)


@celery_app.task(
    name="src.auth.tasks.send_demo_credentials_email_task",
    bind=True,
    max_retries=3,
)
def send_demo_credentials_email_task(self, email: str, password: str) -> None:
    """Send demo account credentials after successful verification. Retries 3× on failure."""
    from src.email.service import send_credentials_email

    try:
        _run_async(send_credentials_email(email, password))
    except Exception as exc:
        raise self.retry(exc=exc, countdown=30)


# ── Demo teacher Celery tasks ─────────────────────────────────────────────────


@celery_app.task(name="src.auth.tasks.sweep_expired_demo_teacher_accounts")
def sweep_expired_demo_teacher_accounts() -> None:
    """
    Nightly sweep: expire demo teacher accounts whose TTL has elapsed.

    For each expired demo_teacher_account:
      1. Soft-delete the associated teachers row (account_status='deleted').
      2. Mark demo_teacher_requests.status = 'expired'.
      3. Delete the demo_teacher_accounts row (hard-delete).

    This task is idempotent — re-running produces no side effects.
    """
    from config import settings as cfg

    async def _sweep() -> None:
        import asyncpg as _asyncpg

        pool = await _asyncpg.create_pool(
            cfg.DATABASE_URL, min_size=1, max_size=2, statement_cache_size=0
        )
        try:
            async with pool.acquire() as conn:
                expired = await conn.fetch(
                    """
                    SELECT dta.id, dta.teacher_id, dta.request_id
                    FROM demo_teacher_accounts dta
                    WHERE dta.expires_at < NOW()
                      AND dta.revoked_at IS NULL
                    """
                )
                if not expired:
                    log.info("demo_teacher_sweep_no_expired")
                    return

                for row in expired:
                    await conn.execute(
                        "UPDATE teachers SET account_status='deleted' WHERE teacher_id=$1",
                        row["teacher_id"],
                    )
                    await conn.execute(
                        "UPDATE demo_teacher_requests SET status='expired' WHERE id=$1",
                        row["request_id"],
                    )
                    await conn.execute(
                        "DELETE FROM demo_teacher_accounts WHERE id=$1",
                        row["id"],
                    )

                log.info("demo_teacher_sweep_complete", swept=len(expired))
        finally:
            await pool.close()

    _run_async(_sweep())


@celery_app.task(
    name="src.auth.tasks.send_demo_teacher_verification_email_task",
    bind=True,
    max_retries=3,
)
def send_demo_teacher_verification_email_task(self, email: str, token: str) -> None:
    """Send the demo teacher email-verification link. Retries up to 3× on SMTP failure."""
    from src.email.service import send_teacher_verification_email

    try:
        _run_async(send_teacher_verification_email(email, token))
    except Exception as exc:
        raise self.retry(exc=exc, countdown=30)


@celery_app.task(
    name="src.auth.tasks.send_demo_teacher_credentials_email_task",
    bind=True,
    max_retries=3,
)
def send_demo_teacher_credentials_email_task(self, email: str, password: str) -> None:
    """Send demo teacher credentials after successful verification. Retries 3× on failure."""
    from src.email.service import send_teacher_credentials_email

    try:
        _run_async(send_teacher_credentials_email(email, password))
    except Exception as exc:
        raise self.retry(exc=exc, countdown=30)


@celery_app.task(name="src.auth.tasks.invalidate_school_entitlement_cache_task")
def invalidate_school_entitlement_cache_task(school_id: str) -> None:
    """
    Bulk-delete all school:{school_id}:* Redis keys after a subscription state change.

    Called after any school subscription event (activate / cancel / payment fail)
    so that enrolled students' next content request re-derives entitlement from DB.
    The school:{school_id}:ent key is deleted synchronously in
    expire_school_entitlement_cache() before this task is dispatched.

    Uses school-prefix SCAN (ADR-001 Decision 3) — no need to enumerate enrolled
    student IDs from the DB; the namespace covers all per-student ent + cur keys.
    """
    from config import settings as cfg
    from src.core.cache_keys import school_scan_pattern

    async def _invalidate() -> None:
        import redis.asyncio as _aioredis

        redis_client = await _aioredis.from_url(cfg.REDIS_URL, decode_responses=True)
        pattern = school_scan_pattern(school_id)
        count = 0
        try:
            cursor = 0
            while True:
                cursor, keys = await redis_client.scan(cursor, match=pattern, count=200)
                if keys:
                    await redis_client.delete(*keys)
                    count += len(keys)
                if cursor == 0:
                    break
        finally:
            await redis_client.aclose()

        log.info(
            "invalidate_school_entitlement_cache school_id=%s keys_deleted=%d",
            school_id,
            count,
        )

    _run_async(_invalidate())


# ── Storage quota reconcile ───────────────────────────────────────────────────


@celery_app.task(name="src.auth.tasks.reconcile_school_storage_task")
def reconcile_school_storage_task() -> None:
    """
    Nightly reconcile: recompute used_bytes for every school from pipeline_jobs.

    The pipeline worker increments school_storage_quotas.used_bytes atomically
    after each successful job.  This task recomputes from scratch nightly so any
    drift (manual deletions, failed increments, Phase B curriculum deletes) is
    corrected before the school admin opens the retention dashboard.

    Only completed pipeline jobs with a non-null payload_bytes contribute.
    Runs at 01:00 UTC (after the nightly retention status sweep).
    This task is idempotent — re-running is safe.
    """
    from config import settings as cfg

    async def _reconcile() -> None:
        import asyncpg as _asyncpg

        pool = await _asyncpg.create_pool(
            cfg.DATABASE_URL, min_size=1, max_size=2, statement_cache_size=0
        )
        try:
            async with pool.acquire() as conn:
                # Bypass RLS — this is an internal admin operation.
                await conn.execute(
                    "SELECT set_config('app.current_school_id', 'bypass', false)"
                )

                # Aggregate payload_bytes per school across all completed jobs.
                rows = await conn.fetch(
                    """
                    SELECT school_id::text, COALESCE(SUM(payload_bytes), 0) AS total_bytes
                    FROM pipeline_jobs
                    WHERE status = 'completed'
                      AND payload_bytes IS NOT NULL
                      AND school_id IS NOT NULL
                    GROUP BY school_id
                    """
                )

                updated = 0
                for row in rows:
                    result = await conn.execute(
                        """
                        UPDATE school_storage_quotas
                        SET used_bytes = $1, updated_at = NOW()
                        WHERE school_id = $2::uuid
                        """,
                        int(row["total_bytes"]),
                        row["school_id"],
                    )
                    if result != "UPDATE 0":
                        updated += 1

                # Zero out schools that have no completed jobs (e.g. all content deleted).
                await conn.execute(
                    """
                    UPDATE school_storage_quotas
                    SET used_bytes = 0, updated_at = NOW()
                    WHERE school_id NOT IN (
                        SELECT DISTINCT school_id
                        FROM pipeline_jobs
                        WHERE status = 'completed'
                          AND payload_bytes IS NOT NULL
                          AND school_id IS NOT NULL
                    )
                    AND used_bytes > 0
                    """
                )

                log.info("storage_reconcile_complete schools_updated=%d", updated)
        finally:
            await pool.close()

    _run_async(_reconcile())


# ── Retention lifecycle tasks ─────────────────────────────────────────────────
#
# All five tasks share the same _db_bypass() helper (RLS bypass) and
# a stub _queue_retention_email() that logs the intent.  Phase E will
# replace the stub with real email dispatch.
#
# Idempotency strategy:
#   - sweep_expired_curricula: state change (active → unavailable) is its own
#     idempotency guard — subsequent runs find no rows matching the WHERE clause.
#   - check_*: fire only on the exact calendar date matching the notification
#     window, so each notification triggers at most once per curriculum.
#   - purge_expired_curricula: sets retention_status = 'purged' before deleting
#     files, so a partial failure on file deletion is safely retried.


# ── Task 1: 30-day pre-expiry warnings ───────────────────────────────────────


@celery_app.task(name="src.auth.tasks.check_retention_pre_expiry_warnings")
def check_retention_pre_expiry_warnings() -> None:
    """
    Daily: send a 30-day pre-expiry warning for school curricula expiring in
    exactly 30 days. No DB state change — email notification only.
    """
    from config import settings as cfg
    from src.school.retention_service import send_pre_expiry_warnings

    async def _run() -> None:
        import asyncpg as _asyncpg

        conn = await _asyncpg.connect(cfg.DATABASE_URL)
        try:
            await conn.execute(
                "SELECT set_config('app.current_school_id', 'bypass', false)"
            )
            await send_pre_expiry_warnings(conn)
        finally:
            await conn.close()

    _run_async(_run())


# ── Task 2: Expiry sweep (active → unavailable) ───────────────────────────────


@celery_app.task(name="src.auth.tasks.sweep_expired_curricula")
def sweep_expired_curricula() -> None:
    """
    Daily: transition school curricula from 'active' to 'unavailable' when
    their expires_at has passed. Sets grace_until = expires_at + 180 days.
    Idempotent — only 'active' rows are touched.
    """
    from config import settings as cfg
    from src.school.retention_service import expire_active_curricula

    async def _run() -> None:
        import asyncpg as _asyncpg

        conn = await _asyncpg.connect(cfg.DATABASE_URL)
        try:
            await conn.execute(
                "SELECT set_config('app.current_school_id', 'bypass', false)"
            )
            await expire_active_curricula(conn)
        finally:
            await conn.close()

    _run_async(_run())


# ── Task 3: 90-day grace period reminder ─────────────────────────────────────


@celery_app.task(name="src.auth.tasks.check_retention_grace_reminders")
def check_retention_grace_reminders() -> None:
    """
    Daily: send a reminder email on day 90 of the grace period
    ((grace_until - 90 days)::date == today). No DB state change.
    """
    from config import settings as cfg
    from src.school.retention_service import send_grace_90day_reminders

    async def _run() -> None:
        import asyncpg as _asyncpg

        conn = await _asyncpg.connect(cfg.DATABASE_URL)
        try:
            await conn.execute(
                "SELECT set_config('app.current_school_id', 'bypass', false)"
            )
            await send_grace_90day_reminders(conn)
        finally:
            await conn.close()

    _run_async(_run())


# ── Task 4: 30-days-to-purge warning (day 150 of grace) ─────────────────────


@celery_app.task(name="src.auth.tasks.check_retention_purge_warnings")
def check_retention_purge_warnings() -> None:
    """
    Daily: send an urgent warning 30 days before purge (day 150 of 180-day grace).
    ((grace_until - 30 days)::date == today). No DB state change.
    """
    from config import settings as cfg
    from src.school.retention_service import send_purge_30day_warnings

    async def _run() -> None:
        import asyncpg as _asyncpg

        conn = await _asyncpg.connect(cfg.DATABASE_URL)
        try:
            await conn.execute(
                "SELECT set_config('app.current_school_id', 'bypass', false)"
            )
            await send_purge_30day_warnings(conn)
        finally:
            await conn.close()

    _run_async(_run())


# ── Retention email task ──────────────────────────────────────────────────────


@celery_app.task(
    name="src.auth.tasks.send_retention_email_task",
    bind=True,
    max_retries=3,
)
def send_retention_email_task(
    self,
    to_email: str,
    template: str,
    grade: int,
    curriculum_name: str,
    expires_date: str = "",
    grace_date: str = "",
    purge_date: str = "",
    days_remaining: int = 0,
) -> None:
    """
    Send one of the five retention lifecycle emails to a school_admin contact.
    Retries up to 3× on SMTP failure (30-second backoff).

    template must be one of:
      retention_pre_expiry_warning
      retention_expiry_notification
      retention_grace_90day_reminder
      retention_purge_warning_30day
      retention_purge_complete
    """
    from src.email.service import send_retention_email

    try:
        _run_async(
            send_retention_email(
                to_email=to_email,
                template=template,
                grade=grade,
                curriculum_name=curriculum_name,
                expires_date=expires_date,
                grace_date=grace_date,
                purge_date=purge_date,
                days_remaining=days_remaining,
            )
        )
    except Exception as exc:
        raise self.retry(exc=exc, countdown=30)


# ── Task 5: File purge (day 180 of grace) ────────────────────────────────────


@celery_app.task(name="src.auth.tasks.purge_expired_curricula")
def purge_expired_curricula() -> None:
    """
    Daily: permanently delete content files for curricula whose 180-day grace
    period has elapsed (grace_until <= NOW(), retention_status = 'unavailable').

    Sets retention_status = 'purged' in DB before deleting files so students
    lose access even during slow file deletion.  FERPA: student progress
    records are NOT deleted.
    """
    from config import settings as cfg
    from src.core.storage import LocalStorage
    from src.school.retention_service import purge_grace_expired

    async def _run() -> None:
        import asyncpg as _asyncpg

        conn = await _asyncpg.connect(cfg.DATABASE_URL)
        try:
            await conn.execute(
                "SELECT set_config('app.current_school_id', 'bypass', false)"
            )
            storage = LocalStorage(root=getattr(cfg, "CONTENT_STORE_PATH", "/tmp/studybuddy-content"))
            await purge_grace_expired(conn, storage)
        finally:
            await conn.close()

    _run_async(_run())
