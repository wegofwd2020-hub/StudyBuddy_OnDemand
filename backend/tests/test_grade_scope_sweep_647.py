"""
tests/test_grade_scope_sweep_647.py

Alerts, classrooms and class metrics must be grade-scoped (issue #647).

Reported by Venki 2026-08-26 as two questions — *"Alerts shows data for all
Grades - Is this OK?"* and *"Class room shows all Grades - Is this OK?"* — and
the answer to both is no.

#576 set the rule: a teacher sees THEIR grades, `school_admin` sees the school
(a teacher superset, ADR-005). #628 applied it to the six report endpoints that
draw their cohort from `_enrolled_ids()`.

## Why it kept being missed

The rule lived as a private helper inside `reports/router.py`:

  - **Alerts** has its own query rather than going through `_enrolled_ids()`,
    so it was not in the swept set — *and it sits in the same file*.
  - **Classrooms** lives in the school router, which could not reach the helper
    without importing across routers.
  - **Class metrics** lives in the analytics router — found by the follow-up
    sweep this issue asked for, not by the report. It honoured a client-supplied
    `?grade=` with no check at all, which is the #576 bug verbatim.

The rule now lives in `src/core/grade_scope.py` so a module cannot miss it for
being unable to import it. Scope the CONCEPT, not the endpoints the issue
happened to list.

## Severity

All three are teacher-facing within one school — no cross-tenant exposure. The
classroom DETAIL endpoint is the sharpest: it returns the classroom's students,
and it was not in the report at all.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from tests.helpers.token_factory import make_teacher_token

_MINE = 8
_THEIRS = 11


async def _register_school(client: AsyncClient, suffix: str) -> dict:
    r = await client.post(
        "/api/v1/schools/register",
        json={
            "school_name": f"Sweep School{suffix}",
            "contact_email": f"sweep{suffix}@school.example.com",
            "country": "IN",
            "password": "SecureTestPwd1!",
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


async def _teacher(client: AsyncClient, school_id: str, grades: list[int]) -> str:
    teacher_id = str(uuid.uuid4())
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await conn.execute(
            """
            INSERT INTO teachers
                (teacher_id, school_id, external_auth_id, name, email, role, account_status)
            VALUES ($1, $2, $3, 'Sweep Teacher', $4, 'teacher', 'active')
            """,
            uuid.UUID(teacher_id),
            uuid.UUID(school_id),
            f"auth0|sweep-{teacher_id.replace('-', '')}",
            f"sweep-{teacher_id[:8]}@example.com",
        )
        for g in grades:
            await conn.execute(
                """
                INSERT INTO teacher_grade_assignments (teacher_id, school_id, grade)
                VALUES ($1, $2, $3) ON CONFLICT DO NOTHING
                """,
                uuid.UUID(teacher_id),
                uuid.UUID(school_id),
                g,
            )
    return teacher_id


def _hdr(teacher_id: str, school_id: str, role: str = "teacher") -> dict:
    return {
        "Authorization": "Bearer "
        + make_teacher_token(teacher_id=teacher_id, school_id=school_id, role=role)
    }


async def _seed_unit(client: AsyncClient, unit_id: str, grade: int) -> str:
    """A platform curriculum at `grade` holding `unit_id`, so alerts resolve."""
    curriculum_id = f"sweep-{uuid.uuid4().hex[:8]}"
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await conn.execute(
            """
            INSERT INTO curricula (curriculum_id, name, grade, year, owner_type, is_default)
            VALUES ($1, 'Sweep Curriculum', $2, 2026, 'platform', FALSE)
            """,
            curriculum_id,
            grade,
        )
        await conn.execute(
            """
            INSERT INTO curriculum_units
                (unit_id, curriculum_id, subject, title, unit_name, sort_order)
            VALUES ($1, $2, 'Sweep', 'Sweep Unit', 'Sweep Unit', 1)
            """,
            unit_id,
            curriculum_id,
        )
    return curriculum_id


async def _alert(client: AsyncClient, school_id: str, unit_id: str) -> None:
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await conn.execute(
            """
            INSERT INTO report_alerts (school_id, alert_type, details)
            VALUES ($1, 'pass_rate_breach', $2::jsonb)
            """,
            uuid.UUID(school_id),
            # A dict, not json.dumps(...): the test pool mirrors the app pool's
            # jsonb codec (conftest `_init_db_conn`), which serialises for us.
            # Pre-dumping stores a JSON *string* rather than an object, and the
            # column then reads back as str.
            {"unit_id": unit_id, "pass_rate": 0.0},
        )


async def _classroom(client: AsyncClient, school_id: str, grade: int, name: str) -> str:
    classroom_id = str(uuid.uuid4())
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await conn.execute(
            """
            INSERT INTO classrooms (classroom_id, school_id, name, grade, status)
            VALUES ($1, $2, $3, $4, 'active')
            """,
            uuid.UUID(classroom_id),
            uuid.UUID(school_id),
            name,
            grade,
        )
    return classroom_id


# ── Alerts ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_a_teacher_sees_alerts_only_for_their_grades(client, db_conn):
    """The reported case: a Grade-8 teacher saw Grade 5, 10 and 11 breaches."""
    school = await _register_school(client, "_alerts")
    await _seed_unit(client, "SWEEP-G8-1", _MINE)
    await _seed_unit(client, "SWEEP-G11-1", _THEIRS)
    await _alert(client, school["school_id"], "SWEEP-G8-1")
    await _alert(client, school["school_id"], "SWEEP-G11-1")

    teacher_id = await _teacher(client, school["school_id"], [_MINE])
    r = await client.get(
        f"/api/v1/reports/school/{school['school_id']}/alerts",
        headers=_hdr(teacher_id, school["school_id"]),
    )
    assert r.status_code == 200, r.text
    units = {a["details"].get("unit_id") for a in r.json()["alerts"]}
    assert "SWEEP-G8-1" in units, r.json()
    assert "SWEEP-G11-1" not in units, r.json()


@pytest.mark.asyncio
async def test_a_school_admin_still_sees_every_grades_alerts(client, db_conn):
    """ADR-005: school_admin is a teacher superset and keeps full visibility."""
    school = await _register_school(client, "_alerts_admin")
    await _seed_unit(client, "SWEEP-A8-1", _MINE)
    await _seed_unit(client, "SWEEP-A11-1", _THEIRS)
    await _alert(client, school["school_id"], "SWEEP-A8-1")
    await _alert(client, school["school_id"], "SWEEP-A11-1")

    r = await client.get(
        f"/api/v1/reports/school/{school['school_id']}/alerts",
        headers=_hdr(school["teacher_id"], school["school_id"], "school_admin"),
    )
    units = {a["details"].get("unit_id") for a in r.json()["alerts"]}
    assert {"SWEEP-A8-1", "SWEEP-A11-1"} <= units, r.json()


@pytest.mark.asyncio
async def test_an_alert_carries_the_grade_it_belongs_to(client, db_conn):
    """Without it a scoped list is indistinguishable from an unscoped one."""
    school = await _register_school(client, "_alert_grade")
    await _seed_unit(client, "SWEEP-GR-1", _MINE)
    await _alert(client, school["school_id"], "SWEEP-GR-1")

    r = await client.get(
        f"/api/v1/reports/school/{school['school_id']}/alerts",
        headers=_hdr(school["teacher_id"], school["school_id"], "school_admin"),
    )
    listed = [a for a in r.json()["alerts"] if a["details"].get("unit_id") == "SWEEP-GR-1"]
    assert listed and listed[0]["grade"] == _MINE, r.json()


# ── Classrooms ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_a_teacher_lists_only_their_grades_classrooms(client, db_conn):
    school = await _register_school(client, "_rooms")
    await _classroom(client, school["school_id"], _MINE, "Mine")
    await _classroom(client, school["school_id"], _THEIRS, "Theirs")

    teacher_id = await _teacher(client, school["school_id"], [_MINE])
    r = await client.get(
        f"/api/v1/schools/{school['school_id']}/classrooms",
        headers=_hdr(teacher_id, school["school_id"]),
    )
    assert r.status_code == 200, r.text
    names = {c["name"] for c in r.json()}
    assert "Mine" in names and "Theirs" not in names, r.json()


@pytest.mark.asyncio
async def test_the_classroom_detail_is_scoped_too(client, db_conn):
    """Not in the report, and the sharper leak — detail returns the students.

    Fixing only what was reported would have left this open.
    """
    school = await _register_school(client, "_room_detail")
    other = await _classroom(client, school["school_id"], _THEIRS, "Theirs")

    teacher_id = await _teacher(client, school["school_id"], [_MINE])
    r = await client.get(
        f"/api/v1/schools/{school['school_id']}/classrooms/{other}",
        headers=_hdr(teacher_id, school["school_id"]),
    )
    # 404, not 403: confirming "exists but not yours" still leaks which grades
    # the school runs.
    assert r.status_code == 404, r.text


@pytest.mark.asyncio
async def test_a_school_admin_still_sees_every_classroom(client, db_conn):
    school = await _register_school(client, "_rooms_admin")
    await _classroom(client, school["school_id"], _MINE, "AdminMine")
    await _classroom(client, school["school_id"], _THEIRS, "AdminTheirs")

    r = await client.get(
        f"/api/v1/schools/{school['school_id']}/classrooms",
        headers=_hdr(school["teacher_id"], school["school_id"], "school_admin"),
    )
    names = {c["name"] for c in r.json()}
    assert {"AdminMine", "AdminTheirs"} <= names, r.json()


# ── Class metrics (found by the sweep, not the report) ────────────────────────


@pytest.mark.asyncio
async def test_class_metrics_rejects_a_grade_the_teacher_is_not_assigned_to(client, db_conn):
    """`?grade=` was honoured with no check — the #576 bug verbatim."""
    school = await _register_school(client, "_metrics")
    teacher_id = await _teacher(client, school["school_id"], [_MINE])

    r = await client.get(
        f"/api/v1/analytics/school/{school['school_id']}/class?grade={_THEIRS}",
        headers=_hdr(teacher_id, school["school_id"]),
    )
    assert r.status_code == 403, r.text


@pytest.mark.asyncio
async def test_class_metrics_allows_a_grade_the_teacher_is_assigned_to(client, db_conn):
    """Guard against over-correcting into blocking legitimate access."""
    school = await _register_school(client, "_metrics_ok")
    teacher_id = await _teacher(client, school["school_id"], [_MINE])

    r = await client.get(
        f"/api/v1/analytics/school/{school['school_id']}/class?grade={_MINE}",
        headers=_hdr(teacher_id, school["school_id"]),
    )
    assert r.status_code == 200, r.text


@pytest.mark.asyncio
async def test_class_metrics_admin_may_request_any_grade(client, db_conn):
    school = await _register_school(client, "_metrics_admin")
    r = await client.get(
        f"/api/v1/analytics/school/{school['school_id']}/class?grade={_THEIRS}",
        headers=_hdr(school["teacher_id"], school["school_id"], "school_admin"),
    )
    assert r.status_code == 200, r.text
