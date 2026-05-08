#!/usr/bin/env python3
"""scripts/doc_audit/check_test_counts.py — drift checker.

Compares backend test count claims in `CLAUDE.md` against the actual
count produced by `pytest --collect-only`.

Two-step flow:

1. Extract the claimed count from CLAUDE.md. The doc carries a phrase
   like "914 total" inside a parenthetical describing the most recent
   epic. We anchor on `(<NUMBER> total;` patterns.

2. Try to count actual tests by:
   a. running `python3 -m pytest --collect-only -q` locally (fast path
      if deps are installed)
   b. falling back to `docker compose exec -T api python -m pytest
      --collect-only -q` (slower but works in the dev stack)
   c. if both fail, report "unable to verify" without erroring — drift
      checking is a soft signal, not a release gate.

Drift threshold: by default the checker tolerates ±5 tests of slop. Above
that it flags. Tune via --tolerance.

Closes acceptance criterion #2 of issue #337.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
CLAUDE_MD = REPO / "CLAUDE.md"

# Match "(914 total" or "(914 total;" or "(914 total in".
CLAIM_RE = re.compile(r"\((\d+)\s+total\b")

# Final pytest summary line: "======= 1002 tests collected in 1.18s ======="
COLLECT_RE = re.compile(r"(\d+)\s+tests?\s+collected")


def extract_claim() -> int | None:
    """Pull the most recent 'NNN total' claim from CLAUDE.md."""
    text = CLAUDE_MD.read_text(encoding="utf-8")
    matches = CLAIM_RE.findall(text)
    if not matches:
        return None
    # The last claim in document order is the freshest.
    return int(matches[-1])


def count_tests_local() -> int | None:
    """Run pytest --collect-only locally; None if it fails for any reason."""
    try:
        result = subprocess.run(
            ["python3", "-m", "pytest", "--collect-only", "-q"],
            cwd=REPO / "backend",
            capture_output=True,
            text=True,
            timeout=180,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    return _parse_collect_output(result.stdout + result.stderr)


def count_tests_docker() -> int | None:
    """Run pytest --collect-only via `docker compose exec api`."""
    try:
        result = subprocess.run(
            [
                "docker",
                "compose",
                "exec",
                "-T",
                "api",
                "python",
                "-m",
                "pytest",
                "--collect-only",
                "-q",
            ],
            cwd=REPO,
            capture_output=True,
            text=True,
            timeout=180,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    return _parse_collect_output(result.stdout + result.stderr)


def _parse_collect_output(output: str) -> int | None:
    m = COLLECT_RE.search(output)
    return int(m.group(1)) if m else None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument(
        "--tolerance",
        type=int,
        default=5,
        help="±N tests of drift before flagging (default 5)",
    )
    parser.add_argument(
        "--actual",
        type=int,
        default=None,
        help="Skip pytest, use this count instead (CI may pre-collect to "
        "save time)",
    )
    args = parser.parse_args()

    claimed = extract_claim()
    if args.actual is not None:
        actual = args.actual
        method = "supplied"
    else:
        # Try docker first — more reliable than local pytest given that
        # the dev stack uses docker for the backend env.
        actual = count_tests_docker()
        method = "docker"
        if actual is None:
            actual = count_tests_local()
            method = "local"
        if actual is None:
            method = "none"

    findings: list[dict] = []
    if claimed is None:
        findings.append(
            {
                "kind": "no_claim_in_doc",
                "hint": "CLAUDE.md should carry a phrase like '(914 total; 0 failing)'.",
            }
        )
    elif actual is None:
        findings.append(
            {
                "kind": "unable_to_verify",
                "claimed": claimed,
                "hint": "pytest --collect-only failed both locally and via "
                "docker compose. Check that the dev stack is up.",
            }
        )
    else:
        delta = actual - claimed
        if abs(delta) > args.tolerance:
            findings.append(
                {
                    "kind": "test_count_drift",
                    "claimed": claimed,
                    "actual": actual,
                    "delta": delta,
                    "tolerance": args.tolerance,
                    "method": method,
                    "hint": (
                        f"Update CLAUDE.md's '{claimed} total' claim to "
                        f"'{actual} total' or add a per-test reason for the gap."
                    ),
                }
            )

    report = {
        "checker": "test_counts",
        "claimed": claimed,
        "actual": actual,
        "method": method,
        "tolerance": args.tolerance,
        "total_findings": len(findings),
        "findings": findings,
    }

    out_text = json.dumps(report, indent=2)
    if args.out:
        args.out.write_text(out_text, encoding="utf-8")
    else:
        print(out_text)

    if not args.quiet:
        if claimed is None:
            print("test-counts: no claim in CLAUDE.md", file=sys.stderr)
        elif actual is None:
            print(
                f"test-counts: claimed={claimed} actual=unverifiable",
                file=sys.stderr,
            )
        else:
            print(
                f"test-counts: claimed={claimed} actual={actual} "
                f"delta={actual - claimed} (via {method})",
                file=sys.stderr,
            )

    return 0 if not findings else 1


if __name__ == "__main__":
    sys.exit(main())
