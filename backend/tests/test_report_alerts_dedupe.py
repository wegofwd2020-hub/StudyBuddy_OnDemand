"""Report alerts: one open alert per unit, and a cleared breach closes itself.

Reported 2026-08-31: the Alert Inbox showed "156 new", all pass-rate breaches,
and passing a quiz changed nothing. Two defects, both invisible to the old tests.

1. `evaluate_report_alerts_task` inserted with `ON CONFLICT DO NOTHING` against a
   table with no unique constraint, so the clause never fired and the daily task
   appended a duplicate row per breaching unit per day — 294 rows over 13 units on
   the demo, one repeated 69 times identically.

2. Nothing withdrew an alert when its breach cleared, so the inbox described the
   past.

These tests call `raise_pass_rate_alert` / `resolve_cleared_alerts` — the same
functions the Celery task calls — rather than re-typing their SQL. Re-typed SQL
would only prove the copy agrees with itself, which is exactly how a dedupe that
could never fire survived this long.

The over-suppression cases matter as much as the dedupe: a partial index that
silenced a *legitimate* second alert would be a worse bug than the one being
fixed, so both directions are asserted.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from src.reports.service import raise_pass_rate_alert, resolve_cleared_alerts
from tests.helpers.token_factory import make_teacher_token

_GRADE = 9


def _hdr(teacher_id: str, school_id: str, role: str = "school_admin") -> dict:
    return {"Authorization": f"Bearer {make_teacher_token(teacher_id, school_id, role)}"}


async def _register_school(client: AsyncClient, suffix: str) -> dict:
    r = await client.post(
        "/api/v1/schools/register",
        json={
            "school_name": f"Alert School{suffix}",
            "contact_email": f"alerts{suffix}{uuid.uuid4().hex[:8]}@school.example.com",
            "country": "IN",
            "password": "SecureTestPwd1!",
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


async def _seed_unit(client: AsyncClient, unit_id: str, title: str) -> None:
    """A platform curriculum holding `unit_id`, so grade and title resolve."""
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        curriculum_id = f"alert-{uuid.uuid4().hex[:8]}"
        await conn.execute(
            """
            INSERT INTO curricula (curriculum_id, name, grade, year, owner_type, is_default)
            VALUES ($1, 'Alert Curriculum', $2, 2026, 'platform', FALSE)
            """,
            curriculum_id,
            _GRADE,
        )
        await conn.execute(
            """
            INSERT INTO curriculum_units
                (unit_id, curriculum_id, subject, title, unit_name, sort_order)
            VALUES ($1, $2, 'Technology', $3, $3, 1)
            """,
            unit_id,
            curriculum_id,
            title,
        )


async def _open_rows(client: AsyncClient, school_id: str, unit_id: str) -> list:
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        return await conn.fetch(
            """
            SELECT alert_id, details, triggered_at, resolved_at, acknowledged
            FROM report_alerts
            WHERE school_id = $1 AND details->>'unit_id' = $2
            ORDER BY triggered_at
            """,
            uuid.UUID(school_id),
            unit_id,
        )


async def _raise(client: AsyncClient, school_id: str, unit_id: str, rate: float) -> None:
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await raise_pass_rate_alert(conn, school_id, unit_id, rate)


async def _resolve(client: AsyncClient, school_id: str, still: list[str]) -> int:
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        return await resolve_cleared_alerts(conn, school_id, still)


# ── Deduplication ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_raising_the_same_breach_twice_keeps_one_open_alert(client, db_conn):
    """The reported bug: the daily task appended a row per run, forever."""
    school = await _register_school(client, "_dedupe")
    await _seed_unit(client, "ALERT-DEDUPE-1", "Weather and Climate")

    for _ in range(5):  # five daily runs
        await _raise(client, school["school_id"], "ALERT-DEDUPE-1", 0.0)

    rows = await _open_rows(client, school["school_id"], "ALERT-DEDUPE-1")
    assert len(rows) == 1, f"expected one open alert, got {len(rows)}"


@pytest.mark.asyncio
async def test_a_repeat_refreshes_the_rate_but_not_the_age(client, db_conn):
    """The alert must keep saying how long the breach has run."""
    school = await _register_school(client, "_refresh")
    await _seed_unit(client, "ALERT-REFRESH-1", "Data and Statistics")

    await _raise(client, school["school_id"], "ALERT-REFRESH-1", 0.0)
    first = (await _open_rows(client, school["school_id"], "ALERT-REFRESH-1"))[0]

    await _raise(client, school["school_id"], "ALERT-REFRESH-1", 22.5)
    rows = await _open_rows(client, school["school_id"], "ALERT-REFRESH-1")
    # Assert the count first. Without it this test passes even when the repeat
    # appends a second row, because it would still find the original at [0] --
    # a test that cannot distinguish "updated" from "duplicated" is no guard.
    assert len(rows) == 1, f"expected one open alert, got {len(rows)}"
    second = rows[0]

    assert second["details"]["pass_rate"] == 22.5, "current rate should be reflected"
    assert second["triggered_at"] == first["triggered_at"], "age must not reset"
    assert second["alert_id"] == first["alert_id"], "should update, not replace"


@pytest.mark.asyncio
async def test_dismissing_an_alert_lets_a_later_breach_raise_a_new_one(client, db_conn):
    """Over-suppression would be worse than the duplication being fixed.

    The unique index is partial (open alerts only) precisely so a unit that
    breaches, is dismissed, and breaches again is not silenced the second time.
    """
    school = await _register_school(client, "_reraise")
    await _seed_unit(client, "ALERT-RERAISE-1", "Digital Citizenship")

    await _raise(client, school["school_id"], "ALERT-RERAISE-1", 0.0)
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await conn.execute(
            "UPDATE report_alerts SET acknowledged = TRUE WHERE school_id = $1",
            uuid.UUID(school["school_id"]),
        )

    await _raise(client, school["school_id"], "ALERT-RERAISE-1", 5.0)

    rows = await _open_rows(client, school["school_id"], "ALERT-RERAISE-1")
    assert len(rows) == 2, "a dismissed alert must not block a later breach"
    assert sum(1 for r in rows if not r["acknowledged"]) == 1


@pytest.mark.asyncio
async def test_two_units_do_not_share_an_alert(client, db_conn):
    """The key is per unit, not per school."""
    school = await _register_school(client, "_perunit")
    await _seed_unit(client, "ALERT-U1", "Unit One")
    await _seed_unit(client, "ALERT-U2", "Unit Two")

    await _raise(client, school["school_id"], "ALERT-U1", 0.0)
    await _raise(client, school["school_id"], "ALERT-U2", 0.0)

    assert len(await _open_rows(client, school["school_id"], "ALERT-U1")) == 1
    assert len(await _open_rows(client, school["school_id"], "ALERT-U2")) == 1


# ── Retraction ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_a_cleared_breach_is_withdrawn(client, db_conn):
    """"I passed the quizzes but the alert is still there." """
    school = await _register_school(client, "_clear")
    await _seed_unit(client, "ALERT-CLEAR-1", "Design Thinking Process")
    await _raise(client, school["school_id"], "ALERT-CLEAR-1", 0.0)

    # Next evaluation: this unit no longer breaches.
    resolved = await _resolve(client, school["school_id"], [])
    assert resolved == 1

    rows = await _open_rows(client, school["school_id"], "ALERT-CLEAR-1")
    assert rows[0]["resolved_at"] is not None


@pytest.mark.asyncio
async def test_a_still_breaching_unit_is_not_withdrawn(client, db_conn):
    """The other direction — a guard that resolves everything is useless."""
    school = await _register_school(client, "_keep")
    await _seed_unit(client, "ALERT-KEEP-1", "Still Failing")
    await _seed_unit(client, "ALERT-KEEP-2", "Now Fine")
    await _raise(client, school["school_id"], "ALERT-KEEP-1", 0.0)
    await _raise(client, school["school_id"], "ALERT-KEEP-2", 0.0)

    resolved = await _resolve(client, school["school_id"], ["ALERT-KEEP-1"])
    assert resolved == 1, "only the cleared unit should be withdrawn"

    keep = await _open_rows(client, school["school_id"], "ALERT-KEEP-1")
    gone = await _open_rows(client, school["school_id"], "ALERT-KEEP-2")
    assert keep[0]["resolved_at"] is None, "still-breaching alert must survive"
    assert gone[0]["resolved_at"] is not None


@pytest.mark.asyncio
async def test_resolution_does_not_reach_another_school(client, db_conn):
    a = await _register_school(client, "_iso_a")
    b = await _register_school(client, "_iso_b")
    await _seed_unit(client, "ALERT-ISO-1", "Shared Unit")
    await _raise(client, a["school_id"], "ALERT-ISO-1", 0.0)
    await _raise(client, b["school_id"], "ALERT-ISO-1", 0.0)

    await _resolve(client, a["school_id"], [])

    assert (await _open_rows(client, a["school_id"], "ALERT-ISO-1"))[0]["resolved_at"] is not None
    assert (await _open_rows(client, b["school_id"], "ALERT-ISO-1"))[0]["resolved_at"] is None


# ── What the teacher sees ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_the_inbox_hides_withdrawn_alerts(client, db_conn):
    school = await _register_school(client, "_hidden")
    await _seed_unit(client, "ALERT-HIDDEN-1", "Resolved Unit")
    await _raise(client, school["school_id"], "ALERT-HIDDEN-1", 0.0)
    await _resolve(client, school["school_id"], [])

    r = await client.get(
        f"/api/v1/reports/school/{school['school_id']}/alerts",
        headers=_hdr(school["teacher_id"], school["school_id"]),
    )
    assert r.status_code == 200, r.text
    units = {a["details"].get("unit_id") for a in r.json()["alerts"]}
    assert "ALERT-HIDDEN-1" not in units


@pytest.mark.asyncio
async def test_an_alert_names_its_unit(client, db_conn):
    """`unit_id: G5-TECH-004` is not something a teacher can act on."""
    school = await _register_school(client, "_title")
    await _seed_unit(client, "ALERT-TITLE-1", "Weather and Climate")
    await _raise(client, school["school_id"], "ALERT-TITLE-1", 0.0)

    r = await client.get(
        f"/api/v1/reports/school/{school['school_id']}/alerts",
        headers=_hdr(school["teacher_id"], school["school_id"]),
    )
    listed = [a for a in r.json()["alerts"] if a["details"].get("unit_id") == "ALERT-TITLE-1"]
    assert listed, r.json()
    assert listed[0]["unit_title"] == "Weather and Climate"


@pytest.mark.asyncio
async def test_the_partial_unique_index_exists(client, db_conn):
    """The mechanism, asserted directly.

    The behavioural tests above prove the OUTCOME, but they cannot prove WHICH
    change delivers it: with the index present, even the old
    `ON CONFLICT DO NOTHING` deduplicates. The index is what actually stops the
    duplication, so it is asserted on its own — including the partial predicate,
    since a non-partial index would suppress legitimate re-alerts after a
    dismissal.
    """
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        definition = await conn.fetchval(
            "SELECT indexdef FROM pg_indexes WHERE indexname = 'uq_report_alerts_open_unit'"
        )
    assert definition, "migration 0066's unique index is missing"
    assert "UNIQUE" in definition
    assert "unit_id" in definition
    assert "acknowledged" in definition and "resolved_at" in definition, (
        f"index must stay partial to open alerts, got: {definition}"
    )
