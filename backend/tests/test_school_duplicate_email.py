"""
tests/test_school_duplicate_email.py

Provisioning a person whose email is already taken (issue #572).

Venki hit this twice. `students.email` and `teachers.email` are globally unique,
so an address registered at ANY school blocks it everywhere — and the API said
only "A student with that email already exists." That tells a school admin
nothing: not that the address is in use elsewhere, not that they cannot see
where, and not what to do about it. From their side it is a dead end.

The message must do two different jobs depending on where the clash is:

  - already on THIS school's roster  -> say so plainly; the admin can act alone
  - registered somewhere else        -> say the address is taken platform-wide
                                        and give a route forward, WITHOUT naming
                                        the other school (that is another
                                        school's data)
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from tests.helpers.token_factory import make_teacher_token


async def _register_school(client: AsyncClient, suffix: str) -> dict:
    r = await client.post(
        "/api/v1/schools/register",
        json={
            "school_name": f"Dup Email School{suffix}",
            "contact_email": f"dupmail{suffix}@school.example.com",
            "country": "ZA",
            "password": "SecureTestPwd1!",
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


def _headers(reg: dict) -> dict:
    token = make_teacher_token(
        teacher_id=reg["teacher_id"], school_id=reg["school_id"], role="school_admin"
    )
    return {"Authorization": f"Bearer {token}"}


async def _add_student(client: AsyncClient, reg: dict, email: str, name: str = "Sam") -> object:
    return await client.post(
        f"/api/v1/schools/{reg['school_id']}/students",
        json={"name": name, "email": email, "grade": 8},
        headers=_headers(reg),
    )


@pytest.mark.asyncio
async def test_duplicate_within_the_same_school_says_so(client, db_conn):
    """A clash the admin CAN see should be named plainly."""
    reg = await _register_school(client, "_same")
    email = f"dup-same-{uuid.uuid4().hex[:8]}@example.com"

    first = await _add_student(client, reg, email)
    assert first.status_code in (200, 201), first.text

    second = await _add_student(client, reg, email)
    assert second.status_code == 409, second.text
    detail = second.json()["detail"].lower()
    assert "already" in detail
    # The admin owns this roster, so tell them it is theirs rather than being coy.
    assert "school" in detail or "roster" in detail


@pytest.mark.asyncio
async def test_a_student_at_another_school_is_now_attached_not_refused(client, db_conn):
    """This case is no longer a conflict at all (#572).

    It used to 409 with a message explaining the address was registered
    platform-wide — that was the best available answer while a student could
    belong to only one school. The product decision of 2026-08-24 changed the
    underlying rule: a student may attend a school AND, say, an external tutor
    running additional classes, so the second school now ATTACHES the existing
    person rather than being refused.

    The explanatory message is still live and still tested — see
    `test_duplicate_teacher_email_gets_the_same_treatment` below. Teachers keep
    the old rule: `teachers.school_id` is a single column, so a teacher belongs
    to one school and a duplicate address there is still a genuine conflict.

    Full coverage of the attach behaviour lives in
    tests/test_multi_school_enrolment_572.py.
    """
    other = await _register_school(client, "_other")
    mine = await _register_school(client, "_mine")
    email = f"dup-cross-{uuid.uuid4().hex[:8]}@example.com"

    first = await _add_student(client, other, email)
    assert first.status_code in (200, 201), first.text

    second = await _add_student(client, mine, email)
    assert second.status_code in (200, 201), second.text


@pytest.mark.asyncio
async def test_duplicate_teacher_email_gets_the_same_treatment(client, db_conn):
    """Teachers hit the identical constraint, so they get the identical help."""
    other = await _register_school(client, "_tother")
    mine = await _register_school(client, "_tmine")
    email = f"dup-teacher-{uuid.uuid4().hex[:8]}@example.com"

    first = await client.post(
        f"/api/v1/schools/{other['school_id']}/teachers",
        json={"name": "Existing Teacher", "email": email},
        headers=_headers(other),
    )
    assert first.status_code in (200, 201), first.text

    blocked = await client.post(
        f"/api/v1/schools/{mine['school_id']}/teachers",
        json={"name": "New Teacher", "email": email},
        headers=_headers(mine),
    )
    assert blocked.status_code == 409, blocked.text
    detail = blocked.json()["detail"].lower()
    assert "already registered" in detail, detail
    assert "support@usestudybuddy.com" in detail, detail


@pytest.mark.asyncio
async def test_a_teacher_address_does_not_block_a_student(client, db_conn):
    """Documents the real behaviour, which surprised me while writing this.

    students.email and teachers.email are SEPARATE unique constraints with no
    cross-table check, so the same address can be both a teacher and a student.
    That is #578, and it is why the duplicate message must never guess which
    kind of record it collided with — the constraint name is the only thing
    that actually knows.
    """
    reg = await _register_school(client, "_mixed")
    email = f"dup-mixed-{uuid.uuid4().hex[:8]}@example.com"

    teacher = await client.post(
        f"/api/v1/schools/{reg['school_id']}/teachers",
        json={"name": "A Teacher", "email": email},
        headers=_headers(reg),
    )
    assert teacher.status_code in (200, 201), teacher.text

    # Not blocked — the address now belongs to two different people.
    student = await _add_student(client, reg, email)
    assert student.status_code in (200, 201), student.text
