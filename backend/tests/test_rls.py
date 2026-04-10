"""
backend/tests/test_rls.py

Row-Level Security isolation tests (migration 0028).

Proves that a tenant scoped to School A cannot read or write School B's rows,
and that the RLS policy is enforced at the DB layer regardless of application
behaviour.

Strategy
--------
All tests use a SINGLE asyncpg connection.  Within one rolled-back transaction:

  1. SET LOCAL ROLE to a non-superuser role so RLS policies are enforced.
     (studybuddy is a superuser and bypasses RLS even with FORCE ROW LEVEL
     SECURITY — PostgreSQL does not apply RLS to superusers regardless of
     the FORCE flag.)
  2. Set app.current_school_id = 'bypass', insert Schools A + B (and teachers).
  3. Switch app.current_school_id to School A's UUID.
  4. Assert School B rows are invisible; School A rows visible.
  5. For insert-blocked tests: attempt INSERT with wrong school_id → expect error.

Using a single connection avoids the committed-visibility problem: rows inserted
in the current transaction are visible to subsequent queries on the same
connection.  set_config(..., true) is transaction-local so switching between
bypass/school_a/empty within the same transaction takes effect immediately.

Fixed UUIDs follow Rule 9 (deterministic IDs in fixtures).
"""

from __future__ import annotations

import os

import pytest
import pytest_asyncio
import asyncpg

# ── Deterministic fixture IDs (Rule 9) ────────────────────────────────────────

SCHOOL_A_ID = "a0000000-0000-0000-0000-000000000001"
SCHOOL_B_ID = "b0000000-0000-0000-0000-000000000002"  # distinct B suffix

TEACHER_A_ID = "a1000000-0000-0000-0000-000000000001"
TEACHER_B_ID = "b1000000-0000-0000-0000-000000000002"

# Non-superuser role used for RLS enforcement.  Created once per session.
_RLS_ROLE = "studybuddy_rls_tester"

# RLS tests connect directly to the test DB (bypasses PgBouncer so set_config
# persists within the transaction).  TEST_DB_URL points to studybuddy_test;
# fall back to DIRECT_DB_URL (dev DB, direct) if TEST_DB_URL is absent.
_dev_url = os.environ.get("DATABASE_URL", "postgresql://studybuddy:studybuddy_dev@db:5432/studybuddy")
_direct_dev_url = _dev_url.replace("@pgbouncer:", "@db:")
_default_test_url = _direct_dev_url.replace("/studybuddy", "/studybuddy_test")
TEST_DB_URL = os.environ.get("TEST_DB_URL", os.environ.get("DIRECT_DB_URL", _default_test_url))


# ── Session-scoped: ensure non-superuser role exists ─────────────────────────


@pytest.fixture(scope="session")
def rls_role_setup():
    """
    Create a non-superuser DB role for RLS testing (synchronous, session-scoped).

    studybuddy is a PostgreSQL superuser, so it bypasses RLS even with
    FORCE ROW LEVEL SECURITY.  All RLS tests must run under a role that
    does NOT have the SUPERUSER attribute, or the policies are never
    applied.

    This fixture creates studybuddy_rls_tester (if absent) and grants
    it full table access.  The role persists between test runs (DDL cannot
    be rolled back within the per-test transaction).

    Synchronous implementation avoids event-loop scope conflicts when
    pytest-asyncio runs in AUTO mode across multiple test modules.
    """
    import asyncio

    async def _setup() -> None:
        conn = await asyncpg.connect(TEST_DB_URL)
        try:
            await conn.execute(f"""
                DO $$ BEGIN
                    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{_RLS_ROLE}') THEN
                        CREATE ROLE {_RLS_ROLE};
                    END IF;
                END $$
            """)
            await conn.execute(f"GRANT ALL ON ALL TABLES IN SCHEMA public TO {_RLS_ROLE}")
            await conn.execute(f"GRANT USAGE ON SCHEMA public TO {_RLS_ROLE}")
        finally:
            await conn.close()

    loop = asyncio.new_event_loop()
    loop.run_until_complete(_setup())
    loop.close()


# ── Single-connection fixture ─────────────────────────────────────────────────


@pytest_asyncio.fixture
async def rls_conn(rls_role_setup):
    """
    Raw asyncpg connection running as a non-superuser role, wrapped in a
    rolled-back transaction.

    SET LOCAL ROLE switches to studybuddy_rls_tester for the duration of
    the transaction; RLS policies are then enforced by the DB engine.
    Tests switch app.current_school_id to simulate different tenant scopes.
    All INSERTs are rolled back on teardown.
    """
    conn = await asyncpg.connect(TEST_DB_URL, timeout=10, command_timeout=10)
    tr = conn.transaction()
    await tr.start()
    # Switch to non-superuser role — RLS is now enforced.
    await conn.execute(f"SET LOCAL ROLE {_RLS_ROLE}")
    # Start in bypass mode so seed helpers can insert cross-school rows.
    await conn.execute("SELECT set_config('app.current_school_id', 'bypass', true)")
    try:
        yield conn
    finally:
        await tr.rollback()
        await conn.close()


# ── Seed helpers ──────────────────────────────────────────────────────────────


async def _seed_schools(conn: asyncpg.Connection) -> None:
    """Insert School A and School B (bypass mode must be active)."""
    for school_id, email, name in [
        (SCHOOL_A_ID, "rls-admin-a@school-a.test", "School A"),
        (SCHOOL_B_ID, "rls-admin-b@school-b.test", "School B"),
    ]:
        await conn.execute(
            """
            INSERT INTO schools (school_id, name, contact_email, country, status)
            VALUES ($1, $2, $3, 'ZZ', 'active')
            ON CONFLICT (school_id) DO NOTHING
            """,
            school_id, name, email,
        )


async def _seed_teachers(conn: asyncpg.Connection) -> None:
    """Insert one teacher per school (bypass mode must be active)."""
    for teacher_id, school_id, email in [
        (TEACHER_A_ID, SCHOOL_A_ID, "rls-teacher-a@school-a.test"),
        (TEACHER_B_ID, SCHOOL_B_ID, "rls-teacher-b@school-b.test"),
    ]:
        await conn.execute(
            """
            INSERT INTO teachers (
                teacher_id, school_id, email, auth_provider, external_auth_id,
                name, role, account_status
            )
            VALUES ($1, $2, $3, 'auth0', $3, 'Teacher', 'teacher', 'active')
            ON CONFLICT (teacher_id) DO NOTHING
            """,
            teacher_id, school_id, email,
        )


# ── Tests ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_schools_rls_select_isolation(rls_conn):
    """
    A tenant scoped to School A can SELECT its own school row but not School B's.
    """
    # Seed both schools while in bypass mode.
    await _seed_schools(rls_conn)

    # Switch to School A scope.
    await rls_conn.execute(
        "SELECT set_config('app.current_school_id', $1, true)", SCHOOL_A_ID
    )

    rows = await rls_conn.fetch(
        "SELECT school_id FROM schools WHERE school_id = ANY($1::uuid[])",
        [SCHOOL_A_ID, SCHOOL_B_ID],
    )
    ids = {str(r["school_id"]) for r in rows}

    assert SCHOOL_A_ID in ids, "School A row must be visible to School A tenant"
    assert SCHOOL_B_ID not in ids, "School B row must be hidden from School A tenant"


@pytest.mark.asyncio
async def test_schools_rls_insert_blocked(rls_conn):
    """
    A tenant scoped to School A cannot INSERT a row with school_id = School B.
    """
    await _seed_schools(rls_conn)

    # Switch to School A scope.
    await rls_conn.execute(
        "SELECT set_config('app.current_school_id', $1, true)", SCHOOL_A_ID
    )

    with pytest.raises(asyncpg.exceptions.InsufficientPrivilegeError):
        await rls_conn.execute(
            """
            INSERT INTO schools (school_id, name, contact_email, country, status)
            VALUES ($1, 'Evil School', 'rls-evil@school-b.test', 'ZZ', 'active')
            """,
            SCHOOL_B_ID,
        )


@pytest.mark.asyncio
async def test_teachers_rls_select_isolation(rls_conn):
    """
    A tenant scoped to School A can SELECT teachers from School A only.
    """
    await _seed_schools(rls_conn)
    await _seed_teachers(rls_conn)

    # Switch to School A scope.
    await rls_conn.execute(
        "SELECT set_config('app.current_school_id', $1, true)", SCHOOL_A_ID
    )

    rows = await rls_conn.fetch(
        "SELECT teacher_id FROM teachers WHERE teacher_id = ANY($1::uuid[])",
        [TEACHER_A_ID, TEACHER_B_ID],
    )
    ids = {str(r["teacher_id"]) for r in rows}

    assert TEACHER_A_ID in ids, "School A teacher must be visible"
    assert TEACHER_B_ID not in ids, "School B teacher must be hidden"


@pytest.mark.asyncio
async def test_teachers_rls_insert_blocked(rls_conn):
    """
    A tenant scoped to School A cannot INSERT a teacher row belonging to School B.
    """
    await _seed_schools(rls_conn)

    # Switch to School A scope.
    await rls_conn.execute(
        "SELECT set_config('app.current_school_id', $1, true)", SCHOOL_A_ID
    )

    with pytest.raises(asyncpg.exceptions.InsufficientPrivilegeError):
        await rls_conn.execute(
            """
            INSERT INTO teachers (
                teacher_id, school_id, email, auth_provider, external_auth_id,
                name, role, account_status
            )
            VALUES (
                'c1000000-0000-0000-0000-000000000001',
                $1, 'rls-intruder@school-b.test', 'auth0', 'rls-intruder@school-b.test',
                'Intruder', 'teacher', 'active'
            )
            """,
            SCHOOL_B_ID,
        )


@pytest.mark.asyncio
async def test_bypass_sees_all_schools(rls_conn):
    """
    The bypass context (admin / student / unauthenticated) can see all school rows.
    """
    await _seed_schools(rls_conn)

    # Still in bypass mode — no scope switch needed.
    rows = await rls_conn.fetch(
        "SELECT school_id FROM schools WHERE school_id = ANY($1::uuid[])",
        [SCHOOL_A_ID, SCHOOL_B_ID],
    )
    ids = {str(r["school_id"]) for r in rows}

    assert SCHOOL_A_ID in ids
    assert SCHOOL_B_ID in ids


@pytest.mark.asyncio
async def test_empty_school_id_denies_all(rls_conn):
    """
    An empty string (unset variable) is denied by the RLS policy — no rows visible.
    """
    await _seed_schools(rls_conn)

    # Switch to empty string — simulates a connection where the variable was never set.
    await rls_conn.execute("SELECT set_config('app.current_school_id', '', true)")

    rows = await rls_conn.fetch(
        "SELECT school_id FROM schools WHERE school_id = ANY($1::uuid[])",
        [SCHOOL_A_ID, SCHOOL_B_ID],
    )
    assert rows == [], "Empty school_id must deny all rows (not bypass, not a valid UUID)"
