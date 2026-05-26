"""
backend/src/admin/authoring_router.py

Curriculum Authoring Studio — super-admin TOC-driven content authoring.

PR-A endpoints (intake → analyze → structure → materialize):
  POST   /admin/authoring/projects                       create
  GET    /admin/authoring/projects                       list
  GET    /admin/authoring/projects/{project_id}          detail
  POST   /admin/authoring/projects/{project_id}/analyze  structure + flow (async)
  PUT    /admin/authoring/projects/{project_id}/structure save edits
  POST   /admin/authoring/projects/{project_id}/materialize  → staged curriculum

Gate: every endpoint requires the `curriculum:author` permission, which only
super_admin holds (via its wildcard). product_admin and below get 403.

PR-B will add generate / topic review / regenerate / snapshot / publish here.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request

from src.admin import authoring_service as svc
from src.admin.authoring_schemas import (
    AnalyzeResponse,
    CreateProjectRequest,
    CreateProjectResponse,
    EditStructureRequest,
    MaterializeResponse,
    ProjectDetail,
    ProjectListResponse,
)
from src.auth.dependencies import get_current_admin
from src.core.db import get_db
from src.core.events import emit_event, write_audit_log
from src.core.permissions import _has_permission
from src.utils.logger import get_logger

log = get_logger("authoring")
router = APIRouter(tags=["authoring"])

_AUTHOR_PERMISSION = "curriculum:author"


def _require_author():
    """Chained dependency: verify admin JWT, then require curriculum:author.

    get_current_admin verifies ADMIN_JWT_SECRET and stamps
    request.state.jwt_payload; this inner dep enforces the permission. Only
    super_admin satisfies curriculum:author (wildcard), so the studio is
    super-admin-only.
    """

    async def dep(
        request: Request,
        admin: Annotated[dict, Depends(get_current_admin)],
    ) -> dict:
        role = admin.get("role", "")
        if not _has_permission(role, _AUTHOR_PERMISSION):
            log.warning(
                "authoring_permission_denied role=%s actor_id=%s",
                role,
                admin.get("admin_id"),
            )
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "forbidden",
                    "detail": (
                        f"Role '{role}' does not have permission "
                        f"'{_AUTHOR_PERMISSION}'."
                    ),
                    "correlation_id": getattr(request.state, "correlation_id", ""),
                },
            )
        return admin

    return dep


def _actor_uuid(admin: dict) -> uuid.UUID | None:
    raw = admin.get("admin_id")
    if not raw:
        return None
    try:
        return uuid.UUID(str(raw))
    except (ValueError, TypeError):
        return None


def _not_found(project_id: str, request: Request) -> HTTPException:
    return HTTPException(
        status_code=404,
        detail={
            "error": "not_found",
            "detail": f"Authoring project {project_id!r} not found.",
            "correlation_id": getattr(request.state, "correlation_id", ""),
        },
    )


# ── 1. Create ──────────────────────────────────────────────────────────────────


@router.post(
    "/admin/authoring/projects",
    response_model=CreateProjectResponse,
    status_code=201,
)
async def create_project(
    body: CreateProjectRequest,
    request: Request,
    admin: Annotated[dict, Depends(_require_author())],
) -> CreateProjectResponse:
    async with get_db(request) as conn:
        project = await svc.create_project(
            conn,
            title=body.title,
            grade=body.grade,
            languages=body.languages,
            raw_toc=body.raw_toc,
            created_by=_actor_uuid(admin),
        )
    emit_event(
        "authoring",
        "project_created",
        project_id=project["project_id"],
        grade=body.grade,
        raw_toc_chars=len(body.raw_toc),
    )
    return CreateProjectResponse(
        project_id=project["project_id"], status=project["status"]
    )


# ── 2. List ──────────────────────────────────────────────────────────────────


@router.get("/admin/authoring/projects", response_model=ProjectListResponse)
async def list_projects(
    request: Request,
    admin: Annotated[dict, Depends(_require_author())],
) -> ProjectListResponse:
    async with get_db(request) as conn:
        projects, total = await svc.list_projects(conn)
    return ProjectListResponse(projects=projects, total=total)


# ── 3. Detail ──────────────────────────────────────────────────────────────────


@router.get(
    "/admin/authoring/projects/{project_id}", response_model=ProjectDetail
)
async def get_project(
    project_id: str,
    request: Request,
    admin: Annotated[dict, Depends(_require_author())],
) -> ProjectDetail:
    async with get_db(request) as conn:
        project = await svc.get_project(conn, project_id)
    if project is None:
        raise _not_found(project_id, request)
    return ProjectDetail(**project)


# ── 4. Analyze (async) ──────────────────────────────────────────────────────────


@router.post(
    "/admin/authoring/projects/{project_id}/analyze",
    response_model=AnalyzeResponse,
    status_code=202,
)
async def analyze_project(
    project_id: str,
    request: Request,
    admin: Annotated[dict, Depends(_require_author())],
) -> AnalyzeResponse:
    async with get_db(request) as conn:
        project = await svc.get_project(conn, project_id)
        if project is None:
            raise _not_found(project_id, request)
        ok = await svc.mark_analyzing(conn, project_id)
    if not ok:
        raise HTTPException(
            status_code=409,
            detail={
                "error": "conflict",
                "detail": (
                    f"Project is in status {project['status']!r}; analysis can "
                    "only run from draft/analyzed/structured."
                ),
                "correlation_id": getattr(request.state, "correlation_id", ""),
            },
        )

    from src.core.celery_app import celery_app as _celery

    job_id = str(uuid.uuid4())
    _celery.send_task(
        "src.auth.tasks.run_authoring_analyze_task",
        args=[project_id],
        queue="pipeline",
    )
    emit_event("authoring", "analyze_dispatched", project_id=project_id, job_id=job_id)
    return AnalyzeResponse(job_id=job_id, status="analyzing")


# ── 5. Save structure edits ─────────────────────────────────────────────────────


@router.put(
    "/admin/authoring/projects/{project_id}/structure",
    response_model=ProjectDetail,
)
async def edit_structure(
    project_id: str,
    body: EditStructureRequest,
    request: Request,
    admin: Annotated[dict, Depends(_require_author())],
) -> ProjectDetail:
    async with get_db(request) as conn:
        existing = await svc.get_project(conn, project_id)
        if existing is None:
            raise _not_found(project_id, request)
        updated = await svc.save_structure(
            conn, project_id, body.structured_toc.model_dump()
        )
    if updated is None:
        raise HTTPException(
            status_code=409,
            detail={
                "error": "conflict",
                "detail": (
                    f"Project is in status {existing['status']!r}; structure can "
                    "only be edited after analysis (analyzed/structured)."
                ),
                "correlation_id": getattr(request.state, "correlation_id", ""),
            },
        )
    return ProjectDetail(**updated)


# ── 6. Materialize → staged platform curriculum ─────────────────────────────────


@router.post(
    "/admin/authoring/projects/{project_id}/materialize",
    response_model=MaterializeResponse,
    status_code=201,
)
async def materialize_project(
    project_id: str,
    request: Request,
    admin: Annotated[dict, Depends(_require_author())],
) -> MaterializeResponse:
    async with get_db(request) as conn:
        try:
            result = await svc.materialize(conn, project_id, _actor_uuid(admin))
        except svc.MaterializeError as exc:
            if "not found" in str(exc):
                raise _not_found(project_id, request) from exc
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "conflict",
                    "detail": str(exc),
                    "correlation_id": getattr(request.state, "correlation_id", ""),
                },
            ) from exc

    emit_event(
        "authoring",
        "materialized",
        project_id=project_id,
        curriculum_id=result["curriculum_id"],
        units=result["units_created"],
    )
    write_audit_log(
        event_type="authoring.materialize",
        actor_type="admin",
        actor_id=_actor_uuid(admin),
        target_type="curriculum",
        target_id=None,
        metadata={
            "project_id": project_id,
            "curriculum_id": result["curriculum_id"],
            "units": result["units_created"],
        },
    )
    return MaterializeResponse(**result)
