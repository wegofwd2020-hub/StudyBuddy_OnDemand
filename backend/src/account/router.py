"""
backend/src/account/router.py

Account management endpoints (product_admin / super_admin only).

Routes:
  PATCH /account/students/{student_id}/status
  PATCH /account/teachers/{teacher_id}/status
  PATCH /account/schools/{school_id}/status   ← cascades via Celery

Account status transition rules (studybuddy-docs/PHASE1_SETUP.md section 10.4):
  pending   → active     (system, not via this endpoint)
  active    → suspended  (product_admin, super_admin)
  suspended → active     (product_admin, super_admin)
  active    → deleted    (product_admin, super_admin — via DELETE endpoint, not here)
  deleted   → *          (NEVER — terminal state)

Prefixed with /api/v1 in main.py.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request

from src.account.schemas import (
    AccountStatusUpdate,
    SchoolStatusResponse,
    StudentStatusResponse,
    TeacherStatusResponse,
)
from src.auth.dependencies import get_current_admin
from src.auth.tasks import cascade_school_suspension
from src.core.db import get_db
from src.core.events import emit_event, write_audit_log
from src.core.redis_client import get_redis
from src.utils.logger import get_logger

log = get_logger("account")
router = APIRouter(tags=["account"])

# Roles that may manage accounts.
_ACCOUNT_ADMIN_ROLES = {"product_admin", "super_admin"}


def _require_account_admin(admin: dict) -> None:
    if admin.get("role") not in _ACCOUNT_ADMIN_ROLES:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "forbidden",
                "detail": "product_admin or super_admin role required.",
            },
        )


# ── Student status ────────────────────────────────────────────────────────────


@router.patch("/account/students/{student_id}/status", response_model=StudentStatusResponse)
async def update_student_status(
    student_id: uuid.UUID,
    body: AccountStatusUpdate,
    request: Request,
    admin: Annotated[dict, Depends(get_current_admin)],
):
    """
    Suspend or reactivate a student account.

    On suspend:     SET suspended:{student_id} 1  (no TTL)
    On reactivate:  DEL suspended:{student_id}
    """
    _require_account_admin(admin)
    cid = getattr(request.state, "correlation_id", "")
    redis = get_redis(request)

    async with get_db(request) as conn:
        row = await conn.fetchrow(
            "SELECT student_id, name, email, account_status FROM students WHERE student_id = $1",
            student_id,
        )

    if not row:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "detail": "Student not found.", "correlation_id": cid},
        )

    current_status = row["account_status"]
    new_status = body.status

    _validate_transition(current_status, new_status, cid)

    async with get_db(request) as conn:
        updated = await conn.fetchrow(
            "UPDATE students SET account_status = $1 WHERE student_id = $2 RETURNING *",
            new_status,
            student_id,
        )

    # Update Redis suspension key.
    if new_status == "suspended":
        await redis.set(f"suspended:{student_id}", "1")
        # Trigger Auth0 block asynchronously.
        _dispatch_auth0_sync(str(student_id), "block", conn=None)
    else:
        await redis.delete(f"suspended:{student_id}")
        _dispatch_auth0_sync(str(student_id), "unblock", conn=None)

    emit_event(
        "account",
        "student_status_changed",
        student_id=str(student_id),
        old_status=current_status,
        new_status=new_status,
        admin_id=admin["admin_id"],
    )
    write_audit_log(
        "student_status_changed",
        "admin",
        uuid.UUID(admin["admin_id"]),
        target_type="student",
        target_id=student_id,
        metadata={"old_status": current_status, "new_status": new_status},
    )

    return StudentStatusResponse(
        student_id=updated["student_id"],
        name=updated["name"],
        email=updated["email"],
        account_status=updated["account_status"],
    )


# ── Teacher status ────────────────────────────────────────────────────────────


@router.patch("/account/teachers/{teacher_id}/status", response_model=TeacherStatusResponse)
async def update_teacher_status(
    teacher_id: uuid.UUID,
    body: AccountStatusUpdate,
    request: Request,
    admin: Annotated[dict, Depends(get_current_admin)],
):
    """Suspend or reactivate a teacher account."""
    _require_account_admin(admin)
    cid = getattr(request.state, "correlation_id", "")
    redis = get_redis(request)

    async with get_db(request) as conn:
        row = await conn.fetchrow(
            "SELECT teacher_id, school_id, name, email, account_status FROM teachers WHERE teacher_id = $1",
            teacher_id,
        )

    if not row:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "detail": "Teacher not found.", "correlation_id": cid},
        )

    current_status = row["account_status"]
    new_status = body.status

    _validate_transition(current_status, new_status, cid)

    async with get_db(request) as conn:
        updated = await conn.fetchrow(
            "UPDATE teachers SET account_status = $1 WHERE teacher_id = $2 RETURNING *",
            new_status,
            teacher_id,
        )

    if new_status == "suspended":
        await redis.set(f"suspended:{teacher_id}", "1")
    else:
        await redis.delete(f"suspended:{teacher_id}")

    emit_event(
        "account",
        "teacher_status_changed",
        teacher_id=str(teacher_id),
        old_status=current_status,
        new_status=new_status,
    )
    write_audit_log(
        "teacher_status_changed",
        "admin",
        uuid.UUID(admin["admin_id"]),
        target_type="teacher",
        target_id=teacher_id,
        metadata={"old_status": current_status, "new_status": new_status},
    )

    return TeacherStatusResponse(
        teacher_id=updated["teacher_id"],
        school_id=updated["school_id"],
        name=updated["name"],
        email=updated["email"],
        account_status=updated["account_status"],
    )


# ── School status (cascades to members via Celery) ────────────────────────────


@router.patch("/account/schools/{school_id}/status", response_model=SchoolStatusResponse)
async def update_school_status(
    school_id: uuid.UUID,
    body: AccountStatusUpdate,
    request: Request,
    admin: Annotated[dict, Depends(get_current_admin)],
):
    """
    Suspend or reactivate a school.

    On suspension: cascades to all teachers + students via Celery.
    On reactivation: does NOT automatically reactivate members
    (per studybuddy-docs/PHASE1_SETUP.md section 10.6).
    """
    _require_account_admin(admin)
    cid = getattr(request.state, "correlation_id", "")

    async with get_db(request) as conn:
        row = await conn.fetchrow(
            "SELECT school_id, name, status FROM schools WHERE school_id = $1",
            school_id,
        )

    if not row:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "detail": "School not found.", "correlation_id": cid},
        )

    current_status = row["status"]
    new_status = body.status

    _validate_transition(current_status, new_status, cid)

    async with get_db(request) as conn:
        updated = await conn.fetchrow(
            "UPDATE schools SET status = $1 WHERE school_id = $2 RETURNING *",
            new_status,
            school_id,
        )

    # Cascade suspension to all school members via Celery.
    if new_status == "suspended":
        cascade_school_suspension.delay(str(school_id), new_status)

    emit_event(
        "account",
        "school_status_changed",
        school_id=str(school_id),
        old_status=current_status,
        new_status=new_status,
    )
    write_audit_log(
        "school_status_changed",
        "admin",
        uuid.UUID(admin["admin_id"]),
        target_type="school",
        target_id=school_id,
        metadata={"old_status": current_status, "new_status": new_status},
    )

    return SchoolStatusResponse(
        school_id=updated["school_id"],
        name=updated["name"],
        status=updated["status"],
    )


# ── Helpers ───────────────────────────────────────────────────────────────────


def _validate_transition(current: str, new: str, cid: str) -> None:
    """Enforce allowed status transitions."""
    if current == "deleted":
        raise HTTPException(
            status_code=409,
            detail={
                "error": "conflict",
                "detail": "Cannot change status of a deleted account.",
                "correlation_id": cid,
            },
        )
    if current == new:
        raise HTTPException(
            status_code=409,
            detail={
                "error": "conflict",
                "detail": f"Account is already {new}.",
                "correlation_id": cid,
            },
        )


def _dispatch_auth0_sync(user_id: str, action: str, conn) -> None:
    """Fire-and-forget Auth0 block/unblock — swallow import errors gracefully."""
    try:
        from src.auth.tasks import sync_auth0_suspension

        sync_auth0_suspension.delay(user_id, action)
    except Exception as exc:
        log.warning("auth0_sync_dispatch_failed", error=str(exc))
