"""
backend/src/scenarios/router.py

Routes:
  POST /scenarios/generate-clips                      — submit scenario JSON, dispatch Celery task
  GET  /scenarios/{scenario_id}/clips/status          — poll job + per-clip status
  GET  /scenarios/{scenario_id}/clips/{turn_index}    — stream MP4 file
"""

from __future__ import annotations

import json
import logging
import uuid
from pathlib import Path

from config import settings
from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import FileResponse

from src.core.redis_client import get_redis
from src.scenarios.schemas import (
    ClipsStatusResponse,
    ClipStatus,
    GenerateClipsRequest,
    GenerateClipsResponse,
)

log = logging.getLogger("scenarios.router")
router = APIRouter(tags=["scenarios"])

_FALLBACK_KEY = "jt2026"


def _api_key() -> str:
    return getattr(settings, "SCENARIO_API_KEY", None) or _FALLBACK_KEY


def _check_key(x_scenario_key: str | None) -> None:
    if x_scenario_key != _api_key():
        raise HTTPException(status_code=403, detail="Invalid scenario API key")


def _clips_dir(scenario_id: str) -> Path:
    return Path(settings.CONTENT_STORE_PATH) / "scenarios" / scenario_id


def _job_redis_key(job_id: str) -> str:
    return f"scenario:job:{job_id}"


# ── POST /scenarios/generate-clips ───────────────────────────────────────────

@router.post("/scenarios/generate-clips", response_model=GenerateClipsResponse)
async def generate_clips(
    body: GenerateClipsRequest,
    request: Request,
    x_scenario_key: str | None = Header(default=None),
):
    _check_key(x_scenario_key)

    scenario = body.scenario
    scenario_id = scenario.get("scenario_id") or f"scenario-{uuid.uuid4().hex[:8]}"
    job_id = str(uuid.uuid4())

    # Persist scenario JSON so the Celery worker can read it
    out_dir = _clips_dir(scenario_id)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "scenario.json").write_text(json.dumps(scenario, indent=2))

    # Initialise job status in Redis
    redis = get_redis(request)
    dialog = scenario.get("dialog", [])
    initial = {
        "status": "pending",
        "scenario_id": scenario_id,
        "total_clips": len(dialog),
        "completed_clips": 0,
        "clips": json.dumps(
            [{"turn_index": i, "status": "pending"} for i in range(len(dialog))]
        ),
    }
    await redis.hset(_job_redis_key(job_id), mapping=initial)
    await redis.expire(_job_redis_key(job_id), 3600)

    # Dispatch to pipeline queue
    from src.auth.tasks import generate_scenario_clips_task

    generate_scenario_clips_task.delay(
        scenario_id=scenario_id,
        job_id=job_id,
        content_store_path=settings.CONTENT_STORE_PATH,
    )

    log.info("scenario_clips_queued scenario_id=%s job_id=%s", scenario_id, job_id)
    return GenerateClipsResponse(job_id=job_id, scenario_id=scenario_id)


# ── GET /scenarios/{scenario_id}/clips/status ────────────────────────────────

@router.get("/scenarios/{scenario_id}/clips/status", response_model=ClipsStatusResponse)
async def clips_status(
    scenario_id: str,
    job_id: str,
    request: Request,
    x_scenario_key: str | None = Header(default=None),
):
    _check_key(x_scenario_key)

    redis = get_redis(request)
    raw = await redis.hgetall(_job_redis_key(job_id))
    if not raw:
        raise HTTPException(status_code=404, detail="Job not found or expired")

    # App-wide Redis client uses decode_responses=False — decode bytes here.
    data: dict[str, str] = {
        (k.decode() if isinstance(k, bytes) else k): (v.decode() if isinstance(v, bytes) else v)
        for k, v in raw.items()
    }

    clips_raw = json.loads(data.get("clips", "[]"))
    clips = [ClipStatus(**c) for c in clips_raw]

    return ClipsStatusResponse(
        job_id=job_id,
        scenario_id=data.get("scenario_id", scenario_id),
        status=data.get("status", "pending"),
        total_clips=int(data.get("total_clips", 0)),
        completed_clips=int(data.get("completed_clips", 0)),
        clips=clips,
        error=data.get("error"),
    )


# ── GET /scenarios/{scenario_id}/clips/{turn_index} ──────────────────────────

@router.get("/scenarios/{scenario_id}/clips/{turn_index}")
async def get_clip(
    scenario_id: str,
    turn_index: int,
    x_scenario_key: str | None = Header(default=None),
):
    _check_key(x_scenario_key)

    path = _clips_dir(scenario_id) / f"turn{turn_index}.mp4"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Clip not found")

    return FileResponse(str(path), media_type="video/mp4")
