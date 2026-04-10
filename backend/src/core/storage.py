"""
backend/src/core/storage.py

StorageBackend abstraction for the content store.

All content reads and writes go through a StorageBackend instance so the
backend API can be deployed on multiple hosts without sharing a local
filesystem.

Implementations:
  LocalStorage  — reads/writes from CONTENT_STORE_PATH on the local disk.
                  Use for single-host dev/staging deployments.
  S3Storage     — reads/writes from an S3 bucket (boto3 via thread executor).
                  Use for production multi-host deployments.

The active backend is created in main.py lifespan and stored on
app.state.storage.  Route handlers access it via the get_storage dependency.

Path convention:
  All paths passed to the backend are RELATIVE to the content root
  (i.e. "curricula/{curriculum_id}/{unit_id}/lesson_en.json").
  The backend prepends its root/prefix internally.  Callers never
  construct absolute filesystem paths or S3 keys directly.
"""

from __future__ import annotations

import asyncio
import json
import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from fastapi import Request

from src.utils.logger import get_logger

log = get_logger("storage")


# ── Abstract interface ────────────────────────────────────────────────────────


class StorageBackend(ABC):
    """Abstract content store backend.

    All methods accept RELATIVE paths (no leading slash).
    Implementations resolve them against their configured root.
    """

    @abstractmethod
    async def read(self, path: str) -> bytes:
        """Read a file and return its raw bytes.  Raises FileNotFoundError if absent."""

    @abstractmethod
    async def read_json(self, path: str) -> Any:
        """Read a JSON file and return the decoded object.  Raises FileNotFoundError if absent."""

    @abstractmethod
    async def write(self, path: str, data: bytes) -> None:
        """Write data to path, creating parent directories as needed."""

    @abstractmethod
    async def exists(self, path: str) -> bool:
        """Return True if the path exists as a file (not a directory)."""

    @abstractmethod
    async def listdir(self, path: str) -> list[str]:
        """Return the immediate children of a directory.  Returns [] if not found."""

    @abstractmethod
    async def delete_tree(self, path: str) -> None:
        """Recursively delete path and all its contents.  No-op if not found."""

    @abstractmethod
    async def total_bytes(self, path: str) -> int:
        """Return the total size in bytes of all files under path (recursive)."""

    @abstractmethod
    def audio_url(self, path: str, ttl_seconds: int = 3600) -> str:
        """Return a URL for the audio file at path.

        LocalStorage returns a /static/… fallback path.
        S3Storage returns a pre-signed URL (presign is CPU-only, no network).
        """


# ── LocalStorage ──────────────────────────────────────────────────────────────


class LocalStorage(StorageBackend):
    """Content store backed by the local filesystem.

    Blocking I/O is dispatched to the default thread pool executor via
    asyncio.to_thread so the event loop is not blocked.
    """

    def __init__(self, root: str) -> None:
        self._root = Path(root)

    def _full(self, path: str) -> Path:
        return self._root / path

    async def read(self, path: str) -> bytes:
        p = self._full(path)
        return await asyncio.to_thread(p.read_bytes)

    async def read_json(self, path: str) -> Any:
        raw = await self.read(path)
        return json.loads(raw)

    async def write(self, path: str, data: bytes) -> None:
        p = self._full(path)

        def _write() -> None:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(data)

        await asyncio.to_thread(_write)

    async def exists(self, path: str) -> bool:
        return await asyncio.to_thread(self._full(path).is_file)

    async def listdir(self, path: str) -> list[str]:
        def _ls() -> list[str]:
            p = self._full(path)
            if not p.is_dir():
                return []
            return [e.name for e in p.iterdir()]

        return await asyncio.to_thread(_ls)

    async def delete_tree(self, path: str) -> None:
        def _rm() -> None:
            p = self._full(path)
            if p.exists():
                shutil.rmtree(p)

        await asyncio.to_thread(_rm)

    async def total_bytes(self, path: str) -> int:
        def _size() -> int:
            p = self._full(path)
            if not p.is_dir():
                return 0
            return sum(f.stat().st_size for f in p.rglob("*") if f.is_file())

        return await asyncio.to_thread(_size)

    def audio_url(self, path: str, ttl_seconds: int = 3600) -> str:
        # In local dev there is no S3; serve via /static/content/…
        return f"/static/content/{path}"


# ── S3Storage ─────────────────────────────────────────────────────────────────


class S3Storage(StorageBackend):
    """Content store backed by an AWS S3 bucket.

    boto3 is synchronous; all SDK calls are dispatched to the default thread
    pool executor via asyncio.to_thread to keep the event loop free.

    Requires boto3 to be installed and AWS credentials configured via
    environment variables or instance profile.
    """

    def __init__(self, bucket: str, prefix: str = "") -> None:
        self._bucket = bucket
        self._prefix = prefix.rstrip("/")
        try:
            import boto3  # type: ignore
            self._s3 = boto3.client("s3")
        except ImportError:
            raise RuntimeError("boto3 is required for S3Storage — run: pip install boto3")

    def _key(self, path: str) -> str:
        return f"{self._prefix}/{path}" if self._prefix else path

    async def read(self, path: str) -> bytes:
        key = self._key(path)

        def _get() -> bytes:
            obj = self._s3.get_object(Bucket=self._bucket, Key=key)
            return obj["Body"].read()

        try:
            return await asyncio.to_thread(_get)
        except self._s3.exceptions.NoSuchKey:
            raise FileNotFoundError(f"s3://{self._bucket}/{key}")

    async def read_json(self, path: str) -> Any:
        raw = await self.read(path)
        return json.loads(raw)

    async def write(self, path: str, data: bytes) -> None:
        key = self._key(path)
        await asyncio.to_thread(
            self._s3.put_object, Bucket=self._bucket, Key=key, Body=data
        )

    async def exists(self, path: str) -> bool:
        from botocore.exceptions import ClientError  # type: ignore

        key = self._key(path)

        def _head() -> bool:
            try:
                self._s3.head_object(Bucket=self._bucket, Key=key)
                return True
            except ClientError as exc:
                if exc.response["Error"]["Code"] == "404":
                    return False
                raise

        return await asyncio.to_thread(_head)

    async def listdir(self, path: str) -> list[str]:
        prefix = self._key(path) + "/"

        def _ls() -> list[str]:
            resp = self._s3.list_objects_v2(
                Bucket=self._bucket, Prefix=prefix, Delimiter="/"
            )
            entries: set[str] = set()
            # Immediate subdirectories (common prefixes)
            for cp in resp.get("CommonPrefixes", []):
                name = cp["Prefix"].removeprefix(prefix).rstrip("/")
                if name:
                    entries.add(name)
            # Files at this level
            for obj in resp.get("Contents", []):
                name = obj["Key"].removeprefix(prefix)
                if name and "/" not in name:
                    entries.add(name)
            return sorted(entries)

        return await asyncio.to_thread(_ls)

    async def delete_tree(self, path: str) -> None:
        prefix = self._key(path) + "/"

        def _del() -> None:
            paginator = self._s3.get_paginator("list_objects_v2")
            for page in paginator.paginate(Bucket=self._bucket, Prefix=prefix):
                objects = [{"Key": obj["Key"]} for obj in page.get("Contents", [])]
                if objects:
                    self._s3.delete_objects(
                        Bucket=self._bucket,
                        Delete={"Objects": objects, "Quiet": True},
                    )

        await asyncio.to_thread(_del)

    async def total_bytes(self, path: str) -> int:
        prefix = self._key(path) + "/"

        def _size() -> int:
            paginator = self._s3.get_paginator("list_objects_v2")
            total = 0
            for page in paginator.paginate(Bucket=self._bucket, Prefix=prefix):
                for obj in page.get("Contents", []):
                    total += obj["Size"]
            return total

        return await asyncio.to_thread(_size)

    def audio_url(self, path: str, ttl_seconds: int = 3600) -> str:
        # generate_presigned_url is pure computation (HMAC signing) — no network call.
        return self._s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": self._bucket, "Key": self._key(path)},
            ExpiresIn=ttl_seconds,
        )


# ── FastAPI dependency ────────────────────────────────────────────────────────


def get_storage(request: Request) -> StorageBackend:
    """FastAPI dependency — returns the StorageBackend from app.state."""
    return request.app.state.storage
