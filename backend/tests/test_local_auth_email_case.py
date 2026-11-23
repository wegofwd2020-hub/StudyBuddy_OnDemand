"""
Local login and password reset match email addresses case-insensitively.
Venki typed "Chnsuri@gmail.com" for an account stored as "chnsuri@gmail.com";
the exact match found no account, so no reset mail was sent.
"""

from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest
from httpx import AsyncClient

from src.auth.service import find_local_user_by_email

_PW = "SecureTestPwd1!"
_KNOWN_TEMP = "KnownTempPwd1!"


async def _school(client: AsyncClient, suffix: str) -> dict:
    r = await client.post(
        "/api/v1/schools/register",
        json={
            "school_name": f"Case School{suffix}",
            "contact_email": f"case{suffix}@school.example.com",
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
            json={"name": "Case Student", "email": email, "grade": 8},
        )
    assert r.status_code == 201, r.text


@pytest.mark.asyncio
async def test_login_matches_capitalised_email(client, db_conn):
    school = await _school(client, "_login")
    email = f"case-{uuid.uuid4().hex[:8]}@example.com"
    await _provision_student(client, school, email)

    capitalised = email[0].upper() + email[1:]
    r = await client.post(
        "/api/v1/auth/login", json={"email": capitalised, "password": _KNOWN_TEMP}
    )
    assert r.status_code == 200, r.text


@pytest.mark.asyncio
async def test_reset_lookup_matches_capitalised_email(client, db_conn):
    school = await _school(client, "_reset")
    email = f"case-{uuid.uuid4().hex[:8]}@example.com"
    await _provision_student(client, school, email)

    capitalised = email[0].upper() + email[1:]
    found = await find_local_user_by_email(client._transport.app.state.pool, capitalised)
    assert found is not None
    assert found["user_type"] == "student", found
