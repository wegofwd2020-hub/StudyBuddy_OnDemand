"""
backend/src/admin/service.py

Admin business logic for Phase 7.

Covers:
  - Content review queue queries
  - Review session (open / annotate / rate / approve / reject)
  - Publish / rollback with Redis + CDN invalidation
  - Content block / unblock
  - Student feedback listing
  - Subscription analytics (MRR, churn)
  - Struggle analytics (mean attempts, pass rate per unit)
  - Pipeline status summary
  - Dictionary lookup (Datamuse + optional Merriam-Webster)
"""

from __future__ import annotations

import json
import os
import uuid

import asyncpg
import httpx
from config import settings as _settings

from src.utils.logger import get_logger

log = get_logger("admin")

# Stripe plan monthly prices (USD) used for MRR estimation
_MONTHLY_PRICE_USD = 9.99
_ANNUAL_MONTHLY_USD = 7.99  # annual / 12


# ── Review queue ──────────────────────────────────────────────────────────────


async def list_review_queue(
    conn: asyncpg.Connection,
    status: str | None = None,
    subject: str | None = None,
    curriculum_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict:
    """Return content_subject_versions rows matching the filters."""
    filters = ["archived_at IS NULL"]
    params: list = []

    if status:
        # "pending" is the canonical pre-review status; also match legacy pipeline values
        if status == "pending":
            filters.append("status IN ('pending', 'ready_for_review', 'needs_review')")
        else:
            params.append(status)
            filters.append(f"status = ${len(params)}")
    if subject:
        params.append(subject)
        filters.append(f"subject = ${len(params)}")
    if curriculum_id:
        params.append(curriculum_id)
        filters.append(f"curriculum_id = ${len(params)}")

    where = " AND ".join(filters)

    rows = await conn.fetch(
        f"""
        SELECT version_id::text, curriculum_id, subject, subject_name, version_number, status,
               alex_warnings_count, generated_at, published_at
        FROM content_subject_versions
        WHERE {where}
        ORDER BY generated_at DESC
        LIMIT ${len(params) + 1} OFFSET ${len(params) + 2}
        """,
        *params,
        limit,
        offset,
    )
    total = await conn.fetchval(
        f"SELECT COUNT(*) FROM content_subject_versions WHERE {where}",
        *params,
    )

    # Build a per-curriculum unit listing (one os.listdir per curriculum_id)
    content_store = getattr(_settings, "CONTENT_STORE_PATH", "/data/content")
    _curriculum_units: dict[str, set[str]] = {}
    for r in rows:
        cid = r["curriculum_id"]
        if cid not in _curriculum_units:
            cdir = os.path.join(content_store, "curricula", cid)
            try:
                _curriculum_units[cid] = set(os.listdir(cdir))
            except OSError:
                _curriculum_units[cid] = set()

    items = []
    for r in rows:
        d = dict(r)
        subject_prefix = r["subject"] + "-"
        units_on_disk = _curriculum_units.get(r["curriculum_id"], set())
        d["has_content"] = any(u.startswith(subject_prefix) for u in units_on_disk)
        items.append(d)

    return {"items": items, "total": total or 0}


# ── Review detail ─────────────────────────────────────────────────────────────


async def get_review_detail(
    conn: asyncpg.Connection,
    version_id: str,
) -> dict | None:
    """Return full detail for a single content version including units, review history, and annotations."""
    version = await conn.fetchrow(
        """
        SELECT version_id::text, curriculum_id, subject, subject_name, version_number, status,
               alex_warnings_count, generated_at, published_at
        FROM content_subject_versions
        WHERE version_id = $1
        """,
        uuid.UUID(version_id),
    )
    if not version:
        return None

    curriculum_id = version["curriculum_id"]
    subject = version["subject"]

    units = await conn.fetch(
        """
        SELECT unit_id, title, sort_order
        FROM curriculum_units
        WHERE curriculum_id = $1 AND subject = $2
        ORDER BY sort_order
        """,
        curriculum_id,
        subject,
    )

    history = await conn.fetch(
        """
        SELECT cr.review_id::text, cr.action, cr.notes, cr.reviewed_at,
               au.email AS reviewer_email
        FROM content_reviews cr
        LEFT JOIN admin_users au ON au.admin_user_id = cr.reviewer_id
        WHERE cr.version_id = $1
        ORDER BY cr.reviewed_at DESC
        LIMIT 20
        """,
        uuid.UUID(version_id),
    )

    annotations = await conn.fetch(
        """
        SELECT ca.annotation_id::text, ca.unit_id, ca.content_type,
               ca.annotation_text, ca.created_at,
               au.email AS reviewer_email
        FROM content_annotations ca
        LEFT JOIN admin_users au ON au.admin_user_id = ca.created_by
        WHERE ca.version_id = $1
        ORDER BY ca.created_at DESC
        """,
        uuid.UUID(version_id),
    )

    return {
        **dict(version),
        "units": [dict(u) for u in units],
        "review_history": [dict(h) for h in history],
        "annotations": [dict(a) for a in annotations],
    }


# ── Review session ────────────────────────────────────────────────────────────


async def open_review(
    conn: asyncpg.Connection,
    version_id: str,
    reviewer_id: str,
    notes: str | None,
) -> dict:
    row = await conn.fetchrow(
        """
        INSERT INTO content_reviews (version_id, reviewer_id, action, notes)
        VALUES ($1, $2, 'open', $3)
        RETURNING review_id::text, version_id::text, action, reviewed_at
        """,
        uuid.UUID(version_id),
        uuid.UUID(reviewer_id),
        notes,
    )
    await conn.execute(
        "UPDATE content_subject_versions SET status = 'in_review' WHERE version_id = $1 AND status = 'ready_for_review'",
        uuid.UUID(version_id),
    )
    from src.core.events import write_audit_log

    write_audit_log("review_opened", "admin", reviewer_id, metadata={"version_id": version_id})
    return dict(row)


async def add_annotation(
    conn: asyncpg.Connection,
    version_id: str,
    reviewer_id: str,
    unit_id: str,
    content_type: str,
    marked_text: str | None,
    annotation_text: str,
    start_offset: int | None,
    end_offset: int | None,
) -> dict:
    row = await conn.fetchrow(
        """
        INSERT INTO content_annotations
            (version_id, unit_id, content_type, marked_text, annotation_text,
             start_offset, end_offset, created_by)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        RETURNING annotation_id::text, version_id::text, unit_id, content_type,
                  annotation_text, created_at
        """,
        uuid.UUID(version_id),
        unit_id,
        content_type,
        marked_text,
        annotation_text,
        start_offset,
        end_offset,
        uuid.UUID(reviewer_id),
    )
    from src.core.events import write_audit_log

    write_audit_log(
        "review_annotated",
        "admin",
        reviewer_id,
        metadata={"version_id": version_id, "unit_id": unit_id},
    )
    return dict(row)


async def delete_annotation(
    conn: asyncpg.Connection,
    annotation_id: str,
    reviewer_id: str,
) -> bool:
    result = await conn.execute(
        "DELETE FROM content_annotations WHERE annotation_id = $1",
        uuid.UUID(annotation_id),
    )
    return result != "DELETE 0"


async def rate_version(
    conn: asyncpg.Connection,
    version_id: str,
    reviewer_id: str,
    language_rating: int,
    content_rating: int,
    notes: str | None,
) -> dict:
    row = await conn.fetchrow(
        """
        INSERT INTO content_reviews
            (version_id, reviewer_id, action, notes, language_rating, content_rating)
        VALUES ($1, $2, 'rate', $3, $4, $5)
        RETURNING review_id::text, version_id::text, language_rating, content_rating
        """,
        uuid.UUID(version_id),
        uuid.UUID(reviewer_id),
        notes,
        language_rating,
        content_rating,
    )
    from src.core.events import write_audit_log

    write_audit_log(
        "review_rated",
        "admin",
        reviewer_id,
        metadata={
            "version_id": version_id,
            "language_rating": language_rating,
            "content_rating": content_rating,
        },
    )
    return dict(row)


async def approve_version(
    conn: asyncpg.Connection,
    version_id: str,
    reviewer_id: str,
    notes: str | None,
) -> dict:
    await conn.execute(
        """
        INSERT INTO content_reviews (version_id, reviewer_id, action, notes)
        VALUES ($1, $2, 'approve', $3)
        """,
        uuid.UUID(version_id),
        uuid.UUID(reviewer_id),
        notes,
    )
    row = await conn.fetchrow(
        """
        UPDATE content_subject_versions
        SET status = 'approved'
        WHERE version_id = $1
        RETURNING version_id::text, status
        """,
        uuid.UUID(version_id),
    )
    from src.core.events import write_audit_log

    write_audit_log("review_approved", "admin", reviewer_id, metadata={"version_id": version_id})
    return dict(row) if row else {"version_id": version_id, "status": "approved"}


async def reject_version(
    conn: asyncpg.Connection,
    version_id: str,
    reviewer_id: str,
    notes: str | None,
    regenerate: bool,
) -> dict:
    await conn.execute(
        """
        INSERT INTO content_reviews (version_id, reviewer_id, action, notes)
        VALUES ($1, $2, 'reject', $3)
        """,
        uuid.UUID(version_id),
        uuid.UUID(reviewer_id),
        notes,
    )
    row = await conn.fetchrow(
        """
        UPDATE content_subject_versions
        SET status = 'rejected'
        WHERE version_id = $1
        RETURNING version_id::text, status, curriculum_id, subject
        """,
        uuid.UUID(version_id),
    )
    result = dict(row) if row else {"version_id": version_id, "status": "rejected"}
    result["regenerating"] = False

    from src.core.events import write_audit_log

    write_audit_log(
        "review_rejected",
        "admin",
        reviewer_id,
        metadata={"version_id": version_id, "regenerate": regenerate},
    )

    if regenerate and row:
        try:
            from src.auth.tasks import celery_app

            celery_app.send_task(
                "src.auth.tasks.regenerate_subject_task",
                args=[row["curriculum_id"], row["subject"]],
            )
            result["regenerating"] = True
            log.info("regenerate_dispatched version_id=%s", version_id)
        except Exception as exc:
            log.warning("regenerate_dispatch_failed version_id=%s error=%s", version_id, exc)

    return result


# ── Publish / rollback ────────────────────────────────────────────────────────


async def publish_version(
    conn: asyncpg.Connection,
    redis,
    version_id: str,
    admin_id: str,
) -> dict:
    """
    Publish a content_subject_versions row:
    1. Archive the currently published version (set archived_at).
    2. Set this version's status = 'published', published_at = NOW().
    3. Log audit event.
    4. Expire Redis content cache + trigger CDN invalidation.
    """
    # Fetch the version to get curriculum_id + subject
    target = await conn.fetchrow(
        "SELECT curriculum_id, subject FROM content_subject_versions WHERE version_id = $1",
        uuid.UUID(version_id),
    )
    if not target:
        return {}

    curriculum_id = target["curriculum_id"]
    subject = target["subject"]

    # Archive the current published version (if any)
    await conn.execute(
        """
        UPDATE content_subject_versions
        SET archived_at = NOW()
        WHERE curriculum_id = $1 AND subject = $2 AND status = 'published'
          AND version_id != $3
        """,
        curriculum_id,
        subject,
        uuid.UUID(version_id),
    )

    row = await conn.fetchrow(
        """
        UPDATE content_subject_versions
        SET status = 'published', published_at = NOW()
        WHERE version_id = $1
        RETURNING version_id::text, status, published_at
        """,
        uuid.UUID(version_id),
    )

    # Audit log
    from src.core.events import write_audit_log

    write_audit_log("content_published", "admin", admin_id, metadata={"version_id": version_id})

    # Expire Redis content cache keys for this curriculum/subject
    await _expire_content_cache(redis, curriculum_id, subject)

    # CDN invalidation
    _invalidate_cdn(curriculum_id)

    return dict(row) if row else {}


async def rollback_version(
    conn: asyncpg.Connection,
    redis,
    version_id: str,
    admin_id: str,
) -> dict:
    """
    Rollback the currently published version:
    1. Move this version back to 'approved' (un-publish it).
    2. Restore the most recently archived version for the same subject to 'published'.
       If no prior version exists, leave the subject without a live published version.
    3. Log audit event, expire Redis + CDN.
    """
    target = await conn.fetchrow(
        "SELECT curriculum_id, subject FROM content_subject_versions WHERE version_id = $1",
        uuid.UUID(version_id),
    )
    if not target:
        return {}

    curriculum_id = target["curriculum_id"]
    subject = target["subject"]

    # Step 1: un-publish the current version
    await conn.execute(
        """
        UPDATE content_subject_versions
        SET status = 'approved', published_at = NULL
        WHERE version_id = $1
        """,
        uuid.UUID(version_id),
    )

    # Step 2: find the most recently archived version and restore it
    prev = await conn.fetchrow(
        """
        SELECT version_id
        FROM content_subject_versions
        WHERE curriculum_id = $1 AND subject = $2
          AND archived_at IS NOT NULL
          AND version_id != $3
        ORDER BY archived_at DESC
        LIMIT 1
        """,
        curriculum_id,
        subject,
        uuid.UUID(version_id),
    )

    restored_id = None
    if prev:
        restored_id = prev["version_id"]
        await conn.execute(
            """
            UPDATE content_subject_versions
            SET status = 'published', published_at = NOW(), archived_at = NULL
            WHERE version_id = $1
            """,
            restored_id,
        )

    row = await conn.fetchrow(
        "SELECT version_id::text, status FROM content_subject_versions WHERE version_id = $1",
        uuid.UUID(version_id),
    )

    from src.core.events import write_audit_log

    write_audit_log(
        "content_rollback",
        "admin",
        admin_id,
        metadata={
            "version_id": version_id,
            "restored_version_id": str(restored_id) if restored_id else None,
        },
    )

    await _expire_content_cache(redis, curriculum_id, subject)
    _invalidate_cdn(curriculum_id)

    return dict(row) if row else {}


async def _expire_content_cache(redis, curriculum_id: str, subject: str) -> None:
    """Delete all Redis content cache keys for a curriculum/subject."""
    try:
        pattern = f"content:{curriculum_id}:*"
        cursor = b"0"
        while cursor:
            cursor, keys = await redis.scan(cursor, match=pattern, count=100)
            if keys:
                await redis.delete(*keys)
            if cursor == b"0":
                break
        log.info("content_cache_expired curriculum_id=%s subject=%s", curriculum_id, subject)
    except Exception as exc:
        log.warning("content_cache_expire_failed error=%s", exc)


def _invalidate_cdn(curriculum_id: str) -> None:
    """Fire-and-forget CloudFront invalidation for a curriculum."""
    try:
        from src.content.service import invalidate_cdn_path

        invalidate_cdn_path(curriculum_id)
    except Exception as exc:
        log.warning("cdn_invalidation_failed curriculum_id=%s error=%s", curriculum_id, exc)


# ── Block version (creates block record + marks version blocked) ───────────────


async def block_version(
    conn: asyncpg.Connection,
    version_id: str,
    unit_id: str,
    content_type: str,
    reason: str | None,
    admin_id: str,
) -> dict:
    """
    Block a unit's content type and flip the subject version status to 'blocked'.
    Both writes happen in the same transaction.
    """
    version = await conn.fetchrow(
        "SELECT curriculum_id, subject FROM content_subject_versions WHERE version_id = $1",
        uuid.UUID(version_id),
    )
    if not version:
        raise ValueError("version_not_found")

    curriculum_id = version["curriculum_id"]

    block_row = await conn.fetchrow(
        """
        INSERT INTO content_blocks (curriculum_id, unit_id, content_type, reason, blocked_by)
        VALUES ($1, $2, $3, $4, $5)
        ON CONFLICT (curriculum_id, unit_id, content_type) DO UPDATE
            SET reason = EXCLUDED.reason, blocked_by = EXCLUDED.blocked_by,
                blocked_at = NOW(), unblocked_at = NULL
        RETURNING block_id::text, curriculum_id, unit_id, content_type, blocked_at
        """,
        curriculum_id,
        unit_id,
        content_type,
        reason,
        uuid.UUID(admin_id),
    )

    await conn.execute(
        "UPDATE content_subject_versions SET status = 'blocked' WHERE version_id = $1",
        uuid.UUID(version_id),
    )

    from src.core.events import write_audit_log

    write_audit_log(
        "content_blocked",
        "admin",
        admin_id,
        metadata={"version_id": version_id, "unit_id": unit_id, "content_type": content_type},
    )
    return dict(block_row)


# ── Content blocks ────────────────────────────────────────────────────────────


async def create_block(
    conn: asyncpg.Connection,
    curriculum_id: str,
    unit_id: str,
    content_type: str,
    reason: str | None,
    admin_id: str,
) -> dict:
    row = await conn.fetchrow(
        """
        INSERT INTO content_blocks (curriculum_id, unit_id, content_type, reason, blocked_by)
        VALUES ($1, $2, $3, $4, $5)
        ON CONFLICT (curriculum_id, unit_id, content_type) DO UPDATE
            SET reason = EXCLUDED.reason, blocked_by = EXCLUDED.blocked_by,
                blocked_at = NOW(), unblocked_at = NULL
        RETURNING block_id::text, curriculum_id, unit_id, content_type, blocked_at
        """,
        curriculum_id,
        unit_id,
        content_type,
        reason,
        uuid.UUID(admin_id),
    )
    from src.core.events import write_audit_log

    write_audit_log(
        "content_blocked",
        "admin",
        admin_id,
        metadata={"unit_id": unit_id, "content_type": content_type},
    )
    return dict(row)


async def remove_block(
    conn: asyncpg.Connection,
    block_id: str,
    admin_id: str,
) -> bool:
    result = await conn.execute(
        "UPDATE content_blocks SET unblocked_at = NOW() WHERE block_id = $1 AND unblocked_at IS NULL",
        uuid.UUID(block_id),
    )
    if result != "UPDATE 0":
        from src.core.events import write_audit_log

        write_audit_log("content_unblocked", "admin", admin_id, metadata={"block_id": block_id})
        return True
    return False


# ── Student feedback listing ──────────────────────────────────────────────────


async def list_feedback(
    conn: asyncpg.Connection,
    unit_id: str,
    limit: int = 50,
    offset: int = 0,
) -> dict:
    rows = await conn.fetch(
        """
        SELECT feedback_id::text, student_id::text, curriculum_id, content_type,
               category, message, created_at
        FROM student_content_feedback
        WHERE unit_id = $1
        ORDER BY created_at DESC
        LIMIT $2 OFFSET $3
        """,
        unit_id,
        limit,
        offset,
    )
    total = await conn.fetchval(
        "SELECT COUNT(*) FROM student_content_feedback WHERE unit_id = $1",
        unit_id,
    )
    return {"items": [dict(r) for r in rows], "total": total or 0}


async def get_feedback_report(
    conn: asyncpg.Connection,
    threshold: int = 3,
    limit: int = 50,
) -> dict:
    """
    Units where student feedback count >= threshold, ordered by report_count desc.

    Surfaces content that students are flagging most so admins can prioritise review.
    """
    rows = await conn.fetch(
        """
        SELECT
            unit_id,
            curriculum_id,
            COUNT(*)                                                        AS report_count,
            COUNT(*) FILTER (WHERE category = 'incorrect')                 AS incorrect_count,
            COUNT(*) FILTER (WHERE category = 'confusing')                 AS confusing_count,
            COUNT(*) FILTER (WHERE category = 'inappropriate')             AS inappropriate_count,
            COUNT(*) FILTER (WHERE category NOT IN ('incorrect','confusing','inappropriate')) AS other_count
        FROM student_content_feedback
        GROUP BY unit_id, curriculum_id
        HAVING COUNT(*) >= $1
        ORDER BY report_count DESC
        LIMIT $2
        """,
        threshold,
        limit,
    )
    return {
        "items": [dict(r) for r in rows],
        "threshold": threshold,
    }


# ── Subscription analytics ────────────────────────────────────────────────────


async def get_subscription_analytics(conn: asyncpg.Connection) -> dict:
    """MRR, churn, new/cancelled this month."""
    totals = await conn.fetchrow(
        """
        SELECT
            COUNT(*) FILTER (WHERE status = 'active' AND plan = 'monthly') AS active_monthly,
            COUNT(*) FILTER (WHERE status = 'active' AND plan = 'annual')  AS active_annual
        FROM subscriptions
        WHERE status = 'active'
        """
    )
    active_monthly = totals["active_monthly"] or 0
    active_annual = totals["active_annual"] or 0
    mrr = round(active_monthly * _MONTHLY_PRICE_USD + active_annual * _ANNUAL_MONTHLY_USD, 2)

    month_stats = await conn.fetchrow(
        """
        SELECT
            COUNT(*) FILTER (WHERE created_at >= date_trunc('month', NOW())) AS new_this_month,
            COUNT(*) FILTER (
                WHERE status = 'cancelled'
                  AND updated_at >= date_trunc('month', NOW())
            ) AS cancelled_this_month
        FROM subscriptions
        """
    )
    new_this_month = month_stats["new_this_month"] or 0
    cancelled_this_month = month_stats["cancelled_this_month"] or 0
    total_active = active_monthly + active_annual
    churn_denominator = total_active + cancelled_this_month
    churn_rate = round(cancelled_this_month / churn_denominator, 4) if churn_denominator else 0.0

    return {
        "active_monthly": active_monthly,
        "active_annual": active_annual,
        "total_active": total_active,
        "mrr_usd": mrr,
        "new_this_month": new_this_month,
        "cancelled_this_month": cancelled_this_month,
        "churn_rate": churn_rate,
    }


# ── Struggle analytics ────────────────────────────────────────────────────────


async def get_struggle_report(conn: asyncpg.Connection, limit: int = 20) -> dict:
    """
    Units where students struggle most:
    ordered by mean_attempts DESC, filtered to units with ≥ 3 attempts.
    """
    rows = await conn.fetch(
        """
        SELECT
            s.unit_id,
            s.curriculum_id,
            COUNT(*)                                          AS total_attempts,
            ROUND(AVG(attempt_number)::numeric, 2)           AS mean_attempts,
            ROUND(AVG(CASE WHEN passed THEN 1 ELSE 0 END)::numeric, 4) AS pass_rate
        FROM progress_sessions s
        WHERE ended_at IS NOT NULL
        GROUP BY s.unit_id, s.curriculum_id
        HAVING COUNT(*) >= 3
        ORDER BY mean_attempts DESC, pass_rate ASC
        LIMIT $1
        """,
        limit,
    )
    return {
        "items": [
            {
                "unit_id": r["unit_id"],
                "curriculum_id": r["curriculum_id"],
                "total_attempts": r["total_attempts"],
                "mean_attempts": float(r["mean_attempts"]),
                "pass_rate": float(r["pass_rate"]),
            }
            for r in rows
        ]
    }


# ── Pipeline status ───────────────────────────────────────────────────────────


async def get_pipeline_status(conn: asyncpg.Connection) -> dict:
    row = await conn.fetchrow(
        """
        SELECT
            MAX(generated_at) AS last_run_at,
            COUNT(*)                                                        AS total_versions,
            COUNT(*) FILTER (WHERE status IN ('pending','ready_for_review','needs_review')) AS ready_for_review,
            COUNT(*) FILTER (WHERE status = 'approved')                    AS approved,
            COUNT(*) FILTER (WHERE status = 'published')                   AS published,
            COUNT(*) FILTER (WHERE status = 'rejected')                    AS rejected,
            COUNT(*) FILTER (WHERE status NOT IN ('pending','ready_for_review','needs_review','approved','published','rejected')) AS other
        FROM content_subject_versions
        WHERE archived_at IS NULL
        """
    )
    return {
        "last_run_at": row["last_run_at"],
        "total_versions": row["total_versions"] or 0,
        "ready_for_review": row["ready_for_review"] or 0,
        "approved": row["approved"] or 0,
        "published": row["published"] or 0,
        "rejected": row["rejected"] or 0,
        "pending": row["pending"] or 0,
    }


# ── Dictionary ────────────────────────────────────────────────────────────────


async def lookup_dictionary(word: str) -> dict:
    """
    Look up a word using Datamuse (free, no key) and optionally
    Merriam-Webster (if MW_API_KEY is configured).

    Returns {word, definitions, synonyms, antonyms}.
    """
    definitions: list[str] = []
    synonyms: list[str] = []
    antonyms: list[str] = []

    try:
        async with httpx.AsyncClient(timeout=5) as client:
            # Synonyms from Datamuse
            r_syn = await client.get(
                "https://api.datamuse.com/words",
                params={"rel_syn": word, "max": 10},
            )
            if r_syn.status_code == 200:
                synonyms = [item["word"] for item in r_syn.json()]

            # Antonyms from Datamuse
            r_ant = await client.get(
                "https://api.datamuse.com/words",
                params={"rel_ant": word, "max": 10},
            )
            if r_ant.status_code == 200:
                antonyms = [item["word"] for item in r_ant.json()]

    except Exception as exc:
        log.warning("datamuse_lookup_failed word=%s error=%s", word, exc)

    # Merriam-Webster definitions (optional)
    try:
        from config import settings

        mw_key = getattr(settings, "MW_API_KEY", None)
        if mw_key:
            async with httpx.AsyncClient(timeout=5) as client:
                r_def = await client.get(
                    f"https://www.dictionaryapi.com/api/v3/references/collegiate/json/{word}",
                    params={"key": mw_key},
                )
                if r_def.status_code == 200:
                    data = r_def.json()
                    for entry in data[:3]:
                        if isinstance(entry, dict):
                            shortdefs = entry.get("shortdef", [])
                            definitions.extend(shortdefs[:2])
    except Exception as exc:
        log.warning("merriam_webster_lookup_failed word=%s error=%s", word, exc)

    return {
        "word": word,
        "definitions": definitions[:6],
        "synonyms": synonyms,
        "antonyms": antonyms,
    }


# ── Unit content viewer ────────────────────────────────────────────────────────

_CONTENT_TYPES_ORDERED = [
    "lesson",
    "tutorial",
    "quiz_set_1",
    "quiz_set_2",
    "quiz_set_3",
    "experiment",
]


async def get_unit_content_meta(
    conn: asyncpg.Connection,
    version_id: str,
    unit_id: str,
    lang: str = "en",
) -> dict | None:
    """
    Return unit title + list of content types that have files on disk.
    Resolves curriculum_id from the version row, then checks the filesystem.
    """
    row = await conn.fetchrow(
        """
        SELECT csv.curriculum_id, cu.title
        FROM content_subject_versions csv
        JOIN curriculum_units cu
          ON cu.unit_id = $2 AND cu.curriculum_id = csv.curriculum_id
        WHERE csv.version_id = $1
        LIMIT 1
        """,
        uuid.UUID(version_id),
        unit_id,
    )
    if not row:
        return None

    curriculum_id = row["curriculum_id"]
    title = row["title"]
    unit_dir = os.path.join(_settings.CONTENT_STORE_PATH, "curricula", curriculum_id, unit_id)

    available: list[str] = []
    for ct in _CONTENT_TYPES_ORDERED:
        if os.path.isfile(os.path.join(unit_dir, f"{ct}_{lang}.json")):
            available.append(ct)

    return {
        "unit_id": unit_id,
        "title": title,
        "curriculum_id": curriculum_id,
        "lang": lang,
        "available_types": available,
    }


async def get_unit_content_file(
    conn: asyncpg.Connection,
    version_id: str,
    unit_id: str,
    content_type: str,
    lang: str = "en",
) -> dict | None:
    """
    Read and return the raw JSON for a specific content type from disk.
    Returns None if version not found; raises FileNotFoundError if file absent.
    """
    row = await conn.fetchrow(
        "SELECT curriculum_id FROM content_subject_versions WHERE version_id = $1",
        uuid.UUID(version_id),
    )
    if not row:
        return None

    curriculum_id = row["curriculum_id"]
    file_path = os.path.join(
        _settings.CONTENT_STORE_PATH,
        "curricula",
        curriculum_id,
        unit_id,
        f"{content_type}_{lang}.json",
    )

    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"Content file not found: {file_path}")

    with open(file_path, encoding="utf-8") as f:
        data = json.load(f)

    return {
        "unit_id": unit_id,
        "curriculum_id": curriculum_id,
        "content_type": content_type,
        "lang": lang,
        "data": data,
    }
