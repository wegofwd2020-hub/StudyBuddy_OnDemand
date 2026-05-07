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
