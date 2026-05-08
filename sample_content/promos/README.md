# Promo Videos — Operator Guide

Two ~3:12 product-showcase videos used on the public landing pages
`/demo/teacher-story` and `/demo/student-story`. Built with Remotion
4 + AWS Polly neural voices.

| Story | Path | Voice | Audience |
|---|---|---|---|
| Teacher — *How a Lesson Gets Built* | `teacher-story/Option3_Video/` | Polly Joanna | School admins, teachers, prospects |
| Student — *What's Inside a Lesson* | `student-story/Option3_Video/` | Polly Salli | Students, parents |

Both use the same kinetic visual vocabulary:
`TypeInText`, `ScopingHexagon`, `SlideInPanel`, `InsetVideoFrame`,
`StreamMontage`, `CursorTrace`, `ConfettiBurst` — all defined in
`<story>/Option3_Video/src/components/`.

---

## Render workflow

### 1. Render the narration WAVs

Two equivalent paths — **Piper is the default** because it runs locally
and needs no cloud account.

#### Option A — Piper (free, local, recommended)

One-time setup:

```bash
python3 -m venv /tmp/piper-venv
/tmp/piper-venv/bin/pip install piper-tts
mkdir -p /tmp/piper-voices && cd /tmp/piper-voices
curl -fsSLO "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium/en_US-amy-medium.onnx"
curl -fsSLO "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium/en_US-amy-medium.onnx.json"
curl -fsSLO "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx"
curl -fsSLO "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json"
```

Render:

```bash
cd sample_content/promos
/tmp/piper-venv/bin/python3 render_narration_piper.py teacher-story en_US-amy-medium
/tmp/piper-venv/bin/python3 render_narration_piper.py student-story en_US-lessac-medium
```

Cost: $0. Render time: ~30 seconds per story on CPU.

#### Option B — AWS Polly (paid, slightly higher quality)

```bash
cd sample_content/promos
./render_narration.sh teacher-story Joanna
./render_narration.sh student-story Salli
```

Note: outputs MP3 instead of WAV. To use Polly, also rename
`audioFile="slide-NN.wav"` → `slide-NN.mp3` in the 24 scene files
(`find sample_content/promos/{teacher,student}-story/Option3_Video/src/scenes -name '*.tsx' -exec sed -i 's/slide-\([0-9]\+\)\.wav/slide-\1.mp3/g' {} +`).

Cost: ~$0.10 per full render (Polly neural is $16 / 1M chars; both
narration sources together are ~5 K chars).

#### Why Piper outputs WAV (not MP3)

Piper's native output is WAV. Conversion to MP3 needs `ffmpeg`, which
isn't always installed. The Remotion `<Audio>` component plays WAV
just as well; the trade-off is file size (~5–6× larger) which doesn't
matter for the 12 MB-per-story scope here.

Both stories together drop 24 WAVs (~12 MB total) into
`<story>/Option3_Video/public/audio/slide-NN.wav`. Each scene's
`<SceneFrame audioFile="slide-NN.wav" />` references them by name.

### 2. Preview in Remotion Studio (interactive)

```bash
cd sample_content/promos/teacher-story/Option3_Video
bun install      # first time only
bun run studio   # opens http://localhost:3000
```

Studio gives you a scrubbable timeline + per-frame preview. Use this
to QA scene timings before rendering.

### 3. Render the final MP4

```bash
cd sample_content/promos/teacher-story/Option3_Video
bun run render        # MP4 → ~/Downloads/StudyBuddy_TeacherStory.mp4
bun run render:webm   # WebM (smaller, modern browsers only)
```

The default output path drops the file at `~/Downloads/`. Override
with the `--output` flag passed through to `remotion render`.

### 4. Publish to the demo site

The web landing pages reference each MP4 at
`/content/promos/StudyBuddy_TeacherStory.mp4` and
`/content/promos/StudyBuddy_StudentStory.mp4`. Copy the rendered
MP4s into the content store under those paths:

```bash
cp ~/Downloads/StudyBuddy_TeacherStory.mp4 \
  /data/content/promos/StudyBuddy_TeacherStory.mp4
cp ~/Downloads/StudyBuddy_StudentStory.mp4 \
  /data/content/promos/StudyBuddy_StudentStory.mp4
```

(Adjust path to match `CONTENT_STORE_PATH` on the deployment target.)

---

## Editing scenes

Each slide is one self-contained component under `src/scenes/`.
The 12 components are wired into `src/Root.tsx` as sequential
`<Sequence>` blocks at 16-second intervals (480 frames at 30 fps).

To change the cadence — e.g., make slide 5 last 20 seconds instead
of 16 — edit `src/Root.tsx` directly:

```tsx
<Sequence from={4 * 480} durationInFrames={600}>  // 600 = 20s × 30fps
  <Slide05_LessonImages />
</Sequence>
```

Then update the slide's narration block in `audio/narration.ssml`
to fit the new duration.

---

## Visual vocabulary — when to use which component

| Component | Use for | Used in |
|---|---|---|
| `TypeInText` | Building anticipation, simulating real-time generation | Story A: 1, 2, 4 · Story B: 1, 2, 3 |
| `ScopingHexagon` | The six-dimension scoped-retrieval reveal | Story A: 3 |
| `SlideInPanel` | Image / quiz / feedback panels with motion-blur | Story A: 5, 7 · Story B: 4, 6 |
| `InsetVideoFrame` | "There's a video inside the lesson" beat | Story A: 6 · Story B: 5 |
| `StreamMontage` | "Same engine, different stream" rapid-cut sequence | Story A: 9 · Story B: 11 |
| `CursorTrace` | Demonstrating a UI interaction (toggle, click-to-expand) | Story A: 10, 11 · Story B: 10 |
| `ConfettiBurst` | Earned celebration — used **once** per video at most | Story B: 9 (12-night streak) |

---

## Captions / accessibility

Every `SceneFrame` renders a lower-third caption mirroring the
narration. Captions fade in over frames 15–30 and hold through 450,
giving silent / muted-autoplay viewers full content access.

The two CTA pills on slide 12 are large, high-contrast, and
center-stacked to meet WCAG 2.1 AA contrast requirements.

---

## Costs (per regenerate)

| Item | Piper (default) | Polly (alternate) |
|---|---|---|
| Narration (12 slides × 2 stories) | $0.00 | ~$0.20 |
| Remotion render (local CPU) | $0.00 | $0.00 |
| **Total per regen** | **$0.00** | **~$0.20** |

Both paths produce comparable audio quality for English content.
Polly's neural voices have slightly more natural prosody on long
sentences; Piper's `medium`-tier voices (Amy, Lessac) sound very
close and are indistinguishable to most listeners on first pass.
