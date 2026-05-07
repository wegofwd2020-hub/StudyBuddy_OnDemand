"""
backend/src/visuals/library.py — visual library data model + helpers (issue #321 / 319a).

The library is the platform-curated reservoir of reusable visual assets.
Each entry references a SVG/PNG/MP4 binary under
${CONTENT_STORE_PATH}/visual_library/{subject}/{slug}.{ext} and carries
metadata used by the pipeline resolver (#319c) to match tutorial
sections to library entries.

Public surface:
  - LibraryEntry              Pydantic model mirroring visual_library_entries
  - library_path()            storage-relative path for a library asset
  - metadata_path()           sidecar metadata.yaml path
  - compute_embedding()       async — 512-d voyage-3-lite cosine embedding
  - embedding_text_for_entry  canonical text shape for embedding
  - LIBRARY_PREFIX            storage-relative root for library assets
  - EMBEDDING_DIM             int (512 — matches voyage-3-lite)
  - SUBJECTS                  closed enum of allowed subject values
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


# ── Embedding helper ──────────────────────────────────────────────────────────
#
# Matches the Voyage convention from the help-retrieval pipeline (migration
# 0040 + backend/src/help/service.py): voyage-3-lite, 512 dims, cosine.

EMBEDDING_DIM = 512
_EMBEDDING_MODEL = "voyage-3-lite"


async def compute_embedding(text: str) -> list[float] | None:
    """Return a 512-d cosine embedding for `text`, or None if VOYAGE_API_KEY
    is not configured.

    Caller behaviour on None:
      - Promotion CI (#322): fail the run with a clear "VOYAGE_API_KEY
        required for library embeddings" message.
      - Resolver (#323): fall back to keyword/topic_phrase exact-match
        search; semantic ranking is unavailable.
    """
    from config import settings

    if not getattr(settings, "VOYAGE_API_KEY", None):
        return None

    import voyageai  # lazy — not required for non-library callers

    client = voyageai.AsyncClient(api_key=settings.VOYAGE_API_KEY)
    result = await client.embed(
        [text], model=_EMBEDDING_MODEL, input_type="document"
    )
    return result.embeddings[0]


def embedding_text_for_entry(entry: LibraryEntry) -> str:
    """Canonical text passed to compute_embedding() for an entry.

    Resolver in #323 will embed section content with the same shape so
    cosine distances are comparable: topic_phrase + " " + keywords.join(" ").
    """
    return f"{entry.topic_phrase} {' '.join(entry.keywords)}".strip()
