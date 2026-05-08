#!/usr/bin/env python3
"""scripts/doc_audit/run_all.py — orchestrator for the doc-audit toolkit.

Runs every checker module in `scripts/doc_audit/check_*.py`, aggregates
findings into a single JSON drift report, and prints a human-readable
summary to stderr.

Each checker exits 0 (clean) or 1 (drift). The orchestrator's exit code
mirrors the worst case:
  0 — every checker clean
  1 — at least one checker reported drift

Usage:
  python3 scripts/doc_audit/run_all.py                          # stdout JSON
  python3 scripts/doc_audit/run_all.py --out drift-report.json  # to file
  python3 scripts/doc_audit/run_all.py --skip test_counts       # skip slow checks

Closes acceptance criterion #6 of issue #337.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
DOC_AUDIT_DIR = Path(__file__).resolve().parent

# Checker module name → CLI args. Runs in this order.
CHECKERS: list[tuple[str, list[str]]] = [
    ("link_integrity", []),
    ("migrations_table", []),
    ("test_counts", []),
]


def run_checker(name: str, extra_args: list[str]) -> tuple[int, dict]:
    """Run a single checker, capture its JSON output and exit code."""
    script = DOC_AUDIT_DIR / f"check_{name}.py"
    if not script.exists():
        return 2, {
            "checker": name,
            "error": f"script not found: {script}",
            "total_findings": 0,
            "findings": [],
        }
    try:
        result = subprocess.run(
            ["python3", str(script), "--quiet", *extra_args],
            capture_output=True,
            text=True,
            timeout=300,
        )
    except subprocess.TimeoutExpired:
        return 2, {
            "checker": name,
            "error": "timed out after 300s",
            "total_findings": 0,
            "findings": [],
        }

    try:
        report = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        return 2, {
            "checker": name,
            "error": f"could not parse JSON output: {e}",
            "stdout_head": result.stdout[:400],
            "stderr_head": result.stderr[:400],
            "total_findings": 0,
            "findings": [],
        }

    return result.returncode, report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument(
        "--skip",
        action="append",
        default=[],
        help="Checker name to skip (e.g. test_counts). May repeat.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress the human-readable summary on stderr",
    )
    args = parser.parse_args()

    started_at = datetime.now(tz=timezone.utc).isoformat()
    aggregated: dict = {
        "doc_audit_run": True,
        "started_at": started_at,
        "checkers_run": [],
        "checkers_skipped": list(args.skip),
        "total_findings": 0,
        "by_checker": {},
        "findings": [],
    }

    worst_exit = 0

    for name, extra in CHECKERS:
        if name in args.skip:
            continue
        rc, report = run_checker(name, extra)
        worst_exit = max(worst_exit, rc)
        aggregated["checkers_run"].append(name)
        aggregated["by_checker"][name] = {
            "exit_code": rc,
            "total_findings": report.get("total_findings", 0),
            "by_kind": report.get("by_kind", {}),
            "summary": _summary_for(name, report),
        }
        for f in report.get("findings", []):
            aggregated["findings"].append({"checker": name, **f})
        aggregated["total_findings"] += report.get("total_findings", 0)

    aggregated["finished_at"] = datetime.now(tz=timezone.utc).isoformat()
    aggregated["worst_exit_code"] = worst_exit

    out_text = json.dumps(aggregated, indent=2)
    if args.out:
        args.out.write_text(out_text, encoding="utf-8")
    else:
        print(out_text)

    if not args.quiet:
        print(file=sys.stderr)
        print(
            f"doc-audit: {aggregated['total_findings']} findings across "
            f"{len(aggregated['checkers_run'])} checker(s)",
            file=sys.stderr,
        )
        for name, info in aggregated["by_checker"].items():
            print(
                f"  {name:20s}  exit={info['exit_code']:1d}  "
                f"findings={info['total_findings']:3d}  {info['summary']}",
                file=sys.stderr,
            )
        if args.skip:
            print(f"  skipped: {', '.join(args.skip)}", file=sys.stderr)

    return worst_exit


def _summary_for(name: str, report: dict) -> str:
    """Per-checker one-line summary for the orchestrator's stderr printout."""
    if name == "test_counts":
        c = report.get("claimed")
        a = report.get("actual")
        if c is None and a is None:
            return "no claim, no actual"
        if a is None:
            return f"claimed={c} actual=unverifiable"
        return f"claimed={c} actual={a} delta={a - c if c else 'n/a'}"
    if name == "migrations_table":
        return (
            f"fs={report.get('filesystem_count', '?')} "
            f"claimed={report.get('claimed_count', '?')}"
        )
    if name == "link_integrity":
        return f"docs_checked={report.get('docs_checked', '?')}"
    return ""


if __name__ == "__main__":
    sys.exit(main())
