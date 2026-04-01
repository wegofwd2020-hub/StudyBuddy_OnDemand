"""
backend/src/school/limits_router.py

School limits and override endpoints.

Routes (all prefixed /api/v1 in main.py):

  School-scoped (teacher/school_admin JWT):
    GET  /schools/{school_id}/limits

  Admin-scoped (admin JWT with school:manage permission):
    GET    /admin/schools/{school_id}/limits
    PUT    /admin/schools/{school_id}/limits
    DELETE /admin/schools/{school_id}/limits

RBAC:
  - school_admin: GET /schools/{id}/limits (own school only, read-only)
  - school:manage (product_admin / super_admin): all /admin/ endpoints
  - PUT and DELETE additionally require the admin_id from the JWT so the
    override can be attributed in the audit log.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from src.auth.dependencies import get_current_admin, get_current_teacher
from src.core.db import get_db
from src.core.events import write_audit_log
from src.core.permissions import ROLE_PERMISSIONS
from src.school.limits_service import (
    clear_school_limits_override,
    get_school_limits_view,
    set_school_limits_override,
)
from src.utils.logger import get_logger

log = get_logger("school.limits")
router = APIRouter(tags=["school-limits"])


# ── Schemas ───────────────────────────────────────────────────────────────────


class SchoolLimitsResponse(BaseModel):
    plan: str
    max_students: int
    max_teachers: int
    pipeline_quota_monthly: int
    pipeline_runs_this_month: int
    pipeline_resets_at: str
    seats_used_students: int
    seats_used_teachers: int
    has_override: bool


class AdminSchoolLimitsResponse(SchoolLimitsResponse):
    override: dict | None = None


class SetOverrideRequest(BaseModel):
    max_students: int | None = None
    max_teachers: int | None = None
    pipeline_quota: int | None = None
    override_reason: str  # required


class SetOverrideResponse(BaseModel):
    status: str
    school_id: str


class ClearOverrideResponse(BaseModel):
    status: str
    school_id: str


# ── Helpers ───────────────────────────────────────────────────────────────────


def _cid(request: Request) -> str:
    return getattr(request.state, "correlation_id", "")


def _require_school_manage(admin: dict, request: Request) -> None:
    """Raise 403 if the admin does not have school:manage permission."""
    role = admin.get("role", "")
    perms = ROLE_PERMISSIONS.get(role, set())
    if "*" not in perms and "school:manage" not in perms:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "forbidden",
                "detail": f"Role '{role}' does not have permission 'school:manage'.",
                "correlation_id": _cid(request),
            },
        )


def _admin_id(admin: dict) -> str:
    return str(admin["admin_id"])


# ── GET /schools/{school_id}/limits ──────────────────────────────────────────


@router.get(
    "/schools/{school_id}/limits",
    response_model=SchoolLimitsResponse,
    status_code=200,
)
async def get_school_limits(
    school_id: str,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
) -> SchoolLimitsResponse:
    """
    View the effective limits for your school (read-only).

    school_admin JWT required. school_id in path must match JWT school_id.
    """
    if teacher.get("school_id") != school_id:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "forbidden",
                "detail": "Cannot view limits for a different school.",
                "correlation_id": _cid(request),
            },
        )

    async with get_db(request) as conn:
        data = await get_school_limits_view(conn, school_id, include_override_detail=False)

    return SchoolLimitsResponse(**data)


# ── GET /admin/schools/{school_id}/limits ────────────────────────────────────


@router.get(
    "/admin/schools/{school_id}/limits",
    response_model=AdminSchoolLimitsResponse,
    status_code=200,
)
async def admin_get_school_limits(
    school_id: str,
    request: Request,
    admin: Annotated[dict, Depends(get_current_admin)],
) -> AdminSchoolLimitsResponse:
    """View limits + raw override for any school (school:manage required)."""
    _require_school_manage(admin, request)

    # Verify school exists
    async with get_db(request) as conn:
        exists = await conn.fetchval(
            "SELECT 1 FROM schools WHERE school_id = $1",
            uuid.UUID(school_id),
        )
        if not exists:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "not_found",
                    "detail": "School not found.",
                    "correlation_id": _cid(request),
                },
            )
        data = await get_school_limits_view(conn, school_id, include_override_detail=True)

    return AdminSchoolLimitsResponse(**data)


# ── PUT /admin/schools/{school_id}/limits ─────────────────────────────────────


@router.put(
    "/admin/schools/{school_id}/limits",
    response_model=SetOverrideResponse,
    status_code=200,
)
async def admin_set_school_limits(
    school_id: str,
    body: SetOverrideRequest,
    request: Request,
    admin: Annotated[dict, Depends(get_current_admin)],
) -> SetOverrideResponse:
    """
    Set per-school limit overrides (school:manage required).

    All limit fields are optional — only provided (non-None) fields are stored.
    NULL values in the DB mean "fall back to plan default for this field".
    override_reason is required.
    """
    _require_school_manage(admin, request)

    admin_id = _admin_id(admin)
    ip = request.client.host if request.client else None

    async with get_db(request) as conn:
        exists = await conn.fetchval(
            "SELECT 1 FROM schools WHERE school_id = $1",
            uuid.UUID(school_id),
        )
        if not exists:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "not_found",
                    "detail": "School not found.",
                    "correlation_id": _cid(request),
                },
            )

        audit_data = await set_school_limits_override(
            conn,
            school_id=school_id,
            admin_id=admin_id,
            max_students=body.max_students,
            max_teachers=body.max_teachers,
            pipeline_quota=body.pipeline_quota,
            override_reason=body.override_reason,
        )

    write_audit_log(
        event_type="SET_SCHOOL_LIMITS_OVERRIDE",
        actor_type="admin",
        actor_id=uuid.UUID(admin_id),
        target_type="school",
        target_id=uuid.UUID(school_id),
        metadata={
            "old_override": audit_data["old_override"],
            "new_override": audit_data["new_override"],
            "override_reason": body.override_reason,
        },
        ip_address=ip,
    )

    return SetOverrideResponse(status="override_set", school_id=school_id)


# ── DELETE /admin/schools/{school_id}/limits ──────────────────────────────────


@router.delete(
    "/admin/schools/{school_id}/limits",
    response_model=ClearOverrideResponse,
    status_code=200,
)
async def admin_clear_school_limits(
    school_id: str,
    request: Request,
    admin: Annotated[dict, Depends(get_current_admin)],
) -> ClearOverrideResponse:
    """
    Clear per-school limit overrides, reverting to plan defaults (school:manage required).
    """
    _require_school_manage(admin, request)

    admin_id = _admin_id(admin)
    ip = request.client.host if request.client else None

    async with get_db(request) as conn:
        exists = await conn.fetchval(
            "SELECT 1 FROM schools WHERE school_id = $1",
            uuid.UUID(school_id),
        )
        if not exists:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "not_found",
                    "detail": "School not found.",
                    "correlation_id": _cid(request),
                },
            )

        cleared = await clear_school_limits_override(conn, school_id, admin_id)

    if cleared is None:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "no_override",
                "detail": "No override exists for this school.",
                "correlation_id": _cid(request),
            },
        )

    write_audit_log(
        event_type="CLEAR_SCHOOL_LIMITS_OVERRIDE",
        actor_type="admin",
        actor_id=uuid.UUID(admin_id),
        target_type="school",
        target_id=uuid.UUID(school_id),
        metadata={"cleared_override": cleared},
        ip_address=ip,
    )

    return ClearOverrideResponse(status="override_cleared", school_id=school_id)
