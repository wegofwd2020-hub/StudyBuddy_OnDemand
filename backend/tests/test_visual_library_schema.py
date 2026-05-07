"""
Tests for migrations 0056+0057 + backend/src/visuals/library.py — issue #321 (319a).

Covers:
  - Schema invariants (CHECK constraints, indexes, defaults)
  - RLS policies (bypass writes; non-bypass reads non-archived only)
  - Soft-unique on s3_path among non-archived rows
  - Pydantic LibraryEntry model + library_path helpers
  - pgvector embedding column (512 dims) + ivfflat index + cosine query
  - compute_embedding() and embedding_text_for_entry() helpers
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


# ── Embedding column (migration 0057) ────────────────────────────────────────


@pytest.mark.asyncio
async def test_embedding_column_present(bypass_conn) -> None:
    """0057 added a `vector(512)` embedding column."""
    row = await bypass_conn.fetchrow(
        """
        SELECT data_type, udt_name
        FROM information_schema.columns
        WHERE table_name='visual_library_entries' AND column_name='embedding'
        """
    )
    assert row is not None
    assert row["udt_name"] == "vector"


@pytest.mark.asyncio
async def test_ivfflat_index_present(bypass_conn) -> None:
    """0057 created an ivfflat index on the embedding column."""
    name = await bypass_conn.fetchval(
        "SELECT indexname FROM pg_indexes WHERE indexname='vle_embedding_ivfflat_idx'"
    )
    assert name == "vle_embedding_ivfflat_idx"


@pytest.mark.asyncio
async def test_embedding_roundtrip_and_cosine_query(bypass_conn) -> None:
    """Insert two rows with distinct 512-d embeddings; cosine query
    returns them ranked by similarity to a probe vector."""

    # Construct two simple unit vectors that point in different directions
    # so cosine distance between them is well-defined and nonzero.
    e1 = [1.0] + [0.0] * 511
    e2 = [0.0] + [1.0] + [0.0] * 510
    probe = e1  # closer to e1 than e2

    rows = []
    for vec, slug in [(e1, "embed-rt-a.svg"), (e2, "embed-rt-b.svg")]:
        # asyncpg can't directly bind list[float] to vector — pgvector
        # accepts a string literal "[v1,v2,...]" cast to vector via ::vector
        vec_lit = "[" + ",".join(f"{x:.6f}" for x in vec) + "]"
        eid = await bypass_conn.fetchval(
            "INSERT INTO visual_library_entries "
            "(kind, subject, topic_phrase, s3_path, embedding) "
            "VALUES ('image', 'physics', 'roundtrip', $1, $2::vector) "
            "RETURNING entry_id",
            f"visual_library/physics/{slug}",
            vec_lit,
        )
        rows.append(eid)

    try:
        probe_lit = "[" + ",".join(f"{x:.6f}" for x in probe) + "]"
        ranked = await bypass_conn.fetch(
            """
            SELECT entry_id, s3_path, embedding <=> $1::vector AS cosine_distance
            FROM visual_library_entries
            WHERE entry_id = ANY($2::uuid[])
            ORDER BY embedding <=> $1::vector
            """,
            probe_lit,
            rows,
        )
        assert len(ranked) == 2
        # Probe == e1, so a is closer than b
        assert ranked[0]["s3_path"].endswith("embed-rt-a.svg")
        assert ranked[1]["s3_path"].endswith("embed-rt-b.svg")
        assert ranked[0]["cosine_distance"] < ranked[1]["cosine_distance"]
    finally:
        await bypass_conn.execute(
            "DELETE FROM visual_library_entries WHERE entry_id = ANY($1::uuid[])",
            rows,
        )


# ── compute_embedding() / embedding_text_for_entry() ────────────────────────


@pytest.mark.asyncio
async def test_compute_embedding_returns_none_without_key(monkeypatch) -> None:
    """compute_embedding() returns None when VOYAGE_API_KEY is empty —
    callers fall back to keyword search (or fail with a clear message)."""
    from config import settings

    from src.visuals.library import compute_embedding

    monkeypatch.setattr(settings, "VOYAGE_API_KEY", "", raising=False)
    out = await compute_embedding("projectile motion physics")
    assert out is None


def test_embedding_text_for_entry_shape() -> None:
    """The canonical embedding text is `topic_phrase + " " + keywords.join(" ")`."""
    from datetime import datetime

    from src.visuals.library import embedding_text_for_entry

    e = LibraryEntry(
        entry_id="x",
        kind="image",
        subject="physics",
        topic_phrase="projectile motion",
        keywords=["projectile", "trajectory", "parabola"],
        s3_path="visual_library/physics/projectile.svg",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    assert (
        embedding_text_for_entry(e)
        == "projectile motion projectile trajectory parabola"
    )


def test_embedding_dim_constant() -> None:
    from src.visuals.library import EMBEDDING_DIM

    assert EMBEDDING_DIM == 512
