"""
tests/test_reports.py

Tests for Phase 11 teacher reporting dashboard endpoints.

Coverage:
  GET  /reports/school/{id}/overview           — class summary, period filter, wrong-school 403
  GET  /reports/school/{id}/unit/{unit_id}     — unit deep-dive
  GET  /reports/school/{id}/student/{sid}      — student report card, not-enrolled 404
  GET  /reports/school/{id}/curriculum-health  — health tier logic
  GET  /reports/school/{id}/feedback           — feedback grouped by unit
  GET  /reports/school/{id}/trends             — week-over-week trend data
  POST /reports/school/{id}/export             — queues Celery task, returns export_id
  GET  /reports/school/{id}/alerts             — unacknowledged alerts
  PUT  /reports/school/{id}/alerts/settings    — upsert threshold settings
  POST /reports/school/{id}/digest/subscribe   — upsert digest subscription
  POST /reports/school/{id}/refresh            — trigger MV refresh (school_admin)
  Auth: all endpoints return 403 without JWT
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from httpx import AsyncClient

from tests.helpers.token_factory import make_teacher_token

# ── Deterministic test IDs (Rule 9 — no uuid4 in fixtures) ───────────────────
# Each constant is a fixed UUID so test runs are fully reproducible.
# "wrong" school / teacher IDs must never match any registered entity.
_SID_OV_DATA   = "a1000000-0000-0000-0000-000000000001"  # overview_with_data
_SID_STUDENT   = "a1000000-0000-0000-0000-000000000002"  # student report card
_SID_TRENDS    = "a1000000-0000-0000-0000-000000000003"  # trends
_SID_FEEDBACK  = "a1000000-0000-0000-0000-000000000004"  # feedback
_SID_HEALTH    = "a1000000-0000-0000-0000-000000000005"  # curriculum health
_SID_EXPORT    = "a1000000-0000-0000-0000-000000000006"  # export
_SID_ALERTS    = "a1000000-0000-0000-0000-000000000007"  # alerts
_WRONG_SCHOOL  = "ffff0000-0000-0000-0000-000000000001"  # 403 wrong-school checks
_NONEXISTENT_SID = "eeee0000-0000-0000-0000-000000000001"  # not-enrolled 404


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _register_school(client: AsyncClient, suffix: str = "") -> dict:
    r = await client.post("/api/v1/schools/register", json={
        "school_name": f"Report School{suffix}",
        "contact_email": f"report{suffix}@school.example.com",
        "country": "ZA",
    })
    assert r.status_code == 201, r.text
    return r.json()


async def _insert_student(client: AsyncClient, student_id: str, email: str) -> None:
    pool = client._transport.app.state.pool
    # Use full UUID (no dashes) as external_auth_id to avoid unique-constraint
    # collisions — all test UUIDs share the same 8-char prefix "a1000000".
    ext_id = f"auth0|rpt-{student_id.replace('-', '')}"
    await pool.execute(
        """
        INSERT INTO students (student_id, external_auth_id, name, email, grade, locale, account_status)
        VALUES ($1, $2, $3, $4, 8, 'en', 'active')
        ON CONFLICT (student_id) DO NOTHING
        """,
        uuid.UUID(student_id),
        ext_id,
        f"Report Student {student_id[:6]}",
        email,
    )


async def _enrol_student(client: AsyncClient, school_id: str, student_id: str, email: str) -> None:
    pool = client._transport.app.state.pool
    # school_enrolments has FORCE RLS; acquire explicitly to set bypass.
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await conn.execute(
            """
            INSERT INTO school_enrolments (school_id, student_email, student_id, status)
            VALUES ($1, $2, $3, 'active')
            ON CONFLICT (school_id, student_email) DO UPDATE SET student_id = EXCLUDED.student_id, status = 'active'
            """,
            uuid.UUID(school_id), email, uuid.UUID(student_id),
        )


async def _insert_session(
    client: AsyncClient,
    student_id: str,
    *,
    unit_id: str = "G8-MATH-001",
    subject: str = "Mathematics",
    curriculum_id: str = "default-2026-g8",
    attempt_number: int = 1,
    score: int = 75,
    completed: bool = True,
    passed: bool = True,
    days_ago: int = 1,
) -> None:
    pool = client._transport.app.state.pool
    started_at = datetime.now(timezone.utc) - timedelta(days=days_ago)
    await pool.execute(
        """
        INSERT INTO progress_sessions
            (student_id, unit_id, curriculum_id, subject, grade,
             attempt_number, score, completed, passed, started_at)
        VALUES ($1, $2, $3, $4, 8, $5, $6, $7, $8, $9)
        """,
        uuid.UUID(student_id), unit_id, curriculum_id, subject,
        attempt_number, score, completed, passed, started_at,
    )


async def _insert_lesson_view(
    client: AsyncClient,
    student_id: str,
    *,
    unit_id: str = "G8-MATH-001",
    duration_s: int = 300,
    audio_played: bool = False,
    days_ago: int = 1,
) -> None:
    pool = client._transport.app.state.pool
    started_at = datetime.now(timezone.utc) - timedelta(days=days_ago)
    await pool.execute(
        """
        INSERT INTO lesson_views
            (student_id, unit_id, curriculum_id, ended_at, duration_s, audio_played, started_at)
        VALUES ($1, $2, 'default-2026-g8', NOW(), $3, $4, $5)
        """,
        uuid.UUID(student_id), unit_id, duration_s, audio_played, started_at,
    )


def _make_teacher(school_id: str, role: str = "teacher") -> str:
    return make_teacher_token(school_id=school_id, role=role)


# ── Overview report ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_overview_empty_school(client, db_conn):
    """School with no enrolled students returns zero-value overview."""
    school = await _register_school(client, "_ov_empty")
    school_id = school["school_id"]
    token = school["access_token"]

    r = await client.get(
        f"/api/v1/reports/school/{school_id}/overview",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["enrolled_students"] == 0
    assert data["lessons_viewed"] == 0
    assert data["quiz_attempts"] == 0


@pytest.mark.asyncio
async def test_overview_with_data(client, db_conn):
    """Overview aggregates lesson views and quiz attempts for enrolled students."""
    school = await _register_school(client, "_ov_data")
    school_id = school["school_id"]
    token = school["access_token"]

    sid = _SID_OV_DATA
    email = "ov-a10000@test.invalid"
    await _insert_student(client, sid, email)
    await _enrol_student(client, school_id, sid, email)
    await _insert_lesson_view(client, sid, audio_played=True)
    await _insert_session(client, sid, score=80, passed=True)

    r = await client.get(
        f"/api/v1/reports/school/{school_id}/overview",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["enrolled_students"] == 1
    assert data["lessons_viewed"] >= 1
    assert data["quiz_attempts"] >= 1
    assert data["audio_play_rate_pct"] == 100.0


@pytest.mark.asyncio
async def test_overview_wrong_school_403(client, db_conn):
    """Teacher cannot access another school's overview."""
    school = await _register_school(client, "_ov_ws")
    school_id = school["school_id"]
    wrong_token = _make_teacher(_WRONG_SCHOOL)

    r = await client.get(
        f"/api/v1/reports/school/{school_id}/overview",
        headers={"Authorization": f"Bearer {wrong_token}"},
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_overview_requires_auth(client, db_conn):
    school = await _register_school(client, "_ov_auth")
    r = await client.get(f"/api/v1/reports/school/{school['school_id']}/overview")
    assert r.status_code == 401


# ── Unit report ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_unit_report_returns_200(client, db_conn):
    """Unit report returns per-unit metrics for enrolled students."""
    school = await _register_school(client, "_ur")
    school_id = school["school_id"]
    token = school["access_token"]

    sid = _SID_STUDENT
    email = "ur-a10000@test.invalid"
    await _insert_student(client, sid, email)
    await _enrol_student(client, school_id, sid, email)
    await _insert_lesson_view(client, sid, unit_id="G8-SCI-001", duration_s=600)
    await _insert_session(client, sid, unit_id="G8-SCI-001", subject="Science", score=70, passed=True)

    r = await client.get(
        f"/api/v1/reports/school/{school_id}/unit/G8-SCI-001",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["unit_id"] == "G8-SCI-001"
    assert data["students_viewed_lesson"] >= 1
    assert data["students_attempted_quiz"] >= 1
    assert "attempt_distribution" in data
    assert "struggle_flag" in data


@pytest.mark.asyncio
async def test_unit_report_wrong_school_403(client, db_conn):
    school = await _register_school(client, "_ur_ws")
    school_id = school["school_id"]
    wrong_token = _make_teacher(_WRONG_SCHOOL)

    r = await client.get(
        f"/api/v1/reports/school/{school_id}/unit/G8-MATH-001",
        headers={"Authorization": f"Bearer {wrong_token}"},
    )
    assert r.status_code == 403


# ── Student report ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_student_report_returns_200(client, db_conn):
    """Student report card returns per-unit breakdown."""
    school = await _register_school(client, "_sr")
    school_id = school["school_id"]
    token = school["access_token"]

    sid = _SID_STUDENT
    email = "sr-a10000@test.invalid"
    await _insert_student(client, sid, email)
    await _enrol_student(client, school_id, sid, email)
    await _insert_lesson_view(client, sid)
    await _insert_session(client, sid, score=85, passed=True)

    r = await client.get(
        f"/api/v1/reports/school/{school_id}/student/{sid}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["student_id"] == sid
    assert data["units_completed"] >= 1
    assert len(data["per_unit"]) >= 1


@pytest.mark.asyncio
async def test_student_report_not_enrolled_returns_404(client, db_conn):
    """Student not enrolled in school returns 404."""
    school = await _register_school(client, "_sr_404")
    school_id = school["school_id"]
    token = school["access_token"]

    random_sid = _NONEXISTENT_SID

    r = await client.get(
        f"/api/v1/reports/school/{school_id}/student/{random_sid}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 404


# ── Curriculum health ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_curriculum_health_returns_200(client, db_conn):
    """Curriculum health returns list of units with health tiers."""
    school = await _register_school(client, "_ch")
    school_id = school["school_id"]
    token = school["access_token"]

    sid = _SID_HEALTH
    email = "ch-a10000@test.invalid"
    await _insert_student(client, sid, email)
    await _enrol_student(client, school_id, sid, email)
    await _insert_lesson_view(client, sid, unit_id="G8-MATH-002")
    await _insert_session(client, sid, unit_id="G8-MATH-002", subject="Mathematics", score=90, passed=True)

    r = await client.get(
        f"/api/v1/reports/school/{school_id}/curriculum-health",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert "units" in data
    assert "healthy_count" in data
    assert "struggling_count" in data
    if data["units"]:
        unit = data["units"][0]
        assert unit["health_tier"] in ("healthy", "watch", "struggling", "no_activity")
        assert "recommended_action" in unit


@pytest.mark.asyncio
async def test_curriculum_health_struggling_tier(client, db_conn):
    """Unit with 0% first-attempt pass rate is classified as struggling."""
    school = await _register_school(client, "_ch_str")
    school_id = school["school_id"]
    token = school["access_token"]

    # Three students all fail first attempt
    _STRUGGLE_SIDS = [
        "b1000000-0000-0000-0000-000000000001",
        "b1000000-0000-0000-0000-000000000002",
        "b1000000-0000-0000-0000-000000000003",
    ]
    for i, sid in enumerate(_STRUGGLE_SIDS):
        email = f"chstr-{i + 1}@test.invalid"
        await _insert_student(client, sid, email)
        await _enrol_student(client, school_id, sid, email)
        await _insert_lesson_view(client, sid, unit_id="G8-STRUGGLE")
        await _insert_session(
            client, sid, unit_id="G8-STRUGGLE", subject="Mathematics",
            score=30, passed=False, attempt_number=1,
        )

    r = await client.get(
        f"/api/v1/reports/school/{school_id}/curriculum-health",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    struggling = [u for u in data["units"] if u["unit_id"] == "G8-STRUGGLE"]
    assert struggling, "G8-STRUGGLE unit not found in response"
    assert struggling[0]["health_tier"] == "struggling"
    assert struggling[0]["recommended_action"] == "report_to_admin"


# ── Feedback report ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_feedback_report_returns_200(client, db_conn):
    """Feedback report returns grouped feedback from enrolled students."""
    school = await _register_school(client, "_fb")
    school_id = school["school_id"]
    token = school["access_token"]

    sid = _SID_FEEDBACK
    email = "fb-a10000@test.invalid"
    await _insert_student(client, sid, email)
    await _enrol_student(client, school_id, sid, email)

    pool = client._transport.app.state.pool
    await pool.execute(
        "INSERT INTO feedback (student_id, category, message, unit_id) VALUES ($1, 'content', 'Great unit!', 'G8-MATH-001')",
        uuid.UUID(sid),
    )

    r = await client.get(
        f"/api/v1/reports/school/{school_id}/feedback",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert "total_feedback_count" in data
    assert "by_unit" in data
    assert data["total_feedback_count"] >= 1


# ── Trends report ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_trends_report_returns_4_weeks(client, db_conn):
    """Trends report returns one entry per week for 4w period."""
    school = await _register_school(client, "_tr")
    school_id = school["school_id"]
    token = school["access_token"]

    r = await client.get(
        f"/api/v1/reports/school/{school_id}/trends?period=4w",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert len(data["weeks"]) == 4
    for week in data["weeks"]:
        assert "week_start" in week
        assert "active_students" in week
        assert "lessons_viewed" in week


# ── Export ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_export_queues_celery_task(client, db_conn):
    """POST /export dispatches Celery task and returns export_id."""
    school = await _register_school(client, "_exp")
    school_id = school["school_id"]
    token = school["access_token"]

    with patch("src.auth.tasks.celery_app.send_task", return_value=None) as mock_send:
        r = await client.post(
            f"/api/v1/reports/school/{school_id}/export",
            json={"report_type": "overview", "filters": {}},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200, r.text
        mock_send.assert_called_once()
        task_name = mock_send.call_args[0][0]
        assert task_name == "src.auth.tasks.export_report_task"

    data = r.json()
    assert "export_id" in data
    uuid.UUID(data["export_id"])
    assert "/reports/download/" in data["download_url"]
    assert data["status"] == "queued"


@pytest.mark.asyncio
async def test_export_wrong_school_403(client, db_conn):
    school = await _register_school(client, "_exp_ws")
    school_id = school["school_id"]
    wrong_token = _make_teacher(_WRONG_SCHOOL)

    r = await client.post(
        f"/api/v1/reports/school/{school_id}/export",
        json={"report_type": "overview"},
        headers={"Authorization": f"Bearer {wrong_token}"},
    )
    assert r.status_code == 403


# ── Alerts ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_alerts_returns_empty_list(client, db_conn):
    """School with no triggered alerts returns empty list."""
    school = await _register_school(client, "_al")
    school_id = school["school_id"]
    token = school["access_token"]

    r = await client.get(
        f"/api/v1/reports/school/{school_id}/alerts",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["alerts"] == []


@pytest.mark.asyncio
async def test_save_alert_settings_returns_200(client, db_conn):
    """PUT /alerts/settings upserts threshold configuration."""
    school = await _register_school(client, "_als")
    school_id = school["school_id"]
    token = school["access_token"]

    r = await client.put(
        f"/api/v1/reports/school/{school_id}/alerts/settings",
        json={"pass_rate_threshold": 60.0, "inactive_days_threshold": 7, "new_feedback_immediate": False},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["pass_rate_threshold"] == 60.0
    assert data["inactive_days_threshold"] == 7
    assert data["new_feedback_immediate"] is False

    # Idempotent: second call updates
    r2 = await client.put(
        f"/api/v1/reports/school/{school_id}/alerts/settings",
        json={"pass_rate_threshold": 45.0},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r2.status_code == 200
    assert r2.json()["pass_rate_threshold"] == 45.0


# ── Digest subscription ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_digest_subscribe_returns_200(client, db_conn):
    """POST /digest/subscribe upserts digest subscription for teacher."""
    school = await _register_school(client, "_dig")
    school_id = school["school_id"]
    token = school["access_token"]

    r = await client.post(
        f"/api/v1/reports/school/{school_id}/digest/subscribe",
        json={"email": "teacher@school.example.com", "timezone": "Africa/Johannesburg", "enabled": True},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert "subscription_id" in data
    assert data["timezone"] == "Africa/Johannesburg"
    assert data["enabled"] is True


# ── Refresh ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_refresh_materialized_views(client, db_conn):
    """POST /refresh triggers MV refresh and returns view names."""
    school = await _register_school(client, "_ref")
    school_id = school["school_id"]
    # school_admin token
    token = make_teacher_token(school_id=school_id, role="school_admin")

    # Override the token with the one from school registration (which is school_admin)
    token = school["access_token"]

    r = await client.post(
        f"/api/v1/reports/school/{school_id}/refresh",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert "views_refreshed" in data
    assert "mv_class_summary" in data["views_refreshed"]
    assert "refreshed_at" in data
