"""
backend/tests/test_demo_test_run.py

Tests for /demo/test-run/* — single submission that provisions both a demo
teacher and a demo student account and emails the combined credentials.

Strategy mirrors test_demo_endpoints.py: real DB state via API calls; Celery
mocked; verification token captured from the patched email task.
"""

from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import patch

import pytest
from httpx import AsyncClient

# ── Helpers ───────────────────────────────────────────────────────────────────


@contextmanager
def _capture_test_run_emails():
    """
    Patch the verification + credentials Celery tasks. Returns a dict with:
      - get_token(): the token from the verification email
      - get_credentials(): the credentials kwargs from the credentials email
    """
    verif_captured: list[str] = []
    creds_captured: list[dict] = []

    def _on_verif(_email: str, token: str) -> None:
        verif_captured.append(token)

    def _on_creds(
        to_email: str,
        name: str,
        teacher_email: str,
        teacher_password: str,
        student_email: str,
        student_password: str,
    ) -> None:
        creds_captured.append(
            {
                "to_email": to_email,
                "name": name,
                "teacher_email": teacher_email,
                "teacher_password": teacher_password,
                "student_email": student_email,
                "student_password": student_password,
            }
        )

    with (
        patch(
            "src.demo.test_run_router.send_test_run_verification_email_task.delay",
            side_effect=_on_verif,
        ),
        patch(
            "src.demo.test_run_router.send_test_run_credentials_email_task.delay",
            side_effect=_on_creds,
        ),
    ):
        yield {
            "get_token": lambda: verif_captured[-1] if verif_captured else None,
            "get_credentials": lambda: creds_captured[-1] if creds_captured else None,
        }


# ── POST /demo/test-run/request ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_test_run_request_success(client: AsyncClient):
    """Valid name + email returns 200, queues a verification email."""
    with _capture_test_run_emails() as captured:
        r = await client.post(
            "/api/v1/demo/test-run/request",
            json={"name": "Test Visitor", "email": "tr-req-ok@example.com"},
        )
    assert r.status_code == 200, r.text
    assert "message" in r.json()
    assert captured["get_token"]() is not None


@pytest.mark.asyncio
async def test_test_run_request_blank_name_rejected(client: AsyncClient):
    """Name is required — empty/whitespace returns 422."""
    r = await client.post(
        "/api/v1/demo/test-run/request",
        json={"name": "   ", "email": "tr-blank-name@example.com"},
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_test_run_request_invalid_email_rejected(client: AsyncClient):
    """Non-email rejected at schema layer."""
    r = await client.post(
        "/api/v1/demo/test-run/request",
        json={"name": "Test Visitor", "email": "not-an-email"},
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_test_run_request_duplicate_pending(client: AsyncClient):
    """Second request before verification returns 409."""
    email = "tr-dup-pending@example.com"
    with _capture_test_run_emails():
        r1 = await client.post(
            "/api/v1/demo/test-run/request", json={"name": "Visitor", "email": email}
        )
    assert r1.status_code == 200

    with _capture_test_run_emails():
        r2 = await client.post(
            "/api/v1/demo/test-run/request", json={"name": "Visitor", "email": email}
        )
    assert r2.status_code == 409
    assert r2.json()["error"] == "verification_pending"


# ── GET /demo/test-run/verify/{token} ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_test_run_verify_provisions_both_accounts(client: AsyncClient):
    """
    Full flow: request → verify → credentials email contains BOTH plus-addressed
    accounts; the inbox email is the visitor's original (un-tagged) address.
    """
    email = "tr-full-flow@example.com"
    name = "Pat Tester"

    with _capture_test_run_emails() as captured:
        r = await client.post(
            "/api/v1/demo/test-run/request",
            json={"name": name, "email": email},
        )
        assert r.status_code == 200, r.text
        token = captured["get_token"]()
        assert token is not None

        rv = await client.get(f"/api/v1/demo/test-run/verify/{token}")
        assert rv.status_code == 200, rv.text

        creds = captured["get_credentials"]()

    assert creds is not None
    # Credentials email goes to the visitor's original inbox, not a +tagged variant.
    assert creds["to_email"] == email
    assert creds["name"] == name
    # Both per-role emails are plus-addressed off the original local-part.
    assert creds["teacher_email"] == "tr-full-flow+teacher@example.com"
    assert creds["student_email"] == "tr-full-flow+student@example.com"
    # Each role has its own freshly-generated password.
    assert creds["teacher_password"]
    assert creds["student_password"]
    assert creds["teacher_password"] != creds["student_password"]


@pytest.mark.asyncio
async def test_test_run_verify_login_works_for_both_roles(client: AsyncClient):
    """
    After verification, /auth/universal-login authenticates BOTH provisioned
    accounts — the teacher with the teacher creds, the student with the
    student creds. Proves the end-to-end test-run flow is fully usable.
    """
    email = "tr-login-both@example.com"

    with _capture_test_run_emails() as captured:
        await client.post(
            "/api/v1/demo/test-run/request",
            json={"name": "Both-Persona Tester", "email": email},
        )
        token = captured["get_token"]()
        await client.get(f"/api/v1/demo/test-run/verify/{token}")
        creds = captured["get_credentials"]()

    # Teacher login
    r_teacher = await client.post(
        "/api/v1/auth/universal-login",
        json={"email": creds["teacher_email"], "password": creds["teacher_password"]},
    )
    assert r_teacher.status_code == 200, r_teacher.text
    assert r_teacher.json()["auth_track"] == "demo_teacher"

    # Student login
    r_student = await client.post(
        "/api/v1/auth/universal-login",
        json={"email": creds["student_email"], "password": creds["student_password"]},
    )
    assert r_student.status_code == 200, r_student.text
    assert r_student.json()["auth_track"] == "demo_student"


@pytest.mark.asyncio
async def test_test_run_provisions_into_milford_grade11_science(client: AsyncClient):
    """
    When the seeded MilfordWaterford sandbox exists, verify:
      - student row: school_id=Milford, grade=11, stream='science'
      - teacher row: school_id=Milford, role='teacher'
      - a new per-visitor classroom is created with the demo teacher as lead,
        Grade 11 Science curriculum attached, and the demo student enrolled.

    Skipped on test DBs without the seed.
    """
    email = "sandbox-wiring@example.com"

    pool = client._transport.app.state.pool  # type: ignore[attr-defined]
    async with pool.acquire() as conn:
        await conn.execute("SET app.current_school_id = 'bypass'")
        school_row = await conn.fetchrow(
            "SELECT school_id FROM schools WHERE contact_email = $1",
            "admin@milfordwaterford.edu",
        )
        if school_row is None:
            pytest.skip("MilfordWaterford sandbox not seeded in this DB")
        milford_id = school_row["school_id"]

    with _capture_test_run_emails() as captured:
        r = await client.post(
            "/api/v1/demo/test-run/request",
            json={"name": "Sandbox Wirer", "email": email},
        )
        assert r.status_code == 200, r.text
        token = captured["get_token"]()
        rv = await client.get(f"/api/v1/demo/test-run/verify/{token}")
        assert rv.status_code == 200, rv.text

    async with pool.acquire() as conn:
        await conn.execute("SET app.current_school_id = 'bypass'")
        student = await conn.fetchrow(
            "SELECT student_id, school_id, grade, stream, name FROM students WHERE email = $1",
            "sandbox-wiring+student@example.com",
        )
        assert student is not None
        assert student["school_id"] == milford_id
        assert student["grade"] == 11
        assert student["stream"] == "science"
        assert "Sandbox Wirer" in student["name"]

        teacher = await conn.fetchrow(
            "SELECT teacher_id, school_id, role, name FROM teachers WHERE email = $1",
            "sandbox-wiring+teacher@example.com",
        )
        assert teacher is not None
        assert teacher["school_id"] == milford_id
        assert teacher["role"] == "teacher"
        assert "Sandbox Wirer" in teacher["name"]

        # Per-visitor classroom owned by the demo teacher.
        classroom = await conn.fetchrow(
            """
            SELECT classroom_id, name, grade FROM classrooms
            WHERE teacher_id = $1 AND school_id = $2
            """,
            teacher["teacher_id"],
            milford_id,
        )
        assert classroom is not None, "demo teacher must lead a per-visitor classroom"
        assert classroom["grade"] == 11
        assert "Sandbox Wirer" in classroom["name"]

        # Grade 11 Science package attached.
        pkg = await conn.fetchval(
            """
            SELECT curriculum_id FROM classroom_packages WHERE classroom_id = $1
            """,
            classroom["classroom_id"],
        )
        assert pkg == "default-2026-g11-science"

        # Demo student enrolled in the demo teacher's classroom (not a seeded one).
        enrolled = await conn.fetchval(
            """
            SELECT COUNT(*) FROM classroom_students
            WHERE classroom_id = $1 AND student_id = $2
            """,
            classroom["classroom_id"],
            student["student_id"],
        )
        assert enrolled == 1


@pytest.mark.asyncio
async def test_admin_delete_drops_per_visitor_classroom(client: AsyncClient):
    """
    The admin DELETE endpoint must clean up the per-visitor classroom before
    deleting the demo teacher; classrooms.teacher_id is ON DELETE SET NULL,
    so without explicit cleanup the classroom would linger as a leaderless
    orphan in the school.
    """
    from tests.helpers.token_factory import make_admin_token

    email = "purge-classroom@example.com"

    pool = client._transport.app.state.pool  # type: ignore[attr-defined]
    async with pool.acquire() as conn:
        await conn.execute("SET app.current_school_id = 'bypass'")
        school_row = await conn.fetchrow(
            "SELECT school_id FROM schools WHERE contact_email = $1",
            "admin@milfordwaterford.edu",
        )
        if school_row is None:
            pytest.skip("MilfordWaterford sandbox not seeded in this DB")

    with _capture_test_run_emails() as captured:
        await client.post(
            "/api/v1/demo/test-run/request",
            json={"name": "Classroom Cleaner", "email": email},
        )
        token = captured["get_token"]()
        await client.get(f"/api/v1/demo/test-run/verify/{token}")

    # Confirm the per-visitor classroom exists before purge.
    async with pool.acquire() as conn:
        await conn.execute("SET app.current_school_id = 'bypass'")
        teacher = await conn.fetchrow(
            "SELECT teacher_id FROM teachers WHERE email = $1",
            "purge-classroom+teacher@example.com",
        )
        before_count = await conn.fetchval(
            "SELECT COUNT(*) FROM classrooms WHERE teacher_id = $1",
            teacher["teacher_id"],
        )
        assert before_count == 1

    admin_token = make_admin_token(role="super_admin")
    r = await client.request(
        "DELETE",
        f"/api/v1/admin/demo/test-runs/by-email?email={email}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["classrooms_deleted"] == 1

    async with pool.acquire() as conn:
        await conn.execute("SET app.current_school_id = 'bypass'")
        after_count = await conn.fetchval(
            "SELECT COUNT(*) FROM classrooms WHERE teacher_id = $1",
            teacher["teacher_id"],
        )
        assert after_count == 0


@pytest.mark.asyncio
async def test_test_run_verify_invalid_token_returns_404(client: AsyncClient):
    r = await client.get("/api/v1/demo/test-run/verify/this-token-does-not-exist")
    assert r.status_code == 404
    assert r.json()["error"] == "token_not_found"


@pytest.mark.asyncio
async def test_test_run_verify_already_used_returns_409(client: AsyncClient):
    """Second click on the same verification link returns 409."""
    email = "tr-double-verify@example.com"

    with _capture_test_run_emails() as captured:
        await client.post(
            "/api/v1/demo/test-run/request",
            json={"name": "Double Click", "email": email},
        )
        token = captured["get_token"]()
        first = await client.get(f"/api/v1/demo/test-run/verify/{token}")
        assert first.status_code == 200

        second = await client.get(f"/api/v1/demo/test-run/verify/{token}")
        assert second.status_code == 409
        assert second.json()["error"] in {"token_already_used", "already_verified"}
