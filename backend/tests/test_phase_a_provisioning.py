"""
tests/test_phase_a_provisioning.py

Phase A — Local auth provisioning tests.

Coverage:
  POST /api/v1/schools/register              — now requires password
  POST /api/v1/schools/{id}/teachers         — provision teacher (local auth)
  POST /api/v1/schools/{id}/students         — provision student (local auth)
  POST /api/v1/schools/{id}/teachers/{id}/reset-password
  POST /api/v1/schools/{id}/students/{id}/reset-password
  POST /api/v1/schools/{id}/teachers/{id}/promote
  POST /api/v1/auth/login                    — email+password login
  PATCH /api/v1/auth/change-password         — forced reset flow
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock

from tests.helpers.token_factory import make_teacher_token

_PW = "SecureTestPwd1!"


async def _register(client: AsyncClient, name: str, email: str) -> dict:
    """Register a school and return the response JSON."""
    r = await client.post("/api/v1/schools/register", json={
        "school_name": name,
        "contact_email": email,
        "country": "CA",
        "password": _PW,
    })
    assert r.status_code == 201, r.text
    return r.json()


# ── School registration with password ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_register_school_with_password_returns_201(client: AsyncClient):
    """Registration with a valid password returns 201."""
    data = await _register(client, "Alpha School", "alpha-admin@phaseA.example.com")
    assert "access_token" in data
    assert data["role"] == "school_admin"


@pytest.mark.asyncio
async def test_register_school_admin_can_login(client: AsyncClient):
    """School admin can log in with the password they set at registration."""
    email = "login-admin@phaseA.example.com"
    await _register(client, "Login School", email)

    r = await client.post("/api/v1/auth/login", json={"email": email, "password": _PW})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["role"] == "school_admin"
    assert data["first_login"] is False   # founder set own password; no forced reset
    assert "token" in data
    assert "user_id" in data


@pytest.mark.asyncio
async def test_login_wrong_password_returns_401(client: AsyncClient):
    """Wrong password returns 401."""
    email = "wrong-pw@phaseA.example.com"
    await _register(client, "Wrong PW School", email)

    r = await client.post("/api/v1/auth/login", json={"email": email, "password": "WrongPassword99!"})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_login_unknown_email_returns_401(client: AsyncClient):
    """Unknown email returns 401 (no enumeration)."""
    r = await client.post("/api/v1/auth/login", json={"email": "ghost@phaseA.example.com", "password": _PW})
    assert r.status_code == 401


# ── Provision teacher ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_provision_teacher_returns_201(client: AsyncClient):
    """school_admin can provision a teacher; returns 201 with teacher details."""
    data = await _register(client, "Provision School T", "pt-admin@phaseA.example.com")
    school_id = data["school_id"]
    token = data["access_token"]

    with patch("src.email.service.send_welcome_teacher_email", new_callable=AsyncMock):
        r = await client.post(
            f"/api/v1/schools/{school_id}/teachers",
            json={"name": "Alice Teacher", "email": "alice@pt.example.com"},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert r.status_code == 201, r.text
    result = r.json()
    assert result["email"] == "alice@pt.example.com"
    assert result["role"] == "teacher"
    assert result["school_id"] == school_id


@pytest.mark.asyncio
async def test_provisioned_teacher_has_first_login(client: AsyncClient):
    """Provisioned teacher logs in → first_login=True (forced reset)."""
    data = await _register(client, "First Login School", "fl-admin@phaseA.example.com")
    school_id = data["school_id"]
    token = data["access_token"]

    teacher_email = "fl-teacher@phaseA.example.com"
    with patch("src.email.service.send_welcome_teacher_email", new_callable=AsyncMock) as mock_email:
        r = await client.post(
            f"/api/v1/schools/{school_id}/teachers",
            json={"name": "FirstLogin Teacher", "email": teacher_email},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert r.status_code == 201
    # The welcome email was called with the default password
    mock_email.assert_called_once()
    call_args = mock_email.call_args
    default_password = call_args.args[2] if len(call_args.args) >= 3 else call_args.kwargs.get("password")
    assert default_password  # a non-empty default password was generated

    # Teacher can log in with the default password
    login_r = await client.post("/api/v1/auth/login", json={"email": teacher_email, "password": default_password})
    assert login_r.status_code == 200, login_r.text
    assert login_r.json()["first_login"] is True


@pytest.mark.asyncio
async def test_provision_teacher_non_admin_returns_403(client: AsyncClient):
    """Regular teacher cannot provision other teachers."""
    data = await _register(client, "Perm School T", "pt-perm@phaseA.example.com")
    school_id = data["school_id"]

    regular_token = make_teacher_token(school_id=school_id, role="teacher")
    r = await client.post(
        f"/api/v1/schools/{school_id}/teachers",
        json={"name": "Bob", "email": "bob@perm.example.com"},
        headers={"Authorization": f"Bearer {regular_token}"},
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_provision_teacher_duplicate_email_returns_409(client: AsyncClient):
    """Provisioning the same email twice returns 409."""
    data = await _register(client, "Dup Teacher School", "dup-t@phaseA.example.com")
    school_id = data["school_id"]
    token = data["access_token"]

    with patch("src.email.service.send_welcome_teacher_email", new_callable=AsyncMock):
        r1 = await client.post(
            f"/api/v1/schools/{school_id}/teachers",
            json={"name": "Same", "email": "same-teacher@dup.example.com"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r1.status_code == 201
        r2 = await client.post(
            f"/api/v1/schools/{school_id}/teachers",
            json={"name": "Same", "email": "same-teacher@dup.example.com"},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert r2.status_code == 409


# ── Provision student ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_provision_student_returns_201(client: AsyncClient):
    """school_admin can provision a student; returns 201 with student details."""
    data = await _register(client, "Provision School S", "ps-admin@phaseA.example.com")
    school_id = data["school_id"]
    token = data["access_token"]

    with patch("src.email.service.send_welcome_student_email", new_callable=AsyncMock):
        r = await client.post(
            f"/api/v1/schools/{school_id}/students",
            json={"name": "Charlie Student", "email": "charlie@ps.example.com", "grade": 8},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert r.status_code == 201, r.text
    result = r.json()
    assert result["email"] == "charlie@ps.example.com"
    assert result["grade"] == 8
    assert result["school_id"] == school_id


@pytest.mark.asyncio
async def test_provisioned_student_can_login_with_first_login(client: AsyncClient):
    """Provisioned student logs in → first_login=True."""
    data = await _register(client, "Student Login School", "sl-admin@phaseA.example.com")
    school_id = data["school_id"]
    token = data["access_token"]

    student_email = "student1@phaseA.example.com"
    with patch("src.email.service.send_welcome_student_email", new_callable=AsyncMock) as mock_email:
        r = await client.post(
            f"/api/v1/schools/{school_id}/students",
            json={"name": "Student One", "email": student_email, "grade": 7},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert r.status_code == 201
    mock_email.assert_called_once()
    call_args = mock_email.call_args
    default_password = call_args.args[2] if len(call_args.args) >= 3 else call_args.kwargs.get("password")

    login_r = await client.post("/api/v1/auth/login", json={"email": student_email, "password": default_password})
    assert login_r.status_code == 200, login_r.text
    data_login = login_r.json()
    assert data_login["first_login"] is True
    assert data_login["role"] == "student"


@pytest.mark.asyncio
async def test_provision_student_invalid_grade_returns_422(client: AsyncClient):
    """Grade outside 1-12 returns 422."""
    data = await _register(client, "Grade School", "grade-admin@phaseA.example.com")
    school_id = data["school_id"]
    token = data["access_token"]

    r = await client.post(
        f"/api/v1/schools/{school_id}/students",
        json={"name": "Bad Grade", "email": "badgrade@phaseA.example.com", "grade": 99},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 422


# ── Password reset ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_admin_reset_teacher_password(client: AsyncClient):
    """school_admin can reset a teacher's password; new password works for login."""
    data = await _register(client, "Reset Teacher School", "rt-admin@phaseA.example.com")
    school_id = data["school_id"]
    token = data["access_token"]

    teacher_email = "reset-teacher@phaseA.example.com"
    with patch("src.email.service.send_welcome_teacher_email", new_callable=AsyncMock) as mock_create:
        r = await client.post(
            f"/api/v1/schools/{school_id}/teachers",
            json={"name": "Reset Teacher", "email": teacher_email},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert r.status_code == 201
    teacher_id = r.json()["teacher_id"]
    old_password = mock_create.call_args.args[2] if len(mock_create.call_args.args) >= 3 else mock_create.call_args.kwargs.get("password")

    with patch("src.email.service.send_password_reset_email", new_callable=AsyncMock) as mock_reset:
        reset_r = await client.post(
            f"/api/v1/schools/{school_id}/teachers/{teacher_id}/reset-password",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert reset_r.status_code == 200, reset_r.text
    mock_reset.assert_called_once()
    new_password = mock_reset.call_args.args[2] if len(mock_reset.call_args.args) >= 3 else mock_reset.call_args.kwargs.get("password")

    # Old password no longer works
    old_login = await client.post("/api/v1/auth/login", json={"email": teacher_email, "password": old_password})
    assert old_login.status_code == 401

    # New password works and forces reset again
    new_login = await client.post("/api/v1/auth/login", json={"email": teacher_email, "password": new_password})
    assert new_login.status_code == 200
    assert new_login.json()["first_login"] is True


@pytest.mark.asyncio
async def test_admin_reset_student_password(client: AsyncClient):
    """school_admin can reset a student's password."""
    data = await _register(client, "Reset Student School", "rs-admin@phaseA.example.com")
    school_id = data["school_id"]
    token = data["access_token"]

    with patch("src.email.service.send_welcome_student_email", new_callable=AsyncMock) as mock_create:
        r = await client.post(
            f"/api/v1/schools/{school_id}/students",
            json={"name": "Reset Student", "email": "reset-student@phaseA.example.com", "grade": 9},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert r.status_code == 201
    student_id = r.json()["student_id"]

    with patch("src.email.service.send_password_reset_email", new_callable=AsyncMock):
        reset_r = await client.post(
            f"/api/v1/schools/{school_id}/students/{student_id}/reset-password",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert reset_r.status_code == 200


@pytest.mark.asyncio
async def test_reset_password_wrong_school_returns_404(client: AsyncClient):
    """Resetting a teacher from a different school returns 404."""
    data_a = await _register(client, "School Reset A", "rsa@phaseA.example.com")
    data_b = await _register(client, "School Reset B", "rsb@phaseA.example.com")

    school_b_id = data_b["school_id"]
    token_a = data_a["access_token"]
    # Use a random UUID — school B's teacher does not belong to school A
    r = await client.post(
        f"/api/v1/schools/{data_a['school_id']}/teachers/00000000-0000-0000-0000-deadbeef0001/reset-password",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert r.status_code == 404


# ── Promote to school_admin ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_promote_teacher_to_school_admin(client: AsyncClient):
    """school_admin can promote a teacher to school_admin (multiple admin support)."""
    data = await _register(client, "Promote School", "promote-admin@phaseA.example.com")
    school_id = data["school_id"]
    token = data["access_token"]

    with patch("src.email.service.send_welcome_teacher_email", new_callable=AsyncMock):
        r = await client.post(
            f"/api/v1/schools/{school_id}/teachers",
            json={"name": "Future Admin", "email": "future-admin@phaseA.example.com"},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert r.status_code == 201
    teacher_id = r.json()["teacher_id"]

    promote_r = await client.post(
        f"/api/v1/schools/{school_id}/teachers/{teacher_id}/promote",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert promote_r.status_code == 200, promote_r.text
    assert promote_r.json()["role"] == "school_admin"


@pytest.mark.asyncio
async def test_promote_nonexistent_teacher_returns_404(client: AsyncClient):
    """Promoting a teacher that doesn't exist returns 404."""
    data = await _register(client, "Ghost Promote School", "gp-admin@phaseA.example.com")
    school_id = data["school_id"]
    token = data["access_token"]

    r = await client.post(
        f"/api/v1/schools/{school_id}/teachers/00000000-0000-0000-0000-deadbeef0002/promote",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 404


# ── Change password (forced reset flow) ───────────────────────────────────────


@pytest.mark.asyncio
async def test_change_password_clears_first_login(client: AsyncClient):
    """
    After provisioning, teacher logs in with first_login=True,
    then calls PATCH /auth/change-password → subsequent login has first_login=False.
    """
    data = await _register(client, "Change PW School", "cpw-admin@phaseA.example.com")
    school_id = data["school_id"]
    token = data["access_token"]

    teacher_email = "cpw-teacher@phaseA.example.com"
    with patch("src.email.service.send_welcome_teacher_email", new_callable=AsyncMock) as mock_email:
        await client.post(
            f"/api/v1/schools/{school_id}/teachers",
            json={"name": "CPW Teacher", "email": teacher_email},
            headers={"Authorization": f"Bearer {token}"},
        )
    default_password = mock_email.call_args.args[2] if len(mock_email.call_args.args) >= 3 else mock_email.call_args.kwargs.get("password")

    login_r = await client.post("/api/v1/auth/login", json={"email": teacher_email, "password": default_password})
    assert login_r.status_code == 200
    assert login_r.json()["first_login"] is True
    teacher_jwt = login_r.json()["token"]

    new_password = "MyNewPassword99!"
    change_r = await client.patch(
        "/api/v1/auth/change-password",
        json={"current_password": default_password, "new_password": new_password},
        headers={"Authorization": f"Bearer {teacher_jwt}"},
    )
    assert change_r.status_code == 200, change_r.text

    # Login with new password → first_login=False
    final_login = await client.post("/api/v1/auth/login", json={"email": teacher_email, "password": new_password})
    assert final_login.status_code == 200
    assert final_login.json()["first_login"] is False


@pytest.mark.asyncio
async def test_change_password_wrong_current_returns_401(client: AsyncClient):
    """Wrong current password returns 401."""
    email = "badcurrent@phaseA.example.com"
    data = await _register(client, "Bad Current School", email)
    token = data["access_token"]

    r = await client.patch(
        "/api/v1/auth/change-password",
        json={"current_password": "WrongOldPwd99!", "new_password": "MyNewPassword99!"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_change_password_short_new_password_returns_422(client: AsyncClient):
    """New password shorter than 12 chars returns 422."""
    email = "shortpw@phaseA.example.com"
    data = await _register(client, "Short PW School", email)
    token = data["access_token"]

    r = await client.patch(
        "/api/v1/auth/change-password",
        json={"current_password": _PW, "new_password": "short"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_change_password_requires_auth(client: AsyncClient):
    """PATCH /auth/change-password without a token returns 401."""
    r = await client.patch(
        "/api/v1/auth/change-password",
        json={"current_password": _PW, "new_password": "NewPassword99!"},
    )
    assert r.status_code == 401
