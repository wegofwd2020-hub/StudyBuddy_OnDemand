"""
backend/src/backup/storage.py

BackupStorageBackend abstraction for curriculum backup archives.

Separate from the main content StorageBackend so backup storage can live on a
different bucket/path from serving content — important for disaster recovery
scenarios where the content store itself may be compromised.

Implementations:
  LocalBackupStorage  — stores backups on the local filesystem under BACKUP_LOCAL_PATH.
  S3BackupStorage     — stores backups in a dedicated S3 bucket.

The active backend is returned by get_backup_storage() and used exclusively
inside Celery tasks (never in the FastAPI request path).
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from pathlib import Path

from src.utils.logger import get_logger

log = get_logger("backup.storage")


# ── Abstract interface ────────────────────────────────────────────────────────


class BackupStorageBackend(ABC):
    """Abstract backup storage backend.

    All paths are relative keys within the backup store (e.g.
    "{school_id}/{backup_id}/manifest.json").  Implementations resolve them
    against their configured root/bucket.
    """

    @abstractmethod
    async def upload(self, path: str, data: bytes) -> None:
        """Write data to the given path, creating any necessary parent structure."""

    @abstractmethod
    async def download(self, path: str) -> bytes:
        """Read and return the raw bytes at path.  Raises FileNotFoundError if absent."""

    @abstractmethod
    async def delete(self, path: str) -> None:
        """Delete the object at path.  No-op if not found."""

    @abstractmethod
    async def exists(self, path: str) -> bool:
        """Return True if an object exists at the given path."""

    @abstractmethod
    async def list_prefix(self, prefix: str) -> list[str]:
        """Return all keys/paths under the given prefix (recursive)."""


# ── LocalBackupStorage ────────────────────────────────────────────────────────


class LocalBackupStorage(BackupStorageBackend):
    """Backup store backed by the local filesystem.

    All blocking I/O is dispatched to the thread pool via asyncio.to_thread so
    the Celery task's event loop is never blocked.
    """

    def __init__(self, root: str) -> None:
        self._root = Path(root)

    def _full(self, path: str) -> Path:
        return self._root / path

    async def upload(self, path: str, data: bytes) -> None:
        p = self._full(path)

        def _write() -> None:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(data)

        await asyncio.to_thread(_write)
        log.debug("backup_upload_local", path=path, bytes=len(data))

    async def download(self, path: str) -> bytes:
        p = self._full(path)
        try:
            return await asyncio.to_thread(p.read_bytes)
        except FileNotFoundError:
            raise FileNotFoundError(f"Backup object not found: {path}")

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
                    # Return path relative to self._root so callers can use them
                    # as keys for download/delete.
                    results.append(str(f.relative_to(self._root)))
            return sorted(results)

        return await asyncio.to_thread(_ls)


# ── S3BackupStorage ───────────────────────────────────────────────────────────


class S3BackupStorage(BackupStorageBackend):
    """Backup store backed by an AWS S3 bucket.

    boto3 is synchronous; all SDK calls are dispatched to the thread pool via
    asyncio.to_thread to keep the async loop free.
    """

    def __init__(self, bucket: str, prefix: str = "") -> None:
        self._bucket = bucket
        self._prefix = prefix.rstrip("/")
        try:
            import boto3  # type: ignore

            self._s3 = boto3.client("s3")
        except ImportError:
            raise RuntimeError("boto3 is required for S3BackupStorage — run: pip install boto3")

    def _key(self, path: str) -> str:
        return f"{self._prefix}/{path}" if self._prefix else path

    async def upload(self, path: str, data: bytes) -> None:
        key = self._key(path)
        await asyncio.to_thread(
            self._s3.put_object, Bucket=self._bucket, Key=key, Body=data
        )
        log.debug("backup_upload_s3", key=key, bytes=len(data))

    async def download(self, path: str) -> bytes:
        from botocore.exceptions import ClientError  # type: ignore

        key = self._key(path)

        def _get() -> bytes:
            try:
                obj = self._s3.get_object(Bucket=self._bucket, Key=key)
                return obj["Body"].read()
            except ClientError as exc:
                if exc.response["Error"]["Code"] in ("NoSuchKey", "404"):
                    raise FileNotFoundError(f"s3://{self._bucket}/{key}")
                raise

        return await asyncio.to_thread(_get)

    async def delete(self, path: str) -> None:
        key = self._key(path)
        await asyncio.to_thread(
            self._s3.delete_object, Bucket=self._bucket, Key=key
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

    async def list_prefix(self, prefix: str) -> list[str]:
        key_prefix = self._key(prefix)
        if not key_prefix.endswith("/"):
            key_prefix += "/"

        def _ls() -> list[str]:
            paginator = self._s3.get_paginator("list_objects_v2")
            results: list[str] = []
            for page in paginator.paginate(Bucket=self._bucket, Prefix=key_prefix):
                for obj in page.get("Contents", []):
                    # Strip the bucket-level prefix so callers get back the
                    # same relative path they would pass to upload/download.
                    rel = obj["Key"]
                    if self._prefix:
                        rel = rel.removeprefix(self._prefix + "/")
                    results.append(rel)
            return sorted(results)

        return await asyncio.to_thread(_ls)


# ── Factory ───────────────────────────────────────────────────────────────────


def get_backup_storage() -> BackupStorageBackend:
    """Return the configured BackupStorageBackend instance.

    Called inside Celery tasks — not in the FastAPI request path.
    """
    from config import settings

    if settings.BACKUP_STORAGE_BACKEND == "s3":
        if not settings.BACKUP_S3_BUCKET:
            raise RuntimeError(
                "BACKUP_S3_BUCKET must be set when BACKUP_STORAGE_BACKEND=s3"
            )
        return S3BackupStorage(bucket=settings.BACKUP_S3_BUCKET)
    return LocalBackupStorage(root=settings.BACKUP_LOCAL_PATH)
