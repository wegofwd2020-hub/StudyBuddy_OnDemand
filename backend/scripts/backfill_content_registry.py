"""
backend/scripts/backfill_content_registry.py

Register pipeline-generated content that exists on disk but has no DB rows.

Why this exists
---------------
`pipeline/build_grade.py` writes content files to the Content Store FIRST, then
performs its DB upserts inside a broad `except` that logs and continues. So when
any of the known pipeline pitfalls fire — missing RLS bypass (#28), a str instead
of a datetime bound to a TIMESTAMPTZ (#29), or the NOT NULL `unit_name` omitted
(#30) — content generation still reports success while `curricula`,
`curriculum_units`, and `content_subject_versions` are never written.

Net effect: real, paid-for content sits on disk and is invisible to the app.
A student clicking the lesson gets "This isn't available yet."

This script reconciles the DB back to what is actually on disk. It is the repair
tool; fixing the pipeline's silent-except is the separate root-cause fix.

What it does, per `default-*` curriculum directory in the Content Store:
  1. Skips units whose lesson is dev-placeholder (never register stub content)
  2. Upserts the `curricula` row
  3. Upserts `curriculum_units` (title/description/has_lab from data/*.json)
  4. Upserts a published `content_subject_versions` row per subject

Metadata (subject display names, unit titles, has_lab) comes from the
authoritative `data/grade{N}_{stream}.json` files — the same source the pipeline
reads — not from the generated content, which does not carry them.

Idempotent. Dry-run by default.

Usage (inside the api container):
    python scripts/backfill_content_registry.py                 # dry run
    python scripts/backfill_content_registry.py --commit
    python scripts/backfill_content_registry.py --commit --only default-2026-g10
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
from datetime import UTC, datetime

import asyncpg

# ── Config ────────────────────────────────────────────────────────────────────

# Connect directly to PostgreSQL, not PgBouncer: transaction-pooling mode drops
# asyncpg prepared statements silently.
_raw_url = os.environ.get(
    "DATABASE_URL", "postgresql://studybuddy:studybuddy_dev@db:5432/studybuddy"
)
DATABASE_URL = _raw_url.replace("@pgbouncer:", "@db:")
CONTENT_STORE_PATH = os.environ.get("CONTENT_STORE_PATH", "/data/content")

DATA_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "data")
)

PLACEHOLDER_MODEL = "dev-placeholder"
YEAR = 2026

# default-2026-g11-science → grade=11, stream="science"
# default-2026-g10         → grade=10, stream="stem"
_CURRICULUM_RE = re.compile(r"^default-(\d{4})-g(\d+)(?:-([a-z]+))?$")


# ── Disk inspection ───────────────────────────────────────────────────────────


def parse_curriculum_id(curriculum_id: str) -> tuple[int, int, str] | None:
    """(year, grade, stream) or None if the id doesn't match the default-* shape."""
    m = _CURRICULUM_RE.match(curriculum_id)
    if not m:
        return None
    year, grade, stream = m.groups()
    return int(year), int(grade), stream or "stem"


def load_source_metadata(grade: int, stream: str) -> dict | None:
    """
    Load data/grade{N}_{stream}.json — the pipeline's own source of truth for
    subject display names and unit titles. Returns None if absent.
    """
    path = os.path.join(DATA_DIR, f"grade{grade}_{stream}.json")
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)


def real_units_on_disk(curriculum_id: str) -> set[str]:
    """
    Unit ids that have genuine generated content.

    A unit counts only if it has a lesson_en.json that is NOT dev-placeholder —
    registering a stub would let the seeder's fake quiz reach a student.
    """
    base = os.path.join(CONTENT_STORE_PATH, "curricula", curriculum_id)
    if not os.path.isdir(base):
        return set()

    units: set[str] = set()
    for unit_id in os.listdir(base):
        lesson = os.path.join(base, unit_id, "lesson_en.json")
        if not os.path.exists(lesson):
            continue
        try:
            with open(lesson) as f:
                data = json.load(f)
        except (OSError, ValueError):
            continue
        if data.get("model") == PLACEHOLDER_MODEL:
            continue
        units.add(unit_id)
    return units


def discover() -> list[str]:
    root = os.path.join(CONTENT_STORE_PATH, "curricula")
    if not os.path.isdir(root):
        return []
    return sorted(c for c in os.listdir(root) if _CURRICULUM_RE.match(c))


# ── Backfill ──────────────────────────────────────────────────────────────────


async def backfill_curriculum(
    conn: asyncpg.Connection, curriculum_id: str, commit: bool
) -> dict:
    """Register one curriculum. Returns a per-table count summary."""
    stats = {"curricula": 0, "units": 0, "subject_versions": 0, "skipped_units": 0}

    parsed = parse_curriculum_id(curriculum_id)
    if not parsed:
        print(f"  ! {curriculum_id}: unrecognised id shape — skipped")
        return stats
    _year, grade, stream = parsed

    on_disk = real_units_on_disk(curriculum_id)
    if not on_disk:
        print(f"  - {curriculum_id}: no real content on disk (all stub/empty) — skipped")
        return stats

    source = load_source_metadata(grade, stream)
    if not source:
        print(
            f"  ! {curriculum_id}: no data/grade{grade}_{stream}.json — "
            f"cannot resolve titles/subject names — skipped"
        )
        return stats

    label = f"Grade {grade}" + ("" if stream == "stem" else f" {stream.title()}")
    name = f"Default {label} Curriculum {YEAR}"

    # ── curricula ─────────────────────────────────────────────────────────────
    # owner_type defaults to 'platform'; migration 0046 puts a RESTRICTIVE RLS
    # policy on platform-owned rows, so the caller must have stamped
    # app.current_school_id='bypass' (pitfall #28) — main() does.
    if commit:
        r = await conn.execute(
            """
            INSERT INTO curricula (curriculum_id, grade, year, name, is_default)
            VALUES ($1, $2, $3, $4, TRUE)
            ON CONFLICT (curriculum_id) DO NOTHING
            """,
            curriculum_id, grade, YEAR, name,
        )
        if r != "INSERT 0 0":
            stats["curricula"] += 1
    else:
        exists = await conn.fetchval(
            "SELECT 1 FROM curricula WHERE curriculum_id = $1", curriculum_id
        )
        if not exists:
            stats["curricula"] += 1

    # ── curriculum_units + content_subject_versions ───────────────────────────
    subjects_with_content: dict[str, str] = {}  # subject_code -> display name

    for subject in source["subjects"]:
        subject_code = subject["subject_id"]      # e.g. G10-MATH
        subject_name = subject["name"]            # e.g. Mathematics  (pitfall #32)

        for sort_order, unit in enumerate(subject["units"]):
            unit_id = unit["unit_id"]
            if unit_id not in on_disk:
                stats["skipped_units"] += 1       # never generated, or stub
                continue

            subjects_with_content[subject_code] = subject_name

            if commit:
                r = await conn.execute(
                    """
                    INSERT INTO curriculum_units
                        (unit_id, curriculum_id, subject, title, unit_name,
                         description, has_lab, sort_order)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    ON CONFLICT (unit_id, curriculum_id) DO NOTHING
                    """,
                    unit_id,
                    curriculum_id,
                    subject_code,
                    unit["title"],
                    unit["title"],   # unit_name is NOT NULL — mirror title (pitfall #30)
                    unit.get("description") or None,
                    unit.get("has_lab", False),
                    sort_order,
                )
                if r != "INSERT 0 0":
                    stats["units"] += 1
            else:
                exists = await conn.fetchval(
                    "SELECT 1 FROM curriculum_units WHERE unit_id = $1 AND curriculum_id = $2",
                    unit_id, curriculum_id,
                )
                if not exists:
                    stats["units"] += 1

    # One published version row per subject that actually has content on disk.
    for subject_code, subject_name in subjects_with_content.items():
        existing = await conn.fetchval(
            """
            SELECT 1 FROM content_subject_versions
            WHERE curriculum_id = $1 AND subject = $2 AND status = 'published'
            """,
            curriculum_id, subject_code,
        )
        if existing:
            continue

        if commit:
            # published_at must be a datetime, never an ISO string — asyncpg
            # rejects the bind and the pipeline's broad except swallows it (#29).
            await conn.execute(
                """
                INSERT INTO content_subject_versions
                    (curriculum_id, subject, subject_name, version_number,
                     status, published_at)
                VALUES ($1, $2, $3, 1, 'published', $4)
                ON CONFLICT (curriculum_id, subject, version_number) DO UPDATE
                    SET status       = 'published',
                        subject_name = EXCLUDED.subject_name,
                        published_at = EXCLUDED.published_at
                """,
                curriculum_id,
                subject_code,
                subject_name,
                datetime.now(tz=UTC),
            )
        stats["subject_versions"] += 1

    verb = "registered" if commit else "would register"
    print(
        f"  ✓ {curriculum_id}: {verb} "
        f"{stats['curricula']} curriculum, {stats['units']} units, "
        f"{stats['subject_versions']} subject versions "
        f"({len(on_disk)} units with real content"
        + (f", {stats['skipped_units']} not generated" if stats["skipped_units"] else "")
        + ")"
    )
    return stats


async def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--commit", action="store_true", help="persist (default: dry run)")
    ap.add_argument("--only", help="restrict to a single curriculum_id")
    args = ap.parse_args()

    curricula = discover()
    if args.only:
        curricula = [c for c in curricula if c == args.only]
        if not curricula:
            print(f"ERROR: {args.only} not found in {CONTENT_STORE_PATH}/curricula")
            sys.exit(1)

    if not curricula:
        print(f"No default-* curricula found in {CONTENT_STORE_PATH}/curricula")
        sys.exit(1)

    mode = "COMMIT" if args.commit else "DRY RUN (no writes — pass --commit to persist)"
    print(f"Content registry backfill — {mode}")
    print(f"  store: {CONTENT_STORE_PATH}/curricula")
    print(f"  found: {len(curricula)} curricula\n")

    conn = await asyncpg.connect(DATABASE_URL)
    # RLS bypass — curricula carries a RESTRICTIVE write-guard policy on
    # owner_type='platform' rows (migration 0046). Without this every INSERT is
    # silently refused. See pitfall #28.
    await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")

    totals = {"curricula": 0, "units": 0, "subject_versions": 0}
    try:
        for curriculum_id in curricula:
            stats = await backfill_curriculum(conn, curriculum_id, args.commit)
            for k in totals:
                totals[k] += stats[k]
    finally:
        await conn.close()

    verb = "Registered" if args.commit else "Would register"
    print(
        f"\n{verb}: {totals['curricula']} curricula, {totals['units']} units, "
        f"{totals['subject_versions']} subject versions"
    )
    if not args.commit:
        print("Dry run — nothing written. Re-run with --commit to apply.")


if __name__ == "__main__":
    asyncio.run(main())
