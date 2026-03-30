"""
backend/src/content/router.py

Content delivery endpoints.

All routes require a valid student JWT (get_current_student dependency).
All routes are prefixed with /api/v1 in main.py.

Routes:
  GET  /content/{unit_id}/lesson           → LessonResponse
  GET  /content/{unit_id}/lesson/audio     → AudioUrlResponse
  GET  /content/{unit_id}/quiz             → QuizResponse (rotated set)
  GET  /content/{unit_id}/tutorial         → TutorialResponse
  GET  /content/{unit_id}/experiment       → ExperimentResponse
  POST /content/{unit_id}/report           → 200
  POST /content/{unit_id}/feedback/marked  → 200
  GET  /app/version                        → AppVersionResponse

Guards applied to all content endpoints:
  1. check_content_published → 404 if not published
  2. check_content_block     → 403 if blocked
  3. Entitlement (lesson only): 402 if free tier >= 2 lessons accessed

Rate limiting: 100 req/min per student JWT via slowapi.
"""

from __future__ import annotations

import os
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request

from src.auth.dependencies import get_current_student
from src.content.schemas import (
    AppVersionResponse,
    AudioUrlResponse,
    ExperimentResponse,
    FeedbackRequest,
    LessonResponse,
    QuizResponse,
    ReportRequest,
    TutorialResponse,
)
from src.content.service import (
    check_content_block,
    check_content_published,
    get_content_file,
    get_entitlement,
    get_next_quiz_set,
    get_unit_subject,
    increment_lessons_accessed,
    resolve_curriculum_id,
)
from src.core.redis_client import get_redis
from src.utils.logger import get_logger

log = get_logger("content")
router = APIRouter(tags=["content"])

_FREE_TIER_LESSON_LIMIT = 2


# ── Helpers ───────────────────────────────────────────────────────────────────


async def _get_curriculum_and_check_published(
    request: Request,
    unit_id: str,
    content_type: str,
    student_payload: dict,
) -> tuple[str, str]:
    """
    Resolve curriculum_id and subject, then check published + block guards.

    Returns (curriculum_id, subject).
    Raises HTTPException 404 if not published, 403 if blocked.
    """
    redis = get_redis(request)
    pool = request.app.state.pool
    student_id = student_payload["student_id"]
    grade = student_payload.get("grade", 8)

    curriculum_id = await resolve_curriculum_id(student_id, grade, pool, redis)

    subject = await get_unit_subject(unit_id, curriculum_id, pool)
    if subject is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "detail": f"Unit {unit_id} not found."},
        )

    published = await check_content_published(curriculum_id, subject, pool, redis)
    if not published:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "content_not_available",
                "detail": "Content for this unit is not yet published.",
            },
        )

    blocked = await check_content_block(curriculum_id, unit_id, content_type, pool)
    if blocked:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "content_blocked",
                "detail": "This content has been temporarily blocked.",
            },
        )

    return curriculum_id, subject


# ── GET /content/{unit_id}/lesson ─────────────────────────────────────────────


@router.get("/content/{unit_id}/lesson", response_model=LessonResponse)
async def get_lesson(
    unit_id: str,
    request: Request,
    student: Annotated[dict, Depends(get_current_student)],
):
    """
    Serve a lesson for the given unit.

    Entitlement guard: free-tier students are limited to 2 lessons.
    Increments lessons_accessed after serving.
    """
    redis = get_redis(request)
    pool = request.app.state.pool
    student_id = student["student_id"]
    locale = student.get("locale", "en")

    curriculum_id, subject = await _get_curriculum_and_check_published(
        request, unit_id, "lesson", student
    )

    # Entitlement check — demo students get full access for the duration of their
    # 24-hour trial; the TTL on their account is the effective subscription limit.
    if student.get("role") != "demo_student":
        entitlement = await get_entitlement(student_id, pool, redis)
        if entitlement["plan"] == "free" and entitlement["lessons_accessed"] >= _FREE_TIER_LESSON_LIMIT:
            raise HTTPException(
                status_code=402,
                detail={
                    "error": "subscription_required",
                    "detail": "Upgrade to StudyBuddy Premium to unlock all lessons.",
                },
            )

    filename = f"lesson_{locale}.json"
    try:
        data = await get_content_file(curriculum_id, unit_id, filename, redis)
    except FileNotFoundError:
        # Try English fallback
        try:
            data = await get_content_file(curriculum_id, unit_id, "lesson_en.json", redis)
        except FileNotFoundError:
            raise HTTPException(
                status_code=404,
                detail={"error": "not_found", "detail": "Lesson content not found."},
            )

    # Fire-and-forget: increment counter (async, no await-on-hot-path issues
    # since this is a simple DB upsert, not a Celery task in Phase 2)
    try:
        await increment_lessons_accessed(student_id, pool, redis)
    except Exception as exc:
        log.warning("increment_lessons_accessed_failed student_id=%s error=%s", student_id, exc)

    log.info("lesson_served unit_id=%s student_id=%s", unit_id, student_id)
    return LessonResponse(**data)


# ── GET /content/{unit_id}/lesson/audio ──────────────────────────────────────


@router.get("/content/{unit_id}/lesson/audio", response_model=AudioUrlResponse)
async def get_lesson_audio(
    unit_id: str,
    request: Request,
    student: Annotated[dict, Depends(get_current_student)],
):
    """
    Return a URL for the lesson MP3 audio file.

    For local dev (no S3): returns a /static/content/... URL.
    For production: returns a pre-signed S3 URL.

    Never proxies audio bytes through this server.
    """
    locale = student.get("locale", "en")
    student_id = student["student_id"]

    curriculum_id, _subject = await _get_curriculum_and_check_published(
        request, unit_id, "lesson", student
    )

    # Check if we have an S3 bucket configured
    s3_bucket = os.environ.get("S3_BUCKET_NAME", "")

    if s3_bucket:
        # Generate pre-signed S3 URL
        try:
            import boto3

            s3_client = boto3.client("s3")
            key = f"curricula/{curriculum_id}/{unit_id}/lesson_{locale}.mp3"
            url = s3_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": s3_bucket, "Key": key},
                ExpiresIn=3600,
            )
            return AudioUrlResponse(url=url, expires_in=3600)
        except Exception as exc:
            log.warning("s3_presign_failed unit_id=%s error=%s", unit_id, exc)

    # Local dev fallback: return static path
    url = f"/static/content/{curriculum_id}/{unit_id}/lesson_{locale}.mp3"
    log.info("audio_url_served unit_id=%s student_id=%s url=%s", unit_id, student_id, url)
    return AudioUrlResponse(url=url, expires_in=3600)


# ── GET /content/{unit_id}/quiz ───────────────────────────────────────────────


@router.get("/content/{unit_id}/quiz", response_model=QuizResponse)
async def get_quiz(
    unit_id: str,
    request: Request,
    student: Annotated[dict, Depends(get_current_student)],
):
    """
    Serve a quiz set, rotating through sets 1→2→3→1 per student per unit.
    """
    redis = get_redis(request)
    student_id = student["student_id"]
    locale = student.get("locale", "en")

    curriculum_id, _subject = await _get_curriculum_and_check_published(
        request, unit_id, "quiz", student
    )

    set_number = await get_next_quiz_set(student_id, unit_id, redis)
    filename = f"quiz_set_{set_number}_{locale}.json"

    try:
        data = await get_content_file(curriculum_id, unit_id, filename, redis)
    except FileNotFoundError:
        try:
            data = await get_content_file(
                curriculum_id, unit_id, f"quiz_set_{set_number}_en.json", redis
            )
        except FileNotFoundError:
            raise HTTPException(
                status_code=404,
                detail={"error": "not_found", "detail": f"Quiz set {set_number} not found."},
            )

    log.info("quiz_served unit_id=%s set=%d student_id=%s", unit_id, set_number, student_id)
    return QuizResponse(**data)


# ── GET /content/{unit_id}/tutorial ──────────────────────────────────────────


@router.get("/content/{unit_id}/tutorial", response_model=TutorialResponse)
async def get_tutorial(
    unit_id: str,
    request: Request,
    student: Annotated[dict, Depends(get_current_student)],
):
    """Serve the tutorial for a unit."""
    redis = get_redis(request)
    locale = student.get("locale", "en")
    student_id = student["student_id"]

    curriculum_id, _subject = await _get_curriculum_and_check_published(
        request, unit_id, "tutorial", student
    )

    filename = f"tutorial_{locale}.json"
    try:
        data = await get_content_file(curriculum_id, unit_id, filename, redis)
    except FileNotFoundError:
        try:
            data = await get_content_file(curriculum_id, unit_id, "tutorial_en.json", redis)
        except FileNotFoundError:
            raise HTTPException(
                status_code=404,
                detail={"error": "not_found", "detail": "Tutorial not found."},
            )

    log.info("tutorial_served unit_id=%s student_id=%s", unit_id, student_id)
    return TutorialResponse(**data)


# ── GET /content/{unit_id}/experiment ────────────────────────────────────────


@router.get("/content/{unit_id}/experiment", response_model=ExperimentResponse)
async def get_experiment(
    unit_id: str,
    request: Request,
    student: Annotated[dict, Depends(get_current_student)],
):
    """
    Serve the lab experiment for a unit.
    Returns 404 if no experiment file exists (non-lab unit).
    """
    redis = get_redis(request)
    locale = student.get("locale", "en")
    student_id = student["student_id"]

    curriculum_id, _subject = await _get_curriculum_and_check_published(
        request, unit_id, "experiment", student
    )

    filename = f"experiment_{locale}.json"
    try:
        data = await get_content_file(curriculum_id, unit_id, filename, redis)
    except FileNotFoundError:
        try:
            data = await get_content_file(curriculum_id, unit_id, "experiment_en.json", redis)
        except FileNotFoundError:
            raise HTTPException(
                status_code=404,
                detail={"error": "not_found", "detail": "No experiment available for this unit."},
            )

    log.info("experiment_served unit_id=%s student_id=%s", unit_id, student_id)
    return ExperimentResponse(**data)


# ── POST /content/{unit_id}/report ────────────────────────────────────────────


@router.post("/content/{unit_id}/report", status_code=200)
async def report_content(
    unit_id: str,
    body: ReportRequest,
    request: Request,
    student: Annotated[dict, Depends(get_current_student)],
):
    """
    Student reports a content issue.
    Stores in student_content_feedback table.
    """
    student_id = student["student_id"]
    pool = request.app.state.pool
    redis = get_redis(request)

    curriculum_id = await resolve_curriculum_id(student_id, student.get("grade", 8), pool, redis)

    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO student_content_feedback
                (student_id, unit_id, curriculum_id, content_type, category, message)
            VALUES ($1, $2, $3, 'lesson', $4, $5)
            """,
            student_id,
            unit_id,
            curriculum_id,
            body.category,
            body.message,
        )

    log.info(
        "content_report unit_id=%s student_id=%s category=%s", unit_id, student_id, body.category
    )
    return {"status": "ok"}


# ── POST /content/{unit_id}/feedback/marked ──────────────────────────────────


@router.post("/content/{unit_id}/feedback/marked", status_code=200)
async def submit_marked_feedback(
    unit_id: str,
    body: FeedbackRequest,
    request: Request,
    student: Annotated[dict, Depends(get_current_student)],
):
    """
    Student submits feedback on a specific marked portion of content.
    Stored as student_content_feedback with content_type from body.
    """
    student_id = student["student_id"]
    pool = request.app.state.pool
    redis = get_redis(request)

    curriculum_id = await resolve_curriculum_id(student_id, student.get("grade", 8), pool, redis)

    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO student_content_feedback
                (student_id, unit_id, curriculum_id, content_type, category, message)
            VALUES ($1, $2, $3, $4, 'other', $5)
            """,
            student_id,
            unit_id,
            curriculum_id,
            body.content_type,
            body.feedback_text,
        )

    log.info(
        "marked_feedback unit_id=%s student_id=%s content_type=%s",
        unit_id,
        student_id,
        body.content_type,
    )
    return {"status": "ok"}


# ── GET /app/version ──────────────────────────────────────────────────────────


@router.get("/app/version", response_model=AppVersionResponse)
async def get_app_version(
    request: Request,
    student: Annotated[dict, Depends(get_current_student)],
):
    """
    Return the current minimum and latest app versions.
    Loaded from the app_versions table (platform='all' or platform='ios'/'android').
    """
    pool = request.app.state.pool

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT min_version, latest_version FROM app_versions
            WHERE platform = 'all'
            ORDER BY id DESC
            LIMIT 1
            """
        )

    if row is None:
        return AppVersionResponse(min_version="0.1.0", latest_version="0.1.0")

    return AppVersionResponse(
        min_version=row["min_version"],
        latest_version=row["latest_version"],
    )
