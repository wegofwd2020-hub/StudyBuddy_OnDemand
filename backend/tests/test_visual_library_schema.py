"""
Tests for migration 0056 + backend/src/visuals/library.py — issue #321 (319a).

Covers:
  - Schema invariants (CHECK constraints, indexes, defaults)
  - RLS policies (bypass writes; non-bypass reads non-archived only)
  - Soft-unique on s3_path among non-archived rows
  - Pydantic LibraryEntry model + library_path helpers

The pgvector embedding column lands in a follow-up migration (0057);
embedding-related queries are out of scope here.
"""

from __future__ import annotations

import os
import uuid
from datetime import UTC

import asyncpg
import pytest
import pytest_asyncio

from src.visuals.library import (
    LIBRARY_PREFIX,
    SUBJECTS,
    LibraryEntry,
    library_path,
    metadata_path,
)

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


# ── Helpers / module-level pure functions ───────────────────────────────────


def test_library_path_format() -> None:
    assert (
        library_path("physics", "projectile-trajectory", "svg")
        == "visual_library/physics/projectile-trajectory.svg"
    )
    # Strip a leading dot if caller passed it
    assert library_path("math", "venn", ".svg") == "visual_library/math/venn.svg"


def test_metadata_path_format() -> None:
    assert (
        metadata_path("biology", "plant-cell")
        == "visual_library/biology/plant-cell.metadata.yaml"
    )


def test_library_prefix_constant() -> None:
    assert LIBRARY_PREFIX == "visual_library"


def test_subjects_is_closed_enum() -> None:
    assert "physics" in SUBJECTS
    assert "math" in SUBJECTS
    assert "rocketry" not in SUBJECTS  # not a subject in the closed list


def test_library_entry_pydantic_roundtrip() -> None:
    from datetime import datetime

    e = LibraryEntry(
        entry_id="abc",
        kind="image",
        subject="physics",
        topic_phrase="projectile motion",
        keywords=["projectile", "trajectory"],
        s3_path="visual_library/physics/projectile.svg",
        license="platform-cc-by-sa",
        source_unit="G11-PHYS-002",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    assert e.archived_at is None
    assert e.embedding is None  # placeholder until 0057 migration


def test_library_entry_rejects_bad_kind() -> None:
    from datetime import datetime
    with pytest.raises(Exception):  # pydantic ValidationError
        LibraryEntry(
            entry_id="abc",
            kind="not-a-real-kind",  # type: ignore[arg-type]
            subject="physics",
            topic_phrase="x",
            s3_path="visual_library/physics/x.svg",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )


# ── Live-DB tests (run against the test DB seeded by conftest) ──────────────


@pytest_asyncio.fixture
async def bypass_conn():
    """A direct asyncpg connection with app.current_school_id=bypass."""
    c = await asyncpg.connect(_TEST_DB_URL)
    await c.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
    yield c
    await c.close()


@pytest_asyncio.fixture
async def school_conn():
    """A direct asyncpg connection scoped to a fake school (non-bypass)."""
    c = await asyncpg.connect(_TEST_DB_URL)
    fake_school = str(uuid.uuid4())
    await c.execute(
        "SELECT set_config('app.current_school_id', $1, false)", fake_school
    )
    yield c
    await c.close()


@pytest.mark.asyncio
async def test_table_exists(bypass_conn) -> None:
    n = await bypass_conn.fetchval(
        "SELECT count(*) FROM information_schema.tables WHERE table_name='visual_library_entries'"
    )
    assert n == 1


@pytest.mark.asyncio
async def test_insert_select_roundtrip(bypass_conn) -> None:
    entry_id = await bypass_conn.fetchval(
        """
        INSERT INTO visual_library_entries
            (kind, subject, topic_phrase, keywords, s3_path, source_unit)
        VALUES ('image', 'physics', 'projectile motion',
                ARRAY['projectile','trajectory'],
                $1, 'G11-PHYS-002')
        RETURNING entry_id
        """,
        "visual_library/physics/projectile-rt.svg",
    )
    assert entry_id is not None

    row = await bypass_conn.fetchrow(
        "SELECT * FROM visual_library_entries WHERE entry_id = $1", entry_id
    )
    assert row["kind"] == "image"
    assert row["subject"] == "physics"
    assert row["keywords"] == ["projectile", "trajectory"]
    assert row["license"] == "platform-cc-by-sa"  # default
    assert row["archived_at"] is None
    assert row["created_at"] is not None

    # Cleanup
    await bypass_conn.execute(
        "DELETE FROM visual_library_entries WHERE entry_id = $1", entry_id
    )


@pytest.mark.asyncio
async def test_kind_check_constraint_rejects_invalid(bypass_conn) -> None:
    with pytest.raises(asyncpg.exceptions.CheckViolationError):
        await bypass_conn.execute(
            """
            INSERT INTO visual_library_entries (kind, subject, topic_phrase, s3_path)
            VALUES ('not-a-kind', 'physics', 'x', 'p.svg')
            """
        )


@pytest.mark.asyncio
async def test_unique_s3_path_among_active(bypass_conn) -> None:
    """Soft-unique: two active rows can't share the same s3_path."""
    s3_path = "visual_library/physics/dup-test.svg"
    e1 = await bypass_conn.fetchval(
        "INSERT INTO visual_library_entries (kind, subject, topic_phrase, s3_path) "
        "VALUES ('image', 'physics', 'a', $1) RETURNING entry_id",
        s3_path,
    )
    try:
        with pytest.raises(asyncpg.exceptions.UniqueViolationError):
            await bypass_conn.execute(
                "INSERT INTO visual_library_entries (kind, subject, topic_phrase, s3_path) "
                "VALUES ('image', 'physics', 'b', $1)",
                s3_path,
            )
        # Archive the first; second insert now succeeds (partial index excludes archived)
        await bypass_conn.execute(
            "UPDATE visual_library_entries SET archived_at = now() WHERE entry_id = $1",
            e1,
        )
        e2 = await bypass_conn.fetchval(
            "INSERT INTO visual_library_entries (kind, subject, topic_phrase, s3_path) "
            "VALUES ('image', 'physics', 'b', $1) RETURNING entry_id",
            s3_path,
        )
        await bypass_conn.execute(
            "DELETE FROM visual_library_entries WHERE entry_id = $1", e2
        )
    finally:
        await bypass_conn.execute(
            "DELETE FROM visual_library_entries WHERE entry_id = $1", e1
        )


@pytest.mark.asyncio
async def test_rls_school_can_read_non_archived(bypass_conn, school_conn) -> None:
    """Non-bypass session can SELECT non-archived rows."""
    e = await bypass_conn.fetchval(
        "INSERT INTO visual_library_entries (kind, subject, topic_phrase, s3_path) "
        "VALUES ('image', 'physics', 'rls-active', $1) RETURNING entry_id",
        "visual_library/physics/rls-active.svg",
    )
    try:
        n = await school_conn.fetchval(
            "SELECT count(*) FROM visual_library_entries WHERE entry_id = $1",
            e,
        )
        assert n == 1
    finally:
        await bypass_conn.execute(
            "DELETE FROM visual_library_entries WHERE entry_id = $1", e
        )


@pytest.mark.asyncio
async def test_rls_school_cannot_read_archived(bypass_conn, school_conn) -> None:
    """Archived rows are hidden from non-bypass sessions."""
    e = await bypass_conn.fetchval(
        "INSERT INTO visual_library_entries (kind, subject, topic_phrase, s3_path, archived_at) "
        "VALUES ('image', 'physics', 'rls-archived', $1, now()) RETURNING entry_id",
        "visual_library/physics/rls-archived.svg",
    )
    try:
        n = await school_conn.fetchval(
            "SELECT count(*) FROM visual_library_entries WHERE entry_id = $1",
            e,
        )
        assert n == 0
    finally:
        await bypass_conn.execute(
            "DELETE FROM visual_library_entries WHERE entry_id = $1", e
        )


@pytest.mark.asyncio
async def test_rls_school_cannot_write(school_conn) -> None:
    """Non-bypass session cannot INSERT — RLS write policy blocks."""
    # asyncpg surfaces this as either a permission error or zero rows changed
    # depending on the postgres setting; pgsql 16 raises insufficient_privilege.
    with pytest.raises(Exception):
        await school_conn.execute(
            "INSERT INTO visual_library_entries (kind, subject, topic_phrase, s3_path) "
            "VALUES ('image', 'physics', 'should-fail', 'visual_library/x.svg')"
        )
