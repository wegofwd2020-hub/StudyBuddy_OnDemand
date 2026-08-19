"""
tests/test_reports_feedback_table.py

Tests for the paginated flat feedback report (issue #611).

Venki, 2026-08-19: "This format is OK as long as few records are there. Once
volume grows this page will be huge."

He was right, and the backend was worse than the layout: the report grouped by
unit, looped over EVERY unit with feedback issuing three queries each, and
returned every item ever with no pagination. Cost grew with total feedback
volume on both axes.

These tests pin the replacement: a flat, paginated, filterable list whose cost
does not grow with the number of units.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from tests.test_reports import _enrol_student, _insert_student, _register_school


async def _add_feedback(
    client: AsyncClient,
    student_id: str,
    unit_id: str,
    *,
    helpful: bool | None = True,
    message: str | None = None,
    category: str = "content",
    reviewed: bool = False,
) -> str:
    pool = client._transport.app.state.pool
    row = await pool.fetchrow(
        """
        INSERT INTO feedback
            (student_id, category, unit_id, helpful, content_type, message, reviewed)
        VALUES ($1, $2, $3, $4, 'lesson', $5, $6)
        RETURNING feedback_id::text
        """,
        uuid.UUID(student_id),
        category,
        unit_id,
        helpful,
        message,
        reviewed,
    )
    return row["feedback_id"]


async def _school_with_feedback(client: AsyncClient, suffix: str, count: int, **kw) -> tuple[str, str]:
    """Register a school with one enrolled student and `count` feedback rows."""
    school = await _register_school(client, suffix)
    school_id = school["school_id"]
    sid = str(uuid.uuid4())
    email = f"fbtable{suffix}@test.invalid"
    await _insert_student(client, sid, email)
    await _enrol_student(client, school_id, sid, email)
    for i in range(count):
        await _add_feedback(client, sid, f"G8-MATH-{i:03d}", **kw)
    return school_id, school["access_token"]


@pytest.mark.asyncio
async def test_report_returns_a_flat_item_list(client, db_conn):
    """The table needs flat rows, each naming its own unit."""
    school_id, token = await _school_with_feedback(client, "_fbflat", 3)

    r = await client.get(
        f"/api/v1/reports/school/{school_id}/feedback",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    data = r.json()

    assert "items" in data, "report should expose a flat item list"
    assert len(data["items"]) == 3
    item = data["items"][0]
    for key in ("feedback_id", "unit_id", "category", "helpful", "content_type",
                "message", "submitted_at", "reviewed"):
        assert key in item, f"item missing {key}"


@pytest.mark.asyncio
async def test_report_paginates_and_does_not_grow_with_volume(client, db_conn):
    """A page is bounded by page_size no matter how much feedback exists.

    This is the actual defect: the old report returned every item ever, so the
    response grew without limit as a school accumulated feedback.
    """
    school_id, token = await _school_with_feedback(client, "_fbpage", 25)
    headers = {"Authorization": f"Bearer {token}"}

    r = await client.get(
        f"/api/v1/reports/school/{school_id}/feedback",
        headers=headers,
        params={"page": 1, "page_size": 10},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert len(data["items"]) == 10, "page_size was not honoured"
    assert data["pagination"]["total"] == 25
    assert data["pagination"]["page"] == 1
    assert data["pagination"]["page_size"] == 10

    last = await client.get(
        f"/api/v1/reports/school/{school_id}/feedback",
        headers=headers,
        params={"page": 3, "page_size": 10},
    )
    assert last.status_code == 200, last.text
    assert len(last.json()["items"]) == 5, "final page should hold the remainder"


@pytest.mark.asyncio
async def test_pages_do_not_repeat_items(client, db_conn):
    """Ordering must be stable, or paging silently drops or duplicates rows."""
    school_id, token = await _school_with_feedback(client, "_fbstable", 12)
    headers = {"Authorization": f"Bearer {token}"}

    seen: list[str] = []
    for page in (1, 2, 3):
        r = await client.get(
            f"/api/v1/reports/school/{school_id}/feedback",
            headers=headers,
            params={"page": page, "page_size": 5},
        )
        assert r.status_code == 200, r.text
        seen.extend(i["feedback_id"] for i in r.json()["items"])

    assert len(seen) == 12
    assert len(set(seen)) == 12, "the same row appeared on more than one page"


@pytest.mark.asyncio
async def test_summary_counts_cover_everything_not_just_the_page(client, db_conn):
    """Header totals describe the school, not the current page."""
    school_id, token = await _school_with_feedback(client, "_fbsum", 15)

    r = await client.get(
        f"/api/v1/reports/school/{school_id}/feedback",
        headers={"Authorization": f"Bearer {token}"},
        params={"page": 1, "page_size": 5},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["total_feedback_count"] == 15
    assert data["unreviewed_count"] == 15
    assert len(data["items"]) == 5


@pytest.mark.asyncio
async def test_reviewed_filter_narrows_the_table(client, db_conn):
    """A reviewer's main job is finding what they have not handled yet."""
    school = await _register_school(client, "_fbrev")
    school_id = school["school_id"]
    token = school["access_token"]
    sid = str(uuid.uuid4())
    email = "fbrev@test.invalid"
    await _insert_student(client, sid, email)
    await _enrol_student(client, school_id, sid, email)

    await _add_feedback(client, sid, "G8-MATH-001", reviewed=False)
    await _add_feedback(client, sid, "G8-MATH-002", reviewed=True)

    r = await client.get(
        f"/api/v1/reports/school/{school_id}/feedback",
        headers={"Authorization": f"Bearer {token}"},
        params={"reviewed": "false"},
    )
    assert r.status_code == 200, r.text
    items = r.json()["items"]
    assert len(items) == 1
    assert items[0]["reviewed"] is False
    assert items[0]["unit_id"] == "G8-MATH-001"


@pytest.mark.asyncio
async def test_unit_filter_narrows_the_table(client, db_conn):
    """Drilling into one unit is how a teacher acts on a struggling topic."""
    school_id, token = await _school_with_feedback(client, "_fbunit", 4)

    r = await client.get(
        f"/api/v1/reports/school/{school_id}/feedback",
        headers={"Authorization": f"Bearer {token}"},
        params={"unit_id": "G8-MATH-002"},
    )
    assert r.status_code == 200, r.text
    items = r.json()["items"]
    assert len(items) == 1
    assert items[0]["unit_id"] == "G8-MATH-002"


@pytest.mark.asyncio
async def test_thumbs_down_reason_reaches_the_reviewer(client, db_conn):
    """A typed reason (#612) must be visible in the table — it is the point."""
    school = await _register_school(client, "_fbreason")
    school_id = school["school_id"]
    token = school["access_token"]
    sid = str(uuid.uuid4())
    email = "fbreason@test.invalid"
    await _insert_student(client, sid, email)
    await _enrol_student(client, school_id, sid, email)
    await _add_feedback(
        client, sid, "G8-MATH-001", helpful=False, message="The second question made no sense."
    )

    r = await client.get(
        f"/api/v1/reports/school/{school_id}/feedback",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    item = r.json()["items"][0]
    assert item["helpful"] is False
    assert item["message"] == "The second question made no sense."


@pytest.mark.asyncio
async def test_empty_school_returns_an_empty_table(client, db_conn):
    """No feedback is a normal state, not an error."""
    school = await _register_school(client, "_fbempty")

    r = await client.get(
        f"/api/v1/reports/school/{school['school_id']}/feedback",
        headers={"Authorization": f"Bearer {school['access_token']}"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["items"] == []
    assert data["total_feedback_count"] == 0
    assert data["pagination"]["total"] == 0
