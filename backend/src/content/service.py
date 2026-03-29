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

from src.utils.logger import get_logger

log = get_logger("content.service")

# Redis key templates
_ENT_KEY = "ent:{student_id}"
_CSV_KEY = "csv:{curriculum_id}:{subject}"
_CONTENT_KEY = "content:{curriculum_id}:{unit_id}:{filename}"
_CUR_KEY = "cur:{student_id}"
_QUIZ_SET_KEY = "quiz_set:{student_id}:{unit_id}"

_ENT_TTL = 300    # 5 minutes
_CSV_TTL = 300    # 5 minutes
_CONTENT_TTL = 3600  # 1 hour


# ── Entitlement ───────────────────────────────────────────────────────────────

async def get_entitlement(
    student_id: str,
    pool: asyncpg.Pool,
    redis,
) -> dict:
    """
    Return {plan, lessons_accessed, valid_until} for a student.

    L2 cache: ent:{student_id} with TTL=300.
    On miss: queries student_entitlements table; inserts free-tier row if absent.
    """
    key = _ENT_KEY.format(student_id=student_id)
    cached = await redis.get(key)
    if cached:
        try:
            return json.loads(cached)
        except Exception:
            pass  # stale / corrupt cache — fall through to DB

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT plan, lessons_accessed, valid_until FROM student_entitlements WHERE student_id = $1",
            student_id,
        )

    if row is None:
        # Free-tier default
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
    key = _CSV_KEY.format(curriculum_id=curriculum_id, subject=subject)
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
    key = _CONTENT_KEY.format(
        curriculum_id=curriculum_id,
        unit_id=unit_id,
        filename=filename,
    )
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
) -> None:
    """
    Increment lessons_accessed for a student.
    Upserts the student_entitlements row if absent.
    Invalidates the ent:{student_id} Redis key.
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
    key = _ENT_KEY.format(student_id=student_id)
    await redis.delete(key)


# ── Curriculum resolver ───────────────────────────────────────────────────────

async def resolve_curriculum_id(
    student_id: str,
    grade: int,
    pool: asyncpg.Pool,
    redis,
    year: int = 2026,
) -> str:
    """
    Return the curriculum_id for a student.

    L2 cache: cur:{student_id} TTL=300.
    On miss: queries school enrollment or falls back to default-{year}-g{grade}.
    """
    key = _CUR_KEY.format(student_id=student_id)
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
    key = _QUIZ_SET_KEY.format(student_id=student_id, unit_id=unit_id)
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
        log.warning("cdn_invalidation_failed distribution=%s path=%s error=%s", distribution_id, path, exc)
