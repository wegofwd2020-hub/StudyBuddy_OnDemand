"""
tests/test_reports_stream_filter_774.py

Filtering a report by STREAM (Venki, 14 Sep — #774, and the same axis asked for
by #771, #772, #773, #776).

    "Add filter dropdown to select: Grade / Stream (STEM/Commerce/Humanities)"

The grade half of #774 already shipped (#733). The stream half could not,
because nothing recorded a stream to filter on:

  - `students.stream` exists (migration 0044) and nothing has ever written it.
  - `curricula.stream_code` exists (same migration) and was NULL for every
    platform curriculum — `seed_default_curriculum` never set it, so all five
    rows of the 0045 registry reported `curricula_count = 0`.

So a student's stream is derived the only way that reflects what they are
actually taught: from the curricula they RESOLVE to, through
`resolve_curriculum_ids` — the same resolver that decides which content they are
served. Re-deriving it with a simpler query is pitfall #31, which is how
`get_curriculum_tree` once served stream students another stream's subjects.

Three properties this pins, each of which has already gone wrong once on the
grade axis:

  1. A set, not a value. Classroom packages are ADDITIVE (#651), so a student
     can be in two streams and must appear in both reports.
  2. `unstreamed` is a real bucket. School-owned curricula have no stream and
     never will; dropping those students would manufacture the coverage gap
     #774's own grade filter was built to avoid.
  3. The picker reports the PERMISSION scope, never the filtered result —
     otherwise choosing Commerce leaves Commerce as the only option and there
     is no way back.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from src.reports.service import UNSTREAMED, get_curriculum_health


async def _school(client: AsyncClient) -> str:
    r = await client.post(
        "/api/v1/schools/register",
        json={
            "school_name": "Stream Filter School",
            "contact_email": f"stream{uuid.uuid4().hex[:8]}@school.example.com",
            "country": "IN",
            "password": "SecureTestPwd1!",
        },
    )
    assert r.status_code == 201, r.text
    return r.json()["school_id"]


async def _curriculum(
    client: AsyncClient,
    grade: int,
    unit_id: str,
    stream_code: str | None,
    source_curriculum_id: str | None = None,
) -> str:
    cid = f"st-{uuid.uuid4().hex[:8]}"
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await conn.execute(
            """
            INSERT INTO curricula
                (curriculum_id, name, grade, year, owner_type, is_default,
                 stream_code, source_curriculum_id)
            VALUES ($1, 'Stream Curriculum', $2, 2026, 'platform', FALSE, $3, $4)
            """,
            cid,
            grade,
            stream_code,
            source_curriculum_id,
        )
        await conn.execute(
            """
            INSERT INTO curriculum_units
                (unit_id, curriculum_id, subject, title, unit_name, sort_order)
            VALUES ($1, $2, $3, $4, $4, 0)
            """,
            unit_id,
            cid,
            f"G{grade}-SUB",
            f"Unit {unit_id}",
        )
    return cid


async def _student_on(client: AsyncClient, school_id: str, grade: int, cids: list[str]) -> str:
    """A student routed to `cids` through classroom packages — the real path."""
    student_id = str(uuid.uuid4())
    email = f"st-{student_id[:8]}@example.com"
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await conn.execute(
            """
            INSERT INTO students
                (student_id, external_auth_id, email, name, grade, locale, school_id)
            VALUES ($1, $2, $3, 'Stream Student', $4, 'en', $5)
            """,
            uuid.UUID(student_id),
            f"auth0|st-{student_id.replace('-', '')}",
            email,
            grade,
            uuid.UUID(school_id),
        )
        await conn.execute(
            """
            INSERT INTO school_enrolments
                (school_id, student_id, student_email, grade, status)
            VALUES ($1, $2, $3, $4, 'active')
            """,
            uuid.UUID(school_id),
            uuid.UUID(student_id),
            email,
            grade,
        )
        classroom_id = await conn.fetchval(
            """
            INSERT INTO classrooms (school_id, name, grade)
            VALUES ($1, $2, $3) RETURNING classroom_id
            """,
            uuid.UUID(school_id),
            f"Room {student_id[:6]}",
            grade,
        )
        for cid in cids:
            await conn.execute(
                "INSERT INTO classroom_packages (classroom_id, curriculum_id) VALUES ($1, $2)",
                classroom_id,
                cid,
            )
        await conn.execute(
            "INSERT INTO classroom_students (classroom_id, student_id) VALUES ($1, $2)",
            classroom_id,
            uuid.UUID(student_id),
        )
    return student_id


async def _activity(client, student_id: str, unit_id: str, cid: str, grade: int) -> None:
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await conn.execute(
            """
            INSERT INTO progress_sessions
                (student_id, unit_id, curriculum_id, grade, subject,
                 attempt_number, completed, passed, score, total_questions)
            VALUES ($1, $2, $3, $4, $5, 1, TRUE, TRUE, 7, 8)
            """,
            uuid.UUID(student_id),
            unit_id,
            cid,
            grade,
            f"G{grade}-SUB",
        )


def _ids(report: dict) -> set[str]:
    return {u["unit_id"] for u in report["units"]}


async def _two_stream_school(client) -> tuple[str, str, str]:
    """One Commerce student and one Science student, both Grade 11."""
    school_id = await _school(client)
    com = await _curriculum(client, 11, "ST-COM-001", "commerce")
    sci = await _curriculum(client, 11, "ST-SCI-001", "science")
    s_com = await _student_on(client, school_id, 11, [com])
    s_sci = await _student_on(client, school_id, 11, [sci])
    await _activity(client, s_com, "ST-COM-001", com, 11)
    await _activity(client, s_sci, "ST-SCI-001", sci, 11)
    return school_id, "ST-COM-001", "ST-SCI-001"


# ── The filter itself ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_no_stream_filter_covers_every_stream(client, db_conn, fake_redis):
    """Adding the parameter must not narrow the unfiltered report."""
    school_id, com_unit, sci_unit = await _two_stream_school(client)
    pool = client._transport.app.state.pool

    report = await get_curriculum_health(db_conn, school_id, pool=pool, redis=fake_redis)

    assert {com_unit, sci_unit} <= _ids(report)
    assert report["selected_stream"] is None


@pytest.mark.asyncio
async def test_selecting_a_stream_drops_the_other_streams_units(client, db_conn, fake_redis):
    school_id, com_unit, sci_unit = await _two_stream_school(client)
    pool = client._transport.app.state.pool

    report = await get_curriculum_health(
        db_conn, school_id, pool=pool, redis=fake_redis, stream="commerce"
    )

    assert com_unit in _ids(report)
    assert sci_unit not in _ids(report), "a Science unit has no place in a Commerce report"
    assert report["selected_stream"] == "commerce"


@pytest.mark.asyncio
async def test_the_counts_describe_the_filtered_set(client, db_conn, fake_redis):
    """Headline counts and the table below them must agree — the exact failure
    the grade filter was pinned against in test_venki_0902_grade_filter."""
    school_id, _, _ = await _two_stream_school(client)
    pool = client._transport.app.state.pool

    everything = await get_curriculum_health(db_conn, school_id, pool=pool, redis=fake_redis)
    just_com = await get_curriculum_health(
        db_conn, school_id, pool=pool, redis=fake_redis, stream="commerce"
    )

    assert just_com["total_units"] == len(just_com["units"])
    assert just_com["total_units"] < everything["total_units"]


# ── The picker ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_selecting_a_stream_does_not_shrink_the_picker(client, db_conn, fake_redis):
    school_id, _, _ = await _two_stream_school(client)
    pool = client._transport.app.state.pool

    unfiltered = await get_curriculum_health(db_conn, school_id, pool=pool, redis=fake_redis)
    filtered = await get_curriculum_health(
        db_conn, school_id, pool=pool, redis=fake_redis, stream="commerce"
    )

    assert unfiltered["available_streams"] == ["commerce", "science"]
    assert filtered["available_streams"] == ["commerce", "science"], "the way back must survive"


@pytest.mark.asyncio
async def test_filtering_by_grade_does_not_shrink_the_stream_picker(client, db_conn, fake_redis):
    """The two filters are independent axes. Narrowing to Grade 11 must not
    remove Commerce from the stream options, or the controls fight each other."""
    school_id = await _school(client)
    com11 = await _curriculum(client, 11, "ST-G11-COM", "commerce")
    sci12 = await _curriculum(client, 12, "ST-G12-SCI", "science")
    s11 = await _student_on(client, school_id, 11, [com11])
    s12 = await _student_on(client, school_id, 12, [sci12])
    await _activity(client, s11, "ST-G11-COM", com11, 11)
    await _activity(client, s12, "ST-G12-SCI", sci12, 12)
    pool = client._transport.app.state.pool

    report = await get_curriculum_health(
        db_conn, school_id, pool=pool, redis=fake_redis, grade=11
    )

    assert report["selected_grade"] == 11
    assert report["available_streams"] == ["commerce", "science"], (
        "stream options come from the permission scope, not the grade selection"
    )


# ── Additive packages: a student can be in two streams ────────────────────────


@pytest.mark.asyncio
async def test_a_student_in_two_streams_appears_in_both(client, db_conn, fake_redis):
    """Classroom packages are additive (#651). Collapsing a student to one
    stream would silently drop them from the other report."""
    school_id = await _school(client)
    com = await _curriculum(client, 11, "ST-BOTH-COM", "commerce")
    sci = await _curriculum(client, 11, "ST-BOTH-SCI", "science")
    both = await _student_on(client, school_id, 11, [com, sci])
    await _activity(client, both, "ST-BOTH-COM", com, 11)
    await _activity(client, both, "ST-BOTH-SCI", sci, 11)
    pool = client._transport.app.state.pool

    as_com = await get_curriculum_health(
        db_conn, school_id, pool=pool, redis=fake_redis, stream="commerce"
    )
    as_sci = await get_curriculum_health(
        db_conn, school_id, pool=pool, redis=fake_redis, stream="science"
    )

    assert "ST-BOTH-COM" in _ids(as_com)
    assert "ST-BOTH-SCI" in _ids(as_sci)


# ── `unstreamed` is a bucket, not a gap ───────────────────────────────────────


@pytest.mark.asyncio
async def test_a_student_with_no_stream_is_offered_as_unstreamed(client, db_conn, fake_redis):
    """School-owned content carries no stream_code and never will. Those
    students must be reachable, not invisible."""
    school_id = await _school(client)
    plain = await _curriculum(client, 11, "ST-PLAIN-001", None)
    s = await _student_on(client, school_id, 11, [plain])
    await _activity(client, s, "ST-PLAIN-001", plain, 11)
    pool = client._transport.app.state.pool

    report = await get_curriculum_health(db_conn, school_id, pool=pool, redis=fake_redis)
    assert UNSTREAMED in report["available_streams"]

    only = await get_curriculum_health(
        db_conn, school_id, pool=pool, redis=fake_redis, stream=UNSTREAMED
    )
    assert "ST-PLAIN-001" in _ids(only)


@pytest.mark.asyncio
async def test_a_fork_inherits_its_source_stream(client, db_conn, fake_redis):
    """A school FORK holds no stream_code of its own — its identity lives under
    `source_curriculum_id` (#650). Without the fallback every forked Commerce
    class would read as unstreamed."""
    school_id = await _school(client)
    source = await _curriculum(client, 11, "ST-SRC-001", "commerce")
    fork = await _curriculum(client, 11, "ST-FORK-001", None, source_curriculum_id=source)
    s = await _student_on(client, school_id, 11, [fork])
    await _activity(client, s, "ST-FORK-001", fork, 11)
    pool = client._transport.app.state.pool

    report = await get_curriculum_health(
        db_conn, school_id, pool=pool, redis=fake_redis, stream="commerce"
    )

    assert "ST-FORK-001" in _ids(report)
    assert UNSTREAMED not in report["available_streams"]


@pytest.mark.asyncio
async def test_an_unknown_stream_returns_empty_rather_than_everything(client, db_conn, fake_redis):
    """The negative case. A filter that silently falls back to "no filter" is
    worse than one that returns nothing: the reader believes they are looking
    at one stream while seeing the whole school."""
    school_id, _, _ = await _two_stream_school(client)
    pool = client._transport.app.state.pool

    report = await get_curriculum_health(
        db_conn, school_id, pool=pool, redis=fake_redis, stream="no-such-stream"
    )

    assert report["units"] == []
    assert report["total_units"] == 0
    assert report["available_streams"] == ["commerce", "science"], "the way back survives"
