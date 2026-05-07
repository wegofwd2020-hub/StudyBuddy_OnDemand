"""
backend/src/visuals/router.py — visual asset upload / list / delete endpoints.

Issue #318 phase 2b. Operates directly on the VisualStorageBackend; integration
with the unit_content_overrides schema (Phase D draft → review → approve) is
deferred to a follow-up slice.

Auth: school_admin or teacher within the school. Path includes school_id for
RLS scoping.

Path convention for assets:
    visuals/{school_id}/{curriculum_id}/{unit_id}/{section_id}/{slug}.{ext}

The renderer reads `public_url(path)` from VisualStorageBackend and embeds
that URL in the visual block items.
"""

from __future__ import annotations

import os
import re
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from pydantic import BaseModel

from src.auth.dependencies import get_current_teacher
from src.utils.logger import get_logger
from src.visuals.storage import get_visual_storage

log = get_logger("visuals.router")

router = APIRouter(prefix="/schools/{school_id}/visuals", tags=["visuals"])

# Accepted MIME types — keep tight; broaden via env if needed
ALLOWED_MIME = {
    "image/svg+xml": ".svg",
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
    "video/mp4": ".mp4",
    "video/webm": ".webm",
}
MAX_BYTES = int(os.environ.get("VISUAL_UPLOAD_MAX_BYTES", str(20 * 1024 * 1024)))  # 20 MB

_SLUG_RE = re.compile(r"[^a-z0-9._-]+")


def _slugify(name: str) -> str:
    base, ext = os.path.splitext(name.lower())
    base = _SLUG_RE.sub("-", base).strip("-") or "asset"
    ext = _SLUG_RE.sub("", ext) or ""
    return f"{base}{ext}"[:80]


# ── Schemas ──────────────────────────────────────────────────────────────────


class UploadResponse(BaseModel):
    path: str
    url: str
    bytes: int
    content_type: str


class AssetEntry(BaseModel):
    path: str
    url: str


class ListResponse(BaseModel):
    assets: list[AssetEntry]


# ── Endpoints ────────────────────────────────────────────────────────────────


@router.post("/upload", response_model=UploadResponse)
async def upload_visual(
    school_id: str,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
    file: UploadFile = File(...),
    curriculum_id: str = Form(...),
    unit_id: str = Form(...),
    section_id: str = Form(...),
) -> UploadResponse:
    """Upload a visual asset for a school's curriculum unit / section.

    Returns the storage path + the public URL the renderer can embed.
    The caller (typically the school portal UI) is responsible for then
    issuing the PUT that adds this URL into the section's visuals[] array.
    """
    if teacher["school_id"] != school_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    content_type = (file.content_type or "").lower()
    if content_type not in ALLOWED_MIME:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported MIME type: {content_type}. "
            f"Allowed: {sorted(ALLOWED_MIME.keys())}",
        )

    body = await file.read()
    if len(body) > MAX_BYTES:
        raise HTTPException(status_code=413, detail=f"File exceeds {MAX_BYTES} bytes")
    if len(body) == 0:
        raise HTTPException(status_code=400, detail="Empty upload")

    storage = get_visual_storage()
    ext = ALLOWED_MIME[content_type]
    slug = _slugify(file.filename or "asset")
    if not slug.endswith(ext):
        slug = f"{slug}-{uuid.uuid4().hex[:8]}{ext}"
    else:
        slug = f"{os.path.splitext(slug)[0]}-{uuid.uuid4().hex[:8]}{ext}"

    path = f"{school_id}/{curriculum_id}/{unit_id}/{section_id}/{slug}"
    await storage.upload(path, body, content_type=content_type)
    url = storage.public_url(path)

    log.info(
        "visual_uploaded school_id=%s teacher_id=%s path=%s bytes=%d content_type=%s",
        school_id, teacher.get("teacher_id"), path, len(body), content_type,
    )
    return UploadResponse(path=path, url=url, bytes=len(body), content_type=content_type)


@router.get("", response_model=ListResponse)
async def list_visuals(
    school_id: str,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
    curriculum_id: str | None = None,
    unit_id: str | None = None,
) -> ListResponse:
    """List uploaded assets for the school, optionally filtered by curriculum / unit."""
    if teacher["school_id"] != school_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    prefix_parts = [school_id]
    if curriculum_id:
        prefix_parts.append(curriculum_id)
        if unit_id:
            prefix_parts.append(unit_id)
    prefix = "/".join(prefix_parts)

    storage = get_visual_storage()
    paths = await storage.list_prefix(prefix)
    return ListResponse(assets=[
        AssetEntry(path=p, url=storage.public_url(p)) for p in paths
    ])


@router.delete("/{asset_path:path}", status_code=204)
async def delete_visual(
    school_id: str,
    asset_path: str,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
) -> None:
    """Delete a previously-uploaded asset.

    asset_path is the full storage path returned from upload (NOT the public
    URL). The school_id prefix must match the authenticated school.
    """
    if teacher["school_id"] != school_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    if not asset_path.startswith(f"{school_id}/"):
        raise HTTPException(status_code=403, detail="Forbidden — asset belongs to another school")

    storage = get_visual_storage()
    if not await storage.exists(asset_path):
        raise HTTPException(status_code=404, detail="Asset not found")

    await storage.delete(asset_path)
    log.info(
        "visual_deleted school_id=%s teacher_id=%s path=%s",
        school_id, teacher.get("teacher_id"), asset_path,
    )


# ── PUT /schools/{school_id}/content/.../section/{section_id}/visuals ────────
#
# Issue #318 phase 2c — override-workflow integration.
# Replaces the visuals[] array on one section of a unit's tutorial in a
# school's draft override. Creates a new draft override row (append-only
# versioning per Phase D), source_override_id pointing at the previous
# version. The school's review queue picks up the new draft.
#
# Body (JSON): { adoption_id, unit_id, section_id, visuals: [VisualBlock] }
# Returns:     { override_id, version_number, review_status }


import json as _json  # local alias avoids reformatter dropping the import


class _VisualItemIn(BaseModel):
    src: str
    alt: str
    caption: str | None = None
    poster: str | None = None
    duration: str | None = None


class _VisualBlockIn(BaseModel):
    kind: str
    heading: str | None = None
    items: list[_VisualItemIn]


class SectionVisualsUpdate(BaseModel):
    adoption_id: str
    unit_id: str
    section_id: str
    visuals: list[_VisualBlockIn]


class SectionVisualsUpdateResponse(BaseModel):
    override_id: str
    version_number: int
    review_status: str


@router.put("/sections", response_model=SectionVisualsUpdateResponse)
async def put_section_visuals(
    school_id: str,
    payload: SectionVisualsUpdate,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
) -> SectionVisualsUpdateResponse:
    """Replace the visuals[] array on one section of a tutorial draft override.

    Pre-conditions:
      - The school owns the adoption (RLS scoping + adoption.school_id check).
      - The unit's tutorial has been imported (`POST /schools/{school_id}/library/{adoption_id}/units/{unit_id}/import`).
      - The current latest version is editable (status in draft / pending_review / rejected).
        Once `approved`, edits create a new draft cycle.

    Effect:
      - Reads the latest tutorial override row for this (forked_curriculum, unit, lang='en').
      - Mutates body["sections"][section_id_match]["visuals"] = payload.visuals.
      - Inserts a new override row with version_number+1 and status='draft'.
      - The serving path keeps showing the previous active version until the
        school admin transitions the new draft through pending_review → approved.
    """
    if teacher["school_id"] != school_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    from src.core.db import get_db  # local import — formatter strips top-level

    async with get_db(request) as conn:
        adoption = await conn.fetchrow(
            """
            SELECT forked_curriculum_id, status
            FROM school_adopted_curricula
            WHERE school_id = $1 AND adoption_id = $2
            """,
            school_id, payload.adoption_id,
        )
        if not adoption:
            raise HTTPException(status_code=404, detail="Adoption not found")
        if adoption["status"] != "active":
            raise HTTPException(status_code=403, detail="Adoption is not active")
        forked = adoption["forked_curriculum_id"]
        if forked is None:
            raise HTTPException(
                status_code=409,
                detail="Unit content has not been imported yet. POST to "
                       f"/schools/{school_id}/library/{payload.adoption_id}/units/"
                       f"{payload.unit_id}/import first.",
            )

        latest = await conn.fetchrow(
            """
            SELECT override_id, body, version_number, review_status, bundle_id
            FROM unit_content_overrides
            WHERE curriculum_id = $1
              AND unit_id = $2
              AND lang = 'en'
              AND content_type = 'tutorial'
            ORDER BY version_number DESC
            LIMIT 1
            """,
            forked, payload.unit_id,
        )
        if not latest:
            raise HTTPException(
                status_code=409,
                detail="No tutorial override found for this unit. Import it first.",
            )

        # Body is JSONB; asyncpg returns it as a JSON-encoded string.
        body = latest["body"]
        if isinstance(body, str):
            body = _json.loads(body)
        elif isinstance(body, (bytes, bytearray)):
            body = _json.loads(body.decode("utf-8"))

        sections = body.get("sections", [])
        target = next(
            (s for s in sections if s.get("section_id") == payload.section_id),
            None,
        )
        if target is None:
            raise HTTPException(
                status_code=404,
                detail=f"Section {payload.section_id!r} not found in tutorial",
            )

        # Replace visuals[]
        target["visuals"] = [block.model_dump() for block in payload.visuals]
        new_version = latest["version_number"] + 1

        row = await conn.fetchrow(
            """
            INSERT INTO unit_content_overrides
                (school_id, curriculum_id, unit_id, lang, content_type,
                 bundle_id, content_source, source_override_id, body,
                 last_edited_by, review_status, version_number)
            VALUES ($1, $2, $3, 'en', 'tutorial',
                    $4, 'teacher_authored', $5, $6,
                    $7, 'draft', $8)
            RETURNING override_id, review_status, version_number
            """,
            school_id,
            forked,
            payload.unit_id,
            latest["bundle_id"],
            latest["override_id"],
            _json.dumps(body),
            teacher["teacher_id"],
            new_version,
        )

    log.info(
        "visual_section_updated school=%s unit=%s section=%s version=%s blocks=%d",
        school_id, payload.unit_id, payload.section_id,
        row["version_number"], len(payload.visuals),
    )
    return SectionVisualsUpdateResponse(
        override_id=str(row["override_id"]),
        version_number=row["version_number"],
        review_status=row["review_status"],
    )
