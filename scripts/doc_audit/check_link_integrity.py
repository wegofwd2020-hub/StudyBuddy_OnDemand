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
    "worktrees",  # .claude/worktrees/<agent>/ — agent scratch copies of the repo
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
#
# The lookbehind rejects matches immediately preceded by a word char or
# a hyphen — so `studybuddy-docs/UX_REQUIREMENTS.md` does NOT extract a
# bare `docs/UX_REQUIREMENTS.md` candidate (the `-docs/` prefix
# disqualifies it).
PROSE_PATH_RE = re.compile(
    r"(?<!`)(?<![\w-])(?<!/)("
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

# URL-stripping regex — collapses any http(s):// link to a placeholder so
# its path component (e.g. `playwright.dev/docs/intro`) doesn't leak into
# the prose-path matcher. Used after fenced-code + inline-backtick + MD
# link-target stripping.
URL_RE = re.compile(r"https?://\S+")

# External-URL prefixes — skip these in MD link checking.
EXTERNAL_PREFIXES = ("http://", "https://", "mailto:", "ftp://", "tel:")

# Ignore-marker convention. A line containing this token suppresses every
# finding on the same line OR the line immediately following. Useful for:
#   - Historic CHANGES.md entries describing files since renamed/deleted
#   - URL endpoints in docs that look like file paths but aren't
#   - Cross-repo references that resolve in studybuddy-docs but not here
#   - Planned-but-not-built file paths in epic specs
IGNORE_MARKER = "<!-- doc-audit:ignore -->"


def walk_md_files() -> Iterator[Path]:
    """Yield every *.md file under REPO, skipping vendor/build trees."""
    for p in REPO.rglob("*.md"):
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        yield p


def _replace_preserving_newlines(pattern: re.Pattern, text: str) -> str:
    """re.sub variant that replaces each match with a newline-equivalent.

    For the prose-path matcher, line numbers reported back to the user
    must match the *original* document. If we strip a fenced code block
    out, the newlines inside it must remain so subsequent lines keep
    their original line numbers.
    """

    def repl(m: re.Match) -> str:
        content = m.group(0)
        return "\n" * content.count("\n")

    return pattern.sub(repl, text)


_FENCE_RE = re.compile(r"```.*?```", re.DOTALL)
_MD_TARGET_RE = re.compile(r"\]\([^)]+\)")
_INLINE_BACKTICK_RE = re.compile(r"`[^`\n]*`")


def strip_code_fences(text: str) -> str:
    """Remove fenced code blocks so we don't pull paths out of code samples.

    Newline-preserving so subsequent prose-pass line numbers remain
    correct.
    """
    return _replace_preserving_newlines(_FENCE_RE, text)


def strip_markdown_link_targets(text: str) -> str:
    """Replace the `(target)` portion of every `[label](target)` link.

    The prose-path matcher should only see bare path mentions in prose,
    not paths embedded inside markdown link targets. Markdown link
    targets are validated separately by the `MD_LINK_RE` pass — so
    stripping them here prevents double-counting and prevents URL
    fragments like `docs/blob/main/X.md` (inside a GitHub URL) from
    being mis-matched as repo paths. Newline-preserving (link targets
    are typically single-line, so this is usually a no-op for newline
    counts, but kept for correctness).
    """
    return _replace_preserving_newlines(_MD_TARGET_RE, text)


def strip_inline_backticks(text: str) -> str:
    """Remove the contents of every inline `<code>` backtick span.

    Inline backticks are scanned separately by `INLINE_PATH_RE` (with
    strict file-extension checking). The prose path-matcher should NOT
    see inline-backtick contents, otherwise a URL endpoint like
    `\\`/admin/pipeline/trigger\\`` lights up `pipeline/trigger` as a
    candidate prose-path even though the surrounding backticks signal
    "this is code, not prose".

    Newline-preserving so prose-pass line numbers remain correct.
    """
    return _replace_preserving_newlines(_INLINE_BACKTICK_RE, text)


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


def _ignored_lines(text: str) -> set[int]:
    """Return the set of 1-indexed line numbers that should be ignored.

    A line N is ignored if line N or line N-1 contains IGNORE_MARKER.
    """
    ignored: set[int] = set()
    for i, line in enumerate(text.splitlines(), start=1):
        if IGNORE_MARKER in line:
            ignored.add(i)
            ignored.add(i + 1)
    return ignored


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
    ignored = _ignored_lines(text)

    # Strip fenced code blocks, markdown-link targets, inline-backtick
    # contents, AND bare http(s):// URLs before applying the prose-path
    # matcher.
    #
    # Inline backticks are validated separately by INLINE_PATH_RE (which
    # uses strict=True file-extension checking). Markdown-link targets are
    # validated by MD_LINK_RE above. Each of these strippers removes a
    # class of false positives:
    #   - fences: paths inside ``` blocks are code samples, not real refs
    #   - link targets: avoid double-counting + URL-fragment false positives
    #   - inline backticks: avoid URL endpoints (`/admin/pipeline/trigger`)
    #     leaking into the prose pass
    #   - bare URLs: avoid URL path fragments like `playwright.dev/docs/intro`
    #     being matched as `docs/intro` (a repo-prefixed candidate)
    prose_text = URL_RE.sub(
        "",
        strip_inline_backticks(
            strip_markdown_link_targets(strip_code_fences(text))
        ),
    )

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
            if line in ignored:
                continue
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
    #
    # Inline backticks have a higher false-positive rate because URL
    # endpoints (`POST /admin/pipeline/trigger`, `/api/v1/foo`) and
    # bash command examples (`docker compose exec api pytest`) all
    # legitimately appear in inline code. We use a tighter check:
    # require either a known file extension or trailing slash.
    for m in INLINE_PATH_RE.finditer(text):
        target = m.group(1)
        if not _looks_like_repo_path(target, strict=True):
            continue
        resolved = (REPO / target).resolve()
        try:
            resolved.relative_to(REPO)
        except ValueError:
            continue
        if not resolved.exists():
            line = text[: m.start()].count("\n") + 1
            if line in ignored:
                continue
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
        # Strip trailing punctuation + emphasis markers. The regex's
        # `[\w./-]+` is greedy and happily consumes the trailing `.` of
        # a sentence, the `_` of an italic-emphasised line, and similar
        # noise chars adjacent to but not part of the actual path.
        target = m.group(1).rstrip(".,;:)_")
        resolved = (REPO / target).resolve()
        try:
            resolved.relative_to(REPO)
        except ValueError:
            continue
        if not resolved.exists():
            line = prose_text[: m.start()].count("\n") + 1
            if line in ignored:
                continue
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


REPO_FILE_EXTENSIONS = (
    ".py", ".ts", ".tsx", ".js", ".jsx",
    ".yaml", ".yml", ".json", ".toml",
    ".md", ".rst", ".txt",
    ".sql", ".sh", ".bash",
    ".html", ".css", ".scss",
    ".env", ".cfg", ".ini",
)


def _looks_like_repo_path(target: str, strict: bool = False) -> bool:
    """Heuristic: target should be an unambiguous repo-rooted path.

    Common case (strict=False): target starts with a known top-level
    directory. Bare relative paths like `tests/test_foo.py` are
    ambiguous and pass through unchecked.

    strict=True (used inside inline backticks where false-positive rate
    is higher): require ALSO that the target ends in a recognised file
    extension or with a trailing slash. This rejects URL endpoints like
    `pipeline/trigger` and command snippets like `bun run start`.
    """
    if "/" not in target:
        return False
    if "@" in target:
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
    if not target.startswith(top_levels):
        return False
    if strict:
        # Must look like a real file or directory reference.
        if target.endswith("/"):
            return True
        return any(target.endswith(ext) for ext in REPO_FILE_EXTENSIONS)
    return True


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
