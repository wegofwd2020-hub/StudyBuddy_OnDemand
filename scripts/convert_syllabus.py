#!/usr/bin/env python3
"""
convert_syllabus.py — convert a CBSE (or similarly structured) syllabus JSON
into the grade{N}_stem.json format the StudyBuddy pipeline consumes.

Input format (CBSE example):
  {
    "metadata": {...},
    "syllabus": [
      {
        "code": "042",
        "name": "Physics",
        "class_level": "XI",      # or "XII"
        "stream": "Science",      # or "Commerce", "Humanities"
        "units": [
          {
            "unit_number": 1,
            "title": "Physical World & Measurement",
            "topics": ["Physical World", "Units and Measurements"],
            "marks": 23
          },
          ...
        ]
      },
      ...
    ]
  }

Output format (one file per grade):
  {
    "grade": 11,
    "subjects": [
      {
        "subject_id": "G11-PHYS",
        "name": "Physics",
        "units": [
          {
            "unit_id": "G11-PHYS-001",
            "title": "Physical World & Measurement",
            "description": "Physical World. Units and Measurements.",
            "has_lab": true
          },
          ...
        ]
      },
      ...
    ]
  }

Usage:
  # Default — Science stream only, write data/cbse_grade11_stem.json and data/cbse_grade12_stem.json
  python3 scripts/convert_syllabus.py --input ~/Downloads/cbse_syllabus.json

  # Include English Core in the output (CBSE lists it under Science)
  python3 scripts/convert_syllabus.py --input ... --include-english

  # Custom output directory + dry run
  python3 scripts/convert_syllabus.py --input ... --output-dir /tmp/syllabus --dry-run

  # All streams (includes Commerce + Humanities — not STEM)
  python3 scripts/convert_syllabus.py --input ... --streams Science,Commerce,Humanities
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

# Roman → Arabic for CBSE class_level. Extend if needed.
CLASS_LEVEL_TO_GRADE: dict[str, int] = {
    "V": 5, "VI": 6, "VII": 7, "VIII": 8, "IX": 9, "X": 10, "XI": 11, "XII": 12,
}

# Curated subject name → short code mapping. Anything not listed here falls back
# to an auto-generated 3–4 letter code from the first word (see _subject_code()).
SUBJECT_CODE_MAP: dict[str, str] = {
    "Physics": "PHYS",
    "Chemistry": "CHEM",
    "Biology": "BIO",
    "Mathematics": "MATH",
    "Math": "MATH",
    "Maths": "MATH",
    "Computer Science": "CS",
    "Computer Applications": "CS",
    "Informatics Practices": "IP",
    "English": "ENG",
    "English Core": "ENG",
    "Hindi": "HIN",
    "Sanskrit": "SAN",
    "Accountancy": "ACC",
    "Business Studies": "BUS",
    "Economics": "ECON",
    "History": "HIST",
    "Political Science": "POL",
    "Geography": "GEO",
    "Psychology": "PSY",
    "Sociology": "SOC",
    "Physical Education": "PE",
    "Environmental Science": "ENV",
}

# Subjects that get has_lab=true by default — experimental science with
# canonical laboratory practicals.
LAB_SUBJECTS: set[str] = {"PHYS", "CHEM", "BIO", "ENV", "CS"}


def _subject_code(name: str) -> str:
    """Fallback code for subjects not in SUBJECT_CODE_MAP."""
    # Take first word, strip non-alpha, uppercase, take up to 4 letters.
    first = re.sub(r"[^A-Za-z]", "", name.split()[0] if name.split() else name)
    return (first[:4] or "SUBJ").upper()


def _resolve_subject_code(name: str) -> str:
    # Try exact match first, then case-insensitive, then fallback.
    if name in SUBJECT_CODE_MAP:
        return SUBJECT_CODE_MAP[name]
    lower = {k.lower(): v for k, v in SUBJECT_CODE_MAP.items()}
    if name.lower() in lower:
        return lower[name.lower()]
    return _subject_code(name)


def _unit_description(topics: list[str]) -> str:
    """Turn CBSE topics into a pipeline-friendly description string."""
    cleaned = [t.strip() for t in topics if isinstance(t, str) and t.strip()]
    if not cleaned:
        return ""
    # Add a trailing period so rendering looks consistent.
    joined = ". ".join(cleaned)
    return joined if joined.endswith(".") else joined + "."


def _subject_to_output(subj: dict[str, Any], grade: int) -> dict[str, Any]:
    name = subj.get("name", "").strip() or "Unnamed"
    code = _resolve_subject_code(name)
    subject_id = f"G{grade}-{code}"
    has_lab_default = code in LAB_SUBJECTS

    out_units: list[dict[str, Any]] = []
    for u in subj.get("units", []):
        unit_num = u.get("unit_number")
        if not isinstance(unit_num, int):
            # Skip malformed units rather than crash — caller sees a warning.
            print(
                f"  warning: skipping unit without numeric unit_number in {subject_id}: {u.get('title')}",
                file=sys.stderr,
            )
            continue
        unit_id = f"G{grade}-{code}-{unit_num:03d}"
        title = (u.get("title") or "").strip() or f"Unit {unit_num}"
        topics = u.get("topics") or []
        description = _unit_description(topics)
        # Per-unit override if present in source; otherwise inherit subject default.
        has_lab = bool(u.get("has_lab", has_lab_default))

        out_units.append({
            "unit_id": unit_id,
            "title": title,
            "description": description,
            "has_lab": has_lab,
        })

    return {
        "subject_id": subject_id,
        "name": name,
        "units": out_units,
    }


def convert(
    source: dict[str, Any],
    streams: set[str],
    include_english: bool,
) -> dict[int, dict[str, Any]]:
    """
    Group source entries by grade and emit one pipeline-ready JSON per grade.

    Returns: {grade_int: grade_json}
    """
    groups: dict[int, list[dict[str, Any]]] = defaultdict(list)
    skipped: list[str] = []

    for entry in source.get("syllabus", []):
        class_level = entry.get("class_level")
        stream = entry.get("stream")
        name = entry.get("name", "")

        grade = CLASS_LEVEL_TO_GRADE.get(class_level)
        if grade is None:
            skipped.append(f"  {name}: unknown class_level '{class_level}'")
            continue

        if stream not in streams:
            skipped.append(f"  {name} (Grade {grade}): stream '{stream}' not in filter")
            continue

        # STEM guardrail: drop English Core unless caller asked for it.
        if not include_english and name.lower() in ("english", "english core"):
            skipped.append(f"  {name} (Grade {grade}): English excluded (use --include-english)")
            continue

        groups[grade].append(entry)

    if skipped:
        print("Skipped entries:", file=sys.stderr)
        for line in skipped:
            print(line, file=sys.stderr)

    out: dict[int, dict[str, Any]] = {}
    for grade, entries in sorted(groups.items()):
        subjects = [_subject_to_output(e, grade) for e in entries]
        out[grade] = {
            "grade": grade,
            "subjects": subjects,
        }
    return out


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--input", required=True, help="Path to source syllabus JSON")
    parser.add_argument(
        "--output-dir",
        default="data",
        help="Directory to write grade JSON files into (default: data/)",
    )
    parser.add_argument(
        "--output-prefix",
        default="cbse_",
        help=(
            "Prefix for output filenames. Default 'cbse_' produces "
            "cbse_grade11_stem.json. Use '' (empty) to overwrite grade{N}_stem.json."
        ),
    )
    parser.add_argument(
        "--suffix",
        default="stem",
        help=(
            "Suffix after grade number. Default 'stem' produces "
            "cbse_grade11_stem.json. Use 'commerce', 'humanities', 'english' etc. "
            "when generating files for non-Science streams so the filename "
            "reflects actual content."
        ),
    )
    parser.add_argument(
        "--streams",
        default="Science",
        help="Comma-separated streams to include (default: Science)",
    )
    parser.add_argument(
        "--include-english",
        action="store_true",
        help="Keep English Core even though it's not strictly STEM",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be written, make no files",
    )
    args = parser.parse_args()

    source_path = Path(args.input).expanduser().resolve()
    if not source_path.exists():
        raise SystemExit(f"error: input file not found: {source_path}")

    with source_path.open("r", encoding="utf-8") as f:
        source = json.load(f)

    streams = {s.strip() for s in args.streams.split(",") if s.strip()}
    grade_jsons = convert(source, streams=streams, include_english=args.include_english)

    if not grade_jsons:
        raise SystemExit("No grades matched the filter. Nothing to write.")

    out_dir = Path(args.output_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    for grade, data in grade_jsons.items():
        filename = f"{args.output_prefix}grade{grade}_{args.suffix}.json"
        dest = out_dir / filename

        unit_total = sum(len(s["units"]) for s in data["subjects"])
        subject_summary = ", ".join(
            f"{s['name']} ({len(s['units'])})" for s in data["subjects"]
        )
        print(
            f"Grade {grade}: {len(data['subjects'])} subjects, {unit_total} units — {subject_summary}"
        )

        if args.dry_run:
            print(f"  [dry-run] would write {dest}")
            continue

        with dest.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"  wrote {dest}")


if __name__ == "__main__":
    main()
