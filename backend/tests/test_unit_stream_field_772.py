"""
tests/test_unit_stream_field_772.py

Every Unit Performance row names its stream (Venki, 14 Sep — #772):

    "CSV export should group data by Grade/Steam ... Grade / Stream / Both"

The export is built in the browser from `get_curriculum_health`. Rows already
carried `grade` (#776); stream existed only as a FILTER, so a whole-school
export had no way to say which stream a unit belonged to, and grouping by it was
not expressible.

A unit's stream is its curriculum's `stream_code`, with the same fork -> source
fallback the stream filter uses (`_streams_by_student`): a school fork
carries no stream of its own. Content with no stream reads `unstreamed`, the
filter's own bucket, so a row's label and the chip that selects it agree.
"""

from __future__ import annotations

import pytest

from src.reports.service import UNSTREAMED, get_curriculum_health
from tests.helpers.token_factory import make_teacher_token
from tests.test_reports_stream_filter_774 import (
    _activity,
    _curriculum,
    _school,
    _student_on,
)


def _by_unit(report: dict) -> dict[str, dict]:
    return {u["unit_id"]: u for u in report["units"]}


@pytest.mark.asyncio
async def test_each_unit_carries_its_curriculums_stream(client, db_conn, fake_redis):
    school_id = await _school(client)
    com = await _curriculum(client, 11, "SF-COM-001", "commerce")
    sci = await _curriculum(client, 11, "SF-SCI-001", "science")
    s = await _student_on(client, school_id, 11, [com, sci])
    await _activity(client, s, "SF-COM-001", com, 11)
    pool = client._transport.app.state.pool

    units = _by_unit(await get_curriculum_health(db_conn, school_id, pool=pool, redis=fake_redis))

    assert units["SF-COM-001"]["stream"] == "commerce"
    # Untouched units come through the catalog merge, not activity — they must
    # be labelled too, or the export's no-activity rows have a blank stream.
    assert units["SF-SCI-001"]["stream"] == "science"


@pytest.mark.asyncio
async def test_content_with_no_stream_reads_unstreamed(client, db_conn, fake_redis):
    school_id = await _school(client)
    plain = await _curriculum(client, 11, "SF-PLAIN-001", None)
    s = await _student_on(client, school_id, 11, [plain])
    await _activity(client, s, "SF-PLAIN-001", plain, 11)
    pool = client._transport.app.state.pool

    units = _by_unit(await get_curriculum_health(db_conn, school_id, pool=pool, redis=fake_redis))

    assert units["SF-PLAIN-001"]["stream"] == UNSTREAMED


@pytest.mark.asyncio
async def test_a_fork_unit_takes_its_source_stream(client, db_conn, fake_redis):
    school_id = await _school(client)
    source = await _curriculum(client, 11, "SF-SRC-001", "commerce")
    fork = await _curriculum(client, 11, "SF-FORK-001", None, source_curriculum_id=source)
    s = await _student_on(client, school_id, 11, [fork])
    await _activity(client, s, "SF-FORK-001", fork, 11)
    pool = client._transport.app.state.pool

    units = _by_unit(await get_curriculum_health(db_conn, school_id, pool=pool, redis=fake_redis))

    assert units["SF-FORK-001"]["stream"] == "commerce"


@pytest.mark.asyncio
async def test_the_stream_reaches_the_api_response(client, db_conn):
    """Through the router: a field the service sets and the response model does
    not declare is silently dropped by pydantic."""
    school_id = await _school(client)
    com = await _curriculum(client, 11, "SF-API-001", "commerce")
    s = await _student_on(client, school_id, 11, [com])
    await _activity(client, s, "SF-API-001", com, 11)
    token = make_teacher_token(school_id=school_id, role="school_admin")

    r = await client.get(
        f"/api/v1/reports/school/{school_id}/curriculum-health",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text

    assert _by_unit(r.json())["SF-API-001"]["stream"] == "commerce"
