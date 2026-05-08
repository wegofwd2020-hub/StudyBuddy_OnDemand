#!/usr/bin/env python3
"""scripts/doc_audit/check_migrations_table.py — drift checker.

Compares the filesystem state of `backend/alembic/versions/*.py` against
the "Current migrations" table in `CLAUDE.md`. Surfaces three classes of
drift:

1. **Filesystem-but-not-claimed** — a migration file exists on disk but
   no row in CLAUDE.md mentions its number. Common when a migration
   shipped after the doc table was last updated.

2. **Claimed-but-missing** — a row in CLAUDE.md references a migration
   number that has no file on disk. Common after a migration is
   reverted/squashed without doc cleanup.

3. **Numbering gaps** — non-contiguous migration numbers on disk
   (e.g. 0048 → 0050 with no 0049). Usually intentional (squashed
   draft); flagged so the operator can confirm.

Emits JSON to stdout (or --out); summary to stderr. Exit 0 on clean,
1 on drift.

Closes acceptance criterion #1 of issue #337.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
ALEMBIC_DIR = REPO / "backend" / "alembic" / "versions"
CLAUDE_MD = REPO / "CLAUDE.md"

# Filename pattern: 0001_phase1_initial_schema.py
ALEMBIC_FILE_RE = re.compile(r"^(\d{4})_(.+)\.py$")

# Markdown table row pattern: `| 0024 | description... |`
# Also handles ranges like `| 0001–0011 |` (en-dash) and `| 0001-0011 |` (hyphen).
TABLE_ROW_SINGLE = re.compile(r"^\|\s*(\d{4})\s*\|\s*(.+?)\s*\|\s*$")
TABLE_ROW_RANGE = re.compile(r"^\|\s*(\d{4})[-–](\d{4})\s*\|\s*(.+?)\s*\|\s*$")


def collect_filesystem_migrations() -> dict[int, str]:
    """Return {migration_number: filename} from backend/alembic/versions/."""
    migrations: dict[int, str] = {}
    for p in sorted(ALEMBIC_DIR.glob("*.py")):
        m = ALEMBIC_FILE_RE.match(p.name)
        if not m:
            continue
        num = int(m.group(1))
        migrations[num] = p.name
    return migrations


def collect_claimed_migrations() -> tuple[set[int], list[tuple[int, int, str]]]:
    """Parse CLAUDE.md's migration table.

    Returns (claimed_numbers, ranges) where:
      - claimed_numbers is a set of every migration number covered
      - ranges is a list of (lo, hi, description) triples for ranges,
        useful for checking range completeness against the filesystem
    """
    text = CLAUDE_MD.read_text(encoding="utf-8")

    # Locate the migration table by anchoring on its header row.
    # The table starts with a row containing "| # | Description |" and
    # continues until we hit a non-table line.
    in_table = False
    claimed: set[int] = set()
    ranges: list[tuple[int, int, str]] = []
    for line in text.splitlines():
        if "| # | Description |" in line:
            in_table = True
            continue
        if not in_table:
            continue
        # The separator row `|---|---|`
        if re.match(r"^\|[-: |]+\|\s*$", line):
            continue
        # Blank line or non-pipe line ends the table.
        if not line.startswith("|"):
            in_table = False
            continue

        m = TABLE_ROW_RANGE.match(line)
        if m:
            lo, hi, desc = int(m.group(1)), int(m.group(2)), m.group(3)
            for n in range(lo, hi + 1):
                claimed.add(n)
            ranges.append((lo, hi, desc))
            continue
        m = TABLE_ROW_SINGLE.match(line)
        if m:
            claimed.add(int(m.group(1)))
            continue
        # Unparseable in-table row — likely the table is over.
        in_table = False

    return claimed, ranges


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    fs = collect_filesystem_migrations()
    claimed, _ranges = collect_claimed_migrations()

    fs_nums = set(fs.keys())

    fs_but_not_claimed = sorted(fs_nums - claimed)
    claimed_but_missing = sorted(claimed - fs_nums)

    # Numbering gaps on the filesystem
    gaps: list[tuple[int, int]] = []
    if fs_nums:
        all_nums = sorted(fs_nums)
        for prev, cur in zip(all_nums, all_nums[1:]):
            if cur - prev > 1:
                gaps.append((prev, cur))

    findings: list[dict] = []
    for n in fs_but_not_claimed:
        findings.append(
            {
                "kind": "filesystem_but_not_claimed",
                "migration": f"{n:04d}",
                "filename": fs[n],
                "hint": "Add a row to CLAUDE.md's migration table.",
            }
        )
    for n in claimed_but_missing:
        findings.append(
            {
                "kind": "claimed_but_missing",
                "migration": f"{n:04d}",
                "hint": "Remove the row from CLAUDE.md or restore the migration.",
            }
        )
    for prev, cur in gaps:
        findings.append(
            {
                "kind": "numbering_gap",
                "between": [f"{prev:04d}", f"{cur:04d}"],
                "missing_count": cur - prev - 1,
                "hint": "Confirm the gap is intentional (squashed/reverted).",
            }
        )

    report = {
        "checker": "migrations_table",
        "filesystem_count": len(fs_nums),
        "claimed_count": len(claimed),
        "total_findings": len(findings),
        "by_kind": {
            "filesystem_but_not_claimed": len(fs_but_not_claimed),
            "claimed_but_missing": len(claimed_but_missing),
            "numbering_gap": len(gaps),
        },
        "findings": findings,
    }

    out_text = json.dumps(report, indent=2)
    if args.out:
        args.out.write_text(out_text, encoding="utf-8")
    else:
        print(out_text)

    if not args.quiet:
        print(
            f"\nmigrations-table: filesystem={len(fs_nums)} "
            f"claimed={len(claimed)} findings={len(findings)}",
            file=sys.stderr,
        )
        for k, v in report["by_kind"].items():
            print(f"  {k:32s}  {v}", file=sys.stderr)

    return 0 if not findings else 1


if __name__ == "__main__":
    sys.exit(main())
