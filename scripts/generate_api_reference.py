#!/usr/bin/env python3
"""AST-scan FastAPI router modules and emit API_REFERENCE.md.

No runtime imports — works regardless of dependency-install state. Extracts:
  - APIRouter tag + prefix (from the `router = APIRouter(...)` statement)
  - Each `@router.METHOD("/path", response_model=..., tags=[...])` decorator
  - The handler's docstring first line as summary

Loses (vs FastAPI's live OpenAPI schema): request/response body schemas,
security definitions, parameter details. For those, use FastAPI's runtime
OpenAPI export when requirements.txt is healthy enough to install cleanly.
"""
from __future__ import annotations

import argparse
import ast
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

HTTP_METHODS = {"get", "post", "put", "patch", "delete"}
APP_PREFIX = "/api/v1"  # set in backend/src/core/app_factory.py include_router()


def _literal(node: ast.AST) -> object:
    """Return the literal value of an AST node, or None if non-literal."""
    try:
        return ast.literal_eval(node)
    except (ValueError, SyntaxError):
        return None


def extract_router_meta(tree: ast.AST) -> dict:
    """Find `router = APIRouter(...)` at module level, pull prefix + tags."""
    meta = {"prefix": "", "tags": []}
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not (len(node.targets) == 1 and isinstance(node.targets[0], ast.Name)):
            continue
        if node.targets[0].id != "router":
            continue
        if not (isinstance(node.value, ast.Call) and
                isinstance(node.value.func, ast.Name) and
                node.value.func.id == "APIRouter"):
            continue
        for kw in node.value.keywords:
            if kw.arg == "prefix":
                v = _literal(kw.value)
                if isinstance(v, str):
                    meta["prefix"] = v
            elif kw.arg == "tags":
                v = _literal(kw.value)
                if isinstance(v, list):
                    meta["tags"] = [t for t in v if isinstance(t, str)]
        break
    return meta


def extract_routes(tree: ast.AST, router_meta: dict) -> list[dict]:
    """Walk function defs, pick decorators of form @router.<method>(...)."""
    routes = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for deco in node.decorator_list:
            call = deco if isinstance(deco, ast.Call) else None
            if call is None:
                continue
            func = call.func
            if not (isinstance(func, ast.Attribute)
                    and isinstance(func.value, ast.Name)
                    and func.value.id == "router"
                    and func.attr in HTTP_METHODS):
                continue
            path_arg = call.args[0] if call.args else None
            path = _literal(path_arg) if path_arg else None
            if not isinstance(path, str):
                continue

            response_model = ""
            status_code = ""
            per_route_tags = []
            for kw in call.keywords:
                if kw.arg == "response_model":
                    if isinstance(kw.value, ast.Name):
                        response_model = kw.value.id
                    elif isinstance(kw.value, ast.Attribute):
                        response_model = ast.unparse(kw.value)
                elif kw.arg == "status_code":
                    v = _literal(kw.value)
                    if v is not None:
                        status_code = str(v)
                elif kw.arg == "tags":
                    v = _literal(kw.value)
                    if isinstance(v, list):
                        per_route_tags = [t for t in v if isinstance(t, str)]

            summary = ""
            doc = ast.get_docstring(node)
            if doc:
                summary = doc.strip().splitlines()[0]

            routes.append({
                "method": func.attr.upper(),
                "path": path,
                "full_path": APP_PREFIX + router_meta["prefix"] + path,
                "handler": node.name,
                "response_model": response_model,
                "status_code": status_code,
                "tags": per_route_tags or router_meta["tags"],
                "summary": summary,
            })
    return routes


def scan_backend(src_root: Path) -> dict[str, list[dict]]:
    """Return {module_name: [routes]} for each *router*.py under src_root."""
    by_module: dict[str, list[dict]] = {}
    for f in sorted(src_root.rglob("*router*.py")):
        if "__pycache__" in f.parts:
            continue
        try:
            tree = ast.parse(f.read_text())
        except SyntaxError:
            continue
        meta = extract_router_meta(tree)
        routes = extract_routes(tree, meta)
        if not routes:
            continue
        # Module identifier: backend/src/admin/router.py -> "src/admin/router"
        rel = f.relative_to(src_root.parent).with_suffix("")
        by_module[str(rel)] = routes
    return by_module


def render(by_module: dict[str, list[dict]]) -> str:
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    total = sum(len(r) for r in by_module.values())
    lines = [
        "# StudyBuddy OnDemand — API Reference",
        "",
        f"_Auto-generated {now}. Regenerated nightly at 04:00 UTC._",
        "",
        f"**{total} endpoints** across **{len(by_module)} router modules**. "
        "Paths shown as mounted — the app's `/api/v1` prefix is already applied.",
        "",
        "Source: AST scan of `backend/src/**/router.py`. For request/response "
        "body schemas, see the live FastAPI docs at `/docs` on any running server.",
        "",
        "## Endpoints by module",
        "",
    ]

    # Also build an endpoint count by tag for a summary table.
    tag_counts: dict[str, int] = defaultdict(int)
    for routes in by_module.values():
        for r in routes:
            for t in r["tags"] or ["(untagged)"]:
                tag_counts[t] += 1

    lines += [
        "### Summary by tag",
        "",
        "| Tag | Endpoints |",
        "|---|---|",
    ]
    for tag, count in sorted(tag_counts.items(), key=lambda x: (-x[1], x[0])):
        lines.append(f"| `{tag}` | {count} |")
    lines.append("")

    for module, routes in sorted(by_module.items()):
        lines += [
            f"### `{module}`",
            "",
            "| Method | Path | Handler | Response model | Summary |",
            "|---|---|---|---|---|",
        ]
        for r in sorted(routes, key=lambda x: (x["full_path"], x["method"])):
            summary = (r["summary"] or "").replace("|", "\\|")[:80]
            lines.append(
                f"| {r['method']} | `{r['full_path']}` | `{r['handler']}` | "
                f"{r['response_model'] or '—'} | {summary} |"
            )
        lines.append("")

    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True, help="Path to backend/src")
    ap.add_argument("--out", required=True, help="Write API_REFERENCE.md here")
    args = ap.parse_args()

    src = Path(args.src).resolve()
    out = Path(args.out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    by_module = scan_backend(src)
    out.write_text(render(by_module))
    total = sum(len(r) for r in by_module.values())
    print(f"Wrote {out} — {total} endpoints, {len(by_module)} modules.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
