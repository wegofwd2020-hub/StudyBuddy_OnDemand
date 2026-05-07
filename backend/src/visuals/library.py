"""
backend/src/visuals/library.py — visual library data model + helpers (issue #321 / 319a).

The library is the platform-curated reservoir of reusable visual assets.
Each entry references a SVG/PNG/MP4 binary under
${CONTENT_STORE_PATH}/visual_library/{subject}/{slug}.{ext} and carries
metadata used by the pipeline resolver (#319c) to match tutorial
sections to library entries.

Public surface (this slice):
  - LibraryEntry  Pydantic model mirroring visual_library_entries
  - library_path(subject, slug, ext) -> str
  - LIBRARY_PREFIX  storage-relative root for library assets
  - SUBJECTS  closed enum of allowed subject values

Out of this slice (next sub-commit of 319a):
  - compute_embedding()  — needs pgvector + embedding column to be useful
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

# Closed enumeration of allowed subjects. Widen via PR + a separate
# migration if a new subject is added.
SUBJECTS = (
    "physics",
    "chemistry",
    "math",
    "biology",
    "geography",
    "history",
    "languages",
)

VisualKind = Literal["image", "image-grid", "animated-svg", "video"]
LicenseKind = Literal["platform-cc-by-sa", "platform-proprietary"]

LIBRARY_PREFIX = "visual_library"


class LibraryEntry(BaseModel):
    """One row of visual_library_entries."""

    entry_id: str
    kind: VisualKind
    subject: str
    topic_phrase: str
    keywords: list[str] = Field(default_factory=list)
    s3_path: str
    s3_metadata_path: str | None = None
    license: LicenseKind = "platform-cc-by-sa"
    source_unit: str | None = None
    archived_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    # `embedding` lands in a follow-up migration once pgvector is on the
    # dev DB. Pydantic side already declares the field so adding the
    # column is non-breaking.
    embedding: list[float] | None = None


def library_path(subject: str, slug: str, ext: str) -> str:
    """Compute the storage-relative path for a library asset.

    Example:
        library_path("physics", "kinematics-projectile-trajectory", "svg")
        -> "visual_library/physics/kinematics-projectile-trajectory.svg"

    Caller is responsible for validating subject (against SUBJECTS),
    slug (against the [a-z0-9-]+ rule), and ext (lowercase, dot-stripped).
    """
    return f"{LIBRARY_PREFIX}/{subject}/{slug}.{ext.lstrip('.')}"


def metadata_path(subject: str, slug: str) -> str:
    """Sidecar metadata.yaml path for a library asset."""
    return f"{LIBRARY_PREFIX}/{subject}/{slug}.metadata.yaml"
