"""
backend/src/admin/router.py

Phase 7 admin API endpoints.

All routes require a valid admin JWT (signed with ADMIN_JWT_SECRET).
Permission checks are applied per-endpoint via _require(permission),
which chains get_current_admin → RBAC check in a single dependency so
FastAPI's dependency graph guarantees auth runs before the permission check.

Routes (all prefixed /api/v1 in main.py):

  GET    /admin/pipeline/status
  GET    /admin/content/review/queue
  POST   /admin/content/review/{version_id}/open
  POST   /admin/content/review/{version_id}/annotate
  DELETE /admin/content/review/annotations/{annotation_id}
  POST   /admin/content/review/{version_id}/rate
  POST   /admin/content/review/{version_id}/approve
  POST   /admin/content/review/{version_id}/reject
  POST   /admin/content/versions/{version_id}/publish
  POST   /admin/content/versions/{version_id}/rollback
  POST   /admin/content/block
  DELETE /admin/content/block/{block_id}
  GET    /admin/content/{unit_id}/feedback/marked
  GET    /admin/content/feedback/report
  GET    /admin/analytics/subscription
  GET    /admin/analytics/struggle
  GET    /admin/content/dictionary
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from src.admin.schemas import (
    AnnotateRequest,
    AnnotateResponse,
    ApproveRequest,
    ApproveResponse,
    BlockRequest,
    BlockResponse,
    DictionaryResponse,
    FeedbackListResponse,
    FeedbackReportResponse,
    OpenReviewRequest,
    OpenReviewResponse,
    PipelineStatusResponse,
    PublishResponse,
    RateRequest,
    RateResponse,
    RejectRequest,
    RejectResponse,
    ReviewQueueResponse,
    RollbackResponse,
    StruggleResponse,
    SubscriptionAnalyticsResponse,
    UnblockResponse,
)
from src.admin.service import (
    add_annotation,
    approve_version,
    create_block,
    delete_annotation,
    get_feedback_report,
    get_pipeline_status,
    get_struggle_report,
    get_subscription_analytics,
    list_feedback,
    list_review_queue,
    lookup_dictionary,
    open_review,
    publish_version,
    rate_version,
    reject_version,
    remove_block,
    rollback_version,
)
from src.auth.dependencies import get_current_admin
from src.core.db import get_db
from src.core.permissions import ROLE_PERMISSIONS
from src.core.redis_client import get_redis
from src.utils.logger import get_logger

log = get_logger("admin")
router = APIRouter(tags=["admin"])


# ── Combined auth + RBAC dependency ──────────────────────────────────────────
# Using a chained dependency ensures get_current_admin always runs first,
# setting request.state.jwt_payload before the permission check reads it.

def _require(permission: str):
    """
    Admin auth + permission check in one chained dependency.

    get_current_admin verifies the ADMIN_JWT_SECRET and sets
    request.state.jwt_payload.  This inner dep then enforces RBAC.
    """
    async def dep(
        request: Request,
        admin: Annotated[dict, Depends(get_current_admin)],
    ) -> dict:
        role = admin.get("role", "")
        perms = ROLE_PERMISSIONS.get(role, set())
        if "*" not in perms and permission not in perms:
            log.warning(
                "permission_denied",
                role=role,
                required=permission,
                actor_id=admin.get("admin_id"),
            )
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "forbidden",
                    "detail": f"Role '{role}' does not have permission '{permission}'.",
                    "correlation_id": getattr(request.state, "correlation_id", ""),
                },
            )
        return admin
    return dep


def _admin_id(admin: dict) -> str:
    return str(admin["admin_id"])


def _cid(request: Request) -> str:
    return getattr(request.state, "correlation_id", "")


# ── Pipeline status ───────────────────────────────────────────────────────────

@router.get(
    "/admin/pipeline/status",
    response_model=PipelineStatusResponse,
)
async def pipeline_status(
    request: Request,
    admin: Annotated[dict, Depends(_require("review:read"))],
) -> PipelineStatusResponse:
    """Return a summary of content pipeline runs and version statuses."""
    async with get_db(request) as conn:
        data = await get_pipeline_status(conn)
    return PipelineStatusResponse(**data)


# ── Review queue ──────────────────────────────────────────────────────────────

@router.get(
    "/admin/content/review/queue",
    response_model=ReviewQueueResponse,
)
async def review_queue(
    request: Request,
    admin: Annotated[dict, Depends(_require("review:read"))],
    status: str | None = Query(None),
    subject: str | None = Query(None),
    curriculum_id: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> ReviewQueueResponse:
    """List content subject versions, optionally filtered."""
    async with get_db(request) as conn:
        data = await list_review_queue(conn, status, subject, curriculum_id, limit, offset)
    return ReviewQueueResponse(**data)


# ── Open review session ───────────────────────────────────────────────────────

@router.post(
    "/admin/content/review/{version_id}/open",
    response_model=OpenReviewResponse,
)
async def open_review_session(
    version_id: str,
    body: OpenReviewRequest,
    request: Request,
    admin: Annotated[dict, Depends(_require("review:annotate"))],
) -> OpenReviewResponse:
    """Open a review session for a content subject version."""
    async with get_db(request) as conn:
        row = await open_review(conn, version_id, _admin_id(admin), body.notes)
    if not row:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "detail": "Version not found.", "correlation_id": _cid(request)},
        )
    return OpenReviewResponse(
        review_id=row["review_id"],
        version_id=row["version_id"],
        action=row["action"],
        reviewed_at=row["reviewed_at"],
    )


# ── Annotate ──────────────────────────────────────────────────────────────────

@router.post(
    "/admin/content/review/{version_id}/annotate",
    response_model=AnnotateResponse,
)
async def annotate(
    version_id: str,
    body: AnnotateRequest,
    request: Request,
    admin: Annotated[dict, Depends(_require("review:annotate"))],
) -> AnnotateResponse:
    """Add a text annotation to a unit within a content version."""
    async with get_db(request) as conn:
        row = await add_annotation(
            conn, version_id, _admin_id(admin),
            body.unit_id, body.content_type,
            body.marked_text, body.annotation_text,
            body.start_offset, body.end_offset,
        )
    return AnnotateResponse(
        annotation_id=row["annotation_id"],
        version_id=row["version_id"],
        unit_id=row["unit_id"],
        content_type=row["content_type"],
        annotation_text=row["annotation_text"],
        created_at=row["created_at"],
    )


@router.delete(
    "/admin/content/review/annotations/{annotation_id}",
)
async def delete_annotation_endpoint(
    annotation_id: str,
    request: Request,
    admin: Annotated[dict, Depends(_require("review:annotate"))],
) -> dict:
    """Delete an annotation by ID."""
    async with get_db(request) as conn:
        deleted = await delete_annotation(conn, annotation_id, _admin_id(admin))
    if not deleted:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "detail": "Annotation not found.", "correlation_id": _cid(request)},
        )
    return {"status": "deleted"}


# ── Rate ──────────────────────────────────────────────────────────────────────

@router.post(
    "/admin/content/review/{version_id}/rate",
    response_model=RateResponse,
)
async def rate(
    version_id: str,
    body: RateRequest,
    request: Request,
    admin: Annotated[dict, Depends(_require("review:rate"))],
) -> RateResponse:
    """Submit language and content ratings (1–5) for a version."""
    async with get_db(request) as conn:
        row = await rate_version(
            conn, version_id, _admin_id(admin),
            body.language_rating, body.content_rating, body.notes,
        )
    return RateResponse(
        review_id=row["review_id"],
        version_id=row["version_id"],
        language_rating=row["language_rating"],
        content_rating=row["content_rating"],
    )


# ── Approve ───────────────────────────────────────────────────────────────────

@router.post(
    "/admin/content/review/{version_id}/approve",
    response_model=ApproveResponse,
)
async def approve(
    version_id: str,
    body: ApproveRequest,
    request: Request,
    admin: Annotated[dict, Depends(_require("review:approve"))],
) -> ApproveResponse:
    """Approve a content version for publishing."""
    async with get_db(request) as conn:
        row = await approve_version(conn, version_id, _admin_id(admin), body.notes)
    return ApproveResponse(**row)


# ── Reject ────────────────────────────────────────────────────────────────────

@router.post(
    "/admin/content/review/{version_id}/reject",
    response_model=RejectResponse,
)
async def reject(
    version_id: str,
    body: RejectRequest,
    request: Request,
    admin: Annotated[dict, Depends(_require("review:approve"))],
) -> RejectResponse:
    """Reject a content version. Set regenerate=true to trigger pipeline rerun."""
    async with get_db(request) as conn:
        row = await reject_version(
            conn, version_id, _admin_id(admin), body.notes, body.regenerate
        )
    return RejectResponse(
        version_id=row["version_id"],
        status=row["status"],
        regenerating=row["regenerating"],
    )


# ── Publish ───────────────────────────────────────────────────────────────────

@router.post(
    "/admin/content/versions/{version_id}/publish",
    response_model=PublishResponse,
)
async def publish(
    version_id: str,
    request: Request,
    admin: Annotated[dict, Depends(_require("content:publish"))],
) -> PublishResponse:
    """
    Publish a content version.

    Archives the current published version, marks this one published,
    invalidates Redis content cache and CloudFront CDN.
    """
    redis = get_redis(request)
    async with get_db(request) as conn:
        row = await publish_version(conn, redis, version_id, _admin_id(admin))
    if not row:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "detail": "Version not found.", "correlation_id": _cid(request)},
        )
    return PublishResponse(
        version_id=row["version_id"],
        status=row["status"],
        published_at=row["published_at"],
    )


# ── Rollback ──────────────────────────────────────────────────────────────────

@router.post(
    "/admin/content/versions/{version_id}/rollback",
    response_model=RollbackResponse,
)
async def rollback(
    version_id: str,
    request: Request,
    admin: Annotated[dict, Depends(_require("content:rollback"))],
) -> RollbackResponse:
    """
    Rollback to a previous version.

    Archives the current published version and restores the target.
    Invalidates Redis and CDN.
    """
    redis = get_redis(request)
    async with get_db(request) as conn:
        row = await rollback_version(conn, redis, version_id, _admin_id(admin))
    if not row:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "detail": "Version not found.", "correlation_id": _cid(request)},
        )
    return RollbackResponse(**row)


# ── Content block ─────────────────────────────────────────────────────────────

@router.post(
    "/admin/content/block",
    response_model=BlockResponse,
    status_code=201,
)
async def block_content(
    body: BlockRequest,
    request: Request,
    admin: Annotated[dict, Depends(_require("content:block"))],
) -> BlockResponse:
    """Block a specific content item (school-scoped or platform-wide)."""
    async with get_db(request) as conn:
        row = await create_block(
            conn, body.curriculum_id, body.unit_id, body.content_type,
            body.reason, _admin_id(admin),
        )
    return BlockResponse(
        block_id=row["block_id"],
        curriculum_id=row["curriculum_id"],
        unit_id=row["unit_id"],
        content_type=row["content_type"],
        blocked_at=row["blocked_at"],
    )


@router.delete(
    "/admin/content/block/{block_id}",
    response_model=UnblockResponse,
)
async def unblock_content(
    block_id: str,
    request: Request,
    admin: Annotated[dict, Depends(_require("content:block"))],
) -> UnblockResponse:
    """Remove a content block."""
    async with get_db(request) as conn:
        removed = await remove_block(conn, block_id, _admin_id(admin))
    if not removed:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "detail": "Block not found.", "correlation_id": _cid(request)},
        )
    return UnblockResponse(status="unblocked")


# ── Student feedback ──────────────────────────────────────────────────────────

@router.get(
    "/admin/content/{unit_id}/feedback/marked",
    response_model=FeedbackListResponse,
)
async def feedback_marked(
    unit_id: str,
    request: Request,
    admin: Annotated[dict, Depends(_require("review:read"))],
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> FeedbackListResponse:
    """List student marked-text feedback for a unit."""
    async with get_db(request) as conn:
        data = await list_feedback(conn, unit_id, limit, offset)
    return FeedbackListResponse(**data)


@router.get(
    "/admin/content/feedback/report",
    response_model=FeedbackReportResponse,
)
async def feedback_report(
    request: Request,
    admin: Annotated[dict, Depends(_require("review:read"))],
    threshold: int = Query(3, ge=1, le=100),
    limit: int = Query(50, ge=1, le=200),
) -> FeedbackReportResponse:
    """Units with student feedback count >= threshold, ordered by report count desc."""
    async with get_db(request) as conn:
        data = await get_feedback_report(conn, threshold, limit)
    return FeedbackReportResponse(**data)


# ── Analytics ─────────────────────────────────────────────────────────────────

@router.get(
    "/admin/analytics/subscription",
    response_model=SubscriptionAnalyticsResponse,
)
async def subscription_analytics(
    request: Request,
    admin: Annotated[dict, Depends(_require("review:read"))],
) -> SubscriptionAnalyticsResponse:
    """Return subscription MRR, active counts, new/cancelled this month, churn rate."""
    async with get_db(request) as conn:
        data = await get_subscription_analytics(conn)
    return SubscriptionAnalyticsResponse(**data)


@router.get(
    "/admin/analytics/struggle",
    response_model=StruggleResponse,
)
async def struggle_analytics(
    request: Request,
    admin: Annotated[dict, Depends(_require("review:read"))],
    limit: int = Query(20, ge=1, le=100),
) -> StruggleResponse:
    """Return units ordered by struggle (mean_attempts desc, pass_rate asc)."""
    async with get_db(request) as conn:
        data = await get_struggle_report(conn, limit)
    return StruggleResponse(**data)


# ── Dictionary ────────────────────────────────────────────────────────────────

@router.get(
    "/admin/content/dictionary",
    response_model=DictionaryResponse,
)
async def dictionary(
    request: Request,
    admin: Annotated[dict, Depends(_require("review:read"))],
    word: str = Query(..., min_length=1, max_length=100),
) -> DictionaryResponse:
    """Look up definitions, synonyms, and antonyms via Datamuse (+ optional Merriam-Webster)."""
    data = await lookup_dictionary(word.strip().lower())
    return DictionaryResponse(**data)
