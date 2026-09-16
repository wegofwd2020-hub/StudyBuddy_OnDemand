#!/usr/bin/env python3
"""
backend/scripts/backfill_curriculum_stream_codes.py

Populate `curricula.stream_code` (migration 0044) for PLATFORM DEFAULT curricula.

Why this is needed
──────────────────
Migration 0044 added the column and 0045 added the `streams` registry with five
system seeds, but nothing ever wrote the column for the default curricula:
`seed_default_curriculum()` inserts `(curriculum_id, grade, year, name,
source_type, status)` and stops there. The two paths that DO set it — the admin
upload endpoint and the stream merge action — were never used for the platform
defaults. Result on the demo: all 19 curricula carry NULL, and every row of the
`streams` registry reports `curricula_count = 0`.

So the one attribute that says which stream a curriculum belongs to lives only
in the curriculum_id's suffix, where no query can reach it. That is what blocks
the Grade/Stream filters Venki asked for (#771, #772, #773, #774, #776): there
is nothing to filter ON.

Why a script rather than a migration
────────────────────────────────────
No schema changes — the column has existed since 0044. This is data repair for
platform-owned rows, which is what `backfill_question_registry.py` is too.

Why an explicit map rather than parsing the id
──────────────────────────────────────────────
`default-2026-g11-commerce` parses cleanly, but the set does not:

  - `default-2026-g8` / `-g10` / `-g11` carry no suffix at all and are STEM
    (their names say so: "Grade 8 STEM 2026").
  - `default-2026-g9-advanced` has a suffix that is NOT a stream. "Advanced" is
    a track within STEM, and `advanced` is not in the registry.
  - `default-2026-g12` is bare and its name says only "Default Grade 12
    Curriculum", so its stream is genuinely unclear — g12 has -commerce and
    -science siblings, which makes the bare one legacy STEM by elimination, but
    that is an inference rather than a fact.

A parser would silently mint `advanced` as a sixth stream and guess at the bare
ids. The two genuinely ambiguous rows are therefore left NULL on purpose and
must be set by a human who knows the answer.

NULL is a first-class value, not a gap
──────────────────────────────────────
School-owned curricula and school forks have no stream and never will. Anything
that filters by stream has to offer an "Unstreamed" bucket rather than dropping
those rows, or the filter manufactures the coverage gap that #774's grade filter
was explicitly built to avoid. This script only ever fills NULLs it is confident
about; it never invents a stream to make a set look complete.

Idempotent
──────────
Only rows whose `stream_code IS NULL` are touched, so a value set by an admin
through the Streams UI is never overwritten by a re-run.

Usage:
    docker compose exec -T api python scripts/backfill_curriculum_stream_codes.py            # dry run
    docker compose exec -T api python scripts/backfill_curriculum_stream_codes.py --commit

Environment:
    DATABASE_URL — required
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys

import asyncpg

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# curriculum_id -> stream code from the 0045 registry.
#
# Deliberately explicit. Every entry here is one someone can check against the
# curriculum's name; anything not listed is left alone rather than guessed.
STREAM_BY_CURRICULUM_ID: dict[str, str] = {
    # Named suffix, unambiguous.
    "default-2026-g5-stem": "stem",
    "default-2026-g6-stem": "stem",
    "default-2026-g7-stem": "stem",
    "default-2026-g9-stem": "stem",
    "default-2026-g9-english": "english",
    "default-2026-g11-commerce": "commerce",
    "default-2026-g11-humanities": "humanities",
    "default-2026-g11-science": "science",
    "default-2026-g12-commerce": "commerce",
    "default-2026-g12-science": "science",
    # No suffix, but the curriculum NAME says STEM explicitly
    # ("Grade 8 STEM 2026", "Grade 10 STEM 2026", "Grade 11 STEM 2026").
    "default-2026-g8": "stem",
    "default-2026-g10": "stem",
    "default-2026-g11": "stem",
}

# Left NULL on purpose — see the module docstring. Listed so the script can say
# why it skipped them instead of leaving someone to wonder.
DELIBERATELY_UNMAPPED: dict[str, str] = {
    "default-2026-g9-advanced": (
        "'advanced' is a track, not a stream, and is not in the registry"
    ),
    "default-2026-g12": (
        "name is 'Default Grade 12 Curriculum 2026' — STEM only by elimination, "
        "which is an inference, not a fact"
    ),
}


async def run(commit: bool) -> int:
    dsn = os.environ.get("DATABASE_URL", "").replace("postgresql+asyncpg://", "postgresql://")
    if not dsn:
        print("DATABASE_URL is not set", file=sys.stderr)
        return 2

    conn = await asyncpg.connect(dsn)
    try:
        # Platform-owned rows are RESTRICTIVE-RLS protected since Epic 10 L-1
        # (migration 0046); without this every UPDATE silently matches 0 rows.
        # Pitfall #28.
        await conn.execute("SET app.current_school_id = 'bypass'")

        known = {r["code"] for r in await conn.fetch("SELECT code FROM streams WHERE NOT is_archived")}
        unknown = set(STREAM_BY_CURRICULUM_ID.values()) - known
        if unknown:
            print(f"refusing to write codes absent from the streams registry: {sorted(unknown)}",
                  file=sys.stderr)
            return 2

        rows = await conn.fetch(
            """
            SELECT curriculum_id, name, grade, stream_code
            FROM curricula
            WHERE owner_type = 'platform'
            ORDER BY grade, curriculum_id
            """
        )

        planned: list[tuple[str, str]] = []
        for r in rows:
            cid = r["curriculum_id"]
            want = STREAM_BY_CURRICULUM_ID.get(cid)
            if r["stream_code"] is not None:
                print(f"  keep    {cid:<30} already {r['stream_code']!r}")
            elif want:
                planned.append((cid, want))
                print(f"  SET     {cid:<30} -> {want}")
            elif cid in DELIBERATELY_UNMAPPED:
                print(f"  skip    {cid:<30} {DELIBERATELY_UNMAPPED[cid]}")
            else:
                print(f"  skip    {cid:<30} not in the map; left NULL")

        print(f"\n{len(planned)} row(s) to update.")
        if not commit:
            print("Dry run — nothing written. Re-run with --commit to persist.")
            return 0

        async with conn.transaction():
            for cid, code in planned:
                # `IS NULL` in the predicate as well as the filter above: two
                # concurrent runs must not have the second overwrite the first.
                await conn.execute(
                    "UPDATE curricula SET stream_code = $2"
                    " WHERE curriculum_id = $1 AND stream_code IS NULL",
                    cid,
                    code,
                )
        print(f"Committed {len(planned)} row(s).")
        return 0
    finally:
        await conn.close()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--commit", action="store_true", help="persist (default is a dry run)")
    args = ap.parse_args()
    raise SystemExit(asyncio.run(run(args.commit)))


if __name__ == "__main__":
    main()
