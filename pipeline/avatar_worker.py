"""
pipeline/avatar_worker.py

Talking-avatar video generation for scenario dialog turns using D-ID.

generate_scenario_clips(scenario, output_dir, lang) → list[dict]

For each dialog turn, calls the D-ID /talks API to generate a short MP4 clip
of an avatar speaking the turn text. Polls until all clips are ready, then
writes the result to {output_dir}/scenario_clips_{lang}.json.

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
from datetime import datetime, timezone
from pathlib import Path

log = logging.getLogger("pipeline.avatar_worker")

_D_ID_BASE = "https://api.d-id.com"
_POLL_INTERVAL = 4       # seconds between status polls
_POLL_TIMEOUT  = 120     # seconds before giving up on a clip

# Default presenter image URLs — override per speaker via D_ID_AVATAR_0, D_ID_AVATAR_1 env vars.
# Both fall back to alice.jpg (confirmed working); override with your own hosted images for
# different-looking characters.
_DEFAULT_AVATARS = {
    "female": "https://d-id-public-bucket.s3.us-east-1.amazonaws.com/alice.jpg",
    "male":   "https://d-id-public-bucket.s3.us-east-1.amazonaws.com/alice.jpg",
}

# Microsoft Azure Neural voices available through D-ID — indexed by speaker position.
_VOICES_EN = ["en-US-JennyNeural", "en-US-GuyNeural",  "en-US-AriaNeural"]
_VOICES_FR = ["fr-FR-DeniseNeural", "fr-FR-HenriNeural"]
_VOICES_ES = ["es-ES-ElviraNeural",  "es-ES-AlvaroNeural"]
_VOICES_BY_LANG = {"en": _VOICES_EN, "fr": _VOICES_FR, "es": _VOICES_ES}


# ── Public API ────────────────────────────────────────────────────────────────

def generate_scenario_clips(
    scenario: dict,
    output_dir: str,
    lang: str = "en",
) -> list[dict]:
    """
    Generate a talking-avatar video clip for every dialog turn in scenario.

    Args:
        scenario:   Parsed scenario JSON dict (must contain 'characters' and 'dialog').
        output_dir: Directory path. scenario_clips_{lang}.json is written here.
        lang:       Language code — controls voice selection and output filename.

    Returns:
        List of clip metadata dicts. Empty list if D-ID is disabled or any
        clip fails (partial results are not written).
    """
    api_key = _api_key()
    if not api_key:
        log.info("avatar_skip: D_ID_API_KEY not configured")
        return []

    try:
        import httpx  # noqa: F401 — validate import before starting work
    except ImportError:
        log.warning("avatar_skip: httpx not installed")
        return []

    auth = _auth_header(api_key)
    chars = scenario.get("characters", [])
    char_index = {c["id"]: i for i, c in enumerate(chars)}

    clips: list[dict] = []
    for turn_index, turn in enumerate(scenario.get("dialog", [])):
        speaker_id = turn["speaker"]
        idx = char_index.get(speaker_id, 0)
        char = chars[idx] if idx < len(chars) else {}

        avatar_url = _avatar_url(char, idx)
        voice_id   = _voice(idx, lang)

        log.info("avatar_generating turn=%d speaker=%s voice=%s", turn_index, speaker_id, voice_id)

        talk_id = _create_talk(auth, turn["text"], avatar_url, voice_id)
        if not talk_id:
            log.error("avatar_create_failed turn=%d", turn_index)
            return []

        result = _poll_talk(auth, talk_id)
        if not result:
            log.error("avatar_timeout turn=%d talk_id=%s", turn_index, talk_id)
            return []

        clip = {
            "turn_index": turn_index,
            "speaker": speaker_id,
            "video_url": result["result_url"],
            "duration_seconds": result.get("duration", 0.0),
            "status": "ready",
        }
        clips.append(clip)
        log.info("avatar_ready turn=%d url=%s", turn_index, result["result_url"])

    output = {
        "scenario_id": scenario.get("scenario_id", ""),
        "language": lang,
        "clips": clips,
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
    }
    out_path = Path(output_dir) / f"scenario_clips_{lang}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, indent=2))
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
    # D-ID keys are already in "base64(email):password" format — the full
    # string is the Basic auth credential, so encode it directly.
    encoded = base64.b64encode(api_key.encode()).decode()
    return f"Basic {encoded}"


def _avatar_url(char: dict, idx: int) -> str:
    if url := os.environ.get(f"D_ID_AVATAR_{idx}"):
        return url
    # Alternate female/male by position; char dict may carry an explicit 'gender' hint.
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
