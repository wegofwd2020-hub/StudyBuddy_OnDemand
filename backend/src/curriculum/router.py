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

import asyncio
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
from src.core.storage import StorageBackend, get_storage
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


async def _has_content_map(
    storage: StorageBackend, content_curriculum_id: str, unit_ids: list[str]
) -> dict[str, bool]:
    """
    Return {unit_id: has_content} by probing the content store for each unit's
    English lesson file (the canonical fallback every content endpoint serves —
    see content/router.py, which tries lesson_{locale} then lesson_en).

    Lets the student UI grey-out units with no generated content instead of
    letting the click dead-end on a 404 "Could not load lesson" (#468/#469).
    One storage probe per unit, run concurrently.
    """
    if not unit_ids:
        return {}

    async def _probe(unit_id: str) -> bool:
        try:
            return await storage.exists(
                f"curricula/{content_curriculum_id}/{unit_id}/lesson_en.json"
            )
        except Exception:
            # A storage hiccup must not blank the whole tree — default to
            # "available" so we never hide content that actually exists.
            return True

    flags = await asyncio.gather(*(_probe(u) for u in unit_ids))
    return dict(zip(unit_ids, flags, strict=True))


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

    # ── Step 1: resolve EVERY curriculum this student's content comes from ──
    #
    # This used to carry its own inline copy of the three-step resolution, with
    # a comment claiming it was "the same as content.service". It was not the
    # same — it was a fourth copy, and copies drift (pitfall #31 is exactly this
    # function serving stream students another stream's subjects).
    #
    # It is now the shared resolver, and it returns a LIST: a classroom's
    # packages are additive (#651), so the tree is the union of them rather than
    # whichever one an arbitrary LIMIT 1 happened to pick.
    from src.content.service import resolve_curriculum_ids

    curriculum_ids = await resolve_curriculum_ids(
        student_id, grade, pool, redis, school_id=school_id
    )
    curriculum_id = curriculum_ids[0]

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
        # A school FORK carries no rows in curriculum_units — they live under
        # its source — so each id is swapped for the one that actually holds
        # units before the lookup.
        lookup_ids: list[str] = []
        fork_lookups: set[str] = set()
        for cid in curriculum_ids:
            source_id = await conn.fetchval(
                "SELECT source_curriculum_id FROM curricula WHERE curriculum_id = $1",
                cid,
            )
            lookup = source_id or cid
            lookup_ids.append(lookup)
            if source_id:
                # A fork serves unit content from teacher DB overrides, so its
                # units must not be probed against the OOB files.
                fork_lookups.add(lookup)

        rows = await conn.fetch(
            """
            SELECT cu.unit_id, cu.curriculum_id AS holder, cu.title, cu.subject,
                   COALESCE(MAX(csv.subject_name), cu.subject) AS subject_display,
                   cu.has_lab, cu.sort_order
            FROM curriculum_units cu
            LEFT JOIN content_subject_versions csv
                ON csv.curriculum_id = cu.curriculum_id
               AND csv.subject = cu.subject
            WHERE cu.curriculum_id = ANY($1::text[])
            GROUP BY cu.unit_id, cu.curriculum_id, cu.title, cu.subject, cu.has_lab, cu.sort_order
            ORDER BY cu.subject, cu.sort_order, cu.unit_id
            """,
            lookup_ids,
        )

    # unit_id -> the curriculum that holds it, so the content probe below can
    # ask the right one (#651). Empty on the JSON fallback path, which then
    # treats provenance as unknown and assumes available.
    holder_by_unit: dict[str, str] = {}

    if rows:
        # Build subjects dict preserving subject order from first encounter
        subjects_map: dict[str, list[dict]] = {}
        for row in rows:
            holder_by_unit[row["unit_id"]] = row["holder"]
            subj = row["subject_display"]
            if subj not in subjects_map:
                subjects_map[subj] = []
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
        subjects = [{"subject": s, "units": u} for s, u in subjects_map.items()]
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
            subjects.append({"subject": subject_name, "units": units})
        log.info(
            "curriculum_tree_from_json",
            curriculum_id=curriculum_id,
            grade=grade,
        )

    # Per-unit content-availability flag (#468/#469) so the UI can grey-out
    # units whose content has not been generated rather than dead-ending on a
    # 404. Probe the content store for the canonical English lesson file.
    #
    # School forks (source_id present) serve unit content from teacher DB
    # overrides, not (only) from files — probing the OOB files would wrongly
    # hide overridden units. Skip the probe for forks and mark everything
    # available; the OOB platform path is where the reported dead-ends occur.
    all_units = [u for subj in subjects for u in subj["units"]]
    # Probe each unit against the curriculum that actually HOLDS it (#651).
    # With several packages in play there is no single id to probe against, and
    # using the first would have marked another package's units as missing.
    content_map: dict[str, bool] = {}
    by_holder: dict[str, list[str]] = {}
    for u in all_units:
        by_holder.setdefault(holder_by_unit.get(u["unit_id"], ""), []).append(u["unit_id"])

    storage = get_storage(request)
    for holder, unit_ids in by_holder.items():
        if not holder or holder in fork_lookups:
            # Fork-held (overrides live in the DB) or unknown provenance —
            # assume available rather than grey out a unit that works.
            content_map.update(dict.fromkeys(unit_ids, True))
        else:
            content_map.update(await _has_content_map(storage, holder, unit_ids))
    for u in all_units:
        u["has_content"] = content_map.get(u["unit_id"], True)

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
