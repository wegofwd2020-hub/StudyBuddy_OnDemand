"""A per-unit rebuild must leave a DB record (#751).

`pipeline/build_unit.py` performed no DB writes at all. Only
`pipeline/build_grade.py` wrote `curriculum_units` and
`content_subject_versions`, so regenerating a single unit changed what a
student reads while leaving no trace anywhere in the database.

The sharp end of that: `check_content_published`
(`backend/src/content/service.py`) serves a subject only when SOME row exists
for it with `status='published'`, and `backend/src/content/router.py` 404s
otherwise. Content produced only by `build_unit.py` had no row, so it could
never enter the review -> publish flow at all. Existing curricula were spared
only because an older `build_grade` run had left v1 rows behind.

These run against the real test database rather than mocks, because every
historical failure in this area was the DATABASE rejecting a write that the
code believed had succeeded (pitfalls #28, #29, #30). A mocked connection
would have accepted all three.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime

import pytest

_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)

from pipeline.db_writes import (  # noqa: E402
    create_subject_version,
    record_unit_build,
    resolve_subject,
    upsert_single_unit,
)

CURRICULUM = "test-2026-g11-science"
SUBJECT = "G11-PHY"
SUBJECT_NAME = "Physics"


async def _seed_curriculum(conn) -> None:
    await conn.execute(
        """
        INSERT INTO curricula (curriculum_id, grade, year, name, is_default)
        VALUES ($1, 11, 2026, 'Test G11 Science', false)
        ON CONFLICT (curriculum_id) DO NOTHING
        """,
        CURRICULUM,
    )


async def _versions(conn) -> list[dict]:
    rows = await conn.fetch(
        """
        SELECT version_number, status, subject_name, generated_at, published_at,
               provider, pipeline_run_id, alex_warnings_count
        FROM content_subject_versions
        WHERE curriculum_id = $1 AND subject = $2
        ORDER BY version_number
        """,
        CURRICULUM,
        SUBJECT,
    )
    return [dict(r) for r in rows]


# ── curriculum_units ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_a_unit_row_is_created_with_unit_name(db_conn):
    """`unit_name` is NOT NULL; omitting it fails every row silently (#30)."""
    await _seed_curriculum(db_conn)
    await upsert_single_unit(
        db_conn, CURRICULUM, SUBJECT, {"unit_id": "G11-PHY-001", "title": "Kinematics"}
    )

    row = await db_conn.fetchrow(
        "SELECT title, unit_name, sort_order FROM curriculum_units "
        "WHERE curriculum_id = $1 AND unit_id = $2",
        CURRICULUM,
        "G11-PHY-001",
    )
    assert row is not None, "the unit row was not written"
    assert row["unit_name"] == "Kinematics"
    assert row["title"] == "Kinematics"


@pytest.mark.asyncio
async def test_a_second_unit_is_appended_not_stacked_at_zero(db_conn):
    """The bulk helper numbers from 0, which is wrong when adding to a subject."""
    await _seed_curriculum(db_conn)
    await upsert_single_unit(db_conn, CURRICULUM, SUBJECT, {"unit_id": "G11-PHY-001"})
    await upsert_single_unit(db_conn, CURRICULUM, SUBJECT, {"unit_id": "G11-PHY-002"})

    rows = await db_conn.fetch(
        "SELECT unit_id, sort_order FROM curriculum_units "
        "WHERE curriculum_id = $1 AND subject = $2 ORDER BY sort_order",
        CURRICULUM,
        SUBJECT,
    )
    assert [r["sort_order"] for r in rows] == [0, 1]


@pytest.mark.asyncio
async def test_rebuilding_the_same_unit_does_not_duplicate_it(db_conn):
    await _seed_curriculum(db_conn)
    for _ in range(3):
        await upsert_single_unit(db_conn, CURRICULUM, SUBJECT, {"unit_id": "G11-PHY-001"})
    count = await db_conn.fetchval(
        "SELECT COUNT(*) FROM curriculum_units WHERE curriculum_id = $1 AND unit_id = $2",
        CURRICULUM,
        "G11-PHY-001",
    )
    assert count == 1


# ── resolve_subject ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_subject_is_resolved_from_the_existing_unit(db_conn):
    """`--subject` defaults to "" and every real invocation omitted it."""
    await _seed_curriculum(db_conn)
    await upsert_single_unit(db_conn, CURRICULUM, SUBJECT, {"unit_id": "G11-PHY-001"})
    assert await resolve_subject(db_conn, CURRICULUM, "G11-PHY-001") == SUBJECT


@pytest.mark.asyncio
async def test_an_unknown_unit_resolves_to_none_rather_than_a_guess(db_conn):
    """A wrong subject would file the content under the wrong heading."""
    await _seed_curriculum(db_conn)
    assert await resolve_subject(db_conn, CURRICULUM, "G11-PHY-999") is None


# ── content_subject_versions ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_the_first_build_creates_a_version(db_conn):
    """The whole defect: content with no row here can never be published."""
    await _seed_curriculum(db_conn)
    assert await _versions(db_conn) == []

    version, how = await record_unit_build(
        db_conn, CURRICULUM, SUBJECT, SUBJECT_NAME, 0, False, "run-1"
    )

    assert (version, how) == (1, "created")
    rows = await _versions(db_conn)
    assert len(rows) == 1
    assert rows[0]["status"] == "pending"
    assert rows[0]["subject_name"] == SUBJECT_NAME


@pytest.mark.asyncio
async def test_a_regen_sweep_produces_exactly_one_version(db_conn):
    """The reason this joins instead of incrementing.

    The #745 regen rebuilt 29 units of one science curriculum. A version per
    unit would have produced 29 "Physics" versions and buried the review queue.
    """
    await _seed_curriculum(db_conn)
    for n in range(1, 30):
        await record_unit_build(
            db_conn, CURRICULUM, SUBJECT, SUBJECT_NAME, 0, False, f"run-{n}"
        )

    rows = await _versions(db_conn)
    assert len(rows) == 1, f"expected one version for the sweep, got {len(rows)}"
    assert rows[0]["version_number"] == 1


@pytest.mark.asyncio
async def test_joining_leaves_the_reviewer_s_fields_alone(db_conn):
    """A single unit is not entitled to restate subject-level facts."""
    await _seed_curriculum(db_conn)
    await record_unit_build(db_conn, CURRICULUM, SUBJECT, SUBJECT_NAME, 7, False, "run-1")
    before = (await _versions(db_conn))[0]

    version, how = await record_unit_build(
        db_conn, CURRICULUM, SUBJECT, SUBJECT_NAME, 0, False, "run-2"
    )
    after = (await _versions(db_conn))[0]

    assert how == "joined" and version == before["version_number"]
    assert after["status"] == before["status"]
    # The subject-wide warning count is not overwritten by one unit's zero.
    assert after["alex_warnings_count"] == 7
    assert after["generated_at"] >= before["generated_at"]
    assert after["pipeline_run_id"] == "run-2"


@pytest.mark.asyncio
async def test_a_reviewed_version_is_never_mutated(db_conn):
    """Once someone has acted on a version, a rebuild opens a new one."""
    await _seed_curriculum(db_conn)
    await record_unit_build(db_conn, CURRICULUM, SUBJECT, SUBJECT_NAME, 0, False, "run-1")
    await db_conn.execute(
        "UPDATE content_subject_versions SET status = 'published' "
        "WHERE curriculum_id = $1 AND subject = $2 AND version_number = 1",
        CURRICULUM,
        SUBJECT,
    )

    version, how = await record_unit_build(
        db_conn, CURRICULUM, SUBJECT, SUBJECT_NAME, 0, False, "run-2"
    )

    assert (version, how) == (2, "created")
    rows = await _versions(db_conn)
    assert [r["version_number"] for r in rows] == [1, 2]
    assert rows[0]["status"] == "published", "the published version must be untouched"


@pytest.mark.asyncio
async def test_published_at_is_bound_as_a_datetime(db_conn):
    """Pitfall #29: an ISO *string* fails the INSERT and used to be swallowed."""
    await _seed_curriculum(db_conn)
    await record_unit_build(
        db_conn, CURRICULUM, SUBJECT, SUBJECT_NAME, 0, True, "run-1"
    )
    row = (await _versions(db_conn))[0]
    assert row["status"] == "published"
    assert isinstance(row["published_at"], datetime)


@pytest.mark.asyncio
async def test_build_grade_still_always_opens_a_new_version(db_conn):
    """A whole-subject build is a new version by definition -- unchanged by #751."""
    await _seed_curriculum(db_conn)
    first = await create_subject_version(
        db_conn, CURRICULUM, SUBJECT, SUBJECT_NAME, 0, False, "grade-run-1"
    )
    second = await create_subject_version(
        db_conn, CURRICULUM, SUBJECT, SUBJECT_NAME, 0, False, "grade-run-2"
    )
    assert (first, second) == (1, 2), "build_grade must not start joining versions"
