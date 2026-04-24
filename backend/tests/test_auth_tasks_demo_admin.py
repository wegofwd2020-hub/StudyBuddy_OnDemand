"""
tests/test_auth_tasks_demo_admin.py

Demo / admin / infra Celery tasks from src/auth/tasks.py. PR #7 of #261.

Covers the remaining zero-coverage tasks:
  - promote_student_grades                      — annual grade promotion
  - sweep_expired_demo_accounts                 — nightly student demo sweep
  - sweep_expired_demo_teacher_accounts         — nightly teacher demo sweep
  - send_demo_verification_email_task           — student demo verification
  - send_demo_credentials_email_task            — student demo creds
  - send_demo_teacher_verification_email_task   — teacher demo verification
  - send_demo_teacher_credentials_email_task    — teacher demo creds
  - invalidate_school_entitlement_cache_task    — SCAN + DEL school:{id}:*
  - poll_infra_metrics                          — Celery queue depth gauges
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _make_pool(conn: AsyncMock) -> MagicMock:
    pool = MagicMock()
    pool.close = AsyncMock()
    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=conn)
    cm.__aexit__ = AsyncMock(return_value=None)
    pool.acquire = MagicMock(return_value=cm)
    return pool


# ── promote_student_grades ────────────────────────────────────────────────────


def test_promote_student_grades_noop_when_date_not_configured():
    from src.auth.tasks import promote_student_grades

    with patch("src.auth.tasks.settings.GRADE_PROMOTION_DATE", None):
        # Must not raise or touch DB.
        promote_student_grades()


def test_promote_student_grades_noop_when_today_does_not_match():
    from src.auth.tasks import promote_student_grades

    # Set a date that is almost certainly not today (Feb 29).
    with (
        patch("src.auth.tasks.settings.GRADE_PROMOTION_DATE", "02-29"),
        patch("asyncpg.connect") as mock_connect,
    ):
        promote_student_grades()

    mock_connect.assert_not_called()


def test_promote_student_grades_promotes_and_invalidates_cache():
    """On promotion day: UPDATE students + SCAN+DELETE ent:*/cur:* keys."""
    from datetime import date

    from src.auth.tasks import promote_student_grades

    today_md = date.today().strftime("%m-%d")

    conn = AsyncMock()
    conn.execute.return_value = "UPDATE 42"

    # Redis SCAN protocol: returns (cursor, keys). Emit keys for each of the
    # 4 patterns, terminate with cursor=0. Async scan+delete+close.
    scan_calls = [
        (0, ["school:a:ent:1", "school:b:ent:2"]),  # school:*:ent:*
        (0, ["school:a:cur:1"]),                     # school:*:cur:*
        (0, ["ent:student-x"]),                      # ent:*
        (0, []),                                     # cur:* — nothing
    ]
    redis_client = AsyncMock()
    redis_client.scan.side_effect = scan_calls

    with (
        patch("src.auth.tasks.settings.GRADE_PROMOTION_DATE", today_md),
        patch("asyncpg.connect", new=AsyncMock(return_value=conn)),
        patch("redis.asyncio.from_url", new=AsyncMock(return_value=redis_client)),
    ):
        promote_student_grades()

    # The UPDATE was executed.
    update_sql = conn.execute.await_args_list[0].args[0]
    assert "UPDATE students" in update_sql
    assert "LEAST(grade + 1, 12)" in update_sql
    # delete() called at least once (for patterns that yielded keys).
    assert redis_client.delete.await_count >= 1
    redis_client.close.assert_awaited_once()


# ── sweep_expired_demo_accounts ───────────────────────────────────────────────


def test_sweep_expired_demo_accounts_noop_when_nothing_expired():
    from src.auth.tasks import sweep_expired_demo_accounts

    conn = AsyncMock()
    conn.fetch.return_value = []
    pool = _make_pool(conn)

    with patch("asyncpg.create_pool", new=AsyncMock(return_value=pool)):
        sweep_expired_demo_accounts()

    # Only the SELECT ran — no UPDATE / DELETE.
    conn.execute.assert_not_called()
    pool.close.assert_awaited_once()


def test_sweep_expired_demo_accounts_soft_deletes_and_hard_deletes():
    from src.auth.tasks import sweep_expired_demo_accounts

    student_id = uuid.uuid4()
    request_id = uuid.uuid4()
    demo_id = uuid.uuid4()

    conn = AsyncMock()
    conn.fetch.return_value = [
        {"id": demo_id, "student_id": student_id, "request_id": request_id}
    ]
    pool = _make_pool(conn)

    with patch("asyncpg.create_pool", new=AsyncMock(return_value=pool)):
        sweep_expired_demo_accounts()

    # Three writes per expired demo: students soft-delete, demo_requests update, demo_accounts delete.
    assert conn.execute.await_count == 3
    sqls = [c.args[0] for c in conn.execute.await_args_list]
    assert any("UPDATE students SET account_status='deleted'" in s for s in sqls)
    assert any("UPDATE demo_requests SET status='expired'" in s for s in sqls)
    assert any("DELETE FROM demo_accounts" in s for s in sqls)


# ── sweep_expired_demo_teacher_accounts ───────────────────────────────────────


def test_sweep_expired_demo_teacher_accounts_soft_deletes_teacher_row():
    from src.auth.tasks import sweep_expired_demo_teacher_accounts

    conn = AsyncMock()
    conn.fetch.return_value = [
        {
            "id": uuid.uuid4(),
            "teacher_id": uuid.uuid4(),
            "request_id": uuid.uuid4(),
        }
    ]
    pool = _make_pool(conn)

    with patch("asyncpg.create_pool", new=AsyncMock(return_value=pool)):
        sweep_expired_demo_teacher_accounts()

    sqls = [c.args[0] for c in conn.execute.await_args_list]
    assert any("UPDATE teachers SET account_status='deleted'" in s for s in sqls)
    assert any("UPDATE demo_teacher_requests" in s for s in sqls)
    assert any("DELETE FROM demo_teacher_accounts" in s for s in sqls)


def test_sweep_expired_demo_teacher_accounts_noop_when_nothing_expired():
    from src.auth.tasks import sweep_expired_demo_teacher_accounts

    conn = AsyncMock()
    conn.fetch.return_value = []
    pool = _make_pool(conn)

    with patch("asyncpg.create_pool", new=AsyncMock(return_value=pool)):
        sweep_expired_demo_teacher_accounts()

    conn.execute.assert_not_called()


# ── Demo email tasks (parametrised — all 4 share the same wrapper shape) ─────


@pytest.mark.parametrize(
    ("task_attr", "service_attr", "args"),
    [
        ("send_demo_verification_email_task", "send_verification_email", ("e@x.com", "tok-1")),
        ("send_demo_credentials_email_task", "send_credentials_email", ("e@x.com", "pw-1")),
        (
            "send_demo_teacher_verification_email_task",
            "send_teacher_verification_email",
            ("t@x.com", "tok-2"),
        ),
        (
            "send_demo_teacher_credentials_email_task",
            "send_teacher_credentials_email",
            ("t@x.com", "pw-2"),
        ),
    ],
)
def test_demo_email_task_delegates_to_email_service(task_attr, service_attr, args):
    import src.auth.tasks as tasks_mod

    task = getattr(tasks_mod, task_attr)
    with patch(
        f"src.email.service.{service_attr}", new_callable=AsyncMock
    ) as mock_send:
        task.run(*args)

    mock_send.assert_awaited_once_with(*args)


@pytest.mark.parametrize(
    ("task_attr", "service_attr", "args"),
    [
        ("send_demo_verification_email_task", "send_verification_email", ("e@x.com", "tok-1")),
        ("send_demo_credentials_email_task", "send_credentials_email", ("e@x.com", "pw-1")),
        (
            "send_demo_teacher_verification_email_task",
            "send_teacher_verification_email",
            ("t@x.com", "tok-2"),
        ),
        (
            "send_demo_teacher_credentials_email_task",
            "send_teacher_credentials_email",
            ("t@x.com", "pw-2"),
        ),
    ],
)
def test_demo_email_task_retries_on_smtp_error(task_attr, service_attr, args):
    import src.auth.tasks as tasks_mod

    task = getattr(tasks_mod, task_attr)
    with patch(
        f"src.email.service.{service_attr}",
        new_callable=AsyncMock,
        side_effect=RuntimeError("smtp down"),
    ):
        with pytest.raises(Exception):
            task.run(*args)


# ── invalidate_school_entitlement_cache_task ─────────────────────────────────


def test_invalidate_school_entitlement_cache_task_scans_and_deletes():
    from src.auth.tasks import invalidate_school_entitlement_cache_task

    school_id = str(uuid.uuid4())

    redis_client = AsyncMock()
    # Two scan iterations, then terminator.
    redis_client.scan.side_effect = [
        (100, [f"school:{school_id}:ent:stu-1", f"school:{school_id}:cur:stu-1"]),
        (0, [f"school:{school_id}:ent:stu-2"]),
    ]

    with patch("redis.asyncio.from_url", new=AsyncMock(return_value=redis_client)):
        invalidate_school_entitlement_cache_task(school_id)

    # Two delete batches.
    assert redis_client.delete.await_count == 2
    redis_client.aclose.assert_awaited_once()


def test_invalidate_school_entitlement_cache_task_noop_when_no_keys():
    from src.auth.tasks import invalidate_school_entitlement_cache_task

    redis_client = AsyncMock()
    redis_client.scan.return_value = (0, [])

    with patch("redis.asyncio.from_url", new=AsyncMock(return_value=redis_client)):
        invalidate_school_entitlement_cache_task(str(uuid.uuid4()))

    redis_client.delete.assert_not_called()
    redis_client.aclose.assert_awaited_once()


# ── poll_infra_metrics ────────────────────────────────────────────────────────


def test_poll_infra_metrics_sets_queue_depth_for_each_queue():
    from src.auth.tasks import poll_infra_metrics

    r = MagicMock()
    r.llen = MagicMock(side_effect=[3, 0, 12])  # io, default, pipeline
    r.close = MagicMock()

    with patch("redis.from_url", return_value=r):
        poll_infra_metrics()

    # LLEN called for each of the 3 queues.
    assert r.llen.call_count == 3
    r.close.assert_called_once()


def test_poll_infra_metrics_swallows_errors():
    """Metrics failure must not interrupt the Beat schedule."""
    from src.auth.tasks import poll_infra_metrics

    with patch("redis.from_url", side_effect=RuntimeError("redis gone")):
        # Must not raise — metrics are best-effort.
        poll_infra_metrics()
