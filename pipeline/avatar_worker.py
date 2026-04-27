"""
pipeline/avatar_worker.py

Talking-avatar video generation for scenario dialog turns using D-ID.

generate_scenario_clips(scenario, output_dir, lang) → list[dict]

For each dialog turn, calls the D-ID /talks API to generate a short MP4 clip
of an avatar speaking the turn text. All talks are submitted in parallel, polled
concurrently, then results are written to {output_dir}/scenario_clips_{lang}.json.

Never crashes the pipeline — missing D_ID_API_KEY or API errors log a
warning and return an empty list.

Output file format (scenario_clips_{lang}.json):
  {
    "scenario_id": "...",
    "language": "en",
    "clips": [
      {
        "turn_index": 0,
        "speaker": "user1",
        "video_url": "https://d-id.com/...",
        "duration_seconds": 8.3,
        "status": "ready"
      }
    ],
    "generated_at": "..."
  }
"""

from __future__ import annotations

import base64
import json
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

log = logging.getLogger("pipeline.avatar_worker")

_D_ID_BASE = "https://api.d-id.com"
_POLL_INTERVAL = 3       # seconds between status polls per clip
_POLL_TIMEOUT  = 120     # seconds before giving up on a clip
_MAX_WORKERS   = 4       # parallel D-ID submissions / polls

_DEFAULT_AVATARS = {
    "female": "https://d-id-public-bucket.s3.us-east-1.amazonaws.com/alice.jpg",
    "male":   "https://d-id-public-bucket.s3.us-east-1.amazonaws.com/alice.jpg",
}

_VOICES_EN = ["en-US-JennyNeural", "en-US-GuyNeural", "en-US-AriaNeural"]
_VOICES_FR = ["fr-FR-DeniseNeural", "fr-FR-HenriNeural"]
_VOICES_ES = ["es-ES-ElviraNeural", "es-ES-AlvaroNeural"]
_VOICES_BY_LANG = {"en": _VOICES_EN, "fr": _VOICES_FR, "es": _VOICES_ES}


# ── Public API ────────────────────────────────────────────────────────────────

def generate_scenario_clips(
    scenario: dict,
    output_dir: str,
    lang: str = "en",
    on_clip_submitted: Callable[[int], None] | None = None,
    on_clip_ready: Callable[[int], None] | None = None,
) -> list[dict]:
    """
    Generate talking-avatar clips for every dialog turn, in parallel.

    Args:
        scenario:          Parsed scenario JSON dict.
        output_dir:        Directory; scenario_clips_{lang}.json is written here.
        lang:              Language code — controls voice selection.
        on_clip_submitted: Optional callback(turn_index) fired after each D-ID POST.
        on_clip_ready:     Optional callback(turn_index) fired after each clip is ready.

    Returns:
        List of clip metadata dicts ordered by turn_index.
        Empty list if D-ID is disabled or any clip fails.
    """
    api_key = _api_key()
    if not api_key:
        log.info("avatar_skip: D_ID_API_KEY not configured")
        return []

    try:
        import httpx  # noqa: F401
    except ImportError:
        log.warning("avatar_skip: httpx not installed")
        return []

    auth = _auth_header(api_key)
    chars = scenario.get("characters", [])
    char_index = {c["id"]: i for i, c in enumerate(chars)}
    dialog = scenario.get("dialog", [])

    # ── Phase 1: Submit all talks in parallel ─────────────────────────────────
    log.info("avatar_submit_all count=%d", len(dialog))
    talk_ids: dict[int, str] = {}  # turn_index → talk_id

    def _submit(turn_index: int, turn: dict) -> tuple[int, str | None]:
        speaker_id = turn["speaker"]
        idx = char_index.get(speaker_id, 0)
        char = chars[idx] if idx < len(chars) else {}
        avatar_url = _avatar_url(char, idx)
        voice_id = _voice(idx, lang)
        log.info("avatar_generating turn=%d speaker=%s voice=%s", turn_index, speaker_id, voice_id)
        talk_id = _create_talk(auth, turn["text"], avatar_url, voice_id)
        if talk_id and on_clip_submitted:
            on_clip_submitted(turn_index)
        return turn_index, talk_id

    with ThreadPoolExecutor(max_workers=_MAX_WORKERS) as pool:
        futures = {pool.submit(_submit, i, turn): i for i, turn in enumerate(dialog)}
        for future in as_completed(futures):
            turn_index, talk_id = future.result()
            if not talk_id:
                log.error("avatar_create_failed turn=%d", turn_index)
                return []
            talk_ids[turn_index] = talk_id

    # ── Phase 2: Poll all talks in parallel ───────────────────────────────────
    log.info("avatar_poll_all count=%d", len(talk_ids))
    results: dict[int, dict] = {}  # turn_index → D-ID result dict

    def _poll(turn_index: int, talk_id: str) -> tuple[int, dict | None]:
        result = _poll_talk(auth, talk_id)
        if result and on_clip_ready:
            on_clip_ready(turn_index)
        return turn_index, result

    with ThreadPoolExecutor(max_workers=_MAX_WORKERS) as pool:
        futures = {pool.submit(_poll, i, tid): i for i, tid in talk_ids.items()}
        for future in as_completed(futures):
            turn_index, result = future.result()
            if not result:
                log.error("avatar_timeout turn=%d", turn_index)
                return []
            results[turn_index] = result
            log.info("avatar_ready turn=%d url=%s", turn_index, result["result_url"])

    # ── Assemble ordered clip list ────────────────────────────────────────────
    clips: list[dict] = []
    for turn_index, turn in enumerate(dialog):
        result = results[turn_index]
        clips.append({
            "turn_index": turn_index,
            "speaker": turn["speaker"],
            "video_url": result["result_url"],
            "duration_seconds": result.get("duration", 0.0),
            "status": "ready",
        })

    out_path = Path(output_dir) / f"scenario_clips_{lang}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps({
        "scenario_id": scenario.get("scenario_id", ""),
        "language": lang,
        "clips": clips,
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
    }, indent=2))
    log.info("avatar_clips_written path=%s count=%d", out_path, len(clips))

    return clips


# ── Internals ─────────────────────────────────────────────────────────────────

def _api_key() -> str | None:
    if key := os.environ.get("D_ID_API_KEY"):
        return key
    try:
        from pipeline.config import settings
        return getattr(settings, "D_ID_API_KEY", None)
    except Exception:
        return None


def _auth_header(api_key: str) -> str:
    # D-ID keys are already in "base64(email):password" format — encode directly.
    encoded = base64.b64encode(api_key.encode()).decode()
    return f"Basic {encoded}"


def _avatar_url(char: dict, idx: int) -> str:
    if url := os.environ.get(f"D_ID_AVATAR_{idx}"):
        return url
    gender = char.get("gender", "female" if idx % 2 == 0 else "male")
    return _DEFAULT_AVATARS.get(gender, _DEFAULT_AVATARS["female"])


def _voice(idx: int, lang: str) -> str:
    voices = _VOICES_BY_LANG.get(lang, _VOICES_EN)
    return voices[min(idx, len(voices) - 1)]


def _create_talk(auth: str, text: str, source_url: str, voice_id: str) -> str | None:
    import httpx

    payload = {
        "source_url": source_url,
        "script": {
            "type": "text",
            "input": text,
            "provider": {"type": "microsoft", "voice_id": voice_id},
        },
        "config": {"fluent": True, "pad_audio": 0},
    }
    try:
        resp = httpx.post(
            f"{_D_ID_BASE}/talks",
            json=payload,
            headers={"Authorization": auth, "Content-Type": "application/json"},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json().get("id")
    except Exception as exc:
        log.error("avatar_create_error: %s", exc)
        return None


def _poll_talk(auth: str, talk_id: str) -> dict | None:
    import httpx

    deadline = time.time() + _POLL_TIMEOUT
    while time.time() < deadline:
        try:
            resp = httpx.get(
                f"{_D_ID_BASE}/talks/{talk_id}",
                headers={"Authorization": auth},
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            status = data.get("status")
            if status == "done":
                return data
            if status == "error":
                log.error("avatar_d_id_error talk_id=%s error=%s", talk_id, data.get("error"))
                return None
            time.sleep(_POLL_INTERVAL)
        except Exception as exc:
            log.error("avatar_poll_error: %s", exc)
            return None
    return None
