"""
tests/test_test_run_email_in_use.py

A test run must not send credentials to an address that already belongs to a real
student or teacher. The duplicate guard only checked the synthetic +student/+teacher
addresses, so a real account at the typed address was never seen.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from tests.test_demo_test_run import _capture_test_run_emails


async def _register_school(client: AsyncClient, name: str, email: str) -> str:
    r = await client.post(
        "/api/v1/schools/register",
        json={"school_name": name, "contact_email": email, "country": "CA", "password": "SecureTestPwd1!"},
    )
    assert r.status_code == 201, r.text
    return r.json()["school_id"]


async def _insert_real_student(client: AsyncClient, school_id: str, email: str) -> None:
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await conn.execute(
            """
            INSERT INTO students
                (student_id, external_auth_id, name, email, grade, locale, account_status, school_id)
            VALUES ($1, $2, 'Real Student', $3, 8, 'en', 'active', $4)
            """,
            uuid.uuid4(),
            f"auth0|eu-{uuid.uuid4().hex}",
            email,
            uuid.UUID(school_id),
        )


@pytest.mark.asyncio
async def test_request_for_an_existing_students_address_is_409(client: AsyncClient, db_conn) -> None:
    school_id = await _register_school(client, "Email In Use 1", "email-in-use-1@example.com")
    await _insert_real_student(client, school_id, "eu-existing@example.com")

    with _capture_test_run_emails() as captured:
        r = await client.post(
            "/api/v1/demo/test-run/request",
            json={"name": "Visitor", "email": "eu-existing@example.com"},
        )

    assert r.status_code == 409, r.text
    assert r.json()["error"] == "email_in_use"
    assert captured["get_token"]() is None, "no verification email may go to an existing account"


@pytest.mark.asyncio
async def test_plus_tagged_form_of_an_existing_address_is_409(client: AsyncClient, db_conn) -> None:
    school_id = await _register_school(client, "Email In Use 2", "email-in-use-2@example.com")
    await _insert_real_student(client, school_id, "eu-base@example.com")

    with _capture_test_run_emails() as captured:
        r = await client.post(
            "/api/v1/demo/test-run/request",
            json={"name": "Visitor", "email": "eu-base+trial@example.com"},
        )

    assert r.status_code == 409, r.text
    assert r.json()["error"] == "email_in_use"
    assert captured["get_token"]() is None


@pytest.mark.asyncio
async def test_account_created_between_request_and_verify_gets_no_credentials(
    client: AsyncClient, db_conn
) -> None:
    with _capture_test_run_emails() as captured:
        r1 = await client.post(
            "/api/v1/demo/test-run/request",
            json={"name": "Visitor", "email": "eu-race@example.com"},
        )
        assert r1.status_code == 200, r1.text
        token = captured["get_token"]()
        assert token is not None

        school_id = await _register_school(client, "Email In Use 3", "email-in-use-3@example.com")
        await _insert_real_student(client, school_id, "eu-race@example.com")

        r2 = await client.get(f"/api/v1/demo/test-run/verify/{token}")

    assert r2.status_code == 409, r2.text
    assert r2.json()["error"] == "email_in_use"
    assert captured["get_credentials"]() is None, "credentials must not reach an existing account"
