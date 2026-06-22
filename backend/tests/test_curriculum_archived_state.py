"""
tests/test_curriculum_archived_state.py

Schema tests for migration 0047_curriculum_archived_state — issue #180
(Epic 10 L-3).

Migration 0047 widens the ``curricula.retention_status`` CHECK constraint to
admit a new ``'archived'`` state and adds the partial sweeper index
``ix_curricula_archived_expires``. These tests assert the resulting schema
invariants directly against the migrated ``studybuddy_test`` database (the
same live-schema approach used by test_retention_lifecycle.py and
test_visual_library_schema.py):

  - happy path:   a curriculum can be moved to ``retention_status='archived'``
  - edge case:    the states predating 0047 (active/unavailable/purged) are
                  still accepted after the constraint is recreated
  - failure case: an unrecognised retention_status is rejected by the CHECK
  - the partial sweeper index exists and is scoped to archived rows

Curricula rows are seeded via the live pool (committed, like the retention
lifecycle tests), so each test cleans up the row it created — otherwise an
``archived`` row would survive to the session-teardown ``downgrade base`` and
violate the pre-0047 constraint that the 0047 downgrade restores.
"""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime, timedelta

import asyncpg
import pytest
import pytest_asyncio
from httpx import AsyncClient

from main import app

_dev_db_url = os.environ.get(
    "DATABASE_URL",
    "postgresql://studybuddy:studybuddy_dev@db:5432/studybuddy",
)
_TEST_DB_URL = os.environ.get(
    "TEST_DB_URL",
    _dev_db_url.replace("/studybuddy", "/studybuddy_test").replace(
        "@pgbouncer:", "@db:"
    ),
)


# ── Helpers ─────────────────────────────────────────────────────────────────


async def _register_school(client: AsyncClient) -> str:
    """Register a school via the API and return its id (FK for curricula)."""
    unique_email = f"archived-{uuid.uuid4().hex[:8]}@example.com"
    r = await client.post("/api/v1/schools/register", json={
        "school_name": "Archived State Test School",
        "contact_email": unique_email,
        "country": "US",
        "password": "SecureTestPwd1!",
    })
    assert r.status_code == 201, r.text
    return r.json()["school_id"]


async def _seed_curriculum(school_id: str, *, grade: int = 8, year: int = 2026) -> str:
    """Insert an active curricula row directly via the app pool (RLS bypassed)."""
    curriculum_id = f"{school_id}-{year}-g{grade}"
    expires_at = datetime.now(UTC) + timedelta(days=365)
    async with app.state.pool.acquire() as conn:
        await conn.execute(
            "SELECT set_config('app.current_school_id', 'bypass', false)"
        )
        await conn.execute(
            """
            INSERT INTO curricula
                (curriculum_id, grade, year, name, is_default, source_type,
                 school_id, status, owner_type, retention_status, expires_at)
            VALUES ($1, $2, $3, $4, false, 'school', $5::uuid,
                    'active', 'school', 'active', $6)
            """,
            curriculum_id, grade, year, f"Grade {grade} Curriculum ({year})",
            school_id, expires_at,
        )
    return curriculum_id


async def _set_retention_status(curriculum_id: str, value: str) -> None:
    """UPDATE a curriculum's retention_status (RLS bypassed)."""
    async with app.state.pool.acquire() as conn:
        await conn.execute(
            "SELECT set_config('app.current_school_id', 'bypass', false)"
        )
        await conn.execute(
            "UPDATE curricula SET retention_status = $2 WHERE curriculum_id = $1",
            curriculum_id, value,
        )


async def _fetch_retention_status(curriculum_id: str) -> str | None:
    async with app.state.pool.acquire() as conn:
        await conn.execute(
            "SELECT set_config('app.current_school_id', 'bypass', false)"
        )
        return await conn.fetchval(
            "SELECT retention_status FROM curricula WHERE curriculum_id = $1",
            curriculum_id,
        )


@pytest_asyncio.fixture
async def seeded_curriculum(client: AsyncClient) -> str:
    """A committed, active curriculum row; deleted on teardown.

    Cleanup runs before the ``client`` fixture closes the pool, and guarantees
    no row this test set to ``'archived'`` survives to ``downgrade base``.
    """
    school_id = await _register_school(client)
    curriculum_id = await _seed_curriculum(school_id)
    try:
        yield curriculum_id
    finally:
        async with app.state.pool.acquire() as conn:
            await conn.execute(
                "SELECT set_config('app.current_school_id', 'bypass', false)"
            )
            await conn.execute(
                "DELETE FROM curricula WHERE curriculum_id = $1", curriculum_id
            )


# ── Tests ───────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_archived_status_accepted(seeded_curriculum: str) -> None:
    """Happy path: UPDATE curricula SET retention_status='archived' succeeds."""
    await _set_retention_status(seeded_curriculum, "archived")
    assert await _fetch_retention_status(seeded_curriculum) == "archived"


@pytest.mark.asyncio
@pytest.mark.parametrize("status", ["active", "unavailable", "purged"])
async def test_pre_0047_states_still_accepted(
    seeded_curriculum: str, status: str
) -> None:
    """Edge: states from migration 0029 survive the constraint recreate."""
    await _set_retention_status(seeded_curriculum, status)
    assert await _fetch_retention_status(seeded_curriculum) == status


@pytest.mark.asyncio
async def test_unrecognised_retention_status_rejected(
    seeded_curriculum: str,
) -> None:
    """Failure: a value outside the CHECK set is rejected by the constraint."""
    with pytest.raises(asyncpg.exceptions.CheckViolationError):
        await _set_retention_status(seeded_curriculum, "definitely-not-valid")


@pytest.mark.asyncio
async def test_archived_sweeper_index_present() -> None:
    """The partial sweeper index exists and is scoped to archived rows.

    Connects directly (no app pool / client) so it is independent of any other
    test's fixture lifecycle.
    """
    conn = await asyncpg.connect(_TEST_DB_URL)
    try:
        indexdef = await conn.fetchval(
            "SELECT indexdef FROM pg_indexes "
            "WHERE indexname = 'ix_curricula_archived_expires'"
        )
    finally:
        await conn.close()

    assert indexdef is not None, "ix_curricula_archived_expires is missing"
    # Partial index over expires_at, restricted to archived rows — this is what
    # the TTL sweeper scans (WHERE retention_status='archived' AND expires_at<now).
    assert "expires_at" in indexdef
    assert "retention_status = 'archived'" in indexdef
