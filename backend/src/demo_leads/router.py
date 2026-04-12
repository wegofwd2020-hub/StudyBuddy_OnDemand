"""
backend/src/demo_leads/router.py

Public and PLAT-ADMIN endpoints for the self-serve demo lead system (Epic 7).

Public (rate-limited, no auth):
  POST /demo/tour/request     — submit a demo lead (Option C guided tour)

PLAT-ADMIN (requires admin JWT + demo:manage permission):
  GET  /admin/demo-leads              — list leads
  POST /admin/demo-leads/{id}/approve — approve lead, generate demo URL
  POST /admin/demo-leads/{id}/reject  — reject lead
  GET  /admin/demo-geo-blocks         — list blocked countries
  POST /admin/demo-geo-blocks         — add country block
  DELETE /admin/demo-geo-blocks/{cc}  — remove country block
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request

from config import settings
from src.auth.dependencies import get_current_admin
from src.core.db import get_db
from src.core.permissions import require_permission
from src.core.redis_client import get_redis
from src.demo_leads import service
from src.demo_leads.schemas import (
    DemoLeadApproveRequest,
    DemoLeadApproveResponse,
    DemoLeadListResponse,
    DemoLeadRejectRequest,
    DemoLeadRejectResponse,
    DemoLeadRequest,
    DemoLeadResponse,
    GeoBlockAddRequest,
    GeoBlockAddResponse,
    GeoBlockListResponse,
)
from src.email.service import send_demo_approval_email
from src.utils.logger import get_logger

log = get_logger("demo_leads")

router = APIRouter()

_DEMO_REQUEST_LIMIT = 3
_DEMO_REQUEST_WINDOW = 3600  # 1 hour


async def _demo_request_rate_limit(request: Request) -> None:
    """Rate-limit POST /demo/tour/request: 3 requests per IP per hour."""
    redis = get_redis(request)
    ip = request.client.host if request.client else "unknown"
    key = f"demo_req_rate:{ip}"
    count = await redis.incr(key)
    if count == 1:
        await redis.expire(key, _DEMO_REQUEST_WINDOW)
    if count > _DEMO_REQUEST_LIMIT:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "rate_limited",
                "detail": "Too many demo requests. Please try again later.",
            },
        )


def _cid(request: Request) -> str:
    return getattr(request.state, "correlation_id", "")


def _tour_url(role: str, token: str) -> str:
    base = settings.FRONTEND_URL.rstrip("/")
    role_path = {"admin": "school-admin", "teacher": "teacher", "student": "student"}[role]
    return f"{base}/tour/{role_path}?demo_token={token}"


# ── POST /demo/request ────────────────────────────────────────────────────────


@router.post(
    "/demo/tour/request",
    response_model=DemoLeadResponse,
    status_code=202,
)
async def request_demo(
    body: DemoLeadRequest,
    request: Request,
    _: None = Depends(_demo_request_rate_limit),
) -> DemoLeadResponse:
    """
    Submit a demo tour request.

    - Geo-blocked countries are rejected with 403.
    - Email already has an active (approved + unexpired) demo → 409.
    - Email lifetime limit reached (10 requests) → 429.
    - Otherwise creates a pending lead for PLAT-ADMIN review.
    """
    # Detect country from CF-IPCountry header (Cloudflare) or X-Country-Code
    ip_country: str | None = (
        request.headers.get("CF-IPCountry")
        or request.headers.get("X-Country-Code")
        or None
    )
    ip_address: str | None = request.headers.get("X-Forwarded-For", request.client.host if request.client else None)

    async with get_db(request) as conn:
        # Geo-lock check
        if ip_country and await service.is_country_blocked(conn, ip_country):
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "geo_blocked",
                    "detail": "Demo access is not available in your region.",
                    "correlation_id": _cid(request),
                },
            )

        # 1-active limit
        if await service.count_active_leads(conn, body.email) >= settings.DEMO_LEAD_ACTIVE_MAX:
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "active_demo_exists",
                    "detail": "You already have an active demo. Check your email for the tour link.",
                    "correlation_id": _cid(request),
                },
            )

        # Lifetime limit
        if await service.count_lifetime_leads(conn, body.email) >= settings.DEMO_LEAD_LIFETIME_MAX:
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "demo_limit_reached",
                    "detail": "You have reached the maximum number of demo requests.",
                    "correlation_id": _cid(request),
                },
            )

        await service.create_lead(
            conn,
            name=body.name,
            email=body.email,
            school_org=body.school_org,
            ip_country=ip_country,
            ip_address=ip_address,
        )

    return DemoLeadResponse(
        status="pending",
        message=(
            "Your demo request has been received. "
            "You'll get an email with your personalised tour link once it's approved — "
            "usually within one business day."
        ),
    )


# ── GET /admin/demo-leads ─────────────────────────────────────────────────────


@router.get(
    "/admin/demo-leads",
    response_model=DemoLeadListResponse,
    dependencies=[Depends(get_current_admin), Depends(require_permission("demo:manage"))],
)
async def list_demo_leads(
    request: Request,
    admin: Annotated[dict, Depends(get_current_admin)],
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> DemoLeadListResponse:
    """List demo leads. Optionally filter by status (pending/approved/rejected)."""
    if status and status not in ("pending", "approved", "rejected"):
        raise HTTPException(
            status_code=400,
            detail={"error": "invalid_status", "detail": "status must be pending, approved, or rejected"},
        )
    async with get_db(request) as conn:
        leads, total = await service.list_leads(conn, status=status, limit=min(limit, 200), offset=offset)
    return DemoLeadListResponse(leads=leads, total=total)


# ── POST /admin/demo-leads/{lead_id}/approve ──────────────────────────────────


@router.post(
    "/admin/demo-leads/{lead_id}/approve",
    response_model=DemoLeadApproveResponse,
    dependencies=[Depends(get_current_admin), Depends(require_permission("demo:manage"))],
)
async def approve_demo_lead(
    lead_id: str,
    body: DemoLeadApproveRequest,
    request: Request,
    admin: Annotated[dict, Depends(get_current_admin)],
) -> DemoLeadApproveResponse:
    """Approve a pending lead, generate personalised tour URLs, and email the requester."""
    async with get_db(request) as conn:
        result = await service.approve_lead(
            conn,
            lead_id=lead_id,
            admin_id=admin["admin_id"],
            ttl_hours=body.ttl_hours,
        )

    if result is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "detail": "Lead not found or already processed."},
        )

    token, expires_at = result

    # Fetch lead email/name for the confirmation email
    async with get_db(request) as conn:
        row = await conn.fetchrow(
            "SELECT name, email, school_org FROM demo_leads WHERE lead_id = $1",
            __import__("uuid").UUID(lead_id),
        )

    url_admin = _tour_url("admin", token)
    url_teacher = _tour_url("teacher", token)
    url_student = _tour_url("student", token)

    if row:
        try:
            await send_demo_approval_email(
                to_email=row["email"],
                name=row["name"],
                school_org=row["school_org"],
                url_admin=url_admin,
                url_teacher=url_teacher,
                url_student=url_student,
                expires_at=expires_at,
            )
        except Exception as exc:
            log.warning("demo_approval_email_failed lead_id=%s error=%s", lead_id, exc)

    return DemoLeadApproveResponse(
        lead_id=lead_id,
        demo_url_admin=url_admin,
        demo_url_teacher=url_teacher,
        demo_url_student=url_student,
        token_expires_at=expires_at,
    )


# ── POST /admin/demo-leads/{lead_id}/reject ───────────────────────────────────


@router.post(
    "/admin/demo-leads/{lead_id}/reject",
    response_model=DemoLeadRejectResponse,
    dependencies=[Depends(get_current_admin), Depends(require_permission("demo:manage"))],
)
async def reject_demo_lead(
    lead_id: str,
    body: DemoLeadRejectRequest,
    request: Request,
    admin: Annotated[dict, Depends(get_current_admin)],
) -> DemoLeadRejectResponse:
    """Reject a pending demo lead."""
    async with get_db(request) as conn:
        updated = await service.reject_lead(
            conn,
            lead_id=lead_id,
            admin_id=admin["admin_id"],
            reason=body.reason,
        )
    if not updated:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "detail": "Lead not found or already processed."},
        )
    return DemoLeadRejectResponse(lead_id=lead_id, status="rejected")


# ── GET /admin/demo-geo-blocks ────────────────────────────────────────────────


@router.get(
    "/admin/demo-geo-blocks",
    response_model=GeoBlockListResponse,
    dependencies=[Depends(get_current_admin), Depends(require_permission("demo:manage"))],
)
async def list_geo_blocks(
    request: Request,
    admin: Annotated[dict, Depends(get_current_admin)],
) -> GeoBlockListResponse:
    async with get_db(request) as conn:
        blocks = await service.list_geo_blocks(conn)
    return GeoBlockListResponse(blocks=blocks)


# ── POST /admin/demo-geo-blocks ───────────────────────────────────────────────


@router.post(
    "/admin/demo-geo-blocks",
    response_model=GeoBlockAddResponse,
    status_code=201,
    dependencies=[Depends(get_current_admin), Depends(require_permission("demo:manage"))],
)
async def add_geo_block(
    body: GeoBlockAddRequest,
    request: Request,
    admin: Annotated[dict, Depends(get_current_admin)],
) -> GeoBlockAddResponse:
    async with get_db(request) as conn:
        added = await service.add_geo_block(
            conn,
            country_code=body.country_code,
            country_name=body.country_name,
            admin_id=admin["admin_id"],
        )
    return GeoBlockAddResponse(country_code=body.country_code.upper(), added=added)


# ── DELETE /admin/demo-geo-blocks/{country_code} ──────────────────────────────


@router.delete(
    "/admin/demo-geo-blocks/{country_code}",
    status_code=200,
    dependencies=[Depends(get_current_admin), Depends(require_permission("demo:manage"))],
)
async def remove_geo_block(
    country_code: str,
    request: Request,
    admin: Annotated[dict, Depends(get_current_admin)],
) -> dict:
    async with get_db(request) as conn:
        removed = await service.remove_geo_block(conn, country_code)
    if not removed:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "detail": f"No geo block for {country_code.upper()}."},
        )
    return {"status": "removed", "country_code": country_code.upper()}
