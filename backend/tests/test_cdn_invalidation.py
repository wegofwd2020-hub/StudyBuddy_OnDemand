"""
tests/test_cdn_invalidation.py

Unit tests for src/core/cdn.py — CloudFront invalidation helpers.

All boto3 calls are mocked; no real AWS credentials or network calls are made.
Tests also cover the integration with purge_grace_expired to verify that CDN
invalidation is invoked after content files are deleted.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.cdn import invalidate_curriculum, invalidate_paths, invalidate_unit


# ── Fixtures ──────────────────────────────────────────────────────────────────


def _make_boto3_mock(invalidation_id: str = "ABCDEFGH12345") -> MagicMock:
    """Return a mock boto3 module whose cloudfront client returns a valid response."""
    client_mock = MagicMock()
    client_mock.create_invalidation.return_value = {
        "Invalidation": {"Id": invalidation_id, "Status": "InProgress"},
        "Location": f"https://cloudfront.amazonaws.com/2020-05-31/distribution/DIST/invalidation/{invalidation_id}",
    }
    boto3_mock = MagicMock()
    boto3_mock.client.return_value = client_mock
    return boto3_mock


# ── invalidate_paths ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_invalidate_paths_noop_when_no_distribution():
    """Returns False and makes no boto3 calls when distribution_id is None."""
    with patch.dict("sys.modules", {"boto3": MagicMock()}):
        result = await invalidate_paths(["/curricula/abc/*"], distribution_id=None)

    assert result is False


@pytest.mark.asyncio
async def test_invalidate_paths_noop_when_empty_distribution_string():
    """Returns False for empty string distribution_id."""
    result = await invalidate_paths(["/curricula/abc/*"], distribution_id="")
    assert result is False


@pytest.mark.asyncio
async def test_invalidate_paths_noop_when_empty_paths():
    """Returns False without calling boto3 when paths list is empty."""
    boto3_mock = _make_boto3_mock()
    with patch.dict("sys.modules", {"boto3": boto3_mock}):
        result = await invalidate_paths([], distribution_id="EDIST1234")

    assert result is False
    boto3_mock.client.assert_not_called()


@pytest.mark.asyncio
async def test_invalidate_paths_calls_cloudfront_with_correct_args():
    """Calls CloudFront create_invalidation with the expected paths and quantity."""
    boto3_mock = _make_boto3_mock()
    paths = ["/curricula/abc-123/*", "/curricula/def-456/*"]

    with patch.dict("sys.modules", {"boto3": boto3_mock}):
        result = await invalidate_paths(
            paths,
            distribution_id="EDIST1234",
            caller_reference="test-ref-001",
        )

    assert result is True
    boto3_mock.client.assert_called_once_with("cloudfront")
    client = boto3_mock.client.return_value
    client.create_invalidation.assert_called_once()
    call_kwargs = client.create_invalidation.call_args[1]
    assert call_kwargs["DistributionId"] == "EDIST1234"
    batch = call_kwargs["InvalidationBatch"]
    assert batch["Paths"]["Quantity"] == 2
    assert set(batch["Paths"]["Items"]) == set(paths)
    assert batch["CallerReference"] == "test-ref-001"


@pytest.mark.asyncio
async def test_invalidate_paths_uses_monotonic_ns_as_default_reference():
    """Uses a non-empty caller reference when none is supplied."""
    boto3_mock = _make_boto3_mock()

    with patch.dict("sys.modules", {"boto3": boto3_mock}):
        result = await invalidate_paths(["/curricula/xyz/*"], distribution_id="EDIST1234")

    assert result is True
    call_kwargs = boto3_mock.client.return_value.create_invalidation.call_args[1]
    assert call_kwargs["InvalidationBatch"]["CallerReference"]  # not empty


@pytest.mark.asyncio
async def test_invalidate_paths_returns_false_when_boto3_not_installed():
    """Handles ImportError gracefully — returns False instead of crashing."""
    import sys

    original = sys.modules.get("boto3")
    sys.modules["boto3"] = None  # type: ignore  # simulate missing package

    try:
        result = await invalidate_paths(["/curricula/abc/*"], distribution_id="EDIST1234")
    finally:
        if original is None:
            sys.modules.pop("boto3", None)
        else:
            sys.modules["boto3"] = original

    assert result is False


@pytest.mark.asyncio
async def test_invalidate_paths_propagates_cloudfront_errors():
    """Re-raises boto3 errors so the caller can decide how to handle them."""
    boto3_mock = MagicMock()
    client_mock = MagicMock()
    client_mock.create_invalidation.side_effect = Exception("CloudFront API error")
    boto3_mock.client.return_value = client_mock

    with patch.dict("sys.modules", {"boto3": boto3_mock}):
        with pytest.raises(Exception, match="CloudFront API error"):
            await invalidate_paths(["/curricula/abc/*"], distribution_id="EDIST1234")


# ── invalidate_curriculum ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_invalidate_curriculum_forms_wildcard_path():
    """invalidate_curriculum sends /curricula/{id}/* as the invalidation path."""
    boto3_mock = _make_boto3_mock()
    curriculum_id = "default-2026-g8"

    with patch.dict("sys.modules", {"boto3": boto3_mock}):
        result = await invalidate_curriculum(curriculum_id, distribution_id="EDIST1234")

    assert result is True
    call_kwargs = boto3_mock.client.return_value.create_invalidation.call_args[1]
    items = call_kwargs["InvalidationBatch"]["Paths"]["Items"]
    assert items == [f"/curricula/{curriculum_id}/*"]


@pytest.mark.asyncio
async def test_invalidate_curriculum_noop_without_distribution():
    """No-op when distribution_id is not configured."""
    result = await invalidate_curriculum("default-2026-g8", distribution_id=None)
    assert result is False


@pytest.mark.asyncio
async def test_invalidate_curriculum_uses_stable_caller_reference():
    """Uses a deterministic caller_reference based on curriculum_id (idempotent retries)."""
    boto3_mock = _make_boto3_mock()
    curriculum_id = "school-uuid-g8"

    with patch.dict("sys.modules", {"boto3": boto3_mock}):
        await invalidate_curriculum(curriculum_id, distribution_id="EDIST1234")

    call_kwargs = boto3_mock.client.return_value.create_invalidation.call_args[1]
    ref = call_kwargs["InvalidationBatch"]["CallerReference"]
    assert curriculum_id in ref  # reference encodes the curriculum for traceability


# ── invalidate_unit ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_invalidate_unit_forms_correct_path():
    """invalidate_unit sends /curricula/{cid}/{uid}/* as the invalidation path."""
    boto3_mock = _make_boto3_mock()
    curriculum_id = "default-2026-g8"
    unit_id = "G8-MATH-001"

    with patch.dict("sys.modules", {"boto3": boto3_mock}):
        result = await invalidate_unit(curriculum_id, unit_id, distribution_id="EDIST1234")

    assert result is True
    call_kwargs = boto3_mock.client.return_value.create_invalidation.call_args[1]
    items = call_kwargs["InvalidationBatch"]["Paths"]["Items"]
    assert items == [f"/curricula/{curriculum_id}/{unit_id}/*"]


@pytest.mark.asyncio
async def test_invalidate_unit_noop_without_distribution():
    result = await invalidate_unit("default-2026-g8", "G8-MATH-001", distribution_id=None)
    assert result is False


# ── Integration: purge_grace_expired calls CDN invalidation ───────────────────


@pytest.mark.asyncio
async def test_purge_grace_expired_triggers_cdn_invalidation(tmp_path: Path):
    """
    purge_grace_expired calls invalidate_curriculum for each purged curriculum
    when distribution_id is provided.
    """
    from src.core.storage import LocalStorage
    from src.school.retention_service import purge_grace_expired

    curriculum_id = f"school-{uuid.uuid4().hex[:8]}-g8"

    # Create fake content files so delete_tree has something to remove.
    content_dir = tmp_path / "curricula" / curriculum_id
    content_dir.mkdir(parents=True)
    (content_dir / "lesson_en.json").write_text("{}")

    storage = LocalStorage(root=str(tmp_path))

    # Build a mock asyncpg connection that returns one row from the WITH..RETURNING query.
    conn_mock = AsyncMock()
    conn_mock.fetch.return_value = [
        {
            "curriculum_id": curriculum_id,
            "grade": 8,
            "school_id": str(uuid.UUID("a1000000-0000-0000-0000-000000000001")),
            "expires_at": datetime.now(UTC) - timedelta(days=200),
            "grace_until": datetime.now(UTC) - timedelta(days=5),
            "contact_email": "admin@school.example.com",
        }
    ]

    boto3_mock = _make_boto3_mock()

    with patch.dict("sys.modules", {"boto3": boto3_mock}):
        results = await purge_grace_expired(
            conn_mock,
            storage,
            distribution_id="EDIST1234",
        )

    assert len(results) == 1
    assert results[0]["curriculum_id"] == curriculum_id

    # CDN invalidation was submitted for the purged curriculum.
    boto3_mock.client.assert_called_once_with("cloudfront")
    call_kwargs = boto3_mock.client.return_value.create_invalidation.call_args[1]
    items = call_kwargs["InvalidationBatch"]["Paths"]["Items"]
    assert items == [f"/curricula/{curriculum_id}/*"]


@pytest.mark.asyncio
async def test_purge_grace_expired_cdn_failure_does_not_abort_purge(tmp_path: Path):
    """
    A CloudFront API error must not prevent the purge from completing —
    the DB state is already set to 'purged' and files are deleted.
    """
    from src.core.storage import LocalStorage
    from src.school.retention_service import purge_grace_expired

    curriculum_id = f"school-{uuid.uuid4().hex[:8]}-g9"

    content_dir = tmp_path / "curricula" / curriculum_id
    content_dir.mkdir(parents=True)
    (content_dir / "lesson_en.json").write_text("{}")

    storage = LocalStorage(root=str(tmp_path))

    conn_mock = AsyncMock()
    conn_mock.fetch.return_value = [
        {
            "curriculum_id": curriculum_id,
            "grade": 9,
            "school_id": str(uuid.UUID("a1000000-0000-0000-0000-000000000002")),
            "expires_at": datetime.now(UTC) - timedelta(days=200),
            "grace_until": datetime.now(UTC) - timedelta(days=5),
            "contact_email": "admin@other.example.com",
        }
    ]

    # boto3 raises — simulates transient CloudFront API failure.
    boto3_mock = MagicMock()
    client_mock = MagicMock()
    client_mock.create_invalidation.side_effect = Exception("CloudFront 503")
    boto3_mock.client.return_value = client_mock

    with patch.dict("sys.modules", {"boto3": boto3_mock}):
        # Must not raise — CDN failure is logged as a warning, not re-raised.
        results = await purge_grace_expired(
            conn_mock,
            storage,
            distribution_id="EDIST1234",
        )

    assert len(results) == 1
    assert results[0]["curriculum_id"] == curriculum_id


@pytest.mark.asyncio
async def test_purge_grace_expired_skips_cdn_when_no_distribution(tmp_path: Path):
    """
    When distribution_id is None (local dev / LocalStorage only), purge runs
    cleanly with no boto3 calls at all.
    """
    from src.core.storage import LocalStorage
    from src.school.retention_service import purge_grace_expired

    curriculum_id = f"school-{uuid.uuid4().hex[:8]}-g10"

    content_dir = tmp_path / "curricula" / curriculum_id
    content_dir.mkdir(parents=True)
    (content_dir / "lesson_en.json").write_text("{}")

    storage = LocalStorage(root=str(tmp_path))

    conn_mock = AsyncMock()
    conn_mock.fetch.return_value = [
        {
            "curriculum_id": curriculum_id,
            "grade": 10,
            "school_id": str(uuid.UUID("a1000000-0000-0000-0000-000000000003")),
            "expires_at": datetime.now(UTC) - timedelta(days=200),
            "grace_until": datetime.now(UTC) - timedelta(days=5),
            "contact_email": "admin@third.example.com",
        }
    ]

    boto3_mock = _make_boto3_mock()

    with patch.dict("sys.modules", {"boto3": boto3_mock}):
        results = await purge_grace_expired(
            conn_mock,
            storage,
            distribution_id=None,
        )

    assert len(results) == 1
    # boto3 client was never instantiated — no CloudFront call.
    boto3_mock.client.assert_not_called()
