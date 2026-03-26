"""
backend/src/curriculum/router.py

Curriculum endpoints.

Phase 1–2 routes (JSON files):
  GET  /curriculum               — list grades
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
from typing import Annotated, List

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import Response

from src.auth.dependencies import get_current_teacher
from src.core.cache import curriculum_cache
from src.core.db import get_db
from src.core.redis_client import get_redis
from src.curriculum.schemas import (
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
_DATA_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "data")
)


def _load_grade(grade: int) -> dict:
    cached = curriculum_cache.get(grade)
    if cached is not None:
        return cached
    path = os.path.join(_DATA_DIR, f"grade{grade}_stem.json")
    if not os.path.exists(path):
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "detail": f"Curriculum data for grade {grade} not found."},
        )
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    curriculum_cache[grade] = data
    log.info("curriculum_loaded", grade=grade)
    return data


def _cid(request: Request) -> str:
    return getattr(request.state, "correlation_id", "")


# ── Grade tree (existing) ─────────────────────────────────────────────────────

@router.get("/curriculum", response_model=List[GradeSummary])
async def list_curriculum(request: Request):
    summaries: List[GradeSummary] = []
    for grade in range(5, 13):
        try:
            data = _load_grade(grade)
        except HTTPException:
            continue
        subjects = data.get("subjects", [])
        unit_count = sum(len(s.get("units", [])) for s in subjects)
        summaries.append(GradeSummary(grade=grade, subject_count=len(subjects), unit_count=unit_count))
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
            detail={"error": "bad_request", "detail": "Grade must be 5–12.", "correlation_id": _cid(request)},
        )
    content = build_xlsx_template(grade)
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="curriculum_template_grade{grade}.xlsx"'},
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
            detail={"error": "bad_request", "detail": "Grade must be 5–12.", "correlation_id": _cid(request)},
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
            conn, redis,
            curriculum_id=body.curriculum_id,
            langs=body.langs,
            force=body.force,
            teacher_id=teacher.get("teacher_id", ""),
        )
    if not result:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "detail": "Curriculum not found.", "correlation_id": _cid(request)},
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
            detail={"error": "not_found", "detail": "Job not found.", "correlation_id": _cid(request)},
        )
    return PipelineJobStatusResponse(**data)


# ── Grade tree /{grade} — kept last to avoid shadowing /template and /pipeline ─

@router.get("/curriculum/{grade}", response_model=GradeCurriculum)
async def get_grade_curriculum(grade: int, request: Request):
    """Return the full subject + unit tree for a grade (5–12)."""
    cid = _cid(request)
    if not (5 <= grade <= 12):
        raise HTTPException(
            status_code=400,
            detail={"error": "bad_request", "detail": "Grade must be between 5 and 12.", "correlation_id": cid},
        )
    data = _load_grade(grade)
    return GradeCurriculum(**data)
