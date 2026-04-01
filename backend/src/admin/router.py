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
  GET    /admin/content/review/{version_id}
  POST   /admin/content/review/{version_id}/open
  POST   /admin/content/review/{version_id}/annotate
  DELETE /admin/content/review/annotations/{annotation_id}
  POST   /admin/content/review/{version_id}/rate
  POST   /admin/content/review/{version_id}/approve
  POST   /admin/content/review/{version_id}/reject
  POST   /admin/content/review/{version_id}/block
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

import json
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile

from src.admin.schemas import (
    AdminPipelineTriggerRequest,
    AdminPipelineTriggerResponse,
    AnnotateRequest,
    AnnotateResponse,
    ApproveRequest,
    ApproveResponse,
    BlockRequest,
    BlockResponse,
    BlockVersionRequest,
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
    ReviewDetailResponse,
    ReviewQueueResponse,
    RollbackResponse,
    StruggleResponse,
    SubscriptionAnalyticsResponse,
    UnblockResponse,
    UnitContentFileResponse,
    UnitContentMetaResponse,
    UploadGradeJsonResponse,
)
from src.admin.service import (
    add_annotation,
    approve_version,
    block_version,
    create_block,
    delete_annotation,
    get_feedback_report,
    get_pipeline_status,
    get_review_detail,
    get_struggle_report,
    get_subscription_analytics,
    get_unit_content_file,
    get_unit_content_meta,
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


# ── Review detail ─────────────────────────────────────────────────────────────


@router.get(
    "/admin/content/review/{version_id}",
    response_model=ReviewDetailResponse,
)
async def review_detail(
    version_id: str,
    request: Request,
    admin: Annotated[dict, Depends(_require("review:read"))],
) -> ReviewDetailResponse:
    """Return full detail for a single content version: metadata, units, review history, annotations."""
    async with get_db(request) as conn:
        data = await get_review_detail(conn, version_id)
    if not data:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "not_found",
                "detail": "Version not found.",
                "correlation_id": _cid(request),
            },
        )
    return ReviewDetailResponse(**data)


# ── Open review session ───────────────────────────────────────────────────────


@router.get(
    "/admin/content/review/{version_id}/unit/{unit_id}",
    response_model=UnitContentMetaResponse,
)
async def unit_content_meta(
    version_id: str,
    unit_id: str,
    request: Request,
    admin: Annotated[dict, Depends(_require("review:read"))],
    lang: str = Query("en", min_length=2, max_length=5),
) -> UnitContentMetaResponse:
    """Return unit title and list of available content type files on disk."""
    async with get_db(request) as conn:
        data = await get_unit_content_meta(conn, version_id, unit_id, lang)
    if not data:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "not_found",
                "detail": "Unit or version not found.",
                "correlation_id": _cid(request),
            },
        )
    return UnitContentMetaResponse(**data)


@router.get(
    "/admin/content/review/{version_id}/unit/{unit_id}/{content_type}",
    response_model=UnitContentFileResponse,
)
async def unit_content_file(
    version_id: str,
    unit_id: str,
    content_type: str,
    request: Request,
    admin: Annotated[dict, Depends(_require("review:read"))],
    lang: str = Query("en", min_length=2, max_length=5),
) -> UnitContentFileResponse:
    """Read and return raw content JSON for the specified type from disk."""
    async with get_db(request) as conn:
        try:
            data = await get_unit_content_file(conn, version_id, unit_id, content_type, lang)
        except FileNotFoundError:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "not_found",
                    "detail": f"Content file '{content_type}_{lang}.json' not found.",
                    "correlation_id": _cid(request),
                },
            )
    if not data:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "not_found",
                "detail": "Version not found.",
                "correlation_id": _cid(request),
            },
        )
    return UnitContentFileResponse(**data)


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
            detail={
                "error": "not_found",
                "detail": "Version not found.",
                "correlation_id": _cid(request),
            },
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
            conn,
            version_id,
            _admin_id(admin),
            body.unit_id,
            body.content_type,
            body.marked_text,
            body.annotation_text,
            body.start_offset,
            body.end_offset,
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
            detail={
                "error": "not_found",
                "detail": "Annotation not found.",
                "correlation_id": _cid(request),
            },
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
            conn,
            version_id,
            _admin_id(admin),
            body.language_rating,
            body.content_rating,
            body.notes,
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
        row = await reject_version(conn, version_id, _admin_id(admin), body.notes, body.regenerate)
    return RejectResponse(
        version_id=row["version_id"],
        status=row["status"],
        regenerating=row["regenerating"],
    )


# ── Block version ─────────────────────────────────────────────────────────────


@router.post(
    "/admin/content/review/{version_id}/block",
    response_model=BlockResponse,
    status_code=200,
)
async def block_version_endpoint(
    version_id: str,
    body: BlockVersionRequest,
    request: Request,
    admin: Annotated[dict, Depends(_require("content:block"))],
) -> BlockResponse:
    """Block a unit's content type and mark the subject version as blocked."""
    async with get_db(request) as conn:
        try:
            row = await block_version(
                conn,
                version_id,
                body.unit_id,
                body.content_type,
                body.reason,
                _admin_id(admin),
            )
        except ValueError:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "not_found",
                    "detail": "Version not found.",
                    "correlation_id": _cid(request),
                },
            )
    return BlockResponse(**row)


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
            detail={
                "error": "not_found",
                "detail": "Version not found.",
                "correlation_id": _cid(request),
            },
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
            detail={
                "error": "not_found",
                "detail": "Version not found.",
                "correlation_id": _cid(request),
            },
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
            conn,
            body.curriculum_id,
            body.unit_id,
            body.content_type,
            body.reason,
            _admin_id(admin),
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
            detail={
                "error": "not_found",
                "detail": "Block not found.",
                "correlation_id": _cid(request),
            },
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


# ── Admin pipeline: upload grade JSON + trigger build ─────────────────────────


@router.post(
    "/admin/pipeline/upload-grade",
    response_model=UploadGradeJsonResponse,
    status_code=200,
)
async def upload_grade_json(
    request: Request,
    admin: Annotated[dict, Depends(_require("content:publish"))],
    file: UploadFile = File(...),
    year: int = Query(2026, ge=2024, le=2040),
) -> UploadGradeJsonResponse:
    """
    Validate a grade JSON file, save it to /data/grade{N}_stem.json,
    and seed the curricula + curriculum_units tables.
    """
    import os

    raw = await file.read()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "validation_error",
                "detail": "File is not valid JSON.",
                "errors": [str(exc)],
            },
        )

    errors: list[str] = []

    grade = data.get("grade")
    if not isinstance(grade, int) or grade < 5 or grade > 12:
        errors.append("'grade' must be an integer between 5 and 12.")

    subjects = data.get("subjects")
    if not isinstance(subjects, list) or len(subjects) == 0:
        errors.append("'subjects' must be a non-empty list.")
        subjects = []

    for si, subj in enumerate(subjects):
        if not isinstance(subj, dict):
            errors.append(f"subjects[{si}] must be an object.")
            continue
        if not subj.get("subject_id"):
            errors.append(f"subjects[{si}] missing 'subject_id'.")
        if not subj.get("name"):
            errors.append(f"subjects[{si}] missing 'name'.")
        units = subj.get("units")
        if not isinstance(units, list) or len(units) == 0:
            errors.append(f"subjects[{si}] 'units' must be a non-empty list.")
            continue
        for ui, unit in enumerate(units):
            if not isinstance(unit, dict):
                errors.append(f"subjects[{si}].units[{ui}] must be an object.")
                continue
            if not unit.get("unit_id"):
                errors.append(f"subjects[{si}].units[{ui}] missing 'unit_id'.")
            if not unit.get("title"):
                errors.append(f"subjects[{si}].units[{ui}] missing 'title'.")

    if errors:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "validation_error",
                "detail": f"{len(errors)} validation error(s) found.",
                "errors": errors,
            },
        )

    dest_path = f"/data/grade{grade}_stem.json"
    os.makedirs("/data", exist_ok=True)
    with open(dest_path, "wb") as fh:
        fh.write(raw)

    curriculum_id = f"default-{year}-g{grade}"
    curriculum_name = f"Grade {grade} STEM ({year})"

    async with get_db(request) as conn:
        await conn.execute(
            """
            INSERT INTO curricula (curriculum_id, grade, year, name, is_default)
            VALUES ($1, $2, $3, $4, true)
            ON CONFLICT (curriculum_id) DO NOTHING
            """,
            curriculum_id,
            grade,
            year,
            curriculum_name,
        )
        sort_order = 0
        for subj in subjects:
            subject_id = subj["subject_id"]
            for unit in subj.get("units", []):
                await conn.execute(
                    """
                    INSERT INTO curriculum_units
                        (unit_id, curriculum_id, subject, title, unit_name, description, has_lab, sort_order)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    ON CONFLICT (unit_id, curriculum_id) DO NOTHING
                    """,
                    unit["unit_id"],
                    curriculum_id,
                    subject_id,
                    unit["title"],
                    unit["title"],
                    unit.get("description", ""),
                    bool(unit.get("has_lab", False)),
                    sort_order,
                )
                sort_order += 1

    unit_count = sum(len(subj.get("units", [])) for subj in subjects)
    log.info(
        "upload_grade_json_complete curriculum_id=%s grade=%d units=%d",
        curriculum_id,
        grade,
        unit_count,
    )
    return UploadGradeJsonResponse(
        curriculum_id=curriculum_id,
        grade=grade,
        unit_count=unit_count,
        subject_count=len(subjects),
    )


@router.post(
    "/admin/pipeline/trigger",
    response_model=AdminPipelineTriggerResponse,
    status_code=202,
)
async def admin_trigger_pipeline(
    body: AdminPipelineTriggerRequest,
    request: Request,
    admin: Annotated[dict, Depends(_require("content:publish"))],
) -> AdminPipelineTriggerResponse:
    """
    Dispatch a run_grade_pipeline_task Celery job for the given grade.

    Returns immediately with job_id; poll GET /admin/pipeline/{job_id}/status
    for progress. Content is built with auto_approve=False so all output goes
    to the review queue.
    """
    from src.auth.tasks import celery_app as _celery

    curriculum_id = f"default-{body.year}-g{body.grade}"

    async with get_db(request) as conn:
        row = await conn.fetchrow(
            "SELECT curriculum_id FROM curricula WHERE curriculum_id = $1",
            curriculum_id,
        )
    if not row:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "not_found",
                "detail": f"Curriculum '{curriculum_id}' not found. Upload the grade JSON first.",
                "correlation_id": _cid(request),
            },
        )

    job_id = str(uuid.uuid4())
    admin_id = _admin_id(admin)
    redis = get_redis(request)
    job_state = {
        "job_id": job_id,
        "curriculum_id": curriculum_id,
        "status": "queued",
        "built": 0,
        "failed": 0,
        "total": 0,
        "progress_pct": 0.0,
        "langs": body.langs,
    }
    await redis.setex(f"pipeline:job:{job_id}", 86400 * 7, json.dumps(job_state))

    async with get_db(request) as conn:
        await conn.execute(
            """
            INSERT INTO pipeline_jobs
                (job_id, curriculum_id, grade, langs, force, status, triggered_by)
            VALUES ($1, $2, $3, $4, $5, 'queued', $6)
            """,
            job_id,
            curriculum_id,
            body.grade,
            body.langs,
            body.force,
            uuid.UUID(admin_id) if admin_id else None,
        )

    _celery.send_task(
        "src.auth.tasks.run_grade_pipeline_task",
        args=[job_id, body.grade, body.langs, body.force, body.year],
        queue="pipeline",
    )

    log.info(
        "admin_pipeline_trigger job_id=%s curriculum_id=%s grade=%d langs=%s",
        job_id,
        curriculum_id,
        body.grade,
        body.langs,
    )
    return AdminPipelineTriggerResponse(
        job_id=job_id,
        status="queued",
        curriculum_id=curriculum_id,
    )


@router.get("/admin/pipeline/jobs")
async def admin_pipeline_jobs(
    request: Request,
    admin: Annotated[dict, Depends(_require("review:read"))],
    limit: int = Query(50, ge=1, le=200),
) -> dict:
    """Return paginated pipeline job history from DB, enriched with live Redis status."""
    redis = get_redis(request)
    async with get_db(request) as conn:
        rows = await conn.fetch(
            """
            SELECT pj.job_id, pj.curriculum_id, pj.grade, pj.langs, pj.force,
                   pj.status, pj.built, pj.failed, pj.total,
                   pj.triggered_at, pj.started_at, pj.completed_at, pj.error,
                   pj.payload_bytes,
                   au.email AS triggered_by_email
            FROM pipeline_jobs pj
            LEFT JOIN admin_users au ON au.admin_user_id = pj.triggered_by
            ORDER BY pj.triggered_at DESC
            LIMIT $1
            """,
            limit,
        )

    jobs = []
    for r in rows:
        job = dict(r)
        # Overlay live Redis state for running/queued jobs
        raw = await redis.get(f"pipeline:job:{job['job_id']}")
        if raw:
            live = json.loads(raw)
            job["status"] = live.get("status", job["status"])
            job["built"] = live.get("built", job["built"])
            job["failed"] = live.get("failed", job["failed"])
            job["total"] = live.get("total", job["total"])
        jobs.append(job)

    return {"jobs": jobs, "total": len(jobs)}


@router.get(
    "/admin/pipeline/{job_id}/status",
)
async def admin_pipeline_job_status(
    job_id: str,
    request: Request,
    admin: Annotated[dict, Depends(_require("review:read"))],
) -> dict:
    """Return the current job state, preferring live Redis data with DB fallback."""
    redis = get_redis(request)
    raw = await redis.get(f"pipeline:job:{job_id}")
    if raw:
        return json.loads(raw)
    # Fallback to DB for completed jobs whose Redis key has expired
    async with get_db(request) as conn:
        row = await conn.fetchrow(
            """
            SELECT job_id, curriculum_id, grade, langs, status, built, failed, total,
                   triggered_at, started_at, completed_at, error, payload_bytes
            FROM pipeline_jobs WHERE job_id = $1
            """,
            job_id,
        )
    if not row:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "not_found",
                "detail": "Pipeline job not found.",
                "correlation_id": _cid(request),
            },
        )
    return dict(row)
