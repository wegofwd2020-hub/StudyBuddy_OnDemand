"""
Tests for backend/src/visuals/storage.py — issue #318 phase 2.

Covers LocalVisualStorage roundtrip + listing + delete, plus the factory's
env-based backend selection. S3VisualStorage is exercised only at boto3
import time (no live AWS calls in CI).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.visuals.storage import (
    LocalVisualStorage,
    _reset_backend_for_tests,
    get_visual_storage,
)

# ── LocalVisualStorage ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_local_upload_download_roundtrip(tmp_path: Path) -> None:
    s = LocalVisualStorage(root=str(tmp_path), public_base_url="/sample-visuals")
    payload = b"<svg/>"
    await s.upload("default-2026-g11-science/G11-PHYS-002/s2/xt-uam.svg", payload, content_type="image/svg+xml")
    got = await s.download("default-2026-g11-science/G11-PHYS-002/s2/xt-uam.svg")
    assert got == payload


@pytest.mark.asyncio
async def test_local_exists(tmp_path: Path) -> None:
    s = LocalVisualStorage(root=str(tmp_path), public_base_url="/sample-visuals")
    assert (await s.exists("nope.svg")) is False
    await s.upload("here.svg", b"<svg/>")
    assert (await s.exists("here.svg")) is True


@pytest.mark.asyncio
async def test_local_delete_idempotent(tmp_path: Path) -> None:
    s = LocalVisualStorage(root=str(tmp_path), public_base_url="/sample-visuals")
    # Delete absent path: should not raise
    await s.delete("nothing.svg")
    # Upload then delete: file gone
    await s.upload("here.svg", b"x")
    assert (await s.exists("here.svg")) is True
    await s.delete("here.svg")
    assert (await s.exists("here.svg")) is False


@pytest.mark.asyncio
async def test_local_list_prefix(tmp_path: Path) -> None:
    s = LocalVisualStorage(root=str(tmp_path), public_base_url="/sample-visuals")
    await s.upload("u/s1/a.svg", b"a")
    await s.upload("u/s1/b.svg", b"b")
    await s.upload("u/s2/c.svg", b"c")
    await s.upload("v/x.svg", b"x")

    keys = await s.list_prefix("u")
    assert keys == ["u/s1/a.svg", "u/s1/b.svg", "u/s2/c.svg"]

    keys2 = await s.list_prefix("u/s1")
    assert keys2 == ["u/s1/a.svg", "u/s1/b.svg"]

    keys3 = await s.list_prefix("absent_prefix")
    assert keys3 == []


@pytest.mark.asyncio
async def test_local_download_missing_raises(tmp_path: Path) -> None:
    s = LocalVisualStorage(root=str(tmp_path), public_base_url="/sample-visuals")
    with pytest.raises(FileNotFoundError):
        await s.download("missing.svg")


def test_local_public_url() -> None:
    s = LocalVisualStorage(root="/tmp/x", public_base_url="/sample-visuals")
    assert s.public_url("a/b/c.svg") == "/sample-visuals/a/b/c.svg"
    assert s.public_url("/leading/slash.svg") == "/sample-visuals/leading/slash.svg"

    s2 = LocalVisualStorage(root="/tmp/x", public_base_url="https://cdn.example.com/visuals/")
    assert s2.public_url("a.svg") == "https://cdn.example.com/visuals/a.svg"


# ── Factory ───────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_factory_local_default(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """get_visual_storage() returns LocalVisualStorage by default."""
    _reset_backend_for_tests()
    monkeypatch.delenv("VISUAL_STORAGE_BACKEND", raising=False)
    monkeypatch.setenv("VISUAL_STORAGE_LOCAL_PATH", str(tmp_path))
    monkeypatch.setenv("VISUAL_STORAGE_PUBLIC_BASE_URL", "/sample-visuals")

    backend = get_visual_storage()
    assert isinstance(backend, LocalVisualStorage)
    # Singleton: second call returns the same instance
    assert get_visual_storage() is backend
    _reset_backend_for_tests()


@pytest.mark.asyncio
async def test_factory_explicit_local(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _reset_backend_for_tests()
    monkeypatch.setenv("VISUAL_STORAGE_BACKEND", "local")
    monkeypatch.setenv("VISUAL_STORAGE_LOCAL_PATH", str(tmp_path))
    monkeypatch.setenv("VISUAL_STORAGE_PUBLIC_BASE_URL", "/sample-visuals")

    backend = get_visual_storage()
    assert isinstance(backend, LocalVisualStorage)
    _reset_backend_for_tests()


@pytest.mark.asyncio
async def test_factory_singleton_isolation(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """_reset_backend_for_tests() actually re-initialises the singleton."""
    _reset_backend_for_tests()
    monkeypatch.setenv("VISUAL_STORAGE_LOCAL_PATH", str(tmp_path / "first"))
    first = get_visual_storage()
    _reset_backend_for_tests()

    monkeypatch.setenv("VISUAL_STORAGE_LOCAL_PATH", str(tmp_path / "second"))
    second = get_visual_storage()
    assert first is not second
    _reset_backend_for_tests()
