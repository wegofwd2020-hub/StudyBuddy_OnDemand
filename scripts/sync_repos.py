#!/usr/bin/env python3
"""Sync local folder with all repos under github.com/wegofwd2020-hub.

For each repo on GitHub:
  - If the local clone is missing -> git clone (default branch)
  - If it exists -> git fetch --all --prune, then ff-only pull on the current branch
  - Skips local dirs that exist but aren't a git repo
  - Skips repos with uncommitted changes (warns, doesn't touch them)

Run:  python3 scripts/sync_repos.py

Env vars (all optional):
  SYNC_REPOS_ROOT   destination directory (where to clone/sync into).
                    Defaults to the parent directory of this repo's checkout
                    (i.e. siblings of StudyBuddy_OnDemand). Override with an
                    absolute path if you want a different location.
  SYNC_REPOS_OWNER  GitHub owner (org or user). Default: wegofwd2020-hub.
  GITHUB_TOKEN      Higher rate limit; needed for private repos.
  CLONE_PROTO       'ssh' (default — uses your SSH keys) or 'https'.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

OWNER = os.environ.get("SYNC_REPOS_OWNER", "wegofwd2020-hub")

# Default destination = sibling of this repo's root (i.e. one directory up
# from scripts/). Override via SYNC_REPOS_ROOT for any custom layout.
_DEFAULT_ROOT = Path(__file__).resolve().parent.parent.parent
LOCAL_ROOT = Path(os.environ.get("SYNC_REPOS_ROOT", str(_DEFAULT_ROOT)))

API_BASE = "https://api.github.com"
CLONE_PROTO = os.environ.get("CLONE_PROTO", "ssh").lower()  # 'ssh' or 'https'


def gh_get(path: str) -> list[dict]:
    """GET a paginated GitHub API endpoint, return all items merged."""
    items: list[dict] = []
    url: str | None = f"{API_BASE}{path}?per_page=100&type=all"
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "sync-repos-script",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    while url:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as resp:
            page = json.loads(resp.read().decode("utf-8"))
            items.extend(page)
            url = _next_link(resp.headers.get("Link"))
    return items


def _next_link(link_header: str | None) -> str | None:
    if not link_header:
        return None
    for part in link_header.split(","):
        section = part.strip().split(";")
        if len(section) < 2:
            continue
        url_part = section[0].strip()
        rel_part = section[1].strip()
        if rel_part == 'rel="next"' and url_part.startswith("<") and url_part.endswith(">"):
            return url_part[1:-1]
    return None


def list_repos(owner: str) -> list[dict]:
    """List repos for a user OR org. Tries org endpoint first, falls back to user."""
    try:
        return gh_get(f"/orgs/{owner}/repos")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return gh_get(f"/users/{owner}/repos")
        raise


def run(cmd: list[str], cwd: Path | None = None) -> tuple[int, str, str]:
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def is_git_repo(path: Path) -> bool:
    return (path / ".git").exists()


def has_uncommitted(path: Path) -> bool:
    code, out, _ = run(["git", "status", "--porcelain"], cwd=path)
    return code == 0 and bool(out)


def sync_repo(repo: dict, root: Path) -> str:
    name = repo["name"]
    clone_url = repo["ssh_url"] if CLONE_PROTO == "ssh" else repo["clone_url"]
    target = root / name

    if not target.exists():
        code, _, err = run(["git", "clone", clone_url, str(target)])
        return f"CLONED  {name}" if code == 0 else f"FAIL    {name}: {err}"

    if not is_git_repo(target):
        return f"SKIP    {name} (not a git repo)"

    if has_uncommitted(target):
        return f"DIRTY   {name} (uncommitted changes — left untouched)"

    code, _, err = run(["git", "fetch", "--all", "--prune"], cwd=target)
    if code != 0:
        return f"FAIL    {name}: fetch failed: {err}"

    code, _, err = run(["git", "pull", "--ff-only"], cwd=target)
    if code != 0:
        return f"WARN    {name}: pull --ff-only failed (non-ff or detached): {err}"

    return f"PULLED  {name}"


def main() -> int:
    if not LOCAL_ROOT.is_dir():
        print(f"ERROR: {LOCAL_ROOT} does not exist", file=sys.stderr)
        print("Set SYNC_REPOS_ROOT to an existing directory, or create it first.", file=sys.stderr)
        return 1

    print(f"Listing repos under github.com/{OWNER} ...")
    try:
        repos = list_repos(OWNER)
    except urllib.error.HTTPError as e:
        print(f"GitHub API error: {e.code} {e.reason}", file=sys.stderr)
        if e.code in (401, 403):
            print("Hint: set GITHUB_TOKEN to raise rate limits or access private repos.", file=sys.stderr)
        return 2

    repos.sort(key=lambda r: r["name"].lower())
    print(f"Found {len(repos)} repos. Syncing into {LOCAL_ROOT}\n")

    results = [sync_repo(r, LOCAL_ROOT) for r in repos]
    for line in results:
        print(line)

    print("\nDone.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
