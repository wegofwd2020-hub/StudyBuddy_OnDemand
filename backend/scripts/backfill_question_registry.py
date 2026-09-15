#!/usr/bin/env python3
"""
backend/scripts/backfill_question_registry.py

Populate `question_registry` (migration 0069) from the questions that already
exist in the content store — ADR-008 Phase 3a.

This is the step that makes a pool draw possible without generating anything. A
unit's three quiz sets already hold a median of 24 distinct questions on platform
content; registering them turns "one of 3 fixed sets" into "8 drawn from 24",
which is the whole of the tester's predictability ask at zero generation cost.

Deduplication is the point, not a detail
────────────────────────────────────────
Rows are keyed by `stable_question_id` — sha256 over curriculum|unit|lang|stem
(migration 0067). Two sets containing the same question therefore collapse to ONE
registry row, which is exactly what a pool needs and exactly what concatenating
the sets would not give you.

It matters here specifically. Measured across the store: platform curricula have
ZERO duplicate stems inside a set, but Authoring Studio output has 82% — one unit
had 24 questions and 1 distinct. Registering by identity means that content
contributes one drawable question rather than twenty-four copies of it. A naive
importer would have built a pool that draws the same question eight times.

Idempotent
──────────
ON CONFLICT DO UPDATE on the identity. Re-running after a content regeneration
adds what is new and refreshes difficulty, without disturbing `status` — so a
question retired by a human stays retired across a re-import. That last clause is
the reason this is an UPDATE of specific columns rather than an upsert of the
whole row.

Usage:
    docker compose exec -T api python scripts/backfill_question_registry.py            # all curricula
    docker compose exec -T api python scripts/backfill_question_registry.py --dry-run
    docker compose exec -T api python scripts/backfill_question_registry.py --curriculum default-2026-g8
    docker compose exec -T api python scripts/backfill_question_registry.py --lang en,fr

Environment:
    DATABASE_URL         — required
    CONTENT_STORE_PATH   — required (defaults to the app setting)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
from pathlib import Path

import asyncpg

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import settings

from src.core.question_identity import stable_question_id

_QUIZ_RE = re.compile(r"^quiz_set_(\d+)_([a-z]{2})\.json$")
_VALID_DIFFICULTY = {"easy", "medium", "hard"}


def _iter_units(root: Path, only_curriculum: str | None):
    if not root.is_dir():
        return
    for cur_dir in sorted(root.iterdir()):
        if not cur_dir.is_dir():
            continue
        if only_curriculum and cur_dir.name != only_curriculum:
            continue
        for unit_dir in sorted(cur_dir.iterdir()):
            if unit_dir.is_dir():
                yield cur_dir.name, unit_dir.name, unit_dir


def _collect(root: Path, only_curriculum: str | None, langs: set[str]) -> tuple[list[dict], dict]:
    """Read every quiz set and reduce it to one row per distinct question."""
    rows: dict[str, dict] = {}
    stats = {
        "files": 0,
        "questions": 0,
        "placeholder_files": 0,
        "units": 0,
        "no_difficulty": 0,
        "unreadable_files": 0,
    }

    for curriculum_id, unit_id, unit_dir in _iter_units(root, only_curriculum):
        saw_unit = False
        for path in sorted(unit_dir.iterdir()):
            m = _QUIZ_RE.match(path.name)
            if not m:
                continue
            set_number, lang = int(m.group(1)), m.group(2)
            if lang not in langs:
                continue
            try:
                body = json.loads(path.read_text())
            except Exception as exc:
                # Counted and reported, not swallowed. A malformed quiz file
                # would otherwise shrink a unit's pool silently — the operator
                # would see a smaller number with no reason given.
                stats["unreadable_files"] += 1
                print(f"  WARNING unreadable, skipped: {path.name} ({type(exc).__name__})")
                continue

            # Placeholder content is refused at serve time (pitfall #36), so
            # registering it would build a pool of questions no student can ever
            # be shown.
            if (body.get("model") or "") == "dev-placeholder":
                stats["placeholder_files"] += 1
                continue

            stats["files"] += 1
            saw_unit = True
            for q in body.get("questions") or []:
                stem = (q.get("question_text") or "").strip()
                if not stem:
                    continue
                stats["questions"] += 1
                qid = stable_question_id(curriculum_id, unit_id, lang, stem)
                difficulty = (q.get("difficulty") or "").strip().lower() or None
                if difficulty not in _VALID_DIFFICULTY:
                    if difficulty is not None:
                        stats["no_difficulty"] += 1
                    difficulty = None

                # First writer wins for provenance, so `source_set` records where
                # the question was FIRST seen rather than wherever the loop
                # happened to end. Difficulty is allowed to fill in later if the
                # earliest copy lacked it.
                existing = rows.get(qid)
                if existing is None:
                    rows[qid] = {
                        "stable_question_id": qid,
                        "curriculum_id": curriculum_id,
                        "unit_id": unit_id,
                        "lang": lang,
                        "difficulty": difficulty,
                        "source_set": set_number,
                    }
                elif existing["difficulty"] is None and difficulty is not None:
                    existing["difficulty"] = difficulty
        if saw_unit:
            stats["units"] += 1

    return list(rows.values()), stats


async def _write(rows: list[dict]) -> int:
    conn = await asyncpg.connect(settings.DATABASE_URL, statement_cache_size=0)
    try:
        await conn.execute("SET app.current_school_id = 'bypass'")
        # executemany, not a loop of execute(). The first draft issued one
        # round-trip per question — 7,124 of them on the current corpus, which
        # took minutes for a job meant to be re-run after every content
        # regeneration. Batched it is a few seconds.
        payload = [
            (
                r["stable_question_id"],
                r["curriculum_id"],
                r["unit_id"],
                r["lang"],
                r["difficulty"],
                r["source_set"],
            )
            for r in rows
        ]
        await conn.executemany(
            """
            INSERT INTO question_registry
                (stable_question_id, curriculum_id, unit_id, lang, difficulty, source_set)
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT (stable_question_id) DO UPDATE
                SET difficulty = EXCLUDED.difficulty,
                    source_set = COALESCE(question_registry.source_set, EXCLUDED.source_set)
            """,
            payload,
        )
        return len(payload)
    finally:
        await conn.close()


async def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true", help="report what would be written")
    ap.add_argument("--curriculum", help="restrict to one curriculum_id")
    ap.add_argument("--lang", default="en", help="comma-separated languages (default: en)")
    args = ap.parse_args()

    root = Path(os.environ.get("CONTENT_STORE_PATH", settings.CONTENT_STORE_PATH)) / "curricula"
    langs = {x.strip() for x in args.lang.split(",") if x.strip()}

    rows, stats = _collect(root, args.curriculum, langs)

    print(
        f"Scanned {stats['units']} units, {stats['files']} quiz files "
        f"({stats['placeholder_files']} placeholder files skipped)"
    )
    print(
        f"  {stats['questions']} questions read -> {len(rows)} distinct "
        f"({stats['questions'] - len(rows)} duplicates collapsed)"
    )
    if stats["unreadable_files"]:
        print(f"  {stats['unreadable_files']} file(s) could not be parsed — see warnings above")
    if stats["no_difficulty"]:
        print(f"  {stats['no_difficulty']} had an unrecognised difficulty; stored as NULL")

    by_diff: dict[str | None, int] = {}
    for r in rows:
        by_diff[r["difficulty"]] = by_diff.get(r["difficulty"], 0) + 1
    print(
        "  by difficulty:",
        {k or "none": v for k, v in sorted(by_diff.items(), key=lambda x: str(x[0]))},
    )

    if args.dry_run:
        print("Dry run — nothing written.")
        return

    written = await _write(rows)
    print(f"Upserted {written} registry row(s).")


if __name__ == "__main__":
    asyncio.run(main())
