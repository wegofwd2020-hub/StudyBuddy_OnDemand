#!/usr/bin/env python3
"""Scan studybuddy-docs for API-route and env-var references that no longer
exist in StudyBuddy_OnDemand's backend source.

Scope is deliberately narrow: routes (drift → 404s) + env vars (drift → failed
boots). Python fence content and Pydantic field references are out of scope
until the docs repo carries more of them.

Exit 0 = clean. Exit 1 = drift detected. Report markdown goes to --out.

Ignore marker: a line containing `drift:ignore` immediately before a reference
suppresses that single reference (per CLAUDE.md §16, generalised beyond fences).
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

# --- Source-side extraction ----------------------------------------------------

ROUTE_DECORATOR_RE = re.compile(
    r"""@(?:router|app)\.(get|post|put|patch|delete)\s*\(\s*["']([^"']+)["']""",
    re.IGNORECASE,
)
# Pydantic-settings field: CAPS_NAME: type = default  (inside the Settings class)
SETTINGS_FIELD_RE = re.compile(r"^\s+([A-Z][A-Z0-9_]+)\s*:\s*[A-Za-z]", re.MULTILINE)


def extract_source_routes(app_root: Path) -> set[str]:
    """Return the set of decorator path strings found in FastAPI routers."""
    paths: set[str] = set()
    for f in app_root.rglob("*.py"):
        if "__pycache__" in f.parts or "alembic" in f.parts:
            continue
        try:
            text = f.read_text()
        except UnicodeDecodeError:
            continue
        for _method, path in ROUTE_DECORATOR_RE.findall(text):
            paths.add(path)
    return paths


def extract_env_vars(config_path: Path) -> set[str]:
    """Parse backend/config.py Settings class for CAPS field declarations."""
    if not config_path.exists():
        return set()
    text = config_path.read_text()
    return set(SETTINGS_FIELD_RE.findall(text))


# --- Docs-side extraction ------------------------------------------------------

# A docs route reference: `GET /api/v1/whatever/{id}` (inside prose or backticks)
DOCS_ROUTE_RE = re.compile(
    r"`?\b(GET|POST|PUT|PATCH|DELETE)\s+(/api/v\d+/[A-Za-z0-9_/{}\-]+)`?"
)
# A docs env-var reference: backtick-wrapped ALLCAPS identifier, length >= 5,
# containing at least one underscore (filters out things like `JSON`, `TODO`).
DOCS_ENVVAR_RE = re.compile(r"`([A-Z][A-Z0-9]*_[A-Z0-9_]+)`")
IGNORE_TOKEN = "drift:ignore"


def extract_docs_refs(docs_root: Path) -> tuple[list[dict], list[dict]]:
    """Return (route_refs, envvar_refs). Each ref carries file, line, value."""
    route_refs: list[dict] = []
    envvar_refs: list[dict] = []
    for f in docs_root.rglob("*.md"):
        try:
            lines = f.read_text().splitlines()
        except UnicodeDecodeError:
            continue
        for i, line in enumerate(lines):
            prev = lines[i - 1] if i > 0 else ""
            ignored = IGNORE_TOKEN in prev
            for m in DOCS_ROUTE_RE.finditer(line):
                if ignored:
                    continue
                route_refs.append(
                    {
                        "file": f,
                        "line": i + 1,
                        "method": m.group(1).upper(),
                        "path": m.group(2),
                        "raw": line.strip()[:120],
                    }
                )
            for m in DOCS_ENVVAR_RE.finditer(line):
                if ignored:
                    continue
                envvar_refs.append(
                    {
                        "file": f,
                        "line": i + 1,
                        "name": m.group(1),
                        "raw": line.strip()[:120],
                    }
                )
    return route_refs, envvar_refs


# --- Matching ------------------------------------------------------------------


def normalize_path(p: str) -> str:
    p = p.rstrip("/").lower()
    p = re.sub(r"\{[^}]+\}", "{}", p)
    return p


def route_matches(doc_path: str, source_paths: set[str]) -> bool:
    """Drift-free if any source decorator path is a suffix of doc path."""
    doc_n = normalize_path(doc_path)
    for sp in source_paths:
        sp_n = normalize_path(sp)
        if doc_n == sp_n or doc_n.endswith(sp_n):
            return True
    return False


# Known env-var-looking backtick tokens that aren't app env vars. Extend as
# false positives emerge.
ENV_ALLOWLIST = {
    "GITHUB_TOKEN",
    "DOCS_REPO_TOKEN",
    "GH_TOKEN",
    "PYTHONPATH",
    "PATH",
    "HOME",
    "USER",
}


# --- Report --------------------------------------------------------------------


def render_report(
    missing_routes: list[dict],
    missing_envvars: list[dict],
    source_route_count: int,
    source_env_count: int,
    docs_root: Path,
) -> str:
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    lines = [
        "# Documentation Drift — StudyBuddy OnDemand",
        "",
        f"_Scan run: {now}_",
        "",
        f"Scanned {source_route_count} source routes + {source_env_count} "
        "env vars against `studybuddy-docs/docs/**/*.md`.",
        "",
    ]
    if not missing_routes and not missing_envvars:
        lines += ["✅ **No drift detected.**", ""]
        return "\n".join(lines)

    if missing_routes:
        by_path: dict[str, list[dict]] = defaultdict(list)
        for r in missing_routes:
            by_path[r["path"]].append(r)
        lines += [
            f"## Routes referenced in docs but not found in source ({len(by_path)})",
            "",
            "| Doc route | References | First location |",
            "|---|---|---|",
        ]
        for path, refs in sorted(by_path.items()):
            first = refs[0]
            rel = first["file"].relative_to(docs_root)
            lines.append(
                f"| `{first['method']} {path}` | {len(refs)} | `{rel}:{first['line']}` |"
            )
        lines.append("")

    if missing_envvars:
        by_name: dict[str, list[dict]] = defaultdict(list)
        for r in missing_envvars:
            by_name[r["name"]].append(r)
        lines += [
            f"## Env vars referenced in docs but not found in backend/config.py "
            f"({len(by_name)})",
            "",
            "| Env var | References | First location |",
            "|---|---|---|",
        ]
        for name, refs in sorted(by_name.items()):
            first = refs[0]
            rel = first["file"].relative_to(docs_root)
            lines.append(
                f"| `{name}` | {len(refs)} | `{rel}:{first['line']}` |"
            )
        lines.append("")

    lines += [
        "---",
        "",
        "**To silence a false positive:** add `<!-- drift:ignore -->` on the line "
        "immediately before the reference.",
        "",
        "**To fix real drift:** update either the doc (if the symbol was renamed "
        "or removed) or the source (if the doc is describing intended state).",
        "",
    ]
    return "\n".join(lines)


# --- Main ----------------------------------------------------------------------


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--app", required=True, help="Path to StudyBuddy_OnDemand root")
    ap.add_argument("--docs", required=True, help="Path to studybuddy-docs/docs root")
    ap.add_argument("--out", required=True, help="Write markdown report here")
    args = ap.parse_args()

    app = Path(args.app).resolve()
    docs = Path(args.docs).resolve()
    out = Path(args.out).resolve()

    source_routes = extract_source_routes(app / "backend" / "src")
    source_envs = extract_env_vars(app / "backend" / "config.py") | ENV_ALLOWLIST

    route_refs, envvar_refs = extract_docs_refs(docs)

    missing_routes = [r for r in route_refs if not route_matches(r["path"], source_routes)]
    missing_envvars = [r for r in envvar_refs if r["name"] not in source_envs]

    report = render_report(
        missing_routes, missing_envvars, len(source_routes), len(source_envs), docs
    )
    out.write_text(report)

    if missing_routes or missing_envvars:
        print(
            f"Drift detected: {len(missing_routes)} route refs, "
            f"{len(missing_envvars)} env-var refs. Report: {out}",
            file=sys.stderr,
        )
        return 1
    print(f"Clean. Report: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
