"""
tests/test_auth_tasks_reports.py

Reports-cluster Celery tasks from src/auth/tasks.py. PR #6 of Issue #261.

Covers four zero-coverage tasks for teacher report scaffolding:
  - refresh_report_views_task   — nightly MV refresh
  - evaluate_report_alerts_task — threshold breaches → report_alerts rows
  - send_weekly_digest_task     — Monday digest email via SendGrid
  - export_report_task          — async CSV export to CONTENT_STORE_PATH/exports/

Same pattern as PRs #267–270. These tasks are not retry-wrapped — they
run on Celery Beat and rely on log-and-continue semantics for transient
failures.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch


def _make_pool(conn: AsyncMock) -> MagicMock:
    """asyncpg pool where `async with pool.acquire() as conn` yields conn."""
    pool = MagicMock()
    pool.close = AsyncMock()
    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=conn)
    cm.__aexit__ = AsyncMock(return_value=None)
    pool.acquire = MagicMock(return_value=cm)
    return pool


# ── refresh_report_views_task ─────────────────────────────────────────────────


def test_refresh_report_views_task_refreshes_all_three_views():
    from src.auth.tasks import refresh_report_views_task

    conn = AsyncMock()
    pool = _make_pool(conn)

    with patch("asyncpg.create_pool", new=AsyncMock(return_value=pool)):
        refresh_report_views_task()

    # Three MV refreshes.
    assert conn.execute.await_count == 3
    refreshed = [c.args[0] for c in conn.execute.await_args_list]
    assert any("mv_class_summary" in q for q in refreshed)
    assert any("mv_student_progress" in q for q in refreshed)
    assert any("mv_feedback_summary" in q for q in refreshed)
    pool.close.assert_awaited_once()


# ── evaluate_report_alerts_task ───────────────────────────────────────────────


def test_evaluate_report_alerts_task_inserts_alert_for_pass_rate_breach():
    from src.auth.tasks import evaluate_report_alerts_task

    school_id = uuid.uuid4()

    conn = AsyncMock()
    conn.fetch.side_effect = [
        # First fetch: report_alert_settings rows
        [{"school_id": str(school_id), "pass_rate_threshold": 60, "inactive_days_threshold": 14}],
        # Second fetch: breach rows for that school
        [{"unit_id": "G8-MATH-001", "pass_rate": 42.5}],
    ]
    pool = _make_pool(conn)

    with patch("asyncpg.create_pool", new=AsyncMock(return_value=pool)):
        evaluate_report_alerts_task()

    # One INSERT INTO report_alerts for the breach.
    insert_calls = [c for c in conn.execute.await_args_list if "INSERT INTO report_alerts" in c.args[0]]
    assert len(insert_calls) == 1
    pool.close.assert_awaited_once()


def test_evaluate_report_alerts_task_noop_when_no_schools_configured():
    from src.auth.tasks import evaluate_report_alerts_task

    conn = AsyncMock()
    conn.fetch.return_value = []  # no settings rows
    pool = _make_pool(conn)

    with patch("asyncpg.create_pool", new=AsyncMock(return_value=pool)):
        evaluate_report_alerts_task()

    # Settings fetch happened, nothing else.
    assert conn.fetch.await_count == 1
    conn.execute.assert_not_called()
    pool.close.assert_awaited_once()


# ── send_weekly_digest_task ───────────────────────────────────────────────────


def _digest_conn_with_subs(subs: list[dict]) -> AsyncMock:
    """Return an asyncpg conn mock configured for send_weekly_digest_task."""
    conn = AsyncMock()
    # Per-sub: active_row (fetchrow), struggling_rows (fetch), fb_row (fetchrow)
    fetch_sequence = [subs]
    fetchrow_sequence = []
    for _ in subs:
        fetch_sequence.append([])  # struggling_rows empty
        fetchrow_sequence.append({"active_students": 7})
        fetchrow_sequence.append({"cnt": 3})

    conn.fetch.side_effect = fetch_sequence
    conn.fetchrow.side_effect = fetchrow_sequence
    return conn


def test_send_weekly_digest_task_sends_via_sendgrid_per_subscription():
    from src.auth.tasks import send_weekly_digest_task

    school_id = uuid.uuid4()
    subs = [
        {
            "subscription_id": str(uuid.uuid4()),
            "school_id": str(school_id),
            "email": "principal@school.example",
            "timezone": "UTC",
        }
    ]
    conn = _digest_conn_with_subs(subs)
    pool = _make_pool(conn)

    with (
        patch("asyncpg.create_pool", new=AsyncMock(return_value=pool)),
        patch("src.auth.tasks.settings.SENDGRID_API_KEY", "sg-key"),
        patch("src.auth.tasks.settings.EMAIL_FROM", "noreply@studybuddy.app"),
        patch("httpx.post") as mock_post,
    ):
        send_weekly_digest_task()

    mock_post.assert_called_once()
    payload = mock_post.call_args.kwargs["json"]
    assert payload["personalizations"][0]["to"][0]["email"] == "principal@school.example"
    assert payload["subject"] == "StudyBuddy Weekly Digest"
    # Both plain + html content.
    types = [c["type"] for c in payload["content"]]
    assert "text/plain" in types and "text/html" in types


def test_send_weekly_digest_task_noop_when_no_subscriptions():
    from src.auth.tasks import send_weekly_digest_task

    conn = AsyncMock()
    conn.fetch.return_value = []  # no subscriptions
    pool = _make_pool(conn)

    with (
        patch("asyncpg.create_pool", new=AsyncMock(return_value=pool)),
        patch("src.auth.tasks.settings.SENDGRID_API_KEY", "sg-key"),
        patch("httpx.post") as mock_post,
    ):
        send_weekly_digest_task()

    mock_post.assert_not_called()
    pool.close.assert_awaited_once()


def test_send_weekly_digest_task_skips_send_when_sendgrid_key_missing():
    """No API key → digest content prepared + logged but not actually sent."""
    from src.auth.tasks import send_weekly_digest_task

    subs = [
        {
            "subscription_id": str(uuid.uuid4()),
            "school_id": str(uuid.uuid4()),
            "email": "a@b.example",
            "timezone": "UTC",
        }
    ]
    conn = _digest_conn_with_subs(subs)
    pool = _make_pool(conn)

    with (
        patch("asyncpg.create_pool", new=AsyncMock(return_value=pool)),
        patch("src.auth.tasks.settings.SENDGRID_API_KEY", None),
        patch("httpx.post") as mock_post,
    ):
        send_weekly_digest_task()

    mock_post.assert_not_called()


def test_send_weekly_digest_task_swallows_sendgrid_errors():
    """httpx failure → logged warning, task continues without raising."""
    from src.auth.tasks import send_weekly_digest_task

    subs = [
        {
            "subscription_id": str(uuid.uuid4()),
            "school_id": str(uuid.uuid4()),
            "email": "a@b.example",
            "timezone": "UTC",
        }
    ]
    conn = _digest_conn_with_subs(subs)
    pool = _make_pool(conn)

    with (
        patch("asyncpg.create_pool", new=AsyncMock(return_value=pool)),
        patch("src.auth.tasks.settings.SENDGRID_API_KEY", "sg-key"),
        patch("src.auth.tasks.settings.EMAIL_FROM", "noreply@studybuddy.app"),
        patch("httpx.post", side_effect=RuntimeError("sendgrid 503")),
    ):
        # Must not raise.
        send_weekly_digest_task()


# ── export_report_task ────────────────────────────────────────────────────────


def test_export_report_task_writes_csv_with_expected_columns(tmp_path):
    from src.auth.tasks import export_report_task

    school_id = uuid.uuid4()
    export_id = str(uuid.uuid4())

    conn = AsyncMock()
    conn.fetch.return_value = [
        {"name": "Alice", "grade": 8, "email": "alice@s.example", "units_passed": 12, "avg_score": 88.5},
        {"name": "Bob", "grade": 8, "email": "bob@s.example", "units_passed": 10, "avg_score": 76.0},
    ]
    pool = _make_pool(conn)

    with (
        patch("asyncpg.create_pool", new=AsyncMock(return_value=pool)),
        patch("src.auth.tasks.settings.CONTENT_STORE_PATH", str(tmp_path)),
    ):
        export_report_task(
            export_id=export_id,
            school_id=str(school_id),
            report_type="class_summary",
            filters={},
        )

    export_path = tmp_path / "exports" / f"{export_id}.csv"
    assert export_path.exists()
    content = export_path.read_text()
    assert "name,grade,email,units_passed,avg_score" in content
    assert "Alice" in content and "Bob" in content
    assert "88.5" in content
