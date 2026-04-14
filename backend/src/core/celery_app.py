"""
backend/src/core/celery_app.py

Shared Celery application instance for all StudyBuddy workers.

Previously the Celery app lived in src/auth/tasks — every non-auth module
(subscription, school, analytics, reports) imported from there, creating a
misleading auth dependency.  This module is the canonical home.

Workers are started with:
  celery -A src.core.celery_app worker -Q io,default --concurrency=4
  celery -A src.core.celery_app worker -Q pipeline --concurrency=2
  celery -A src.core.celery_app beat --loglevel=info

Beat is configured to use RedBeat (celery-redbeat) which stores the schedule
state in Redis instead of a local file.  Two Beat instances run simultaneously
(primary and standby); the primary holds a Redis lock that expires after
REDBEAT_LOCK_TIMEOUT seconds.  If the primary crashes, the standby acquires
the lock within one lock-timeout window and resumes task dispatch automatically,
eliminating the single-point-of-failure in the original file-based scheduler.

All task *implementations* remain in src/auth/tasks — they register onto
this Celery instance by importing celery_app from here.
"""

from __future__ import annotations

import asyncio

from celery import Celery
from celery.schedules import crontab
from config import settings

celery_app = Celery(
    "studybuddy",
    broker=settings.effective_celery_broker_url,
    # `include` is eager — Celery imports these modules at app construction so
    # every @celery_app.task decorator registers onto this instance before any
    # worker consumes a message. Without this, the task registry is empty at
    # worker boot and every incoming task is silently discarded as
    # "unregistered" — which is exactly what was happening to
    # run_curriculum_pipeline_task.
    include=["src.auth.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # ── RedBeat — distributed Beat scheduler ─────────────────────────────────
    # Stores schedule state in Redis so multiple Beat instances can safely
    # compete for the scheduler lock.  Only one instance dispatches tasks at
    # a time; the other waits and takes over within lock_timeout seconds if
    # the primary crashes.
    beat_scheduler="redbeat.RedBeatScheduler",
    redbeat_redis_url=settings.effective_celery_broker_url,
    redbeat_lock_timeout=settings.REDBEAT_LOCK_TIMEOUT,
    redbeat_key_prefix="redbeat:",
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
        "src.auth.tasks.check_teacher_seat_quotas": {"queue": "default"},
        # Retention lifecycle tasks
        "src.auth.tasks.check_retention_pre_expiry_warnings": {"queue": "default"},
        "src.auth.tasks.sweep_expired_curricula": {"queue": "default"},
        "src.auth.tasks.check_retention_grace_reminders": {"queue": "default"},
        "src.auth.tasks.check_retention_purge_warnings": {"queue": "default"},
        "src.auth.tasks.purge_expired_curricula": {"queue": "default"},
        "src.auth.tasks.send_retention_email_task": {"queue": "io"},
        "src.auth.tasks.send_payment_action_required_email_task": {"queue": "io"},
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
        "sweep-expired-demo-accounts-nightly": {
            "task": "src.auth.tasks.sweep_expired_demo_accounts",
            "schedule": crontab(hour=3, minute=0),
        },
        # Nightly demo teacher account sweep at 03:15 UTC.
        "sweep-expired-demo-teacher-accounts-nightly": {
            "task": "src.auth.tasks.sweep_expired_demo_teacher_accounts",
            "schedule": crontab(hour=3, minute=15),
        },
        # Nightly storage quota reconcile at 01:00 UTC.
        "reconcile-school-storage-nightly": {
            "task": "src.auth.tasks.reconcile_school_storage_task",
            "schedule": crontab(hour=1, minute=0),
        },
        # Retention lifecycle — daily from 02:00 UTC, offset 5 min each.
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
        # Daily independent teacher seat-quota check at 07:00 UTC.
        "check-teacher-seat-quotas-daily": {
            "task": "src.auth.tasks.check_teacher_seat_quotas",
            "schedule": crontab(hour=7, minute=0),
        },
    },
)


def _run_async(coro):
    """Run an async coroutine from a sync Celery task body."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# Import task modules so their @celery_app.task decorators register onto
# this instance when a worker process starts.
# Deferred to avoid circular imports at module load time — tasks themselves
# import from src.core.celery_app, so this import must come last.
def autodiscover() -> None:
    """Register all task modules with this Celery app. Called by worker entrypoint."""
    celery_app.autodiscover_tasks(["src.auth.tasks"])
