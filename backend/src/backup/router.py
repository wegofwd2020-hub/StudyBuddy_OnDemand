"""
backend/src/backup/router.py

REST API for Epic 15 — School Curriculum Backup & Restore.

Admin endpoints (super_admin only):
  POST   /admin/schools/{school_id}/backups
  GET    /admin/schools/{school_id}/backups
  GET    /admin/backups
  GET    /admin/backups/{backup_id}
  GET    /admin/restore-requests
  PATCH  /admin/restore-requests/{request_id}/acknowledge
  PATCH  /admin/restore-requests/{request_id}/execute
  PATCH  /admin/restore-requests/{request_id}/cancel
  GET    /admin/backup-schedules
  PUT    /admin/backup-schedules/{school_id}

School endpoints (school_admin role, own school only):
  GET    /schools/{school_id}/backups
  POST   /schools/{school_id}/restore-requests
  GET    /schools/{school_id}/restore-requests
  PATCH  /schools/{school_id}/restore-requests/{request_id}/confirm
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request

from src.auth.dependencies import get_current_admin, get_current_teacher
from src.backup.schemas import (
    BackupCreateRequest,
    BackupListResponse,
    BackupResponse,
    BackupScheduleResponse,
    BackupScheduleUpdate,
    ConfirmOverrideRequest,
    RestoreRequestCreate,
    RestoreRequestListResponse,
    RestoreRequestResponse,
)
from src.backup.service import (
    acknowledge_restore_request,
    cancel_restore_request,
    create_backup_record,
    get_backup,
    get_restore_request,
    get_school_backups,
    list_restore_requests,
    school_confirm_override,
    set_backup_schedule,
    submit_restore_request,
)
from src.core.db import get_db
from src.utils.logger import get_logger

log = get_logger("backup.router")

router = APIRouter()


# ── Helpers ───────────────────────────────────────────────────────────────────


def _require_super_admin(admin: dict) -> None:
    if admin.get("role") != "super_admin":
        raise HTTPException(status_code=403, detail="super_admin role required")


def _require_school_admin(teacher: dict, school_id: str) -> None:
    if str(teacher.get("school_id", "")) != school_id:
        raise HTTPException(status_code=403, detail="Access denied to this school")
    if teacher.get("role") != "school_admin":
        raise HTTPException(status_code=403, detail="school_admin role required")


def _backup_row_to_response(row: dict) -> BackupResponse:
    return BackupResponse(
        id=str(row["id"]),
        school_id=str(row["school_id"]),
        label=row.get("label") or "",
        scope_type=row["scope_type"],
        scope_value=row.get("scope_value"),
        status=row["status"],
        file_count=row.get("file_count") or 0,
        total_bytes=row.get("total_bytes") or 0,
        created_at=row["created_at"],
        triggered_by=str(row["triggered_by"]) if row.get("triggered_by") else None,
    )


def _restore_row_to_response(row: dict) -> RestoreRequestResponse:
    return RestoreRequestResponse(
        id=str(row["id"]),
        school_id=str(row["school_id"]),
        backup_id=str(row["backup_id"]) if row.get("backup_id") else None,
        status=row["status"],
        scope_type=row["scope_type"],
        scope_value=row.get("scope_value"),
        side_by_side=row.get("side_by_side", False),
        conflict_catalog_id=str(row["conflict_catalog_id"])
        if row.get("conflict_catalog_id")
        else None,
        scheduled_at=row.get("scheduled_at"),
        notes=row.get("notes"),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


# ── Admin — backup endpoints ──────────────────────────────────────────────────


@router.post("/admin/schools/{school_id}/backups", response_model=BackupResponse)
async def admin_create_backup(
    school_id: str,
    body: BackupCreateRequest,
    request: Request,
    admin: Annotated[dict, Depends(get_current_admin)],
):
    """Create a backup record and dispatch the backup Celery task."""
    _require_super_admin(admin)

    from src.backup.tasks import backup_school_task

    async with get_db(request) as conn:
        backup_id = await create_backup_record(
            conn=conn,
            school_id=school_id,
            scope_type=body.scope_type,
            scope_value=body.scope_value,
            triggered_by=admin.get("admin_id"),
            label=body.label,
        )

        backup_school_task.delay(
            school_id=school_id,
            scope_type=body.scope_type,
            scope_value=body.scope_value,
            triggered_by=admin.get("admin_id"),
            backup_id=backup_id,
        )

        row = await get_backup(conn=conn, backup_id=backup_id, school_id=school_id)
    if not row:
        raise HTTPException(status_code=500, detail="Backup record not found after creation")
    return _backup_row_to_response(row)


@router.get("/admin/schools/{school_id}/backups", response_model=BackupListResponse)
async def admin_list_school_backups(
    school_id: str,
    request: Request,
    admin: Annotated[dict, Depends(get_current_admin)],
):
    """List all backups for a specific school."""
    _require_super_admin(admin)
    async with get_db(request) as conn:
        rows = await get_school_backups(conn=conn, school_id=school_id)
    backups = [_backup_row_to_response(r) for r in rows]
    return BackupListResponse(backups=backups, total=len(backups))


@router.get("/admin/backups", response_model=BackupListResponse)
async def admin_list_all_backups(
    request: Request,
    admin: Annotated[dict, Depends(get_current_admin)],
    page: int = 1,
    per_page: int = 20,
):
    """List all backups across all schools, paginated."""
    _require_super_admin(admin)
    offset = (page - 1) * per_page
    async with get_db(request) as conn:
        rows = await conn.fetch(
            """
            SELECT id, school_id, label, scope_type, scope_value, storage_path,
                   manifest_json, status, triggered_by, created_at, expires_at,
                   file_count, total_bytes
            FROM curriculum_backups
            ORDER BY created_at DESC
            LIMIT $1 OFFSET $2
            """,
            per_page,
            offset,
        )
        total_row = await conn.fetchrow("SELECT COUNT(*) FROM curriculum_backups")
        total = total_row[0] if total_row else 0
    backups = [_backup_row_to_response(dict(r)) for r in rows]
    return BackupListResponse(backups=backups, total=total)


@router.get("/admin/backups/{backup_id}", response_model=BackupResponse)
async def admin_get_backup(
    backup_id: str,
    request: Request,
    admin: Annotated[dict, Depends(get_current_admin)],
):
    """Get a single backup by ID."""
    _require_super_admin(admin)
    async with get_db(request) as conn:
        row = await conn.fetchrow(
            """
            SELECT id, school_id, label, scope_type, scope_value, storage_path,
                   manifest_json, status, triggered_by, created_at, expires_at,
                   file_count, total_bytes
            FROM curriculum_backups WHERE id=$1
            """,
            uuid.UUID(backup_id),
        )
    if not row:
        raise HTTPException(status_code=404, detail="Backup not found")
    return _backup_row_to_response(dict(row))


# ── Admin — restore request endpoints ────────────────────────────────────────


@router.get("/admin/restore-requests", response_model=RestoreRequestListResponse)
async def admin_list_restore_requests(
    request: Request,
    admin: Annotated[dict, Depends(get_current_admin)],
):
    """List all restore requests across all schools."""
    _require_super_admin(admin)
    async with get_db(request) as conn:
        rows = await list_restore_requests(conn=conn)
    requests = [_restore_row_to_response(r) for r in rows]
    return RestoreRequestListResponse(requests=requests, total=len(requests))


@router.patch(
    "/admin/restore-requests/{request_id}/acknowledge",
    response_model=RestoreRequestResponse,
)
async def admin_acknowledge_restore_request(
    request_id: str,
    request: Request,
    admin: Annotated[dict, Depends(get_current_admin)],
):
    """Acknowledge a restore request and dispatch dry-run verification."""
    _require_super_admin(admin)

    from src.backup.tasks import dry_run_restore_task

    async with get_db(request) as conn:
        try:
            row = await acknowledge_restore_request(
                conn=conn,
                request_id=request_id,
                admin_id=admin.get("admin_id", ""),
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    dry_run_restore_task.delay(request_id=request_id)
    return _restore_row_to_response(row)


@router.patch(
    "/admin/restore-requests/{request_id}/execute",
    response_model=RestoreRequestResponse,
)
async def admin_execute_restore_request(
    request_id: str,
    request: Request,
    admin: Annotated[dict, Depends(get_current_admin)],
):
    """Manually dispatch execute_restore_task for an awaiting or acknowledged request."""
    _require_super_admin(admin)

    from src.backup.tasks import execute_restore_task

    async with get_db(request) as conn:
        row = await get_restore_request(conn=conn, request_id=request_id)
    if not row:
        raise HTTPException(status_code=404, detail="Restore request not found")
    if row["status"] not in ("awaiting_school_confirm", "acknowledged"):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot execute restore in status '{row['status']}'",
        )

    execute_restore_task.delay(request_id=request_id)
    return _restore_row_to_response(row)


@router.patch(
    "/admin/restore-requests/{request_id}/cancel",
    response_model=RestoreRequestResponse,
)
async def admin_cancel_restore_request(
    request_id: str,
    request: Request,
    admin: Annotated[dict, Depends(get_current_admin)],
):
    """Cancel a restore request."""
    _require_super_admin(admin)
    async with get_db(request) as conn:
        row = await get_restore_request(conn=conn, request_id=request_id)
        if not row:
            raise HTTPException(status_code=404, detail="Restore request not found")
        await cancel_restore_request(conn=conn, request_id=request_id)
    row["status"] = "cancelled"
    return _restore_row_to_response(row)


# ── Admin — backup schedule endpoints ────────────────────────────────────────


@router.get("/admin/backup-schedules")
async def admin_list_backup_schedules(
    request: Request,
    admin: Annotated[dict, Depends(get_current_admin)],
):
    """List all schools with their backup_cron setting."""
    _require_super_admin(admin)
    async with get_db(request) as conn:
        rows = await conn.fetch(
            "SELECT school_id, backup_cron FROM schools ORDER BY school_id"
        )
    return [
        BackupScheduleResponse(
            school_id=str(r["school_id"]),
            cron=r.get("backup_cron"),
        )
        for r in rows
    ]


@router.put(
    "/admin/backup-schedules/{school_id}",
    response_model=BackupScheduleResponse,
)
async def admin_update_backup_schedule(
    school_id: str,
    body: BackupScheduleUpdate,
    request: Request,
    admin: Annotated[dict, Depends(get_current_admin)],
):
    """Update the backup cron expression for a school."""
    _require_super_admin(admin)
    async with get_db(request) as conn:
        await set_backup_schedule(conn=conn, school_id=school_id, cron=body.cron)
    return BackupScheduleResponse(school_id=school_id, cron=body.cron)


# ── School — backup endpoints (read-only) ────────────────────────────────────


@router.get("/schools/{school_id}/backups", response_model=BackupListResponse)
async def school_list_backups(
    school_id: str,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
):
    """List backups for the school (school_admin, own school only)."""
    _require_school_admin(teacher, school_id)
    async with get_db(request) as conn:
        rows = await get_school_backups(conn=conn, school_id=school_id)
    backups = [_backup_row_to_response(r) for r in rows]
    return BackupListResponse(backups=backups, total=len(backups))


# ── School — restore request endpoints ───────────────────────────────────────


@router.post(
    "/schools/{school_id}/restore-requests",
    response_model=RestoreRequestResponse,
)
async def school_submit_restore_request(
    school_id: str,
    body: RestoreRequestCreate,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
):
    """Submit a restore request on behalf of the school."""
    _require_school_admin(teacher, school_id)

    async with get_db(request) as conn:
        # Validate the backup belongs to this school
        backup = await get_backup(conn=conn, backup_id=body.backup_id, school_id=school_id)
        if not backup:
            raise HTTPException(status_code=404, detail="Backup not found")
        if backup["status"] != "completed":
            raise HTTPException(
                status_code=400,
                detail="Can only restore from a completed backup",
            )

        request_id = await submit_restore_request(
            conn=conn,
            school_id=school_id,
            backup_id=body.backup_id,
            scope_type=body.scope_type,
            scope_value=body.scope_value,
            notes=body.notes,
            scheduled_at=body.scheduled_at,
            requested_by=str(teacher.get("teacher_id", "")),
            side_by_side=body.side_by_side,
        )

        row = await get_restore_request(conn=conn, request_id=request_id)
    if not row:
        raise HTTPException(status_code=500, detail="Restore request not found after creation")
    return _restore_row_to_response(row)


@router.get(
    "/schools/{school_id}/restore-requests/{request_id}",
    response_model=RestoreRequestResponse,
)
async def school_get_restore_request(
    school_id: str,
    request_id: str,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
):
    """Get a single restore request for the school."""
    _require_school_admin(teacher, school_id)
    async with get_db(request) as conn:
        row = await get_restore_request(conn=conn, request_id=request_id)
    if not row or str(row["school_id"]) != school_id:
        raise HTTPException(status_code=404, detail="Restore request not found")
    return _restore_row_to_response(row)


@router.patch(
    "/schools/{school_id}/restore-requests/{request_id}/cancel",
    response_model=RestoreRequestResponse,
)
async def school_cancel_restore_request(
    school_id: str,
    request_id: str,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
):
    """School admin cancels their own restore request (submitted state only)."""
    _require_school_admin(teacher, school_id)
    async with get_db(request) as conn:
        row = await get_restore_request(conn=conn, request_id=request_id)
        if not row or str(row["school_id"]) != school_id:
            raise HTTPException(status_code=404, detail="Restore request not found")
        if row["status"] not in ("submitted",):
            raise HTTPException(
                status_code=400,
                detail="Only submitted requests can be cancelled by the school",
            )
        await cancel_restore_request(conn=conn, request_id=request_id)
    row["status"] = "cancelled"
    return _restore_row_to_response(row)


@router.get(
    "/schools/{school_id}/restore-requests",
    response_model=RestoreRequestListResponse,
)
async def school_list_restore_requests(
    school_id: str,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
):
    """List restore requests for the school."""
    _require_school_admin(teacher, school_id)
    async with get_db(request) as conn:
        rows = await list_restore_requests(conn=conn, school_id=school_id)
    requests = [_restore_row_to_response(r) for r in rows]
    return RestoreRequestListResponse(requests=requests, total=len(requests))


@router.patch(
    "/schools/{school_id}/restore-requests/{request_id}/confirm",
    response_model=RestoreRequestResponse,
)
async def school_confirm_restore_override(
    school_id: str,
    request_id: str,
    body: ConfirmOverrideRequest,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
):
    """School admin confirms a restore that has conflicts (awaiting_school_confirm)."""
    _require_school_admin(teacher, school_id)

    from src.backup.tasks import execute_restore_task

    async with get_db(request) as conn:
        try:
            row = await school_confirm_override(
                conn=conn,
                request_id=request_id,
                school_id=school_id,
                side_by_side=body.side_by_side,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    execute_restore_task.delay(request_id=request_id)
    return _restore_row_to_response(row)
