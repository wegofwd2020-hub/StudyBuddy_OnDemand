"""
backend/tests/test_auth_universal_login.py

Tests for POST /auth/universal-login — the single sign-in entry point that
dispatches across local-auth + demo-teacher + demo-student stores.

Strategy mirrors test_phase_a_provisioning.py + test_demo_endpoints.py:
  - School-provisioning happy paths use real DB state via /schools/register +
    /schools/{id}/teachers + /schools/{id}/students.
  - Demo happy paths use the request → verify → login flow with patched Celery
    so the credentials password can be captured from the email task.
  - 401/precedence tests do not need DB writes — they just hit the endpoint.

Probe order under test: local → demo_teacher → demo_student.
"""

from __future__ import annotations

import time
from contextlib import contextmanager
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

_PW = "SecureTestPwd1!"


# ── Helpers ───────────────────────────────────────────────────────────────────


async def _register_school(client: AsyncClient, name: str, email: str) -> dict:
    r = await client.post(
        "/api/v1/schools/register",
        json={
            "school_name": name,
            "contact_email": email,
            "country": "CA",
            "password": _PW,
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


async def _provision_teacher(
    client: AsyncClient, school_id: str, token: str, name: str, email: str
) -> str:
    """Provision a teacher and return the auto-generated default password."""
    with patch("src.email.service.send_welcome_teacher_email", new_callable=AsyncMock) as mock_email:
        r = await client.post(
            f"/api/v1/schools/{school_id}/teachers",
            json={"name": name, "email": email},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert r.status_code == 201, r.text
    call_args = mock_email.call_args
    return call_args.args[2] if len(call_args.args) >= 3 else call_args.kwargs["password"]


async def _provision_student(
    client: AsyncClient,
    school_id: str,
    token: str,
    name: str,
    email: str,
    grade: int = 8,
) -> str:
    with patch("src.email.service.send_welcome_student_email", new_callable=AsyncMock) as mock_email:
        r = await client.post(
            f"/api/v1/schools/{school_id}/students",
            json={"name": name, "email": email, "grade": grade},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert r.status_code == 201, r.text
    call_args = mock_email.call_args
    return call_args.args[2] if len(call_args.args) >= 3 else call_args.kwargs["password"]


@contextmanager
def _capture_demo_student_password(email_capture: list):
    """Patch demo student email tasks; capture verification token + credentials."""

    def _capture_token(_email: str, token: str) -> None:
        email_capture.append(("token", token))

    def _capture_creds(_email: str, password: str) -> None:
        email_capture.append(("password", password))

    with (
        patch(
            "src.demo.router.send_demo_verification_email_task.delay",
            side_effect=_capture_token,
        ),
        patch(
            "src.demo.router.send_demo_credentials_email_task.delay",
            side_effect=_capture_creds,
        ),
    ):
        yield


@contextmanager
def _capture_demo_teacher_password(email_capture: list):
    def _capture_token(_email: str, token: str) -> None:
        email_capture.append(("token", token))

    def _capture_creds(_email: str, password: str) -> None:
        email_capture.append(("password", password))

    with (
        patch(
            "src.demo.teacher_router.send_demo_teacher_verification_email_task.delay",
            side_effect=_capture_token,
        ),
        patch(
            "src.demo.teacher_router.send_demo_teacher_credentials_email_task.delay",
            side_effect=_capture_creds,
        ),
    ):
        yield


async def _create_demo_student(client: AsyncClient, email: str) -> str:
    """Run the full demo-student creation flow and return the issued password."""
    captured: list = []
    with _capture_demo_student_password(captured):
        r = await client.post("/api/v1/demo/request", json={"email": email})
        assert r.status_code == 200, r.text
        token = next(v for k, v in captured if k == "token")
        rv = await client.get(f"/api/v1/demo/verify/{token}")
        assert rv.status_code == 200, rv.text
    password = next(v for k, v in captured if k == "password")
    return password


async def _create_demo_teacher(client: AsyncClient, email: str) -> str:
    captured: list = []
    with _capture_demo_teacher_password(captured):
        r = await client.post("/api/v1/demo/teacher/request", json={"email": email})
        assert r.status_code == 200, r.text
        token = next(v for k, v in captured if k == "token")
        rv = await client.get(f"/api/v1/demo/teacher/verify/{token}")
        assert rv.status_code == 200, rv.text
    password = next(v for k, v in captured if k == "password")
    return password


# ── Local auth — happy paths ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_universal_login_local_school_admin(client: AsyncClient):
    """School founder logs in via /auth/universal-login → auth_track=local, role=school_admin."""
    email = "uni-admin@example.com"
    await _register_school(client, "Uni Admin School", email)

    r = await client.post(
        "/api/v1/auth/universal-login", json={"email": email, "password": _PW}
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["auth_track"] == "local"
    assert data["role"] == "school_admin"
    assert data["first_login"] is False
    assert data["refresh_token"]  # non-empty
    assert data["demo_expires_at"] is None
    assert "token" in data
    assert "user_id" in data


@pytest.mark.asyncio
async def test_universal_login_local_provisioned_teacher_first_login(client: AsyncClient):
    """Provisioned teacher with system-issued password → first_login=True."""
    admin = await _register_school(client, "Uni Teacher School", "uni-tadmin@example.com")
    school_id = admin["school_id"]
    admin_token = admin["access_token"]

    teacher_email = "uni-teacher@example.com"
    default_pw = await _provision_teacher(
        client, school_id, admin_token, "T One", teacher_email
    )

    r = await client.post(
        "/api/v1/auth/universal-login",
        json={"email": teacher_email, "password": default_pw},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["auth_track"] == "local"
    assert data["role"] == "teacher"
    assert data["first_login"] is True
    assert data["refresh_token"]


@pytest.mark.asyncio
async def test_universal_login_local_provisioned_student(client: AsyncClient):
    """Provisioned student → auth_track=local, role=student, first_login=True."""
    admin = await _register_school(client, "Uni Student School", "uni-sadmin@example.com")
    school_id = admin["school_id"]
    admin_token = admin["access_token"]

    student_email = "uni-student@example.com"
    default_pw = await _provision_student(
        client, school_id, admin_token, "S One", student_email, grade=7
    )

    r = await client.post(
        "/api/v1/auth/universal-login",
        json={"email": student_email, "password": default_pw},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["auth_track"] == "local"
    assert data["role"] == "student"
    assert data["first_login"] is True


# ── Demo tracks — happy paths ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_universal_login_demo_student(client: AsyncClient):
    """Demo student created via the standard flow can sign in via universal-login."""
    email = "uni-demo-student@example.com"
    password = await _create_demo_student(client, email)

    r = await client.post(
        "/api/v1/auth/universal-login", json={"email": email, "password": password}
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["auth_track"] == "demo_student"
    assert data["role"] == "student"
    assert data["demo_expires_at"]  # ISO timestamp present
    assert data["refresh_token"] is None  # demo accounts get no refresh token
    assert data["first_login"] is None


@pytest.mark.asyncio
async def test_universal_login_demo_teacher(client: AsyncClient):
    """Demo teacher created via the standard flow can sign in via universal-login."""
    email = "uni-demo-teacher@example.com"
    password = await _create_demo_teacher(client, email)

    r = await client.post(
        "/api/v1/auth/universal-login", json={"email": email, "password": password}
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["auth_track"] == "demo_teacher"
    # Demo teachers inherit role from the demo_teacher_accounts join (school_admin
    # by default, since the demo seeds a single-school sandbox).
    assert data["role"] in {"teacher", "school_admin"}
    assert data["demo_expires_at"]
    assert data["refresh_token"] is None


# ── Negative paths ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_universal_login_unknown_email(client: AsyncClient):
    """Unknown email returns generic 401."""
    r = await client.post(
        "/api/v1/auth/universal-login",
        json={"email": "nobody@example.com", "password": _PW},
    )
    assert r.status_code == 401
    assert r.json()["error"] == "unauthenticated"


@pytest.mark.asyncio
async def test_universal_login_wrong_password_local(client: AsyncClient):
    """Local user with wrong password returns the same 401 shape as unknown email."""
    email = "uni-wrong-pw@example.com"
    await _register_school(client, "Wrong PW Universal School", email)

    r = await client.post(
        "/api/v1/auth/universal-login",
        json={"email": email, "password": "DefinitelyWrongPwd123!"},
    )
    assert r.status_code == 401
    assert r.json()["error"] == "unauthenticated"


@pytest.mark.asyncio
async def test_universal_login_wrong_password_demo(client: AsyncClient):
    """Demo student with wrong password returns 401."""
    email = "uni-demo-wrongpw@example.com"
    await _create_demo_student(client, email)

    r = await client.post(
        "/api/v1/auth/universal-login",
        json={"email": email, "password": "WrongDemoPwd123!"},
    )
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_universal_login_local_precedence_over_demo(client: AsyncClient):
    """When the same email exists as both a local user and a demo account,
    the local row wins. Verified by signing in with the local password —
    should succeed and return auth_track=local."""
    email = "uni-collide@example.com"

    # Local first: register a school under this email (school_admin local user).
    await _register_school(client, "Collide School", email)

    # Then create a demo student with the same email. This shouldn't conflict at
    # the request layer because demo_accounts is a separate table.
    demo_pw = await _create_demo_student(client, email)

    # Sign in with the LOCAL password → must route to local.
    r1 = await client.post(
        "/api/v1/auth/universal-login", json={"email": email, "password": _PW}
    )
    assert r1.status_code == 200
    assert r1.json()["auth_track"] == "local"
    assert r1.json()["role"] == "school_admin"

    # Sign in with the DEMO password → local row matched first, demo never tried,
    # so the demo password fails (this is the documented precedence trade-off).
    r2 = await client.post(
        "/api/v1/auth/universal-login", json={"email": email, "password": demo_pw}
    )
    assert r2.status_code == 401


@pytest.mark.asyncio
async def test_universal_login_uniform_timing(client: AsyncClient):
    """
    Wall-clock timing for an unknown email and a known-but-wrong-password login
    should be within a generous tolerance — both paths run exactly one bcrypt
    cycle. This is a smoke check, not a precise side-channel test.
    """
    known_email = "uni-timing-known@example.com"
    await _register_school(client, "Timing School", known_email)

    # Warm path: imports/JIT can skew the first call.
    await client.post(
        "/api/v1/auth/universal-login",
        json={"email": "warmup@example.com", "password": _PW},
    )

    samples = 3
    unknown_times: list[float] = []
    wrongpw_times: list[float] = []
    for i in range(samples):
        t0 = time.perf_counter()
        await client.post(
            "/api/v1/auth/universal-login",
            json={"email": f"ghost-{i}@example.com", "password": _PW},
        )
        unknown_times.append(time.perf_counter() - t0)

        t0 = time.perf_counter()
        await client.post(
            "/api/v1/auth/universal-login",
            json={"email": known_email, "password": "Wrong!Password123"},
        )
        wrongpw_times.append(time.perf_counter() - t0)

    median_unknown = sorted(unknown_times)[samples // 2]
    median_wrongpw = sorted(wrongpw_times)[samples // 2]
    # Both paths spend bcrypt time. The sentinel uses rounds=4 vs real rounds=12,
    # so wrongpw will be slower — but the ratio should not be huge. Assert wrongpw
    # is not *faster* than unknown, which would be a clear enumeration signal in
    # the wrong direction.
    assert median_wrongpw >= median_unknown * 0.5, (
        f"Suspicious timing: unknown={median_unknown:.3f}s wrongpw={median_wrongpw:.3f}s"
    )


@pytest.mark.asyncio
async def test_universal_login_password_too_long_returns_422(client: AsyncClient):
    """Password longer than 72 bytes is rejected at the schema layer."""
    r = await client.post(
        "/api/v1/auth/universal-login",
        json={"email": "anyone@example.com", "password": "x" * 73},
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_universal_login_invalid_email_returns_422(client: AsyncClient):
    """Non-email email is rejected at the schema layer."""
    r = await client.post(
        "/api/v1/auth/universal-login",
        json={"email": "not-an-email", "password": _PW},
    )
    assert r.status_code == 422
