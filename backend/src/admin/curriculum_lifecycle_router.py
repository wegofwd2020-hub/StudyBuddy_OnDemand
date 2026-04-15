"""
backend/src/admin/curriculum_lifecycle_router.py

Admin endpoints for the Epic 10 curriculum lifecycle (L-2 onwards).

L-2 ships the read-only "usage" endpoint; L-4 will extend this module with
archive / unarchive / delete endpoints.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from src.admin.curriculum_service import (
    ArchiveBlocker,
    archive_curriculum,
    assert_archivable,
    fetch_curriculum_owner,
    get_curriculum_usage_summary,
    unarchive_curriculum,
)
from src.auth.dependencies import get_current_admin
from src.core.db import get_db
from src.core.events import write_audit_log
from src.core.permissions import ROLE_PERMISSIONS
from src.utils.logger import get_logger

log = get_logger("admin.curriculum_lifecycle")

router = APIRouter()


def _require(permission: str):
    async def dep(
        request: Request,
        admin: Annotated[dict, Depends(get_current_admin)],
    ) -> dict:
        role = admin.get("role", "")
        perms = ROLE_PERMISSIONS.get(role, set())
        if "*" not in perms and permission not in perms:
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "forbidden",
                    "detail": f"Role '{role}' does not have permission '{permission}'.",
                },
            )
        return admin

    return dep


class CurriculumUsageResponse(BaseModel):
    curriculum_id: str
    owner_type: str
    school_id: str | None
    active_students: int
    active_teachers: int
    schools_assigned: int
    in_use: bool


@router.get("/admin/curricula/{curriculum_id}/usage", response_model=CurriculumUsageResponse)
async def get_curriculum_usage(
    curriculum_id: str,
    request: Request,
    admin: Annotated[dict, Depends(_require("content:publish"))],
) -> CurriculumUsageResponse:
    """
    Return active-assignment counts for a curriculum.

    Used by the admin UI to show "N students currently using this" before an
    archive action, and by the archive endpoint itself (L-4) as the
    pre-condition gate.
    """
    async with get_db(request) as conn:
        owner = await fetch_curriculum_owner(conn, curriculum_id)
        if not owner:
            raise HTTPException(
                status_code=404,
                detail={"error": "not_found", "detail": f"Curriculum '{curriculum_id}' not found."},
            )
        summary = await get_curriculum_usage_summary(conn, curriculum_id)
    return CurriculumUsageResponse(
        curriculum_id=curriculum_id,
        owner_type=owner["owner_type"],
        school_id=str(owner["school_id"]) if owner["school_id"] else None,
        active_students=summary["active_students"],
        active_teachers=summary["active_teachers"],
        schools_assigned=summary["schools_assigned"],
        in_use=summary["in_use"],
    )


# ── Archive / unarchive / delete ─────────────────────────────────────────────


class ArchiveRequest(BaseModel):
    reason: str | None = Field(
        default=None,
        min_length=5,
        max_length=500,
        description="Required when a super-admin archives school-owned content.",
    )


class ArchiveResponse(BaseModel):
    curriculum_id: str
    retention_status: str
    expires_at: datetime | None
    reason: str | None = None


def _is_super_admin(admin: dict) -> bool:
    return admin.get("role") == "super_admin"


async def _emit_lifecycle_audit(
    *,
    event_type: str,
    admin: dict,
    curriculum: dict,
    prior_status: str,
    new_status: str,
    reason: str | None,
) -> None:
    """Fire-and-forget audit row for L-5 action types."""
    actor_id_raw = admin.get("admin_id")
    try:
        actor_uuid = uuid.UUID(actor_id_raw) if actor_id_raw else None
    except (TypeError, ValueError):
        actor_uuid = None
    write_audit_log(
        event_type=event_type,
        actor_type="admin",
        actor_id=actor_uuid,
        target_type="curriculum",
        target_id=None,  # curriculum_id is text, not UUID — stored in metadata
        metadata={
            "curriculum_id": curriculum["curriculum_id"],
            "owner_type": curriculum["owner_type"],
            "school_id": str(curriculum["school_id"]) if curriculum.get("school_id") else None,
            "prior_retention_status": prior_status,
            "new_retention_status": new_status,
            "reason": reason,
            "actor_role": admin.get("role"),
        },
    )


@router.post(
    "/admin/curricula/{curriculum_id}/archive",
    response_model=ArchiveResponse,
)
async def admin_archive_curriculum(
    curriculum_id: str,
    body: ArchiveRequest,
    request: Request,
    admin: Annotated[dict, Depends(_require("content:publish"))],
) -> ArchiveResponse:
    """
    Archive a curriculum.

    Super-admin can archive anything; when the target is `owner_type='school'`
    the platform-admin-override path requires a written `reason` (Follow-up A
    resolution). product_admin can archive platform content without a reason
    but cannot override school content.
    """
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

            overriding_school = curr["owner_type"] == "school"
            if overriding_school:
                if not _is_super_admin(admin):
                    raise HTTPException(
                        status_code=403,
                        detail={
                            "error": "forbidden",
                            "detail": (
                                "Only super-admin can archive school-owned curricula. "
                                "School admins should use the school portal."
                            ),
                        },
                    )
                if not body.reason:
                    raise HTTPException(
                        status_code=400,
                        detail={
                            "error": "reason_required",
                            "detail": (
                                "A written reason is required when platform admins "
                                "archive school-owned content."
                            ),
                        },
                    )

            prior_status = curr["retention_status"]
            updated = await archive_curriculum(conn, curriculum_id=curriculum_id)

    event_type = (
        "curriculum.archive_by_platform_admin" if overriding_school else "curriculum.archive"
    )
    await _emit_lifecycle_audit(
        event_type=event_type,
        admin=admin,
        curriculum=curr,
        prior_status=prior_status,
        new_status="archived",
        reason=body.reason,
    )
    log.info(
        "curriculum_archived curriculum_id=%s owner=%s admin=%s",
        curriculum_id,
        curr["owner_type"],
        admin.get("admin_id"),
    )
    return ArchiveResponse(
        curriculum_id=curriculum_id,
        retention_status=updated["retention_status"],
        expires_at=updated["expires_at"],
        reason=body.reason,
    )


@router.post(
    "/admin/curricula/{curriculum_id}/unarchive",
    response_model=ArchiveResponse,
)
async def admin_unarchive_curriculum(
    curriculum_id: str,
    request: Request,
    admin: Annotated[dict, Depends(_require("content:publish"))],
) -> ArchiveResponse:
    """Unarchive a curriculum. Super-admin only."""
    if not _is_super_admin(admin):
        raise HTTPException(
            status_code=403,
            detail={
                "error": "forbidden",
                "detail": "Only super-admin can unarchive curricula.",
            },
        )

    async with get_db(request) as conn:
        async with conn.transaction():
            curr = await fetch_curriculum_owner(conn, curriculum_id)
            if not curr:
                raise HTTPException(
                    status_code=404,
                    detail={"error": "not_found", "detail": f"Curriculum '{curriculum_id}' not found."},
                )
            if curr["retention_status"] != "archived":
                raise HTTPException(
                    status_code=409,
                    detail={
                        "error": "not_archived",
                        "detail": f"Curriculum '{curriculum_id}' is not archived.",
                    },
                )
            prior_status = curr["retention_status"]
            updated = await unarchive_curriculum(conn, curriculum_id)

    await _emit_lifecycle_audit(
        event_type="curriculum.unarchive",
        admin=admin,
        curriculum=curr,
        prior_status=prior_status,
        new_status="active",
        reason=None,
    )
    log.info("curriculum_unarchived curriculum_id=%s admin=%s", curriculum_id, admin.get("admin_id"))
    return ArchiveResponse(
        curriculum_id=curriculum_id,
        retention_status=updated["retention_status"],
        expires_at=updated["expires_at"],
    )


@router.delete("/admin/curricula/{curriculum_id}", response_model=ArchiveResponse)
async def admin_delete_curriculum(
    curriculum_id: str,
    request: Request,
    admin: Annotated[dict, Depends(_require("content:publish"))],
) -> ArchiveResponse:
    """DELETE is an alias for archive — no hard-delete via the API."""
    return await admin_archive_curriculum(
        curriculum_id=curriculum_id,
        body=ArchiveRequest(),
        request=request,
        admin=admin,
    )
