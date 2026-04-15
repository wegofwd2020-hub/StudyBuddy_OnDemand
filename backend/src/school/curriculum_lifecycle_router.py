"""
backend/src/school/curriculum_lifecycle_router.py

School-portal counterpart of the admin curriculum lifecycle endpoints
(Epic 10 L-4). Ownership-gated: school_admin can archive only their own
school's curricula; platform content is read-only here.

School admins use this endpoint via the school portal; super-admin and
product-admin use /admin/curricula/{id}/archive (which also supports the
written-reason override for platform-admin-archives-school-content).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from src.admin.curriculum_service import (
    ArchiveBlocker,
    archive_curriculum,
    assert_archivable,
    fetch_curriculum_owner,
    unarchive_curriculum,
)
from src.auth.dependencies import get_current_teacher
from src.core.db import get_db
from src.core.events import write_audit_log
from src.utils.logger import get_logger

log = get_logger("school.curriculum_lifecycle")

router = APIRouter()


class ArchiveResponse(BaseModel):
    curriculum_id: str
    retention_status: str
    expires_at: datetime | None


def _require_school_admin(teacher: dict, school_id: str) -> None:
    if teacher.get("role") != "school_admin":
        raise HTTPException(
            status_code=403,
            detail={"error": "forbidden", "detail": "School admin role required."},
        )
    if str(teacher.get("school_id")) != str(school_id):
        raise HTTPException(
            status_code=403,
            detail={"error": "forbidden", "detail": "Cannot act on another school."},
        )


def _require_ownership(curr: dict, school_id: str) -> None:
    if curr["owner_type"] != "school":
        raise HTTPException(
            status_code=403,
            detail={
                "error": "forbidden",
                "detail": "Only school-owned curricula can be archived via the school portal.",
            },
        )
    if str(curr["school_id"]) != str(school_id):
        raise HTTPException(
            status_code=403,
            detail={"error": "forbidden", "detail": "Cannot act on another school's curriculum."},
        )


async def _emit_audit(
    *,
    event_type: str,
    teacher: dict,
    curriculum: dict,
    prior_status: str,
    new_status: str,
) -> None:
    actor_id_raw = teacher.get("teacher_id")
    try:
        actor_uuid = uuid.UUID(actor_id_raw) if actor_id_raw else None
    except (TypeError, ValueError):
        actor_uuid = None
    write_audit_log(
        event_type=event_type,
        actor_type="school_admin",
        actor_id=actor_uuid,
        target_type="curriculum",
        target_id=None,
        metadata={
            "curriculum_id": curriculum["curriculum_id"],
            "owner_type": curriculum["owner_type"],
            "school_id": str(curriculum["school_id"]) if curriculum.get("school_id") else None,
            "prior_retention_status": prior_status,
            "new_retention_status": new_status,
            "actor_role": teacher.get("role"),
        },
    )


@router.post(
    "/schools/{school_id}/curricula/{curriculum_id}/archive",
    response_model=ArchiveResponse,
)
async def school_archive_curriculum(
    school_id: str,
    curriculum_id: str,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
) -> ArchiveResponse:
    _require_school_admin(teacher, school_id)

    async with get_db(request) as conn:
        async with conn.transaction():
            try:
                curr = await assert_archivable(conn, curriculum_id)
            except ArchiveBlocker as blk:
                status_code = 404 if blk.code == "not_found" else 409
                raise HTTPException(
                    status_code=status_code,
                    detail={"error": blk.code, "detail": blk.detail},
                )
            _require_ownership(curr, school_id)
            prior_status = curr["retention_status"]
            updated = await archive_curriculum(conn, curriculum_id=curriculum_id)

    await _emit_audit(
        event_type="curriculum.archive",
        teacher=teacher,
        curriculum=curr,
        prior_status=prior_status,
        new_status="archived",
    )
    log.info(
        "school_curriculum_archived curriculum_id=%s school=%s teacher=%s",
        curriculum_id,
        school_id,
        teacher.get("teacher_id"),
    )
    return ArchiveResponse(
        curriculum_id=curriculum_id,
        retention_status=updated["retention_status"],
        expires_at=updated["expires_at"],
    )


@router.delete(
    "/schools/{school_id}/curricula/{curriculum_id}",
    response_model=ArchiveResponse,
)
async def school_delete_curriculum(
    school_id: str,
    curriculum_id: str,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
) -> ArchiveResponse:
    """DELETE is an alias for archive — no hard delete via the API."""
    return await school_archive_curriculum(
        school_id=school_id,
        curriculum_id=curriculum_id,
        request=request,
        teacher=teacher,
    )
