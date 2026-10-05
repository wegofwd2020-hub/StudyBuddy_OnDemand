"""
pipeline/validate_content.py

Validate content store integrity: JSON parseable, required fields present,
visual_hints populated for supported subjects.

Usage:
    python3 pipeline/validate_content.py
    python3 pipeline/validate_content.py --curriculum-id default-2026-g11-science
    python3 pipeline/validate_content.py --grade 11 --stream science

Exit codes:
    0 — all checks passed
    1 — one or more validation errors found
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pipeline.config import settings

# Subjects that must have non-empty visual_hints
VISUAL_HINT_SUBJECTS = {
    "biology", "chemistry", "physics", "mathematics",
    "commerce", "economics", "accounting", "business",
    "history", "geography", "political science", "psychology",
}

REQUIRED_LESSON_FIELDS = {"topic", "sections", "key_points", "visual_hints"}
REQUIRED_SECTION_FIELDS = {"heading", "body"}
REQUIRED_META_FIELDS = {"generated_at", "content_version", "langs_built"}


def _subject_needs_hints(unit_id: str) -> bool:
    """Infer subject from unit_id code (e.g. G11-BIO-001 → biology)."""
    code_map = {
        "BIO": "biology", "CHEM": "chemistry", "PHYS": "physics",
        "MATH": "mathematics", "HIST": "history", "GEO": "geography",
        "POL": "political science", "PSY": "psychology",
        "ACC": "accounting", "ECON": "economics", "BUS": "business",
    }
    parts = unit_id.upper().split("-")
    if len(parts) >= 2:
        code = parts[1]
        subject = code_map.get(code, "").lower()
        return subject in VISUAL_HINT_SUBJECTS
    return False


def validate_unit(unit_dir: Path) -> list[str]:
    errors = []
    unit_id = unit_dir.name

    # meta.json
    meta_path = unit_dir / "meta.json"
    if not meta_path.exists():
        errors.append(f"{unit_id}: missing meta.json")
    else:
        try:
            meta = json.loads(meta_path.read_text())
            for f in REQUIRED_META_FIELDS:
                if f not in meta:
                    errors.append(f"{unit_id}: meta.json missing field '{f}'")
        except json.JSONDecodeError as e:
            errors.append(f"{unit_id}: meta.json invalid JSON — {e}")

    # lesson_en.json
    lesson_path = unit_dir / "lesson_en.json"
    if not lesson_path.exists():
        errors.append(f"{unit_id}: missing lesson_en.json")
    else:
        try:
            lesson = json.loads(lesson_path.read_text())
            for f in REQUIRED_LESSON_FIELDS:
                if f not in lesson:
                    errors.append(f"{unit_id}: lesson_en.json missing field '{f}'")
            for i, sec in enumerate(lesson.get("sections", [])):
                for sf in REQUIRED_SECTION_FIELDS:
                    if sf not in sec:
                        errors.append(f"{unit_id}: section[{i}] missing field '{sf}'")
            hints = lesson.get("visual_hints") or []
            if _subject_needs_hints(unit_id) and not hints:
                errors.append(f"{unit_id}: visual_hints empty (subject requires hints)")
            for j, h in enumerate(hints):
                for hf in ("query", "caption", "placement"):
                    if not h.get(hf):
                        errors.append(f"{unit_id}: visual_hints[{j}] missing '{hf}'")
        except json.JSONDecodeError as e:
            errors.append(f"{unit_id}: lesson_en.json invalid JSON — {e}")

    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate content store integrity")
    parser.add_argument("--curriculum-id", default=None, help="Validate one curriculum")
    parser.add_argument("--grade", type=int, default=None, help="Filter by grade")
    parser.add_argument("--stream", default=None, help="Filter by stream (e.g. science)")
    args = parser.parse_args()

    store = Path(settings.CONTENT_STORE_PATH)
    curricula_dir = store / "curricula"
    if not curricula_dir.exists():
        print(f"ERROR: curricula directory not found: {curricula_dir}", file=sys.stderr)
        sys.exit(1)

    # Collect curricula to validate
    all_curricula = sorted(p for p in curricula_dir.iterdir() if p.is_dir())
    if args.curriculum_id:
        all_curricula = [p for p in all_curricula if p.name == args.curriculum_id]
    else:
        if args.grade:
            all_curricula = [p for p in all_curricula if f"-g{args.grade}" in p.name or f"-g{args.grade}-" in p.name]
        if args.stream:
            all_curricula = [p for p in all_curricula if args.stream.lower() in p.name.lower()]

    if not all_curricula:
        print("No curricula matched the filter.", file=sys.stderr)
        sys.exit(1)

    total_units = 0
    total_errors = 0

    for curriculum in all_curricula:
        units = sorted(p for p in curriculum.iterdir() if p.is_dir())
        c_errors = []
        for unit_dir in units:
            unit_errors = validate_unit(unit_dir)
            c_errors.extend(unit_errors)
        total_units += len(units)
        total_errors += len(c_errors)
        status = "✅" if not c_errors else "❌"
        print(f"{status} {curriculum.name}: {len(units)} units, {len(c_errors)} errors")
        for e in c_errors:
            print(f"     {e}")

    print()
    print(f"Total: {total_units} units, {total_errors} errors")
    sys.exit(0 if total_errors == 0 else 1)


if __name__ == "__main__":
    main()
