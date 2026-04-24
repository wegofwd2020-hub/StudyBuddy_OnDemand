"""
tests/test_content_service_coverage.py

Targeted coverage of src/content/service.py — PR #9 of #261.

Focuses on the pure helpers that don't need the full FastAPI stack:
  - _get_school_sub         — L47-85 (cache hit/miss, all subscription-status branches)
  - get_entitlement         — L116-117 corrupt-cache, L146 free-tier fallback
  - check_content_published — L172-190 cache miss + DB query
  - get_content_file        — L210-222 cache miss + storage read
  - increment_lessons_accessed — L239-252 upsert + cache invalidation
  - resolve_curriculum_id   — L275-278 cache hit (bytes + str)
  - check_content_block     — L317-331 row present/absent
  - get_next_quiz_set       — L354-355 invalid cached value fallback + rotation

Each test exercises the real service function with AsyncMock pool + redis +
storage — no live DB, no HTTP layer.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest


def _make_pool(conn: AsyncMock) -> MagicMock:
    pool = MagicMock()
    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=conn)
    cm.__aexit__ = AsyncMock(return_value=None)
    pool.acquire = MagicMock(return_value=cm)
    return pool


# ── _get_school_sub ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_school_sub_cache_hit_active():
    from src.content.service import _get_school_sub

    school_id = "d3000000-0000-0000-0000-000000000099"
    redis = AsyncMock()
    redis.get.return_value = json.dumps(
        {"active": True, "plan": "basic", "status": "active", "valid_until": "2027-01-01"}
    ).encode()

    conn = AsyncMock()
    pool = _make_pool(conn)

    result = await _get_school_sub(school_id, pool, redis)
    assert result == {
        "active": True,
        "plan": "basic",
        "status": "active",
        "valid_until": "2027-01-01",
    }
    conn.fetchrow.assert_not_called()


@pytest.mark.asyncio
async def test_get_school_sub_cache_hit_inactive_returns_none():
    from src.content.service import _get_school_sub

    redis = AsyncMock()
    redis.get.return_value = json.dumps(
        {"active": False, "plan": None, "status": None, "valid_until": None}
    ).encode()

    conn = AsyncMock()
    pool = _make_pool(conn)

    result = await _get_school_sub(
        "d3000000-0000-0000-0000-000000000099", pool, redis
    )
    assert result is None


@pytest.mark.asyncio
async def test_get_school_sub_cache_corrupt_falls_through_to_db():
    from src.content.service import _get_school_sub

    redis = AsyncMock()
    redis.get.return_value = b"not valid json"

    conn = AsyncMock()
    conn.fetchrow.return_value = None  # no subscription row → inactive
    pool = _make_pool(conn)

    result = await _get_school_sub(
        "d3000000-0000-0000-0000-000000000099", pool, redis
    )
    # Corrupt cache → falls through → DB says no subscription → returns None.
    assert result is None
    conn.fetchrow.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_school_sub_past_due_uses_grace_period_end():
    from src.content.service import _get_school_sub

    redis = AsyncMock()
    redis.get.return_value = None

    grace_end = datetime.now(UTC) + timedelta(days=3)
    conn = AsyncMock()
    conn.fetchrow.return_value = {
        "plan": "basic",
        "status": "past_due",
        "current_period_end": None,
        "grace_period_end": grace_end,
    }
    pool = _make_pool(conn)

    result = await _get_school_sub(
        "d3000000-0000-0000-0000-000000000099", pool, redis
    )
    assert result is not None
    assert result["status"] == "past_due"
    assert result["valid_until"] == grace_end.isoformat()


@pytest.mark.asyncio
async def test_get_school_sub_active_uses_current_period_end():
    from src.content.service import _get_school_sub

    redis = AsyncMock()
    redis.get.return_value = None

    period_end = datetime.now(UTC) + timedelta(days=30)
    conn = AsyncMock()
    conn.fetchrow.return_value = {
        "plan": "premium",
        "status": "trialing",
        "current_period_end": period_end,
        "grace_period_end": None,
    }
    pool = _make_pool(conn)

    result = await _get_school_sub(
        "d3000000-0000-0000-0000-000000000099", pool, redis
    )
    assert result["plan"] == "premium"
    assert result["status"] == "trialing"
    assert result["valid_until"] == period_end.isoformat()


@pytest.mark.asyncio
async def test_get_school_sub_no_row_returns_none():
    from src.content.service import _get_school_sub

    redis = AsyncMock()
    redis.get.return_value = None

    conn = AsyncMock()
    conn.fetchrow.return_value = None
    pool = _make_pool(conn)

    result = await _get_school_sub(
        "d3000000-0000-0000-0000-000000000099", pool, redis
    )
    assert result is None
    # Still writes an inactive blob to the cache for future requests.
    redis.set.assert_awaited_once()


# ── get_entitlement ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_entitlement_corrupt_cache_falls_through():
    """Corrupt cache entry is ignored; DB is queried."""
    from src.content.service import get_entitlement

    redis = AsyncMock()
    redis.get.return_value = b"not json"

    conn = AsyncMock()
    conn.fetchrow.return_value = None  # no entitlement row → free tier
    pool = _make_pool(conn)

    result = await get_entitlement("d1000000-0000-0000-0000-000000000099", pool, redis)
    assert result == {"plan": "free", "lessons_accessed": 0, "valid_until": None}


@pytest.mark.asyncio
async def test_get_entitlement_school_active_subscription_derives_plan():
    """school_id present + active sub → plan comes from sub, usage from
    student_entitlements (L120-135)."""
    from src.content.service import get_entitlement

    redis = AsyncMock()
    # Cache miss on ent key (first get); cache hit on school_ent key (second).
    redis.get.side_effect = [
        None,  # ent:{sid} or school:{school_id}:ent:{sid}
        json.dumps(
            {"active": True, "plan": "basic", "status": "active", "valid_until": "2027-01-01"}
        ).encode(),  # school_ent cache hit → _get_school_sub short-circuits
    ]

    conn = AsyncMock()
    conn.fetchrow.return_value = {"lessons_accessed": 42}
    pool = _make_pool(conn)

    result = await get_entitlement(
        "d1000000-0000-0000-0000-000000000099",
        pool,
        redis,
        school_id="d3000000-0000-0000-0000-000000000099",
    )
    assert result == {
        "plan": "basic",
        "lessons_accessed": 42,
        "valid_until": "2027-01-01",
    }


@pytest.mark.asyncio
async def test_get_entitlement_existing_entitlement_row():
    """Unaffiliated student with an entitlement row → returns its values (L148)."""
    from src.content.service import get_entitlement

    redis = AsyncMock()
    redis.get.return_value = None

    valid_until = datetime.now(UTC) + timedelta(days=30)
    conn = AsyncMock()
    conn.fetchrow.return_value = {
        "plan": "premium",
        "lessons_accessed": 5,
        "valid_until": valid_until,
    }
    pool = _make_pool(conn)

    result = await get_entitlement(
        "d1000000-0000-0000-0000-000000000099", pool, redis, school_id=None
    )
    assert result["plan"] == "premium"
    assert result["lessons_accessed"] == 5
    assert result["valid_until"] == valid_until.isoformat()


@pytest.mark.asyncio
async def test_get_entitlement_free_tier_when_no_row_and_no_school():
    """Unaffiliated student with no entitlement row → free tier."""
    from src.content.service import get_entitlement

    redis = AsyncMock()
    redis.get.return_value = None

    conn = AsyncMock()
    conn.fetchrow.return_value = None
    pool = _make_pool(conn)

    result = await get_entitlement(
        "d1000000-0000-0000-0000-000000000099", pool, redis, school_id=None
    )
    assert result["plan"] == "free"
    assert result["lessons_accessed"] == 0


# ── check_content_published ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_check_content_published_cache_miss_db_hit():
    from src.content.service import check_content_published

    redis = AsyncMock()
    redis.get.return_value = None  # cache miss

    conn = AsyncMock()
    conn.fetchrow.return_value = {"?column?": 1}  # row present
    pool = _make_pool(conn)

    result = await check_content_published("cur-1", "Math", pool, redis)
    assert result is True
    # Cache set with "1".
    redis.set.assert_awaited_once()
    assert redis.set.call_args.args[1] == "1"


@pytest.mark.asyncio
async def test_check_content_published_cache_miss_db_miss():
    from src.content.service import check_content_published

    redis = AsyncMock()
    redis.get.return_value = None

    conn = AsyncMock()
    conn.fetchrow.return_value = None
    pool = _make_pool(conn)

    result = await check_content_published("cur-1", "Math", pool, redis)
    assert result is False
    assert redis.set.call_args.args[1] == "0"


# ── get_content_file ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_content_file_cache_miss_reads_storage():
    from src.content.service import get_content_file

    redis = AsyncMock()
    redis.get.return_value = None

    storage = MagicMock()
    storage.read_json = AsyncMock(return_value={"sections": [], "meta": "x"})

    result = await get_content_file(
        "cur-1", "U1", "lesson_en.json", redis=redis, storage=storage
    )
    assert result == {"sections": [], "meta": "x"}
    storage.read_json.assert_awaited_once_with("curricula/cur-1/U1/lesson_en.json")
    redis.set.assert_awaited_once()  # cached


@pytest.mark.asyncio
async def test_get_content_file_cache_hit_skips_storage():
    from src.content.service import get_content_file

    redis = AsyncMock()
    redis.get.return_value = json.dumps({"from": "cache"}).encode()

    storage = MagicMock()
    storage.read_json = AsyncMock()

    result = await get_content_file(
        "cur-1", "U1", "lesson_en.json", redis=redis, storage=storage
    )
    assert result == {"from": "cache"}
    storage.read_json.assert_not_called()


# ── increment_lessons_accessed ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_increment_lessons_accessed_upserts_and_invalidates_cache():
    from src.content.service import increment_lessons_accessed

    conn = AsyncMock()
    pool = _make_pool(conn)
    redis = AsyncMock()

    await increment_lessons_accessed(
        "d1000000-0000-0000-0000-000000000099", pool, redis, school_id=None
    )

    # Upsert INSERT ... ON CONFLICT ran.
    conn.execute.assert_awaited_once()
    assert "INSERT INTO student_entitlements" in conn.execute.call_args.args[0]

    # Cache invalidated.
    redis.delete.assert_awaited_once()


# ── resolve_curriculum_id cache hit ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_resolve_curriculum_id_cache_hit_bytes():
    """cached value comes back as bytes (real redis) → decoded to str."""
    from src.content.service import resolve_curriculum_id

    redis = AsyncMock()
    redis.get.return_value = b"cur-from-cache"

    conn = AsyncMock()
    pool = _make_pool(conn)

    result = await resolve_curriculum_id(
        "d1000000-0000-0000-0000-000000000099", 8, pool, redis
    )
    assert result == "cur-from-cache"
    conn.fetchrow.assert_not_called()


@pytest.mark.asyncio
async def test_resolve_curriculum_id_cache_hit_str():
    """cached value already a str (fakeredis / decode_responses=True) → pass through."""
    from src.content.service import resolve_curriculum_id

    redis = AsyncMock()
    redis.get.return_value = "cur-from-cache-str"

    conn = AsyncMock()
    pool = _make_pool(conn)

    result = await resolve_curriculum_id(
        "d1000000-0000-0000-0000-000000000099", 8, pool, redis
    )
    assert result == "cur-from-cache-str"


# ── resolve_curriculum_id cache-miss paths ────────────────────────────────────


@pytest.mark.asyncio
async def test_resolve_curriculum_id_cache_miss_school_curriculum():
    """Cache miss, student enrolled in a school with a custom curriculum."""
    from src.content.service import resolve_curriculum_id

    redis = AsyncMock()
    redis.get.return_value = None

    conn = AsyncMock()
    conn.fetchrow.return_value = {"curriculum_id": "school-cur-abc"}
    pool = _make_pool(conn)

    result = await resolve_curriculum_id(
        "d1000000-0000-0000-0000-000000000099", 8, pool, redis
    )
    assert result == "school-cur-abc"
    # Cache populated for next time.
    redis.set.assert_awaited_once()


@pytest.mark.asyncio
async def test_resolve_curriculum_id_cache_miss_falls_back_to_default():
    """Unaffiliated student / no custom curriculum → default-{year}-g{grade}."""
    from src.content.service import resolve_curriculum_id

    redis = AsyncMock()
    redis.get.return_value = None

    conn = AsyncMock()
    conn.fetchrow.return_value = None
    pool = _make_pool(conn)

    result = await resolve_curriculum_id(
        "d1000000-0000-0000-0000-000000000099", 9, pool, redis, year=2026
    )
    assert result == "default-2026-g9"


# ── check_content_block ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_check_content_block_returns_true_when_blocked():
    from src.content.service import check_content_block

    conn = AsyncMock()
    conn.fetchrow.return_value = {"?column?": 1}
    pool = _make_pool(conn)

    result = await check_content_block("cur-1", "U1", "lesson", pool)
    assert result is True


@pytest.mark.asyncio
async def test_check_content_block_returns_false_when_not_blocked():
    from src.content.service import check_content_block

    conn = AsyncMock()
    conn.fetchrow.return_value = None
    pool = _make_pool(conn)

    result = await check_content_block("cur-1", "U1", "lesson", pool)
    assert result is False


# ── get_next_quiz_set ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_next_quiz_set_starts_at_1_when_no_prior():
    from src.content.service import get_next_quiz_set

    redis = AsyncMock()
    redis.get.return_value = None

    result = await get_next_quiz_set("stu-1", "U1", redis)
    assert result == 1


@pytest.mark.asyncio
async def test_get_next_quiz_set_rotates_1_to_2_to_3_to_1():
    from src.content.service import get_next_quiz_set

    redis = AsyncMock()

    redis.get.return_value = b"1"
    assert await get_next_quiz_set("stu-1", "U1", redis) == 2

    redis.get.return_value = b"2"
    assert await get_next_quiz_set("stu-1", "U1", redis) == 3

    redis.get.return_value = b"3"
    assert await get_next_quiz_set("stu-1", "U1", redis) == 1  # wrap


@pytest.mark.asyncio
async def test_get_next_quiz_set_invalid_cached_value_falls_back_to_1():
    """Garbage in the cache key → defaults to 0 → next is 1."""
    from src.content.service import get_next_quiz_set

    redis = AsyncMock()
    redis.get.return_value = b"not-a-number"

    result = await get_next_quiz_set("stu-1", "U1", redis)
    assert result == 1  # (0 % 3) + 1
