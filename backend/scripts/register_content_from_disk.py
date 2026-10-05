"""
register_content_from_disk.py

Scans CONTENT_STORE_PATH/curricula/ and registers any curricula + units
that exist on disk but are missing from the DB. Idempotent.

Usage:
    DATABASE_URL=... CONTENT_STORE_PATH=... python scripts/register_content_from_disk.py
"""
from __future__ import annotations

import asyncio
import json
import os
import re
from pathlib import Path

import asyncpg

DB_URL = os.environ.get("DATABASE_URL", "postgresql://studybuddy:studybuddy@localhost:5432/studybuddy")
CONTENT_ROOT = Path(os.environ.get("CONTENT_STORE_PATH", "/tmp/studybuddy-content")) / "curricula"

# e.g. default-2026-g11 → grade 11, year 2026
CURRICULUM_RE = re.compile(r"default-(\d{4})-g(\d+)")


def _grade_from_id(curriculum_id: str) -> int | None:
    m = CURRICULUM_RE.search(curriculum_id)
    return int(m.group(2)) if m else None


def _year_from_id(curriculum_id: str) -> int:
    m = CURRICULUM_RE.search(curriculum_id)
    return int(m.group(1)) if m else 2026


def _unit_title(unit_dir: Path) -> str:
    lesson = unit_dir / "lesson_en.json"
    if lesson.exists():
        d = json.loads(lesson.read_text())
        return d.get("topic") or d.get("title") or unit_dir.name
    return unit_dir.name


def _unit_subject(unit_dir: Path) -> str:
    lesson = unit_dir / "lesson_en.json"
    if lesson.exists():
        d = json.loads(lesson.read_text())
        return d.get("subject") or unit_dir.name.rsplit("-", 1)[0]
    return unit_dir.name.rsplit("-", 1)[0]


async def main() -> None:
    conn = await asyncpg.connect(DB_URL)
    await conn.execute("SET app.current_school_id = 'bypass'")

    existing_curricula = {
        r["curriculum_id"]
        for r in await conn.fetch("SELECT curriculum_id FROM curricula")
    }
    existing_units = {
        (r["unit_id"], r["curriculum_id"])
        for r in await conn.fetch("SELECT unit_id, curriculum_id FROM curriculum_units")
    }

    for curr_dir in sorted(CONTENT_ROOT.iterdir()):
        if not curr_dir.is_dir():
            continue
        curriculum_id = curr_dir.name
        grade = _grade_from_id(curriculum_id)
        if grade is None:
            print(f"  skip {curriculum_id} (can't parse grade)")
            continue
        year = _year_from_id(curriculum_id)

        if curriculum_id not in existing_curricula:
            name = f"Grade {grade} Default Curriculum {year}"
            await conn.execute("""
                INSERT INTO curricula (curriculum_id, grade, year, name, is_default,
                                       source_type, status, owner_type)
                VALUES ($1, $2, $3, $4, true, 'default', 'active', 'platform')
                ON CONFLICT (curriculum_id) DO NOTHING
            """, curriculum_id, grade, year, name)
            print(f"  created curriculum  {curriculum_id}")
        else:
            print(f"  exists  curriculum  {curriculum_id}")

        unit_dirs = sorted(
            d for d in curr_dir.iterdir()
            if d.is_dir() and (d / "meta.json").exists()
        )
        new_units = 0
        for unit_dir in unit_dirs:
            unit_id = unit_dir.name
            if (unit_id, curriculum_id) in existing_units:
                continue
            title = _unit_title(unit_dir)
            subject = _unit_subject(unit_dir)
            await conn.execute("""
                INSERT INTO curriculum_units
                    (unit_id, curriculum_id, subject, title, unit_name,
                     content_status, sort_order, objectives)
                VALUES ($1, $2, $3, $4, $4, 'built', 1, '{}')
                ON CONFLICT (unit_id, curriculum_id) DO NOTHING
            """, unit_id, curriculum_id, subject, title)
            new_units += 1

        if new_units:
            print(f"    registered {new_units} units")

    await conn.close()
    print("\nDone.")

asyncio.run(main())
