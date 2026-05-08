#!/usr/bin/env python3
"""Render per-slide narration WAVs from `narration.ssml` via Piper TTS.

Uses the Piper Python API (`PiperVoice.synthesize()`) rather than the CLI
because Piper's CLI int16 conversion uses numpy `astype(int16)`, which
wraps modulo when the model output exceeds [-1, 1] — producing sample-
level wraparound corruption that's audible as crackle / digital noise
and cannot be undone by post-process amplitude scaling. The Python API
exposes `AudioChunk.audio_float_array` so we can clip floats to [-1, 1]
*before* the int16 cast.

Piper does not parse SSML; we strip tags and convert `<break time="Xms"/>`
to inline newlines, then synthesize each line with inter-line silence to
mimic the SSML break.

Usage (must be run inside the Piper venv so `piper` imports cleanly):
    /tmp/piper-venv/bin/python3 render_narration_piper.py <story-dir> <voice>

Examples:
    /tmp/piper-venv/bin/python3 render_narration_piper.py teacher-story en_US-amy-medium
    /tmp/piper-venv/bin/python3 render_narration_piper.py student-story en_US-lessac-medium

Pre-reqs:
    - Piper installed in /tmp/piper-venv (with onnxruntime)
    - Voice model + config at /tmp/piper-voices/<voice>.onnx{,.json}
    - sample_content/promos/<story-dir>/audio/narration.ssml exists

Outputs:
    sample_content/promos/<story-dir>/Option3_Video/public/audio/slide-NN.wav
"""
from __future__ import annotations

import re
import struct
import sys
import wave
from pathlib import Path

import numpy as np
from piper import PiperVoice
from piper.config import SynthesisConfig

# Target headroom — peak amplitude after rendering.
# 0.90 × 32767 ≈ 29490 — leaves enough headroom that no sample saturates
# even on the noisy slides where the model output exceeds [-1, 1].
PEAK_HEADROOM_RATIO = 0.90
TARGET_PEAK_INT16 = int(32767 * PEAK_HEADROOM_RATIO)

# Leading silence prepended to every clip. Keeps the first word from
# feeling clipped — Piper starts speaking immediately, and the AAC
# encoder Remotion uses adds ~21 ms of priming silence that some
# players fade in over, which can chew the first phoneme. 1 s gives
# both a clear lead-in for the listener and headroom for codec quirks.
LEADING_SILENCE_SEC = 1.00

# Inter-line silence (seconds). One newline → silence_short. A blank line
# (two consecutive newlines) → silence_long, mapping the SSML 500ms+ break.
# Tuned to roughly match the original SSML break intent — 100 ms tracks
# the common 120-200 ms breaks; 300 ms tracks the 400-500 ms breaks.
# Larger values inflated several slides past the 16 s slide budget.
SILENCE_SHORT_SEC = 0.10
SILENCE_LONG_SEC = 0.30

VOICES_DIR = Path("/tmp/piper-voices")


# `<!-- slide-NN.mp3 -->` immediately preceding a <speak>...</speak> block.
SLIDE_HEADER_RE = re.compile(r"<!--\s*(slide-\d+)\.mp3\s*-->")
SPEAK_BLOCK_RE = re.compile(r"<speak>(.*?)</speak>", re.DOTALL)
BREAK_RE = re.compile(r'<break\s+time="(\d+)ms"\s*/>')
TAG_RE = re.compile(r"<[^>]+>")


def ssml_to_text(ssml: str) -> str:
    """Approximate SSML → plain-text conversion for Piper (one phrase per line).

    Each `<break time="Xms"/>` becomes a newline. Piper renders one line at
    a time and inserts `--sentence-silence` between them, so newline-as-
    pause maps cleanly onto SSML break semantics. Long breaks (≥ 500 ms)
    get a blank line for a doubled inter-phrase pause.

    All other tags are stripped. Punctuation that ends up adjacent to the
    newline (e.g. trailing comma from "topic," before a break) is preserved.
    """
    # The SSML source uses indentation + literal newlines for readability.
    # Those source-code newlines must NOT become inter-line silences;
    # only the explicit `<break>` tags should. Strip whitespace runs
    # (including newlines) BEFORE processing breaks so only break-induced
    # newlines survive.
    ssml = re.sub(r"\s+", " ", ssml)

    def break_repl(m: re.Match[str]) -> str:
        ms = int(m.group(1))
        return "\n\n" if ms >= 500 else "\n"

    text = BREAK_RE.sub(break_repl, ssml)
    text = TAG_RE.sub("", text)
    # Collapse runs of intra-line whitespace, preserving newline structure.
    lines = [re.sub(r"[ \t]+", " ", ln).strip() for ln in text.splitlines()]
    # Drop empty leading/trailing lines but keep internal blank lines.
    while lines and not lines[0]:
        lines.pop(0)
    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines)


def parse_ssml_blocks(narration_path: Path) -> list[tuple[str, str]]:
    """Return a list of (slide_name, text) tuples from a narration.ssml file.

    Walks the source line-by-line so each `<!-- slide-NN.mp3 -->` header
    stays paired with the very next `<speak>` block.
    """
    src = narration_path.read_text()
    out: list[tuple[str, str]] = []
    pos = 0
    while pos < len(src):
        header = SLIDE_HEADER_RE.search(src, pos)
        if not header:
            break
        slide_name = header.group(1)
        block = SPEAK_BLOCK_RE.search(src, header.end())
        if not block:
            raise ValueError(f"no <speak> block found after {slide_name} marker")
        text = ssml_to_text(block.group(1))
        out.append((slide_name, text))
        pos = block.end()
    return out


def synth_line(voice_obj: PiperVoice, line: str) -> np.ndarray:
    """Synthesize one line of text → float32 audio array in [-1, 1].

    Concatenates the float arrays from each AudioChunk so we operate on
    raw model output, not Piper's pre-int16-cast representation.
    """
    chunks: list[np.ndarray] = []
    for chunk in voice_obj.synthesize(line, syn_config=SynthesisConfig()):
        chunks.append(chunk.audio_float_array)
    if not chunks:
        return np.zeros(0, dtype=np.float32)
    return np.concatenate(chunks)


def render_block(
    slide_name: str,
    text: str,
    voice_obj: PiperVoice,
    sample_rate: int,
    out_dir: Path,
) -> tuple[Path, float, float]:
    """Render a multi-line text block to a WAV file.

    Empty lines insert SILENCE_LONG_SEC of silence; line breaks insert
    SILENCE_SHORT_SEC. Each non-empty line is synthesized separately so
    inter-line silence is exact rather than relying on Piper's prosody.

    Returns (path, raw_peak_float, output_peak_int16) for telemetry.
    The raw float peak tells us whether the model overshot [-1, 1] on
    this clip — values > 1.0 indicate the bug we're working around.
    """
    out_path = out_dir / f"{slide_name}.wav"

    short_silence = np.zeros(int(sample_rate * SILENCE_SHORT_SEC), dtype=np.float32)
    long_silence = np.zeros(int(sample_rate * SILENCE_LONG_SEC), dtype=np.float32)
    leading_silence = np.zeros(int(sample_rate * LEADING_SILENCE_SEC), dtype=np.float32)

    pieces: list[np.ndarray] = [leading_silence]
    lines = text.split("\n")
    prev_was_blank = True  # treat the leading silence as a "blank" so the
                            # first synthesized line isn't preceded by a
                            # short_silence on top of leading_silence.
    for line in lines:
        stripped = line.strip()
        if not stripped:
            if not prev_was_blank and pieces:
                pieces.append(long_silence)
            prev_was_blank = True
            continue
        if not prev_was_blank:
            pieces.append(short_silence)
        pieces.append(synth_line(voice_obj, stripped))
        prev_was_blank = False

    if not pieces:
        sys.stderr.write(f"empty render for {slide_name}\n")
        raise SystemExit(1)

    audio = np.concatenate(pieces)
    raw_peak = float(np.max(np.abs(audio))) if audio.size else 0.0

    # Saturate (clip) to [-1, 1] BEFORE int16 conversion. This is the
    # critical step that Piper's CLI gets wrong — np.clip + multiply +
    # round + astype guarantees no wraparound.
    audio = np.clip(audio, -1.0, 1.0)

    # Scale so peak == TARGET_PEAK_INT16. If raw_peak < 1 already, this
    # also normalises loudness across slides.
    if raw_peak > 0:
        # Use the *clipped* peak (capped at 1.0) so we get consistent
        # loudness even when the model overshoots.
        clipped_peak = min(raw_peak, 1.0)
        scale = (TARGET_PEAK_INT16 / 32767.0) / clipped_peak
        audio = audio * scale
        # `audio` is now in [-PEAK_HEADROOM_RATIO, PEAK_HEADROOM_RATIO].

    int16 = np.clip(np.round(audio * 32767.0), -32767, 32767).astype(np.int16)
    output_peak = int(np.max(np.abs(int16))) if int16.size else 0

    with wave.open(str(out_path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(int16.tobytes())

    return out_path, raw_peak, float(output_peak)


def main() -> int:
    if len(sys.argv) != 3:
        sys.stderr.write("usage: render_narration_piper.py <story-dir> <voice-name>\n")
        return 2

    story_dir = sys.argv[1]
    voice = sys.argv[2]

    repo_root = Path(__file__).resolve().parent
    narration_path = repo_root / story_dir / "audio" / "narration.ssml"
    out_dir = repo_root / story_dir / "Option3_Video" / "public" / "audio"

    if not narration_path.exists():
        sys.stderr.write(f"narration source missing: {narration_path}\n")
        return 1

    model_path = VOICES_DIR / f"{voice}.onnx"
    config_path = VOICES_DIR / f"{voice}.onnx.json"
    if not model_path.exists():
        sys.stderr.write(f"voice model missing: {model_path}\n")
        return 1

    out_dir.mkdir(parents=True, exist_ok=True)
    blocks = parse_ssml_blocks(narration_path)
    if not blocks:
        sys.stderr.write("no SSML blocks found in source\n")
        return 1

    print(f"loading voice: {voice}")
    voice_obj = PiperVoice.load(model_path, config_path=config_path)
    sample_rate = voice_obj.config.sample_rate

    print(f"rendering {len(blocks)} blocks to {out_dir}  (sample_rate={sample_rate})")
    overshoots = 0
    for slide_name, text in blocks:
        path, raw_peak, output_peak = render_block(
            slide_name, text, voice_obj, sample_rate, out_dir,
        )
        preview = text[:60].replace("\n", " ⏎ ") + ("…" if len(text) > 60 else "")
        size_kb = path.stat().st_size // 1024
        overshoot_note = ""
        if raw_peak > 1.0:
            overshoots += 1
            overshoot_note = f"  ⚠ raw float peak={raw_peak:.3f} (clipped pre-int16)"
        print(
            f"  {slide_name}: {size_kb} KB  out_peak={output_peak} "
            f"raw_peak={raw_peak:.3f}{overshoot_note}  | {preview}"
        )

    print(f"done — {len(blocks)} clips in {out_dir}")
    if overshoots:
        print(
            f"note: {overshoots} blocks had raw float output > 1.0 — these "
            "would have been corrupted by the CLI; the Python API path "
            "saturates them cleanly."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
