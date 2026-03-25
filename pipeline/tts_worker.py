"""
pipeline/tts_worker.py

Text-to-Speech synthesis for lesson audio MP3s.

synthesize_lesson(text, lang, output_path) → bool

Supports:
  - AWS Polly  (TTS_PROVIDER=polly)
  - Google TTS (TTS_PROVIDER=google)
  - No-op      (TTS_PROVIDER unset or libs not installed)

Never crashes the pipeline — missing TTS configuration logs a warning and
returns False.
"""

from __future__ import annotations

import logging
import os

log = logging.getLogger("pipeline.tts_worker")

# Voice mapping: ISO 639-1 lang code → Polly VoiceId
_POLLY_VOICES: dict = {
    "en": "Joanna",
    "fr": "Celine",
    "es": "Conchita",
}

# Voice mapping: lang code → Google TTS language code
_GOOGLE_LANG_CODES: dict = {
    "en": "en-US",
    "fr": "fr-FR",
    "es": "es-ES",
}


def synthesize_lesson(text: str, lang: str, output_path: str) -> bool:
    """
    Synthesise lesson text to an MP3 file at output_path.

    Args:
        text:        Plain text to convert to speech.
        lang:        ISO 639-1 language code (e.g. "en", "fr", "es").
        output_path: Absolute path where the MP3 should be written.

    Returns:
        True  — MP3 written successfully
        False — TTS disabled, provider missing, or synthesis failed
    """
    try:
        from pipeline.config import settings as pipeline_settings
        provider = pipeline_settings.TTS_PROVIDER
    except Exception:
        # If config cannot be imported (e.g. in tests), use env var directly.
        provider = os.environ.get("TTS_PROVIDER", "")

    if not provider:
        log.info("tts_disabled: no TTS_PROVIDER configured")
        return False

    provider = provider.lower().strip()

    if provider == "polly":
        return _synthesize_polly(text, lang, output_path)
    elif provider == "google":
        return _synthesize_google(text, lang, output_path)
    else:
        log.warning("tts_unknown_provider: %s", provider)
        return False


def _synthesize_polly(text: str, lang: str, output_path: str) -> bool:
    """Synthesise using AWS Polly via boto3."""
    try:
        import boto3  # type: ignore
    except ImportError:
        log.warning("tts_skip: boto3 not installed; cannot use Polly")
        return False

    voice_id = _POLLY_VOICES.get(lang, "Joanna")

    try:
        client = boto3.client("polly")
        response = client.synthesize_speech(
            Text=text,
            OutputFormat="mp3",
            VoiceId=voice_id,
            LanguageCode=_GOOGLE_LANG_CODES.get(lang, "en-US"),
        )

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(response["AudioStream"].read())

        log.info("tts_polly_ok: voice=%s path=%s", voice_id, output_path)
        return True

    except Exception as exc:
        log.error("tts_polly_error: %s", exc)
        return False


def _synthesize_google(text: str, lang: str, output_path: str) -> bool:
    """Synthesise using Google Cloud Text-to-Speech."""
    try:
        from google.cloud import texttospeech  # type: ignore
    except ImportError:
        log.warning("tts_skip: google-cloud-texttospeech not installed")
        return False

    lang_code = _GOOGLE_LANG_CODES.get(lang, "en-US")

    try:
        client = texttospeech.TextToSpeechClient()

        synthesis_input = texttospeech.SynthesisInput(text=text)
        voice = texttospeech.VoiceSelectionParams(
            language_code=lang_code,
            ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL,
        )
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3
        )

        response = client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config,
        )

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(response.audio_content)

        log.info("tts_google_ok: lang=%s path=%s", lang_code, output_path)
        return True

    except Exception as exc:
        log.error("tts_google_error: %s", exc)
        return False
