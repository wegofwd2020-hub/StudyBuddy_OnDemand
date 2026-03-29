"""
backend/src/admin/build_reports.py

GET /admin/ci/reports

Returns the last 10 GitHub Actions CI runs for the configured repo,
with per-job details for the most recent run.  Responses are cached in
Redis for 5 minutes to avoid GitHub API rate limits.

Permission: super_admin only (all other admin roles are excluded).

Configuration (both optional — the endpoint returns github_configured=false
if GITHUB_REPO is not set):
  GITHUB_REPO   "owner/repo"  e.g. "wegofwd2020-hub/StudyBuddy_OnDemand"
  GITHUB_TOKEN  PAT with Actions:read  (60 req/h unauthenticated otherwise)
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

import httpx
from config import settings
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from src.auth.dependencies import get_current_admin
from src.core.redis_client import get_redis
from src.utils.logger import get_logger

log = get_logger("admin.ci")
router = APIRouter(tags=["admin"])

_CACHE_KEY = "ci:reports:latest"
_CACHE_TTL = 300  # 5 minutes
_GITHUB_API = "https://api.github.com"
_RUNS_PER_PAGE = 10


# ── RBAC dependency ───────────────────────────────────────────────────────────


async def _super_admin_only(
    request: Request,
    admin: Annotated[dict, Depends(get_current_admin)],
) -> dict:
    if admin.get("role") != "super_admin":
        raise HTTPException(
            status_code=403,
            detail={
                "error": "forbidden",
                "detail": "CI reports are restricted to super_admin.",
                "correlation_id": getattr(request.state, "correlation_id", ""),
            },
        )
    return admin


# ── Pydantic schemas ──────────────────────────────────────────────────────────


class CiJob(BaseModel):
    name: str
    status: str
    conclusion: str | None
    duration_s: int | None
    html_url: str


class CiRun(BaseModel):
    run_id: int
    head_branch: str
    head_sha: str  # first 7 characters
    conclusion: str | None  # success | failure | cancelled | timed_out | None
    created_at: str
    duration_s: int | None
    html_url: str
    jobs: list[CiJob]  # populated only for the latest run; empty for history rows


class CiReportsResponse(BaseModel):
    github_configured: bool
    repo: str
    runs: list[CiRun]  # most-recent first; runs[0] has full job details
    cached_at: str


# ── GitHub API helpers ────────────────────────────────────────────────────────


def _gh_headers() -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if settings.GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {settings.GITHUB_TOKEN}"
    return headers


def _duration(start: str | None, end: str | None) -> int | None:
    """Return elapsed seconds between two ISO-8601 timestamps, or None."""
    if not start or not end:
        return None
    try:
        s = datetime.fromisoformat(start.replace("Z", "+00:00"))
        e = datetime.fromisoformat(end.replace("Z", "+00:00"))
        return max(0, int((e - s).total_seconds()))
    except (ValueError, TypeError):
        return None


async def _fetch_runs(client: httpx.AsyncClient, repo: str) -> list[CiRun]:
    """Fetch the last _RUNS_PER_PAGE CI runs from GitHub Actions."""
    url = f"{_GITHUB_API}/repos/{repo}/actions/runs"
    resp = await client.get(
        url,
        params={
            "per_page": _RUNS_PER_PAGE,
            "branch": "main",
            "event": "push",
        },
        headers=_gh_headers(),
        timeout=10.0,
    )
    if resp.status_code == 404:
        log.warning("github_repo_not_found", repo=repo)
        return []
    resp.raise_for_status()
    data = resp.json()
    runs = []
    for r in data.get("workflow_runs", []):
        runs.append(
            CiRun(
                run_id=r["id"],
                head_branch=r.get("head_branch", ""),
                head_sha=r.get("head_sha", "")[:7],
                conclusion=r.get("conclusion"),
                created_at=r.get("created_at", ""),
                duration_s=_duration(r.get("run_started_at"), r.get("updated_at")),
                html_url=r.get("html_url", ""),
                jobs=[],
            )
        )
    return runs


async def _fetch_jobs(client: httpx.AsyncClient, repo: str, run_id: int) -> list[CiJob]:
    """Fetch jobs for a single CI run."""
    url = f"{_GITHUB_API}/repos/{repo}/actions/runs/{run_id}/jobs"
    resp = await client.get(url, headers=_gh_headers(), timeout=10.0)
    if resp.status_code != 200:
        return []
    jobs = []
    for j in resp.json().get("jobs", []):
        jobs.append(
            CiJob(
                name=j.get("name", ""),
                status=j.get("status", ""),
                conclusion=j.get("conclusion"),
                duration_s=_duration(j.get("started_at"), j.get("completed_at")),
                html_url=j.get("html_url", ""),
            )
        )
    return jobs


# ── Endpoint ──────────────────────────────────────────────────────────────────


@router.get(
    "/admin/ci/reports",
    response_model=CiReportsResponse,
    summary="Latest CI build and test reports",
)
async def get_ci_reports(
    _admin: Annotated[dict, Depends(_super_admin_only)],
    redis=Depends(get_redis),
) -> CiReportsResponse:
    """
    Return the last 10 GitHub Actions CI runs with per-job details on
    the most recent run.  Results are cached for 5 minutes.
    """
    if not settings.GITHUB_REPO:
        return CiReportsResponse(
            github_configured=False,
            repo="",
            runs=[],
            cached_at=datetime.now(UTC).isoformat(),
        )

    # L2 cache check
    cached = await redis.get(_CACHE_KEY)
    if cached:
        try:
            return CiReportsResponse.model_validate_json(cached)
        except Exception:
            pass  # stale/corrupt cache — fall through to live fetch

    repo = settings.GITHUB_REPO
    try:
        async with httpx.AsyncClient() as client:
            runs = await _fetch_runs(client, repo)
            if runs:
                runs[0].jobs = await _fetch_jobs(client, repo, runs[0].run_id)
    except httpx.HTTPStatusError as exc:
        log.error("github_api_error", status=exc.response.status_code, repo=repo)
        raise HTTPException(
            status_code=502,
            detail={
                "error": "github_api_error",
                "detail": f"GitHub API returned {exc.response.status_code}.",
            },
        )
    except httpx.RequestError as exc:
        log.error("github_request_error", error=str(exc), repo=repo)
        raise HTTPException(
            status_code=502,
            detail={"error": "github_unreachable", "detail": "Could not reach GitHub API."},
        )

    response = CiReportsResponse(
        github_configured=True,
        repo=repo,
        runs=runs,
        cached_at=datetime.now(UTC).isoformat(),
    )

    # Store in Redis (fire-and-forget — a cache write failure is non-fatal)
    try:
        await redis.setex(_CACHE_KEY, _CACHE_TTL, response.model_dump_json())
    except Exception as exc:
        log.warning("ci_cache_write_failed", error=str(exc))

    return response
