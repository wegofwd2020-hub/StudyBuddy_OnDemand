#!/usr/bin/env python3
"""scripts/doc_audit/check_link_integrity.py — drift checker.

Walks all `*.md` files in the repo (excluding vendor/build paths) and
validates two classes of links:

1. **Markdown links** like `[label](path/to/file.md)` and
   `[label](path#anchor)`. The relative target must resolve to a real file
   inside the repo. External URLs (http://, https://, mailto:) are skipped.

2. **Inline code-path references** — bare paths like `backend/src/foo.py`,
   `pipeline/build_grade.py`, `scripts/seed.ts` mentioned in prose or in
   inline backtick code. The path must exist as a file or directory.

Emits a JSON report to stdout (or to --out if provided), plus a
human-readable summary to stderr.

Exit codes:
  0 — no drift
  1 — drift detected (broken links or missing code paths)

Closes acceptance criteria #3 + #4 of issue #337.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Iterator

REPO = Path(__file__).resolve().parent.parent.parent

# Directories to skip when walking *.md. Vendor + build + binary trees.
SKIP_DIRS = {
    "node_modules",
    ".venv",
    "venv",
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".next",
    "dist",
    "build",
    ".cache",
    "sample_content",  # massive, unrelated to doc-integrity
}

# Markdown link regex: [label](target) where target starts with / or ./ or
# alphabetic char (relative path) and is NOT an external URL. Group 1 is
# the label (unused here), group 2 is the target.
MD_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")

# Inline-code path regex — matches bare paths like `backend/src/foo.py` or
# `pipeline/build_grade.py` inside backticks. The path must contain at
# least one `/` (otherwise too noisy) and end in a recognised extension or
# be a known directory pattern.
INLINE_PATH_RE = re.compile(
    r"`(([\w.-]+/)+[\w.-]+)`"
)

# Prose-mention regex — matches paths NOT inside backticks. Tighter:
# require a known top-level directory prefix to avoid false positives on
# every slash-containing string. Top-level dirs in the repo + common
# subpaths the docs reference.
PROSE_PATH_RE = re.compile(
    r"(?<!`)(?<!\w)("
    r"backend/[\w./-]+"
    r"|pipeline/[\w./-]+"
    r"|scripts/[\w./-]+"
    r"|web/[\w./-]+"
    r"|mobile/[\w./-]+"
    r"|data/[\w./-]+"
    r"|docs/[\w./-]+"
    r"|sample_content/[\w./-]+"
    r")(?!\w)"
)

# External-URL prefixes — skip these in MD link checking.
EXTERNAL_PREFIXES = ("http://", "https://", "mailto:", "ftp://", "tel:")


def walk_md_files() -> Iterator[Path]:
    """Yield every *.md file under REPO, skipping vendor/build trees."""
    for p in REPO.rglob("*.md"):
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        yield p


def strip_code_fences(text: str) -> str:
    """Remove fenced code blocks so we don't pull paths out of code samples.

    Inline backticks are KEPT — those are intentional path mentions.
    """
    return re.sub(r"```.*?```", "", text, flags=re.DOTALL)


def strip_markdown_link_targets(text: str) -> str:
    """Remove the `(target)` portion of every `[label](target)` link.

    The prose-path matcher should only see bare path mentions in prose,
    not paths embedded inside markdown link targets. Markdown link
    targets are validated separately by the `MD_LINK_RE` pass — so
    stripping them here prevents double-counting and prevents URL
    fragments like `docs/blob/main/X.md` (inside a GitHub URL) from
    being mis-matched as repo paths.
    """
    return re.sub(r"\]\([^)]+\)", "]()", text)


def resolve_link_target(doc_path: Path, target: str) -> Path:
    """Resolve a markdown link target relative to the doc that contains it.

    Strips any `#anchor` suffix. Strips any `?query` suffix.
    """
    target = target.split("#", 1)[0].split("?", 1)[0]
    if not target:
        # Bare anchor like [foo](#bar) — treat as same-file
        return doc_path
    p = (doc_path.parent / target).resolve()
    return p


def check_doc(doc_path: Path) -> list[dict]:
    """Run both checks against a single markdown file.

    Returns a list of finding dicts, each with:
      kind: 'broken_link' | 'missing_path'
      doc:  relative path of the .md file
      target: the broken link or path
      label: (broken_link only) the link's display text
      line: (best-effort line number)
    """
    findings: list[dict] = []
    text = doc_path.read_text(encoding="utf-8", errors="replace")
    rel_doc = doc_path.relative_to(REPO).as_posix()

    # Strip fenced code blocks AND markdown-link targets for prose-path
    # matching. Inline backticks are kept (they're separately scanned by
    # INLINE_PATH_RE). Markdown-link targets are validated by MD_LINK_RE
    # above; stripping their `(target)` here prevents prose-matcher
    # double-counting and avoids false positives on URL fragments
    # (e.g. `docs/blob/main/X.md` inside a GitHub URL).
    prose_text = strip_markdown_link_targets(strip_code_fences(text))

    # ── 1. Markdown links ──────────────────────────────────────────────────
    for m in MD_LINK_RE.finditer(text):
        label, target = m.group(1), m.group(2).strip()

        # Skip external URLs.
        if target.startswith(EXTERNAL_PREFIXES):
            continue

        # Skip pure anchors and empty targets.
        target_path_part = target.split("#", 1)[0].split("?", 1)[0]
        if not target_path_part:
            continue

        # Resolve and check existence.
        resolved = resolve_link_target(doc_path, target)

        # Only flag if it's an in-repo target (resolved is under REPO) — and
        # only if the file doesn't exist.
        try:
            resolved.relative_to(REPO)
        except ValueError:
            # Resolved escaped the repo (e.g., link to /tmp/foo) — skip.
            continue

        if not resolved.exists():
            line = text[: m.start()].count("\n") + 1
            findings.append(
                {
                    "kind": "broken_link",
                    "doc": rel_doc,
                    "label": label,
                    "target": target,
                    "resolved": resolved.relative_to(REPO).as_posix()
                    if resolved.is_relative_to(REPO)
                    else str(resolved),
                    "line": line,
                }
            )

    # ── 2. Inline code-path references ────────────────────────────────────
    for m in INLINE_PATH_RE.finditer(text):
        target = m.group(1)
        # Skip if the target looks like a URL slug (no extension, no known prefix)
        if not _looks_like_repo_path(target):
            continue
        resolved = (REPO / target).resolve()
        try:
            resolved.relative_to(REPO)
        except ValueError:
            continue
        if not resolved.exists():
            line = text[: m.start()].count("\n") + 1
            findings.append(
                {
                    "kind": "missing_path",
                    "doc": rel_doc,
                    "target": target,
                    "line": line,
                    "context": "inline-backticks",
                }
            )

    # ── 3. Prose-mention path references ──────────────────────────────────
    for m in PROSE_PATH_RE.finditer(prose_text):
        target = m.group(1).rstrip(".,;:)")  # strip trailing punctuation
        resolved = (REPO / target).resolve()
        try:
            resolved.relative_to(REPO)
        except ValueError:
            continue
        if not resolved.exists():
            line = prose_text[: m.start()].count("\n") + 1
            findings.append(
                {
                    "kind": "missing_path",
                    "doc": rel_doc,
                    "target": target,
                    "line": line,
                    "context": "prose",
                }
            )

    return findings


def _looks_like_repo_path(target: str) -> bool:
    """Heuristic: target should be an unambiguous repo-rooted path.

    To minimise false positives the checker ONLY flags paths starting
    with a known top-level directory. Bare relative paths like
    `tests/test_foo.py` (which could be relative to backend/, web/, or
    something else entirely) are not flagged — they're ambiguous, not
    verifiably broken.
    """
    if "/" not in target:
        return False
    if "@" in target:
        # Package@version refs aren't repo paths.
        return False
    top_levels = (
        "backend/",
        "pipeline/",
        "scripts/",
        "web/",
        "mobile/",
        "data/",
        "docs/",
        "sample_content/",
        ".github/",
        "alembic/",
    )
    return target.startswith(top_levels)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Path to write the JSON report (default: stdout)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress the human-readable summary on stderr",
    )
    args = parser.parse_args()

    all_findings: list[dict] = []
    docs_checked = 0
    for doc_path in walk_md_files():
        docs_checked += 1
        all_findings.extend(check_doc(doc_path))

    by_kind: dict[str, int] = defaultdict(int)
    for f in all_findings:
        by_kind[f["kind"]] += 1

    report = {
        "checker": "link_integrity",
        "docs_checked": docs_checked,
        "total_findings": len(all_findings),
        "by_kind": dict(by_kind),
        "findings": all_findings,
    }

    out_text = json.dumps(report, indent=2)
    if args.out:
        args.out.write_text(out_text, encoding="utf-8")
    else:
        print(out_text)

    if not args.quiet:
        print(
            f"\nlink-integrity: {len(all_findings)} findings across "
            f"{docs_checked} docs",
            file=sys.stderr,
        )
        for kind, n in sorted(by_kind.items()):
            print(f"  {kind:16s}  {n}", file=sys.stderr)

    return 0 if not all_findings else 1


if __name__ == "__main__":
    sys.exit(main())
