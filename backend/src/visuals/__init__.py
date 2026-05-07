"""
backend/src/visuals — visual asset storage and serving.

Public surface (issue #318 phase 2):
  - VisualStorageBackend (ABC)
  - LocalVisualStorage   — filesystem-backed; dev / test
  - S3VisualStorage      — boto3-backed; production
  - get_visual_storage() — factory that returns the configured backend

Eventually also: the upload / put / delete endpoints registered into the
backend router. See ../content/router.py for serving (the renderer reads
asset URLs from the tutorial JSON; storage is opaque to it).
"""

from src.visuals.storage import (
    LocalVisualStorage,
    S3VisualStorage,
    VisualStorageBackend,
    get_visual_storage,
)

__all__ = [
    "LocalVisualStorage",
    "S3VisualStorage",
    "VisualStorageBackend",
    "get_visual_storage",
]
