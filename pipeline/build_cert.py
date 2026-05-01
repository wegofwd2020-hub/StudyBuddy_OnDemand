"""
pipeline/build_cert.py

CLI to build content for a certification (or any non-numeric-grade) curriculum JSON.

Reads the curriculum JSON, iterates over every subject → unit, and calls
build_unit() for each one. Works identically to build_grade.py but accepts
curricula where the grade field is a string rather than an integer.

Usage:
  python pipeline/build_cert.py \\
      --curriculum-file data/cert_claude_architect_foundations.json \\
      --curriculum-id  cert-architect-foundations-2026 \\
      --lang en \\
      [--force] [--dry-run] [--provider anthropic]
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from pipeline.build_unit import SpendCapExceeded, build_unit

log = logging.getLogger("pipeline.build_cert")


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    parser = argparse.ArgumentParser(
        description="Build content for a certification curriculum JSON."
    )
    parser.add_argument(
        "--curriculum-file",
        required=True,
        help="Path to the curriculum JSON file, e.g. data/cert_claude_architect_foundations.json",
    )
    parser.add_argument(
        "--curriculum-id",
        required=True,
        help="Curriculum ID to use as the content-store key, e.g. cert-architect-foundations-2026",
    )
    parser.add_argument(
        "--lang",
        default="en",
        help="Language code (default: en)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Rebuild even if content already exists",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Log what would be done without calling the LLM",
    )
    parser.add_argument(
        "--provider",
        default=None,
        help="LLM provider: anthropic (default) | openai | google",
    )
    args = parser.parse_args()

    curriculum_file = os.path.join(_REPO_ROOT, args.curriculum_file) \
        if not os.path.isabs(args.curriculum_file) else args.curriculum_file

    if not os.path.exists(curriculum_file):
        log.error("curriculum_file_not_found path=%s", curriculum_file)
        sys.exit(1)

    with open(curriculum_file, encoding="utf-8") as f:
        curriculum = json.load(f)

    grade = curriculum.get("grade", "cert")
    subjects = curriculum.get("subjects", [])

    total_units = sum(len(s.get("units", [])) for s in subjects)
    log.info(
        "build_cert_start curriculum_id=%s lang=%s subjects=%d units=%d",
        args.curriculum_id, args.lang, len(subjects), total_units,
    )

    from pipeline.config import settings as config  # imported late to respect env setup

    completed = 0
    skipped = 0
    failed: list[str] = []
    start_total = time.monotonic()

    for subject in subjects:
        subject_name = subject.get("name", "")
        for unit in subject.get("units", []):
            unit_id = unit["unit_id"]
            unit_data = {
                "title": unit.get("title", unit_id),
                "description": unit.get("description", ""),
                "subject": subject_name,
                "has_lab": unit.get("has_lab", False),
                "grade": grade,
                "num_quiz_sets": unit.get("num_quiz_sets", 3),
            }

            try:
                result = build_unit(
                    curriculum_id=args.curriculum_id,
                    unit_id=unit_id,
                    unit_data=unit_data,
                    lang=args.lang,
                    config=config,
                    force=args.force,
                    dry_run=args.dry_run,
                    provider_id=args.provider,
                )
                status = result.get("status", "unknown")
                if status == "skipped":
                    skipped += 1
                else:
                    completed += 1
                log.info(
                    "unit_done %d/%d unit_id=%s status=%s tokens=%s cost=$%.4f",
                    completed + skipped + len(failed),
                    total_units,
                    unit_id,
                    status,
                    result.get("tokens_used", 0),
                    result.get("cost_usd", 0.0),
                )

            except SpendCapExceeded as exc:
                log.error("spend_cap_exceeded unit_id=%s error=%s", unit_id, exc)
                sys.exit(1)
            except Exception as exc:  # noqa: BLE001
                log.error("unit_error unit_id=%s error=%s", unit_id, exc)
                failed.append(unit_id)

    elapsed = time.monotonic() - start_total
    log.info(
        "build_cert_complete curriculum_id=%s lang=%s "
        "completed=%d skipped=%d failed=%d elapsed_s=%.1f",
        args.curriculum_id, args.lang,
        completed, skipped, len(failed), elapsed,
    )

    if failed:
        log.warning("failed_units=%s", failed)
        sys.exit(1)


if __name__ == "__main__":
    main()
