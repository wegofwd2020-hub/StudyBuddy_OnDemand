"""
backend/src/school/retention_router.py

School curriculum version retention endpoints.

Routes (all prefixed /api/v1 in main.py):
  DELETE /schools/{school_id}/curriculum/versions/{curriculum_id}
         — Remove a curriculum version and free its slot toward the 5-version cap.

Auth:
  school_admin JWT only (not plain teacher).
  The school_id in the path must match the JWT's school_id claim.

Guards:
  - 403 if JWT school_id ≠ path school_id
  - 403 if role ≠ school_admin
  - 404 if curriculum_id does not exist or belongs to a different school
  - 409 if the version is currently assigned to one or more grades
    (returns list of affected grades — admin must reassign before deleting)
  - 409 if the version has a running or queued pipeline job

Delete cascade (manual — content_subject_versions has no FK to curricula):
  1. content_annotations rows for units in this curriculum
  2. content_reviews rows for versions of this curriculum
  3. content_subject_versions rows for this curriculum
  4. curriculum_units rows for this curriculum
  5. curricula row itself
  Storage quota used_bytes is NOT decremented here — the nightly reconciliation
  job recomputes used_bytes from pipeline_jobs.payload_bytes.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from src.auth.dependencies import get_current_teacher
from src.core.db import get_db
from src.utils.logger import get_logger

log = get_logger("school.retention")
router = APIRouter(tags=["school-retention"])


# ── Schemas ───────────────────────────────────────────────────────────────────


class DeleteVersionResponse(BaseModel):
    curriculum_id: str
    grade: int
    deleted: bool
    units_removed: int
    versions_removed: int
    version_count: int  # versions remaining for this school+grade


# ── Helpers ───────────────────────────────────────────────────────────────────


def _cid(request: Request) -> str:
    return getattr(request.state, "correlation_id", "")


def _assert_school_match(teacher: dict, school_id: str, request: Request) -> None:
    if teacher.get("school_id") != school_id:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "forbidden",
                "detail": "You can only manage curriculum for your own school.",
                "correlation_id": _cid(request),
            },
        )


def _assert_school_admin(teacher: dict, request: Request) -> None:
    if teacher.get("role") != "school_admin":
        raise HTTPException(
            status_code=403,
            detail={
                "error": "forbidden",
                "detail": "Only school_admin can delete curriculum versions.",
                "correlation_id": _cid(request),
            },
        )


# ── DELETE /schools/{school_id}/curriculum/versions/{curriculum_id} ───────────


@router.delete(
    "/schools/{school_id}/curriculum/versions/{curriculum_id}",
    response_model=DeleteVersionResponse,
    status_code=200,
)
async def delete_curriculum_version(
    school_id: str,
    curriculum_id: str,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
) -> DeleteVersionResponse:
    """
    Permanently delete a curriculum version and free its slot toward the 5-version cap.

    The version must not be actively assigned to any grade. If it is, the response
    includes the list of affected grades so the admin can reassign them first.

    Deletes (in dependency order):
      content_annotations → content_reviews → content_subject_versions
      → curriculum_units → curricula row

    The operation is atomic — all deletes run inside a single transaction.
    """
    _assert_school_match(teacher, school_id, request)
    _assert_school_admin(teacher, request)

    async with get_db(request) as conn:
        # ── Ownership check ───────────────────────────────────────────────────
        row = await conn.fetchrow(
            """
            SELECT curriculum_id, grade, school_id::text AS school_id_str
            FROM curricula
            WHERE curriculum_id = $1
            """,
            curriculum_id,
        )
        if not row or row["school_id_str"] != school_id:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "not_found",
                    "detail": "Curriculum version not found.",
                    "correlation_id": _cid(request),
                },
            )

        grade: int = row["grade"]

        # ── Grade assignment guard ────────────────────────────────────────────
        # grade_curriculum_assignments has FK ON DELETE RESTRICT — we check first
        # and return a clear 409 rather than letting the DB raise an FK violation.
        assigned_grades = await conn.fetch(
            """
            SELECT grade FROM grade_curriculum_assignments
            WHERE curriculum_id = $1
            """,
            curriculum_id,
        )
        if assigned_grades:
            affected = [r["grade"] for r in assigned_grades]
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "version_assigned",
                    "message": (
                        "This curriculum version is currently assigned to one or more grades. "
                        "Reassign those grades to a different version before deleting."
                    ),
                    "assigned_grades": affected,
                    "correlation_id": _cid(request),
                },
            )

        # ── Active pipeline guard ─────────────────────────────────────────────
        active_job = await conn.fetchrow(
            """
            SELECT job_id, status FROM pipeline_jobs
            WHERE curriculum_id = $1
              AND status IN ('queued', 'running')
            LIMIT 1
            """,
            curriculum_id,
        )
        if active_job:
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "pipeline_active",
                    "message": (
                        "A pipeline job is currently running for this curriculum version. "
                        "Wait for it to complete or cancel it before deleting."
                    ),
                    "job_id": str(active_job["job_id"]),
                    "status": active_job["status"],
                    "correlation_id": _cid(request),
                },
            )

        # ── Cascade delete (manual — content tables have no FK to curricula) ─
        async with conn.transaction():
            # 1. content_annotations — keyed by unit_id; unit_ids belong to this curriculum
            annotations_deleted = await conn.execute(
                """
                DELETE FROM content_annotations
                WHERE unit_id IN (
                    SELECT unit_id FROM curriculum_units
                    WHERE curriculum_id = $1
                )
                """,
                curriculum_id,
            )

            # 2. content_reviews — keyed by version_id from content_subject_versions
            reviews_deleted = await conn.execute(
                """
                DELETE FROM content_reviews
                WHERE version_id IN (
                    SELECT version_id FROM content_subject_versions
                    WHERE curriculum_id = $1
                )
                """,
                curriculum_id,
            )

            # 3. content_subject_versions
            versions_result = await conn.execute(
                "DELETE FROM content_subject_versions WHERE curriculum_id = $1",
                curriculum_id,
            )

            # 4. curriculum_units
            units_result = await conn.execute(
                "DELETE FROM curriculum_units WHERE curriculum_id = $1",
                curriculum_id,
            )

            # 5. curricula row itself
            await conn.execute(
                "DELETE FROM curricula WHERE curriculum_id = $1",
                curriculum_id,
            )

        # Parse rowcount from "DELETE N" execute result strings
        def _rowcount(result: str) -> int:
            try:
                return int(result.split()[-1])
            except (IndexError, ValueError):
                return 0

        units_removed = _rowcount(units_result)
        versions_removed = _rowcount(versions_result)

        # Version count remaining for this school+grade after deletion
        remaining = await conn.fetchval(
            "SELECT COUNT(*) FROM curricula WHERE school_id = $1::uuid AND grade = $2",
            school_id, grade,
        )

    log.info(
        "school_curriculum_delete school_id=%s curriculum_id=%s grade=%d "
        "units=%d versions=%d remaining=%d",
        school_id, curriculum_id, grade,
        units_removed, versions_removed, remaining,
    )

    return DeleteVersionResponse(
        curriculum_id=curriculum_id,
        grade=grade,
        deleted=True,
        units_removed=units_removed,
        versions_removed=versions_removed,
        version_count=int(remaining),
    )
