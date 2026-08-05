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
  GET  /content/{unit_id}/scenario         → ScenarioResponse
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

import re
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
    ScenarioResponse,
    TutorialResponse,
)
from src.content.service import (
    check_content_block,
    check_content_published,
    get_content_file,
    get_entitlement,
    get_next_quiz_set,
    increment_lessons_accessed,
    resolve_curriculum_id,
)
from src.core.redis_client import get_redis
from src.core.storage import StorageBackend, get_storage
from src.core.subjects import display_subject, resolve_subject_labels
from src.utils.logger import get_logger

log = get_logger("content")
router = APIRouter(tags=["content"])

_FREE_TIER_LESSON_LIMIT = 2


async def _subject_display_name(pool, unit_id: str, fallback: str | None) -> str:
    """Resolve a unit's human-readable subject name for the quiz result screen
    (#461), falling back to whatever the content file stored (#462 semantics)."""
    async with pool.acquire() as conn:
        labels = await resolve_subject_labels(conn, [unit_id])
    return display_subject(labels, unit_id, fallback)


_GRADE_RE = re.compile(r"^G(\d+)-")


def _normalize_lesson(data: dict) -> dict:
    """
    Normalise pipeline lesson JSON to the LessonResponse wire format.

    Three input formats are handled in priority order:

    1. Old format (has 'title'): pass through — already in wire format.
    2. New rich format (has 'sections'): use sections + key_points directly.
    3. Legacy minimal format (synopsis/key_concepts only, no sections): synthesize
       sections from synopsis/learning_objectives/reading_level so existing
       pre-C5-regen content renders as well as possible until regenerated.
    """
    if "title" in data:
        # Old format — already in wire format
        return data

    uid = data.get("unit_id", "")
    m = _GRADE_RE.match(uid)
    grade = int(m.group(1)) if m else 0
    base = {
        "unit_id": uid,
        "title": data.get("topic", uid),
        "grade": grade,
        "subject": data.get("subject", ""),
        "lang": data.get("language", "en"),
        "has_audio": data.get("has_audio", False),
        "generated_at": data.get("generated_at"),
        "model": data.get("model"),
        "content_version": data.get("content_version"),
    }

    if "sections" in data:
        # New rich format — sections and key_points are already correct shape
        base["sections"] = data["sections"]
        base["key_points"] = data.get("key_points") or data.get("key_concepts", [])
        return base

    # Legacy minimal format: synthesize sections from available metadata fields
    sections = []
    if synopsis := data.get("synopsis"):
        sections.append({"heading": "Overview", "body": synopsis})
    if objectives := data.get("learning_objectives"):
        body = "\n".join(f"- {o}" for o in objectives)
        sections.append({"heading": "Learning Objectives", "body": body})
    if reading_level := data.get("reading_level"):
        sections.append({"heading": "Reading Level", "body": reading_level})
    base["sections"] = sections
    base["key_points"] = data.get("key_concepts", [])
    return base


# ── Helpers ───────────────────────────────────────────────────────────────────


async def _get_curriculum_and_check_published(
    request: Request,
    unit_id: str,
    content_type: str,
    student_payload: dict,
    pre_resolved_curriculum_id: str | None = None,
) -> tuple[str, str]:
    """
    Resolve curriculum_id and subject, then check published + block guards.

    Returns (serving_curriculum_id, subject). For school fork curricula,
    serving_curriculum_id is the source OOB curriculum_id so that
    curriculum_units and content_subject_versions lookups work correctly.
    Raises HTTPException 404 if not published, 403 if blocked.
    """
    from src.content.service import resolve_content_curriculum as _rcc

    redis = get_redis(request)
    pool = request.app.state.pool
    student_id = student_payload["student_id"]
    grade = student_payload.get("grade", 8)
    school_id = student_payload.get("school_id")

    curriculum_id = pre_resolved_curriculum_id or await resolve_curriculum_id(
        student_id, grade, pool, redis, school_id=school_id
    )

    # Fork→OOB fallback: school fork curricula have no rows in curriculum_units
    # (those live under the source OOB curriculum_id). Swap to the OOB id so that
    # the published check and content store reads work. This is the SAME helper the
    # quiz grading path uses, so the two can no longer drift (#529).
    curriculum_id, subject = await _rcc(unit_id, curriculum_id, school_id, pool)

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
    storage: StorageBackend = Depends(get_storage),
):
    """
    Serve a lesson for the given unit.

    Entitlement guard: free-tier students are limited to 2 lessons.
    Increments lessons_accessed after serving.
    """
    from src.content.service import get_active_override as _gao

    redis = get_redis(request)
    pool = request.app.state.pool
    student_id = student["student_id"]
    locale = student.get("locale", "en")
    school_id = student.get("school_id")

    # Active override path: school students may have teacher-authored content.
    pre_resolved: str | None = None
    if school_id:
        pre_resolved = await resolve_curriculum_id(
            student_id, student.get("grade", 8), pool, redis, school_id=school_id
        )
        override = await _gao(school_id, pre_resolved, unit_id, locale, "lesson", pool, redis)
        if override:
            try:
                await increment_lessons_accessed(student_id, pool, redis, school_id=school_id)
            except Exception as exc:
                log.warning(
                    "increment_lessons_accessed_failed student_id=%s error=%s", student_id, exc
                )
            log.info("lesson_override_served unit_id=%s student_id=%s", unit_id, student_id)
            return LessonResponse(**_normalize_lesson(override))

    curriculum_id, _subject = await _get_curriculum_and_check_published(
        request, unit_id, "lesson", student, pre_resolved_curriculum_id=pre_resolved
    )

    # Entitlement check — demo students get full access for the duration of their
    # 24-hour trial; the TTL on their account is the effective subscription limit.
    if student.get("role") != "demo_student":
        entitlement = await get_entitlement(student_id, pool, redis, school_id=school_id)
        if (
            entitlement["plan"] == "free"
            and entitlement["lessons_accessed"] >= _FREE_TIER_LESSON_LIMIT
        ):
            raise HTTPException(
                status_code=402,
                detail={
                    "error": "subscription_required",
                    "detail": "Upgrade to StudyBuddy Premium to unlock all lessons.",
                },
            )

    filename = f"lesson_{locale}.json"
    try:
        data = await get_content_file(curriculum_id, unit_id, filename, redis, storage)
    except FileNotFoundError:
        try:
            data = await get_content_file(curriculum_id, unit_id, "lesson_en.json", redis, storage)
        except FileNotFoundError:
            raise HTTPException(
                status_code=404,
                detail={"error": "not_found", "detail": "Lesson content not found."},
            )

    try:
        await increment_lessons_accessed(student_id, pool, redis, school_id=school_id)
    except Exception as exc:
        log.warning("increment_lessons_accessed_failed student_id=%s error=%s", student_id, exc)

    log.info("lesson_served unit_id=%s student_id=%s", unit_id, student_id)
    return LessonResponse(**_normalize_lesson(data))


# ── GET /content/{unit_id}/lesson/audio ──────────────────────────────────────


@router.get("/content/{unit_id}/lesson/audio", response_model=AudioUrlResponse)
async def get_lesson_audio(
    unit_id: str,
    request: Request,
    student: Annotated[dict, Depends(get_current_student)],
    storage: StorageBackend = Depends(get_storage),
):
    """
    Return a URL for the lesson MP3 audio file.

    For local dev (LocalStorage): returns a /static/content/... URL.
    For production (S3Storage): returns a pre-signed S3 URL valid for 1 hour.

    Never proxies audio bytes through this server.
    """
    locale = student.get("locale", "en")
    student_id = student["student_id"]

    curriculum_id, _subject = await _get_curriculum_and_check_published(
        request, unit_id, "lesson", student
    )

    audio_path = f"curricula/{curriculum_id}/{unit_id}/lesson_{locale}.mp3"
    url = storage.audio_url(audio_path, ttl_seconds=3600)
    log.info("audio_url_served unit_id=%s student_id=%s", unit_id, student_id)
    return AudioUrlResponse(url=url, expires_in=3600)


# ── GET /content/{unit_id}/quiz ───────────────────────────────────────────────


def _strip_answer_key(data: dict) -> dict:
    """
    Remove `correct_option` and `explanation` from every question before the quiz
    leaves the server.

    Shipping the answer key to the browser meant a student could read the correct
    answers straight out of the network response. The key is revealed one question
    at a time by POST /progress/session/{id}/answer, after the student commits to
    a choice — which is also where grading now happens.

    Copies rather than mutating: `data` may be the dict cached in L2/L1, and
    stripping it in place would poison the cache for the grader.
    """
    return {
        **data,
        "questions": [
            {k: v for k, v in q.items() if k not in ("correct_option", "explanation")}
            for q in data.get("questions", [])
        ],
    }


# exclude_none: the answer-key fields are stripped above, so they serialise as
# null. Omit them entirely rather than shipping `"correct_option": null` — a null
# there reads like an oversight and invites someone to "fix" it by populating it.
@router.get(
    "/content/{unit_id}/quiz", response_model=QuizResponse, response_model_exclude_none=True
)
async def get_quiz(
    unit_id: str,
    request: Request,
    student: Annotated[dict, Depends(get_current_student)],
    storage: StorageBackend = Depends(get_storage),
):
    """
    Serve a quiz set, rotating through sets 1→2→3→1 per student per unit.
    """
    from src.content.service import get_active_override as _gao

    redis = get_redis(request)
    pool = request.app.state.pool
    student_id = student["student_id"]
    locale = student.get("locale", "en")
    school_id = student.get("school_id")

    set_number = await get_next_quiz_set(student_id, unit_id, redis)
    quiz_content_type = f"quiz_set_{set_number}"

    # Active override path: school students may have teacher-authored quiz sets.
    pre_resolved: str | None = None
    if school_id:
        pre_resolved = await resolve_curriculum_id(
            student_id, student.get("grade", 8), pool, redis, school_id=school_id
        )
        override = await _gao(
            school_id, pre_resolved, unit_id, locale, quiz_content_type, pool, redis
        )
        if override:
            log.info(
                "quiz_override_served unit_id=%s set=%d student_id=%s",
                unit_id,
                set_number,
                student_id,
            )
            override["subject"] = await _subject_display_name(
                pool, unit_id, override.get("subject")
            )
            return QuizResponse(**_strip_answer_key(override))

    curriculum_id, _subject = await _get_curriculum_and_check_published(
        request, unit_id, "quiz", student, pre_resolved_curriculum_id=pre_resolved
    )

    filename = f"quiz_set_{set_number}_{locale}.json"
    try:
        data = await get_content_file(curriculum_id, unit_id, filename, redis, storage)
    except FileNotFoundError:
        try:
            data = await get_content_file(
                curriculum_id, unit_id, f"quiz_set_{set_number}_en.json", redis, storage
            )
        except FileNotFoundError:
            raise HTTPException(
                status_code=404,
                detail={"error": "not_found", "detail": f"Quiz set {set_number} not found."},
            )

    data["subject"] = await _subject_display_name(pool, unit_id, _subject or data.get("subject"))
    log.info("quiz_served unit_id=%s set=%d student_id=%s", unit_id, set_number, student_id)
    return QuizResponse(**_strip_answer_key(data))


# ── GET /content/{unit_id}/tutorial ──────────────────────────────────────────


@router.get("/content/{unit_id}/tutorial", response_model=TutorialResponse)
async def get_tutorial(
    unit_id: str,
    request: Request,
    student: Annotated[dict, Depends(get_current_student)],
    storage: StorageBackend = Depends(get_storage),
):
    """Serve the tutorial for a unit."""
    from src.content.service import get_active_override as _gao

    redis = get_redis(request)
    pool = request.app.state.pool
    locale = student.get("locale", "en")
    student_id = student["student_id"]
    school_id = student.get("school_id")

    # Active override path for school students.
    pre_resolved: str | None = None
    if school_id:
        pre_resolved = await resolve_curriculum_id(
            student_id, student.get("grade", 8), pool, redis, school_id=school_id
        )
        override = await _gao(school_id, pre_resolved, unit_id, locale, "tutorial", pool, redis)
        if override:
            log.info("tutorial_override_served unit_id=%s student_id=%s", unit_id, student_id)
            return TutorialResponse(**override)

    curriculum_id, _subject = await _get_curriculum_and_check_published(
        request, unit_id, "tutorial", student, pre_resolved_curriculum_id=pre_resolved
    )

    filename = f"tutorial_{locale}.json"
    try:
        data = await get_content_file(curriculum_id, unit_id, filename, redis, storage)
    except FileNotFoundError:
        try:
            data = await get_content_file(
                curriculum_id, unit_id, "tutorial_en.json", redis, storage
            )
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
    storage: StorageBackend = Depends(get_storage),
):
    """
    Serve the lab experiment for a unit.
    Returns 404 if no experiment file exists (non-lab unit).
    """
    from src.content.service import get_active_override as _gao

    redis = get_redis(request)
    pool = request.app.state.pool
    locale = student.get("locale", "en")
    student_id = student["student_id"]
    school_id = student.get("school_id")

    # Active override path for school students.
    pre_resolved: str | None = None
    if school_id:
        pre_resolved = await resolve_curriculum_id(
            student_id, student.get("grade", 8), pool, redis, school_id=school_id
        )
        override = await _gao(school_id, pre_resolved, unit_id, locale, "experiment", pool, redis)
        if override:
            log.info("experiment_override_served unit_id=%s student_id=%s", unit_id, student_id)
            return ExperimentResponse(**override)

    curriculum_id, _subject = await _get_curriculum_and_check_published(
        request, unit_id, "experiment", student, pre_resolved_curriculum_id=pre_resolved
    )

    filename = f"experiment_{locale}.json"
    try:
        data = await get_content_file(curriculum_id, unit_id, filename, redis, storage)
    except FileNotFoundError:
        try:
            data = await get_content_file(
                curriculum_id, unit_id, "experiment_en.json", redis, storage
            )
        except FileNotFoundError:
            raise HTTPException(
                status_code=404,
                detail={"error": "not_found", "detail": "No experiment available for this unit."},
            )

    log.info("experiment_served unit_id=%s student_id=%s", unit_id, student_id)
    return ExperimentResponse(**data)


# ── GET /content/{unit_id}/scenario ──────────────────────────────────────────


@router.get("/content/{unit_id}/scenario", response_model=ScenarioResponse)
async def get_scenario(
    unit_id: str,
    request: Request,
    student: Annotated[dict, Depends(get_current_student)],
    storage: StorageBackend = Depends(get_storage),
):
    """Serve the scenario-based training module for a unit."""
    redis = get_redis(request)
    locale = student.get("locale", "en")
    student_id = student["student_id"]

    curriculum_id, _subject = await _get_curriculum_and_check_published(
        request, unit_id, "scenario", student
    )

    filename = f"scenario_{locale}.json"
    try:
        data = await get_content_file(curriculum_id, unit_id, filename, redis, storage)
    except FileNotFoundError:
        try:
            data = await get_content_file(
                curriculum_id, unit_id, "scenario_en.json", redis, storage
            )
        except FileNotFoundError:
            raise HTTPException(
                status_code=404,
                detail={"error": "not_found", "detail": "No scenario available for this unit."},
            )

    # Optionally merge in video clips if avatar_worker has generated them.
    clips_file = f"scenario_clips_{locale}.json"
    try:
        clips_data = await get_content_file(curriculum_id, unit_id, clips_file, redis, storage)
        data["video_clips"] = clips_data.get("clips", [])
    except FileNotFoundError:
        try:
            clips_data = await get_content_file(
                curriculum_id, unit_id, "scenario_clips_en.json", redis, storage
            )
            data["video_clips"] = clips_data.get("clips", [])
        except FileNotFoundError:
            data["video_clips"] = None

    log.info(
        "scenario_served unit_id=%s student_id=%s clips=%s",
        unit_id,
        student_id,
        len(data.get("video_clips") or []),
    )
    return ScenarioResponse(**data)


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

    curriculum_id = await resolve_curriculum_id(
        student_id, student.get("grade", 8), pool, redis, school_id=student.get("school_id")
    )

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

    curriculum_id = await resolve_curriculum_id(
        student_id, student.get("grade", 8), pool, redis, school_id=student.get("school_id")
    )

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
):
    """
    Return the current minimum and latest app versions.

    No authentication required — called by the mobile app on startup before
    the user has logged in.  Version info is not sensitive.

    Loaded from the app_versions table (platform='all').
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
