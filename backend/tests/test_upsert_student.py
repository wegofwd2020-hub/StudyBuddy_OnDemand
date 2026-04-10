"""
tests/test_upsert_student.py

Tests for upsert_student account_status transition rules (#118).

Scenario matrix:
  1. pending → re-login without consent  → stays pending (still blocked)
  2. pending → re-login with consent     → transitions to active (COPPA fix)
  3. suspended → re-login               → stays suspended (never auto-unsuspend)
  4. active → re-login                  → stays active
  5. school-enrolled student re-login   → grade not overridden by Auth0 claim
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


# ── Helpers ───────────────────────────────────────────────────────────────────


def _claims(
    sub: str,
    email: str | None = None,
    grade: int = 8,
    requires_consent: bool = False,
) -> dict:
    # Each sub gets a deterministic but unique email to avoid students_email_key violations.
    resolved_email = email or f"student-{sub.replace('|', '-').replace('auth0-', '')}@example.com"
    return {
        "sub": sub,
        "email": resolved_email,
        "name": "Test Student",
        "https://studybuddy.app/grade": grade,
        "locale": "en",
        "aud": "test-student-client-id",
        "https://studybuddy.app/requires_parental_consent": requires_consent,
    }


async def _exchange(client: AsyncClient, claims: dict) -> dict:
    with patch("src.auth.router.verify_auth0_token", AsyncMock(return_value=claims)):
        r = await client.post("/api/v1/auth/exchange", json={"id_token": "fake"})
    return r


async def _get_account_status(client: AsyncClient, student_id: str) -> str:
    pool = client._transport.app.state.pool
    return await pool.fetchval(
        "SELECT account_status::text FROM students WHERE student_id = $1",
        uuid.UUID(student_id),
    )


async def _set_account_status(client: AsyncClient, student_id: str, status: str) -> None:
    pool = client._transport.app.state.pool
    await pool.execute(
        "UPDATE students SET account_status = $1::account_status WHERE student_id = $2",
        status,
        uuid.UUID(student_id),
    )


# ── Tests ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_pending_stays_pending_without_consent(client: AsyncClient):
    """
    Under-13 student re-authenticates while still pending consent.
    account_status must stay 'pending' — not flip to active.
    """
    sub = f"auth0|{uuid.uuid4()}"

    # First login — creates the pending account.
    r1 = await _exchange(client, _claims(sub, requires_consent=True))
    assert r1.status_code == 403
    assert r1.json()["error"] == "account_pending"

    # Second login — still pending consent (Auth0 still sends requires_parental_consent=True).
    r2 = await _exchange(client, _claims(sub, requires_consent=True))
    assert r2.status_code == 403
    assert r2.json()["error"] == "account_pending"

    # Confirm DB value is still 'pending'.
    pool = client._transport.app.state.pool
    status = await pool.fetchval(
        "SELECT account_status::text FROM students WHERE external_auth_id = $1",
        sub,
    )
    assert status == "pending"


@pytest.mark.asyncio
async def test_pending_transitions_to_active_after_consent(client: AsyncClient):
    """
    COPPA fix: student was pending, parent completes consent externally.
    Auth0 now sends requires_parental_consent=False → account_status must become 'active'.
    """
    sub = f"auth0|{uuid.uuid4()}"

    # First login — pending.
    r1 = await _exchange(client, _claims(sub, requires_consent=True))
    assert r1.status_code == 403
    assert r1.json()["error"] == "account_pending"

    # Second login — consent completed; Auth0 no longer sets the flag.
    r2 = await _exchange(client, _claims(sub, requires_consent=False))
    assert r2.status_code == 200, r2.text
    data = r2.json()
    assert data["student"]["account_status"] == "active"

    # Confirm in DB.
    pool = client._transport.app.state.pool
    status = await pool.fetchval(
        "SELECT account_status::text FROM students WHERE external_auth_id = $1",
        sub,
    )
    assert status == "active"


@pytest.mark.asyncio
async def test_suspended_stays_suspended_on_relogin(client: AsyncClient):
    """
    Suspended student re-authenticates — must not be silently re-activated.
    The exchange endpoint returns 403 account_suspended, not 200.
    """
    sub = f"auth0|{uuid.uuid4()}"

    # Create active account (email derived from sub — unique per test).
    r1 = await _exchange(client, _claims(sub))
    assert r1.status_code == 200
    student_id = r1.json()["student_id"]

    # Manually suspend.
    await _set_account_status(client, student_id, "suspended")

    # Re-authenticate — must remain suspended.
    r2 = await _exchange(client, _claims(sub))
    assert r2.status_code == 403
    assert r2.json()["error"] == "account_suspended"

    # Confirm in DB.
    assert await _get_account_status(client, student_id) == "suspended"


@pytest.mark.asyncio
async def test_active_stays_active_on_relogin(client: AsyncClient):
    """Active student re-logs in — account_status stays active."""
    sub = f"auth0|{uuid.uuid4()}"

    r1 = await _exchange(client, _claims(sub))
    assert r1.status_code == 200
    student_id = r1.json()["student_id"]
    assert await _get_account_status(client, student_id) == "active"

    r2 = await _exchange(client, _claims(sub))
    assert r2.status_code == 200
    assert r2.json()["student"]["account_status"] == "active"
    assert await _get_account_status(client, student_id) == "active"


@pytest.mark.asyncio
async def test_school_enrolled_grade_not_overridden(client: AsyncClient):
    """
    School-enrolled student re-authenticates with a different grade in the Auth0 claim.
    The school-assigned grade must be preserved — never overridden by the JWT claim.
    """
    sub = f"auth0|{uuid.uuid4()}"

    # Create student at grade 8.
    r1 = await _exchange(client, _claims(sub, email="enrolled@example.com", grade=8))
    assert r1.status_code == 200
    student_id = r1.json()["student_id"]

    # Simulate school enrolment: create a school (bypassing RLS) then link student.
    pool = client._transport.app.state.pool
    school_id = uuid.uuid4()
    async with pool.acquire() as conn:
        await conn.execute(
            "SELECT set_config('app.current_school_id', 'bypass', false)"
        )
        await conn.execute(
            """
            INSERT INTO schools (school_id, name, contact_email, country, status)
            VALUES ($1, 'Grade Test School', $2, 'CA', 'active')
            ON CONFLICT DO NOTHING
            """,
            school_id,
            f"gradeschool-{uuid.uuid4().hex[:8]}@example.com",
        )
        await conn.execute(
            "UPDATE students SET school_id = $1, grade = 10 WHERE student_id = $2",
            school_id,
            uuid.UUID(student_id),
        )

    # Re-authenticate with grade=12 in Auth0 claim — school-managed grade must not change.
    r2 = await _exchange(client, _claims(sub, email="enrolled@example.com", grade=12))
    assert r2.status_code == 200

    db_grade = await pool.fetchval(
        "SELECT grade FROM students WHERE student_id = $1",
        uuid.UUID(student_id),
    )
    assert db_grade == 10, f"Expected grade 10 (school-assigned) but got {db_grade}"
