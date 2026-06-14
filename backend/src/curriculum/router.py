"""
backend/src/curriculum/router.py

Curriculum endpoints.

Phase 1–2 routes (JSON files):
  GET  /curriculum               — list grades
  GET  /curriculum/tree          — student's grade tree (JWT-resolved)
  GET  /curriculum/{grade}       — grade tree

Phase 8 routes (DB + XLSX):
  GET  /curriculum/template      — download XLSX template
  POST /curriculum/upload        — create curriculum from JSON body
  POST /curriculum/upload/xlsx   — create curriculum from XLSX file
  POST /curriculum/pipeline/trigger        — trigger async pipeline job
  GET  /curriculum/pipeline/{job_id}/status — poll job state (Redis)

All Phase 8 write endpoints require a teacher JWT.
Prefixed with /api/v1 in main.py.
"""

from __future__ import annotations

import json
import os
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import Response

from src.auth.dependencies import (
    get_current_student,
    get_current_student_optional,
    get_current_teacher,
)
from src.core.cache import curriculum_cache
from src.core.cache_keys import cur_key
from src.core.db import get_db
from src.core.redis_client import get_redis
from src.curriculum.schemas import (
    CurriculumActivateResponse,
    CurriculumUploadRequest,
    CurriculumUploadResponse,
    GradeCurriculum,
    GradeSummary,
    PipelineJobStatusResponse,
    PipelineTriggerRequest,
    PipelineTriggerResponse,
)
from src.curriculum.upload_service import (
    build_xlsx_template,
    create_curriculum_from_json,
    get_pipeline_job_status,
    parse_xlsx,
    trigger_pipeline,
)
from src.utils.logger import get_logger

log = get_logger("curriculum")
router = APIRouter(tags=["curriculum"])

# Path to data directory (relative to repo root, resolved at import time).
_DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "data"))


def _load_grade(grade: int) -> dict:
    cached = curriculum_cache.get(grade)
    if cached is not None:
        return cached
    path = os.path.join(_DATA_DIR, f"grade{grade}_stem.json")
    if not os.path.exists(path):
        raise HTTPException(
            status_code=404,
            detail={
                "error": "not_found",
                "detail": f"Curriculum data for grade {grade} not found.",
            },
        )
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    curriculum_cache[grade] = data
    log.info("curriculum_loaded", grade=grade)
    return data


def _cid(request: Request) -> str:
    return getattr(request.state, "correlation_id", "")


# ── Grade tree (existing) ─────────────────────────────────────────────────────


@router.get("/curriculum", response_model=list[GradeSummary])
async def list_curriculum(request: Request):
    summaries: list[GradeSummary] = []
    for grade in range(5, 13):
        try:
            data = _load_grade(grade)
        except HTTPException:
            continue
        subjects = data.get("subjects", [])
        unit_count = sum(len(s.get("units", [])) for s in subjects)
        summaries.append(
            GradeSummary(grade=grade, subject_count=len(subjects), unit_count=unit_count)
        )
    return summaries


# ── XLSX template — must be registered before /{grade} to avoid route conflict ─


@router.get("/curriculum/template")
async def download_template(
    request: Request,
    grade: int = 8,
) -> Response:
    """Download an XLSX curriculum template for the given grade."""
    if not (5 <= grade <= 12):
        raise HTTPException(
            status_code=400,
            detail={
                "error": "bad_request",
                "detail": "Grade must be 5–12.",
                "correlation_id": _cid(request),
            },
        )
    content = build_xlsx_template(grade)
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="curriculum_template_grade{grade}.xlsx"'
        },
    )


# ── Curriculum upload (JSON body) ─────────────────────────────────────────────


@router.post(
    "/curriculum/upload",
    response_model=CurriculumUploadResponse,
    status_code=201,
)
async def upload_curriculum_json(
    body: CurriculumUploadRequest,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
) -> CurriculumUploadResponse:
    """Create a curriculum from a JSON unit list. Returns 400 with per-row errors on validation failure."""
    units = [u.model_dump() for u in body.units]
    async with get_db(request) as conn:
        result = await create_curriculum_from_json(
            conn,
            grade=body.grade,
            year=body.year,
            name=body.name,
            units=units,
            teacher_id=teacher.get("teacher_id"),
            school_id=teacher.get("school_id"),
        )
    if result["errors"]:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "validation_error",
                "detail": "Curriculum validation failed.",
                "errors": result["errors"],
                "correlation_id": _cid(request),
            },
        )
    return CurriculumUploadResponse(**result)


# ── Curriculum upload (XLSX file) ─────────────────────────────────────────────


@router.post(
    "/curriculum/upload/xlsx",
    response_model=CurriculumUploadResponse,
    status_code=201,
)
async def upload_curriculum_xlsx(
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
    file: UploadFile = File(...),
    grade: int = 8,
    year: int = 2026,
    name: str = "",
) -> CurriculumUploadResponse:
    """Upload an XLSX file to create a curriculum. Returns 400 with per-row errors on failure."""
    if not (5 <= grade <= 12):
        raise HTTPException(
            status_code=400,
            detail={
                "error": "bad_request",
                "detail": "Grade must be 5–12.",
                "correlation_id": _cid(request),
            },
        )
    content = await file.read()
    units, parse_errors = parse_xlsx(content, grade)
    if parse_errors:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "validation_error",
                "detail": "XLSX parse error.",
                "errors": parse_errors,
                "correlation_id": _cid(request),
            },
        )
    curriculum_name = name or f"Grade {grade} STEM {year}"
    async with get_db(request) as conn:
        result = await create_curriculum_from_json(
            conn,
            grade=grade,
            year=year,
            name=curriculum_name,
            units=units,
            teacher_id=teacher.get("teacher_id"),
            school_id=teacher.get("school_id"),
        )
    if result["errors"]:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "validation_error",
                "detail": "Curriculum validation failed.",
                "errors": result["errors"],
                "correlation_id": _cid(request),
            },
        )
    return CurriculumUploadResponse(**result)


# ── Pipeline trigger ──────────────────────────────────────────────────────────


@router.post(
    "/curriculum/pipeline/trigger",
    response_model=PipelineTriggerResponse,
    status_code=202,
)
async def pipeline_trigger(
    body: PipelineTriggerRequest,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
) -> PipelineTriggerResponse:
    """Dispatch an async content-generation pipeline job. Returns job_id immediately."""
    redis = get_redis(request)
    async with get_db(request) as conn:
        result = await trigger_pipeline(
            conn,
            redis,
            curriculum_id=body.curriculum_id,
            langs=body.langs,
            force=body.force,
            teacher_id=teacher.get("teacher_id", ""),
        )
    if not result:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "not_found",
                "detail": "Curriculum not found.",
                "correlation_id": _cid(request),
            },
        )
    return PipelineTriggerResponse(**result)


# ── Pipeline job status ───────────────────────────────────────────────────────


@router.get(
    "/curriculum/pipeline/{job_id}/status",
    response_model=PipelineJobStatusResponse,
)
async def pipeline_job_status(
    job_id: str,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
) -> PipelineJobStatusResponse:
    """Poll the status of a pipeline job (reads from Redis)."""
    redis = get_redis(request)
    data = await get_pipeline_job_status(redis, job_id)
    if not data:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "not_found",
                "detail": "Job not found.",
                "correlation_id": _cid(request),
            },
        )
    return PipelineJobStatusResponse(**data)


# ── Curriculum activation ─────────────────────────────────────────────────────


@router.put(
    "/curriculum/{curriculum_id}/activate",
    response_model=CurriculumActivateResponse,
)
async def activate_curriculum(
    curriculum_id: str,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
) -> CurriculumActivateResponse:
    """
    Activate a curriculum for its school/grade/year.

    - Sets status='active', activated_at=NOW().
    - Archives any other active curriculum for the same (school_id, grade, year).
    - Invalidates cur:{student_id} Redis cache for all enrolled students.
    """
    from src.curriculum.resolver import invalidate_resolver_cache_for_school

    redis = get_redis(request)
    async with get_db(request) as conn:
        row = await conn.fetchrow(
            "SELECT curriculum_id, school_id::text, grade, year, status FROM curricula WHERE curriculum_id = $1",
            curriculum_id,
        )
        if not row:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "not_found",
                    "detail": "Curriculum not found.",
                    "correlation_id": _cid(request),
                },
            )

        school_id = row["school_id"]

        # Only school curricula can be activated by a teacher (not default ones).
        if school_id is None:
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "forbidden",
                    "detail": "Default curricula cannot be activated via this endpoint.",
                    "correlation_id": _cid(request),
                },
            )

        if school_id != teacher.get("school_id"):
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "forbidden",
                    "detail": "Cannot activate curriculum for a different school.",
                    "correlation_id": _cid(request),
                },
            )

        import uuid as _uuid

        school_uuid = _uuid.UUID(school_id)

        # Archive any other active curriculum for (school_id, grade, year).
        archive_status = await conn.execute(
            """
            UPDATE curricula
            SET status = 'archived'
            WHERE school_id = $1 AND grade = $2 AND year = $3
              AND status = 'active' AND curriculum_id != $4
            """,
            school_uuid,
            row["grade"],
            row["year"],
            curriculum_id,
        )
        # asyncpg returns "UPDATE N" string; parse the count.
        try:
            archived_count = int(archive_status.split()[-1])
        except (ValueError, IndexError):
            archived_count = 0

        # Activate the target curriculum.
        await conn.execute(
            "UPDATE curricula SET status = 'active', activated_at = NOW() WHERE curriculum_id = $1",
            curriculum_id,
        )

    # Invalidate resolver cache for all enrolled students.
    await invalidate_resolver_cache_for_school(redis, request.app.state.pool, school_id)

    log.info("curriculum_activated", curriculum_id=curriculum_id, school_id=school_id)
    return CurriculumActivateResponse(
        curriculum_id=curriculum_id,
        status="active",
        archived_count=archived_count,
    )


# ── Student curriculum tree — resolves curriculum_id from JWT + enrollment ──────


@router.get("/curriculum/tree")
async def get_curriculum_tree(
    request: Request,
    student: Annotated[dict, Depends(get_current_student)],
) -> dict:
    """
    Return the full subject + unit tree for the authenticated student.

    Resolves curriculum_id via the full 3-step resolver:
      1. School-owned custom curriculum
      2. Classroom package assignment (resolves stream-specific platform curricula)
      3. Default STEM fallback

    Loads units from curriculum_units DB table for the resolved curriculum.
    Falls back to the grade JSON file only when no DB units are found (STEM
    default curricula seeded before the DB table was populated).

    Returns the shape the web frontend expects:
      { curriculum_id, grade, subjects: [{ subject, units: [{ unit_id, title, subject, grade, sort_order, has_lab }] }] }
    """
    grade = student.get("grade", 8)
    student_id = student["student_id"]
    school_id = student.get("school_id")
    redis = request.app.state.redis
    pool = request.app.state.pool

    # ── Step 1: resolve curriculum_id (full 3-step, same as content.service) ──
    _cur_key = cur_key(student_id, school_id)
    cached = await redis.get(_cur_key)
    if cached:
        curriculum_id = cached.decode() if isinstance(cached, bytes) else cached
    else:
        curriculum_id = None
        async with pool.acquire() as conn:
            # 1a. School-owned custom curriculum
            row = await conn.fetchrow(
                """
                SELECT c.curriculum_id
                FROM students s
                JOIN schools sc ON s.school_id = sc.school_id
                JOIN curricula c ON c.school_id = sc.school_id AND c.grade = s.grade
                WHERE s.student_id = $1
                LIMIT 1
                """,
                student_id,
            )
            if row:
                curriculum_id = row["curriculum_id"]

            # 1b. Classroom package assignment (stream-specific platform curricula)
            if not curriculum_id and school_id:
                await conn.execute(
                    "SELECT set_config('app.current_school_id', $1, false)", school_id
                )
                row = await conn.fetchrow(
                    """
                    SELECT cp.curriculum_id
                    FROM classroom_students cs
                    JOIN classrooms cl ON cl.classroom_id = cs.classroom_id
                    JOIN classroom_packages cp ON cp.classroom_id = cl.classroom_id
                    WHERE cs.student_id = $1
                    ORDER BY cl.created_at DESC
                    LIMIT 1
                    """,
                    student_id,
                )
                if row:
                    curriculum_id = row["curriculum_id"]

        # 1c. Default STEM fallback
        if not curriculum_id:
            curriculum_id = f"default-2026-g{grade}"
        await redis.set(_cur_key, curriculum_id, ex=300)

    # ── Step 2: load units from curriculum_units DB table ─────────────────────
    # Join content_subject_versions to get the human-readable subject display
    # name (e.g. "Physics" instead of "G11-PHYS"). Falls back to the raw subject
    # code when no CSV row exists (newly-seeded curriculum with no content yet).
    #
    # If the resolved curriculum is a school fork (owner_type='school'), its
    # curriculum_units table is empty by design — forks inherit the structural
    # unit list from their OOB source and only override content via
    # unit_content_overrides. Resolve the source id first so the units query
    # actually finds rows.
    async with pool.acquire() as conn:
        source_id = await conn.fetchval(
            "SELECT source_curriculum_id FROM curricula WHERE curriculum_id = $1",
            curriculum_id,
        )
        units_lookup_id = source_id or curriculum_id

        rows = await conn.fetch(
            """
            SELECT cu.unit_id, cu.title, cu.subject,
                   COALESCE(MAX(csv.subject_name), cu.subject) AS subject_display,
                   -- Whether the subject has published content (#469): used to
                   -- gate selection so students don't open a subject that would
                   -- 404. Mirrors the check_content_published serve-time guard.
                   BOOL_OR(csv.status = 'published') AS has_content,
                   cu.has_lab, cu.sort_order
            FROM curriculum_units cu
            LEFT JOIN content_subject_versions csv
                ON csv.curriculum_id = cu.curriculum_id
               AND csv.subject = cu.subject
            WHERE cu.curriculum_id = $1
            GROUP BY cu.unit_id, cu.title, cu.subject, cu.has_lab, cu.sort_order
            ORDER BY cu.subject, cu.sort_order, cu.unit_id
            """,
            units_lookup_id,
        )

    if rows:
        # Build subjects dict preserving subject order from first encounter
        subjects_map: dict[str, list[dict]] = {}
        subject_has_content: dict[str, bool] = {}
        for row in rows:
            subj = row["subject_display"]
            if subj not in subjects_map:
                subjects_map[subj] = []
            subject_has_content[subj] = subject_has_content.get(subj, False) or bool(
                row["has_content"]
            )
            subjects_map[subj].append(
                {
                    "unit_id": row["unit_id"],
                    "title": row["title"],
                    "subject": subj,
                    "grade": grade,
                    "sort_order": row["sort_order"],
                    "has_lab": row["has_lab"],
                }
            )
        subjects = [
            {"subject": s, "units": u, "has_content": subject_has_content.get(s, False)}
            for s, u in subjects_map.items()
        ]
        log.info("curriculum_tree_from_db", curriculum_id=curriculum_id, unit_count=len(rows))
    else:
        # Fallback: STEM default curricula may not have curriculum_units rows yet
        data = _load_grade(grade)
        subjects = []
        for subj in data.get("subjects", []):
            subject_name = subj.get("name", subj.get("subject", ""))
            units = [
                {
                    "unit_id": u["unit_id"],
                    "title": u["title"],
                    "subject": subject_name,
                    "grade": grade,
                    "sort_order": idx,
                    "has_lab": u.get("has_lab", False),
                }
                for idx, u in enumerate(subj.get("units", []))
            ]
            # JSON fallback (default STEM curricula): content readiness can't be
            # determined from the DB here, so don't over-gate — assume available.
            subjects.append({"subject": subject_name, "units": units, "has_content": True})
        log.info(
            "curriculum_tree_from_json",
            curriculum_id=curriculum_id,
            grade=grade,
        )

    return {"curriculum_id": curriculum_id, "grade": grade, "subjects": subjects}


# ── Grade tree /{grade} — kept last to avoid shadowing /template and /pipeline ─


@router.get("/curriculum/{grade}", response_model=GradeCurriculum)
async def get_grade_curriculum(
    grade: int,
    request: Request,
    student: dict | None = Depends(get_current_student_optional),
):
    """
    Return the full subject + unit tree for a grade (5–12).

    Stream-aware when an authenticated student token is supplied AND the path
    grade matches the student's grade: resolves the student's actual
    curriculum_id (school-owned → classroom packages → STEM fallback) and
    builds the response from `curriculum_units` rows. Otherwise falls back to
    the legacy `data/grade{N}_stem.json` fixture for backwards compatibility
    with anonymous callers and out-of-grade lookups.
    """
    cid = _cid(request)
    if not (5 <= grade <= 12):
        raise HTTPException(
            status_code=400,
            detail={
                "error": "bad_request",
                "detail": "Grade must be between 5 and 12.",
                "correlation_id": cid,
            },
        )

    # Stream-aware path: only when an authenticated student is asking for
    # *their own* grade. Anonymous callers and admin/demo-data lookups for
    # other grades still get the STEM JSON fallback.
    if student and student.get("grade") == grade:
        built = await _build_grade_curriculum_for_student(student, grade, request)
        if built is not None:
            return built

    data = _load_grade(grade)
    return GradeCurriculum(**data)


async def _build_grade_curriculum_for_student(
    student: dict, grade: int, request: Request
) -> GradeCurriculum | None:
    """
    Resolve the student's actual curriculum_id (3-step resolver), fetch the
    units from `curriculum_units`, and build a `GradeCurriculum` payload.

    Returns None when no DB rows exist for the resolved curriculum so the
    caller can fall back to the legacy JSON fixture.
    """
    student_id = student["student_id"]
    school_id = student.get("school_id")
    redis = request.app.state.redis
    pool = request.app.state.pool

    # Step 1: resolve curriculum_id (mirrors get_curriculum_tree).
    _cur_key = cur_key(student_id, school_id)
    cached = await redis.get(_cur_key)
    if cached:
        curriculum_id = cached.decode() if isinstance(cached, bytes) else cached
    else:
        curriculum_id = None
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT c.curriculum_id
                FROM students s
                JOIN schools sc ON s.school_id = sc.school_id
                JOIN curricula c ON c.school_id = sc.school_id AND c.grade = s.grade
                WHERE s.student_id = $1
                LIMIT 1
                """,
                student_id,
            )
            if row:
                curriculum_id = row["curriculum_id"]
            if not curriculum_id and school_id:
                await conn.execute(
                    "SELECT set_config('app.current_school_id', $1, false)", school_id
                )
                row = await conn.fetchrow(
                    """
                    SELECT cp.curriculum_id
                    FROM classroom_students cs
                    JOIN classrooms cl ON cl.classroom_id = cs.classroom_id
                    JOIN classroom_packages cp ON cp.classroom_id = cl.classroom_id
                    WHERE cs.student_id = $1
                    ORDER BY cl.created_at DESC
                    LIMIT 1
                    """,
                    student_id,
                )
                if row:
                    curriculum_id = row["curriculum_id"]
        if not curriculum_id:
            curriculum_id = f"default-2026-g{grade}"
        await redis.set(_cur_key, curriculum_id, ex=300)

    # Step 2: load units from DB; abort to JSON fallback if none.
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT cu.unit_id, cu.title, cu.subject,
                   COALESCE(MAX(csv.subject_name), cu.subject) AS subject_display,
                   cu.has_lab, cu.sort_order
            FROM curriculum_units cu
            LEFT JOIN content_subject_versions csv
                ON csv.curriculum_id = cu.curriculum_id
               AND csv.subject = cu.subject
            WHERE cu.curriculum_id = $1
            GROUP BY cu.unit_id, cu.title, cu.subject, cu.has_lab, cu.sort_order
            ORDER BY cu.subject, cu.sort_order, cu.unit_id
            """,
            curriculum_id,
        )
    if not rows:
        return None

    # Step 3: build the GradeCurriculum payload.
    subjects_map: dict[str, list[dict]] = {}
    for row in rows:
        subj_name = row["subject_display"]
        if subj_name not in subjects_map:
            subjects_map[subj_name] = []
        subjects_map[subj_name].append(
            {
                "unit_id": row["unit_id"],
                "title": row["title"],
                "description": "",
                "has_lab": row["has_lab"],
            }
        )
    subjects = [
        {"subject_id": name.lower().replace(" ", "-"), "name": name, "units": units}
        for name, units in subjects_map.items()
    ]
    log.info(
        "grade_curriculum_from_db",
        curriculum_id=curriculum_id,
        unit_count=len(rows),
    )
    return GradeCurriculum(grade=grade, subjects=subjects)
