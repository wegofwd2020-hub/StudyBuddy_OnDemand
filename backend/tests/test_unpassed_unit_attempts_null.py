"""
tests/test_unpassed_unit_attempts_null.py

A unit no student has passed has no attempts-to-pass to average. It must report
null, not 0.0 — a zero reads as "passed first time" and is the Venki 11-08 report.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.test_curriculum_health_join_fanout import (
    _UNIT,
    _headers,
    _register_school,
    _student_with_views,
)


@pytest.mark.asyncio
async def test_unit_nobody_has_passed_reports_null_attempts(client: AsyncClient, db_conn) -> None:
    school = await _register_school(client, "_nullatt")
    await _student_with_views(
        client, school["school_id"], score=3, attempt=1, passed=False, lesson_views=1
    )

    r = await client.get(
        f"/api/v1/reports/school/{school['school_id']}/curriculum-health",
        headers=_headers(school),
    )
    assert r.status_code == 200, r.text

    unit = next(u for u in r.json()["units"] if u["unit_id"] == _UNIT)
    assert unit["avg_attempts_to_pass"] is None, unit
