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
        "audit:view",
        "demo:reset",
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

# ── Additive capabilities (issue #358) ────────────────────────────────────────
# Capabilities are an *additive* grant carried in the JWT `capabilities[]` array
# alongside the single `role` claim. Unlike ROLE_PERMISSIONS (deploy-time, per
# role), capabilities are granted per teacher at runtime and minted into the JWT
# at login. school_admin is an implicit superset — it never needs a grant.
ALLOWED_CAPABILITIES: set[str] = {
    "curriculum.commission",  # Gate 1 — approve/adopt/load + trigger generation
    "curriculum.review",  # Gate 2 — approve/publish generated content
    "curriculum_mgmt",  # umbrella — covers both gates
}

# Umbrella capability → the specific capabilities it satisfies.
_CAPABILITY_UMBRELLAS: dict[str, set[str]] = {
    "curriculum_mgmt": {"curriculum.commission", "curriculum.review", "curriculum_mgmt"},
}

# Roles that implicitly hold every curriculum capability (superset).
_CAPABILITY_SUPERSET_ROLES: set[str] = {"school_admin"}


def _is_capability_superset(role: str) -> bool:
    """True if the role implicitly holds all capabilities (school_admin, or a
    wildcard admin role such as super_admin)."""
    return role in _CAPABILITY_SUPERSET_ROLES or "*" in ROLE_PERMISSIONS.get(role, set())


def has_capability(payload: dict, capability: str) -> bool:
    """Return True if the JWT payload grants *capability*.

    Passes when the role is a superset (school_admin / super_admin), the exact
    capability is held, or an umbrella capability covering it is held.
    """
    if _is_capability_superset(payload.get("role", "")):
        return True
    held: list[str] = payload.get("capabilities") or []
    if capability in held:
        return True
    return any(capability in _CAPABILITY_UMBRELLAS.get(h, set()) for h in held)


def has_any_curriculum_capability(payload: dict) -> bool:
    """Return True if the payload holds *any* curriculum capability (the view
    tier — lets a reviewer see what's been commissioned and vice versa)."""
    if _is_capability_superset(payload.get("role", "")):
        return True
    return bool(set(payload.get("capabilities") or []) & ALLOWED_CAPABILITIES)


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
