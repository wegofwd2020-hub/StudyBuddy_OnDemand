"""
backend/src/core/permissions.py

Static RBAC permission map and require_permission() FastAPI dependency.

No DB lookups on the hot path — permissions are defined at deploy time.
Adding a permission to a role = code change + deployment.
"""

from __future__ import annotations

from collections.abc import Callable

from fastapi import HTTPException, Request
from fastapi.security import HTTPBearer

from src.utils.logger import get_logger

log = get_logger("permissions")

# ── Permission matrix ─────────────────────────────────────────────────────────
# "*" means all permissions granted (super_admin only).
ROLE_PERMISSIONS: dict[str, set[str]] = {
    "student": {
        "content:read",
        "content:feedback",
    },
    # Demo students get read access for the duration of their trial.
    # No content:feedback — demo submissions would pollute the real feedback queue.
    "demo_student": {
        "content:read",
    },
    "teacher": {
        "content:read",
        "review:read",
        "review:annotate",
        "review:rate",
        "student:manage",
        "pipeline:trigger",
        "pipeline:view",
    },
    "school_admin": {
        "content:read",
        "review:read",
        "review:annotate",
        "review:rate",
        "review:approve",
        "content:block",
        "student:manage",
        "pipeline:trigger",
        "pipeline:view",
        "school:view_limits",
        "curriculum:delete",
    },
    "product_admin": {
        "content:read",
        "content:publish",
        "content:rollback",
        "content:block",
        "content:regenerate",
        "review:read",
        "review:annotate",
        "review:rate",
        "review:approve",
        "review:assign",
        "student:manage",
        "school:manage",
        "feedback:view",
    },
    "super_admin": {"*"},  # wildcard — all permissions granted
    # Platform Administrator — manages demo leads, geo-blocks, and demo settings only.
    "plat_admin": {
        "demo:manage",
    },
    "developer": {
        "content:read",
        "review:read",
        "review:rate",
    },
    "tester": {
        "content:read",
        "review:read",
        "review:rate",
        "review:annotate",
    },
}

_bearer = HTTPBearer(auto_error=False)


def _has_permission(role: str, permission: str) -> bool:
    """Return True if the role grants the given permission."""
    perms = ROLE_PERMISSIONS.get(role, set())
    return "*" in perms or permission in perms


def require_permission(permission: str) -> Callable:
    """
    FastAPI dependency factory.

    Raises HTTP 403 if the token's role does not grant *permission*.

    Usage:
        @router.get("/admin/something",
                    dependencies=[Depends(require_permission("school:manage"))])
        async def handler():
            ...

    The dependency relies on the JWT payload being stored on request.state
    by get_current_student / get_current_teacher / get_current_admin.
    """

    async def dependency(request: Request) -> None:
        # The auth dependency must have already run and stored the payload.
        payload: dict | None = getattr(request.state, "jwt_payload", None)
        if payload is None:
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "forbidden",
                    "detail": "Authentication required.",
                    "correlation_id": getattr(request.state, "correlation_id", ""),
                },
            )
        role: str = payload.get("role", "")
        if not _has_permission(role, permission):
            log.warning(
                "permission_denied",
                role=role,
                required=permission,
                actor_id=payload.get("student_id")
                or payload.get("teacher_id")
                or payload.get("admin_id"),
            )
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "forbidden",
                    "detail": f"Role '{role}' does not have permission '{permission}'.",
                    "correlation_id": getattr(request.state, "correlation_id", ""),
                },
            )

    return dependency
