#!/usr/bin/env python3
"""
Operator-run smoke test for the Curriculum Authoring Studio — against a REAL LLM.

⚠️  Makes live Anthropic API calls and costs a few cents. It is deliberately
    NOT a pytest test and NOT wired into CI — CLAUDE.md forbids live external
    API calls in the test suite. Run it manually when you want to verify the
    prompts behave against a real model (the unit tests use fake providers).

Run:
    # Flow-analyzer + structurer smoke (default):
    docker compose exec api python3 scripts/smoke_flow_analyzer.py

    # Generation smoke — generate one real lesson and check the Mermaid block:
    docker compose exec api python3 scripts/smoke_flow_analyzer.py --generate

    # Both:
    docker compose exec api python3 scripts/smoke_flow_analyzer.py --all

    # On the host (from repo root) with ANTHROPIC_API_KEY set:
    #   python3 backend/scripts/smoke_flow_analyzer.py [--generate|--all]

Flow smoke checks:
    [1] structure_toc() turns a realistic free-text TOC into a sensible
        subjects → units → subtopics tree.
    [2] analyze_toc_flow() (LLM, advisory) flags a DELIBERATELY BROKEN TOC
        where a unit is taught before its prerequisite.
    [3] check_topic_ordering() (deterministic, no LLM) catches the same break.

Generation smoke checks:
    [G] generate_one() produces a schema-valid lesson for a diagram-worthy
        topic with diagram_emphasis ON, and the output embeds a renderable
        ```mermaid fenced block (the "too terse" → richer-visuals fix).

Exit code: 0 = PASS, 2 = review needed, 1 = hard failure.
"""

from __future__ import annotations

import argparse
import json
import os
import re
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
from src.admin.authoring_generation import GenerationError, generate_one  # noqa: E402

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

# Diagram-worthy topic: a cycle/process the model should render as a Mermaid
# flowchart when diagram_emphasis is on.
GEN_SUBJECT = "Natural Sciences"
GEN_TOPIC = "The Water Cycle"

# Mermaid diagram-type keywords a fenced block may start with.
_MERMAID_HEADS = (
    "graph",
    "flowchart",
    "sequenceDiagram",
    "classDiagram",
    "stateDiagram",
    "stateDiagram-v2",
    "erDiagram",
    "mindmap",
    "gantt",
    "pie",
    "journey",
)


def smoke_flow(provider) -> int:
    """Structurer + flow-analyzer smoke. Returns an exit code."""
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
    print(f"FLOW SMOKE VERDICT: {'PASS' if verdict else 'REVIEW NEEDED'}")
    return 0 if verdict else 2


def smoke_generate(provider) -> int:
    """Generate one real lesson with diagram emphasis and check the Mermaid block."""
    print(
        f"=== [G] generate_one(lesson) subject={GEN_SUBJECT!r} topic={GEN_TOPIC!r} "
        "(diagram_emphasis ON) ==="
    )
    try:
        # generate_one builds the lesson prompt with diagram_emphasis=True and
        # schema-validates the response before returning it.
        body, tokens = generate_one(
            provider,
            content_type="lesson",
            unit_id="SMOKE-WATER-001",
            subject=GEN_SUBJECT,
            topic=GEN_TOPIC,
            grade=9,
            lang="en",
        )
    except GenerationError as exc:
        print(f"GENERATION FAILED: {exc}")
        return 1

    sections = body.get("sections", [])
    full = "\n\n".join(s.get("body", "") for s in sections)
    print(
        f"schema-valid lesson: tokens={tokens} sections={len(sections)} "
        f"key_points={len(body.get('key_points', []))} "
        f"objectives={len(body.get('learning_objectives', []))}"
    )

    # Mermaid presence + basic shape check (true visual rendering is covered by
    # the web vitest test for SBMarkdown + MermaidDiagram).
    blocks = re.findall(r"```mermaid\s*\n(.*?)```", full, re.DOTALL)
    if blocks:
        first = blocks[0].strip()
        head = first.splitlines()[0].strip() if first else ""
        shape_ok = any(head.startswith(k) for k in _MERMAID_HEADS)
        print(
            f"-> MERMAID FOUND: {len(blocks)} block(s); first starts with {head!r} "
            f"{'OK' if shape_ok else 'UNRECOGNISED TYPE — review'}"
        )
        print("----- first mermaid block -----")
        print(first[:800])
        print("-------------------------------")
        ok_mermaid = shape_ok
    else:
        print(
            "-> NO ```mermaid block emitted. Either the model judged none needed "
            "for this topic, or the diagram_emphasis prompt needs strengthening — "
            "inspect the lesson below."
        )
        ok_mermaid = False

    print(f"\nsynopsis: {body.get('synopsis', '')}")
    print(f"\nGENERATE SMOKE VERDICT: {'PASS' if ok_mermaid else 'REVIEW NEEDED'}")
    return 0 if ok_mermaid else 2


def main() -> int:
    parser = argparse.ArgumentParser(description="Authoring Studio real-LLM smoke test.")
    parser.add_argument(
        "--generate",
        action="store_true",
        help="Run the generation smoke (real lesson + Mermaid check) instead of the flow smoke.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run both the flow smoke and the generation smoke.",
    )
    args = parser.parse_args()

    provider = get_provider(settings.DEFAULT_PROVIDER, settings)
    print(f"provider={settings.DEFAULT_PROVIDER} model={getattr(provider, 'model', '?')}\n")

    codes: list[int] = []
    if args.all or not args.generate:
        codes.append(smoke_flow(provider))
        if args.all:
            print()
    if args.all or args.generate:
        codes.append(smoke_generate(provider))

    # Worst (highest) exit code wins: 1 hard-fail > 2 review > 0 pass... but we
    # want 1 to dominate 2, and both to dominate 0. Map: 1>2>0.
    if 1 in codes:
        return 1
    if 2 in codes:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
