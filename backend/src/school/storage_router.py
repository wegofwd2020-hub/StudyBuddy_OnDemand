"""
backend/src/school/storage_router.py

School storage quota and metering endpoints.

Routes (all prefixed /api/v1 in main.py):
  GET /schools/{school_id}/storage   — quota summary + per-curriculum breakdown
                                       school_admin JWT only

Auth:
  school_admin JWT only.
  school_id in path must match the JWT school_id claim.

Storage model (from DESIGN_lesson_retention_service.md §5):
  - Base quota: 5 GB included with every school subscription.
  - Additional: 5 GB add-on increments via Stripe (Phase G).
  - Metering: SUM(payload_bytes) across pipeline_jobs for the school's curricula.
  - Fast read: school_storage_quotas.used_bytes (updated by nightly reconcile task
    and atomically incremented by the pipeline worker on job completion).
  - Breakdown: aggregated from pipeline_jobs grouped by curriculum_id.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException, Request
from fastapi.params import Depends
from pydantic import BaseModel

from src.auth.dependencies import get_current_teacher
from src.core.db import get_db
from src.pricing import SCHOOL_PLANS as _PLANS
from src.utils.logger import get_logger

# Base storage GB included with every school subscription.
# Defined in src/pricing.py — no magic numbers here.
_BASE_STORAGE_GB: int = _PLANS["starter"].storage_base_gb

log = get_logger("school.storage")
router = APIRouter(tags=["school-storage"])

_BYTES_PER_GB = 1_073_741_824  # 1024^3


# ── Schemas ───────────────────────────────────────────────────────────────────


class CurriculumStorageBreakdown(BaseModel):
    curriculum_id: str
    grade: int
    name: str
    bytes_used: int
    gb_used: float
    job_count: int


class SchoolStorageResponse(BaseModel):
    school_id: str
    base_gb: int
    purchased_gb: int
    total_gb: int
    used_bytes: int
    used_gb: float
    used_pct: float           # percentage of total quota used (capped at 100 in display)
    over_quota: bool
    breakdown: list[CurriculumStorageBreakdown]


# ── Helpers ───────────────────────────────────────────────────────────────────


def _cid(request: Request) -> str:
    return getattr(request.state, "correlation_id", "")


def _assert_school_match(teacher: dict, school_id: str, request: Request) -> None:
    if teacher.get("school_id") != school_id:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "forbidden",
                "detail": "You can only view storage for your own school.",
                "correlation_id": _cid(request),
            },
        )


def _assert_school_admin(teacher: dict, request: Request) -> None:
    if teacher.get("role") != "school_admin":
        raise HTTPException(
            status_code=403,
            detail={
                "error": "forbidden",
                "detail": "Only school_admin can view storage quotas.",
                "correlation_id": _cid(request),
            },
        )


def _round_gb(byte_count: int) -> float:
    return round(byte_count / _BYTES_PER_GB, 2)


# ── GET /schools/{school_id}/storage ─────────────────────────────────────────


@router.get(
    "/schools/{school_id}/storage",
    response_model=SchoolStorageResponse,
)
async def get_school_storage(
    school_id: str,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
) -> SchoolStorageResponse:
    """
    Return the school's storage quota and current usage.

    Fast path: used_bytes is read from school_storage_quotas (maintained by the
    nightly reconcile task and updated atomically by the pipeline worker).

    Breakdown: payload_bytes aggregated from pipeline_jobs per curriculum_id
    (joined to curricula for grade/name). Only completed jobs are counted —
    queued/running/failed jobs do not contribute to storage.
    """
    _assert_school_match(teacher, school_id, request)
    _assert_school_admin(teacher, request)

    async with get_db(request) as conn:
        # ── Quota row ─────────────────────────────────────────────────────────
        quota_row = await conn.fetchrow(
            """
            SELECT base_gb, purchased_gb, used_bytes
            FROM school_storage_quotas
            WHERE school_id = $1::uuid
            """,
            school_id,
        )

        if not quota_row:
            # This should not happen — migration 0029 seeds one row per school.
            # Guard defensively and return zero-state.
            log.warning("school_storage_quota_missing school_id=%s", school_id)
            base_gb, purchased_gb, used_bytes = _BASE_STORAGE_GB, 0, 0
        else:
            base_gb = quota_row["base_gb"]
            purchased_gb = quota_row["purchased_gb"]
            used_bytes = quota_row["used_bytes"]

        # ── Per-curriculum breakdown ──────────────────────────────────────────
        # SUM payload_bytes across completed pipeline jobs per curriculum.
        # Jobs that are queued, running, or failed do not yet represent
        # persisted content on disk, so we exclude them.
        rows = await conn.fetch(
            """
            SELECT
                pj.curriculum_id,
                COALESCE(MAX(pj.grade), 0)          AS grade,
                COALESCE(MAX(c.name), pj.curriculum_id) AS name,
                COALESCE(SUM(pj.payload_bytes), 0)  AS bytes_used,
                COUNT(pj.job_id)                    AS job_count
            FROM pipeline_jobs pj
            LEFT JOIN curricula c ON c.curriculum_id = pj.curriculum_id
            WHERE pj.school_id = $1::uuid
              AND pj.status = 'completed'
              AND pj.payload_bytes IS NOT NULL
            GROUP BY pj.curriculum_id
            ORDER BY bytes_used DESC
            """,
            school_id,
        )

    total_gb = base_gb + purchased_gb
    total_bytes = total_gb * _BYTES_PER_GB
    used_gb = _round_gb(used_bytes)
    used_pct = round((used_bytes / total_bytes * 100) if total_bytes > 0 else 0.0, 1)

    breakdown = [
        CurriculumStorageBreakdown(
            curriculum_id=r["curriculum_id"],
            grade=r["grade"] or 0,
            name=r["name"],
            bytes_used=int(r["bytes_used"]),
            gb_used=_round_gb(int(r["bytes_used"])),
            job_count=int(r["job_count"]),
        )
        for r in rows
    ]

    return SchoolStorageResponse(
        school_id=school_id,
        base_gb=base_gb,
        purchased_gb=purchased_gb,
        total_gb=total_gb,
        used_bytes=used_bytes,
        used_gb=used_gb,
        used_pct=used_pct,
        over_quota=used_bytes > total_bytes,
        breakdown=breakdown,
    )
