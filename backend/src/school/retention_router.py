"""
backend/src/school/retention_router.py

School curriculum version retention endpoints (Phase B + Phase F).

Routes (all prefixed /api/v1 in main.py):

  Phase B:
    DELETE /schools/{school_id}/curriculum/versions/{curriculum_id}
           — Remove a curriculum version and free its slot toward the 5-version cap.

  Phase F (retention dashboard):
    GET  /schools/{school_id}/retention
         — Full retention dashboard: all curriculum versions with status, expiry dates,
           grade assignments, and computed urgency signals.
    POST /schools/{school_id}/curriculum/versions/{curriculum_id}/renew
         — Renew a curriculum: extends expires_at by 1 year from original expiry,
           resets retention_status to 'active', clears grace_until.
    PUT  /schools/{school_id}/grades/{grade}/curriculum
         — Assign an active curriculum version as the live content source for a grade.
           Upserts into grade_curriculum_assignments.

Auth:
  school_admin JWT only (not plain teacher).
  The school_id in the path must match the JWT's school_id claim.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Request
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


class RetentionVersion(BaseModel):
    """One curriculum version as shown on the retention dashboard."""
    curriculum_id: str
    grade: int
    name: str
    year: int
    retention_status: str          # active | unavailable | purged
    expires_at: datetime | None
    grace_until: datetime | None
    renewed_at: datetime | None
    is_assigned: bool              # currently assigned to grade via grade_curriculum_assignments
    days_until_expiry: int | None  # positive = days left; None if already expired or purged
    days_until_purge: int | None   # days left in grace period; None if not in grace


class RetentionDashboard(BaseModel):
    school_id: str
    total_versions: int
    active_count: int
    unavailable_count: int
    purged_count: int
    curricula: list[RetentionVersion]


class RenewResponse(BaseModel):
    curriculum_id: str
    grade: int
    previous_expires_at: datetime | None
    new_expires_at: datetime
    renewed_at: datetime
    retention_status: str


class AssignCurriculumRequest(BaseModel):
    curriculum_id: str


class AssignCurriculumResponse(BaseModel):
    school_id: str
    grade: int
    curriculum_id: str
    assigned_at: datetime
    previous_curriculum_id: str | None


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
                "detail": "Only school_admin can perform this action.",
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

        # Version count remaining for this school+grade after deletion (purged don't count)
        remaining = await conn.fetchval(
            """
            SELECT COUNT(*) FROM curricula
            WHERE school_id = $1::uuid AND grade = $2
              AND retention_status <> 'purged'
            """,
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


# ── GET /schools/{school_id}/retention ───────────────────────────────────────


@router.get(
    "/schools/{school_id}/retention",
    response_model=RetentionDashboard,
    status_code=200,
)
async def get_retention_dashboard(
    school_id: str,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
) -> RetentionDashboard:
    """
    Return the full retention dashboard for a school.

    Lists every curriculum version (active / unavailable / purged) with:
      - Expiry and grace-period dates
      - Computed days_until_expiry and days_until_purge urgency signals
      - is_assigned flag — whether this version is the live content for its grade
      - Aggregate counts by retention_status

    Accessible by any teacher or school_admin of this school.
    """
    _assert_school_match(teacher, school_id, request)

    async with get_db(request) as conn:
        rows = await conn.fetch(
            """
            SELECT
                c.curriculum_id,
                c.grade,
                c.name,
                c.year,
                c.retention_status,
                c.expires_at,
                c.grace_until,
                c.renewed_at,
                CASE WHEN gca.curriculum_id IS NOT NULL THEN TRUE ELSE FALSE END AS is_assigned
            FROM curricula c
            LEFT JOIN grade_curriculum_assignments gca
                   ON gca.curriculum_id = c.curriculum_id
                  AND gca.school_id = c.school_id
            WHERE c.school_id = $1::uuid
              AND c.owner_type = 'school'
            ORDER BY c.grade ASC, c.expires_at DESC NULLS LAST
            """,
            school_id,
        )

    now = datetime.now(UTC)
    curricula: list[RetentionVersion] = []
    active_count = unavailable_count = purged_count = 0

    for row in rows:
        status = row["retention_status"]
        expires_at = row["expires_at"]
        grace_until = row["grace_until"]

        if status == "active":
            active_count += 1
        elif status == "unavailable":
            unavailable_count += 1
        else:
            purged_count += 1

        # Compute urgency signals — None when not applicable.
        days_until_expiry: int | None = None
        if status == "active" and expires_at is not None:
            delta = (expires_at - now).days
            days_until_expiry = max(delta, 0)

        days_until_purge: int | None = None
        if status == "unavailable" and grace_until is not None:
            delta = (grace_until - now).days
            days_until_purge = max(delta, 0)

        curricula.append(RetentionVersion(
            curriculum_id=row["curriculum_id"],
            grade=row["grade"],
            name=row["name"],
            year=row["year"],
            retention_status=status,
            expires_at=expires_at,
            grace_until=grace_until,
            renewed_at=row["renewed_at"],
            is_assigned=row["is_assigned"],
            days_until_expiry=days_until_expiry,
            days_until_purge=days_until_purge,
        ))

    log.info(
        "school_retention_dashboard school_id=%s total=%d active=%d "
        "unavailable=%d purged=%d",
        school_id, len(curricula), active_count, unavailable_count, purged_count,
    )

    return RetentionDashboard(
        school_id=school_id,
        total_versions=len(curricula),
        active_count=active_count,
        unavailable_count=unavailable_count,
        purged_count=purged_count,
        curricula=curricula,
    )


# ── POST /schools/{school_id}/curriculum/versions/{curriculum_id}/renew ───────


@router.post(
    "/schools/{school_id}/curriculum/versions/{curriculum_id}/renew",
    response_model=RenewResponse,
    status_code=200,
)
async def renew_curriculum_version(
    school_id: str,
    curriculum_id: str,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
) -> RenewResponse:
    """
    Renew a curriculum version by extending its expiry by one year.

    Renewal semantics:
      - new expires_at = old expires_at + 1 year (no overlap, no gap from original date)
      - retention_status reset to 'active'
      - grace_until cleared (NULL)
      - renewed_at = NOW()

    Renewal is allowed for retention_status 'active' or 'unavailable'.
    Purged curricula cannot be renewed — they must be rebuilt from scratch.

    Only school_admin may renew.  The curriculum must belong to this school.
    """
    _assert_school_match(teacher, school_id, request)
    _assert_school_admin(teacher, request)

    async with get_db(request) as conn:
        row = await conn.fetchrow(
            """
            SELECT curriculum_id, grade, retention_status, expires_at
            FROM curricula
            WHERE curriculum_id = $1
              AND school_id = $2::uuid
              AND owner_type = 'school'
            """,
            curriculum_id, school_id,
        )
        if row is None:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "not_found",
                    "detail": "Curriculum version not found.",
                    "correlation_id": _cid(request),
                },
            )

        if row["retention_status"] == "purged":
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "already_purged",
                    "detail": (
                        "This curriculum version has been permanently purged and "
                        "cannot be renewed. Upload a new curriculum JSON and rebuild."
                    ),
                    "correlation_id": _cid(request),
                },
            )

        old_expires = row["expires_at"]

        updated = await conn.fetchrow(
            """
            UPDATE curricula
            SET expires_at        = expires_at + INTERVAL '1 year',
                grace_until       = NULL,
                retention_status  = 'active',
                renewed_at        = NOW()
            WHERE curriculum_id = $1
            RETURNING expires_at, grace_until, renewed_at
            """,
            curriculum_id,
        )

    log.info(
        "school_curriculum_renew school_id=%s curriculum_id=%s grade=%d "
        "old_expires=%s new_expires=%s",
        school_id, curriculum_id, row["grade"],
        old_expires.isoformat() if old_expires else None,
        updated["expires_at"].isoformat(),
    )

    return RenewResponse(
        curriculum_id=curriculum_id,
        grade=row["grade"],
        previous_expires_at=old_expires,
        new_expires_at=updated["expires_at"],
        renewed_at=updated["renewed_at"],
        retention_status="active",
    )


# ── PUT /schools/{school_id}/grades/{grade}/curriculum ────────────────────────


@router.put(
    "/schools/{school_id}/grades/{grade}/curriculum",
    response_model=AssignCurriculumResponse,
    status_code=200,
)
async def assign_curriculum_to_grade(
    school_id: str,
    grade: int,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
    body: AssignCurriculumRequest = Body(...),
) -> AssignCurriculumResponse:
    """
    Assign a curriculum version as the active content source for a grade.

    Upserts into grade_curriculum_assignments (PRIMARY KEY: school_id, grade).
    Returns the previous assignment so the UI can surface an undo prompt.

    Guards:
      - curriculum_id must belong to this school
      - curriculum grade must match the path grade
      - retention_status must be 'active' (unavailable/purged cannot be assigned)

    Only school_admin may reassign grades.
    """
    _assert_school_match(teacher, school_id, request)
    _assert_school_admin(teacher, request)

    curriculum_id = body.curriculum_id

    async with get_db(request) as conn:
        # Validate curriculum belongs to school, correct grade, and is active.
        cur = await conn.fetchrow(
            """
            SELECT curriculum_id, grade, retention_status
            FROM curricula
            WHERE curriculum_id = $1
              AND school_id = $2::uuid
              AND owner_type = 'school'
            """,
            curriculum_id, school_id,
        )
        if cur is None:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "not_found",
                    "detail": "Curriculum version not found for this school.",
                    "correlation_id": _cid(request),
                },
            )

        if cur["grade"] != grade:
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "grade_mismatch",
                    "detail": (
                        f"Curriculum grade ({cur['grade']}) does not match "
                        f"the requested grade ({grade})."
                    ),
                    "correlation_id": _cid(request),
                },
            )

        if cur["retention_status"] != "active":
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "curriculum_not_active",
                    "detail": (
                        f"Only active curriculum versions can be assigned. "
                        f"This version is '{cur['retention_status']}'. "
                        "Renew it before assigning."
                    ),
                    "correlation_id": _cid(request),
                },
            )

        # Capture previous assignment before upsert.
        prev_row = await conn.fetchrow(
            """
            SELECT curriculum_id FROM grade_curriculum_assignments
            WHERE school_id = $1::uuid AND grade = $2
            """,
            school_id, grade,
        )
        previous_curriculum_id = prev_row["curriculum_id"] if prev_row else None

        # Upsert — if same curriculum is already assigned this is a no-op.
        result_row = await conn.fetchrow(
            """
            INSERT INTO grade_curriculum_assignments
                (school_id, grade, curriculum_id, assigned_by)
            VALUES ($1::uuid, $2, $3, $4::uuid)
            ON CONFLICT (school_id, grade) DO UPDATE
                SET curriculum_id = EXCLUDED.curriculum_id,
                    assigned_at   = NOW(),
                    assigned_by   = EXCLUDED.assigned_by
            RETURNING assigned_at
            """,
            school_id, grade, curriculum_id, teacher.get("teacher_id"),
        )

    log.info(
        "school_grade_curriculum_assign school_id=%s grade=%d "
        "curriculum_id=%s previous=%s",
        school_id, grade, curriculum_id, previous_curriculum_id,
    )

    return AssignCurriculumResponse(
        school_id=school_id,
        grade=grade,
        curriculum_id=curriculum_id,
        assigned_at=result_row["assigned_at"],
        previous_curriculum_id=previous_curriculum_id,
    )
