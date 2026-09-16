"""
tests/test_earlier_curriculum_activity_758.py

Activity from a curriculum the student is no longer served (Venki, 14 Sep — #758):

    "For commerce stream students, unit progress is showing all subjects instead
     of only commerce-related subjects ... Engineering, Mathematics & Technology."

The rows were real. On the demo, the Grade 11 student had been served G11 STEM
and then G5 STEM before the classroom was moved onto Commerce, and both the
teacher's "Unit progress" table and the student's Subject Breakdown are built
from ACTIVITY — so they list everything ever touched, with nothing to tell
"working on" from "worked on once, somewhere else".

Decision (2026-09-16): group, do not hide. Those rows are educational records,
and "Reading time" must still equal the sum of its column. Each unit / subject
now carries `current`, computed from the shared resolver (pitfall #31) plus the
fork -> source rule, and the client groups `current: false` apart.

The fork case is tested because #763's first draft read `curriculum_units`
for the resolved ids directly — which returns nothing for a school fork, the
same trap #650 hit on the demo for this very student.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from src.reports.service import get_student_report
from tests.helpers.token_factory import make_teacher_token
from tests.test_subject_breakdown_zero_attempts_763 import (
    _attempt,
    _by_subject,
    _curriculum,
    _student_id,
    _student_on,
    _token_for,
)


async def _enrol(client: AsyncClient, school_id: str, student_id: str, grade: int) -> None:
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await conn.execute(
            """
            INSERT INTO school_enrolments (school_id, student_id, student_email, grade, status)
            VALUES ($1, $2, $3, $4, 'active')
            """,
            uuid.UUID(school_id),
            uuid.UUID(student_id),
            f"e758-{student_id[:8]}@example.com",
            grade,
        )


async def _moved_to_commerce(client: AsyncClient, seed: str) -> tuple[str, str]:
    """A student with STEM history, now routed to Commerce. Returns (student, school)."""
    student_id = _student_id(seed)
    stem = await _curriculum(client, 11, [(f"E-PHY-{seed[-4:]}", "G11-PHYS", "Physics")])
    commerce = await _curriculum(
        client,
        11,
        [
            (f"E-ACC-{seed[-4:]}", "G11-ACC", "Accountancy"),
            (f"E-BUS-{seed[-4:]}", "G11-BUS", "Business Studies"),
        ],
    )
    school_id = await _student_on(client, student_id, 11, commerce)
    # History on a curriculum no package points at any more.
    await _attempt(client, student_id, f"E-PHY-{seed[-4:]}", stem, "G11-PHYS")
    await _attempt(client, student_id, f"E-ACC-{seed[-4:]}", commerce, "G11-ACC")
    return student_id, school_id


# ── Student: Subject Breakdown ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_breakdown_marks_earlier_curriculum_subjects_not_current(client, db_conn):
    student_id, school_id = await _moved_to_commerce(client, "b7580000-0000-0000-0000-000000000001")

    r = await client.get(
        "/api/v1/analytics/student/stats?period=all",
        headers={"Authorization": f"Bearer {_token_for(student_id, school_id)}"},
    )
    assert r.status_code == 200, r.text
    by_subject = _by_subject(r.json())

    # Kept — the attempt happened — but flagged.
    assert by_subject["Physics"]["attempts"] == 1
    assert by_subject["Physics"]["current"] is False
    assert by_subject["Accountancy"]["current"] is True
    assert by_subject["Business Studies"]["current"] is True


@pytest.mark.asyncio
async def test_breakdown_lists_current_subjects_first(client, db_conn):
    """Alphabetically "Physics" would sit among the Commerce subjects; the
    student's own subjects must lead, history after."""
    student_id, school_id = await _moved_to_commerce(client, "b7580000-0000-0000-0000-000000000002")

    r = await client.get(
        "/api/v1/analytics/student/stats?period=all",
        headers={"Authorization": f"Bearer {_token_for(student_id, school_id)}"},
    )
    flags = [b["current"] for b in r.json()["subject_breakdown"]]

    assert flags == sorted(flags, reverse=True), flags


@pytest.mark.asyncio
async def test_breakdown_reads_a_forks_units_from_its_source(client, db_conn):
    """A school fork has no `curriculum_units` of its own. Reading the resolved
    id directly lists no taught subjects at all, and the zero-attempt seeding
    from #763 silently does nothing for exactly the demo student who reported it."""
    student_id = _student_id("b7580000-0000-0000-0000-000000000003")
    source = await _curriculum(client, 11, [("E-F-BUS", "G11-BUS", "Business Studies")])
    placeholder = await _curriculum(client, 11, [])
    school_id = await _student_on(client, student_id, 11, placeholder)

    fork_id = str(uuid.uuid4())
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        # School-owned at the student's grade: resolver step 1 picks it.
        await conn.execute(
            """
            INSERT INTO curricula
                (curriculum_id, name, grade, year, owner_type, school_id,
                 is_default, source_curriculum_id)
            VALUES ($1, 'Forked Commerce', 11, 2026, 'school', $2, FALSE, $3)
            """,
            fork_id,
            uuid.UUID(school_id),
            source,
        )

    r = await client.get(
        "/api/v1/analytics/student/stats?period=all",
        headers={"Authorization": f"Bearer {_token_for(student_id, school_id)}"},
    )
    by_subject = _by_subject(r.json())

    assert "Business Studies" in by_subject, r.json()
    assert by_subject["Business Studies"]["current"] is True


# ── Teacher: Unit progress ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_unit_progress_marks_earlier_curriculum_units_via_the_api(client, db_conn):
    """Through the router, because the router is what supplies pool + redis —
    without them every unit reads as current and the fix is inert."""
    student_id, school_id = await _moved_to_commerce(client, "b7580000-0000-0000-0000-000000000004")
    await _enrol(client, school_id, student_id, 11)
    token = make_teacher_token(school_id=school_id, role="school_admin")

    r = await client.get(
        f"/api/v1/reports/school/{school_id}/student/{student_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    by_unit = {u["unit_id"]: u for u in r.json()["per_unit"]}

    assert by_unit["E-PHY-0004"]["current"] is False
    assert by_unit["E-ACC-0004"]["current"] is True


@pytest.mark.asyncio
async def test_needs_attention_ignores_earlier_curriculum_subjects(client, db_conn):
    """Physics scored 7/8 and Accountancy 7/8 — with Physics counted there are two
    subjects and one is named "needs attention". Only one is current, so neither
    label applies to a subject the student no longer takes."""
    student_id, school_id = await _moved_to_commerce(client, "b7580000-0000-0000-0000-000000000005")
    await _enrol(client, school_id, student_id, 11)
    pool = client._transport.app.state.pool
    redis = client._transport.app.state.redis

    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        report = await get_student_report(conn, school_id, student_id, pool, redis)

    assert report["needs_attention_subject"] is None
    assert report["strongest_subject"] == "Accountancy"


@pytest.mark.asyncio
async def test_without_pool_every_unit_reads_as_current(client, db_conn):
    """Direct callers that predate #758 keep the old view rather than having every
    row flagged as history."""
    student_id, school_id = await _moved_to_commerce(client, "b7580000-0000-0000-0000-000000000006")
    await _enrol(client, school_id, student_id, 11)
    pool = client._transport.app.state.pool

    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        report = await get_student_report(conn, school_id, student_id)

    assert report["per_unit"]
    assert all(u["current"] for u in report["per_unit"])
