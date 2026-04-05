"""
backend/tests/test_rls.py

Row-Level Security isolation tests (migration 0028).

Proves that a teacher from School A cannot read or write School B's rows,
regardless of application behaviour — the constraint is enforced at the DB layer.

Strategy
--------
Each test:
  1. Inserts rows for School A and School B using bypass mode (fixture inserts).
  2. Sets app.current_school_id to School A's ID (simulating School A JWT).
  3. Queries the table and asserts School B rows are invisible.
  4. Verifies School A rows ARE visible.
  5. Verifies that an INSERT with School B's school_id is blocked (WITH CHECK).

All assertions run within a rolled-back transaction — no data persists.

Fixed UUIDs follow Rule 9 (deterministic IDs in fixtures).
"""

from __future__ import annotations

import pytest
import pytest_asyncio
import asyncpg

# ── Deterministic fixture IDs (Rule 9) ────────────────────────────────────────

SCHOOL_A_ID = "a0000000-0000-0000-0000-000000000001"
SCHOOL_B_ID = "b0000000-0000-0000-0000-000000000001"

TEACHER_A_ID = "a1000000-0000-0000-0000-000000000001"
TEACHER_B_ID = "b1000000-0000-0000-0000-000000000001"

TEST_DB_URL = "postgresql://studybuddy:testpassword@localhost:5432/studybuddy_test"


# ── Helper: connection scoped to a specific school ────────────────────────────

@pytest_asyncio.fixture
async def bypass_conn():
    """
    Raw asyncpg connection with RLS bypass — used for fixture setup.
    Rolls back on teardown.
    """
    conn = await asyncpg.connect(TEST_DB_URL)
    tr = conn.transaction()
    await tr.start()
    await conn.execute("SELECT set_config('app.current_school_id', 'bypass', true)")
    yield conn
    await tr.rollback()
    await conn.close()


@pytest_asyncio.fixture
async def school_a_conn():
    """
    Raw asyncpg connection scoped to School A.
    Rolls back on teardown.
    """
    conn = await asyncpg.connect(TEST_DB_URL)
    tr = conn.transaction()
    await tr.start()
    await conn.execute(
        "SELECT set_config('app.current_school_id', $1, true)", SCHOOL_A_ID
    )
    yield conn
    await tr.rollback()
    await conn.close()


# ── Fixtures: seed schools and teachers ───────────────────────────────────────

async def _seed_schools(conn: asyncpg.Connection) -> None:
    """Insert School A and School B rows (bypass mode required)."""
    for school_id, email, name in [
        (SCHOOL_A_ID, "admin-a@school-a.test", "School A"),
        (SCHOOL_B_ID, "admin-b@school-b.test", "School B"),
    ]:
        await conn.execute(
            """
            INSERT INTO schools (id, name, contact_email, country, status)
            VALUES ($1, $2, $3, 'ZZ', 'active')
            ON CONFLICT (id) DO NOTHING
            """,
            school_id, name, email,
        )


async def _seed_teachers(conn: asyncpg.Connection) -> None:
    """Insert one teacher per school (bypass mode required)."""
    for teacher_id, school_id, email in [
        (TEACHER_A_ID, SCHOOL_A_ID, "teacher-a@school-a.test"),
        (TEACHER_B_ID, SCHOOL_B_ID, "teacher-b@school-b.test"),
    ]:
        await conn.execute(
            """
            INSERT INTO teachers (
                id, school_id, email, auth_provider, auth_provider_id,
                display_name, role, status
            )
            VALUES ($1, $2, $3, 'auth0', $3, 'Teacher', 'teacher', 'active')
            ON CONFLICT (id) DO NOTHING
            """,
            teacher_id, school_id, email,
        )


# ── Tests ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_schools_rls_select_isolation(bypass_conn, school_a_conn):
    """
    A teacher scoped to School A can SELECT their own school row but not School B's.
    """
    await _seed_schools(bypass_conn)

    # School A connection should see only School A.
    rows = await school_a_conn.fetch("SELECT id FROM schools WHERE id = ANY($1::uuid[])",
                                     [SCHOOL_A_ID, SCHOOL_B_ID])
    ids = {str(r["id"]) for r in rows}

    assert SCHOOL_A_ID in ids, "School A row must be visible to School A tenant"
    assert SCHOOL_B_ID not in ids, "School B row must be hidden from School A tenant"


@pytest.mark.asyncio
async def test_schools_rls_insert_blocked(bypass_conn, school_a_conn):
    """
    A tenant scoped to School A cannot INSERT a row with school_id = School B.
    """
    await _seed_schools(bypass_conn)

    with pytest.raises(asyncpg.exceptions.InsufficientPrivilegeError):
        await school_a_conn.execute(
            """
            INSERT INTO schools (id, name, contact_email, country, status)
            VALUES ($1, 'Evil School', 'evil@school-b.test', 'ZZ', 'active')
            """,
            SCHOOL_B_ID,
        )


@pytest.mark.asyncio
async def test_teachers_rls_select_isolation(bypass_conn, school_a_conn):
    """
    A teacher scoped to School A can SELECT teachers from School A only.
    """
    await _seed_schools(bypass_conn)
    await _seed_teachers(bypass_conn)

    rows = await school_a_conn.fetch(
        "SELECT id FROM teachers WHERE id = ANY($1::uuid[])",
        [TEACHER_A_ID, TEACHER_B_ID],
    )
    ids = {str(r["id"]) for r in rows}

    assert TEACHER_A_ID in ids, "School A teacher must be visible"
    assert TEACHER_B_ID not in ids, "School B teacher must be hidden"


@pytest.mark.asyncio
async def test_teachers_rls_insert_blocked(bypass_conn, school_a_conn):
    """
    A tenant scoped to School A cannot INSERT a teacher row belonging to School B.
    """
    await _seed_schools(bypass_conn)

    with pytest.raises(asyncpg.exceptions.InsufficientPrivilegeError):
        await school_a_conn.execute(
            """
            INSERT INTO teachers (
                id, school_id, email, auth_provider, auth_provider_id,
                display_name, role, status
            )
            VALUES (
                'c1000000-0000-0000-0000-000000000001',
                $1, 'intruder@school-b.test', 'auth0', 'intruder@school-b.test',
                'Intruder', 'teacher', 'active'
            )
            """,
            SCHOOL_B_ID,
        )


@pytest.mark.asyncio
async def test_bypass_sees_all_schools(bypass_conn):
    """
    The bypass context (admin / student / unauthenticated) can see all school rows.
    """
    await _seed_schools(bypass_conn)

    rows = await bypass_conn.fetch(
        "SELECT id FROM schools WHERE id = ANY($1::uuid[])",
        [SCHOOL_A_ID, SCHOOL_B_ID],
    )
    ids = {str(r["id"]) for r in rows}

    assert SCHOOL_A_ID in ids
    assert SCHOOL_B_ID in ids


@pytest.mark.asyncio
async def test_empty_school_id_denies_all(bypass_conn):
    """
    An empty string (unset variable) is denied by the RLS policy — no rows visible.
    """
    await _seed_schools(bypass_conn)

    # Open a fresh connection and set the variable to '' (empty = unset/erroneous path).
    conn = await asyncpg.connect(TEST_DB_URL)
    try:
        # Note: we do NOT bypass — use transaction-local empty string to simulate
        # a connection where the variable was never set (production safety check).
        tr = conn.transaction()
        await tr.start()
        await conn.execute("SELECT set_config('app.current_school_id', '', true)")

        rows = await conn.fetch(
            "SELECT id FROM schools WHERE id = ANY($1::uuid[])",
            [SCHOOL_A_ID, SCHOOL_B_ID],
        )
        assert rows == [], "Empty school_id must deny all rows (not bypass, not a valid UUID)"
        await tr.rollback()
    finally:
        await conn.close()
