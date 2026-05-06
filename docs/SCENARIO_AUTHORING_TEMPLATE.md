# Scenario Authoring Template

> Fill out the fields below in plain prose. Hand the completed template back to broker and broker will:
> 1. Generate the merged scenario JSON (`web/data/scenarios/<slug>_en.json`)
> 2. Pre-generate stylized character portraits (so faces look the way you asked)
> 3. Run the D-ID pipeline (`pipeline/avatar_worker.py`) to make per-turn talking-avatar MP4s
> 4. Wire the scenario into the `/jt` landing page as a new use case
>
> **Required fields are marked ★.** Everything else has sensible defaults.

---

## 1. Use-Case Identity ★

| Field | Your value |
|---|---|
| One-line title (shown on landing card) | _e.g., "Inappropriate Workplace Talk — Code of Conduct"_ |
| Slug (URL-safe, kebab-case; broker can suggest) | _e.g., "in-office-behavior"_ |
| Domain / category | _e.g., Code of Conduct / FCPA / GDPR / Harassment / AML / Insider Trading_ |
| Card description (1–2 sentences) | _Two IT colleagues at SmallThings.com…_ |

---

## 2. Characters (one block per speaker; default 2, max 3)

Each character becomes a talking avatar. **Style preference is the lever for animation-vs-realism.**

### Character 1 ★

| Field | Your value |
|---|---|
| Display name | _e.g., "Jon Samual"_ |
| Role label (short, all-caps in player) | _e.g., "IT MANAGER"_ |
| Organisation | _e.g., "SmallThings.com"_ |
| Gender (drives default voice) | _male / female / non-binary_ |
| Approx age | _e.g., 45_ |
| Ethnicity (used by image generator for accurate representation) | _e.g., Caucasian / Hispanic / South Asian / East Asian / Black / Mixed_ |
| **Animation style ★** | **photorealistic / 3D-Pixar / 2D-cartoon / anime / claymation** |
| Voice tone (optional) | _friendly / authoritative / nervous / casual_ |
| Specific look notes (optional) | _e.g., "glasses, beard, navy blazer"_ |

### Character 2 ★

(same fields)

### Character 3 (optional)

(same fields)

---

## 3. Setting (optional)

| Field | Your value |
|---|---|
| Background | _office / conference room / boardroom / coffee shop / generic neutral_ |
| Tone (helps writing style) | _professional / casual / tense / urgent_ |

---

## 4. Dialog ★

> Write 2–6 turns. Each turn is **one** character speaking. Keep each turn under ~25s of speech (≈50 words) — D-ID generates per-turn, so shorter = faster + cheaper.

- **Turn 1** — speaker: _<character display name>_  
  Text: _"…"_
- **Turn 2** — speaker: _<character display name>_  
  Text: _"…"_
- **Turn 3** — speaker: _<character display name>_  
  Text: _"…"_

(continue as needed)

---

## 5. Quiz ★

| Field | Your value |
|---|---|
| Question | _"…"_ |
| Format | _true_false_ (MCQ supported but ask broker — needs a small renderer change) |
| Correct answer | _true / false_ |
| Explanation (1–4 sentences, shown after answer) | _"…"_ |

---

## 6. Localisation (optional)

| Field | Your value |
|---|---|
| Other languages to generate | _e.g., fr, es_ — broker runs the pipeline once per language; voice + dialog are per-language |

---

## 7. Special instructions / edge cases (optional)

_Anything broker should know — sensitive content warnings, deviation from defaults, unusual avatar look, references to real people/companies to avoid, etc._

---

## How your inputs map to D-ID parameters

For **each dialog turn**, broker submits to `POST https://api.d-id.com/talks`:

| Your input | D-ID parameter | Notes |
|---|---|---|
| Character + Animation style | `source_url` | URL of the character's image — **this is what determines whether the face is realistic or animated**. Photorealistic = real photo. 3D-Pixar/cartoon/anime = a stylized image broker pre-generates via Flux / Nano-Banana / GPT-Image. |
| Turn text | `script.input` | What the avatar says. |
| Character gender + voice tone + language | `script.provider.voice_id` | Microsoft Neural voice (e.g., `en-US-GuyNeural`, `en-US-JennyNeural`, `en-US-AriaNeural`). D-ID also supports ElevenLabs / Amazon / Google providers if needed. |
| (default) | `config.fluent: true` | Smooth lip-sync. |
| (default) | `config.pad_audio: 0` | No leading silence. |

D-ID returns an MP4 URL → broker downloads it → saves to `web/public/scenarios/<slug>/turn{N}.mp4` → wires into the registry → renders via `<ScenarioVideoPlayer />`.

---

## Animation-style options — how to get the look you want

The face style is **entirely determined by the source image**. The path is the same for all styles; only the image changes.

| Style | Source image | When to use |
|---|---|---|
| **Photorealistic** *(today's default)* | A real headshot photo (current default = D-ID's "Alice" image, hard-coded) | Compliance training, corporate rigor |
| **3D Pixar-style** | Stylized 3D-render portrait (broker generates) | Approachable, friendly — works for most internal training |
| **2D cartoon / illustrated** | 2D character art (broker generates) | Kids, playful tone, social-story format (Silas use case) |
| **Anime** | Anime-style portrait | Energetic, youth-oriented |
| **Claymation / 3D toy** | Stop-motion / toy-render look | Memorable, quirky, experimental |

**To switch from today's photoreal default to animation:**
1. Pick a style per character (`Animation style` field above).
2. broker generates a 1024×1024 portrait per character with a prompt template like:
   > *"[Style] portrait, [age]-year-old [gender] [ethnicity] [role], [look notes], plain neutral background, soft even lighting, head-and-shoulders, looking at camera, slight friendly expression"*
3. broker hosts the image at `web/public/avatars/<slug>-<character-id>.png` (Next.js dev server already serves `/public/`, so the URL is reachable by D-ID).
4. broker passes that public URL as `source_url` instead of the default Alice photo.

**Small wiring patch needed (not done yet):** `pipeline/avatar_worker.py` currently picks the source via `D_ID_AVATAR_<idx>` env vars. The clean fix is to read a `source_image_url` field on each character entry. ~2 lines. broker can apply this when you start using the template.

---

## Cost note (D-ID)

Each dialog turn = one `/talks` call ≈ 5–10 D-ID credits depending on speech length. A 3-turn EN scenario ≈ 15–30 credits. Multi-language multiplies linearly. Generation runs in parallel (up to 4 concurrent talks).

---

## Worked example (filled template — `in-office-behavior`)

For reference, the in-office-behavior scenario maps to:

| Field | Value |
|---|---|
| Title | Inappropriate Workplace Talk — Code of Conduct |
| Slug | in-office-behavior |
| Domain | Code of Conduct |
| Description | "Two IT colleagues at SmallThings.com talk about a female coworker's dress and looks…" |
| Character 1 | Jon Samual · IT MANAGER · SmallThings.com · male · 45 · Caucasian · *(today: photorealistic — defaulted)* |
| Character 2 | Jack Riaz · IT OPERATOR · SmallThings.com · male · 35 · Hispanic · *(today: photorealistic — defaulted)* |
| Dialog | 3 turns (Jon → Jack → Jon) |
| Quiz | T/F — "Is this appropriate office conversation, even though no derogatory language…?" → false |

*If you re-run that scenario with `Animation style: 3D-Pixar` set on each character, broker will pre-generate two Pixar-style portraits, host them, and the regenerated MP4s will look animated rather than realistic.*
