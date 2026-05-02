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


async def fetch_curriculum_owner(conn: asyncpg.Connection, curriculum_id: str) -> dict | None:
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


async def unarchive_curriculum(conn: asyncpg.Connection, curriculum_id: str) -> dict:
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


# ── L-7: Archive view list ───────────────────────────────────────────────────


async def list_archived_curricula(
    conn: asyncpg.Connection,
    *,
    owner_type: str | None = None,
    school_id: str | None = None,
    grade: int | None = None,
    days_until_ttl_max: int | None = None,
) -> list[dict]:
    """
    Return all archived curricula platform-wide with optional filters.

    Joins schools for display name and laterally joins audit_log to surface
    the most recent archive event (actor, reason, timestamp) per row.
    The audit join covers both target_id-based entries (retention_router
    pattern) and metadata-based entries (lifecycle_router pattern).
    """
    import json as _json

    conditions = ["c.retention_status = 'archived'"]
    params: list = []

    if owner_type:
        params.append(owner_type)
        conditions.append(f"c.owner_type = ${len(params)}")
    if school_id:
        params.append(school_id)
        conditions.append(f"c.school_id = ${len(params)}::uuid")
    if grade is not None:
        params.append(grade)
        conditions.append(f"c.grade = ${len(params)}")
    if days_until_ttl_max is not None:
        params.append(days_until_ttl_max)
        conditions.append(
            f"c.expires_at <= NOW() + (${len(params)} * INTERVAL '1 day')"
        )

    where = " AND ".join(conditions)

    rows = await conn.fetch(
        f"""
        SELECT
            c.curriculum_id,
            c.owner_type,
            c.school_id::text            AS school_id,
            s.name                       AS school_name,
            c.grade,
            c.year,
            c.name,
            c.expires_at,
            GREATEST(
                0,
                EXTRACT(DAY FROM (c.expires_at - NOW()))::int
            )                            AS days_until_ttl,
            al.event_type                AS archive_event_type,
            al.actor_id::text            AS archived_by,
            al.timestamp                 AS archived_at,
            al.metadata                  AS archive_metadata
        FROM curricula c
        LEFT JOIN schools s ON s.school_id = c.school_id
        LEFT JOIN LATERAL (
            SELECT event_type, actor_id, timestamp, metadata
              FROM audit_log
             WHERE target_type = 'curriculum'
               AND (
                   target_id::text = c.curriculum_id
                   OR metadata->>'curriculum_id' = c.curriculum_id
               )
               AND event_type LIKE 'curriculum.archive%'
             ORDER BY timestamp DESC
             LIMIT 1
        ) al ON TRUE
        WHERE {where}
        ORDER BY c.expires_at ASC NULLS LAST
        """,
        *params,
    )

    result = []
    for r in rows:
        raw_meta = r["archive_metadata"]
        if isinstance(raw_meta, str):
            meta = _json.loads(raw_meta)
        elif raw_meta is None:
            meta = {}
        else:
            meta = dict(raw_meta)
        result.append({
            "curriculum_id": r["curriculum_id"],
            "owner_type": r["owner_type"],
            "school_id": r["school_id"],
            "school_name": r["school_name"],
            "grade": r["grade"],
            "year": r["year"],
            "name": r["name"],
            "expires_at": r["expires_at"].isoformat() if r["expires_at"] else None,
            "days_until_ttl": r["days_until_ttl"],
            "archive_event_type": r["archive_event_type"],
            "archived_by": r["archived_by"],
            "archived_at": r["archived_at"].isoformat() if r["archived_at"] else None,
            "archive_reason": meta.get("reason"),
        })
    return result
