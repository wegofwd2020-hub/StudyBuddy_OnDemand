"""
backend/src/admin/curriculum_lifecycle_router.py

Admin endpoints for the Epic 10 curriculum lifecycle (L-2 onwards).

L-2 ships the read-only "usage" endpoint; L-4 will extend this module with
archive / unarchive / delete endpoints.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from src.admin.curriculum_service import (
    fetch_curriculum_owner,
    get_curriculum_usage_summary,
)
from src.auth.dependencies import get_current_admin
from src.core.db import get_db
from src.core.permissions import ROLE_PERMISSIONS

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
