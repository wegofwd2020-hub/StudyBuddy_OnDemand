"""
backend/src/school/content_router.py

Read-only curriculum content endpoints for school teachers.

Routes (all prefixed /api/v1 in main.py):
  GET /schools/{school_id}/content/subjects
      — list content_subject_versions for this school's curricula
        optional ?grade=N filter
  GET /schools/{school_id}/content/versions/{version_id}
      — version detail: subject, grade, units list
  GET /schools/{school_id}/content/versions/{version_id}/unit/{unit_id}
      — unit content meta (which content types have files on disk)
  GET /schools/{school_id}/content/versions/{version_id}/unit/{unit_id}/{content_type}
      — unit content JSON file

Auth:
  All endpoints require teacher or school_admin JWT.
  The school_id in the path must match the JWT's school_id claim.
  The requested version must belong to a curriculum owned by this school
  (curricula.school_id = school_id).
"""

from __future__ import annotations

import json
import os
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from config import settings
from src.auth.dependencies import get_current_teacher
from src.core.db import get_db
from src.utils.logger import get_logger

log = get_logger("school.content")
router = APIRouter(tags=["school-content"])

_CONTENT_TYPES_ORDERED = [
    "lesson",
    "tutorial",
    "quiz_set_1",
    "quiz_set_2",
    "quiz_set_3",
    "experiment",
]


def _cid(request: Request) -> str:
    return getattr(request.state, "correlation_id", "")


def _assert_school_match(teacher: dict, school_id: str, request: Request) -> None:
    if teacher.get("school_id") != school_id:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "forbidden",
                "detail": "You can only access content for your own school.",
                "correlation_id": _cid(request),
            },
        )


async def _assert_version_belongs_to_school(
    conn, version_id: str, school_id: str, request: Request
) -> str:
    """Verify version_id belongs to a curriculum owned by school_id; return curriculum_id."""
    row = await conn.fetchrow(
        """
        SELECT csv.curriculum_id
        FROM content_subject_versions csv
        JOIN curricula c ON c.curriculum_id = csv.curriculum_id
        WHERE csv.version_id = $1
          AND (c.school_id = $2::uuid OR c.is_default = true)
        """,
        uuid.UUID(version_id),
        school_id,
    )
    if not row:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "not_found",
                "detail": "Content version not found for this school.",
                "correlation_id": _cid(request),
            },
        )
    return row["curriculum_id"]


# ── GET /schools/{school_id}/content/subjects ─────────────────────────────────


@router.get("/schools/{school_id}/content/subjects")
async def list_school_content_subjects(
    school_id: str,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
    grade: int | None = Query(None, ge=5, le=12),
) -> dict:
    """
    List content subject versions for this school's own curricula plus all
    default (platform) curricula. Default curricula are shared across all schools
    and represent the base content teachers can assign from.
    """
    _assert_school_match(teacher, school_id, request)

    async with get_db(request) as conn:
        params: list = [school_id]
        grade_filter = ""
        if grade is not None:
            params.append(grade)
            grade_filter = f"AND c.grade = ${len(params)}"

        rows = await conn.fetch(
            f"""
            SELECT csv.version_id::text,
                   csv.curriculum_id,
                   csv.subject,
                   csv.subject_name,
                   csv.version_number,
                   csv.status,
                   csv.generated_at,
                   csv.published_at,
                   csv.alex_warnings_count,
                   c.grade,
                   c.year,
                   c.name AS curriculum_name
            FROM content_subject_versions csv
            JOIN curricula c ON c.curriculum_id = csv.curriculum_id
            WHERE (c.school_id = $1::uuid OR c.is_default = true)
              AND csv.archived_at IS NULL
              {grade_filter}
            ORDER BY c.grade, csv.subject, csv.version_number DESC
            """,
            *params,
        )

        # Check which ones have content on disk
        content_store = getattr(settings, "CONTENT_STORE_PATH", "/data/content")
        _dirs_cache: dict[str, set[str]] = {}
        _units_cache: dict[tuple[str, str], list[str]] = {}

        for r in rows:
            cid = r["curriculum_id"]
            if cid not in _dirs_cache:
                cdir = os.path.join(content_store, "curricula", cid)
                try:
                    _dirs_cache[cid] = set(os.listdir(cdir))
                except OSError:
                    _dirs_cache[cid] = set()

        unique_pairs = {(r["curriculum_id"], r["subject"]) for r in rows}
        for cid, subj in unique_pairs:
            unit_rows = await conn.fetch(
                "SELECT unit_id FROM curriculum_units WHERE curriculum_id = $1 AND subject = $2",
                cid,
                subj,
            )
            _units_cache[(cid, subj)] = [ur["unit_id"] for ur in unit_rows]

        items = []
        for r in rows:
            d = dict(r)
            dirs = _dirs_cache.get(r["curriculum_id"], set())
            unit_ids = _units_cache.get((r["curriculum_id"], r["subject"]), [])
            d["has_content"] = any(uid in dirs for uid in unit_ids)
            d["unit_count"] = len(unit_ids)
            items.append(d)

    return {"subjects": items, "total": len(items)}


# ── GET /schools/{school_id}/content/versions/{version_id} ───────────────────


@router.get("/schools/{school_id}/content/versions/{version_id}")
async def get_school_content_version(
    school_id: str,
    version_id: str,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
) -> dict:
    """Return version metadata + list of units for a content subject version."""
    _assert_school_match(teacher, school_id, request)

    async with get_db(request) as conn:
        await _assert_version_belongs_to_school(conn, version_id, school_id, request)

        version = await conn.fetchrow(
            """
            SELECT csv.version_id::text,
                   csv.curriculum_id,
                   csv.subject,
                   csv.subject_name,
                   csv.version_number,
                   csv.status,
                   csv.generated_at,
                   csv.published_at,
                   csv.alex_warnings_count,
                   c.grade,
                   c.year,
                   c.name AS curriculum_name
            FROM content_subject_versions csv
            JOIN curricula c ON c.curriculum_id = csv.curriculum_id
            WHERE csv.version_id = $1
            """,
            uuid.UUID(version_id),
        )

        units = await conn.fetch(
            """
            SELECT unit_id, title, sort_order
            FROM curriculum_units
            WHERE curriculum_id = $1 AND subject = $2
            ORDER BY sort_order
            """,
            version["curriculum_id"],
            version["subject"],
        )

    return {
        **dict(version),
        "units": [dict(u) for u in units],
    }


# ── GET /schools/{school_id}/content/versions/{version_id}/unit/{unit_id} ────


@router.get("/schools/{school_id}/content/versions/{version_id}/unit/{unit_id}")
async def get_school_unit_meta(
    school_id: str,
    version_id: str,
    unit_id: str,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
    lang: str = Query("en", min_length=2, max_length=5),
) -> dict:
    """Return unit title + list of available content types on disk."""
    _assert_school_match(teacher, school_id, request)

    async with get_db(request) as conn:
        curriculum_id = await _assert_version_belongs_to_school(
            conn, version_id, school_id, request
        )

        row = await conn.fetchrow(
            "SELECT title FROM curriculum_units WHERE unit_id = $1 AND curriculum_id = $2",
            unit_id,
            curriculum_id,
        )
        if not row:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "not_found",
                    "detail": "Unit not found.",
                    "correlation_id": _cid(request),
                },
            )

        annotations_rows = await conn.fetch(
            """
            SELECT ca.annotation_id::text,
                   ca.content_type,
                   ca.annotation_text,
                   ca.created_at,
                   au.email AS reviewer_email
            FROM content_annotations ca
            LEFT JOIN admin_users au ON au.admin_user_id = ca.created_by
            WHERE ca.version_id = $1 AND ca.unit_id = $2
            ORDER BY ca.created_at
            """,
            uuid.UUID(version_id),
            unit_id,
        )

    content_store = getattr(settings, "CONTENT_STORE_PATH", "/data/content")
    unit_dir = os.path.join(content_store, "curricula", curriculum_id, unit_id)

    available: list[str] = []
    for ct in _CONTENT_TYPES_ORDERED:
        if os.path.isfile(os.path.join(unit_dir, f"{ct}_{lang}.json")):
            available.append(ct)

    alex_warnings_count = 0
    meta_path = os.path.join(unit_dir, "meta.json")
    if os.path.isfile(meta_path):
        try:
            with open(meta_path, encoding="utf-8") as f:
                meta = json.load(f)
            alex_warnings_count = int(meta.get("alex_warnings_count", 0))
        except Exception:
            pass

    return {
        "unit_id": unit_id,
        "title": row["title"],
        "curriculum_id": curriculum_id,
        "lang": lang,
        "available_types": available,
        "alex_warnings_count": alex_warnings_count,
        "annotations": [dict(a) for a in annotations_rows],
    }


# ── GET /schools/{school_id}/content/versions/{version_id}/unit/{unit_id}/{ct}


@router.get(
    "/schools/{school_id}/content/versions/{version_id}/unit/{unit_id}/{content_type}"
)
async def get_school_unit_content(
    school_id: str,
    version_id: str,
    unit_id: str,
    content_type: str,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
    lang: str = Query("en", min_length=2, max_length=5),
) -> dict:
    """Return the raw JSON for a specific content type file."""
    if content_type not in _CONTENT_TYPES_ORDERED:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "invalid_content_type",
                "detail": f"content_type must be one of {_CONTENT_TYPES_ORDERED}",
                "correlation_id": _cid(request),
            },
        )

    _assert_school_match(teacher, school_id, request)

    async with get_db(request) as conn:
        curriculum_id = await _assert_version_belongs_to_school(
            conn, version_id, school_id, request
        )

    content_store = getattr(settings, "CONTENT_STORE_PATH", "/data/content")
    file_path = os.path.join(
        content_store,
        "curricula",
        curriculum_id,
        unit_id,
        f"{content_type}_{lang}.json",
    )

    if not os.path.isfile(file_path):
        raise HTTPException(
            status_code=404,
            detail={
                "error": "not_found",
                "detail": f"Content file '{content_type}_{lang}.json' not found for this unit.",
                "correlation_id": _cid(request),
            },
        )

    with open(file_path, encoding="utf-8") as f:
        data = json.load(f)

    return {
        "unit_id": unit_id,
        "curriculum_id": curriculum_id,
        "content_type": content_type,
        "lang": lang,
        "content": data,
    }
