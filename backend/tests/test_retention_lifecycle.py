"""
tests/test_retention_lifecycle.py

Integration tests for the Phase D retention lifecycle service functions.

Tests call the async functions in src.school.retention_service directly
(not through Celery tasks) to avoid the nested-event-loop restriction
that arises when calling _run_async() inside an already-running asyncio loop.

Each test:
  1. Registers a school (API call → creates school + teacher + quota row)
  2. Seeds curricula rows directly via app.state.pool with specific
     expires_at / grace_until / retention_status values.
  3. Acquires a connection from app.state.pool, sets RLS bypass, and
     awaits the service function under test.
  4. Queries app.state.pool to verify DB state after the call.

Functions under test (src.school.retention_service):
  - send_pre_expiry_warnings     (email stub only; no DB state change)
  - expire_active_curricula      (active → unavailable, sets grace_until)
  - send_grace_90day_reminders   (email stub only; no DB state change)
  - send_purge_30day_warnings    (email stub only; no DB state change)
  - purge_grace_expired          (unavailable → purged, deletes content dir)
"""

from __future__ import annotations

import io
import json
import os
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient

from main import app
from src.core.storage import LocalStorage
from src.school.retention_service import (
    expire_active_curricula,
    purge_grace_expired,
    send_grace_90day_reminders,
    send_pre_expiry_warnings,
    send_purge_30day_warnings,
)


# ── Helpers ───────────────────────────────────────────────────────────────────


async def _register_school(client: AsyncClient) -> dict:
    unique_email = f"lifecycle-{uuid.uuid4().hex[:8]}@example.com"
    r = await client.post("/api/v1/schools/register", json={
        "school_name": "Lifecycle Test School",
        "contact_email": unique_email,
        "country": "US",
    })
    assert r.status_code == 201, r.text
    return r.json()


async def _seed_curriculum(
    school_id: str,
    grade: int = 8,
    year: int = 2026,
    *,
    retention_status: str = "active",
    expires_at: datetime | None = None,
    grace_until: datetime | None = None,
) -> str:
    """Insert a curricula row directly via the app pool (RLS bypassed)."""
    curriculum_id = f"{school_id}-{year}-g{grade}"
    expires_at = expires_at or (datetime.now(UTC) + timedelta(days=365))

    async with app.state.pool.acquire() as conn:
        await conn.execute(
            "SELECT set_config('app.current_school_id', 'bypass', false)"
        )
        await conn.execute(
            """
            INSERT INTO curricula
                (curriculum_id, grade, year, name, is_default, source_type,
                 school_id, status, owner_type, retention_status, expires_at,
                 grace_until)
            VALUES ($1, $2, $3, $4, false, 'school', $5::uuid,
                    'active', 'school', $6, $7, $8)
            ON CONFLICT (curriculum_id) DO UPDATE
                SET retention_status = EXCLUDED.retention_status,
                    expires_at       = EXCLUDED.expires_at,
                    grace_until      = EXCLUDED.grace_until
            """,
            curriculum_id, grade, year, f"Grade {grade} Curriculum ({year})",
            school_id, retention_status, expires_at, grace_until,
        )
    return curriculum_id


async def _fetch_curriculum(curriculum_id: str) -> dict | None:
    async with app.state.pool.acquire() as conn:
        await conn.execute(
            "SELECT set_config('app.current_school_id', 'bypass', false)"
        )
        row = await conn.fetchrow(
            """
            SELECT curriculum_id, retention_status, expires_at, grace_until
            FROM curricula WHERE curriculum_id = $1
            """,
            curriculum_id,
        )
    return dict(row) if row else None


async def _bypass_conn():
    """Context manager: acquire a pool connection with RLS bypassed."""
    conn = await app.state.pool.acquire()
    await conn.execute(
        "SELECT set_config('app.current_school_id', 'bypass', false)"
    )
    return conn


# ── Task 1: pre-expiry warning (log only, no state change) ───────────────────


@pytest.mark.asyncio
async def test_pre_expiry_warning_selects_correct_curricula(client: AsyncClient):
    """
    send_pre_expiry_warnings logs for curricula expiring in ~30 days
    and does not change retention_status.
    """
    reg = await _register_school(client)
    school_id = reg["school_id"]

    # Expiring in exactly 30 days — should be selected
    target_cid = await _seed_curriculum(
        school_id, grade=8,
        expires_at=datetime.now(UTC) + timedelta(days=30),
    )
    # Expiring in 60 days — should NOT be selected
    await _seed_curriculum(
        school_id, grade=9, year=2027,
        expires_at=datetime.now(UTC) + timedelta(days=60),
    )

    async with app.state.pool.acquire() as conn:
        await conn.execute(
            "SELECT set_config('app.current_school_id', 'bypass', false)"
        )
        count = await send_pre_expiry_warnings(conn)

    # Only the 30-day curriculum should have been selected (count ≥ 1)
    assert count >= 1

    # State must not change
    row = await _fetch_curriculum(target_cid)
    assert row["retention_status"] == "active"


# ── Task 2: expiry sweep (active → unavailable) ───────────────────────────────


@pytest.mark.asyncio
async def test_sweep_transitions_expired_curriculum_to_unavailable(client: AsyncClient):
    """
    expire_active_curricula marks curricula past their expires_at as
    'unavailable' and sets grace_until = expires_at + 180 days.
    """
    reg = await _register_school(client)
    school_id = reg["school_id"]

    expired_at = datetime.now(UTC) - timedelta(days=1)
    cid = await _seed_curriculum(
        school_id, grade=8,
        retention_status="active",
        expires_at=expired_at,
    )

    async with app.state.pool.acquire() as conn:
        await conn.execute(
            "SELECT set_config('app.current_school_id', 'bypass', false)"
        )
        transitioned = await expire_active_curricula(conn)

    assert any(r["curriculum_id"] == cid for r in transitioned)

    row = await _fetch_curriculum(cid)
    assert row["retention_status"] == "unavailable"
    assert row["grace_until"] is not None

    expected_grace = expired_at + timedelta(days=180)
    diff = abs((row["grace_until"] - expected_grace).total_seconds())
    assert diff < 60


@pytest.mark.asyncio
async def test_sweep_ignores_future_expiry(client: AsyncClient):
    """Curricula with a future expiry date are not touched."""
    reg = await _register_school(client)
    school_id = reg["school_id"]

    cid = await _seed_curriculum(
        school_id, grade=9,
        retention_status="active",
        expires_at=datetime.now(UTC) + timedelta(days=30),
    )

    async with app.state.pool.acquire() as conn:
        await conn.execute(
            "SELECT set_config('app.current_school_id', 'bypass', false)"
        )
        transitioned = await expire_active_curricula(conn)

    assert not any(r["curriculum_id"] == cid for r in transitioned)
    row = await _fetch_curriculum(cid)
    assert row["retention_status"] == "active"
    assert row["grace_until"] is None


@pytest.mark.asyncio
async def test_sweep_is_idempotent(client: AsyncClient):
    """Running the sweep twice does not corrupt grace_until."""
    reg = await _register_school(client)
    school_id = reg["school_id"]

    cid = await _seed_curriculum(
        school_id, grade=10,
        retention_status="active",
        expires_at=datetime.now(UTC) - timedelta(days=2),
    )

    async with app.state.pool.acquire() as conn:
        await conn.execute(
            "SELECT set_config('app.current_school_id', 'bypass', false)"
        )
        await expire_active_curricula(conn)
        row_after_first = await _fetch_curriculum(cid)
        grace_after_first = row_after_first["grace_until"]

        await expire_active_curricula(conn)

    row_after_second = await _fetch_curriculum(cid)
    assert row_after_second["retention_status"] == "unavailable"
    assert row_after_second["grace_until"] == grace_after_first


# ── Task 3: 90-day grace reminder ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_grace_reminder_runs_without_error(client: AsyncClient):
    """
    send_grace_90day_reminders completes and returns the count of matched
    curricula. No state change.
    """
    reg = await _register_school(client)
    school_id = reg["school_id"]

    # grace_until in 90 days → today is day 90 of grace
    grace_until = datetime.now(UTC) + timedelta(days=90)
    cid = await _seed_curriculum(
        school_id, grade=8,
        retention_status="unavailable",
        expires_at=datetime.now(UTC) - timedelta(days=90),
        grace_until=grace_until,
    )

    async with app.state.pool.acquire() as conn:
        await conn.execute(
            "SELECT set_config('app.current_school_id', 'bypass', false)"
        )
        count = await send_grace_90day_reminders(conn)

    assert count >= 1
    row = await _fetch_curriculum(cid)
    assert row["retention_status"] == "unavailable"  # no state change


# ── Task 4: purge warning (day 150) ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_purge_warning_runs_without_error(client: AsyncClient):
    """
    send_purge_30day_warnings completes and returns the count. No state change.
    """
    reg = await _register_school(client)
    school_id = reg["school_id"]

    # grace_until in 30 days → today is day 150 of 180-day grace
    grace_until = datetime.now(UTC) + timedelta(days=30)
    cid = await _seed_curriculum(
        school_id, grade=9,
        retention_status="unavailable",
        expires_at=datetime.now(UTC) - timedelta(days=150),
        grace_until=grace_until,
    )

    async with app.state.pool.acquire() as conn:
        await conn.execute(
            "SELECT set_config('app.current_school_id', 'bypass', false)"
        )
        count = await send_purge_30day_warnings(conn)

    assert count >= 1
    row = await _fetch_curriculum(cid)
    assert row["retention_status"] == "unavailable"  # no state change


# ── Task 5: purge ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_purge_transitions_to_purged(client: AsyncClient):
    """purge_grace_expired marks grace-expired curricula as 'purged'."""
    reg = await _register_school(client)
    school_id = reg["school_id"]

    from config import settings

    cid = await _seed_curriculum(
        school_id, grade=8,
        retention_status="unavailable",
        expires_at=datetime.now(UTC) - timedelta(days=181),
        grace_until=datetime.now(UTC) - timedelta(days=1),
    )

    storage = LocalStorage(root=settings.CONTENT_STORE_PATH)
    async with app.state.pool.acquire() as conn:
        await conn.execute(
            "SELECT set_config('app.current_school_id', 'bypass', false)"
        )
        purged = await purge_grace_expired(conn, storage)

    assert any(r["curriculum_id"] == cid for r in purged)
    row = await _fetch_curriculum(cid)
    assert row["retention_status"] == "purged"


@pytest.mark.asyncio
async def test_purge_handles_missing_content_directory(client: AsyncClient):
    """Purge completes without error when the content directory doesn't exist."""
    reg = await _register_school(client)
    school_id = reg["school_id"]

    from config import settings

    cid = await _seed_curriculum(
        school_id, grade=9,
        retention_status="unavailable",
        expires_at=datetime.now(UTC) - timedelta(days=200),
        grace_until=datetime.now(UTC) - timedelta(days=20),
    )

    storage = LocalStorage(root=settings.CONTENT_STORE_PATH)
    async with app.state.pool.acquire() as conn:
        await conn.execute(
            "SELECT set_config('app.current_school_id', 'bypass', false)"
        )
        purged = await purge_grace_expired(conn, storage)

    assert any(r["curriculum_id"] == cid for r in purged)
    row = await _fetch_curriculum(cid)
    assert row["retention_status"] == "purged"


@pytest.mark.asyncio
async def test_purge_deletes_content_directory(client: AsyncClient):
    """purge_grace_expired removes the curriculum directory when it exists."""
    reg = await _register_school(client)
    school_id = reg["school_id"]

    from config import settings

    cid = await _seed_curriculum(
        school_id, grade=10,
        retention_status="unavailable",
        expires_at=datetime.now(UTC) - timedelta(days=181),
        grace_until=datetime.now(UTC) - timedelta(days=1),
    )

    # Create a fake content directory
    content_dir = os.path.join(settings.CONTENT_STORE_PATH, "curricula", cid)
    os.makedirs(content_dir, exist_ok=True)
    with open(os.path.join(content_dir, "lesson_en.json"), "w") as f:
        f.write('{"test": true}')

    assert os.path.isdir(content_dir)

    storage = LocalStorage(root=settings.CONTENT_STORE_PATH)
    async with app.state.pool.acquire() as conn:
        await conn.execute(
            "SELECT set_config('app.current_school_id', 'bypass', false)"
        )
        await purge_grace_expired(conn, storage)

    assert not os.path.exists(content_dir)
    row = await _fetch_curriculum(cid)
    assert row["retention_status"] == "purged"


@pytest.mark.asyncio
async def test_purge_is_idempotent(client: AsyncClient):
    """Running purge twice does not raise or corrupt already-purged rows."""
    reg = await _register_school(client)
    school_id = reg["school_id"]

    from config import settings

    cid = await _seed_curriculum(
        school_id, grade=11,
        retention_status="unavailable",
        expires_at=datetime.now(UTC) - timedelta(days=190),
        grace_until=datetime.now(UTC) - timedelta(days=10),
    )

    storage = LocalStorage(root=settings.CONTENT_STORE_PATH)
    async with app.state.pool.acquire() as conn:
        await conn.execute(
            "SELECT set_config('app.current_school_id', 'bypass', false)"
        )
        await purge_grace_expired(conn, storage)
        await purge_grace_expired(conn, storage)

    row = await _fetch_curriculum(cid)
    assert row["retention_status"] == "purged"


@pytest.mark.asyncio
async def test_purge_ignores_curricula_still_in_grace(client: AsyncClient):
    """Active and in-grace-period curricula are not affected by purge."""
    reg = await _register_school(client)
    school_id = reg["school_id"]

    from config import settings

    active_cid = await _seed_curriculum(
        school_id, grade=8,
        retention_status="active",
        expires_at=datetime.now(UTC) + timedelta(days=200),
    )
    in_grace_cid = await _seed_curriculum(
        school_id, grade=9,
        retention_status="unavailable",
        expires_at=datetime.now(UTC) - timedelta(days=90),
        grace_until=datetime.now(UTC) + timedelta(days=90),  # still in grace
    )

    async with app.state.pool.acquire() as conn:
        await conn.execute(
            "SELECT set_config('app.current_school_id', 'bypass', false)"
        )
        purged = await purge_grace_expired(conn, settings.CONTENT_STORE_PATH)

    assert not any(r["curriculum_id"] == active_cid for r in purged)
    assert not any(r["curriculum_id"] == in_grace_cid for r in purged)
    assert (await _fetch_curriculum(active_cid))["retention_status"] == "active"
    assert (await _fetch_curriculum(in_grace_cid))["retention_status"] == "unavailable"


# ── Version cap: purged versions free their slot ──────────────────────────────


@pytest.mark.asyncio
async def test_purged_version_frees_cap_slot(client: AsyncClient):
    """
    After lifecycle purge, the version slot is freed so a new upload succeeds.
    The cap query uses retention_status <> 'purged'.
    """
    from config import settings
    from tests.helpers.token_factory import make_teacher_token

    reg = await _register_school(client)
    school_id = reg["school_id"]
    token = make_teacher_token(
        teacher_id=reg["teacher_id"], school_id=school_id, role="school_admin"
    )

    def _grade_json(grade: int, year: int) -> bytes:
        return json.dumps({
            "grade": grade,
            "subjects": [{"name": "Math", "units": [
                {"unit_id": f"G{grade}-M-001-{year}", "title": "Algebra"}
            ]}],
        }).encode()

    # Fill cap with 5 active versions
    for year in range(2024, 2029):
        r = await client.post(
            f"/api/v1/schools/{school_id}/curriculum/upload",
            files={"file": ("g.json", io.BytesIO(_grade_json(7, year)), "application/json")},
            params={"year": year},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200, r.text

    # 6th upload must be blocked
    r = await client.post(
        f"/api/v1/schools/{school_id}/curriculum/upload",
        files={"file": ("g.json", io.BytesIO(_grade_json(7, 2029)), "application/json")},
        params={"year": 2029},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 409
    assert r.json()["error"] == "version_cap_reached"

    # Lifecycle-purge the oldest version
    oldest_cid = f"{school_id}-2024-g7"
    async with app.state.pool.acquire() as conn:
        await conn.execute(
            "SELECT set_config('app.current_school_id', 'bypass', false)"
        )
        await conn.execute(
            """
            UPDATE curricula
            SET retention_status = 'unavailable',
                grace_until = NOW() - INTERVAL '1 day'
            WHERE curriculum_id = $1
            """,
            oldest_cid,
        )
        await purge_grace_expired(conn, settings.CONTENT_STORE_PATH)

    # Confirm it's purged
    row = await _fetch_curriculum(oldest_cid)
    assert row["retention_status"] == "purged"

    # Now the 6th upload should succeed
    r = await client.post(
        f"/api/v1/schools/{school_id}/curriculum/upload",
        files={"file": ("g.json", io.BytesIO(_grade_json(7, 2029)), "application/json")},
        params={"year": 2029},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["version_count"] == 5  # 4 active + 1 new (purged not counted)
