"""
pipeline/build_unit.py

Core unit build logic for the StudyBuddy content pipeline.

build_unit(curriculum_id, unit_id, unit_data, lang, config, force=False) -> dict

Generates lesson, 3 quiz sets, tutorial, and (if has_lab) experiment content
for a single unit + language combination using the Claude API.

CLI usage:
  python pipeline/build_unit.py \\
      --curriculum-id default-2026-g8 \\
      --unit G8-MATH-001 \\
      --lang en \\
      [--force] \\
      [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from typing import Any

import jsonschema

# Allow running as a script from the repo root
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from pipeline.alex_runner import run_alex
from pipeline.prompts import (
    build_experiment_prompt,
    build_lesson_prompt,
    build_quiz_prompt,
    build_tutorial_prompt,
)
from pipeline.schemas import (
    validate_experiment,
    validate_lesson,
    validate_quiz,
    validate_tutorial,
)
from pipeline.tts_worker import synthesize_lesson

log = logging.getLogger("pipeline.build_unit")


class SpendCapExceeded(Exception):
    """Raised when the estimated pipeline cost exceeds MAX_PIPELINE_COST_USD."""
    pass


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _call_claude(client: Any, model: str, prompt: str) -> tuple[str, int, int]:
    """
    Call Claude and return (response_text, input_tokens, output_tokens).
    """
    message = client.messages.create(
        model=model,
        max_tokens=8192,
        messages=[{"role": "user", "content": prompt}],
    )
    text = message.content[0].text if message.content else ""
    input_tokens = message.usage.input_tokens if message.usage else 0
    output_tokens = message.usage.output_tokens if message.usage else 0
    return text, input_tokens, output_tokens


def _parse_json_response(text: str) -> dict:
    """
    Extract JSON from a Claude response.
    Strips markdown fences if present.
    """
    text = text.strip()
    # Strip ```json ... ``` fences
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first and last fence lines
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return json.loads(text)


def _generate_and_validate(
    client: Any,
    model: str,
    prompt: str,
    validator: Any,
    content_type: str,
    max_retries: int = 3,
) -> tuple[dict, int, int]:
    """
    Call Claude, parse JSON, validate schema. Retry up to max_retries times.

    Returns (data, total_input_tokens, total_output_tokens).
    Raises RuntimeError if all retries fail.
    """
    total_in = 0
    total_out = 0
    last_error = None

    for attempt in range(1, max_retries + 1):
        try:
            text, in_tok, out_tok = _call_claude(client, model, prompt)
            total_in += in_tok
            total_out += out_tok

            data = _parse_json_response(text)
            validator(data)
            return data, total_in, total_out

        except json.JSONDecodeError as exc:
            last_error = f"JSON parse error (attempt {attempt}): {exc}"
            log.warning("generate_retry json_error attempt=%d content_type=%s error=%s", attempt, content_type, exc)
        except jsonschema.ValidationError as exc:
            last_error = f"Schema validation error (attempt {attempt}): {exc.message}"
            log.warning("generate_retry schema_error attempt=%d content_type=%s error=%s", attempt, content_type, exc.message)
        except Exception as exc:
            last_error = f"Unexpected error (attempt {attempt}): {exc}"
            log.warning("generate_retry unexpected attempt=%d content_type=%s error=%s", attempt, content_type, exc)

    raise RuntimeError(
        f"Failed to generate valid {content_type} after {max_retries} attempts. Last error: {last_error}"
    )


def _all_files_exist(store_path: str, lang: str, has_lab: bool) -> bool:
    """Check whether all expected content files exist for this unit/lang."""
    expected = [
        f"lesson_{lang}.json",
        f"quiz_set_1_{lang}.json",
        f"quiz_set_2_{lang}.json",
        f"quiz_set_3_{lang}.json",
        f"tutorial_{lang}.json",
    ]
    if has_lab:
        expected.append(f"experiment_{lang}.json")

    return all(os.path.exists(os.path.join(store_path, f)) for f in expected)


def build_unit(
    curriculum_id: str,
    unit_id: str,
    unit_data: dict,
    lang: str,
    config: Any,
    force: bool = False,
    dry_run: bool = False,
) -> dict:
    """
    Build content for a single unit + language.

    Args:
        curriculum_id: e.g. "default-2026-g8"
        unit_id:       e.g. "G8-MATH-001"
        unit_data:     dict with keys: title, description, has_lab, subject (injected)
        lang:          ISO 639-1 code e.g. "en"
        config:        PipelineSettings instance
        force:         Skip idempotency check and regenerate
        dry_run:       Log what would be done but don't call Claude or write files

    Returns:
        {unit_id, lang, tokens_used, cost_usd, duration_ms, alex_warnings, status}
    """
    start_ms = time.monotonic()

    store_path = os.path.join(
        config.CONTENT_STORE_PATH, "curricula", curriculum_id, unit_id
    )
    meta_path = os.path.join(store_path, "meta.json")

    title = unit_data.get("title", unit_id)
    subject = unit_data.get("subject", "")
    has_lab = unit_data.get("has_lab", False)
    grade = unit_data.get("grade", 8)

    # ── Idempotency check ─────────────────────────────────────────────────────
    if not force and os.path.exists(meta_path):
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)

        if (
            meta.get("content_version") == config.CONTENT_VERSION
            and lang in meta.get("langs_built", [])
            and _all_files_exist(store_path, lang, has_lab)
        ):
            log.info(
                "unit_skip unit_id=%s lang=%s content_version=%d (already built)",
                unit_id, lang, config.CONTENT_VERSION,
            )
            duration_ms = int((time.monotonic() - start_ms) * 1000)
            return {
                "unit_id": unit_id,
                "lang": lang,
                "tokens_used": 0,
                "cost_usd": 0.0,
                "duration_ms": duration_ms,
                "alex_warnings": 0,
                "status": "skipped",
            }

    if dry_run:
        log.info("dry_run unit_id=%s lang=%s (would generate content)", unit_id, lang)
        duration_ms = int((time.monotonic() - start_ms) * 1000)
        return {
            "unit_id": unit_id,
            "lang": lang,
            "tokens_used": 0,
            "cost_usd": 0.0,
            "duration_ms": duration_ms,
            "alex_warnings": 0,
            "status": "dry_run",
        }

    # ── Initialise Anthropic client ───────────────────────────────────────────
    try:
        import anthropic  # type: ignore
    except ImportError:
        raise RuntimeError(
            "anthropic SDK not installed. Run: pip install anthropic"
        )

    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    model = config.CLAUDE_MODEL

    total_input_tokens = 0
    total_output_tokens = 0
    generated_content: dict[str, dict] = {}
    failed = False
    fail_reason = ""

    try:
        # ── Lesson ────────────────────────────────────────────────────────────
        log.info("generating lesson unit_id=%s lang=%s", unit_id, lang)
        prompt = build_lesson_prompt(unit_id, subject, title, grade, lang)
        lesson_data, in_tok, out_tok = _generate_and_validate(
            client, model, prompt, validate_lesson, "lesson"
        )
        lesson_data["generated_at"] = _now_iso()
        lesson_data["model"] = model
        total_input_tokens += in_tok
        total_output_tokens += out_tok
        generated_content["lesson"] = lesson_data

        # ── 3 Quiz sets ───────────────────────────────────────────────────────
        for set_num in range(1, 4):
            log.info("generating quiz set=%d unit_id=%s lang=%s", set_num, unit_id, lang)
            prompt = build_quiz_prompt(unit_id, subject, title, grade, lang, set_num)
            quiz_data, in_tok, out_tok = _generate_and_validate(
                client, model, prompt, validate_quiz, f"quiz_set_{set_num}"
            )
            quiz_data["generated_at"] = _now_iso()
            quiz_data["model"] = model
            total_input_tokens += in_tok
            total_output_tokens += out_tok
            generated_content[f"quiz_{set_num}"] = quiz_data

        # ── Tutorial ─────────────────────────────────────────────────────────
        log.info("generating tutorial unit_id=%s lang=%s", unit_id, lang)
        prompt = build_tutorial_prompt(unit_id, subject, title, grade, lang)
        tutorial_data, in_tok, out_tok = _generate_and_validate(
            client, model, prompt, validate_tutorial, "tutorial"
        )
        tutorial_data["generated_at"] = _now_iso()
        tutorial_data["model"] = model
        total_input_tokens += in_tok
        total_output_tokens += out_tok
        generated_content["tutorial"] = tutorial_data

        # ── Experiment (has_lab only) ─────────────────────────────────────────
        if has_lab:
            log.info("generating experiment unit_id=%s lang=%s", unit_id, lang)
            prompt = build_experiment_prompt(unit_id, subject, title, grade, lang)
            exp_data, in_tok, out_tok = _generate_and_validate(
                client, model, prompt, validate_experiment, "experiment"
            )
            exp_data["generated_at"] = _now_iso()
            exp_data["model"] = model
            total_input_tokens += in_tok
            total_output_tokens += out_tok
            generated_content["experiment"] = exp_data

    except RuntimeError as exc:
        log.error("unit_failed unit_id=%s lang=%s error=%s", unit_id, lang, exc)
        failed = True
        fail_reason = str(exc)

    # ── Spend cap check ───────────────────────────────────────────────────────
    cost_usd = (
        total_input_tokens * config.TOKEN_COST_INPUT_USD
        + total_output_tokens * config.TOKEN_COST_OUTPUT_USD
    )
    # Note: SpendCapExceeded is checked by the caller (build_grade) across runs.
    # Here we check just this unit's cost in case it alone exceeds the cap.
    if cost_usd > config.MAX_PIPELINE_COST_USD:
        raise SpendCapExceeded(
            f"Unit {unit_id} cost ${cost_usd:.4f} exceeds MAX_PIPELINE_COST_USD=${config.MAX_PIPELINE_COST_USD}"
        )

    if failed:
        duration_ms = int((time.monotonic() - start_ms) * 1000)
        return {
            "unit_id": unit_id,
            "lang": lang,
            "tokens_used": total_input_tokens + total_output_tokens,
            "cost_usd": cost_usd,
            "duration_ms": duration_ms,
            "alex_warnings": 0,
            "status": "failed",
            "error": fail_reason,
        }

    # ── Run AlexJS per content type ───────────────────────────────────────────
    alex_warnings_by_type: dict[str, int] = {}
    for ct, text in _extract_text_for_alex_by_type(generated_content).items():
        alex_warnings_by_type[ct] = run_alex(text)["warnings_count"] if text else 0
    alex_warnings = sum(alex_warnings_by_type.values())

    # ── Write content files ───────────────────────────────────────────────────
    os.makedirs(store_path, exist_ok=True)

    _write_json(store_path, f"lesson_{lang}.json", generated_content["lesson"])
    for set_num in range(1, 4):
        _write_json(store_path, f"quiz_set_{set_num}_{lang}.json", generated_content[f"quiz_{set_num}"])
    _write_json(store_path, f"tutorial_{lang}.json", generated_content["tutorial"])
    if has_lab and "experiment" in generated_content:
        _write_json(store_path, f"experiment_{lang}.json", generated_content["experiment"])

    # ── TTS synthesis ─────────────────────────────────────────────────────────
    lesson_text = _lesson_to_speech_text(generated_content["lesson"])
    audio_path = os.path.join(store_path, f"lesson_{lang}.mp3")
    synthesize_lesson(lesson_text, lang, audio_path)

    # ── Upload to S3 (if configured) ──────────────────────────────────────────
    _upload_unit_to_s3(curriculum_id, unit_id, store_path, lang, has_lab)

    # ── Update meta.json ──────────────────────────────────────────────────────
    _update_meta(
        meta_path=meta_path,
        unit_id=unit_id,
        curriculum_id=curriculum_id,
        model=model,
        content_version=config.CONTENT_VERSION,
        lang=lang,
        alex_warnings_count=alex_warnings,
        alex_warnings_by_type=alex_warnings_by_type,
    )

    duration_ms = int((time.monotonic() - start_ms) * 1000)
    tokens_used = total_input_tokens + total_output_tokens

    log.info(
        json.dumps({
            "event": "unit_complete",
            "unit_id": unit_id,
            "lang": lang,
            "tokens": tokens_used,
            "cost_usd": round(cost_usd, 6),
            "duration_ms": duration_ms,
            "alex_warnings": alex_warnings,
        })
    )

    return {
        "unit_id": unit_id,
        "lang": lang,
        "tokens_used": tokens_used,
        "cost_usd": cost_usd,
        "duration_ms": duration_ms,
        "alex_warnings": alex_warnings,
        "status": "ok",
    }


def _write_json(directory: str, filename: str, data: dict) -> None:
    path = os.path.join(directory, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    log.debug("wrote %s", path)


def _upload_unit_to_s3(curriculum_id: str, unit_id: str, store_path: str, lang: str, has_lab: bool) -> None:
    """
    Upload all content files for a unit to S3 with correct Cache-Control headers.

    Cache-Control values per CLAUDE.md non-negotiable rule #7:
      - lesson JSON, quiz JSON, tutorial JSON, experiment JSON: max-age=3600  (1 hour)
      - lesson MP3:                                             max-age=86400 (24 hours)

    Silently skips if S3_BUCKET_NAME is not set or boto3 is not installed.
    """
    try:
        bucket = config.S3_BUCKET_NAME
    except (AttributeError, NameError):
        bucket = None

    if not bucket:
        return

    try:
        import boto3  # type: ignore
    except ImportError:
        log.debug("s3_upload_skip: boto3 not installed")
        return

    try:
        s3 = boto3.client("s3")
        prefix = f"curricula/{curriculum_id}/{unit_id}"

        json_files = [
            f"lesson_{lang}.json",
            f"quiz_set_1_{lang}.json",
            f"quiz_set_2_{lang}.json",
            f"quiz_set_3_{lang}.json",
            f"tutorial_{lang}.json",
        ]
        if has_lab:
            json_files.append(f"experiment_{lang}.json")

        for filename in json_files:
            local_path = os.path.join(store_path, filename)
            if not os.path.exists(local_path):
                continue
            s3.upload_file(
                local_path,
                bucket,
                f"{prefix}/{filename}",
                ExtraArgs={
                    "ContentType": "application/json",
                    "CacheControl": "max-age=3600",
                },
            )
            log.debug("s3_uploaded key=%s/%s", prefix, filename)

        # MP3 — 24hr Cache-Control
        mp3_filename = f"lesson_{lang}.mp3"
        mp3_local = os.path.join(store_path, mp3_filename)
        if os.path.exists(mp3_local):
            s3.upload_file(
                mp3_local,
                bucket,
                f"{prefix}/{mp3_filename}",
                ExtraArgs={
                    "ContentType": "audio/mpeg",
                    "CacheControl": "max-age=86400",
                },
            )
            log.debug("s3_uploaded key=%s/%s", prefix, mp3_filename)

        log.info("s3_unit_uploaded curriculum_id=%s unit_id=%s lang=%s", curriculum_id, unit_id, lang)

    except Exception as exc:
        log.warning("s3_upload_failed curriculum_id=%s unit_id=%s lang=%s error=%s", curriculum_id, unit_id, lang, exc)


def _extract_text_for_alex_by_type(content: dict) -> dict[str, str]:
    """Return {content_type: text} for per-type AlexJS analysis."""
    result: dict[str, str] = {}

    if "lesson" in content:
        lesson = content["lesson"]
        parts: list[str] = [lesson.get("synopsis", "")]
        parts.extend(lesson.get("key_concepts", []))
        parts.extend(lesson.get("learning_objectives", []))
        result["lesson"] = "\n".join(p for p in parts if p)

    for set_num in range(1, 4):
        key = f"quiz_{set_num}"
        if key in content:
            parts = []
            for q in content[key].get("questions", []):
                parts.append(q.get("question_text", ""))
                parts.append(q.get("explanation", ""))
                for opt in q.get("options", []):
                    parts.append(opt.get("text", ""))
            result[f"quiz_set_{set_num}"] = "\n".join(p for p in parts if p)

    if "tutorial" in content:
        tutorial = content["tutorial"]
        parts = []
        for section in tutorial.get("sections", []):
            parts.append(section.get("content", ""))
            parts.extend(section.get("examples", []))
            parts.append(section.get("practice_question", ""))
        parts.extend(tutorial.get("common_mistakes", []))
        result["tutorial"] = "\n".join(p for p in parts if p)

    if "experiment" in content:
        exp = content["experiment"]
        parts = list(exp.get("materials", []))
        parts.extend(exp.get("safety_notes", []))
        for step in exp.get("steps", []):
            parts.append(step.get("instruction", ""))
            parts.append(step.get("expected_observation", ""))
        parts.append(exp.get("conclusion_prompt", ""))
        result["experiment"] = "\n".join(p for p in parts if p)

    return result


def _lesson_to_speech_text(lesson: dict) -> str:
    """Convert lesson JSON to plain text suitable for TTS."""
    parts = [
        lesson.get("topic", ""),
        lesson.get("synopsis", ""),
    ]
    parts.extend(lesson.get("key_concepts", []))
    return " ".join(p for p in parts if p)


def _update_meta(
    meta_path: str,
    unit_id: str,
    curriculum_id: str,
    model: str,
    content_version: int,
    lang: str,
    alex_warnings_count: int,
    alex_warnings_by_type: dict[str, int] | None = None,
) -> None:
    """Read existing meta.json (if any), update, and write back."""
    if os.path.exists(meta_path):
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
    else:
        meta = {
            "unit_id": unit_id,
            "curriculum_id": curriculum_id,
            "langs_built": [],
        }

    meta["unit_id"] = unit_id
    meta["curriculum_id"] = curriculum_id
    meta["generated_at"] = _now_iso()
    meta["model"] = model
    meta["content_version"] = content_version
    meta["alex_warnings_count"] = alex_warnings_count
    meta["alex_warnings_by_type"] = alex_warnings_by_type or {}

    langs = meta.get("langs_built", [])
    if lang not in langs:
        langs.append(lang)
    meta["langs_built"] = langs

    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)


# ── CLI entry point ───────────────────────────────────────────────────────────

def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")

    parser = argparse.ArgumentParser(description="Build content for a single unit.")
    parser.add_argument("--curriculum-id", required=True, help="e.g. default-2026-g8")
    parser.add_argument("--unit", required=True, help="Unit ID e.g. G8-MATH-001")
    parser.add_argument("--lang", required=True, help="Language code e.g. en")
    parser.add_argument("--force", action="store_true", help="Rebuild even if already built")
    parser.add_argument("--dry-run", action="store_true", help="Log what would be done without calling Claude")
    parser.add_argument("--subject", default="", help="Subject name (optional override)")
    parser.add_argument("--title", default="", help="Unit title (optional override)")
    parser.add_argument("--grade", type=int, default=8, help="Grade number (default: 8)")
    parser.add_argument("--has-lab", action="store_true", help="Unit has a lab experiment")
    args = parser.parse_args()

    from pipeline.config import settings as config

    unit_data = {
        "title": args.title or args.unit,
        "description": "",
        "subject": args.subject,
        "has_lab": args.has_lab,
        "grade": args.grade,
    }

    result = build_unit(
        curriculum_id=args.curriculum_id,
        unit_id=args.unit,
        unit_data=unit_data,
        lang=args.lang,
        config=config,
        force=args.force,
        dry_run=args.dry_run,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
