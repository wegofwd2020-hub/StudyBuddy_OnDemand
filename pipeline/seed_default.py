"""
pipeline/seed_default.py

Seeds the curricula and curriculum_units tables with default content for
grades 5-12 from data/grade{N}_stem.json files.

Usage:
  python pipeline/seed_default.py --year 2026
  python pipeline/seed_default.py --year 2026 --grade 8  # single grade

Idempotent — uses ON CONFLICT DO UPDATE in seed_default_curriculum().
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys

# Allow running from repo root or pipeline/ directory.
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_THIS_DIR)
for _p in (_REPO_ROOT, os.path.join(_REPO_ROOT, "backend")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

_DATA_DIR = os.path.join(_REPO_ROOT, "data")

log = logging.getLogger("pipeline.seed_default")


def _load_units_from_json(grade: int, subject_name: str, subject_units: list) -> list:
    """Convert the data JSON unit list into upload_service format."""
    units = []
    for unit in subject_units:
        description = unit.get("description", "")
        # Use description as a single objective; pipeline will expand later.
        objectives = [description] if description else ["To be defined."]
        units.append({
            "unit_id": unit.get("unit_id", ""),
            "subject": subject_name,
            "unit_name": unit.get("title", unit.get("unit_id", "")),
            "objectives": objectives,
            "has_lab": bool(unit.get("has_lab", False)),
            "lab_description": unit.get("lab_description") or None,
        })
    return units


async def seed_grade(conn: object, grade: int, year: int) -> None:
    """Seed one grade's default curriculum and units from data/grade{N}_stem.json."""
    from backend.src.curriculum.upload_service import seed_default_curriculum  # noqa: PLC0415

    data_path = os.path.join(_DATA_DIR, f"grade{grade}_stem.json")
    if not os.path.exists(data_path):
        log.warning("seed_skip: %s not found", data_path)
        return

    with open(data_path, "r", encoding="utf-8") as f:
        grade_data = json.load(f)

    all_units: list = []
    for subject_block in grade_data.get("subjects", []):
        subject_name = subject_block.get("name", "Unknown")
        subject_units = subject_block.get("units", [])
        all_units.extend(_load_units_from_json(grade, subject_name, subject_units))

    if not all_units:
        log.warning("seed_skip: no units found in %s", data_path)
        return

    curriculum_id = await seed_default_curriculum(conn, grade, year, all_units)
    log.info("seeded grade=%d units=%d curriculum_id=%s", grade, len(all_units), curriculum_id)


async def seed_all(year: int, grades: list[int]) -> None:
    """Seed the requested grades."""
    import asyncpg  # noqa: PLC0415

    # Import pipeline config (DATABASE_URL lives there for pipeline context).
    try:
        sys.path.insert(0, _THIS_DIR)
        from config import settings as pipeline_cfg  # type: ignore
        db_url = pipeline_cfg.DATABASE_URL
    except Exception:
        db_url = os.environ.get("DATABASE_URL", "")

    if not db_url:
        raise RuntimeError("DATABASE_URL must be set (env var or pipeline/config.py)")

    conn = await asyncpg.connect(db_url)
    try:
        for grade in grades:
            await seed_grade(conn, grade, year)
        log.info("seed_complete year=%d grades=%s", year, grades)
    finally:
        await conn.close()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")

    parser = argparse.ArgumentParser(description="Seed default curricula (grades 5-12) into DB.")
    parser.add_argument("--year", type=int, default=2026, help="Curriculum year (default: 2026)")
    parser.add_argument(
        "--grade",
        type=int,
        default=None,
        help="Seed a single grade only (default: all grades 5-12)",
    )
    args = parser.parse_args()

    grades = [args.grade] if args.grade else list(range(5, 13))
    asyncio.run(seed_all(year=args.year, grades=grades))


if __name__ == "__main__":
    main()
