"""
A retired (account_status='deleted') teacher must not shadow a student that
shares its email. Local login checks teachers first; a deleted teacher row
must be skipped so the lookup falls through to the student.
"""

from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest
from httpx import AsyncClient

from src.auth.service import find_local_user_by_email, hash_password

_PW = "SecureTestPwd1!"
_KNOWN_TEMP = "KnownTempPwd1!"


async def _school(client: AsyncClient, suffix: str) -> dict:
    r = await client.post(
        "/api/v1/schools/register",
        json={
            "school_name": f"Shadow School{suffix}",
            "contact_email": f"shadow{suffix}@school.example.com",
            "country": "IN",
            "password": _PW,
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


async def _provision_student(client: AsyncClient, school: dict, email: str) -> None:
    with patch("src.school.service.generate_default_password", return_value=_KNOWN_TEMP):
        r = await client.post(
            f"/api/v1/schools/{school['school_id']}/students",
            headers={"Authorization": f"Bearer {school['access_token']}"},
            json={"name": "Shadow Student", "email": email, "grade": 8},
        )
    assert r.status_code == 201, r.text


async def _insert_retired_teacher(client: AsyncClient, school: dict, email: str) -> None:
    pool = client._transport.app.state.pool
    password_hash = await hash_password(_KNOWN_TEMP)
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await conn.execute(
            """
            INSERT INTO teachers
                (school_id, external_auth_id, name, email, role, account_status,
                 auth_provider, password_hash)
            VALUES ($1::uuid, $2, 'Retired Teacher', $3, 'teacher', 'deleted',
                    'local', $4)
            """,
            school["school_id"],
            f"retired-{uuid.uuid4().hex}",
            email,
            password_hash,
        )


@pytest.mark.asyncio
async def test_retired_teacher_does_not_shadow_student_login(client, db_conn):
    school = await _school(client, "_fallthrough")
    email = f"shadow-{uuid.uuid4().hex[:8]}@example.com"
    await _provision_student(client, school, email)
    await _insert_retired_teacher(client, school, email)

    r = await client.post("/api/v1/auth/login", json={"email": email, "password": _KNOWN_TEMP})
    assert r.status_code == 200, r.text
    assert r.json()["first_login"] is True, r.json()


@pytest.mark.asyncio
async def test_retired_teacher_does_not_shadow_password_reset_lookup(client, db_conn):
    school = await _school(client, "_reset_fallthrough")
    email = f"shadow-{uuid.uuid4().hex[:8]}@example.com"
    await _provision_student(client, school, email)
    await _insert_retired_teacher(client, school, email)

    found = await find_local_user_by_email(client._transport.app.state.pool, email)
    assert found is not None
    assert found["user_type"] == "student", found
