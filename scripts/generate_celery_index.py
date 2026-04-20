#!/usr/bin/env python3
"""AST-scan for Celery task declarations and emit CELERY_TASKS.md.

Matches decorators of the form:
  @shared_task(...)              @shared_task
  @celery_app.task(...)          @celery_app.task
  @app.task(...)                 @app.task

For each task records: task name (from `name=` kwarg if present, else
`module.function_name`), queue (from `queue=` kwarg if present), first line
of the handler's docstring, parameter names.
"""
from __future__ import annotations

import argparse
import ast
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


def _literal(node: ast.AST) -> object:
    try:
        return ast.literal_eval(node)
    except (ValueError, SyntaxError):
        return None


def _is_celery_decorator(deco: ast.AST) -> bool:
    target = deco.func if isinstance(deco, ast.Call) else deco
    if isinstance(target, ast.Name):
        return target.id == "shared_task"
    if isinstance(target, ast.Attribute) and target.attr == "task":
        return isinstance(target.value, ast.Name) and target.value.id in {
            "celery_app",
            "app",
        }
    return False


def _deco_kwargs(deco: ast.AST) -> dict[str, object]:
    if not isinstance(deco, ast.Call):
        return {}
    out = {}
    for kw in deco.keywords:
        v = _literal(kw.value)
        if v is not None and kw.arg:
            out[kw.arg] = v
    return out


def extract_tasks(tree: ast.AST, module_name: str) -> list[dict]:
    tasks = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        celery_decos = [d for d in node.decorator_list if _is_celery_decorator(d)]
        if not celery_decos:
            continue
        deco = celery_decos[0]
        kwargs = _deco_kwargs(deco)

        task_name = kwargs.get("name") or f"{module_name}.{node.name}"
        queue = kwargs.get("queue", "")

        params = [a.arg for a in node.args.args if a.arg != "self"]

        summary = ""
        doc = ast.get_docstring(node)
        if doc:
            summary = doc.strip().splitlines()[0]

        tasks.append({
            "name": str(task_name),
            "module": module_name,
            "function": node.name,
            "queue": str(queue) if queue else "",
            "params": params,
            "summary": summary,
        })
    return tasks


def scan(src_root: Path) -> list[dict]:
    found: list[dict] = []
    for f in sorted(src_root.rglob("*.py")):
        if "__pycache__" in f.parts:
            continue
        try:
            tree = ast.parse(f.read_text())
        except SyntaxError:
            continue
        module_name = str(f.relative_to(src_root.parent).with_suffix("")).replace(
            "/", "."
        )
        found.extend(extract_tasks(tree, module_name))
    return found


def render(tasks: list[dict]) -> str:
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    lines = [
        "# StudyBuddy OnDemand — Celery Task Index",
        "",
        f"_Auto-generated {now}. Regenerated nightly at 04:00 UTC._",
        "",
        f"**{len(tasks)} tasks** found via AST scan of `backend/src/**/*.py`. "
        "Source-of-truth for task names used by `.delay()` / `.apply_async()` "
        "callers and for queue routing in `celery_app.py`.",
        "",
    ]

    by_queue: dict[str, list[dict]] = defaultdict(list)
    for t in tasks:
        by_queue[t["queue"] or "(default)"].append(t)

    lines += [
        "## Summary by queue",
        "",
        "| Queue | Task count |",
        "|---|---|",
    ]
    for q in sorted(by_queue, key=lambda k: (-len(by_queue[k]), k)):
        lines.append(f"| `{q}` | {len(by_queue[q])} |")
    lines.append("")

    lines.append("## All tasks")
    lines.append("")
    lines.append("| Task name | Queue | Module | Function | Params | Summary |")
    lines.append("|---|---|---|---|---|---|")
    for t in sorted(tasks, key=lambda x: x["name"]):
        params = ", ".join(f"`{p}`" for p in t["params"]) or "—"
        summary = (t["summary"] or "").replace("|", "\\|")[:80]
        lines.append(
            f"| `{t['name']}` | `{t['queue'] or 'default'}` | "
            f"`{t['module']}` | `{t['function']}` | {params} | {summary} |"
        )
    lines.append("")

    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True, help="Path to backend/src")
    ap.add_argument("--out", required=True, help="Write CELERY_TASKS.md here")
    args = ap.parse_args()

    src = Path(args.src).resolve()
    out = Path(args.out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    tasks = scan(src)
    out.write_text(render(tasks))
    print(f"Wrote {out} — {len(tasks)} celery tasks.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
