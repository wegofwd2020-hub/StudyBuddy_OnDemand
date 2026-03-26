"""
backend/src/school/router.py

Phase 8 school endpoints.

Routes (all prefixed /api/v1 in main.py):

  POST /schools/register                     — create school + school_admin (public)
  GET  /schools/{school_id}                  — school profile (teacher-scoped)
  POST /schools/{school_id}/teachers/invite  — invite a teacher (school_admin only)
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request

from src.auth.dependencies import get_current_teacher
from src.core.db import get_db
from src.school.schemas import (
    SchoolProfileResponse,
    SchoolRegisterRequest,
    SchoolRegisterResponse,
    TeacherInviteRequest,
    TeacherInviteResponse,
)
from src.school.service import fetch_school, invite_teacher, register_school
from src.utils.logger import get_logger

log = get_logger("school")
router = APIRouter(tags=["school"])


def _cid(request: Request) -> str:
    return getattr(request.state, "correlation_id", "")


# ── School registration (public — no JWT required) ────────────────────────────

@router.post(
    "/schools/register",
    response_model=SchoolRegisterResponse,
    status_code=201,
)
async def register_school_endpoint(
    body: SchoolRegisterRequest,
    request: Request,
) -> SchoolRegisterResponse:
    """
    Register a new school.

    Auto-approves the school and creates a school_admin teacher account.
    Returns an access token for immediate use.
    """
    async with get_db(request) as conn:
        try:
            result = await register_school(
                conn, body.school_name, body.contact_email, body.country
            )
        except Exception as exc:
            if "unique" in str(exc).lower():
                raise HTTPException(
                    status_code=409,
                    detail={
                        "error": "conflict",
                        "detail": "A teacher account with that email already exists.",
                        "correlation_id": _cid(request),
                    },
                )
            raise
    return SchoolRegisterResponse(**result)


# ── School profile ────────────────────────────────────────────────────────────

@router.get(
    "/schools/{school_id}",
    response_model=SchoolProfileResponse,
)
async def get_school_profile(
    school_id: str,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
) -> SchoolProfileResponse:
    """Return the profile for the teacher's school."""
    async with get_db(request) as conn:
        school = await fetch_school(conn, school_id, teacher["school_id"])
    if not school:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "detail": "School not found.", "correlation_id": _cid(request)},
        )
    return SchoolProfileResponse(**school)


# ── Teacher invite ────────────────────────────────────────────────────────────

@router.post(
    "/schools/{school_id}/teachers/invite",
    response_model=TeacherInviteResponse,
    status_code=201,
)
async def invite_teacher_endpoint(
    school_id: str,
    body: TeacherInviteRequest,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
) -> TeacherInviteResponse:
    """Invite a new teacher to the school (school_admin only)."""
    if teacher.get("role") != "school_admin":
        raise HTTPException(
            status_code=403,
            detail={
                "error": "forbidden",
                "detail": "Only school_admin can invite teachers.",
                "correlation_id": _cid(request),
            },
        )
    if teacher["school_id"] != school_id:
        raise HTTPException(
            status_code=403,
            detail={"error": "forbidden", "detail": "Cannot invite to a different school.", "correlation_id": _cid(request)},
        )
    async with get_db(request) as conn:
        try:
            result = await invite_teacher(conn, school_id, body.name, body.email)
        except Exception as exc:
            if "unique" in str(exc).lower():
                raise HTTPException(
                    status_code=409,
                    detail={"error": "conflict", "detail": "Teacher email already registered.", "correlation_id": _cid(request)},
                )
            raise
    return TeacherInviteResponse(**result)
