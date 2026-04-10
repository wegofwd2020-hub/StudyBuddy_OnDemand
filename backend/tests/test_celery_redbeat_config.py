"""
tests/test_celery_redbeat_config.py

Unit tests verifying that the Celery application is configured to use
RedBeat as its Beat scheduler with the expected settings.

These tests are purely structural — they inspect the celery_app.conf object
directly without starting a worker, connecting to Redis, or requiring any
external services.
"""
from __future__ import annotations

import pytest

from src.core.celery_app import celery_app


# ── Scheduler selection ───────────────────────────────────────────────────────


def test_beat_scheduler_is_redbeat():
    """RedBeat must be the configured Beat scheduler."""
    assert celery_app.conf.beat_scheduler == "redbeat.RedBeatScheduler"


# ── Redis connection ──────────────────────────────────────────────────────────


def test_redbeat_redis_url_is_set():
    """RedBeat must have a Redis URL to store schedule state."""
    url = celery_app.conf.redbeat_redis_url
    assert url, "redbeat_redis_url must not be empty"
    # Must be a Redis URL (redis:// or rediss://)
    assert url.startswith(("redis://", "rediss://")), (
        f"redbeat_redis_url must be a redis:// or rediss:// URL, got: {url!r}"
    )


def test_redbeat_redis_url_matches_broker():
    """RedBeat must use the same Redis as the Celery broker."""
    assert celery_app.conf.redbeat_redis_url == celery_app.conf.broker_url, (
        "redbeat_redis_url must point to the same Redis instance as the broker "
        "to avoid split-brain between schedule state and task dispatch"
    )


# ── Lock timeout ──────────────────────────────────────────────────────────────


def test_redbeat_lock_timeout_is_positive():
    """Lock timeout must be a positive integer."""
    timeout = celery_app.conf.redbeat_lock_timeout
    assert isinstance(timeout, int), f"Expected int, got {type(timeout)}"
    assert timeout > 0, f"redbeat_lock_timeout must be > 0, got {timeout}"


def test_redbeat_lock_timeout_is_at_least_60s():
    """Lock timeout must be at least 60 seconds — shorter values risk spurious failovers."""
    assert celery_app.conf.redbeat_lock_timeout >= 60, (
        f"redbeat_lock_timeout is {celery_app.conf.redbeat_lock_timeout}s; "
        "values below 60s risk the standby taking over during a normal slow cycle"
    )


def test_redbeat_lock_timeout_default_is_5_minutes():
    """Default lock timeout should be 300 seconds (5 minutes) as per issue #128."""
    from config import settings

    assert settings.REDBEAT_LOCK_TIMEOUT == 300, (
        f"Expected default REDBEAT_LOCK_TIMEOUT=300, got {settings.REDBEAT_LOCK_TIMEOUT}"
    )
    assert celery_app.conf.redbeat_lock_timeout == settings.REDBEAT_LOCK_TIMEOUT


# ── Key prefix ───────────────────────────────────────────────────────────────


def test_redbeat_key_prefix_is_set():
    """RedBeat must use a namespaced key prefix to avoid collisions with other Redis keys."""
    prefix = celery_app.conf.redbeat_key_prefix
    assert prefix, "redbeat_key_prefix must not be empty"
    assert prefix == "redbeat:", f"Expected 'redbeat:', got {prefix!r}"


# ── Beat schedule intact ──────────────────────────────────────────────────────


def test_beat_schedule_is_non_empty():
    """The beat_schedule dict must survive the RedBeat migration — no tasks lost."""
    schedule = celery_app.conf.beat_schedule
    assert schedule, "beat_schedule must not be empty"


def test_critical_beat_tasks_present():
    """Grade promotion, weekly digest, and report views must still be scheduled."""
    schedule = celery_app.conf.beat_schedule
    task_names = {entry["task"] for entry in schedule.values()}

    critical = {
        "src.auth.tasks.promote_student_grades",
        "src.auth.tasks.send_weekly_digest_task",
        "src.auth.tasks.refresh_report_views_task",
        "src.auth.tasks.evaluate_report_alerts_task",
    }
    missing = critical - task_names
    assert not missing, f"Critical beat tasks missing from schedule: {missing}"


def test_beat_schedule_has_expected_count():
    """Beat schedule should have at least 15 entries — a drop in count indicates a bug."""
    assert len(celery_app.conf.beat_schedule) >= 15, (
        f"Expected at least 15 beat schedule entries, found {len(celery_app.conf.beat_schedule)}"
    )
