"""
tests/test_feedback_stream_filter_771.py

Grade / Stream on the Feedback report (Venki, 14 Sep — #771):

    "1. Option to view report based on Grade/Steam selection
     2. If showing all grades, group by Grade/Steam for better organization"

Two halves, and the second is why the items carry `grade` / `streams` rather
than the client being told to infer them.

The interesting decision here is the SUMMARY. `get_feedback_report` documents,
deliberately, that its header counts ignore the filters — "the header describes
the school, not whatever the current filters happen to show". That is right for
`unit_id` / `category` / `reviewed`, which are CONTENT filters: they choose which
of this school's feedback to look at.

Grade and stream are not that. They are COHORT filters — they change WHOSE
feedback is in scope — and a header reading "120 items" above a table showing one
grade's twelve is the same "two halves of the page disagree" failure the grade
filter on Unit Performance was pinned against. So the cohort filters move the
summary and the content filters still do not, and both rules are tested below.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from src.reports.service import UNSTREAMED, get_feedback_report


async def _school(client: AsyncClient) -> str:
    r = await client.post(
        "/api/v1/schools/register",
        json={
            "school_name": "Feedback Stream School",
            "contact_email": f"fbs{uuid.uuid4().hex[:8]}@school.example.com",
            "country": "IN",
            "password": "SecureTestPwd1!",
        },
    )
    assert r.status_code == 201, r.text
    return r.json()["school_id"]


async def _curriculum(client: AsyncClient, grade: int, unit_id: str, stream_code: str | None) -> str:
    cid = f"fb-{uuid.uuid4().hex[:8]}"
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await conn.execute(
            """
            INSERT INTO curricula
                (curriculum_id, name, grade, year, owner_type, is_default, stream_code)
            VALUES ($1, 'FB Curriculum', $2, 2026, 'platform', FALSE, $3)
            """,
            cid,
            grade,
            stream_code,
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


async def _student_with_feedback(
    client: AsyncClient, school_id: str, grade: int, cid: str, unit_id: str, message: str
) -> str:
    student_id = str(uuid.uuid4())
    email = f"fb-{student_id[:8]}@example.com"
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await conn.execute(
            """
            INSERT INTO students
                (student_id, external_auth_id, email, name, grade, locale, school_id)
            VALUES ($1, $2, $3, 'FB Student', $4, 'en', $5)
            """,
            uuid.UUID(student_id),
            f"auth0|fb-{student_id.replace('-', '')}",
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
            "INSERT INTO classrooms (school_id, name, grade) VALUES ($1, $2, $3)"
            " RETURNING classroom_id",
            uuid.UUID(school_id),
            f"FB Room {student_id[:6]}",
            grade,
        )
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
        await conn.execute(
            """
            INSERT INTO feedback (student_id, unit_id, category, rating, message, reviewed)
            VALUES ($1, $2, 'content', 3, $3, FALSE)
            """,
            uuid.UUID(student_id),
            unit_id,
            message,
        )
    return student_id


async def _two_stream_school(client) -> str:
    school_id = await _school(client)
    com = await _curriculum(client, 11, "FB-COM-001", "commerce")
    sci = await _curriculum(client, 12, "FB-SCI-001", "science")
    await _student_with_feedback(client, school_id, 11, com, "FB-COM-001", "commerce note")
    await _student_with_feedback(client, school_id, 12, sci, "FB-SCI-001", "science note")
    return school_id


def _messages(report: dict) -> set[str]:
    return {i["message"] for i in report["items"]}


# ── Half 1: the filter ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_unfiltered_shows_every_stream(client, db_conn, fake_redis):
    school_id = await _two_stream_school(client)
    pool = client._transport.app.state.pool

    report = await get_feedback_report(db_conn, school_id, pool=pool, redis=fake_redis)

    assert _messages(report) == {"commerce note", "science note"}
    assert report["selected_stream"] is None
    assert report["selected_grade"] is None


@pytest.mark.asyncio
async def test_filtering_by_stream_narrows_the_items(client, db_conn, fake_redis):
    school_id = await _two_stream_school(client)
    pool = client._transport.app.state.pool

    report = await get_feedback_report(
        db_conn, school_id, pool=pool, redis=fake_redis, stream="commerce"
    )

    assert _messages(report) == {"commerce note"}
    assert report["selected_stream"] == "commerce"


@pytest.mark.asyncio
async def test_filtering_by_grade_narrows_the_items(client, db_conn, fake_redis):
    school_id = await _two_stream_school(client)
    pool = client._transport.app.state.pool

    report = await get_feedback_report(db_conn, school_id, pool=pool, redis=fake_redis, grade=11)

    assert _messages(report) == {"commerce note"}
    assert report["selected_grade"] == 11


# ── The summary follows a COHORT filter, not a CONTENT one ────────────────────


@pytest.mark.asyncio
async def test_a_cohort_filter_moves_the_header_counts(client, db_conn, fake_redis):
    """Otherwise "2 items" sits above a table showing 1, and the reader cannot
    tell which half is wrong."""
    school_id = await _two_stream_school(client)
    pool = client._transport.app.state.pool

    everything = await get_feedback_report(db_conn, school_id, pool=pool, redis=fake_redis)
    just_com = await get_feedback_report(
        db_conn, school_id, pool=pool, redis=fake_redis, stream="commerce"
    )

    assert everything["total_feedback_count"] == 2
    assert just_com["total_feedback_count"] == 1
    assert just_com["total_feedback_count"] == len(just_com["items"])


@pytest.mark.asyncio
async def test_a_content_filter_still_leaves_the_header_alone(client, db_conn, fake_redis):
    """The documented pre-existing behaviour, pinned so the #771 change does not
    quietly redefine it: `reviewed` chooses WHICH of the school's feedback to
    show, not whose."""
    school_id = await _two_stream_school(client)
    pool = client._transport.app.state.pool

    filtered = await get_feedback_report(
        db_conn, school_id, pool=pool, redis=fake_redis, reviewed=True
    )

    assert filtered["items"] == [], "nothing is reviewed yet"
    assert filtered["total_feedback_count"] == 2, "the header still describes the school"
    assert filtered["pagination"]["total"] == 0, "pagination follows the content filter"


# ── Half 2: grouping ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_every_item_carries_its_grade_and_streams(client, db_conn, fake_redis):
    """"If showing all grades, group by Grade/Steam" — the client cannot group
    by an attribute the rows do not carry, and a second request per row to find
    out would be worse."""
    school_id = await _two_stream_school(client)
    pool = client._transport.app.state.pool

    report = await get_feedback_report(db_conn, school_id, pool=pool, redis=fake_redis)
    by_message = {i["message"]: i for i in report["items"]}

    assert by_message["commerce note"]["grade"] == 11
    assert by_message["commerce note"]["streams"] == ["commerce"]
    assert by_message["science note"]["grade"] == 12
    assert by_message["science note"]["streams"] == ["science"]


@pytest.mark.asyncio
async def test_the_student_id_is_not_exposed(client, db_conn, fake_redis):
    """A named student attached to a complaint is an educational record, and
    this report has no reason to carry one (FERPA). The grouping attributes are
    derived from it server-side and it does not travel."""
    school_id = await _two_stream_school(client)
    pool = client._transport.app.state.pool

    report = await get_feedback_report(db_conn, school_id, pool=pool, redis=fake_redis)

    for item in report["items"]:
        assert "student_id" not in item
        assert "_sid" not in item, "the internal join column must not leak either"


# ── The picker ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_selecting_does_not_shrink_either_picker(client, db_conn, fake_redis):
    school_id = await _two_stream_school(client)
    pool = client._transport.app.state.pool

    filtered = await get_feedback_report(
        db_conn, school_id, pool=pool, redis=fake_redis, stream="commerce"
    )

    assert filtered["available_streams"] == ["commerce", "science"]
    assert filtered["available_grades"] == [11, 12]


@pytest.mark.asyncio
async def test_an_empty_selection_still_reports_the_way_back(client, db_conn, fake_redis):
    """The early return must carry the pickers, or a selection matching nobody
    is a dead end needing a page reload to escape."""
    school_id = await _two_stream_school(client)
    pool = client._transport.app.state.pool

    report = await get_feedback_report(
        db_conn, school_id, pool=pool, redis=fake_redis, stream=UNSTREAMED
    )

    assert report["items"] == []
    assert report["available_streams"] == ["commerce", "science"]
    assert report["available_grades"] == [11, 12]
    assert report["selected_stream"] == UNSTREAMED
