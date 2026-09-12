"""
tests/test_one_email_one_role.py

"One email, one role" — migration 0072.

A tester reported that both of his student test accounts logged in as staff.
Each address existed as BOTH a `teachers` row and a `students` row;
`login_local_user` queries teachers first and falls through to students only
when nothing matched, so the student row was unreachable — no error, no hint,
just the wrong portal.

`teachers.email` and `students.email` have each been UNIQUE since 0001, so the
duplicate WITHIN a role was already impossible. The missing half was
cross-table: two constraints, neither aware of the other.

Enforced by a trigger rather than an application check because twelve code
paths insert a teacher or a student, and a guard in the provisioning endpoints
would have covered the school-admin UI while every other path — roster upload,
Auth0 exchange, the demo seeder, anything added later — opted out silently.

The two properties most worth pinning are the ones a narrower guard would have
got wrong:

  * case-insensitivity, because login matches case-SENSITIVELY, so a
    mixed-case variant would otherwise slip past and land in exactly the
    unreachable state the trigger exists to prevent;
  * deleted accounts NOT reserving an address, because deletion is soft
    (ADR-005 keeps the row with its email for FERPA retention) and a guard
    counting those rows would refuse an address permanently the first time an
    account holding it was deleted.
"""

from __future__ import annotations

import uuid

import asyncpg
import pytest
from httpx import AsyncClient


def _email() -> str:
    return f"oneole-{uuid.uuid4().hex[:10]}@example.com"


async def _school(client: AsyncClient) -> str:
    r = await client.post(
        "/api/v1/schools/register",
        json={
            "school_name": "One Role School",
            "contact_email": _email(),
            "country": "IN",
            "password": "SecureTestPwd1!",
        },
    )
    assert r.status_code == 201, r.text
    return r.json()["school_id"]


async def _insert_student(
    conn, school_id: str, email: str, status: str = "active", provider: str = "local"
) -> None:
    """`provider` is explicit and defaults to 'local' on purpose.

    The trigger only governs the local auth track. Leaving `auth_provider` to
    the column default silently put these fixtures on another track, the trigger
    correctly skipped them, and three tests reported DID NOT RAISE — a fixture
    that opted out of the very rule it was asserting.
    """
    await conn.execute(
        """
        INSERT INTO students
            (student_id, external_auth_id, email, name, grade, locale, school_id,
             account_status, auth_provider)
        VALUES ($1, $2, $3, 'S', 8, 'en', $4, $5, $6)
        """,
        uuid.uuid4(),
        f"{provider}|{uuid.uuid4().hex}",
        email,
        uuid.UUID(school_id),
        status,
        provider,
    )


async def _insert_teacher(conn, school_id: str, email: str, status: str = "active") -> None:
    await conn.execute(
        """
        INSERT INTO teachers
            (teacher_id, school_id, external_auth_id, auth_provider, name, email,
             role, account_status)
        VALUES ($1, $2, $3, 'local', 'T', $4, 'teacher', $5)
        """,
        uuid.uuid4(),
        uuid.UUID(school_id),
        f"local|{uuid.uuid4().hex}",
        email,
        status,
    )


# ── The rule, both directions ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_a_teacher_cannot_take_a_students_address(client, db_conn):
    school_id = await _school(client)
    email = _email()
    await db_conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
    await _insert_student(db_conn, school_id, email)

    with pytest.raises(asyncpg.UniqueViolationError) as exc:
        await _insert_teacher(db_conn, school_id, email)
    assert exc.value.constraint_name == "one_email_one_role"


@pytest.mark.asyncio
async def test_a_student_cannot_take_a_teachers_address(client, db_conn):
    """The other direction. A trigger on one table only would pass the test
    above and leave the reported defect reachable from the other side."""
    school_id = await _school(client)
    email = _email()
    await db_conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
    await _insert_teacher(db_conn, school_id, email)

    with pytest.raises(asyncpg.UniqueViolationError) as exc:
        await _insert_student(db_conn, school_id, email)
    assert exc.value.constraint_name == "one_email_one_role"


@pytest.mark.asyncio
async def test_the_check_ignores_case(client, db_conn):
    """Login matches case-sensitively (`WHERE email = $1`), so a mixed-case
    variant that slipped past would create precisely the unreachable account
    this trigger exists to prevent."""
    school_id = await _school(client)
    email = _email()
    await db_conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
    await _insert_student(db_conn, school_id, email)

    with pytest.raises(asyncpg.UniqueViolationError) as exc:
        await _insert_teacher(db_conn, school_id, email.upper())
    assert exc.value.constraint_name == "one_email_one_role"


# ── What the rule must NOT block ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_a_deleted_account_does_not_reserve_the_address(client, db_conn):
    """Deletion is soft (ADR-005): the row stays, with its email, for FERPA
    retention. Counting it would refuse the address forever — a guard
    condemning a legitimate case rather than the defect."""
    school_id = await _school(client)
    email = _email()
    await db_conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
    await _insert_student(db_conn, school_id, email, status="deleted")

    # Must not raise.
    await _insert_teacher(db_conn, school_id, email)

    live = await db_conn.fetchval(
        "SELECT count(*) FROM teachers WHERE lower(email) = lower($1)", email
    )
    assert live == 1


@pytest.mark.asyncio
async def test_a_demo_account_does_not_collide_with_a_local_one(client, db_conn):
    """The over-reach my first draft had, and the reason this test exists.

    The ambiguity is confined to the local login path: `login_local_user` looks
    a person up with `auth_provider='local'`, so a demo row can never shadow a
    local one through it. Blocking the pair would refuse a real flow — register
    a school, then try the student demo on the same address — which
    `/auth/universal-login` already resolves deliberately.

    The first trigger I wrote ignored auth_provider and broke
    `test_auth_universal_login.py::test_universal_login_local_precedence_over_demo`.
    """
    school_id = await _school(client)
    email = _email()
    await db_conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
    await _insert_teacher(db_conn, school_id, email)  # local

    # A DEMO student on the same address must be allowed.
    await _insert_student(db_conn, school_id, email, provider="demo")

    assert (
        await db_conn.fetchval(
            "SELECT count(*) FROM students WHERE lower(email) = lower($1)", email
        )
    ) == 1


@pytest.mark.asyncio
async def test_an_update_that_leaves_the_address_alone_is_not_checked(client, db_conn):
    """The trigger is `UPDATE OF email`, and returns early when the value has
    not changed — a password reset or grade change must not pay for a lookup it
    cannot invalidate, nor fail because of one."""
    school_id = await _school(client)
    email = _email()
    await db_conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
    await _insert_student(db_conn, school_id, email)

    await db_conn.execute("UPDATE students SET grade = 9 WHERE lower(email) = lower($1)", email)
    assert (
        await db_conn.fetchval("SELECT grade FROM students WHERE lower(email) = lower($1)", email)
    ) == 9


@pytest.mark.asyncio
async def test_renaming_to_a_free_address_still_works(client, db_conn):
    """The escape hatch actually used to unblock the reported accounts: moving
    the staff row to a `+suffix` address so the student login comes through."""
    school_id = await _school(client)
    email = _email()
    free = _email()
    await db_conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
    await _insert_teacher(db_conn, school_id, email)

    await db_conn.execute(
        "UPDATE teachers SET email = $1 WHERE lower(email) = lower($2)", free, email
    )
    assert (
        await db_conn.fetchval("SELECT count(*) FROM teachers WHERE email = $1", free)
    ) == 1


# ── The API surface: a 409 with a message that names the right role ──────────


@pytest.mark.asyncio
async def test_provisioning_a_student_over_a_teacher_is_a_409_not_a_500(client, db_conn):
    """The handlers re-raise any constraint they do not recognise, so without
    the trigger name mapped this surfaces as a 500."""
    from tests.helpers.token_factory import make_teacher_token

    school_id = await _school(client)
    email = _email()
    # Seeded through the APP POOL, not `db_conn`. The endpoint runs on its own
    # connection, and a row written on the test connection is not visible to it
    # — the first draft of this test seeded via `db_conn`, the trigger found no
    # clash, and provisioning returned 201.
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await _insert_teacher(conn, school_id, email)

    await db_conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
    admin_id = await db_conn.fetchval(
        "SELECT teacher_id::text FROM teachers WHERE school_id = $1 AND role = 'school_admin'"
        " LIMIT 1",
        uuid.UUID(school_id),
    )
    headers = {
        "Authorization": "Bearer "
        + make_teacher_token(teacher_id=admin_id, school_id=school_id, role="school_admin")
    }

    r = await client.post(
        f"/api/v1/schools/{school_id}/students",
        headers=headers,
        json={"name": "Clash", "email": email, "grade": 8},
    )
    assert r.status_code == 409, r.text
    body = r.json()
    assert body["error"] == "conflict", body
    # FastAPI flattens the HTTPException detail dict into the body, so the
    # human message is at `detail`, not `detail.detail`.
    detail = body["detail"]
    # Names the role that actually holds it. Reporting "already used by a
    # student" here would send the admin hunting through the wrong list.
    assert "teacher" in detail.lower(), detail
