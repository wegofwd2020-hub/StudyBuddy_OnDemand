"""
backend/src/admin/retention_router.py

Platform-wide curriculum retention monitor for super_admin / product_admin.

Routes (all prefixed /api/v1 in main.py):
  GET  /admin/retention
       — Platform-wide view of all school curricula with retention status,
         urgency signals, and school contact details.
         Sortable by urgency (soonest expiry/purge first).
         Optional filters: status, school_id, grade, expiring_days.

  POST /admin/schools/{school_id}/curriculum/versions/{curriculum_id}/action
       — Renew, force-expire, or force-delete a curriculum version on behalf
         of any school. All actions are written to the audit log with a reason.

Auth: Admin JWT only (product_admin or super_admin via 'school:manage' permission).
      'developer' and 'tester' roles are rejected.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from src.auth.dependencies import get_current_admin
from src.core.cdn import invalidate_curriculum
from src.core.db import get_db
from src.core.permissions import ROLE_PERMISSIONS
from src.core.storage import StorageBackend, get_storage
from src.utils.logger import get_logger

log = get_logger("admin.retention")
router = APIRouter(tags=["admin-retention"])


# ── Combined auth + RBAC dependency (same pattern as admin/router.py) ──────────
# Chaining get_current_admin inside ensures JWT verify always runs first,
# setting request.state.jwt_payload before the permission check reads it.


def _require(permission: str):
    """Admin auth + RBAC check in one chained dependency."""

    async def dep(
        request: Request,
        admin: Annotated[dict, Depends(get_current_admin)],
    ) -> dict:
        role = admin.get("role", "")
        perms = ROLE_PERMISSIONS.get(role, set())
        if "*" not in perms and permission not in perms:
            log.warning(
                "permission_denied",
                role=role,
                required=permission,
                actor_id=admin.get("admin_id"),
            )
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "forbidden",
                    "detail": f"Role '{role}' does not have permission '{permission}'.",
                    "correlation_id": getattr(request.state, "correlation_id", ""),
                },
            )
        return admin

    return dep


# ── Schemas ───────────────────────────────────────────────────────────────────


class AdminRetentionItem(BaseModel):
    curriculum_id: str
    school_id: str
    school_name: str
    contact_email: str
    grade: int
    name: str
    year: int
    retention_status: str          # active | unavailable | purged
    expires_at: datetime | None
    grace_until: datetime | None
    days_until_expiry: int | None  # set for active curricula only
    days_until_purge: int | None   # set for unavailable curricula in grace
    is_assigned: bool


class AdminRetentionSummary(BaseModel):
    total: int
    active: int
    unavailable: int
    purged: int
    expiring_soon: int             # active with days_until_expiry ≤ expiring_days threshold


class AdminRetentionDashboard(BaseModel):
    summary: AdminRetentionSummary
    curricula: list[AdminRetentionItem]


class CurriculumActionRequest(BaseModel):
    action: Literal["renew", "force_expire", "force_delete"]
    reason: str = ""


class CurriculumActionResponse(BaseModel):
    curriculum_id: str
    school_id: str
    action: str
    success: bool
    detail: str
    # Populated for renew and force_expire:
    new_expires_at: datetime | None = None
    new_grace_until: datetime | None = None
    new_retention_status: str | None = None
    # Populated for force_delete:
    units_removed: int | None = None
    versions_removed: int | None = None


# ── Helpers ───────────────────────────────────────────────────────────────────


def _cid(request: Request) -> str:
    return getattr(request.state, "correlation_id", "")


def _admin_id(admin: dict) -> str:
    return admin.get("admin_id", "")


# ── GET /admin/retention ──────────────────────────────────────────────────────


@router.get(
    "/admin/retention",
    response_model=AdminRetentionDashboard,
    status_code=200,
)
async def get_admin_retention_dashboard(
    request: Request,
    admin: Annotated[dict, Depends(_require("school:manage"))],
    status: str | None = Query(None, description="Filter by retention_status"),
    school_id: str | None = Query(None, description="Filter by school_id UUID"),
    grade: int | None = Query(None, description="Filter by grade"),
    expiring_days: int = Query(30, ge=1, le=365, description="Days threshold for expiring_soon count"),
) -> AdminRetentionDashboard:
    """
    Platform-wide retention dashboard.

    Returns every school curriculum across all schools, sorted by urgency:
      1. Unavailable (in grace), fewest days_until_purge first
      2. Active, fewest days_until_expiry first
      3. Purged (most recently purged first)
      4. Active with no expiry set (alphabetical by school name)

    Accessible by product_admin and super_admin only.
    RLS is bypassed (admin context has no school_id constraint).
    """
    now = datetime.now(UTC)

    # Build optional WHERE clauses
    conditions = ["c.owner_type = 'school'"]
    params: list = []
    p = 1

    if status:
        conditions.append(f"c.retention_status = ${p}")
        params.append(status)
        p += 1
    if school_id:
        try:
            conditions.append(f"c.school_id = ${p}::uuid")
            params.append(school_id)
            p += 1
        except Exception:
            raise HTTPException(
                status_code=422,
                detail={"error": "invalid_school_id", "detail": "school_id must be a valid UUID"},
            )
    if grade is not None:
        conditions.append(f"c.grade = ${p}")
        params.append(grade)
        p += 1

    where = " AND ".join(conditions)

    async with get_db(request) as conn:
        rows = await conn.fetch(
            f"""
            SELECT
                c.curriculum_id,
                c.school_id::text AS school_id,
                s.name            AS school_name,
                s.contact_email,
                c.grade,
                c.name,
                c.year,
                c.retention_status,
                c.expires_at,
                c.grace_until,
                CASE WHEN gca.curriculum_id IS NOT NULL THEN TRUE ELSE FALSE END AS is_assigned
            FROM curricula c
            JOIN schools s ON s.school_id = c.school_id
            LEFT JOIN grade_curriculum_assignments gca
                   ON gca.curriculum_id = c.curriculum_id
                  AND gca.school_id = c.school_id
            WHERE {where}
            ORDER BY
                -- unavailable with fewest days in grace first
                CASE WHEN c.retention_status = 'unavailable' AND c.grace_until IS NOT NULL
                     THEN c.grace_until END ASC NULLS LAST,
                -- active with fewest days to expiry first
                CASE WHEN c.retention_status = 'active' AND c.expires_at IS NOT NULL
                     THEN c.expires_at END ASC NULLS LAST,
                -- purged: most recently expired first
                CASE WHEN c.retention_status = 'purged' THEN c.expires_at END DESC NULLS LAST,
                s.name ASC, c.grade ASC
            """,
            *params,
        )

    curricula: list[AdminRetentionItem] = []
    active_count = unavailable_count = purged_count = expiring_soon = 0

    for row in rows:
        rs = row["retention_status"]
        expires_at = row["expires_at"]
        grace_until = row["grace_until"]

        if rs == "active":
            active_count += 1
        elif rs == "unavailable":
            unavailable_count += 1
        else:
            purged_count += 1

        days_until_expiry: int | None = None
        if rs == "active" and expires_at is not None:
            delta = (expires_at - now).days
            days_until_expiry = max(delta, 0)
            if days_until_expiry <= expiring_days:
                expiring_soon += 1

        days_until_purge: int | None = None
        if rs == "unavailable" and grace_until is not None:
            delta = (grace_until - now).days
            days_until_purge = max(delta, 0)

        curricula.append(AdminRetentionItem(
            curriculum_id=row["curriculum_id"],
            school_id=row["school_id"],
            school_name=row["school_name"],
            contact_email=row["contact_email"],
            grade=row["grade"],
            name=row["name"],
            year=row["year"],
            retention_status=rs,
            expires_at=expires_at,
            grace_until=grace_until,
            days_until_expiry=days_until_expiry,
            days_until_purge=days_until_purge,
            is_assigned=row["is_assigned"],
        ))

    log.info(
        "admin_retention_dashboard total=%d active=%d unavailable=%d purged=%d expiring_soon=%d",
        len(curricula), active_count, unavailable_count, purged_count, expiring_soon,
    )

    return AdminRetentionDashboard(
        summary=AdminRetentionSummary(
            total=len(curricula),
            active=active_count,
            unavailable=unavailable_count,
            purged=purged_count,
            expiring_soon=expiring_soon,
        ),
        curricula=curricula,
    )


# ── POST /admin/schools/{school_id}/curriculum/versions/{curriculum_id}/action ─


@router.post(
    "/admin/schools/{school_id}/curriculum/versions/{curriculum_id}/action",
    response_model=CurriculumActionResponse,
    status_code=200,
)
async def admin_curriculum_action(
    school_id: str,
    curriculum_id: str,
    body: CurriculumActionRequest,
    request: Request,
    admin: Annotated[dict, Depends(_require("school:manage"))],
    storage: StorageBackend = Depends(get_storage),
) -> CurriculumActionResponse:
    """
    Perform an admin action on any school's curriculum version.

    Actions:
      renew        — Extend expires_at +1 year from original expiry;
                     reset retention_status='active'; clear grace_until.
                     Allowed for 'active' and 'unavailable' curricula.
                     Blocked for 'purged' (data already deleted from Content Store).

      force_expire — Immediately transition to 'unavailable' and set
                     grace_until = NOW() + 180 days.
                     Useful when a school requests early removal of access
                     without immediately deleting data.
                     Only allowed for 'active' curricula.

      force_delete — Cascading delete of all rows (annotations → reviews →
                     content_subject_versions → curriculum_units → curricula).
                     Bypasses the grade-assignment guard (admin override).
                     Unassigns the grade if necessary before deleting.

    All actions are written to audit_log.
    """
    admin_id_str = _admin_id(admin)

    async with get_db(request) as conn:
        # ── Ownership check ────────────────────────────────────────────────────
        row = await conn.fetchrow(
            """
            SELECT curriculum_id, grade, retention_status, expires_at, school_id::text AS sid
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
                    "detail": "Curriculum version not found for this school.",
                    "correlation_id": _cid(request),
                },
            )

        current_status = row["retention_status"]
        grade = row["grade"]

        # ── RENEW ──────────────────────────────────────────────────────────────
        if body.action == "renew":
            if current_status == "purged":
                raise HTTPException(
                    status_code=409,
                    detail={
                        "error": "already_purged",
                        "detail": (
                            "This curriculum has been permanently purged. "
                            "Content Store files are gone; it cannot be renewed. "
                            "Ask the school to upload and rebuild."
                        ),
                        "correlation_id": _cid(request),
                    },
                )

            updated = await conn.fetchrow(
                """
                UPDATE curricula
                SET expires_at       = COALESCE(expires_at, NOW()) + INTERVAL '1 year',
                    grace_until      = NULL,
                    retention_status = 'active',
                    renewed_at       = NOW()
                WHERE curriculum_id = $1
                RETURNING expires_at, grace_until, retention_status
                """,
                curriculum_id,
            )

            await _write_audit(
                conn, admin_id_str, "admin_curriculum_renew",
                curriculum_id, school_id, body.reason,
                {"previous_status": current_status, "new_expires_at": str(updated["expires_at"])},
            )

            log.info(
                "admin_curriculum_renew admin=%s curriculum=%s school=%s grade=%d",
                admin_id_str, curriculum_id, school_id, grade,
            )
            return CurriculumActionResponse(
                curriculum_id=curriculum_id,
                school_id=school_id,
                action="renew",
                success=True,
                detail="Curriculum renewed — expiry extended by 1 year.",
                new_expires_at=updated["expires_at"],
                new_grace_until=None,
                new_retention_status="active",
            )

        # ── FORCE EXPIRE ───────────────────────────────────────────────────────
        if body.action == "force_expire":
            if current_status != "active":
                raise HTTPException(
                    status_code=409,
                    detail={
                        "error": "not_active",
                        "detail": (
                            f"force_expire only applies to active curricula. "
                            f"This curriculum is '{current_status}'."
                        ),
                        "correlation_id": _cid(request),
                    },
                )

            updated = await conn.fetchrow(
                """
                UPDATE curricula
                SET retention_status = 'unavailable',
                    grace_until      = NOW() + INTERVAL '180 days'
                WHERE curriculum_id = $1
                RETURNING grace_until, retention_status
                """,
                curriculum_id,
            )

            await _write_audit(
                conn, admin_id_str, "admin_curriculum_force_expire",
                curriculum_id, school_id, body.reason,
                {"previous_status": current_status, "grace_until": str(updated["grace_until"])},
            )

            log.info(
                "admin_curriculum_force_expire admin=%s curriculum=%s school=%s grade=%d",
                admin_id_str, curriculum_id, school_id, grade,
            )
            return CurriculumActionResponse(
                curriculum_id=curriculum_id,
                school_id=school_id,
                action="force_expire",
                success=True,
                detail="Curriculum set to unavailable with 180-day grace period.",
                new_expires_at=row["expires_at"],
                new_grace_until=updated["grace_until"],
                new_retention_status="unavailable",
            )

        # ── FORCE DELETE ───────────────────────────────────────────────────────
        if body.action == "force_delete":
            async with conn.transaction():
                # Unassign from grade_curriculum_assignments if assigned (admin override)
                await conn.execute(
                    "DELETE FROM grade_curriculum_assignments WHERE curriculum_id = $1",
                    curriculum_id,
                )

                # Cascade delete
                await conn.execute(
                    """
                    DELETE FROM content_annotations
                    WHERE unit_id IN (
                        SELECT unit_id FROM curriculum_units WHERE curriculum_id = $1
                    )
                    """,
                    curriculum_id,
                )
                await conn.execute(
                    """
                    DELETE FROM content_reviews
                    WHERE version_id IN (
                        SELECT version_id FROM content_subject_versions WHERE curriculum_id = $1
                    )
                    """,
                    curriculum_id,
                )
                versions_result = await conn.execute(
                    "DELETE FROM content_subject_versions WHERE curriculum_id = $1",
                    curriculum_id,
                )
                units_result = await conn.execute(
                    "DELETE FROM curriculum_units WHERE curriculum_id = $1",
                    curriculum_id,
                )
                await conn.execute(
                    "DELETE FROM curricula WHERE curriculum_id = $1",
                    curriculum_id,
                )

            def _rowcount(result: str) -> int:
                try:
                    return int(result.split()[-1])
                except (IndexError, ValueError):
                    return 0

            units_removed = _rowcount(units_result)
            versions_removed = _rowcount(versions_result)

            # Delete content files from the Content Store.
            # Must run after the DB transaction so any request racing against
            # the delete already sees the curricula row as gone.
            try:
                await storage.delete_tree(f"curricula/{curriculum_id}")
                log.info(
                    "admin_force_delete_files_removed curriculum_id=%s", curriculum_id
                )
            except Exception as exc:
                # File deletion failure is logged but never suppresses the action —
                # the DB row is already gone; orphaned files can be cleaned up manually.
                log.warning(
                    "admin_force_delete_file_error curriculum_id=%s err=%s",
                    curriculum_id, exc,
                )

            # Invalidate CloudFront so purged content is evicted from the CDN edge.
            try:
                from config import settings as _cfg  # noqa: PLC0415
                await invalidate_curriculum(
                    curriculum_id,
                    getattr(_cfg, "CLOUDFRONT_DISTRIBUTION_ID", None),
                )
            except Exception as exc:
                log.warning(
                    "admin_force_delete_cdn_error curriculum_id=%s err=%s",
                    curriculum_id, exc,
                )

            await _write_audit(
                conn, admin_id_str, "admin_curriculum_force_delete",
                curriculum_id, school_id, body.reason,
                {
                    "previous_status": current_status,
                    "grade": grade,
                    "units_removed": units_removed,
                    "versions_removed": versions_removed,
                },
            )

            log.info(
                "admin_curriculum_force_delete admin=%s curriculum=%s school=%s "
                "grade=%d units=%d versions=%d",
                admin_id_str, curriculum_id, school_id, grade,
                units_removed, versions_removed,
            )
            return CurriculumActionResponse(
                curriculum_id=curriculum_id,
                school_id=school_id,
                action="force_delete",
                success=True,
                detail="Curriculum version permanently deleted.",
                units_removed=units_removed,
                versions_removed=versions_removed,
            )

        # Unreachable — Pydantic Literal validates the action field
        raise HTTPException(status_code=422, detail={"error": "invalid_action"})


# ── Audit helper ──────────────────────────────────────────────────────────────


async def _write_audit(
    conn,
    admin_id: str,
    action: str,
    curriculum_id: str,
    school_id: str,
    reason: str,
    metadata: dict,
) -> None:
    """Append an immutable audit log entry for an admin retention action."""
    import json as _json

    meta = {**metadata, "reason": reason, "school_id": school_id}
    try:
        await conn.execute(
            """
            INSERT INTO audit_log
                (event_type, actor_type, actor_id, target_type, target_id, metadata, timestamp)
            VALUES ($1, 'admin', $2::uuid, 'curriculum', $3, $4::jsonb, NOW())
            """,
            action,
            admin_id,
            curriculum_id,
            _json.dumps(meta),
        )
    except Exception as exc:
        # Audit failure must never suppress the primary action.
        log.error("admin_retention_audit_write_failed action=%s error=%s", action, exc)
