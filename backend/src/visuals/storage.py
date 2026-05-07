"""
backend/src/visuals/storage.py — visual asset storage backend (issue #318 phase 2).

Mirrors the BackupStorageBackend pattern (Epic 15) but targets the visual
asset store, which is served from a public/CDN-fronted bucket in prod and
the local filesystem in dev.

Path convention:
    visuals/{curriculum_id}/{unit_id}/{section_id}/{slug}.{ext}

For schools, `curriculum_id` is the school-specific curriculum UUID; for
platform default content, it's the canonical ID like `default-2026-g11-science`.

The active backend is returned by get_visual_storage(). Selection is by env:
    VISUAL_STORAGE_BACKEND = "local"  (default in dev) | "s3"
    VISUAL_STORAGE_LOCAL_PATH = filesystem root (default: ${CONTENT_STORE_PATH}/visuals)
    VISUAL_STORAGE_S3_BUCKET, VISUAL_STORAGE_S3_PREFIX = S3 config
    VISUAL_STORAGE_PUBLIC_BASE_URL = base URL the renderer prepends to the path
                                     (e.g. "https://cdn.studybuddy.io/visuals" in prod;
                                      "/sample-visuals" in dev for backwards compat)
"""

from __future__ import annotations

import asyncio
import os
from abc import ABC, abstractmethod
from pathlib import Path

from src.utils.logger import get_logger

log = get_logger("visuals.storage")


# ── Abstract interface ────────────────────────────────────────────────────────


class VisualStorageBackend(ABC):
    """Abstract visual asset storage backend.

    All paths are relative keys within the visual store (e.g.
    "default-2026-g11-science/G11-PHYS-002/s2/xt-uam.svg"). Implementations
    resolve them against their configured root/bucket.
    """

    @abstractmethod
    async def upload(self, path: str, data: bytes, content_type: str | None = None) -> None:
        """Write data to the given path; create parent structure if needed."""

    @abstractmethod
    async def download(self, path: str) -> bytes:
        """Read and return the raw bytes at path. Raises FileNotFoundError if absent."""

    @abstractmethod
    async def delete(self, path: str) -> None:
        """Delete the object at path. No-op if not found."""

    @abstractmethod
    async def exists(self, path: str) -> bool:
        """Return True if an object exists at the given path."""

    @abstractmethod
    async def list_prefix(self, prefix: str) -> list[str]:
        """Return all keys/paths under the given prefix (recursive)."""

    @abstractmethod
    def public_url(self, path: str) -> str:
        """Return the URL the renderer should embed for this asset."""


# ── LocalVisualStorage ────────────────────────────────────────────────────────


class LocalVisualStorage(VisualStorageBackend):
    """Visual store backed by the local filesystem.

    All blocking I/O is dispatched to the thread pool via asyncio.to_thread so
    the FastAPI request loop is never blocked.
    """

    def __init__(self, root: str, public_base_url: str) -> None:
        self._root = Path(root)
        self._public_base_url = public_base_url.rstrip("/")

    def _full(self, path: str) -> Path:
        return self._root / path

    async def upload(self, path: str, data: bytes, content_type: str | None = None) -> None:
        p = self._full(path)

        def _write() -> None:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(data)

        await asyncio.to_thread(_write)
        log.debug(
            "visual_upload_local path=%s bytes=%d content_type=%s",
            path, len(data), content_type or "?",
        )

    async def download(self, path: str) -> bytes:
        p = self._full(path)
        try:
            return await asyncio.to_thread(p.read_bytes)
        except FileNotFoundError:
            raise FileNotFoundError(f"Visual asset not found: {path}")

    async def delete(self, path: str) -> None:
        p = self._full(path)

        def _rm() -> None:
            if p.exists():
                p.unlink()

        await asyncio.to_thread(_rm)

    async def exists(self, path: str) -> bool:
        return await asyncio.to_thread(self._full(path).is_file)

    async def list_prefix(self, prefix: str) -> list[str]:
        base = self._root / prefix

        def _ls() -> list[str]:
            if not base.exists():
                return []
            results: list[str] = []
            for f in base.rglob("*"):
                if f.is_file():
                    results.append(str(f.relative_to(self._root)))
            return sorted(results)

        return await asyncio.to_thread(_ls)

    def public_url(self, path: str) -> str:
        return f"{self._public_base_url}/{path.lstrip('/')}"


# ── S3VisualStorage ───────────────────────────────────────────────────────────


class S3VisualStorage(VisualStorageBackend):
    """Visual store backed by S3.

    Uploaded objects are public-read by default (visuals are not student PII);
    if a school marks a curriculum as private, the upload caller can pass
    content_type and tags to override that policy on a per-asset basis (future
    extension; v1 ships public-read only).
    """

    def __init__(self, bucket: str, prefix: str = "", public_base_url: str = "") -> None:
        try:
            import boto3  # type: ignore

            self._client = boto3.client("s3")
        except ImportError as e:
            raise RuntimeError(
                "S3VisualStorage requires boto3. Install via `pip install boto3` "
                "or set VISUAL_STORAGE_BACKEND=local for dev."
            ) from e
        self._bucket = bucket
        self._prefix = prefix.strip("/")
        self._public_base_url = public_base_url.rstrip("/")

    def _key(self, path: str) -> str:
        path = path.lstrip("/")
        return f"{self._prefix}/{path}" if self._prefix else path

    async def upload(self, path: str, data: bytes, content_type: str | None = None) -> None:
        key = self._key(path)

        def _put() -> None:
            extra: dict = {"ACL": "public-read"}
            if content_type:
                extra["ContentType"] = content_type
            self._client.put_object(Bucket=self._bucket, Key=key, Body=data, **extra)

        await asyncio.to_thread(_put)
        log.debug(
            "visual_upload_s3 bucket=%s key=%s bytes=%d content_type=%s",
            self._bucket, key, len(data), content_type or "?",
        )

    async def download(self, path: str) -> bytes:
        key = self._key(path)

        def _get() -> bytes:
            try:
                obj = self._client.get_object(Bucket=self._bucket, Key=key)
                return obj["Body"].read()
            except self._client.exceptions.NoSuchKey as e:
                raise FileNotFoundError(f"Visual asset not found: {path}") from e

        return await asyncio.to_thread(_get)

    async def delete(self, path: str) -> None:
        key = self._key(path)

        def _del() -> None:
            self._client.delete_object(Bucket=self._bucket, Key=key)

        await asyncio.to_thread(_del)

    async def exists(self, path: str) -> bool:
        key = self._key(path)

        def _head() -> bool:
            try:
                self._client.head_object(Bucket=self._bucket, Key=key)
                return True
            except self._client.exceptions.ClientError as e:
                if e.response.get("Error", {}).get("Code") in ("404", "NoSuchKey"):
                    return False
                raise

        return await asyncio.to_thread(_head)

    async def list_prefix(self, prefix: str) -> list[str]:
        base_key = self._key(prefix).rstrip("/")
        results: list[str] = []

        def _list() -> list[str]:
            paginator = self._client.get_paginator("list_objects_v2")
            keys: list[str] = []
            for page in paginator.paginate(Bucket=self._bucket, Prefix=base_key + "/"):
                for obj in page.get("Contents", []):
                    k = obj["Key"]
                    if self._prefix:
                        k = k[len(self._prefix) + 1:]  # strip "{prefix}/"
                    keys.append(k)
            return sorted(keys)

        results = await asyncio.to_thread(_list)
        return results

    def public_url(self, path: str) -> str:
        return f"{self._public_base_url}/{path.lstrip('/')}"


# ── Factory ───────────────────────────────────────────────────────────────────


_active_backend: VisualStorageBackend | None = None


def get_visual_storage() -> VisualStorageBackend:
    """Return the configured visual storage backend (singleton).

    Selection by env:
      VISUAL_STORAGE_BACKEND = "local" | "s3"  (default: "local")
    """
    global _active_backend
    if _active_backend is not None:
        return _active_backend

    backend = os.environ.get("VISUAL_STORAGE_BACKEND", "local").lower()
    if backend == "s3":
        bucket = os.environ["VISUAL_STORAGE_S3_BUCKET"]
        prefix = os.environ.get("VISUAL_STORAGE_S3_PREFIX", "visuals")
        public = os.environ.get(
            "VISUAL_STORAGE_PUBLIC_BASE_URL",
            f"https://{bucket}.s3.amazonaws.com/{prefix}",
        )
        _active_backend = S3VisualStorage(bucket=bucket, prefix=prefix, public_base_url=public)
        log.info("visual_storage backend=s3 bucket=%s prefix=%s", bucket, prefix)
    else:
        content_root = os.environ.get("CONTENT_STORE_PATH", "/data/content")
        root = os.environ.get("VISUAL_STORAGE_LOCAL_PATH", f"{content_root}/visuals")
        # In dev, default the public URL to /sample-visuals so existing exemplar
        # paths keep working until the asset migration lands. Override for prod.
        public = os.environ.get("VISUAL_STORAGE_PUBLIC_BASE_URL", "/sample-visuals")
        _active_backend = LocalVisualStorage(root=root, public_base_url=public)
        log.info("visual_storage backend=local root=%s public=%s", root, public)

    return _active_backend


def _reset_backend_for_tests() -> None:
    """Test-only — drop the singleton so per-test env can re-initialise."""
    global _active_backend
    _active_backend = None
