"""
tests/test_auth_router_coverage.py

Targeted coverage of src/auth/router.py — next-round PR A of Issue #261.

Covers the endpoints / branches at 0% on main:
  - POST /auth/refresh     — teacher branch (L321-334)
  - PATCH /auth/change-password — student local-auth branch (L543-573)
  - PATCH /student/profile — no-fields 400, grade-locked-by-school 403, name+locale happy
  - GET  /auth/settings    — happy + no notification_preferences row fallback
  - PATCH /auth/settings   — display_name/locale/notifications upsert
  - DELETE /auth/account   — dispatches gdpr_delete_account.delay
"""

from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest
from httpx import AsyncClient

from tests.helpers.token_factory import (
    make_student_token,
)

# ── Helpers ───────────────────────────────────────────────────────────────────


async def _insert_student(
    client: AsyncClient,
    student_id: str,
    *,
    school_id: uuid.UUID | None = None,
    auth_provider: str = "auth0",
    password_hash: str | None = None,
) -> None:
    pool = client._transport.app.state.pool
    await pool.execute(
        """
        INSERT INTO students
            (student_id, external_auth_id, auth_provider, name, email, grade,
             locale, account_status, school_id, password_hash)
        VALUES ($1, $2, $3, $4, $5, 8, 'en', 'active', $6, $7)
        ON CONFLICT (student_id) DO UPDATE
           SET auth_provider = EXCLUDED.auth_provider,
               school_id     = EXCLUDED.school_id,
               password_hash = EXCLUDED.password_hash
        """,
        uuid.UUID(student_id),
        # Use the full (hex-only) UUID so every test's external_auth_id
        # and email are unique, not just the final segment.
        f"auth0|cov-{student_id.replace('-', '')}",
        auth_provider,
        f"Cov Student {student_id[-6:]}",
        f"cov-{student_id.replace('-', '')}@test.invalid",
        school_id,
        password_hash,
    )


async def _insert_school_and_teacher(
    client: AsyncClient,
    school_id: uuid.UUID,
    teacher_id: uuid.UUID,
) -> None:
    pool = client._transport.app.state.pool
    await pool.execute(
        """
        INSERT INTO schools (school_id, name, contact_email, country, status)
        VALUES ($1, $2, $3, 'CA', 'active')
        ON CONFLICT (school_id) DO NOTHING
        """,
        school_id,
        f"Cov School {str(school_id)[:6]}",
        f"school-{str(school_id)[:6]}@test.invalid",
    )
    await pool.execute(
        """
        INSERT INTO teachers
            (teacher_id, school_id, external_auth_id, auth_provider, name, email,
             role, account_status)
        VALUES ($1, $2, $3, 'auth0', $4, $5, 'teacher', 'active')
        ON CONFLICT (teacher_id) DO NOTHING
        """,
        teacher_id,
        school_id,
        f"auth0|cov-t-{str(teacher_id)[:6]}",
        f"Cov Teacher {str(teacher_id)[:6]}",
        f"cov-t-{str(teacher_id)[:6]}@test.invalid",
    )


# ── /auth/refresh teacher branch ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_refresh_token_teacher_branch(client: AsyncClient, fake_redis):
    """Refresh token for a teacher_id resolves teachers table and returns teacher JWT."""
    client._transport.app.state.redis = fake_redis

    school_id = uuid.UUID("d3100000-0000-0000-0000-000000000099")
    teacher_id = uuid.UUID("d2100000-0000-0000-0000-000000000099")
    await _insert_school_and_teacher(client, school_id, teacher_id)

    # Install a refresh token pointing at the teacher ID (not a student ID).
    refresh_token_value = "refresh-for-teacher-cov-99"
    import hashlib

    rt_hash = hashlib.sha256(refresh_token_value.encode()).hexdigest()
    await fake_redis.set(f"refresh:{rt_hash}", str(teacher_id))

    r = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token_value},
    )

    assert r.status_code == 200, r.text
    assert "token" in r.json()


@pytest.mark.asyncio
async def test_refresh_token_unknown_user_returns_401(client: AsyncClient, fake_redis):
    """Refresh token points at an ID that matches no student and no teacher → 401."""
    client._transport.app.state.redis = fake_redis

    ghost_id = str(uuid.UUID("d9000000-0000-0000-0000-000000000099"))
    refresh_token_value = "refresh-for-ghost-cov-99"
    import hashlib

    rt_hash = hashlib.sha256(refresh_token_value.encode()).hexdigest()
    await fake_redis.set(f"refresh:{rt_hash}", ghost_id)

    r = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token_value},
    )

    assert r.status_code == 401
    assert r.json()["error"] == "unauthenticated"


# ── /auth/change-password student branch ──────────────────────────────────────


@pytest.mark.asyncio
async def test_change_password_student_local_auth(client: AsyncClient):
    """Student with local auth can change their password via PATCH /auth/change-password."""
    from src.auth.service import hash_password

    student_id = "d1100000-0000-0000-0000-000000000099"
    existing_hash = await hash_password("OldCorrectPw1!")
    await _insert_student(
        client,
        student_id,
        auth_provider="local",
        password_hash=existing_hash,
    )

    token = make_student_token(student_id=student_id)

    r = await client.patch(
        "/api/v1/auth/change-password",
        headers={"Authorization": f"Bearer {token}"},
        json={"current_password": "OldCorrectPw1!", "new_password": "NewStrongPw2@abc"},
    )

    assert r.status_code == 200, r.text
    body = r.json()
    assert "token" in body and "refresh_token" in body
    assert body["role"] == "student"


@pytest.mark.asyncio
async def test_change_password_wrong_current_password(client: AsyncClient):
    """Wrong current password returns 401 (student branch)."""
    from src.auth.service import hash_password

    student_id = "d1100000-0000-0000-0000-000000000100"
    existing_hash = await hash_password("RealCurrentPw1!")
    await _insert_student(
        client,
        student_id,
        auth_provider="local",
        password_hash=existing_hash,
    )

    token = make_student_token(student_id=student_id)

    r = await client.patch(
        "/api/v1/auth/change-password",
        headers={"Authorization": f"Bearer {token}"},
        json={"current_password": "WrongPw1!", "new_password": "NewStrongPw2@abc"},
    )

    assert r.status_code == 401
    assert r.json()["error"] == "unauthenticated"


@pytest.mark.asyncio
async def test_change_password_student_without_local_auth_rejected(client: AsyncClient):
    """Student on auth0 (no password_hash) can't change password → 400."""
    student_id = "d1100000-0000-0000-0000-000000000101"
    await _insert_student(
        client,
        student_id,
        auth_provider="auth0",  # no local password
        password_hash=None,
    )

    token = make_student_token(student_id=student_id)

    r = await client.patch(
        "/api/v1/auth/change-password",
        headers={"Authorization": f"Bearer {token}"},
        json={"current_password": "anything", "new_password": "NewStrongPw2@abc"},
    )

    assert r.status_code == 400


@pytest.mark.asyncio
async def test_change_password_missing_auth_header_returns_401(client: AsyncClient):
    r = await client.patch(
        "/api/v1/auth/change-password",
        json={"current_password": "x", "new_password": "y" * 12},
    )
    assert r.status_code == 401


# ── /student/profile update branches ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_update_student_profile_no_fields_returns_400(client: AsyncClient):
    student_id = "d1200000-0000-0000-0000-000000000099"
    await _insert_student(client, student_id)

    token = make_student_token(student_id=student_id)
    r = await client.patch(
        "/api/v1/student/profile",
        headers={"Authorization": f"Bearer {token}"},
        json={},  # no name/locale/grade
    )

    assert r.status_code == 400


@pytest.mark.asyncio
async def test_update_student_profile_grade_blocked_for_school_enrolled(
    client: AsyncClient,
):
    """School-enrolled student cannot self-change grade — 403."""
    school_id = uuid.UUID("d3200000-0000-0000-0000-000000000099")
    teacher_id = uuid.UUID("d2200000-0000-0000-0000-000000000099")
    await _insert_school_and_teacher(client, school_id, teacher_id)

    student_id = "d1200000-0000-0000-0000-000000000100"
    await _insert_student(client, student_id, school_id=school_id)

    token = make_student_token(student_id=student_id)
    r = await client.patch(
        "/api/v1/student/profile",
        headers={"Authorization": f"Bearer {token}"},
        json={"grade": 9},
    )

    assert r.status_code == 403
    assert r.json()["error"] == "forbidden"


@pytest.mark.asyncio
async def test_update_student_profile_name_locale_happy(client: AsyncClient):
    """Unaffiliated student updates name + locale — 200 with new values."""
    student_id = "d1200000-0000-0000-0000-000000000101"
    await _insert_student(client, student_id)

    token = make_student_token(student_id=student_id)
    r = await client.patch(
        "/api/v1/student/profile",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Renamed Alice", "locale": "fr"},
    )

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["name"] == "Renamed Alice"
    assert body["locale"] == "fr"


# ── /auth/settings ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_settings_falls_back_when_no_notif_row(client: AsyncClient):
    """Student with no notification_preferences row → defaults all True."""
    student_id = "d1300000-0000-0000-0000-000000000099"
    await _insert_student(client, student_id)

    token = make_student_token(student_id=student_id)
    r = await client.get(
        "/api/v1/auth/settings",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert r.status_code == 200, r.text
    body = r.json()
    assert "display_name" in body
    assert body["locale"] == "en"
    assert body["notifications"] == {
        "streak_reminders": True,
        "weekly_summary": True,
        "quiz_nudges": True,
    }


@pytest.mark.asyncio
async def test_update_settings_roundtrip_display_name_locale_notifications(
    client: AsyncClient,
):
    """PATCH /auth/settings persists all three fields; subsequent GET reflects them."""
    student_id = "d1300000-0000-0000-0000-000000000100"
    await _insert_student(client, student_id)

    token = make_student_token(student_id=student_id)

    r = await client.patch(
        "/api/v1/auth/settings",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "display_name": "New Display",
            "locale": "es",
            "notifications": {
                "streak_reminders": False,
                "weekly_summary": True,
                "quiz_nudges": False,
            },
        },
    )
    assert r.status_code == 200, r.text

    r2 = await client.get(
        "/api/v1/auth/settings",
        headers={"Authorization": f"Bearer {token}"},
    )
    body = r2.json()
    assert body["display_name"] == "New Display"
    assert body["locale"] == "es"
    assert body["notifications"] == {
        "streak_reminders": False,
        "weekly_summary": True,
        "quiz_nudges": False,
    }


@pytest.mark.asyncio
async def test_update_settings_ignores_invalid_locale(client: AsyncClient):
    """Locale outside {en, fr, es} is silently skipped — no DB update for that column."""
    student_id = "d1300000-0000-0000-0000-000000000101"
    await _insert_student(client, student_id)

    token = make_student_token(student_id=student_id)
    r = await client.patch(
        "/api/v1/auth/settings",
        headers={"Authorization": f"Bearer {token}"},
        json={"locale": "xx"},
    )
    assert r.status_code == 200, r.text

    # Locale unchanged on GET.
    r2 = await client.get(
        "/api/v1/auth/settings",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r2.json()["locale"] == "en"


# ── DELETE /auth/account ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_delete_account_dispatches_gdpr_task(client: AsyncClient):
    """DELETE /auth/account returns 200 and dispatches gdpr_delete_account.delay."""
    student_id = "d1400000-0000-0000-0000-000000000099"
    await _insert_student(client, student_id)

    token = make_student_token(student_id=student_id)

    with patch("src.auth.tasks.gdpr_delete_account.delay") as mock_delay:
        r = await client.delete(
            "/api/v1/auth/account",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert r.status_code == 200
    mock_delay.assert_called_once()
    # First positional arg is student_id; second is the external_auth_id we inserted.
    call_args = mock_delay.call_args.args
    assert call_args[0] == student_id
    assert call_args[1].startswith("auth0|cov-")
