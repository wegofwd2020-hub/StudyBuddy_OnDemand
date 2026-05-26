#!/usr/bin/env python3
"""
Operator-run smoke test for the Curriculum Authoring Studio's TOC structurer
and flow analyzer — against a REAL LLM.

⚠️  Makes live Anthropic API calls and costs a few cents. It is deliberately
    NOT a pytest test and NOT wired into CI — CLAUDE.md forbids live external
    API calls in the test suite. Run it manually when you want to verify the
    prompts behave against a real model (the unit tests use fake providers).

Run:
    docker compose exec api python3 scripts/smoke_flow_analyzer.py
    # or on the host, from repo root, with ANTHROPIC_API_KEY set:
    #   python3 backend/scripts/smoke_flow_analyzer.py

What it checks:
    [1] structure_toc() turns a realistic free-text TOC into a sensible
        subjects → units → subtopics tree.
    [2] analyze_toc_flow() (LLM, advisory) flags a DELIBERATELY BROKEN TOC
        where a unit is taught before its prerequisite.
    [3] check_topic_ordering() (deterministic, no LLM) catches the same break.

Exit code: 0 = PASS, 2 = review needed, 1 = hard failure (structuring raised).
"""

from __future__ import annotations

import json
import os
import sys

# pipeline lives at repo root; backend/src is importable from backend/.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)
_BACKEND = os.path.join(_REPO_ROOT, "backend")
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

from pipeline.config import settings  # noqa: E402
from pipeline.flow_analyzer import analyze_toc_flow  # noqa: E402
from pipeline.providers import get_provider  # noqa: E402
from pipeline.toc_structurer import StructureError, structure_toc  # noqa: E402

from src.admin.authoring_flow import check_topic_ordering  # noqa: E402

RAW_TOC = """Chapter 1: Motion
  1.1 Distance and displacement
  1.2 Speed and velocity
  1.3 Acceleration
Chapter 2: Forces
  2.1 Newton's First Law
  2.2 Newton's Second Law (F = ma)
  2.3 Friction
Chapter 3: Energy
  3.1 Work
  3.2 Kinetic and potential energy
  3.3 Conservation of energy
"""

# Deliberately out of order: Acceleration (needs Velocity) is sequenced BEFORE
# Velocity; Conservation of energy is sequenced before Work.
BROKEN_TOC = {
    "subjects": [
        {
            "subject_label": "Physics",
            "units": [
                {
                    "title": "Acceleration",
                    "subtopics": ["average", "instantaneous"],
                    "prerequisites": ["Velocity"],
                },
                {"title": "Velocity", "subtopics": ["speed", "direction"], "prerequisites": []},
                {
                    "title": "Conservation of energy",
                    "subtopics": ["systems"],
                    "prerequisites": ["Work", "Kinetic energy"],
                },
                {"title": "Work", "subtopics": ["force x distance"], "prerequisites": []},
            ],
        }
    ]
}


def main() -> int:
    provider = get_provider(settings.DEFAULT_PROVIDER, settings)
    print(f"provider={settings.DEFAULT_PROVIDER} model={getattr(provider, 'model', '?')}\n")

    # [1] Structuring a realistic free-text TOC.
    print("=== [1] structure_toc() on a realistic free-text TOC ===")
    try:
        structured = structure_toc(RAW_TOC, grade=9, provider=provider)
    except StructureError as exc:
        print(f"STRUCTURE FAILED: {exc}")
        return 1
    print(json.dumps(structured.model_dump(), indent=2, ensure_ascii=False))
    n_units = sum(len(s.units) for s in structured.subjects)
    ok_struct = bool(structured.subjects) and n_units >= 3
    print(
        f"-> subjects={len(structured.subjects)} units={n_units} "
        f"{'OK' if ok_struct else 'WEAK — review'}\n"
    )

    # [2] LLM flow analysis on a deliberately broken TOC.
    print("=== [2] analyze_toc_flow() on a DELIBERATELY BROKEN TOC (prereq-after-use) ===")
    report = analyze_toc_flow(BROKEN_TOC, provider=provider)
    print(f"summary: {report.summary}")
    for w in report.warnings:
        print(f"  - [{w.kind}] unit={w.unit!r}: {w.detail}")
    ok_flow = len(report.warnings) > 0
    print(
        f"-> warnings={len(report.warnings)} "
        f"{'CAUGHT issue(s)' if ok_flow else 'MISSED — no warnings!'}\n"
    )

    # [3] Deterministic (no-LLM) ordering check on the same broken TOC.
    print("=== [3] check_topic_ordering() — deterministic, no LLM ===")
    det = check_topic_ordering(BROKEN_TOC)
    for w in det:
        print(f"  - [{w['kind']}] unit={w['unit']!r}")
    ok_det = any(w["kind"] == "prerequisite_after_use" for w in det)
    print(f"-> {'OK' if ok_det else 'FAILED — expected prerequisite_after_use'}\n")

    verdict = ok_struct and ok_flow and ok_det
    print(f"SMOKE VERDICT: {'PASS' if verdict else 'REVIEW NEEDED'}")
    return 0 if verdict else 2


if __name__ == "__main__":
    raise SystemExit(main())
