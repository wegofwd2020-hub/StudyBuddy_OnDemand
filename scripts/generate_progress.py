#!/usr/bin/env python3
"""Generate docs/PROGRESS.md from docs/epics/ + git log.

Treats each EPIC_NN_*.md as a feature. Attributes commits to epics by:
  1. Conventional-commit scope  -> `feat(epic-11): ...`
  2. Ticket IDs in subject      -> `C-5`, `L-1`, `T-1a` (each epic has a letter prefix)

A ticket that appears in 2+ commits is counted as iterated/redesigned.
"""
from __future__ import annotations

import csv
import re
import subprocess
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
EPICS_DIR = REPO / "docs" / "epics"
OUTPUT = REPO / "docs" / "PROGRESS.md"
OUTPUT_EPICS_CSV = REPO / "docs" / "PROGRESS_epics.csv"
OUTPUT_TICKETS_CSV = REPO / "docs" / "PROGRESS_tickets.csv"

TICKET_RE = re.compile(r"\b([A-Z])-(\d+[a-z]?)\b")
EPIC_SCOPE_RE = re.compile(r"\(epic-(\d+)\)", re.IGNORECASE)
STATUS_RE = re.compile(r"^\*\*Status:\*\*\s*(.+?)$", re.MULTILINE)
TITLE_RE = re.compile(r"^#\s+(.+)$", re.MULTILINE)


def parse_epics() -> dict[int, dict]:
    epics: dict[int, dict] = {}
    for f in sorted(EPICS_DIR.glob("EPIC_*.md")):
        m = re.match(r"EPIC_(\d+)_", f.name)
        if not m:
            continue
        num = int(m.group(1))
        text = f.read_text()

        title_m = TITLE_RE.search(text)
        title = title_m.group(1).strip() if title_m else f.stem

        status_m = STATUS_RE.search(text)
        status = status_m.group(1).strip()[:80] if status_m else ""

        prefix_counts: dict[str, int] = defaultdict(int)
        for letter, _ in TICKET_RE.findall(text):
            prefix_counts[letter] += 1

        epics[num] = {
            "num": num,
            "title": title,
            "status": status,
            "prefix_counts": dict(prefix_counts),
            "prefix": max(prefix_counts, key=prefix_counts.get) if prefix_counts else None,
            "file": f.name,
        }
    return epics


def get_commits() -> list[dict]:
    out = subprocess.check_output(
        ["git", "log", "--pretty=format:%H|%aI|%s"],
        cwd=REPO,
        text=True,
    )
    commits = []
    for line in out.splitlines():
        h, d, s = line.split("|", 2)
        commits.append(
            {
                "hash": h,
                "date": datetime.fromisoformat(d).date().isoformat(),
                "subject": s,
            }
        )
    return commits


def attribute_commits(commits: list[dict], epics: dict[int, dict]) -> None:
    # Each prefix letter goes to the epic that references it most heavily.
    # This avoids mis-attribution when one epic mentions another's tickets in passing.
    prefix_owner_scores: dict[str, tuple[int, int]] = {}  # letter -> (epic_num, count)
    for num, e in epics.items():
        for letter, count in e["prefix_counts"].items():
            best = prefix_owner_scores.get(letter)
            if best is None or count > best[1]:
                prefix_owner_scores[letter] = (num, count)
    prefix_to_epic = {letter: owner for letter, (owner, _) in prefix_owner_scores.items()}

    for c in commits:
        owners: set[int] = set()
        for m in EPIC_SCOPE_RE.finditer(c["subject"]):
            n = int(m.group(1))
            if n in epics:
                owners.add(n)
        c["tickets"] = []
        for letter, num in TICKET_RE.findall(c["subject"]):
            tid = f"{letter}-{num}"
            c["tickets"].append(tid)
            if letter in prefix_to_epic:
                owners.add(prefix_to_epic[letter])
        c["epics"] = sorted(owners)


def render(epics: dict[int, dict], commits: list[dict]) -> str:
    per_epic: dict[int, dict] = defaultdict(
        lambda: {"commits": [], "tickets": defaultdict(list)}
    )
    for c in commits:
        for n in c["epics"]:
            per_epic[n]["commits"].append(c)
            for t in c["tickets"]:
                per_epic[n]["tickets"][t].append(c)

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    lines: list[str] = []
    lines.append("# StudyBuddy OnDemand — Progress Chart")
    lines.append("")
    lines.append(f"_Auto-generated {now}. Regenerated nightly at 21:00 EST._")
    lines.append("")
    lines.append(
        "Source: `docs/epics/` (feature manifest) + `git log` (activity). "
        "Script: `scripts/generate_progress.py`."
    )
    lines.append("")

    lines.append("## Timeline")
    lines.append("")
    lines.append("```mermaid")
    lines.append("gantt")
    lines.append("    title Epic Activity Windows")
    lines.append("    dateFormat YYYY-MM-DD")
    lines.append("    axisFormat %Y-%m")
    for num in sorted(epics):
        data = per_epic.get(num)
        if not data or not data["commits"]:
            continue
        dates = sorted(c["date"] for c in data["commits"])
        first, last = dates[0], dates[-1]
        if first == last:
            last_dt = datetime.fromisoformat(first).date()
            last = last_dt.replace(day=min(last_dt.day + 1, 28)).isoformat()
        label = f"Epic {num}".ljust(7)
        section = "done" if "✅" in epics[num]["status"] else "active"
        lines.append(f"    {label} :{section}, e{num}, {first}, {last}")
    lines.append("```")
    lines.append("")

    lines.append("## Summary")
    lines.append("")
    lines.append(
        "| # | Epic | Status | First | Last | Commits | Tickets | Hot-spots (≥2 commits) |"
    )
    lines.append("|---|---|---|---|---|---|---|---|")
    for num in sorted(epics):
        e = epics[num]
        data = per_epic.get(num, {"commits": [], "tickets": {}})
        cs = data["commits"]
        if cs:
            ds = sorted(c["date"] for c in cs)
            first, last = ds[0], ds[-1]
        else:
            first = last = "—"
        hot = [
            (t, len(v)) for t, v in data["tickets"].items() if len(v) >= 2
        ]
        hot.sort(key=lambda x: -x[1])
        hot_str = ", ".join(f"{t}×{n}" for t, n in hot[:4]) or "—"
        title_short = re.sub(r"^Epic \d+\s*—\s*", "", e["title"])
        lines.append(
            f"| {num} | [{title_short}](epics/{e['file']}) | {e['status']} | "
            f"{first} | {last} | {len(cs)} | {len(data['tickets'])} | {hot_str} |"
        )
    lines.append("")

    lines.append("## Redesign leaderboard")
    lines.append("")
    lines.append("Tickets with 2+ commits — each extra commit is an iteration or rework.")
    lines.append("")
    lines.append("| Ticket | Epic | Commits | First | Last | Span (days) |")
    lines.append("|---|---|---|---|---|---|")
    rows = []
    for num, data in per_epic.items():
        for t, cs in data["tickets"].items():
            if len(cs) >= 2:
                ds = sorted(c["date"] for c in cs)
                span = (
                    datetime.fromisoformat(ds[-1]).date()
                    - datetime.fromisoformat(ds[0]).date()
                ).days
                rows.append((t, num, len(cs), ds[0], ds[-1], span))
    rows.sort(key=lambda r: (-r[2], r[1]))
    if not rows:
        lines.append("| — | — | — | — | — | — |")
    for t, num, cnt, first, last, span in rows:
        lines.append(f"| {t} | Epic {num} | {cnt} | {first} | {last} | {span} |")
    lines.append("")

    lines.append("## Per-epic detail")
    lines.append("")
    for num in sorted(epics):
        e = epics[num]
        data = per_epic.get(num, {"commits": [], "tickets": {}})
        lines.append(f"### {e['title']}")
        lines.append("")
        lines.append(f"- **Status:** {e['status'] or '—'}")
        lines.append(f"- **Epic file:** [{e['file']}](epics/{e['file']})")
        lines.append(f"- **Ticket prefix:** `{e['prefix'] or '—'}`")
        lines.append(f"- **Commits attributed:** {len(data['commits'])}")
        lines.append("")
        if data["tickets"]:
            lines.append("| Ticket | Commits | First | Last |")
            lines.append("|---|---|---|---|")
            for t in sorted(
                data["tickets"],
                key=lambda k: (k[0], int(re.match(r"\d+", k.split("-")[1]).group())),
            ):
                cs = data["tickets"][t]
                ds = sorted(c["date"] for c in cs)
                lines.append(f"| {t} | {len(cs)} | {ds[0]} | {ds[-1]} |")
            lines.append("")

    return "\n".join(lines) + "\n"


def write_csvs(epics: dict[int, dict], commits: list[dict]) -> None:
    """Write PROGRESS_epics.csv + PROGRESS_tickets.csv for spreadsheet analysis.

    Same data as the markdown tables, flattened to a format friendly to
    `=IMPORTDATA(...)` in Google Sheets or plain `File > Import` in Excel.
    """
    per_epic: dict[int, dict] = defaultdict(
        lambda: {"commits": [], "tickets": defaultdict(list)}
    )
    for c in commits:
        for n in c["epics"]:
            per_epic[n]["commits"].append(c)
            for t in c["tickets"]:
                per_epic[n]["tickets"][t].append(c)

    # Epics sheet — one row per epic.
    with OUTPUT_EPICS_CSV.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "epic_num", "title", "status", "prefix",
            "first_activity", "last_activity",
            "commit_count", "ticket_count", "hotspots",
        ])
        for num in sorted(epics):
            e = epics[num]
            data = per_epic.get(num, {"commits": [], "tickets": {}})
            cs = data["commits"]
            ds = sorted(c["date"] for c in cs)
            first = ds[0] if ds else ""
            last = ds[-1] if ds else ""
            hot = [(t, len(v)) for t, v in data["tickets"].items() if len(v) >= 2]
            hot.sort(key=lambda x: -x[1])
            hotspots = "; ".join(f"{t}x{n}" for t, n in hot[:4])
            w.writerow([
                num, e["title"], e["status"], e["prefix"] or "",
                first, last, len(cs), len(data["tickets"]), hotspots,
            ])

    # Tickets sheet — one row per ticket that appears in 1+ commits.
    with OUTPUT_TICKETS_CSV.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "ticket", "epic_num", "epic_title",
            "commit_count", "first", "last", "span_days",
        ])
        for num in sorted(epics):
            data = per_epic.get(num, {"commits": [], "tickets": {}})
            for t, tc in sorted(data["tickets"].items()):
                ds = sorted(c["date"] for c in tc)
                span = (
                    datetime.fromisoformat(ds[-1]).date()
                    - datetime.fromisoformat(ds[0]).date()
                ).days
                w.writerow([
                    t, num, epics[num]["title"],
                    len(tc), ds[0], ds[-1], span,
                ])


def main() -> None:
    epics = parse_epics()
    commits = get_commits()
    attribute_commits(commits, epics)
    OUTPUT.write_text(render(epics, commits))
    write_csvs(epics, commits)
    print(
        f"Wrote {OUTPUT} + {OUTPUT_EPICS_CSV.name} + {OUTPUT_TICKETS_CSV.name} "
        f"— {len(epics)} epics, {len(commits)} commits scanned."
    )


if __name__ == "__main__":
    main()
