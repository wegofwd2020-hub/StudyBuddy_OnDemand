"""
backend/src/admin/demo_accounts.py

Admin endpoints for managing demo student accounts.

Routes (all prefixed /api/v1 in main.py, require admin JWT):
  GET  /admin/demo-accounts                        — list all requests/accounts
  POST /admin/demo-accounts/{account_id}/extend    — extend TTL (1–168 hours)
  POST /admin/demo-accounts/{account_id}/revoke    — revoke active account
  POST /admin/demo-requests/{request_id}/resend    — resend verification email

Access: super_admin and product_admin (demo:manage permission).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from src.auth.dependencies import get_current_admin
from src.auth.tasks import send_demo_verification_email_task
from src.core.db import get_db
from src.demo.service import replace_verification_token
from src.utils.logger import get_logger

log = get_logger("admin.demo")
router = APIRouter(tags=["admin-demo"])

_MAX_EXTEND_HOURS = 168  # 7 days


# ── RBAC dependency ───────────────────────────────────────────────────────────


def _require_demo_manage():
    """Admin auth + demo:manage permission check."""

    async def dep(
        request: Request,
        admin: Annotated[dict, Depends(get_current_admin)],
    ) -> dict:
        role = admin.get("role", "")
        if role not in ("super_admin", "product_admin"):
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "forbidden",
                    "detail": "super_admin or product_admin role required.",
                    "correlation_id": getattr(request.state, "correlation_id", ""),
                },
            )
        return admin

    return dep


_demo_manage = _require_demo_manage()


# ── Schemas ───────────────────────────────────────────────────────────────────


class DemoAccountItem(BaseModel):
    """Single row in the admin demo accounts list."""

    request_id: UUID
    email: str
    requested_at: datetime
    request_status: str

    # Present only for verified accounts
    account_id: UUID | None = None
    expires_at: datetime | None = None
    account_created_at: datetime | None = None
    last_login_at: datetime | None = None
    extended_at: datetime | None = None
    revoked_at: datetime | None = None

    # Pending verification info
    verification_pending: bool = False
    verification_expires_at: datetime | None = None


class DemoAccountListResponse(BaseModel):
    items: list[DemoAccountItem]
    total: int
    page: int
    page_size: int


class ExtendRequest(BaseModel):
    hours: int = Field(default=24, ge=1, le=_MAX_EXTEND_HOURS)


# ── Service helpers ───────────────────────────────────────────────────────────


async def _list_demo_accounts(
    conn,
    status_filter: str | None,
    email_filter: str | None,
    offset: int,
    limit: int,
) -> list:
    where_clauses = []
    params: list = []
    p = 1

    if status_filter and status_filter != "all":
        where_clauses.append(f"dr.status = ${p}")
        params.append(status_filter)
        p += 1

    if email_filter:
        where_clauses.append(f"dr.email ILIKE ${p}")
        params.append(f"%{email_filter}%")
        p += 1

    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

    params.extend([limit, offset])
    rows = await conn.fetch(
        f"""
        SELECT
            dr.id           AS request_id,
            dr.email,
            dr.requested_at,
            dr.status       AS request_status,
            da.id           AS account_id,
            da.expires_at,
            da.created_at   AS account_created_at,
            da.last_login_at,
            da.extended_at,
            da.revoked_at,
            -- Latest unused, non-expired verification (if any)
            (
                SELECT dv.expires_at
                FROM demo_verifications dv
                WHERE dv.request_id = dr.id
                  AND dv.used_at IS NULL
                  AND dv.expires_at > NOW()
                ORDER BY dv.created_at DESC
                LIMIT 1
            ) AS verification_expires_at
        FROM demo_requests dr
        LEFT JOIN demo_accounts da ON da.request_id = dr.id
        {where_sql}
        ORDER BY dr.requested_at DESC
        LIMIT ${p} OFFSET ${p + 1}
        """,
        *params,
    )
    return rows


async def _count_demo_accounts(
    conn,
    status_filter: str | None,
    email_filter: str | None,
) -> int:
    where_clauses = []
    params: list = []
    p = 1

    if status_filter and status_filter != "all":
        where_clauses.append(f"dr.status = ${p}")
        params.append(status_filter)
        p += 1

    if email_filter:
        where_clauses.append(f"dr.email ILIKE ${p}")
        params.append(f"%{email_filter}%")
        p += 1

    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
    return await conn.fetchval(f"SELECT COUNT(*) FROM demo_requests dr {where_sql}", *params)


async def _get_active_account(conn, account_id: UUID):
    """Return active demo_account or raise 404/409."""
    row = await conn.fetchrow(
        """
        SELECT da.id, da.student_id, da.request_id, da.email,
               da.expires_at, da.revoked_at
        FROM demo_accounts da
        WHERE da.id = $1
        """,
        account_id,
    )
    return row


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get("/admin/demo-accounts", response_model=DemoAccountListResponse)
async def list_demo_accounts(
    request: Request,
    admin: Annotated[dict, Depends(_demo_manage)],
    status: str | None = Query(
        default=None, description="Filter by status: pending/verified/expired/revoked/all"
    ),
    email: str | None = Query(default=None, description="Partial email match"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    """List all demo account requests with optional filters."""
    offset = (page - 1) * page_size

    async with get_db(request) as conn:
        rows = await _list_demo_accounts(conn, status, email, offset, page_size)
        total = await _count_demo_accounts(conn, status, email)

    items = [
        DemoAccountItem(
            request_id=r["request_id"],
            email=r["email"],
            requested_at=r["requested_at"],
            request_status=r["request_status"],
            account_id=r["account_id"],
            expires_at=r["expires_at"],
            account_created_at=r["account_created_at"],
            last_login_at=r["last_login_at"],
            extended_at=r["extended_at"],
            revoked_at=r["revoked_at"],
            verification_pending=r["verification_expires_at"] is not None,
            verification_expires_at=r["verification_expires_at"],
        )
        for r in rows
    ]
    return DemoAccountListResponse(items=items, total=total, page=page, page_size=page_size)


@router.post("/admin/demo-accounts/{account_id}/extend", status_code=200)
async def extend_demo_account(
    account_id: UUID,
    body: ExtendRequest,
    request: Request,
    admin: Annotated[dict, Depends(_demo_manage)],
):
    """
    Extend a demo account's TTL.

    Sets expires_at = NOW() + {hours} hours (max 168 hours / 7 days).
    """
    cid = getattr(request.state, "correlation_id", "")
    admin_id = admin.get("admin_id")

    async with get_db(request) as conn:
        row = await _get_active_account(conn, account_id)
        if row is None:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "not_found",
                    "detail": "Demo account not found.",
                    "correlation_id": cid,
                },
            )
        if row["revoked_at"] is not None:
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "already_revoked",
                    "detail": "Cannot extend a revoked demo account.",
                    "correlation_id": cid,
                },
            )

        new_expires = datetime.now(UTC) + timedelta(hours=body.hours)
        updated = await conn.fetchrow(
            """
            UPDATE demo_accounts
            SET expires_at  = $2,
                extended_at = NOW(),
                extended_by = $3
            WHERE id = $1
            RETURNING id, email, expires_at, extended_at
            """,
            account_id,
            new_expires,
            admin_id,
        )

    log.info(
        "demo_account_extended",
        account_id=str(account_id),
        new_expires=str(new_expires),
        by=admin_id,
    )
    return {
        "account_id": str(updated["id"]),
        "email": updated["email"],
        "expires_at": updated["expires_at"].isoformat(),
        "extended_at": updated["extended_at"].isoformat(),
        "message": f"Demo account extended by {body.hours} hours.",
    }


@router.post("/admin/demo-accounts/{account_id}/revoke", status_code=200)
async def revoke_demo_account(
    account_id: UUID,
    request: Request,
    admin: Annotated[dict, Depends(_demo_manage)],
):
    """
    Revoke an active demo account immediately.

    - Sets demo_accounts.revoked_at / revoked_by
    - Marks demo_requests.status = 'revoked'
    - Soft-deletes the student row (account_status = 'deleted')
    """
    cid = getattr(request.state, "correlation_id", "")
    admin_id = admin.get("admin_id")

    async with get_db(request) as conn:
        row = await _get_active_account(conn, account_id)
        if row is None:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "not_found",
                    "detail": "Demo account not found.",
                    "correlation_id": cid,
                },
            )
        if row["revoked_at"] is not None:
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "already_revoked",
                    "detail": "Demo account is already revoked.",
                    "correlation_id": cid,
                },
            )

        await conn.execute(
            """
            UPDATE demo_accounts
            SET revoked_at = NOW(), revoked_by = $2
            WHERE id = $1
            """,
            account_id,
            admin_id,
        )
        await conn.execute(
            "UPDATE demo_requests SET status = 'revoked' WHERE id = $1",
            row["request_id"],
        )
        await conn.execute(
            "UPDATE students SET account_status = 'deleted' WHERE student_id = $1",
            row["student_id"],
        )

    log.info(
        "demo_account_revoked",
        account_id=str(account_id),
        email=row["email"],
        by=admin_id,
    )
    return {"message": "Demo account revoked.", "email": row["email"]}


@router.post("/admin/demo-requests/{request_id}/resend", status_code=200)
async def resend_demo_verification(
    request_id: UUID,
    request: Request,
    admin: Annotated[dict, Depends(_demo_manage)],
):
    """
    Resend the verification email for a pending demo request.

    Invalidates the current token and issues a fresh one.
    Does not enforce cooldown (admin override).
    """
    cid = getattr(request.state, "correlation_id", "")

    async with get_db(request) as conn:
        req_row = await conn.fetchrow(
            "SELECT id, email, status FROM demo_requests WHERE id = $1",
            request_id,
        )
        if req_row is None:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "not_found",
                    "detail": "Demo request not found.",
                    "correlation_id": cid,
                },
            )
        if req_row["status"] != "pending":
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "not_pending",
                    "detail": f"Demo request status is '{req_row['status']}', not pending.",
                    "correlation_id": cid,
                },
            )

        new_token = await replace_verification_token(conn, request_id, req_row["email"])

    send_demo_verification_email_task.delay(req_row["email"], new_token)

    log.info(
        "admin_demo_verification_resent",
        request_id=str(request_id),
        email=req_row["email"],
        by=admin.get("admin_id"),
    )
    return {
        "message": "Verification email resent.",
        "email": req_row["email"],
    }
