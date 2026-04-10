"""
backend/src/content/service.py

Core business logic for the Content Service.

All functions are async and use the asyncpg pool + aioredis passed in as
arguments — no global state, easy to unit-test with mocks.

Cache read order (per CLAUDE.md / studybuddy-docs/BACKEND_ARCHITECTURE.md):
  L1 (in-process TTLCache) → L2 (Redis) → DB / filesystem

This module handles L2 (Redis) + DB/filesystem. The router sits above and
handles L1 where applicable.
"""

from __future__ import annotations

import json
import os

import asyncpg
from config import settings

import uuid as _uuid

from src.core.cache_keys import content_key, csv_key, cur_key, ent_key, quiz_set_key, school_ent_key
from src.utils.logger import get_logger

log = get_logger("content.service")

_ENT_TTL = 300  # 5 minutes
_CSV_TTL = 300  # 5 minutes
_CONTENT_TTL = 3600  # 1 hour


# ── School subscription helper ────────────────────────────────────────────────


async def _get_school_sub(school_id: str, pool: asyncpg.Pool, redis) -> dict | None:
    """
    Return the active school subscription as {plan, status, valid_until} or None.

    Uses school:{school_id}:ent (TTL=300 s) as L2 cache.

    Called by get_entitlement() instead of the old get_school_entitlement_for_student()
    so that the school_id (already present in the JWT) is used directly — no extra
    SELECT from the students table.
    """
    cache_key = school_ent_key(school_id)
    cached = await redis.get(cache_key)
    if cached:
        try:
            data = json.loads(cached)
            return data if data.get("active") else None
        except Exception:
            pass

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT plan, status, current_period_end, grace_period_end
            FROM school_subscriptions
            WHERE school_id = $1
            """,
            _uuid.UUID(school_id),
        )

    active = row is not None and row["status"] in ("active", "trialing", "past_due")

    if active:
        if row["status"] == "past_due" and row["grace_period_end"]:
            valid_until = row["grace_period_end"].isoformat()
        elif row["current_period_end"]:
            valid_until = row["current_period_end"].isoformat()
        else:
            valid_until = None
        blob = {
            "active": True,
            "plan": row["plan"],
            "status": row["status"],
            "valid_until": valid_until,
        }
    else:
        blob = {"active": False, "plan": None, "status": None, "valid_until": None}

    await redis.set(cache_key, json.dumps(blob), ex=_ENT_TTL)
    return blob if active else None


# ── Entitlement ───────────────────────────────────────────────────────────────


async def get_entitlement(
    student_id: str,
    pool: asyncpg.Pool,
    redis,
    school_id: str | None = None,
) -> dict:
    """
    Return {plan, lessons_accessed, valid_until} for a student.

    Decision order (ADR-001 Decision 2 — school_subscriptions is source of truth):

      1. L2 cache: school:{school_id}:ent:{student_id}  (or ent:{student_id})  TTL=300
      2. If school_id present → query school_subscriptions via _get_school_sub()
           active/trialing/past_due  → derive plan from subscription
                                        lessons_accessed from student_entitlements (usage only)
           absent / cancelled        → treat as free
      3. Unaffiliated / free tier → query student_entitlements directly

    school_id is taken from the JWT payload, so no extra students-table lookup is needed.
    """
    key = ent_key(student_id, school_id)
    cached = await redis.get(key)
    if cached:
        try:
            return json.loads(cached)
        except Exception:
            pass  # stale / corrupt — fall through to DB

    # ── School subscription path ──────────────────────────────────────────────
    if school_id:
        sub = await _get_school_sub(school_id, pool, redis)
        if sub is not None:
            # lessons_accessed is still tracked in student_entitlements (usage counter).
            async with pool.acquire() as conn:
                ent_row = await conn.fetchrow(
                    "SELECT lessons_accessed FROM student_entitlements WHERE student_id = $1",
                    student_id,
                )
            entitlement = {
                "plan": sub["plan"],
                "lessons_accessed": ent_row["lessons_accessed"] if ent_row else 0,
                "valid_until": sub["valid_until"],
            }
            await redis.set(key, json.dumps(entitlement), ex=_ENT_TTL)
            return entitlement
        # School exists but subscription inactive → fall through to free tier

    # ── Free / unaffiliated path ──────────────────────────────────────────────
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT plan, lessons_accessed, valid_until FROM student_entitlements WHERE student_id = $1",
            student_id,
        )

    if row is None:
        entitlement = {"plan": "free", "lessons_accessed": 0, "valid_until": None}
    else:
        entitlement = {
            "plan": row["plan"],
            "lessons_accessed": row["lessons_accessed"],
            "valid_until": row["valid_until"].isoformat() if row["valid_until"] else None,
        }

    await redis.set(key, json.dumps(entitlement), ex=_ENT_TTL)
    return entitlement


# ── Content publish check ─────────────────────────────────────────────────────


async def check_content_published(
    curriculum_id: str,
    subject: str,
    pool: asyncpg.Pool,
    redis,
) -> bool:
    """
    Return True if the subject's content is published for the given curriculum.

    L2 cache: csv:{curriculum_id}:{subject} TTL=300.
    """
    key = csv_key(curriculum_id, subject)
    cached = await redis.get(key)
    if cached is not None:
        return cached == b"1" or cached == "1"

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT 1 FROM content_subject_versions
            WHERE curriculum_id = $1 AND subject = $2 AND status = 'published'
            LIMIT 1
            """,
            curriculum_id,
            subject,
        )

    published = row is not None
    await redis.set(key, "1" if published else "0", ex=_CSV_TTL)
    return published


# ── Content file serving ──────────────────────────────────────────────────────


async def get_content_file(
    curriculum_id: str,
    unit_id: str,
    filename: str,
    redis,
) -> dict:
    """
    Read a content JSON file from the Content Store.

    L2 cache: content:{curriculum_id}:{unit_id}:{filename} TTL=3600.

    Raises FileNotFoundError if the file doesn't exist.
    """
    key = content_key(curriculum_id, unit_id, filename)
    cached = await redis.get(key)
    if cached:
        try:
            return json.loads(cached)
        except Exception:
            pass  # corrupt cache entry — fall through

    file_path = os.path.join(
        settings.CONTENT_STORE_PATH,
        "curricula",
        curriculum_id,
        unit_id,
        filename,
    )

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Content file not found: {file_path}")

    with open(file_path, encoding="utf-8") as f:
        data = json.load(f)

    await redis.set(key, json.dumps(data), ex=_CONTENT_TTL)
    return data


# ── Lessons-accessed counter ──────────────────────────────────────────────────


async def increment_lessons_accessed(
    student_id: str,
    pool: asyncpg.Pool,
    redis,
    school_id: str | None = None,
) -> None:
    """
    Increment lessons_accessed for a student.
    Upserts the student_entitlements row if absent.
    Invalidates the correct namespaced ent key (ADR-001 Decision 3).
    """
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO student_entitlements (student_id, plan, lessons_accessed)
            VALUES ($1, 'free', 1)
            ON CONFLICT (student_id) DO UPDATE
                SET lessons_accessed = student_entitlements.lessons_accessed + 1,
                    updated_at = NOW()
            """,
            student_id,
        )

    # Invalidate L2 cache
    await redis.delete(ent_key(student_id, school_id))


# ── Curriculum resolver ───────────────────────────────────────────────────────


async def resolve_curriculum_id(
    student_id: str,
    grade: int,
    pool: asyncpg.Pool,
    redis,
    year: int = 2026,
    school_id: str | None = None,
) -> str:
    """
    Return the curriculum_id for a student.

    L2 cache: school:{school_id}:cur:{student_id} (or cur:{student_id} if unaffiliated).
    On miss: queries school enrollment or falls back to default-{year}-g{grade}.
    """
    key = cur_key(student_id, school_id)
    cached = await redis.get(key)
    if cached:
        try:
            return cached.decode() if isinstance(cached, bytes) else cached
        except Exception:
            pass

    # Check school enrollment for a custom curriculum
    curriculum_id: str | None = None
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT c.curriculum_id
            FROM students s
            JOIN schools sc ON s.school_id = sc.school_id
            JOIN curricula c ON c.school_id = sc.school_id AND c.grade = s.grade
            WHERE s.student_id = $1
            LIMIT 1
            """,
            student_id,
        )
        if row:
            curriculum_id = row["curriculum_id"]

    if not curriculum_id:
        curriculum_id = f"default-{year}-g{grade}"

    await redis.set(key, curriculum_id, ex=_CSV_TTL)
    return curriculum_id


# ── Content block check ───────────────────────────────────────────────────────


async def check_content_block(
    curriculum_id: str,
    unit_id: str,
    content_type: str,
    pool: asyncpg.Pool,
) -> bool:
    """
    Return True if the content item is actively blocked by an admin.
    A block is active when unblocked_at IS NULL.
    """
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT 1 FROM content_blocks
            WHERE curriculum_id = $1
              AND unit_id = $2
              AND content_type = $3
              AND unblocked_at IS NULL
            LIMIT 1
            """,
            curriculum_id,
            unit_id,
            content_type,
        )
    return row is not None


# ── Quiz rotation ─────────────────────────────────────────────────────────────


async def get_next_quiz_set(
    student_id: str,
    unit_id: str,
    redis,
) -> int:
    """
    Return the next quiz set number (1, 2, or 3) using round-robin rotation.
    Tracks state in Redis key quiz_set:{student_id}:{unit_id}.
    """
    key = quiz_set_key(student_id, unit_id)
    current = await redis.get(key)

    if current is None:
        next_set = 1
    else:
        try:
            last = int(current)
        except (ValueError, TypeError):
            last = 0
        next_set = (last % 3) + 1

    await redis.set(key, str(next_set), ex=86400 * 7)  # 7-day TTL
    return next_set


# ── Subject from unit ID ──────────────────────────────────────────────────────


async def get_unit_subject(
    unit_id: str,
    curriculum_id: str,
    pool: asyncpg.Pool,
) -> str | None:
    """
    Return the subject for a unit by looking it up in curriculum_units.
    Returns None if the unit is not found.
    """
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT subject FROM curriculum_units WHERE unit_id = $1 AND curriculum_id = $2",
            unit_id,
            curriculum_id,
        )
    return row["subject"] if row else None


async def invalidate_cdn_path(curriculum_id: str, unit_id: str | None = None) -> None:
    """
    Invalidate CloudFront CDN paths after a content version bump.

    Per CLAUDE.md non-negotiable rule #7: CDN invalidation must accompany
    Redis cache invalidation on content bumps.

    Pattern invalidated:
      - unit_id provided:  curricula/{curriculum_id}/{unit_id}/*
      - unit_id omitted:   curricula/{curriculum_id}/*

    Silently skips if CLOUDFRONT_DISTRIBUTION_ID is not set (local dev).
    """
    distribution_id = settings.CLOUDFRONT_DISTRIBUTION_ID
    if not distribution_id:
        log.debug("cloudfront_distribution_id_absent_skipping_invalidation")
        return

    if unit_id:
        path = f"/curricula/{curriculum_id}/{unit_id}/*"
    else:
        path = f"/curricula/{curriculum_id}/*"

    try:
        import time

        import boto3

        cf = boto3.client("cloudfront")
        cf.create_invalidation(
            DistributionId=distribution_id,
            InvalidationBatch={
                "Paths": {"Quantity": 1, "Items": [path]},
                "CallerReference": str(int(time.time())),
            },
        )
        log.info("cdn_invalidation_created distribution=%s path=%s", distribution_id, path)
    except Exception as exc:
        log.warning(
            "cdn_invalidation_failed distribution=%s path=%s error=%s", distribution_id, path, exc
        )
