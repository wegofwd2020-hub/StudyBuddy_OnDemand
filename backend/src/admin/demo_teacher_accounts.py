"""
backend/src/admin/demo_teacher_accounts.py

Admin endpoints for managing demo teacher accounts.

Routes (all prefixed /api/v1):
  GET  /admin/demo-teacher-accounts                         — list requests + accounts
  POST /admin/demo-teacher-accounts/{account_id}/extend     — extend expiry
  POST /admin/demo-teacher-accounts/{account_id}/revoke     — revoke account
  POST /admin/demo-teacher-requests/{request_id}/resend     — resend verification

Permission: super_admin or product_admin.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from src.auth.dependencies import get_current_admin
from src.core.db import get_db
from src.utils.logger import get_logger

log = get_logger("admin.demo_teacher")
router = APIRouter(tags=["admin"])


# ── RBAC dependency ───────────────────────────────────────────────────────────


async def _demo_admin_only(
    request: Request,
    admin: Annotated[dict, Depends(get_current_admin)],
) -> dict:
    if admin.get("role") not in ("super_admin", "product_admin"):
        raise HTTPException(
            status_code=403,
            detail={
                "error": "forbidden",
                "detail": "super_admin or product_admin required.",
                "correlation_id": getattr(request.state, "correlation_id", ""),
            },
        )
    return admin


# ── Schemas ───────────────────────────────────────────────────────────────────


class DemoTeacherAccountRow(BaseModel):
    request_id: str
    email: str
    request_status: str
    requested_at: datetime
    account_id: str | None
    teacher_id: str | None
    expires_at: datetime | None
    created_at: datetime | None
    last_login_at: datetime | None
    extended_at: datetime | None
    revoked_at: datetime | None


class DemoTeacherListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[DemoTeacherAccountRow]


class ExtendInput(BaseModel):
    hours: int  # 1–168


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get(
    "/admin/demo-teacher-accounts",
    response_model=DemoTeacherListResponse,
    summary="List demo teacher requests and accounts",
)
async def list_demo_teacher_accounts(
    _admin: Annotated[dict, Depends(_demo_admin_only)],
    request: Request,
    status: str | None = Query(None, description="Filter by request status"),
    email: str | None = Query(None, description="Filter by email (partial match)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    offset = (page - 1) * page_size

    conditions = []
    params: list = []
    idx = 1

    if status:
        conditions.append(f"dtr.status = ${idx}")
        params.append(status)
        idx += 1
    if email:
        conditions.append(f"dtr.email ILIKE ${idx}")
        params.append(f"%{email}%")
        idx += 1

    where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    async with get_db(request) as conn:
        total = await conn.fetchval(
            f"""
            SELECT COUNT(*)
            FROM demo_teacher_requests dtr
            {where_clause}
            """,
            *params,
        )

        rows = await conn.fetch(
            f"""
            SELECT
                dtr.id           AS request_id,
                dtr.email,
                dtr.status       AS request_status,
                dtr.requested_at,
                dta.id           AS account_id,
                dta.teacher_id,
                dta.expires_at,
                dta.created_at,
                dta.last_login_at,
                dta.extended_at,
                dta.revoked_at
            FROM demo_teacher_requests dtr
            LEFT JOIN demo_teacher_accounts dta ON dta.request_id = dtr.id
            {where_clause}
            ORDER BY dtr.requested_at DESC
            LIMIT ${idx} OFFSET ${idx + 1}
            """,
            *params,
            page_size,
            offset,
        )

    items = [
        DemoTeacherAccountRow(
            request_id=str(r["request_id"]),
            email=r["email"],
            request_status=r["request_status"],
            requested_at=r["requested_at"],
            account_id=str(r["account_id"]) if r["account_id"] else None,
            teacher_id=str(r["teacher_id"]) if r["teacher_id"] else None,
            expires_at=r["expires_at"],
            created_at=r["created_at"],
            last_login_at=r["last_login_at"],
            extended_at=r["extended_at"],
            revoked_at=r["revoked_at"],
        )
        for r in rows
    ]

    return DemoTeacherListResponse(total=total, page=page, page_size=page_size, items=items)


@router.post(
    "/admin/demo-teacher-accounts/{account_id}/extend",
    status_code=200,
    summary="Extend a demo teacher account's expiry",
)
async def extend_demo_teacher_account(
    account_id: uuid.UUID,
    body: ExtendInput,
    admin: Annotated[dict, Depends(_demo_admin_only)],
    request: Request,
):
    if not (1 <= body.hours <= 168):
        raise HTTPException(status_code=422, detail="hours must be between 1 and 168")

    async with get_db(request) as conn:
        row = await conn.fetchrow(
            """
            SELECT id, expires_at, revoked_at
            FROM demo_teacher_accounts WHERE id = $1
            """,
            account_id,
        )
        if row is None:
            raise HTTPException(status_code=404, detail="Account not found")
        if row["revoked_at"] is not None:
            raise HTTPException(status_code=409, detail="Account already revoked")

        from datetime import timedelta

        new_expires = row["expires_at"] + timedelta(hours=body.hours)
        await conn.execute(
            """
            UPDATE demo_teacher_accounts
            SET expires_at  = $1,
                extended_at = NOW(),
                extended_by = $2
            WHERE id = $3
            """,
            new_expires,
            uuid.UUID(admin["admin_id"]),
            account_id,
        )

    log.info("demo_teacher_account_extended", account_id=str(account_id), hours=body.hours)
    return {"message": f"Account extended by {body.hours} hour(s)."}


@router.post(
    "/admin/demo-teacher-accounts/{account_id}/revoke",
    status_code=200,
    summary="Revoke a demo teacher account",
)
async def revoke_demo_teacher_account(
    account_id: uuid.UUID,
    admin: Annotated[dict, Depends(_demo_admin_only)],
    request: Request,
):
    async with get_db(request) as conn:
        row = await conn.fetchrow(
            "SELECT id, teacher_id, request_id, revoked_at FROM demo_teacher_accounts WHERE id = $1",
            account_id,
        )
        if row is None:
            raise HTTPException(status_code=404, detail="Account not found")
        if row["revoked_at"] is not None:
            raise HTTPException(status_code=409, detail="Account already revoked")

        async with conn.transaction():
            await conn.execute(
                "UPDATE teachers SET account_status='deleted' WHERE teacher_id=$1",
                row["teacher_id"],
            )
            await conn.execute(
                "UPDATE demo_teacher_requests SET status='revoked' WHERE id=$1",
                row["request_id"],
            )
            await conn.execute(
                "UPDATE demo_teacher_accounts SET revoked_at=NOW(), revoked_by=$1 WHERE id=$2",
                uuid.UUID(admin["admin_id"]),
                account_id,
            )

    log.info("demo_teacher_account_revoked", account_id=str(account_id))
    return {"message": "Account revoked."}


@router.post(
    "/admin/demo-teacher-requests/{request_id}/resend",
    status_code=200,
    summary="Resend verification email for a pending teacher demo request",
)
async def resend_demo_teacher_verification(
    request_id: uuid.UUID,
    _admin: Annotated[dict, Depends(_demo_admin_only)],
    request: Request,
):
    from src.auth.tasks import send_demo_teacher_verification_email_task
    from src.demo.teacher_service import (
        create_demo_teacher_verification,
        replace_teacher_verification_token,
    )

    async with get_db(request) as conn:
        row = await conn.fetchrow(
            "SELECT id, email, status FROM demo_teacher_requests WHERE id = $1",
            request_id,
        )
        if row is None:
            raise HTTPException(status_code=404, detail="Request not found")
        if row["status"] != "pending":
            raise HTTPException(
                status_code=409,
                detail=f"Request status is '{row['status']}' — can only resend for pending requests.",
            )

        pending_verif = await conn.fetchrow(
            """
            SELECT id, request_id FROM demo_teacher_verifications
            WHERE request_id = $1 AND used_at IS NULL AND expires_at > NOW()
            ORDER BY created_at DESC LIMIT 1
            """,
            request_id,
        )

        if pending_verif:
            new_token = await replace_teacher_verification_token(conn, request_id, row["email"])
        else:
            new_token = await create_demo_teacher_verification(conn, request_id, row["email"])

    send_demo_teacher_verification_email_task.delay(row["email"], new_token)
    log.info("admin_demo_teacher_verification_resent", request_id=str(request_id))
    return {"message": "Verification email resent."}
