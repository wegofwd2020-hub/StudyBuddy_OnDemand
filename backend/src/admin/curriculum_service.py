"""
backend/src/admin/curriculum_service.py

Shared curriculum lifecycle helpers — Epic 10 L-2 and onwards.

The canonical "is this curriculum actively in use" check lives here so archive
pre-conditions (L-4), the usage endpoint, and future admin tooling all agree
on the same definition.

"In use" definition (from Q2 resolution):
    Active student enrolments at a (school, grade) pair that's mapped to this
    curriculum via `grade_curriculum_assignments`. Historical assignments —
    rows where `school_enrolments.status != 'active'` — do NOT count.
"""

from __future__ import annotations

from typing import TypedDict

import asyncpg


class CurriculumUsageSummary(TypedDict):
    curriculum_id: str
    active_students: int
    active_teachers: int
    schools_assigned: int
    in_use: bool


async def is_curriculum_in_use(conn: asyncpg.Connection, curriculum_id: str) -> bool:
    """
    Return True if any active student is enrolled at a (school, grade) mapped
    to this curriculum via `grade_curriculum_assignments`.

    Q2 resolution: active status only — historical enrolments don't block
    archival of superseded curricula.
    """
    return bool(
        await conn.fetchval(
            """
            SELECT EXISTS (
                SELECT 1
                  FROM grade_curriculum_assignments gca
                  JOIN school_enrolments se
                    ON se.school_id = gca.school_id
                   AND se.grade = gca.grade
                   AND se.status = 'active'
                   AND se.student_id IS NOT NULL
                 WHERE gca.curriculum_id = $1
            )
            """,
            curriculum_id,
        )
    )


async def get_curriculum_usage_summary(
    conn: asyncpg.Connection, curriculum_id: str
) -> CurriculumUsageSummary:
    """
    Return counts used by the admin usage endpoint + archive confirmation
    dialogs. A zero across all three counters is equivalent to
    `is_curriculum_in_use=False`.
    """
    row = await conn.fetchrow(
        """
        WITH in_use AS (
            SELECT gca.school_id, gca.grade
              FROM grade_curriculum_assignments gca
             WHERE gca.curriculum_id = $1
        )
        SELECT
            (SELECT COUNT(DISTINCT se.student_id)
               FROM school_enrolments se
               JOIN in_use iu ON iu.school_id = se.school_id AND iu.grade = se.grade
              WHERE se.status = 'active' AND se.student_id IS NOT NULL) AS active_students,
            (SELECT COUNT(DISTINCT sta.teacher_id)
               FROM student_teacher_assignments sta
               JOIN in_use iu ON iu.school_id = sta.school_id AND iu.grade = sta.grade
               JOIN school_enrolments se
                 ON se.student_id = sta.student_id AND se.status = 'active') AS active_teachers,
            (SELECT COUNT(*) FROM in_use) AS schools_assigned
        """,
        curriculum_id,
    )
    active_students = int(row["active_students"] or 0)
    active_teachers = int(row["active_teachers"] or 0)
    schools_assigned = int(row["schools_assigned"] or 0)
    return {
        "curriculum_id": curriculum_id,
        "active_students": active_students,
        "active_teachers": active_teachers,
        "schools_assigned": schools_assigned,
        "in_use": active_students > 0,
    }


async def fetch_curriculum_owner(
    conn: asyncpg.Connection, curriculum_id: str
) -> dict | None:
    """Return owner_type / owner_id / school_id for a curriculum, or None if absent."""
    row = await conn.fetchrow(
        """
        SELECT curriculum_id, owner_type, owner_id, school_id, grade, year, name,
               retention_status, expires_at
          FROM curricula
         WHERE curriculum_id = $1
        """,
        curriculum_id,
    )
    return dict(row) if row else None


# ── Archive preconditions ────────────────────────────────────────────────────

class ArchiveBlocker(Exception):
    """Raised when an archive pre-condition isn't met."""

    def __init__(self, code: str, detail: str):
        self.code = code
        self.detail = detail
        super().__init__(detail)


async def assert_archivable(conn: asyncpg.Connection, curriculum_id: str) -> dict:
    """
    Verify the curriculum can be archived per Epic 10 L-4 rules.

    Raises ArchiveBlocker on any failed pre-condition. Returns the curriculum
    row on success so callers don't re-fetch.
    """
    row = await fetch_curriculum_owner(conn, curriculum_id)
    if not row:
        raise ArchiveBlocker("not_found", f"Curriculum '{curriculum_id}' not found.")

    if row["retention_status"] == "archived":
        raise ArchiveBlocker(
            "already_archived",
            f"Curriculum '{curriculum_id}' is already archived.",
        )

    if await is_curriculum_in_use(conn, curriculum_id):
        raise ArchiveBlocker(
            "in_use",
            f"Curriculum '{curriculum_id}' still has active student assignments. "
            "Unassign them before archiving.",
        )

    # "Either at least one version has been published OR no versions exist."
    version_count = await conn.fetchval(
        "SELECT COUNT(*) FROM content_subject_versions WHERE curriculum_id = $1",
        curriculum_id,
    )
    if version_count:
        published_count = await conn.fetchval(
            """
            SELECT COUNT(*)
              FROM content_subject_versions
             WHERE curriculum_id = $1
               AND status = 'published'
            """,
            curriculum_id,
        )
        if not published_count:
            raise ArchiveBlocker(
                "no_published_version",
                f"Curriculum '{curriculum_id}' has versions but none are published. "
                "Publish a version first or build without uploading to archive an empty shell.",
            )

    return row


# ── Archive / unarchive mutators ────────────────────────────────────────────


async def archive_curriculum(
    conn: asyncpg.Connection,
    *,
    curriculum_id: str,
    ttl_days: int = 365,
) -> dict:
    """
    Flip a curriculum to retention_status='archived' with expires_at set to
    now + ttl_days. Does NOT enforce pre-conditions — the caller must run
    assert_archivable first.

    Returns the updated row.
    """
    row = await conn.fetchrow(
        """
        UPDATE curricula
           SET retention_status = 'archived',
               expires_at = now() + ($2 || ' days')::interval
         WHERE curriculum_id = $1
        RETURNING curriculum_id, owner_type, owner_id, school_id,
                  retention_status, expires_at
        """,
        curriculum_id,
        str(ttl_days),
    )
    return dict(row) if row else {}


async def unarchive_curriculum(
    conn: asyncpg.Connection, curriculum_id: str
) -> dict:
    """Reverse archive: retention_status='active', clear expires_at."""
    row = await conn.fetchrow(
        """
        UPDATE curricula
           SET retention_status = 'active',
               expires_at = NULL
         WHERE curriculum_id = $1
           AND retention_status = 'archived'
        RETURNING curriculum_id, owner_type, owner_id, school_id,
                  retention_status, expires_at
        """,
        curriculum_id,
    )
    return dict(row) if row else {}
