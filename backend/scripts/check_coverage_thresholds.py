#!/usr/bin/env python3
"""
backend/scripts/check_coverage_thresholds.py

Enforce per-module coverage thresholds against a coverage.json report.

The JSON report is produced by pytest with --cov-report=json:
  pytest tests/ --cov=src --cov-report=json

Usage:
  python scripts/check_coverage_thresholds.py [path/to/coverage.json]

Default path: coverage.json (relative to cwd, i.e. the backend/ directory).

Exit codes:
  0 — all thresholds met
  1 — one or more thresholds not met (details printed to stdout)

Thresholds (per-module, aggregated over all .py files under that prefix):
  src/auth/                90%  — token flows, COPPA, suspension paths
  src/subscription/        90%  — Stripe webhook, plan transitions
  src/school/subscription  90%  — school billing, SCA handling
  src/content/             85%  — content serving, entitlement edge cases
  src/progress/            80%
  everything else          80%
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

# Longest-prefix-wins matching.  Key must NOT include a trailing slash.
THRESHOLDS: dict[str, int] = {
    "src/auth": 90,
    "src/subscription": 90,
    "src/school/subscription": 90,
    "src/content": 85,
    "src/progress": 80,
}
DEFAULT_THRESHOLD = 80


def _bucket(filepath: str) -> str:
    """Return the most-specific THRESHOLDS key that matches filepath, else 'default'."""
    fp = filepath.replace("\\", "/")
    best: str | None = None
    for prefix in THRESHOLDS:
        if not fp.startswith(prefix):
            continue
        # Accept the match only when the prefix ends on a real path/name boundary:
        #   '/'  — prefix is a directory  (src/auth/router.py)
        #   '_'  — prefix is a filename prefix within a dir (src/school/subscription_service.py)
        #   '.'  — prefix equals the bare module name (edge case)
        #   end  — exact match
        tail = fp[len(prefix):]
        if tail and tail[0] not in ("/", "_", "."):
            continue
        if best is None or len(prefix) > len(best):
            best = prefix
    return best or "default"


def main(report_path: str = "coverage.json") -> int:
    path = Path(report_path)
    if not path.exists():
        print(
            f"ERROR: {report_path} not found.\n"
            "Run pytest with --cov=src --cov-report=json to generate it.",
            file=sys.stderr,
        )
        return 1

    report = json.loads(path.read_text())
    files: dict[str, dict] = report.get("files", {})

    covered: dict[str, int] = defaultdict(int)
    total: dict[str, int] = defaultdict(int)

    for filepath, data in files.items():
        summary = data.get("summary", {})
        n_statements = summary.get("num_statements", 0)
        if n_statements == 0:
            continue
        n_covered = summary.get("covered_lines", 0)
        bkt = _bucket(filepath)
        covered[bkt] += n_covered
        total[bkt] += n_statements

    buckets_to_check: dict[str, int] = {**THRESHOLDS, "default": DEFAULT_THRESHOLD}

    print("Coverage threshold check:")
    failed: list[str] = []

    for bucket in sorted(buckets_to_check):
        threshold = buckets_to_check[bucket]
        n_total = total.get(bucket, 0)
        if n_total == 0:
            continue  # no files matched this prefix — nothing to enforce
        pct = 100.0 * covered[bucket] / n_total
        label = bucket if bucket != "default" else "everything else"
        status = "PASS" if pct >= threshold else "FAIL"
        print(f"  [{status}]  {label}: {pct:.1f}% (required {threshold}%)")
        if pct < threshold:
            failed.append(f"{label}: {pct:.1f}% < {threshold}%")

    if failed:
        print("\nCoverage threshold failures:")
        for msg in failed:
            print(f"  {msg}")
        return 1

    print("\nAll coverage thresholds passed.")
    return 0


if __name__ == "__main__":
    report_file = sys.argv[1] if len(sys.argv) > 1 else "coverage.json"
    sys.exit(main(report_file))
