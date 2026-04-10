"""
backend/src/school/pipeline_router.py

School-scoped pipeline endpoints.

Routes (all prefixed /api/v1 in main.py):
  POST /schools/{school_id}/curriculum/upload   — validate + store grade JSON, seed curriculum
  POST /schools/{school_id}/pipeline/trigger    — trigger Celery build (quota + concurrency gated)
  GET  /schools/{school_id}/pipeline            — list pipeline jobs for this school
  GET  /schools/{school_id}/pipeline/{job_id}   — job detail (403 if wrong school)

Auth:
  All endpoints require a teacher or school_admin JWT.
  The school_id in the path must match the JWT's school_id claim.

Quota:
  Monthly pipeline run limit resolved from school_plan_overrides (if set)
  then plan-level defaults from settings (SCHOOL_PIPELINE_QUOTA_*).
  Exceeding the quota returns HTTP 429.

Concurrency:
  Only one running/queued job per (school_id, grade) at a time.
  Duplicate trigger returns HTTP 409.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from pydantic import BaseModel

from config import settings
from src.auth.dependencies import get_current_teacher
from src.core.db import get_db
from src.core.redis_client import get_redis
from src.utils.logger import get_logger

log = get_logger("school.pipeline")
router = APIRouter(tags=["school-pipeline"])


# ── Schemas ───────────────────────────────────────────────────────────────────


VERSION_CAP = 5

class UploadCurriculumResponse(BaseModel):
    curriculum_id: str
    grade: int
    year: int
    unit_count: int
    subject_count: int
    subjects: list[str]
    version_count: int  # how many curriculum versions this school now holds for this grade
    version_cap: int = VERSION_CAP


class PipelineTriggerRequest(BaseModel):
    langs: str = "en"
    force: bool = False
    year: int = 2026


class PipelineTriggerResponse(BaseModel):
    job_id: str
    status: str
    curriculum_id: str


# ── Helpers ───────────────────────────────────────────────────────────────────


def _cid(request: Request) -> str:
    return getattr(request.state, "correlation_id", "")


def _assert_school_match(teacher: dict, school_id: str, request: Request) -> None:
    if teacher.get("school_id") != school_id:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "forbidden",
                "detail": "You can only access pipeline for your own school.",
                "correlation_id": _cid(request),
            },
        )


async def _resolve_quota(conn, school_id: str, plan: str | None) -> int:
    """Return the monthly pipeline quota for this school.

    Resolution order:
    1. Per-school override from school_plan_overrides
    2. Plan-level default from settings
    """
    override = await conn.fetchval(
        "SELECT pipeline_quota FROM school_plan_overrides WHERE school_id = $1::uuid",
        school_id,
    )
    if override is not None:
        return override
    mapping = {
        "starter": settings.SCHOOL_PIPELINE_QUOTA_STARTER,
        "professional": settings.SCHOOL_PIPELINE_QUOTA_PROFESSIONAL,
        "enterprise": settings.SCHOOL_PIPELINE_QUOTA_ENTERPRISE,
    }
    return mapping.get(plan or "starter", settings.SCHOOL_PIPELINE_QUOTA_STARTER)


# ── POST /schools/{school_id}/curriculum/upload ───────────────────────────────


@router.post(
    "/schools/{school_id}/curriculum/upload",
    response_model=UploadCurriculumResponse,
    status_code=200,
)
async def upload_school_curriculum(
    school_id: str,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
    file: UploadFile = File(...),
    year: int = Query(2026, ge=2024, le=2040),
) -> UploadCurriculumResponse:
    """
    Validate and store a grade JSON file for this school.

    Seeds the curricula and curriculum_units tables with ON CONFLICT DO NOTHING
    so re-uploads add new units without overwriting existing ones. Use
    pipeline trigger with force=True to rebuild content for changed units.
    """
    _assert_school_match(teacher, school_id, request)

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

    curriculum_id = f"{school_id}-{year}-g{grade}"
    curriculum_name = f"School Grade {grade} Curriculum ({year})"
    unit_count = sum(len(s.get("units", [])) for s in subjects)

    async with get_db(request) as conn:
        # ── Version cap check ─────────────────────────────────────────────────
        # Only applies when this would create a NEW curricula row.
        # Re-uploading the same year+grade is idempotent (ON CONFLICT DO NOTHING)
        # and does not count as a new version.
        existing_id = await conn.fetchval(
            "SELECT curriculum_id FROM curricula WHERE curriculum_id = $1",
            curriculum_id,
        )
        if not existing_id:
            version_count = await conn.fetchval(
                """
                SELECT COUNT(*) FROM curricula
                WHERE school_id = $1::uuid AND grade = $2
                  AND retention_status <> 'purged'
                """,
                school_id, grade,
            )
            if version_count >= VERSION_CAP:
                raise HTTPException(
                    status_code=409,
                    detail={
                        "error": "version_cap_reached",
                        "message": (
                            f"Grade {grade} already has {VERSION_CAP} curriculum versions. "
                            f"Remove a version before uploading a new one."
                        ),
                        "current_count": int(version_count),
                        "cap": VERSION_CAP,
                        "correlation_id": _cid(request),
                    },
                )

        await conn.execute(
            """
            INSERT INTO curricula
                (curriculum_id, grade, year, name, is_default, source_type, school_id,
                 status, owner_type, owner_id, expires_at)
            VALUES ($1, $2, $3, $4, false, 'school', $5::uuid, 'draft',
                    'school', $5::uuid, NOW() + INTERVAL '1 year')
            ON CONFLICT (curriculum_id) DO NOTHING
            """,
            curriculum_id, grade, year, curriculum_name, school_id,
        )
        sort_order = 0
        for subj in subjects:
            subj_name = subj["name"]
            for unit in subj.get("units", []):
                await conn.execute(
                    """
                    INSERT INTO curriculum_units
                        (unit_id, curriculum_id, subject, title, unit_name,
                         description, has_lab, sort_order)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    ON CONFLICT (unit_id, curriculum_id) DO NOTHING
                    """,
                    unit["unit_id"], curriculum_id, subj_name,
                    unit["title"], unit["title"],
                    unit.get("description", ""),
                    bool(unit.get("has_lab", False)),
                    sort_order,
                )
                sort_order += 1

        # Fetch updated version count for the response (purged versions don't count)
        final_version_count = await conn.fetchval(
            """
            SELECT COUNT(*) FROM curricula
            WHERE school_id = $1::uuid AND grade = $2
              AND retention_status <> 'purged'
            """,
            school_id, grade,
        )

    log.info(
        "school_curriculum_upload school_id=%s curriculum_id=%s grade=%d units=%d versions=%d",
        school_id, curriculum_id, grade, unit_count, final_version_count,
    )
    return UploadCurriculumResponse(
        curriculum_id=curriculum_id,
        grade=grade,
        year=year,
        unit_count=unit_count,
        subject_count=len(subjects),
        subjects=[s["name"] for s in subjects],
        version_count=int(final_version_count),
    )


# ── POST /schools/{school_id}/pipeline/trigger ────────────────────────────────


@router.post(
    "/schools/{school_id}/pipeline/trigger",
    response_model=PipelineTriggerResponse,
    status_code=202,
)
async def trigger_school_pipeline(
    school_id: str,
    body: PipelineTriggerRequest,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
) -> PipelineTriggerResponse:
    """
    Trigger the content pipeline for a school-owned curriculum.

    Checks (in order):
    1. JWT school_id matches path school_id
    2. Monthly quota not exceeded
    3. No running/queued job for the same school + grade
    4. Curriculum record exists for this school

    Dispatches run_curriculum_pipeline_task to the 'pipeline' Celery queue
    and returns immediately with the job_id.
    """
    from src.core.celery_app import celery_app as _celery

    _assert_school_match(teacher, school_id, request)
    teacher_id = teacher.get("teacher_id", "")
    curriculum_id = f"{school_id}-{body.year}-g"

    async with get_db(request) as conn:
        # Resolve school plan for quota calculation
        sub_row = await conn.fetchrow(
            "SELECT plan FROM school_subscriptions WHERE school_id = $1::uuid",
            school_id,
        )
        plan = sub_row["plan"] if sub_row else "starter"

        # 1. Monthly quota check
        quota = await _resolve_quota(conn, school_id, plan)
        used_this_month = await conn.fetchval(
            """
            SELECT COUNT(*) FROM pipeline_jobs
            WHERE school_id = $1::uuid
              AND triggered_at >= date_trunc('month', NOW())
              AND status NOT IN ('failed', 'cancelled')
            """,
            school_id,
        )
        if used_this_month >= quota:
            # Calculate first day of next month for resets_at
            now = datetime.now(UTC)
            if now.month == 12:
                resets_at = now.replace(year=now.year + 1, month=1, day=1,
                                        hour=0, minute=0, second=0, microsecond=0)
            else:
                resets_at = now.replace(month=now.month + 1, day=1,
                                        hour=0, minute=0, second=0, microsecond=0)
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "quota_exceeded",
                    "limit": quota,
                    "used": used_this_month,
                    "resets_at": resets_at.isoformat(),
                    "correlation_id": _cid(request),
                },
            )

        # Derive grade from curriculum upload: find curricula for this school
        curriculum_row = await conn.fetchrow(
            """
            SELECT curriculum_id, grade FROM curricula
            WHERE school_id = $1::uuid AND grade IS NOT NULL
              AND curriculum_id LIKE $2
            ORDER BY created_at DESC LIMIT 1
            """,
            school_id,
            f"{school_id}-{body.year}-g%",
        )
        if not curriculum_row:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "not_found",
                    "detail": "No curriculum found for this school and year. Upload a grade JSON first.",
                    "correlation_id": _cid(request),
                },
            )
        curriculum_id = curriculum_row["curriculum_id"]
        grade = curriculum_row["grade"]

        # 2. Concurrency check
        conflict_row = await conn.fetchrow(
            """
            SELECT job_id, status FROM pipeline_jobs
            WHERE school_id = $1::uuid
              AND grade = $2
              AND status IN ('queued', 'running')
            LIMIT 1
            """,
            school_id, grade,
        )
        if conflict_row:
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "pipeline_already_running",
                    "job_id": conflict_row["job_id"],
                    "status": conflict_row["status"],
                    "correlation_id": _cid(request),
                },
            )

        # Create job record
        job_id = str(uuid.uuid4())
        await conn.execute(
            """
            INSERT INTO pipeline_jobs
                (job_id, curriculum_id, grade, langs, force, status,
                 school_id, triggered_by_teacher_id)
            VALUES ($1, $2, $3, $4, $5, 'queued', $6::uuid, $7::uuid)
            """,
            job_id, curriculum_id, grade, body.langs, body.force,
            school_id,
            teacher_id if teacher_id else None,
        )

    # Seed Redis job state for live polling
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

    # Dispatch to pipeline queue
    _celery.send_task(
        "src.auth.tasks.run_curriculum_pipeline_task",
        args=[job_id, curriculum_id, body.langs, body.force, teacher_id],
        queue="pipeline",
    )

    log.info(
        "school_pipeline_trigger school_id=%s job_id=%s curriculum_id=%s grade=%d langs=%s",
        school_id, job_id, curriculum_id, grade, body.langs,
    )
    return PipelineTriggerResponse(
        job_id=job_id,
        status="queued",
        curriculum_id=curriculum_id,
    )


# ── GET /schools/{school_id}/pipeline ────────────────────────────────────────


@router.get("/schools/{school_id}/pipeline")
async def list_school_pipeline_jobs(
    school_id: str,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> dict:
    """List pipeline jobs for this school, newest first."""
    _assert_school_match(teacher, school_id, request)
    redis = get_redis(request)
    offset = (page - 1) * page_size

    conditions = ["pj.school_id = $1::uuid"]
    params: list = [school_id]
    idx = 2

    if status:
        conditions.append(f"pj.status = ${idx}")
        params.append(status)
        idx += 1

    where = " AND ".join(conditions)

    async with get_db(request) as conn:
        total = await conn.fetchval(
            f"SELECT COUNT(*) FROM pipeline_jobs pj WHERE {where}", *params
        )
        rows = await conn.fetch(
            f"""
            SELECT pj.job_id, pj.curriculum_id, pj.grade, pj.langs, pj.force,
                   pj.status, pj.built, pj.failed, pj.total,
                   pj.triggered_at, pj.started_at, pj.completed_at,
                   pj.error, pj.payload_bytes,
                   t.email AS triggered_by_email
            FROM pipeline_jobs pj
            LEFT JOIN teachers t ON t.teacher_id = pj.triggered_by_teacher_id
            WHERE {where}
            ORDER BY pj.triggered_at DESC
            LIMIT ${idx} OFFSET ${idx + 1}
            """,
            *params, page_size, offset,
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
            job["progress_pct"] = live.get("progress_pct", 0.0)
        jobs.append(job)

    return {"jobs": jobs, "total": total, "page": page, "page_size": page_size}


# ── GET /schools/{school_id}/pipeline/{job_id} ───────────────────────────────


@router.get("/schools/{school_id}/pipeline/{job_id}")
async def get_school_pipeline_job(
    school_id: str,
    job_id: str,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
) -> dict:
    """Return job detail. 403 if the job belongs to a different school."""
    _assert_school_match(teacher, school_id, request)
    redis = get_redis(request)

    # Prefer live Redis state
    raw = await redis.get(f"pipeline:job:{job_id}")
    if raw:
        live = json.loads(raw)
        # Verify school ownership via DB
        async with get_db(request) as conn:
            owner = await conn.fetchval(
                "SELECT school_id::text FROM pipeline_jobs WHERE job_id = $1", job_id
            )
        if owner != school_id:
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "forbidden",
                    "detail": "This job does not belong to your school.",
                    "correlation_id": _cid(request),
                },
            )
        return live

    # Fallback to DB for completed jobs whose Redis key has expired
    async with get_db(request) as conn:
        row = await conn.fetchrow(
            """
            SELECT job_id, curriculum_id, grade, langs, status, built, failed, total,
                   triggered_at, started_at, completed_at, error, payload_bytes,
                   school_id::text AS school_id_str
            FROM pipeline_jobs WHERE job_id = $1
            """,
            job_id,
        )

    if not row:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "not_found",
                "detail": "Job not found.",
                "correlation_id": _cid(request),
            },
        )

    if row["school_id_str"] != school_id:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "forbidden",
                "detail": "This job does not belong to your school.",
                "correlation_id": _cid(request),
            },
        )

    return dict(row)
