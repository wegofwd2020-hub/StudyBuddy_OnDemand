"""
backend/src/school/capability_guards.py

Three-tier curriculum-capability guards (issue #358), shared across the school
routers so the same authorization logic isn't duplicated.

Each guard takes the decoded teacher JWT payload, the path school_id, and the
request (for the correlation id), and raises HTTP 403 when the caller is not
authorized. They are *the* authorization gate — hiding a nav button is never
sufficient (pitfall #10).

Tiers
─────
  require_curriculum_view  — any curriculum capability (or school_admin). Lets a
                             reviewer see what's been commissioned and vice versa.
  require_commission       — Gate 1: curriculum.commission | umbrella | school_admin
  require_review           — Gate 2: curriculum.review     | umbrella | school_admin

All three first enforce that the caller belongs to the path school.
"""

from __future__ import annotations

from fastapi import HTTPException, Request

from src.core.permissions import has_any_curriculum_capability, has_capability


def _cid(request: Request) -> str:
    return getattr(request.state, "correlation_id", "")


def _forbidden(request: Request, detail: str) -> HTTPException:
    return HTTPException(
        status_code=403,
        detail={"error": "forbidden", "detail": detail, "correlation_id": _cid(request)},
    )


def _assert_same_school(teacher: dict, school_id: str, request: Request) -> None:
    if teacher.get("school_id") != school_id:
        raise _forbidden(request, "Cannot manage curriculum for a different school.")


def require_curriculum_view(teacher: dict, school_id: str, request: Request) -> None:
    """Tier 0 — view the pending-approval / content-review queues."""
    _assert_same_school(teacher, school_id, request)
    if not has_any_curriculum_capability(teacher):
        raise _forbidden(request, "Requires a curriculum-management capability to view this.")


def require_commission(teacher: dict, school_id: str, request: Request) -> None:
    """Gate 1 — commission: approve/adopt/load + trigger generation (spends budget)."""
    _assert_same_school(teacher, school_id, request)
    if not has_capability(teacher, "curriculum.commission"):
        raise _forbidden(
            request, "Requires the 'curriculum.commission' capability (or school_admin)."
        )


def require_review(teacher: dict, school_id: str, request: Request) -> None:
    """Gate 2 — review: approve/publish generated content (editorial)."""
    _assert_same_school(teacher, school_id, request)
    if not has_capability(teacher, "curriculum.review"):
        raise _forbidden(request, "Requires the 'curriculum.review' capability (or school_admin).")
