"""
tests/test_resend_enrolment_invite.py

School admins re-send the sign-up invite to a roster student who has no account yet
(status 'pending'). Active students and unknown emails are refused, and only
school_admin may send.
"""

from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest
from httpx import AsyncClient

from src.auth.tasks import send_enrolment_invite_email_task
from tests.helpers.token_factory import make_teacher_token

_PW = "SecureTestPwd1!"


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _register(client: AsyncClient, name: str, email: str) -> dict:
    r = await client.post(
        "/api/v1/schools/register",
        json={"school_name": name, "contact_email": email, "country": "CA", "password": _PW},
    )
    assert r.status_code == 201, r.text
    return r.json()


async def _roster(client: AsyncClient, school: dict, emails: list[str]) -> None:
    r = await client.post(
        f"/api/v1/schools/{school['school_id']}/enrolment",
        json={"students": [{"email": e} for e in emails]},
        headers=_auth(school["access_token"]),
    )
    assert r.status_code == 201, r.text


async def _active_student_on_roster(client: AsyncClient, email: str) -> None:
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await conn.execute(
            """
            INSERT INTO students
                (student_id, external_auth_id, name, email, grade, locale, account_status)
            VALUES ($1, $2, 'Has Account', $3, 8, 'en', 'active')
            """,
            uuid.uuid4(),
            f"auth0|ri-{uuid.uuid4().hex}",
            email,
        )


@pytest.mark.asyncio
async def test_pending_student_is_sent_the_invite(client: AsyncClient, db_conn) -> None:
    school = await _register(client, "Resend Invite 1", "resend-invite-1@example.com")
    await _roster(client, school, ["ri-pending@example.com"])

    with patch.object(send_enrolment_invite_email_task, "delay") as delay:
        r = await client.post(
            f"/api/v1/schools/{school['school_id']}/enrolment/resend-invite",
            json={"email": "ri-pending@example.com"},
            headers=_auth(school["access_token"]),
        )

    assert r.status_code == 200, r.text
    delay.assert_called_once_with("ri-pending@example.com", "Resend Invite 1")


@pytest.mark.asyncio
async def test_email_is_matched_case_insensitively(client: AsyncClient, db_conn) -> None:
    school = await _register(client, "Resend Invite 2", "resend-invite-2@example.com")
    await _roster(client, school, ["ri-case@example.com"])

    with patch.object(send_enrolment_invite_email_task, "delay") as delay:
        r = await client.post(
            f"/api/v1/schools/{school['school_id']}/enrolment/resend-invite",
            json={"email": "RI-Case@Example.com"},
            headers=_auth(school["access_token"]),
        )

    assert r.status_code == 200, r.text
    delay.assert_called_once_with("ri-case@example.com", "Resend Invite 2")


@pytest.mark.asyncio
async def test_active_student_is_refused_and_not_emailed(client: AsyncClient, db_conn) -> None:
    school = await _register(client, "Resend Invite 3", "resend-invite-3@example.com")
    await _active_student_on_roster(client, "ri-active@example.com")
    await _roster(client, school, ["ri-active@example.com"])

    with patch.object(send_enrolment_invite_email_task, "delay") as delay:
        r = await client.post(
            f"/api/v1/schools/{school['school_id']}/enrolment/resend-invite",
            json={"email": "ri-active@example.com"},
            headers=_auth(school["access_token"]),
        )

    assert r.status_code == 409, r.text
    assert r.json()["error"] == "not_pending"
    delay.assert_not_called()


@pytest.mark.asyncio
async def test_email_not_on_roster_is_404(client: AsyncClient, db_conn) -> None:
    school = await _register(client, "Resend Invite 4", "resend-invite-4@example.com")

    with patch.object(send_enrolment_invite_email_task, "delay") as delay:
        r = await client.post(
            f"/api/v1/schools/{school['school_id']}/enrolment/resend-invite",
            json={"email": "ri-nobody@example.com"},
            headers=_auth(school["access_token"]),
        )

    assert r.status_code == 404, r.text
    assert r.json()["error"] == "not_found"
    delay.assert_not_called()


@pytest.mark.asyncio
async def test_non_admin_teacher_is_403_and_not_emailed(client: AsyncClient, db_conn) -> None:
    school = await _register(client, "Resend Invite 5", "resend-invite-5@example.com")
    await _roster(client, school, ["ri-teacher-blocked@example.com"])
    teacher_token = make_teacher_token(
        teacher_id=str(uuid.uuid4()), school_id=school["school_id"], role="teacher"
    )

    with patch.object(send_enrolment_invite_email_task, "delay") as delay:
        r = await client.post(
            f"/api/v1/schools/{school['school_id']}/enrolment/resend-invite",
            json={"email": "ri-teacher-blocked@example.com"},
            headers=_auth(teacher_token),
        )

    assert r.status_code == 403, r.text
    delay.assert_not_called()
