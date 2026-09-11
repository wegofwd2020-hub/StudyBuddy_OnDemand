"""Database writes shared by the two pipeline entry points.

`build_grade.py` and `build_unit.py` both produce content, but only
`build_grade.py` ever recorded it. `build_unit.py` performed no writes at all,
so a per-unit rebuild updated what a student reads while leaving no DB trace
(#751). This module is the single place those writes live, so the two entry
points cannot drift apart again -- and it cannot live in either of them,
because `build_grade` imports `build_unit`.

Three pitfalls have each caused this class of write to fail SILENTLY, writing
content to disk while leaving the DB untouched. They are the reason the
helpers here are small and explicit:

  #28  Platform-owner writes need `app.current_school_id = 'bypass'` set on the
       connection, or the RESTRICTIVE RLS added in migration 0046 rejects them.
       `connect_with_bypass` is the only sanctioned way to open a connection.
  #29  `published_at` is TIMESTAMPTZ -- asyncpg requires a `datetime`, and the
       ISO *string* used for JSON serialisation fails the INSERT.
  #30  `curriculum_units.unit_name` is NOT NULL; omitting it fails every row.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

log = logging.getLogger("pipeline.db_writes")

# A version row that is still `pending` has not been reviewed yet, so a further
# unit rebuild belongs to it rather than to a new version. Any other status
# means someone has acted on it and it must not be mutated.
_OPEN_STATUS = "pending"


async def connect_with_bypass(database_url: str) -> Any:
    """Open an asyncpg connection able to write platform-owned rows.

    The `SET` is not optional. Without it, migration 0046's RESTRICTIVE policy
    refuses INSERT/UPDATE on `curricula` for `owner_type='platform'` rows and
    the caller sees only a generic error -- pitfall #28.
    """
    import asyncpg  # imported here so the module is importable without the driver

    conn = await asyncpg.connect(database_url)
    await conn.execute("SET app.current_school_id = 'bypass'")
    return conn


async def resolve_subject(conn: Any, curriculum_id: str, unit_id: str) -> str | None:
    """The subject code a unit belongs to, or None if the unit is unknown.

    `build_unit.py --subject` defaults to an empty string and every historical
    invocation has omitted it, so the subject has to come from the row that
    already exists. `content_subject_versions` is keyed on this value, so
    guessing it would attach content to the wrong subject.
    """
    row = await conn.fetchrow(
        "SELECT subject FROM curriculum_units WHERE curriculum_id = $1 AND unit_id = $2",
        curriculum_id,
        unit_id,
    )
    return row["subject"] if row else None


async def upsert_curriculum_units(
    conn: Any,
    curriculum_id: str,
    subject_id: str,
    units: list[dict],
) -> None:
    """Upsert `curriculum_units` rows for a subject.

    `unit_name` is NOT NULL per the Phase-8 schema. We mirror `title` into it --
    the same value -- because the source grade data files carry one field per
    unit (`title`) while the table evolved to hold both a long-form title and a
    short unique name. Omitting it fails the INSERT silently and leaves the
    admin review queue showing empty unit lists over content that is on disk.
    Pitfall #30.
    """
    for sort_order, unit in enumerate(units):
        title = unit.get("title", unit["unit_id"])
        await conn.execute(
            """
            INSERT INTO curriculum_units
                (unit_id, curriculum_id, subject, title, unit_name,
                 description, has_lab, sort_order)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            ON CONFLICT (unit_id, curriculum_id) DO NOTHING
            """,
            unit["unit_id"],
            curriculum_id,
            subject_id,
            title,
            title,  # unit_name — same as title for platform-seeded curricula
            unit.get("description", ""),
            unit.get("has_lab", False),
            sort_order,
        )


async def upsert_single_unit(
    conn: Any,
    curriculum_id: str,
    subject_id: str,
    unit: dict,
) -> None:
    """`upsert_curriculum_units` for one unit, appended after any existing rows.

    Separate because the bulk form numbers `sort_order` from zero, which is
    correct when it owns the whole subject and wrong when adding to it.
    """
    row = await conn.fetchrow(
        """
        SELECT COALESCE(MAX(sort_order), -1) AS max_order
        FROM curriculum_units WHERE curriculum_id = $1 AND subject = $2
        """,
        curriculum_id,
        subject_id,
    )
    next_order = (row["max_order"] if row else -1) + 1
    title = unit.get("title") or unit["unit_id"]
    await conn.execute(
        """
        INSERT INTO curriculum_units
            (unit_id, curriculum_id, subject, title, unit_name,
             description, has_lab, sort_order)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        ON CONFLICT (unit_id, curriculum_id) DO NOTHING
        """,
        unit["unit_id"],
        curriculum_id,
        subject_id,
        title,
        title,
        unit.get("description", ""),
        unit.get("has_lab", False),
        next_order,
    )


async def _next_version_number(conn: Any, curriculum_id: str, subject: str) -> int:
    row = await conn.fetchrow(
        """
        SELECT COALESCE(MAX(version_number), 0) AS max_ver
        FROM content_subject_versions
        WHERE curriculum_id = $1 AND subject = $2
        """,
        curriculum_id,
        subject,
    )
    return (row["max_ver"] or 0) + 1


async def create_subject_version(
    conn: Any,
    curriculum_id: str,
    subject: str,
    subject_name: str,
    alex_warnings: int,
    auto_approve: bool,
    pipeline_run_id: str,
    provider: str = "anthropic",
) -> int:
    """Record a NEW version of a subject's content. Used by `build_grade`.

    A whole-subject build is a new version by definition, so this always takes
    the next version number. Returns that number.
    """
    status = "pending"
    published_at = None
    if auto_approve:
        status = "published"
        # asyncpg requires a datetime for TIMESTAMPTZ. `_now_iso()` returns a
        # string, which fails the INSERT and used to be swallowed. Pitfall #29.
        published_at = datetime.now(tz=timezone.utc)

    next_version = await _next_version_number(conn, curriculum_id, subject)
    await conn.execute(
        """
        INSERT INTO content_subject_versions
            (curriculum_id, subject, subject_name, version_number, status,
             alex_warnings_count, provider, generated_at, published_at, pipeline_run_id)
        VALUES ($1, $2, $3, $4, $5, $6, $7, NOW(), $8, $9)
        ON CONFLICT (curriculum_id, subject, version_number) DO UPDATE
            SET status = EXCLUDED.status,
                subject_name = EXCLUDED.subject_name,
                alex_warnings_count = EXCLUDED.alex_warnings_count,
                provider = EXCLUDED.provider,
                published_at = EXCLUDED.published_at,
                pipeline_run_id = EXCLUDED.pipeline_run_id
        """,
        curriculum_id,
        subject,
        subject_name,
        next_version,
        status,
        alex_warnings,
        provider,
        published_at,
        pipeline_run_id,
    )
    return next_version


async def record_unit_build(
    conn: Any,
    curriculum_id: str,
    subject: str,
    subject_name: str,
    alex_warnings: int,
    auto_approve: bool,
    pipeline_run_id: str,
    provider: str = "anthropic",
) -> tuple[int, str]:
    """Record that ONE unit was rebuilt. Used by `build_unit`.

    Returns `(version_number, "created" | "joined")`.

    Unlike a whole-subject build this does NOT always start a new version. If
    the subject's latest version is still `pending` -- nobody has reviewed it --
    the rebuild joins that version. Otherwise it opens a new one.

    The alternative, a new version per unit, was rejected: the #745 regen
    rebuilt 29 units of `default-2026-g11-science`, which would have produced 29
    versions of "Physics" and buried the review queue. A subject version means
    "this subject's content changed"; one sweep is one such change.

    Joining deliberately leaves `status`, `alex_warnings_count` and
    `published_at` alone -- those belong to the version as a whole, and a single
    unit is not entitled to restate them. Only `generated_at` moves, so the
    review queue orders by genuine recency.
    """
    latest = await conn.fetchrow(
        """
        SELECT version_number, status
        FROM content_subject_versions
        WHERE curriculum_id = $1 AND subject = $2
        ORDER BY version_number DESC
        LIMIT 1
        """,
        curriculum_id,
        subject,
    )

    if latest is not None and latest["status"] == _OPEN_STATUS:
        await conn.execute(
            """
            UPDATE content_subject_versions
               SET generated_at = NOW(),
                   provider = $3,
                   pipeline_run_id = $4
             WHERE curriculum_id = $1 AND subject = $2 AND version_number = $5
            """,
            curriculum_id,
            subject,
            provider,
            pipeline_run_id,
            latest["version_number"],
        )
        return int(latest["version_number"]), "joined"

    version = await create_subject_version(
        conn,
        curriculum_id,
        subject,
        subject_name,
        alex_warnings,
        auto_approve,
        pipeline_run_id,
        provider=provider,
    )
    return version, "created"
