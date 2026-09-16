"""
tests/test_stream_filter_history_793.py

A stream filter shows that stream's units, even for a student who changed stream
(#793).

Found verifying #772 on the demo: ABC School filtered to Commerce listed 27
units, 14 of them STEM or Science — every one from Venky_Gr11, whose class moved
from STEM to Commerce on 11 Sep.

The filter narrowed the COHORT (students whose resolved curricula are Commerce)
and then listed every unit that cohort had touched, so a student who changed
stream carried their old units into the new stream's view. #774's own test is
named `test_selecting_a_stream_drops_the_other_streams_units`, but its students
never changed stream, so it could not see this.

Decision (2026-09-16): filter on the UNIT's stream as well. History stays in the
unfiltered view, labelled with its own stream (#772). Counts describe the rows.
"""

from __future__ import annotations

import pytest

from src.reports.service import get_curriculum_health
from tests.test_reports_stream_filter_774 import (
    _activity,
    _curriculum,
    _school,
    _student_on,
)


async def _moved_from_stem_to_commerce(client) -> tuple[str, str, str]:
    """One student: STEM history on a curriculum no package points at any more,
    now routed to Commerce. Returns (school_id, stem_unit, commerce_unit)."""
    school_id = await _school(client)
    stem = await _curriculum(client, 11, "SH-STEM-001", "stem")
    com = await _curriculum(client, 11, "SH-COM-001", "commerce")
    s = await _student_on(client, school_id, 11, [com])
    await _activity(client, s, "SH-STEM-001", stem, 11)
    await _activity(client, s, "SH-COM-001", com, 11)
    return school_id, "SH-STEM-001", "SH-COM-001"


def _ids(report: dict) -> set[str]:
    return {u["unit_id"] for u in report["units"]}


@pytest.mark.asyncio
async def test_a_stream_filter_drops_a_students_earlier_stream_units(client, db_conn, fake_redis):
    school_id, stem_unit, com_unit = await _moved_from_stem_to_commerce(client)
    pool = client._transport.app.state.pool

    report = await get_curriculum_health(
        db_conn, school_id, pool=pool, redis=fake_redis, stream="commerce"
    )

    assert com_unit in _ids(report)
    assert stem_unit not in _ids(report), "the student's earlier STEM unit"
    assert {u["stream"] for u in report["units"]} == {"commerce"}


@pytest.mark.asyncio
async def test_the_counts_describe_the_filtered_rows(client, db_conn, fake_redis):
    """Dropping rows without recounting would leave "2 units" above a table of
    one — the mismatch the cohort-first design of #774 existed to prevent."""
    school_id, _, _ = await _moved_from_stem_to_commerce(client)
    pool = client._transport.app.state.pool

    report = await get_curriculum_health(
        db_conn, school_id, pool=pool, redis=fake_redis, stream="commerce"
    )

    assert report["total_units"] == len(report["units"])
    tiers = [u["health_tier"] for u in report["units"]]
    for tier in ("healthy", "watch", "struggling", "no_activity"):
        assert report[f"{tier}_count"] == tiers.count(tier), tier


@pytest.mark.asyncio
async def test_history_stays_in_the_unfiltered_view(client, db_conn, fake_redis):
    """The negative case: the fix must not hide the work from the school view."""
    school_id, stem_unit, com_unit = await _moved_from_stem_to_commerce(client)
    pool = client._transport.app.state.pool

    report = await get_curriculum_health(db_conn, school_id, pool=pool, redis=fake_redis)
    by_unit = {u["unit_id"]: u for u in report["units"]}

    assert by_unit[stem_unit]["stream"] == "stem"
    assert by_unit[com_unit]["stream"] == "commerce"
