"""
tests/test_additive_packages_651.py

A classroom's packages are ADDITIVE and DISTINCT (issue #651).

Product decision, 2026-08-28: *"There can be multiple packages to a classroom.
They need to be additive and distinct."*

Reported symptom: a Grade 11 student on the demo was served Grade 8 content
while two other packages sat unread. The diagnosis in #651 — "nothing validates
that a classroom's curriculum matches its grade" — turned out to be the wrong
frame. A Grade 11 classroom carrying Grade 5, 8 and 10 packages is legitimate;
what was wrong is that resolution collapsed them:

    JOIN classroom_packages cp ON cp.classroom_id = cl.classroom_id
    ORDER BY cl.created_at DESC
    LIMIT 1

Ordered by the CLASSROOM's creation date, then an arbitrary package among that
classroom's several. `classroom_packages.sort_order` existed the whole time and
was never read.

## What "distinct" already gives us

`classroom_packages` has PRIMARY KEY (classroom_id, curriculum_id), so a package
cannot be added twice. Nothing yet prevents two *different* packages from
containing the same unit — a separate guard at assignment time, and the reason
these tests pin the union rather than a sum of counts.

## Why the counters matter here

"Units done N/M" has been wrong twice already: #638 summed unrelated streams,
#650 counted a fork that holds no units. Making the numerator additive without
the denominator would break it a third way, so both are covered.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from tests.helpers.token_factory import make_student_token, make_teacher_token

_YEAR = 2026
_GRADE = 11


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _school(client: AsyncClient, suffix: str) -> dict:
    r = await client.post(
        "/api/v1/schools/register",
        json={
            "school_name": f"Additive School{suffix}",
            "contact_email": f"additive{suffix}@school.example.com",
            "country": "IN",
            "password": "SecureTestPwd1!",
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


async def _package(client: AsyncClient, units: list[str], *, grade: int) -> str:
    """A platform curriculum holding `units`, usable as a classroom package."""
    curriculum_id = f"pkg-{uuid.uuid4().hex[:8]}"
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await conn.execute(
            """
            INSERT INTO curricula (curriculum_id, name, grade, year, owner_type, is_default)
            VALUES ($1, 'Additive Package', $2, $3, 'platform', FALSE)
            """,
            curriculum_id,
            grade,
            _YEAR,
        )
        for i, unit_id in enumerate(units, start=1):
            await conn.execute(
                """
                INSERT INTO curriculum_units
                    (unit_id, curriculum_id, subject, title, unit_name, sort_order)
                VALUES ($1, $2, $3, $4, $4, $5)
                """,
                unit_id,
                curriculum_id,
                f"Subject {unit_id.split('-')[0]}",
                f"Title {unit_id}",
                i,
            )
    return curriculum_id


async def _classroom_with(
    client: AsyncClient, school_id: str, packages: list[str], *, grade: int = _GRADE
) -> str:
    classroom_id = str(uuid.uuid4())
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await conn.execute(
            """
            INSERT INTO classrooms (classroom_id, school_id, name, grade, status)
            VALUES ($1, $2, 'Additive Classroom', $3, 'active')
            """,
            uuid.UUID(classroom_id),
            uuid.UUID(school_id),
            grade,
        )
        for i, cid in enumerate(packages):
            await conn.execute(
                """
                INSERT INTO classroom_packages (classroom_id, curriculum_id, sort_order)
                VALUES ($1, $2, $3)
                """,
                uuid.UUID(classroom_id),
                cid,
                i,
            )
    return classroom_id


async def _student_in(client: AsyncClient, school_id: str, classroom_id: str) -> str:
    student_id = str(uuid.uuid4())
    email = f"add-{student_id[:8]}@example.com"
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await conn.execute(
            """
            INSERT INTO students
                (student_id, external_auth_id, name, email, grade, locale,
                 account_status, school_id)
            VALUES ($1, $2, 'Additive Student', $3, $4, 'en', 'active', $5)
            """,
            uuid.UUID(student_id),
            f"auth0|add-{student_id.replace('-', '')}",
            email,
            _GRADE,
            uuid.UUID(school_id),
        )
        await conn.execute(
            """
            INSERT INTO school_enrolments (school_id, student_email, student_id, status, grade)
            VALUES ($1, $2, $3, 'active', $4)
            """,
            uuid.UUID(school_id),
            email,
            uuid.UUID(student_id),
            _GRADE,
        )
        await conn.execute(
            "INSERT INTO classroom_students (classroom_id, student_id) VALUES ($1, $2)",
            uuid.UUID(classroom_id),
            uuid.UUID(student_id),
        )
    return student_id


# ── The resolver ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_every_package_is_resolved_not_just_one(client, db_conn):
    """The reported case: three packages, one served."""
    from src.content.service import resolve_curriculum_ids

    school = await _school(client, "_all")
    a = await _package(client, ["ADD-A1"], grade=5)
    b = await _package(client, ["ADD-B1"], grade=8)
    c = await _package(client, ["ADD-C1"], grade=11)
    classroom = await _classroom_with(client, school["school_id"], [a, b, c])
    student = await _student_in(client, school["school_id"], classroom)

    ids = await resolve_curriculum_ids(
        student,
        _GRADE,
        client._transport.app.state.pool,
        client._transport.app.state.redis,
        school_id=school["school_id"],
    )
    assert set(ids) == {a, b, c}, ids


@pytest.mark.asyncio
async def test_the_primary_is_the_first_by_sort_order(client, db_conn):
    """`resolve_curriculum_id` must be element [0], and stable.

    It used to order by the CLASSROOM's created_at and then take whichever
    package came back first — so the single-curriculum callers and the additive
    ones could disagree about which curriculum is primary.
    """
    from src.content.service import resolve_curriculum_id, resolve_curriculum_ids

    school = await _school(client, "_primary")
    first = await _package(client, ["ADD-P1"], grade=11)
    second = await _package(client, ["ADD-P2"], grade=8)
    classroom = await _classroom_with(client, school["school_id"], [first, second])
    student = await _student_in(client, school["school_id"], classroom)

    pool = client._transport.app.state.pool
    redis = client._transport.app.state.redis
    ids = await resolve_curriculum_ids(student, _GRADE, pool, redis, school_id=school["school_id"])
    one = await resolve_curriculum_id(student, _GRADE, pool, redis, school_id=school["school_id"])

    assert ids[0] == first, ids
    assert one == ids[0], (one, ids)


@pytest.mark.asyncio
async def test_a_single_package_is_unchanged(client, db_conn):
    """The common case must not move.

    Most classrooms carry one package; this is the regression guard for them.
    """
    from src.content.service import resolve_curriculum_ids

    school = await _school(client, "_single")
    only = await _package(client, ["ADD-S1", "ADD-S2"], grade=11)
    classroom = await _classroom_with(client, school["school_id"], [only])
    student = await _student_in(client, school["school_id"], classroom)

    ids = await resolve_curriculum_ids(
        student,
        _GRADE,
        client._transport.app.state.pool,
        client._transport.app.state.redis,
        school_id=school["school_id"],
    )
    assert ids == [only], ids


# ── What the student sees ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_the_curriculum_tree_unions_every_package(client, db_conn):
    """The tree is what the student browses — it must show all of it."""
    school = await _school(client, "_tree")
    a = await _package(client, ["TREE-A1", "TREE-A2"], grade=5)
    b = await _package(client, ["TREE-B1"], grade=11)
    classroom = await _classroom_with(client, school["school_id"], [a, b])
    student = await _student_in(client, school["school_id"], classroom)

    # The tree resolves packages from the JWT's school_id — real student tokens
    # carry it, so the test must too or step 2 is skipped and the default
    # curriculum answers instead.
    token = make_student_token(
        student_id=student, grade=_GRADE, school_id=school["school_id"]
    )
    r = await client.get("/api/v1/curriculum/tree", headers=_auth(token))
    assert r.status_code == 200, r.text

    unit_ids = {u["unit_id"] for s in r.json()["subjects"] for u in s["units"]}
    assert {"TREE-A1", "TREE-A2", "TREE-B1"} <= unit_ids, unit_ids


@pytest.mark.asyncio
async def test_the_dashboard_counts_units_from_every_package(client, db_conn):
    """"Units done N/M" — M is the union, or the fraction lies again (#638/#650)."""
    school = await _school(client, "_dash")
    a = await _package(client, ["DASH-A1", "DASH-A2"], grade=5)
    b = await _package(client, ["DASH-B1"], grade=11)
    classroom = await _classroom_with(client, school["school_id"], [a, b])
    student = await _student_in(client, school["school_id"], classroom)

    token = make_student_token(student_id=student, grade=_GRADE)
    r = await client.get("/api/v1/student/dashboard", headers=_auth(token))
    assert r.status_code == 200, r.text

    total = sum(s["units_total"] for s in r.json()["subject_progress"])
    assert total == 3, r.json()["subject_progress"]


@pytest.mark.asyncio
async def test_the_teacher_denominator_sums_every_package(client, db_conn):
    """The roster's "N/M" has to agree with the student's own screen."""
    school = await _school(client, "_roster")
    a = await _package(client, ["ROST-A1", "ROST-A2"], grade=5)
    b = await _package(client, ["ROST-B1"], grade=11)
    classroom = await _classroom_with(client, school["school_id"], [a, b])
    await _student_in(client, school["school_id"], classroom)

    token = make_teacher_token(
        teacher_id=school["teacher_id"], school_id=school["school_id"], role="school_admin"
    )
    r = await client.get(
        f"/api/v1/reports/school/{school['school_id']}/roster", headers=_auth(token)
    )
    assert r.status_code == 200, r.text
    assert r.json()["students"][0]["total_units"] == 3, r.json()["students"][0]


# ── Serving a unit that lives in a NON-primary package ────────────────────────


@pytest.mark.asyncio
async def test_a_unit_from_a_later_package_resolves(client, db_conn):
    """Stage 2: the tree lists every package, so serving must find every package.

    Serving used the PRIMARY curriculum, so a unit belonging to the second or
    third package resolved nowhere and 404'd — a unit the curriculum tree had
    just shown the student.
    """
    from src.content.service import resolve_unit_curriculum

    school = await _school(client, "_serve")
    first = await _package(client, ["SERVE-P1"], grade=11)
    second = await _package(client, ["SERVE-P2"], grade=8)
    classroom = await _classroom_with(client, school["school_id"], [first, second])
    await _student_in(client, school["school_id"], classroom)

    pool = client._transport.app.state.pool
    resolved, subject = await resolve_unit_curriculum(
        "SERVE-P2", [first, second], school["school_id"], pool
    )
    assert resolved == second, resolved
    assert subject is not None


@pytest.mark.asyncio
async def test_the_primary_still_wins_for_its_own_units(client, db_conn):
    """Order matters: a unit in the primary must not be looked up elsewhere."""
    from src.content.service import resolve_unit_curriculum

    school = await _school(client, "_serve_primary")
    first = await _package(client, ["SERVE-Q1"], grade=11)
    second = await _package(client, ["SERVE-Q2"], grade=8)
    classroom = await _classroom_with(client, school["school_id"], [first, second])
    await _student_in(client, school["school_id"], classroom)

    resolved, subject = await resolve_unit_curriculum(
        "SERVE-Q1", [first, second], school["school_id"], client._transport.app.state.pool
    )
    assert resolved == first, resolved
    assert subject is not None


@pytest.mark.asyncio
async def test_a_unit_in_no_package_still_reports_not_found(client, db_conn):
    """The 404 signal must survive: subject None is how callers raise it."""
    from src.content.service import resolve_unit_curriculum

    school = await _school(client, "_serve_missing")
    only = await _package(client, ["SERVE-R1"], grade=11)
    classroom = await _classroom_with(client, school["school_id"], [only])
    await _student_in(client, school["school_id"], classroom)

    resolved, subject = await resolve_unit_curriculum(
        "SERVE-NOPE", [only], school["school_id"], client._transport.app.state.pool
    )
    assert subject is None, (resolved, subject)


@pytest.mark.asyncio
async def test_a_session_records_the_package_that_holds_the_unit(client, db_conn):
    """Grading reads the session's curriculum_id, so it must be the serving one.

    start_session used to call resolve_curriculum_id and stop — a documented
    drift (#529) that additive packages turn from latent into routine, since
    with three packages the primary is simply not where most units live.
    """
    school = await _school(client, "_session")
    first = await _package(client, ["SESS-P1"], grade=11)
    second = await _package(client, ["SESS-P2"], grade=8)
    classroom = await _classroom_with(client, school["school_id"], [first, second])
    student = await _student_in(client, school["school_id"], classroom)

    token = make_student_token(
        student_id=student, grade=_GRADE, school_id=school["school_id"]
    )
    r = await client.post(
        "/api/v1/progress/session",
        json={"unit_id": "SESS-P2", "curriculum_id": "ignored-by-the-server"},
        headers=_auth(token),
    )
    assert r.status_code == 201, r.text

    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        recorded = await conn.fetchval(
            "SELECT curriculum_id FROM progress_sessions WHERE session_id = $1",
            uuid.UUID(r.json()["session_id"]),
        )
    assert recorded == second, recorded


# ── Stage 3: distinct by UNIT, not just by package ────────────────────────────


async def _assign(client: AsyncClient, school: dict, classroom_id: str, curriculum_id: str):
    token = make_teacher_token(
        teacher_id=school["teacher_id"], school_id=school["school_id"], role="school_admin"
    )
    return await client.post(
        f"/api/v1/schools/{school['school_id']}/classrooms/{classroom_id}/packages",
        json={"curriculum_id": curriculum_id, "sort_order": 0},
        headers=_auth(token),
    )


@pytest.mark.asyncio
async def test_a_package_sharing_a_unit_is_refused(client, db_conn):
    """Overlap would make resolution a coin-toss the school never sees.

    `resolve_unit_curriculum` returns the FIRST package holding the unit, so an
    overlapping second package's version silently becomes unreachable. Refusing
    at assignment keeps the ambiguity where someone can act on it.
    """
    school = await _school(client, "_overlap")
    first = await _package(client, ["OVER-1", "OVER-2"], grade=11)
    clashing = await _package(client, ["OVER-2", "OVER-3"], grade=8)
    classroom = await _classroom_with(client, school["school_id"], [])

    assert (await _assign(client, school, classroom, first)).status_code == 204
    r = await _assign(client, school, classroom, clashing)

    assert r.status_code == 409, r.text
    body = r.json()
    assert body["error"] == "overlapping_package", body
    # Names the colliding unit — "conflict" alone leaves nobody able to act.
    assert body["units"] == ["OVER-2"], body


@pytest.mark.asyncio
async def test_packages_that_do_not_overlap_are_accepted(client, db_conn):
    """Additive is the point — distinctness must not block the normal case."""
    school = await _school(client, "_no_overlap")
    a = await _package(client, ["FINE-1"], grade=11)
    b = await _package(client, ["FINE-2"], grade=8)
    classroom = await _classroom_with(client, school["school_id"], [])

    assert (await _assign(client, school, classroom, a)).status_code == 204
    assert (await _assign(client, school, classroom, b)).status_code == 204


@pytest.mark.asyncio
async def test_reassigning_the_same_package_is_still_idempotent(client, db_conn):
    """The endpoint is documented as safe to call twice.

    A naive overlap check compares the incoming package against every row
    including itself, which would turn every re-assign into a conflict.
    """
    school = await _school(client, "_idempotent")
    only = await _package(client, ["SAME-1"], grade=11)
    classroom = await _classroom_with(client, school["school_id"], [])

    assert (await _assign(client, school, classroom, only)).status_code == 204
    assert (await _assign(client, school, classroom, only)).status_code == 204
