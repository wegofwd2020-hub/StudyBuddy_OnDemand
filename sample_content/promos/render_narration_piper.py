#!/usr/bin/env python3
"""Render per-slide narration WAVs from `narration.ssml` via Piper TTS.

Piper does not parse SSML; we strip tags and convert `<break time="Xms"/>`
to inline punctuation (commas / periods / ellipses) that Piper renders as
audible pauses of comparable duration.

Usage:
    python3 render_narration_piper.py <story-dir> <voice-name>

Examples:
    python3 render_narration_piper.py teacher-story en_US-amy-medium
    python3 render_narration_piper.py student-story en_US-lessac-medium

Pre-reqs:
    - Piper installed at /tmp/piper-venv/bin/piper
    - Voice model + config at /tmp/piper-voices/<voice-name>.onnx{,.json}
    - sample_content/promos/<story-dir>/audio/narration.ssml exists

Outputs:
    sample_content/promos/<story-dir>/Option3_Video/public/audio/slide-NN.wav
"""
from __future__ import annotations

import re
import shutil
import struct
import subprocess
import sys
import wave
from pathlib import Path

# Target headroom — 0.85 × 32767 ≈ 27851 — leaves 15 % below the 16-bit
# ceiling. Lower is quieter / more conservative; higher risks the
# inter-sample peaks Piper occasionally produces still saturating.
PEAK_HEADROOM_RATIO = 0.85
TARGET_PEAK_INT16 = int(32767 * PEAK_HEADROOM_RATIO)

PIPER_BIN = Path("/tmp/piper-venv/bin/piper")
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
    def break_repl(m: re.Match[str]) -> str:
        ms = int(m.group(1))
        return "\n\n" if ms >= 500 else "\n"

    text = BREAK_RE.sub(break_repl, ssml)
    text = TAG_RE.sub("", text)
    # Collapse runs of intra-line whitespace, but preserve newline structure.
    lines = [re.sub(r"[ \t]+", " ", ln).strip() for ln in text.splitlines()]
    # Drop empty leading/trailing lines but keep internal blank lines (which
    # Piper interprets as a longer pause).
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


def normalize_wav_peak(path: Path, target_peak: int = TARGET_PEAK_INT16) -> tuple[int, int]:
    """Re-scale a 16-bit mono PCM WAV so peak amplitude == `target_peak`.

    Piper's `--volume` flag is applied before int16 conversion; on some
    inputs the model produces inter-sample peaks that overflow int16
    anyway, leaving a flat-topped waveform with audible digital clipping.
    Post-processing the rendered WAV is the only reliable fix.

    Returns (original_peak, new_peak) for telemetry.
    """
    with wave.open(str(path), "rb") as r:
        n_channels = r.getnchannels()
        sample_width = r.getsampwidth()
        frame_rate = r.getframerate()
        n_frames = r.getnframes()
        raw = r.readframes(n_frames)

    if sample_width != 2 or n_channels != 1:
        # We only handle 16-bit mono. Piper's defaults match this; refuse
        # silently rather than corrupting an unexpected file.
        return (0, 0)

    samples = list(struct.unpack(f"<{len(raw) // 2}h", raw))
    original_peak = max(abs(s) for s in samples) or 1
    if original_peak <= target_peak:
        return (original_peak, original_peak)

    scale = target_peak / original_peak
    scaled = [max(-32768, min(32767, int(s * scale))) for s in samples]
    new_peak = max(abs(s) for s in scaled)
    new_raw = struct.pack(f"<{len(scaled)}h", *scaled)

    with wave.open(str(path), "wb") as w:
        w.setnchannels(n_channels)
        w.setsampwidth(sample_width)
        w.setframerate(frame_rate)
        w.writeframes(new_raw)
    return (original_peak, new_peak)


def render_block(slide_name: str, text: str, voice: str, out_dir: Path) -> Path:
    out_path = out_dir / f"{slide_name}.wav"
    model = VOICES_DIR / f"{voice}.onnx"
    cmd = [
        str(PIPER_BIN),
        "-m", str(model),
        "-f", str(out_path),
        # Add ~250 ms of silence between sentences so the pauses we
        # emitted as periods land naturally.
        "--sentence-silence", "0.25",
    ]
    proc = subprocess.run(
        cmd,
        input=text,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0 or not out_path.exists():
        sys.stderr.write(f"piper failed for {slide_name}:\n{proc.stderr}\n")
        raise SystemExit(1)
    return out_path


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
    if not (VOICES_DIR / f"{voice}.onnx").exists():
        sys.stderr.write(f"voice model missing: {VOICES_DIR / (voice + '.onnx')}\n")
        return 1
    if not PIPER_BIN.exists():
        sys.stderr.write(f"piper binary missing: {PIPER_BIN}\n")
        return 1

    out_dir.mkdir(parents=True, exist_ok=True)
    blocks = parse_ssml_blocks(narration_path)
    if not blocks:
        sys.stderr.write("no SSML blocks found in source\n")
        return 1

    print(f"rendering {len(blocks)} blocks to {out_dir} (voice={voice})")
    for slide_name, text in blocks:
        path = render_block(slide_name, text, voice, out_dir)
        original_peak, new_peak = normalize_wav_peak(path)
        # Brief preview of what Piper saw: first 60 chars of the cleaned text.
        preview = text[:60].replace("\n", " ⏎ ") + ("…" if len(text) > 60 else "")
        size_kb = path.stat().st_size // 1024
        norm_note = (
            ""
            if original_peak == new_peak
            else f"  (normalised {original_peak} → {new_peak})"
        )
        print(f"  {slide_name}: {size_kb} KB  peak={new_peak}{norm_note}  | {preview}")

    print(f"done — {len(blocks)} clips in {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
