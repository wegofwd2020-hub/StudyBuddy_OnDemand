"""
tests/test_temp_password_expiry_664.py

School-issued temporary passwords expire (issue #664).

Venki 2026-08-27: *"Allows me login today using the password received through
mail yesterday (Looks password expiry policy is not defined for this activity)."*

Provisioning generates a random password, emails it in plaintext, and sets
`first_login = TRUE` — but nothing bounded how long that credential stayed
valid. So it sits in an inbox, and in every archive, forward and backup that
inbox reaches, and works forever.

`first_login` is a PROMPT, not an expiry: it fires whenever the person
eventually logs in, which may be never, while the password stays live.

## The three properties that matter

  - a temporary password stops working after its window;
  - a password the USER chose never expires — only the one somebody else picked
    and emailed them;
  - NULL means no expiry, so accounts provisioned before this shipped are not
    locked out by the deploy.

## And one that is easy to get wrong

The expiry is checked AFTER the password itself verifies. Checking it first
would make the endpoint an oracle: a wrong password would answer "expired" for
a real account and "invalid" for an unknown one, which is the enumeration leak
the timing sentinel elsewhere in this module exists to prevent.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from httpx import AsyncClient

_PW = "SecureTestPwd1!"


async def _school(client: AsyncClient, suffix: str) -> dict:
    r = await client.post(
        "/api/v1/schools/register",
        json={
            "school_name": f"Expiry School{suffix}",
            "contact_email": f"expiry{suffix}@school.example.com",
            "country": "IN",
            "password": _PW,
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


async def _set_expiry(client: AsyncClient, email: str, when: datetime | None) -> None:
    """Move a provisioned account's password expiry, as time passing would."""
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await conn.execute(
            "UPDATE students SET password_expires_at = $1 WHERE email = $2", when, email
        )
        await conn.execute(
            "UPDATE teachers SET password_expires_at = $1 WHERE email = $2", when, email
        )


# The provision response deliberately does NOT return the generated password —
# it is emailed and nothing else (unlike admin reset, which hands it back to the
# caller; that asymmetry is part of why #665 keeps reset with the primary school
# only). So the test pins the generator instead of reading it off the response.
_KNOWN_TEMP = "KnownTempPwd1!"


async def _provision_student(client: AsyncClient, school: dict) -> tuple[str, str]:
    """Returns (email, temporary password)."""
    email = f"expiry-{uuid.uuid4().hex[:8]}@example.com"
    with patch("src.school.service.generate_default_password", return_value=_KNOWN_TEMP):
        r = await client.post(
            f"/api/v1/schools/{school['school_id']}/students",
            headers={"Authorization": f"Bearer {school['access_token']}"},
            json={"name": "Expiry Student", "email": email, "grade": 8},
        )
    assert r.status_code == 201, r.text
    return email, _KNOWN_TEMP


async def _login(client: AsyncClient, email: str, password: str):
    return await client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )


@pytest.mark.asyncio
async def test_a_fresh_temporary_password_works(client, db_conn):
    """The normal case: provisioned today, used today."""
    school = await _school(client, "_fresh")
    email, password = await _provision_student(client, school)

    r = await _login(client, email, password)
    assert r.status_code == 200, r.text
    assert r.json()["first_login"] is True, r.json()


@pytest.mark.asyncio
async def test_an_expired_temporary_password_is_refused(client, db_conn):
    """The reported case, once the window has passed."""
    school = await _school(client, "_expired")
    email, password = await _provision_student(client, school)
    await _set_expiry(client, email, datetime.now(tz=UTC) - timedelta(hours=1))

    r = await _login(client, email, password)
    assert r.status_code == 401, r.text
    body = r.json()
    assert body["error"] == "temp_password_expired", body
    # Age-appropriate and actionable: it says what to do next, and exposes no
    # status code or identifier (Content Rule #5).
    assert "ask your school" in body["detail"].lower(), body


@pytest.mark.asyncio
async def test_provisioning_stamps_an_expiry(client, db_conn):
    """Guards the stamp itself — the check is worthless if nothing sets it."""
    school = await _school(client, "_stamp")
    email, _ = await _provision_student(client, school)

    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        expires = await conn.fetchval(
            "SELECT password_expires_at FROM students WHERE email = $1", email
        )
    assert expires is not None, "provisioning left the password unbounded"
    assert expires > datetime.now(tz=UTC), expires


@pytest.mark.asyncio
async def test_a_password_the_user_chose_never_expires(client, db_conn):
    """Only a credential somebody ELSE picked has a lifetime.

    After the forced first-login change, the account must not start lapsing.
    """
    school = await _school(client, "_chosen")
    email, temp = await _provision_student(client, school)

    login = await _login(client, email, temp)
    token = login.json()["token"]

    chosen = "MyOwnChosenPwd1!"
    r = await client.patch(
        "/api/v1/auth/change-password",
        headers={"Authorization": f"Bearer {token}"},
        json={"current_password": temp, "new_password": chosen},
    )
    assert r.status_code == 200, r.text

    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        expires = await conn.fetchval(
            "SELECT password_expires_at FROM students WHERE email = $1", email
        )
    assert expires is None, f"a self-chosen password was given an expiry: {expires}"

    # And it keeps working even with the clock well past the old window.
    r = await _login(client, email, chosen)
    assert r.status_code == 200, r.text


@pytest.mark.asyncio
async def test_an_account_with_no_expiry_still_logs_in(client, db_conn):
    """NULL means no expiry.

    Every account provisioned before this shipped has NULL, and a deploy must
    not lock them out.
    """
    school = await _school(client, "_legacy")
    email, password = await _provision_student(client, school)
    await _set_expiry(client, email, None)

    r = await _login(client, email, password)
    assert r.status_code == 200, r.text


@pytest.mark.asyncio
async def test_expiry_is_not_an_account_enumeration_oracle(client, db_conn):
    """A WRONG password on an expired account must look like any other failure.

    Checking expiry before verifying the password would let an attacker sort
    real accounts from unknown ones without holding any credential.
    """
    school = await _school(client, "_oracle")
    email, _ = await _provision_student(client, school)
    await _set_expiry(client, email, datetime.now(tz=UTC) - timedelta(hours=1))

    real = await _login(client, email, "TotallyWrongPassword1!")
    unknown = await _login(client, "no-such-account-9f3a@example.com", "TotallyWrongPassword1!")

    assert real.status_code == unknown.status_code == 401
    assert real.json()["error"] == unknown.json()["error"], (real.json(), unknown.json())
