"""
backend/src/admin/streams_router.py

Admin CRUD + housekeeping for the curriculum Streams registry (H-10 / S-2).

Soft registry model: `curricula.stream_code` stays free text; `streams` is a
lookup table that is upserted on use (by upload-grade) and maintained via the
endpoints below. There is deliberately no FK between them — see migration 0045.

Routes (all prefixed /api/v1 in app_factory, all require `content:publish`):

  GET    /admin/streams                       — list (q prefix, include_archived)
  GET    /admin/streams/{code}                — detail + sample curricula
  POST   /admin/streams                       — create (non-system)
  PATCH  /admin/streams/{code}                — update display_name / description
  POST   /admin/streams/{code}/archive
  POST   /admin/streams/{code}/unarchive
  POST   /admin/streams/{code}/merge          — move all curricula + archive source
  DELETE /admin/streams/{code}                — hard delete (gated)
"""

from __future__ import annotations

import re
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from src.admin.schemas import (
    StreamCreateRequest,
    StreamCurriculumSummary,
    StreamDetailResponse,
    StreamListResponse,
    StreamMergeRequest,
    StreamMergeResponse,
    StreamResponse,
    StreamUpdateRequest,
)
from src.auth.dependencies import get_current_admin
from src.core.db import get_db
from src.core.permissions import ROLE_PERMISSIONS
from src.utils.logger import get_logger

log = get_logger("admin.streams")

router = APIRouter()


_CODE_PATTERN = re.compile(r"^[a-z0-9-]+$")
_RESERVED_CODES = {"none", "other", "all", "default", "null"}
_CODE_SLUG_REPLACE = re.compile(r"[^a-z0-9-]+")


def _require(permission: str):
    async def dep(
        request: Request,
        admin: Annotated[dict, Depends(get_current_admin)],
    ) -> dict:
        role = admin.get("role", "")
        perms = ROLE_PERMISSIONS.get(role, set())
        if "*" not in perms and permission not in perms:
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "forbidden",
                    "detail": f"Role '{role}' does not have permission '{permission}'.",
                },
            )
        return admin

    return dep


def slugify_stream_code(raw: str) -> str:
    """Lowercase, collapse whitespace + non-[a-z0-9-] runs into '-'."""
    s = raw.strip().lower()
    s = s.replace(" ", "-")
    s = _CODE_SLUG_REPLACE.sub("-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s


def _validate_code_shape(code: str) -> None:
    if not (3 <= len(code) <= 30):
        raise HTTPException(
            status_code=400,
            detail={"error": "validation_error", "detail": "Stream code must be 3–30 characters."},
        )
    if not _CODE_PATTERN.match(code):
        raise HTTPException(
            status_code=400,
            detail={
                "error": "validation_error",
                "detail": "Stream code may only contain lowercase letters, digits, and hyphens.",
            },
        )
    if code in _RESERVED_CODES:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "validation_error",
                "detail": f"'{code}' is a reserved code.",
            },
        )


def _row_to_stream(row) -> StreamResponse:
    return StreamResponse(
        code=row["code"],
        display_name=row["display_name"],
        description=row["description"],
        is_system=row["is_system"],
        is_archived=row["is_archived"],
        curricula_count=row["curricula_count"],
        created_at=row["created_at"],
    )


async def _recompute_count(conn, code: str) -> int:
    count = await conn.fetchval(
        "SELECT COUNT(*) FROM curricula WHERE stream_code = $1",
        code,
    )
    await conn.execute(
        "UPDATE streams SET curricula_count = $1 WHERE code = $2",
        count,
        code,
    )
    return count


# ── Internal helpers used by the upload-grade / trigger endpoints ────────────


async def resolve_stream_for_upload(
    conn,
    *,
    stream: str | None,
    display_name: str | None,
    admin_id: str | None,
) -> str | None:
    """
    Resolve a user-submitted stream to its canonical code.

    Behaviour:
      - stream is None → return None (stream-unaware upload, legacy path)
      - stream exists in registry → return its canonical code
      - stream not in registry AND display_name supplied → create a non-system
        row via slugified code, return it
      - stream not in registry AND no display_name → 400

    Archived streams are treated as unknown — you have to unarchive before
    using again, which is deliberate.
    """
    if not stream:
        return None
    code = slugify_stream_code(stream)
    if not code:
        raise HTTPException(
            status_code=400,
            detail={"error": "validation_error", "detail": "Stream code is empty after normalising."},
        )

    row = await conn.fetchrow(
        "SELECT code, is_archived FROM streams WHERE code = $1",
        code,
    )
    if row and not row["is_archived"]:
        return row["code"]
    if row and row["is_archived"]:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "validation_error",
                "detail": f"Stream '{code}' is archived. Unarchive it before uploading.",
            },
        )

    if not display_name:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "validation_error",
                "detail": (
                    f"Stream '{code}' is not in the registry. "
                    "Pass stream_display_name to create it on first use."
                ),
            },
        )

    _validate_code_shape(code)

    await conn.execute(
        """
        INSERT INTO streams (code, display_name, is_system, created_by_admin_id)
        VALUES ($1, $2, false, $3)
        ON CONFLICT (code) DO NOTHING
        """,
        code,
        display_name.strip(),
        uuid.UUID(admin_id) if admin_id else None,
    )
    log.info("stream_upserted_on_use code=%s admin=%s", code, admin_id)
    return code


# ── Endpoints ────────────────────────────────────────────────────────────────


@router.get("/admin/streams", response_model=StreamListResponse)
async def list_streams(
    request: Request,
    admin: Annotated[dict, Depends(_require("content:publish"))],
    q: str | None = Query(None, min_length=1, max_length=50),
    include_archived: bool = Query(False),
) -> StreamListResponse:
    sql = [
        "SELECT code, display_name, description, is_system, is_archived,",
        "       curricula_count, created_at",
        "  FROM streams",
        " WHERE 1 = 1",
    ]
    args: list = []
    if not include_archived:
        sql.append("   AND is_archived = false")
    if q:
        args.append(f"{q.strip().lower()}%")
        sql.append(f"   AND (lower(code) LIKE ${len(args)} OR lower(display_name) LIKE ${len(args)})")
    sql.append(" ORDER BY is_archived ASC, code ASC")

    async with get_db(request) as conn:
        rows = await conn.fetch(" ".join(sql), *args)
    return StreamListResponse(streams=[_row_to_stream(r) for r in rows])


@router.get("/admin/streams/{code}", response_model=StreamDetailResponse)
async def get_stream(
    code: str,
    request: Request,
    admin: Annotated[dict, Depends(_require("content:publish"))],
) -> StreamDetailResponse:
    async with get_db(request) as conn:
        row = await conn.fetchrow(
            """
            SELECT code, display_name, description, is_system, is_archived,
                   curricula_count, created_at
              FROM streams
             WHERE code = $1
            """,
            code,
        )
        if not row:
            raise HTTPException(
                status_code=404,
                detail={"error": "not_found", "detail": f"Stream '{code}' not found."},
            )
        curricula = await conn.fetch(
            """
            SELECT curriculum_id, grade, year, name
              FROM curricula
             WHERE stream_code = $1
             ORDER BY grade ASC, year DESC
             LIMIT 50
            """,
            code,
        )
    return StreamDetailResponse(
        stream=_row_to_stream(row),
        curricula=[
            StreamCurriculumSummary(
                curriculum_id=c["curriculum_id"],
                grade=c["grade"],
                year=c["year"],
                name=c["name"],
            )
            for c in curricula
        ],
    )


@router.post("/admin/streams", response_model=StreamResponse, status_code=201)
async def create_stream(
    body: StreamCreateRequest,
    request: Request,
    admin: Annotated[dict, Depends(_require("content:publish"))],
) -> StreamResponse:
    code = body.code.strip().lower()
    _validate_code_shape(code)

    admin_id = admin.get("admin_id")
    async with get_db(request) as conn:
        existing = await conn.fetchrow(
            "SELECT code FROM streams WHERE lower(code) = $1",
            code,
        )
        if existing:
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "conflict",
                    "detail": f"Stream '{existing['code']}' already exists.",
                },
            )
        row = await conn.fetchrow(
            """
            INSERT INTO streams (code, display_name, description, is_system, created_by_admin_id)
            VALUES ($1, $2, $3, false, $4)
            RETURNING code, display_name, description, is_system, is_archived,
                      curricula_count, created_at
            """,
            code,
            body.display_name.strip(),
            (body.description or "").strip() or None,
            uuid.UUID(admin_id) if admin_id else None,
        )
    log.info("stream_created code=%s admin=%s", code, admin_id)
    return _row_to_stream(row)


@router.patch("/admin/streams/{code}", response_model=StreamResponse)
async def update_stream(
    code: str,
    body: StreamUpdateRequest,
    request: Request,
    admin: Annotated[dict, Depends(_require("content:publish"))],
) -> StreamResponse:
    if body.display_name is None and body.description is None:
        raise HTTPException(
            status_code=400,
            detail={"error": "validation_error", "detail": "Nothing to update."},
        )
    async with get_db(request) as conn:
        row = await conn.fetchrow(
            """
            UPDATE streams
               SET display_name = COALESCE($2, display_name),
                   description  = COALESCE($3, description)
             WHERE code = $1
            RETURNING code, display_name, description, is_system, is_archived,
                      curricula_count, created_at
            """,
            code,
            body.display_name.strip() if body.display_name else None,
            body.description.strip() if body.description is not None else None,
        )
        if not row:
            raise HTTPException(
                status_code=404,
                detail={"error": "not_found", "detail": f"Stream '{code}' not found."},
            )
    return _row_to_stream(row)


@router.post("/admin/streams/{code}/archive", response_model=StreamResponse)
async def archive_stream(
    code: str,
    request: Request,
    admin: Annotated[dict, Depends(_require("content:publish"))],
) -> StreamResponse:
    async with get_db(request) as conn:
        row = await conn.fetchrow(
            """
            UPDATE streams
               SET is_archived = true
             WHERE code = $1
            RETURNING code, display_name, description, is_system, is_archived,
                      curricula_count, created_at
            """,
            code,
        )
        if not row:
            raise HTTPException(
                status_code=404,
                detail={"error": "not_found", "detail": f"Stream '{code}' not found."},
            )
    log.info("stream_archived code=%s admin=%s", code, admin.get("admin_id"))
    return _row_to_stream(row)


@router.post("/admin/streams/{code}/unarchive", response_model=StreamResponse)
async def unarchive_stream(
    code: str,
    request: Request,
    admin: Annotated[dict, Depends(_require("content:publish"))],
) -> StreamResponse:
    async with get_db(request) as conn:
        row = await conn.fetchrow(
            """
            UPDATE streams
               SET is_archived = false
             WHERE code = $1
            RETURNING code, display_name, description, is_system, is_archived,
                      curricula_count, created_at
            """,
            code,
        )
        if not row:
            raise HTTPException(
                status_code=404,
                detail={"error": "not_found", "detail": f"Stream '{code}' not found."},
            )
    log.info("stream_unarchived code=%s admin=%s", code, admin.get("admin_id"))
    return _row_to_stream(row)


@router.post("/admin/streams/{code}/merge", response_model=StreamMergeResponse)
async def merge_stream(
    code: str,
    body: StreamMergeRequest,
    request: Request,
    admin: Annotated[dict, Depends(_require("content:publish"))],
) -> StreamMergeResponse:
    target_code = body.target_code.strip().lower()
    if target_code == code:
        raise HTTPException(
            status_code=400,
            detail={"error": "validation_error", "detail": "Source and target must differ."},
        )

    async with get_db(request) as conn:
        async with conn.transaction():
            source = await conn.fetchrow(
                "SELECT code, is_system FROM streams WHERE code = $1",
                code,
            )
            if not source:
                raise HTTPException(
                    status_code=404,
                    detail={"error": "not_found", "detail": f"Source stream '{code}' not found."},
                )
            if source["is_system"]:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "validation_error",
                        "detail": "System streams cannot be merged away.",
                    },
                )
            target = await conn.fetchrow(
                "SELECT code, is_archived FROM streams WHERE code = $1",
                target_code,
            )
            if not target:
                raise HTTPException(
                    status_code=404,
                    detail={"error": "not_found", "detail": f"Target stream '{target_code}' not found."},
                )
            if target["is_archived"]:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "validation_error",
                        "detail": f"Target stream '{target_code}' is archived.",
                    },
                )

            affected = await conn.fetchval(
                """
                WITH moved AS (
                    UPDATE curricula
                       SET stream_code = $2
                     WHERE stream_code = $1
                    RETURNING 1
                )
                SELECT COUNT(*) FROM moved
                """,
                code,
                target_code,
            )
            await _recompute_count(conn, code)
            await _recompute_count(conn, target_code)
            await conn.execute(
                "UPDATE streams SET is_archived = true WHERE code = $1",
                code,
            )

    log.info(
        "stream_merged source=%s target=%s affected=%d admin=%s",
        code,
        target_code,
        affected,
        admin.get("admin_id"),
    )
    return StreamMergeResponse(affected_curricula=int(affected or 0), source_archived=True)


@router.delete("/admin/streams/{code}", status_code=204)
async def delete_stream(
    code: str,
    request: Request,
    admin: Annotated[dict, Depends(_require("content:publish"))],
) -> None:
    async with get_db(request) as conn:
        row = await conn.fetchrow(
            """
            SELECT code, is_system, is_archived, curricula_count
              FROM streams
             WHERE code = $1
            """,
            code,
        )
        if not row:
            raise HTTPException(
                status_code=404,
                detail={"error": "not_found", "detail": f"Stream '{code}' not found."},
            )
        if row["is_system"]:
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "conflict",
                    "detail": "System streams cannot be deleted. Archive instead.",
                },
            )
        if row["curricula_count"] > 0:
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "conflict",
                    "detail": (
                        f"Stream '{code}' still has {row['curricula_count']} curriculum(s). "
                        "Merge into another stream first."
                    ),
                },
            )
        if not row["is_archived"]:
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "conflict",
                    "detail": "Archive the stream before deleting.",
                },
            )
        await conn.execute("DELETE FROM streams WHERE code = $1", code)
    log.info("stream_deleted code=%s admin=%s", code, admin.get("admin_id"))
