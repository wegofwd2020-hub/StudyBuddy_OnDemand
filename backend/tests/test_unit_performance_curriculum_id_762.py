"""
tests/test_unit_performance_curriculum_id_762.py

Every Unit Performance row names the curriculum its unit lives in (#762).

The row is the entry point to quiz answer review. Its page route is
`/school/content/{curriculum_id}/units/{unit_id}/answers` — curriculum first,
because a unit id alone is ambiguous once a school has a fork, and the answers
endpoint resolves ownership FROM that id
(`src/school/answer_review_service._resolve_ownership`).

The row carried `unit_id`, `subject`, `grade` and `stream` and no curriculum, so
there was nothing to build that link out of. On the demo (spec, measured
2026-09-17) no curriculum any class actually uses is adopted, so this report is
the ONLY workable entry point: without this field the feature is unreachable
exactly where it is needed.

WHICH id, precisely — and why not the fork's. The brief asked for "the fork's id
when the school has one". That is not obtainable here and is not what the
consumer wants:

  * A school fork carries NO `curriculum_units` rows of its own; its units live
    under `source_curriculum_id` (`content/service.served_units`, the #650 trap).
    So a unit -> curriculum mapping built from `curriculum_units` — the only
    per-unit mapping this report has — can only ever yield the SOURCE.
  * `_resolve_ownership` documents the platform id as the shape the Unit
    Performance report sends, and does the reverse lookup (source -> this
    school's fork, if any) itself. Sending the source is therefore correct, not
    a degradation: a school that owns a fork still sees its own questions.

So the rule is: the curriculum whose `curriculum_units` hold this unit, chosen
deterministically (`DISTINCT ON`) the way `_grades_by_unit` and
`_streams_by_unit` already choose theirs.
"""

from __future__ import annotations

import uuid

import pytest

from src.reports.service import get_curriculum_health
from tests.helpers.token_factory import make_teacher_token
from tests.test_reports_stream_filter_774 import (
    _activity,
    _curriculum,
    _school,
    _student_on,
)


def _by_unit(report: dict) -> dict[str, dict]:
    return {u["unit_id"]: u for u in report["units"]}


async def _fork_of(client, school_id: str, source_id: str, grade: int) -> str:
    """A school fork exactly as `import_unit_overrides` makes one: school-owned,
    pointing at its source, and with NO `curriculum_units` rows of its own."""
    cid = f"fork-{uuid.uuid4().hex[:8]}"
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await conn.execute(
            """
            INSERT INTO curricula
                (curriculum_id, name, grade, year, owner_type, school_id,
                 is_default, source_curriculum_id)
            VALUES ($1, 'Forked Curriculum', $2, 2026, 'school', $3, FALSE, $4)
            """,
            cid,
            grade,
            uuid.UUID(school_id),
            source_id,
        )
    return cid


@pytest.mark.asyncio
async def test_a_touched_unit_carries_its_curriculum(client, db_conn, fake_redis):
    school_id = await _school(client)
    com = await _curriculum(client, 11, "CID-COM-001", "commerce")
    student = await _student_on(client, school_id, 11, [com])
    await _activity(client, student, "CID-COM-001", com, 11)
    pool = client._transport.app.state.pool

    units = _by_unit(await get_curriculum_health(db_conn, school_id, pool=pool, redis=fake_redis))

    assert units["CID-COM-001"]["curriculum_id"] == com


@pytest.mark.asyncio
async def test_an_untouched_unit_carries_its_curriculum_too(client, db_conn, fake_redis):
    """Units nobody has opened arrive through the catalog merge, not activity.

    They are the rows a reviewer is most likely to click — a unit with a broken
    answer key can sit at no_activity — so a link that only works on touched
    rows would miss them.
    """
    school_id = await _school(client)
    com = await _curriculum(client, 11, "CID-TOUCHED-001", "commerce")
    sci = await _curriculum(client, 11, "CID-UNTOUCHED-001", "science")
    student = await _student_on(client, school_id, 11, [com, sci])
    await _activity(client, student, "CID-TOUCHED-001", com, 11)
    pool = client._transport.app.state.pool

    units = _by_unit(await get_curriculum_health(db_conn, school_id, pool=pool, redis=fake_redis))

    assert units["CID-UNTOUCHED-001"]["health_tier"] == "no_activity"
    assert units["CID-UNTOUCHED-001"]["curriculum_id"] == sci


@pytest.mark.asyncio
async def test_a_fork_unit_carries_the_source_id_the_answers_endpoint_resolves_from(
    client, db_conn, fake_redis
):
    """A fork holds no units of its own, so the row names the SOURCE.

    That is the id `_resolve_ownership` expects from this report, and it looks
    the school's fork up from it — so the reviewer still reaches their own copy.
    Naming the fork here would be naming a curriculum with no row for this unit.
    """
    school_id = await _school(client)
    source = await _curriculum(client, 11, "CID-FORKED-001", "commerce")
    fork = await _fork_of(client, school_id, source, 11)
    student = await _student_on(client, school_id, 11, [fork])
    # The session stores the SOURCE id: `resolve_unit_curriculum` applies the
    # fork -> OOB swap before writing it (progress/router.py).
    await _activity(client, student, "CID-FORKED-001", source, 11)
    pool = client._transport.app.state.pool

    units = _by_unit(await get_curriculum_health(db_conn, school_id, pool=pool, redis=fake_redis))

    assert units["CID-FORKED-001"]["curriculum_id"] == source


@pytest.mark.asyncio
async def test_the_curriculum_id_reaches_the_api_response(client, db_conn):
    """Through the router: a field the service sets and the response model does
    not declare is silently dropped by pydantic — and the link is the feature."""
    school_id = await _school(client)
    com = await _curriculum(client, 11, "CID-API-001", "commerce")
    student = await _student_on(client, school_id, 11, [com])
    await _activity(client, student, "CID-API-001", com, 11)
    token = make_teacher_token(school_id=school_id, role="school_admin")

    r = await client.get(
        f"/api/v1/reports/school/{school_id}/curriculum-health",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text

    assert _by_unit(r.json())["CID-API-001"]["curriculum_id"] == com
