"""
backend/src/backup/service.py

Pure async service functions for curriculum backup and restore operations.

All functions accept an asyncpg.Connection as their first argument — no
FastAPI dependencies here.  The RLS bypass must be set by the caller before
these functions are invoked (Celery tasks set it; router helpers use get_db
which stamps the school_id).
"""

from __future__ import annotations

import uuid
from datetime import datetime

import asyncpg

from src.utils.logger import get_logger

log = get_logger("backup.service")


# ── Backup helpers ────────────────────────────────────────────────────────────


async def get_school_backups(conn: asyncpg.Connection, school_id: str) -> list[dict]:
    """Return all backups for a school ordered by created_at DESC."""
    rows = await conn.fetch(
        """
        SELECT id, school_id, label, scope_type, scope_value, storage_path,
               manifest_json, status, triggered_by, created_at, expires_at,
               file_count, total_bytes
        FROM curriculum_backups
        WHERE school_id = $1
        ORDER BY created_at DESC
        """,
        uuid.UUID(school_id),
    )
    return [dict(r) for r in rows]


async def get_backup(
    conn: asyncpg.Connection, backup_id: str, school_id: str
) -> dict | None:
    """Return a single backup row, scoped to school_id."""
    row = await conn.fetchrow(
        """
        SELECT id, school_id, label, scope_type, scope_value, storage_path,
               manifest_json, status, triggered_by, created_at, expires_at,
               file_count, total_bytes
        FROM curriculum_backups
        WHERE id = $1 AND school_id = $2
        """,
        uuid.UUID(backup_id),
        uuid.UUID(school_id),
    )
    return dict(row) if row else None


async def create_backup_record(
    conn: asyncpg.Connection,
    school_id: str,
    scope_type: str,
    scope_value: str | None,
    triggered_by: str | None,
    label: str,
) -> str:
    """Insert a pending curriculum_backups row, return the new UUID as str."""
    row = await conn.fetchrow(
        """
        INSERT INTO curriculum_backups
            (school_id, label, scope_type, scope_value, triggered_by, status)
        VALUES ($1, $2, $3, $4, $5, 'pending')
        RETURNING id
        """,
        uuid.UUID(school_id),
        label,
        scope_type,
        scope_value,
        uuid.UUID(triggered_by) if triggered_by else None,
    )
    new_id = str(row["id"])
    log.info(
        "backup_record_created",
        backup_id=new_id,
        school_id=school_id,
        scope_type=scope_type,
    )
    return new_id


# ── Restore request helpers ───────────────────────────────────────────────────


async def submit_restore_request(
    conn: asyncpg.Connection,
    school_id: str,
    backup_id: str,
    scope_type: str,
    scope_value: str | None,
    notes: str | None,
    scheduled_at: datetime | None,
    requested_by: str | None,
    side_by_side: bool = False,
) -> str:
    """
    Insert a backup_restore_requests row.

    Deduplication: cancel any prior submitted/acknowledged request for the
    same school + backup + scope_type + scope_value before inserting so the
    admin queue stays clean.
    Returns the new request UUID as str.
    """
    # Cancel any pre-existing open requests for the same scope.
    await conn.execute(
        """
        UPDATE backup_restore_requests
        SET status = 'cancelled', updated_at = NOW()
        WHERE school_id = $1
          AND backup_id = $2
          AND scope_type = $3
          AND (scope_value = $4 OR (scope_value IS NULL AND $4 IS NULL))
          AND status IN ('submitted', 'acknowledged')
        """,
        uuid.UUID(school_id),
        uuid.UUID(backup_id),
        scope_type,
        scope_value,
    )

    row = await conn.fetchrow(
        """
        INSERT INTO backup_restore_requests
            (school_id, backup_id, scope_type, scope_value, notes,
             scheduled_at, requested_by, side_by_side, status)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, 'submitted')
        RETURNING id
        """,
        uuid.UUID(school_id),
        uuid.UUID(backup_id),
        scope_type,
        scope_value,
        notes,
        scheduled_at,
        uuid.UUID(requested_by) if requested_by else None,
        side_by_side,
    )
    new_id = str(row["id"])
    log.info(
        "restore_request_submitted",
        request_id=new_id,
        school_id=school_id,
        backup_id=backup_id,
    )
    return new_id


async def acknowledge_restore_request(
    conn: asyncpg.Connection, request_id: str, admin_id: str
) -> dict:
    """Advance status submitted → acknowledged.  Return the updated request row."""
    row = await conn.fetchrow(
        """
        UPDATE backup_restore_requests
        SET status = 'acknowledged', updated_at = NOW()
        WHERE id = $1 AND status = 'submitted'
        RETURNING *
        """,
        uuid.UUID(request_id),
    )
    if not row:
        raise ValueError(f"Restore request {request_id} not found or not in submitted state")
    log.info("restore_request_acknowledged", request_id=request_id, admin_id=admin_id)
    return dict(row)


async def school_confirm_override(
    conn: asyncpg.Connection,
    request_id: str,
    school_id: str,
    side_by_side: bool,
) -> dict:
    """Advance status awaiting_school_confirm → in_progress.  Update side_by_side flag."""
    row = await conn.fetchrow(
        """
        UPDATE backup_restore_requests
        SET status = 'in_progress', side_by_side = $3, updated_at = NOW()
        WHERE id = $1 AND school_id = $2 AND status = 'awaiting_school_confirm'
        RETURNING *
        """,
        uuid.UUID(request_id),
        uuid.UUID(school_id),
        side_by_side,
    )
    if not row:
        raise ValueError(
            f"Restore request {request_id} not found or not awaiting school confirmation"
        )
    log.info(
        "restore_request_school_confirmed",
        request_id=request_id,
        school_id=school_id,
        side_by_side=side_by_side,
    )
    return dict(row)


async def cancel_restore_request(conn: asyncpg.Connection, request_id: str) -> None:
    """Set status = 'cancelled'."""
    await conn.execute(
        """
        UPDATE backup_restore_requests
        SET status = 'cancelled', updated_at = NOW()
        WHERE id = $1
        """,
        uuid.UUID(request_id),
    )
    log.info("restore_request_cancelled", request_id=request_id)


async def get_restore_request(
    conn: asyncpg.Connection, request_id: str
) -> dict | None:
    """Return a single restore request row."""
    row = await conn.fetchrow(
        "SELECT * FROM backup_restore_requests WHERE id = $1",
        uuid.UUID(request_id),
    )
    return dict(row) if row else None


async def list_restore_requests(
    conn: asyncpg.Connection, school_id: str | None = None
) -> list[dict]:
    """List restore requests; if school_id given, filter to that school."""
    if school_id:
        rows = await conn.fetch(
            """
            SELECT * FROM backup_restore_requests
            WHERE school_id = $1
            ORDER BY created_at DESC
            """,
            uuid.UUID(school_id),
        )
    else:
        rows = await conn.fetch(
            "SELECT * FROM backup_restore_requests ORDER BY created_at DESC"
        )
    return [dict(r) for r in rows]


# ── Backup schedule helpers ───────────────────────────────────────────────────


async def get_backup_schedule(conn: asyncpg.Connection, school_id: str) -> str | None:
    """Return schools.backup_cron for the school."""
    row = await conn.fetchrow(
        "SELECT backup_cron FROM schools WHERE school_id = $1",
        uuid.UUID(school_id),
    )
    return row["backup_cron"] if row else None


async def set_backup_schedule(
    conn: asyncpg.Connection, school_id: str, cron: str
) -> None:
    """Update schools.backup_cron."""
    await conn.execute(
        "UPDATE schools SET backup_cron = $1 WHERE school_id = $2",
        cron,
        uuid.UUID(school_id),
    )
    log.info("backup_schedule_updated", school_id=school_id, cron=cron)
