# Media Generation Services — Cost & Capability Comparison

> **Purpose:** plan media-generation spend across the StudyBuddy / `/jt` / `/stories` product lines.
> **Pricing as of:** late 2025 / early 2026 (broker training data). All numbers are list price in USD; verify the linked vendor pricing page before committing to any contract — these change quarterly.
> **Integration column:** "Drop-in" = swap one URL or model name in `pipeline/avatar_worker.py` or `~/.claude/skills/Art/Tools/Generate.ts`. "Adapter" = new provider class needed (~50–150 LOC). "Rewrite" = different output paradigm, substantial work.

---

## Quick-pick: which service for which job?

| Job-to-be-done | Recommended | Backup |
|---|---|---|
| Talking-head lipsync from a portrait | **D-ID** (current) — cheapest per minute | HeyGen (better avatar variety, no watermark on paid) |
| Talking-head with a *cartoon* character | **HeyGen** or **Synthesia** | (D-ID's face detector rejects non-human faces) |
| **Full animated story video, cartoon human chars, kid audience** | **Animaker** (API + 100+ kid-friendly chars) | **Vyond** (richer expression library, more expensive); **Plotagon** (kid-tuned but no API) |
| **Multi-scene cartoon narrative from text** | **Steve.AI** (AI text-to-video) | InVideo AI, Topview AI |
| Pixar/Disney-style human portrait | **Replicate Flux 1.1 Pro** | OpenAI gpt-image-2 (HD), Google Nano-Banana-Pro |
| Cheap illustration / iteration | **Replicate Flux Schnell** | Replicate Nano-Banana, Stability SD 3.5 |
| High-quality voice for narration | **ElevenLabs Multilingual v2** | Azure Neural (current, via D-ID) |
| Multilingual dubbing of existing video | **ElevenLabs Dubbing** | HeyGen Translate, Rask AI |
| General text-to-video (no specific character) | **Runway Gen-3 Alpha** | Google Veo 3, Pika, Kling |
| Cinematic music bed | **Suno v4** | Udio, ElevenLabs Music |
| Background-music removal / clean up | **Cleanvoice** or **Adobe Podcast** | Krisp, Auphonic |

---

## 1. Talking-head / Lipsync Video

The most directly relevant category — current pipeline runs through D-ID's `/talks` API in `pipeline/avatar_worker.py`.

| Service | Entry tier | Per-minute cost | Watermark policy | Avatar variety | Code change to adopt |
|---|---|---|---|---|---|
| **D-ID** *(current)* | Lite ~$5.90/mo (10 cr) | ~$0.20–0.30/credit; ~$1–2 per dialog turn | Lite tier shows "AI" or "D-iD" corner badge; **Pro+ ($50/mo) removes watermark** | ~40 public Studio Adults, photorealistic 3D humans only; no cartoon/animal faces | Drop-in (zero) |
| **HeyGen** | Creator $24/mo, 15 min | ~$0.40–1.60/min depending on tier | None on paid; watermark on Free | 100+ avatars **including cartoon/2D/anime**; supports custom avatars from selfie | Adapter (~120 LOC; different talk-creation API) |
| **Synthesia** | Starter $22/mo, 10 min | ~$0.73–2.20/min | None on paid | 230+ avatars across photoreal + stylized; 140+ languages | Adapter (~150 LOC) |
| **Tavus** | Developer $59/mo, 100 min | ~$0.59/min | None on paid | Custom avatars (replicas) — needs 2-min training video per avatar | Adapter (~100 LOC) |
| **Hour One** | Lite $25/mo, 10 min | ~$2.50/min | None on paid | 100+ photoreal "presenters"; less variety than HeyGen | Adapter (~100 LOC) |
| **AKOOL** | Lite $7.99/mo, 10 cr | ~$0.80–2/min | None on paid | Strong on face-swap + custom avatars; supports anime/cartoon | Adapter (~120 LOC) |
| **ElevenLabs Studios** | Per-character pricing | ~$0.05–0.10/sec | None on paid | Limited avatar set, but voice quality is best-in-class | Adapter (~120 LOC) |
| **Argil** | $39/mo+ | ~$0.50–1/min | None on paid | Custom avatars from selfie video | Adapter (~100 LOC) |

**Cost-per-deliverable for our actual scenarios:**

- 4-turn FCPA scenario (~57s dialog): D-ID **$5–8** | HeyGen **$1–2** | Synthesia **$2–4** | Tavus **$1**
- 12-turn social story (~82s dialog): D-ID **$15–18** | HeyGen **$1.5–3** | Synthesia **$2–4** | Tavus **$1.50**

D-ID is cheapest for our bursty usage *if* we stay on Lite, but the per-minute price doesn't drop with scale. HeyGen/Synthesia have monthly minimums but win at >5 min/month.

**Critical capability gaps for our use case:**

- **D-ID rejects non-human faces.** Confirmed empirically 2026-05-05 — ABSI polar bears all returned `FaceError: face not detected`. To deliver a true cartoon look (animal characters or Pixar 2D illustration), we would have to switch to HeyGen or Synthesia, or use a Pixar-style **human** image (which D-ID accepts).
- **D-ID has no child voices in the public catalog.** Workaround: use Microsoft Azure `en-US-AnaNeural` via TTS injection (requires patching `_create_talk` in `avatar_worker.py` to support custom `voice_id`).
- **D-ID watermark on Lite tier** is a corner badge; acceptable for prototypes, blocking for production B2B demos. Pro tier ($50/mo) removes it.

---

## 2. Image Generation (text-to-image)

For character portraits feeding into D-ID `source_url`, or for blog hero images, content illustrations, etc.

| Service | Per-image cost (1024×1024) | Quality tier | Style strengths | Code change |
|---|---|---|---|---|
| **OpenAI gpt-image-2** | Standard $0.04 / HD $0.17 | High at HD; can handle text-in-image well | Photorealism, illustration, technical diagrams | Drop-in (`Generate.ts` already supports) |
| **Replicate Flux 1.1 Pro** | ~$0.04 | High | **Best-in-class for Pixar-style human portraits**, photoreal | Drop-in |
| **Replicate Flux Pro Ultra** | ~$0.06 | Very high | Same as 1.1 Pro + better detail at 4K | Drop-in |
| **Replicate Flux Schnell** | ~$0.003 | Medium-high | Fast iteration, good general quality, 4-step inference | Drop-in |
| **Replicate Nano-Banana** *(Stability AI Stable Diffusion 3.5 Medium)* | ~$0.005 | Medium | Strong general-purpose, weakest at faces | Drop-in |
| **Google Nano-Banana-Pro** *(Imagen 4 / Gemini 3 Pro Image)* | ~$0.02–0.10 | High | Excellent character consistency, prompt following | Drop-in |
| **Midjourney** | $10–60/mo subscription | Best aesthetic quality in industry | Cinematic, stylized; **no public API** (Discord-only) | Rewrite |
| **Adobe Firefly** | Free w/ Creative Cloud or $4.99/mo | Medium | Commercially safe (trained only on licensed Adobe Stock) | Adapter (~100 LOC) |
| **Ideogram** | $7–20/mo | High at typography | Best for text-in-image, posters, logos | Adapter (~80 LOC) |
| **Recraft** | $12–22/mo | High at vector | Best for SVG / vector illustration output | Adapter |
| **Black Forest Labs direct** | Pay-as-you-go ~$0.04 | Same as Replicate-hosted Flux | Direct API (skip Replicate fee) | Adapter (~80 LOC) |

**Cost for our use case (4 character portraits per scenario):**

- Pixar-style human cast for a social story: 4 × $0.04 (Flux 1.1 Pro) = **$0.16** total
- Same on gpt-image-2 HD: 4 × $0.17 = **$0.68**
- Same on Flux Schnell for rough iteration: 4 × $0.003 = **$0.012**

**Recommendation:** generate at Flux Schnell ($0.012) for iteration, then re-render the chosen one at Flux 1.1 Pro ($0.04) for the production portrait. Even at full HD across 5 distinct characters, image gen is **<$1 per scenario**, dwarfed by D-ID rendering.

---

## 3. Text-to-Speech (voiceovers, narration, audio for video)

Currently we get TTS *through* D-ID (Microsoft Azure Neural via `provider.type: microsoft`). For higher-quality standalone narration or to bypass D-ID's voice constraints, direct TTS providers:

| Service | Cost per 1K chars | Voice quality | Voice variety | Multilingual | Latency | Code change |
|---|---|---|---|---|---|---|
| **Microsoft Azure Neural TTS** *(current via D-ID)* | $0.016 (Standard) / $0.024 (Neural) | Very good | 400+ voices, 140 langs | Excellent | <500ms | Drop-in (D-ID forwards) |
| **OpenAI TTS** | $0.015 (tts-1) / $0.030 (tts-1-hd) | Good | 6 voices | Limited (English-tuned) | <1s | Adapter (~50 LOC) |
| **ElevenLabs Multilingual v2** | $0.30 (Pro tier; ~$0.06 amortized on $99/mo plan) | **Best in class** — emotion + style support | 1000+ voices + voice clone | 29 langs | <1s | Adapter (~80 LOC) |
| **ElevenLabs Turbo v2.5** | ~$0.18 amortized | Very good | Same library | 32 langs | <300ms | Adapter |
| **Cartesia Sonic** | $0.02–0.05 | Very good | 20+ voices | Limited | <100ms (industry-leading) | Adapter (~80 LOC) |
| **PlayHT 2.0** | $0.04 (subscription) / $0.30 (PAYG) | Very good | 800+ voices | 100 langs | <500ms | Adapter |
| **Resemble AI** | Custom enterprise pricing | Good | Voice cloning specialty | Limited | <500ms | Adapter |
| **Speechify API** | $20-99/mo subscription | Good | Limited | Good | <1s | Adapter |

**Style/SSML support** (most important for the "calm/empathetic vs newscaster" tone-control we hit):

- **Azure** supports `<mstts:express-as style="empathetic">` — but only for select voices, and D-ID may not pass the SSML through. Worker patch needed.
- **ElevenLabs** has *Voice Settings* (stability, similarity, style exaggeration) that map to emotion. Best for narration with consistent emotional register.
- **OpenAI TTS** has no style parameter — neutral default only.

**Cost for our use case (~80s of dialog per scenario, ~150 words = ~750 chars):**
- Azure: $0.012 — negligible
- ElevenLabs Pro: $0.05 — still negligible
- TTS is **never the cost driver**; only relevant for quality / style.

---

## 4. Text-to-Video (general, less character-driven)

For B-roll, transitions, scene establishments, or full text-to-video stories without a fixed character:

| Service | Per-second cost | Max duration | Resolution | Strengths | Code change |
|---|---|---|---|---|---|
| **Runway Gen-4** | ~$0.05–0.10/sec | 10s clips | 1080p+ | Best motion fidelity; image-to-video and video-to-video | Adapter (~120 LOC) |
| **OpenAI Sora 2** | Bundled in ChatGPT Plus ($20/mo) — limited; Pro $200/mo for higher cap | 20s | 1080p+ | Best world-model coherence; highest realism | Pro tier API limited, mostly UI-only |
| **Google Veo 3** | $0.50/sec (Vertex AI, audio included); $0.30/sec without audio | 8s | 720p–1080p | **Native synchronized audio + dialog** in the video itself | Adapter (~100 LOC) |
| **Pika 2.0** | $10–95/mo subscriptions, ~625–6250 credits | 10s | 1080p | Strong stylization, "Pikaffects" preset library | Adapter |
| **Luma Dream Machine 2** | $30–450/mo | 10s | 1080p+ | Smooth camera motion, good for cinematic | Adapter |
| **Kling 2.0** | ~$0.03–0.10/sec via API | 10s+ | 1080p | Strong human action/dance; cheaper than Runway | Adapter |
| **MiniMax Hailuo 02** | ~$0.04/sec | 10s | 1080p | Budget alternative; quality lower than Runway/Veo | Adapter |
| **HeyGen AI Studio** | Bundled with HeyGen subscription | 60s+ scenes | 1080p | Combines avatar + B-roll + transitions in one API | Adapter (already in HeyGen plan if we adopt) |

**Cost for a 1-min B-roll segment:**
- Runway Gen-4: ~$3–6
- Veo 3: ~$30 with native audio (premium)
- Kling/Hailuo: ~$2–6

**Note:** these don't replace D-ID for talking-head dialog — they're complementary. Use them for *establishing shots*, *cutaways*, *opener animations*. For our compliance + social-story format, talking-head is 90% of the runtime; B-roll is the remaining 10%.

---

## 5. Dubbing & Translation (existing video → other languages)

For multilingual scaling of finished scenarios:

| Service | Cost | Languages | Lip-sync to new language | Voice cloning |
|---|---|---|---|---|
| **ElevenLabs Dubbing** | $1/min for Studio Dub; $0.10/min for Auto Dub | 29 | Yes (lip-sync optional) | Yes — clones original speaker |
| **HeyGen Video Translate** | Bundled in HeyGen subscription | 175+ | Yes | Yes |
| **Rask AI** | $20–60/mo, ~$1–2/min | 130+ | Yes | Yes |
| **Papercup** | Enterprise only, custom pricing | 65+ | Yes (highest quality) | Yes |
| **Synthesia Multi-language** | Bundled | 140+ | Yes | Yes |

**Cost to add Spanish + French to a single 80s social story:** ~$2.70 on ElevenLabs Studio Dub, ~$0.27 on Auto Dub. Very cheap relative to original render.

---

## 6. Audio: Music & Sound Design

For background music beds, soundtracks, intros/outros:

| Service | Cost | Output | Strengths |
|---|---|---|---|
| **Suno v4** | $10/mo Pro / $30/mo Premier | 4-min songs with vocals + lyrics | Best overall song quality; instant generation |
| **Udio v1.5** | $10/mo Standard / $30/mo Pro | 2-min songs | Slightly higher fidelity than Suno; better for instrumental |
| **ElevenLabs Music** | Included in $99/mo Pro | 30s–5min instrumentals | Tight integration with their voice stack |
| **Stable Audio Open** | Free, self-hostable | 47s clips | Open-source, good for SFX |
| **Beatoven.ai** | $5–20/mo | Royalty-free background | Specifically tuned for video BGM use case |

**Cost for a calm-music bed under a 60s social story:** $0 if subscribed, ~$0.50–2 if pay-per-track on a marketplace.

---

## 7. Voice Cloning (personalization layer)

If parents want their *own* voice on a custom social story (high-emotional-pull personalization):

| Service | Cost to clone | Quality | Storage | Privacy |
|---|---|---|---|---|
| **ElevenLabs Instant Clone** | Free w/ Creator+ subscription | Good (1-min sample) | Saved per user | Private to your account |
| **ElevenLabs Professional Voice** | $99/mo Pro | Excellent (30-min sample) | Saved per user | Private |
| **Resemble AI** | $30–100/mo | Excellent | Per-user voice | Private |
| **PlayHT Voice Clone** | $39+/mo | Good | Per-user voice | Private |
| **Cartesia Voice Clone** | $5/mo Hobbyist | Good (3-sec sample) | Per-user | Private |

**Compliance note:** if shipping voice-clone-as-a-feature to parents, need explicit consent UX, age-gating (no minor voices), and a delete-on-request flow. Both ElevenLabs and Resemble have docs on this.

---

## 8. Animated Story Video for Children — Cartoon Human Characters

**Specifically for the special-needs / social-stories use case** — full animated narrative videos with stylized human characters (NOT animal mascots), kid-friendly aesthetic, predictable expressions across scenes, and narration support. Different from "talking-head lipsync" (Section 1) — these tools build full multi-scene stories with character animation, scene transitions, and automated lip-sync, not single-character monologues.

### 8a. Dedicated cartoon-story video platforms

These are *the* category for what you're describing — drag-and-drop or text-to-video editors with libraries of pre-built cartoon human characters, scene backgrounds, props, and motion presets.

| Service | Entry tier | Per-month cost (full features) | Character library | API access | Kid-friendly defaults | Best fit for |
|---|---|---|---|---|---|---|
| **Vyond** *(industry leader; ex-GoAnimate)* | Essential $49/mo | Professional $89/mo / Enterprise $299–999/mo | 1000+ stylized human chars across "Contemporary," "Business Friendly," "Whiteboard" styles; **expression library is best-in-class** (~50 emotions per char) | Yes (Enterprise tier only) | Yes — has dedicated *Education* assets | Production-grade social stories; multi-scene narrative; consistent character across an entire catalog |
| **Animaker** | Free / Basic $12.50/mo | Business $39/mo / Enterprise $79/mo+ | 100+ stylized human chars + 30+ kid-specific chars; lip-sync auto-generated; full body motion presets | **Yes** (Business tier and up) | Yes — explicit "Kids" character pack | Cheapest tier with API access; good for prototyping then scaling |
| **Powtoon** | Pro $20/mo | Pro+ $59/mo / Agency $125/mo | 5000+ assets; cartoon humans available but more biased toward business/explainer use | API only via Agency tier | Limited (more business-explainer than kids) | Educational explainers more than narrative stories |
| **Plotagon Story** | $9.99/mo (consumer) | School license $99/yr per teacher | 500+ stylized human chars; **specifically designed for child-authored stories** (school market) | No public API | Yes — built for K-12 classrooms | One-off classroom use, not programmatic generation |
| **Renderforest** | Lite $12.99/mo | Pro $49/mo / Enterprise $69/mo | Cartoon templates + character library; less character-flexible than Vyond/Animaker | No API; CLI export only | Mixed | Animated explainer-style stories, less narrative-driven |
| **Doodly / Toonly** | One-time $39–67 license | n/a (perpetual) | Whiteboard (Doodly) or 2D cartoon (Toonly) human chars | No (desktop app) | Whiteboard style is great for autism (low sensory load) | Solo creators on a budget; no API integration possible |

**Cost-per-deliverable estimate (1 social story = 80s, 4 distinct characters, 6 scenes):**

| Service | Production cost | Caveat |
|---|---|---|
| **Vyond Professional** | $89/mo (unlimited) → effectively $0/scenario marginal cost | Best character expression range; manual scene assembly |
| **Animaker Business** | $39/mo + ~$0.10–0.20/min API call → $0.50–1/scenario | API enables programmatic generation; better unit economics |
| **Steve.AI** | $45/mo (Pro) → ~$0.50–1/scenario marginal | AI-driven; less manual control over character behavior |
| **Plotagon Story** | $9.99/mo, no API → manual export per scenario | Cheapest if you don't need automation |

### 8b. AI-driven cartoon video generation (text-to-video for cartoon characters)

Newer category — give it a script, it generates the full cartoon-character video without manual scene assembly. More automation, less per-frame control.

| Service | Cost | Output | Strengths | Weaknesses for kids/special-needs |
|---|---|---|---|---|
| **Steve.AI** | $15–45/mo (Pro tier with cartoon avatars) | 1080p, multi-scene cartoon | Very fast; good for prototyping | Character expressions can be over-energetic — needs autism-friendly tuning |
| **Krikey AI** | $5–50/mo + per-credit | 3D animated humans w/ custom motion | Best for action / motion-driven stories | Fewer "calm narrative" presets; more game-dev oriented |
| **Hedra Character-3** | $10–50/mo | Multimodal cartoon characters that lip-sync to your audio | Newest, fastest evolving | Library is smaller than Vyond/Animaker; quality variable |
| **Topview AI** | Pay-per-use ~$0.30/min | Auto-generates full cartoon stories from script | Cheapest fully-automated path | Very limited character customization |
| **InVideo AI** | $15–60/mo | AI-driven; mixed cartoon + photoreal | Strong template library | Cartoon humans aren't its primary strength |
| **Pictory** | $19–99/mo | Mostly photoreal; cartoon as add-on | Best for transcript-to-video | Less suited for character-driven narrative |

### 8c. Talking-head with cartoon avatars (already covered in §1, listed here for completeness)

| Service | Cartoon human support | Cost | Where in the pipeline |
|---|---|---|---|
| **HeyGen** | Yes (anime, illustrated, 3D Pixar-style) | $24+/mo | Drop-in for `/stories` if narrator-only format is acceptable |
| **Synthesia** | Yes (stylized illustrated) | $22+/mo | Same; broader avatar library |
| **AKOOL** | Yes (anime + Pixar-style) | $7.99+/mo | Cheapest; quality more variable |

These are *talking-head only* — single character on screen for the duration. If your social story is single-narrator (like the current `anxiety-001` format), they work as-is. For multi-character dialog stories (like `accepting-no` with Daniel + Mom + Dad + Narrator), you'd render each character's turn separately and stitch — adds editing time but works.

### 8d. Open-source / self-hostable

If budget is the dominant constraint and you have GPU access:

| Service | Cost | Output | Setup |
|---|---|---|---|
| **LivePortrait** | Free (open-source, MIT) | Talking-head from any portrait, including cartoon | Self-host on a 12GB+ GPU; ~3-day learning curve to wire into a pipeline |
| **SadTalker** | Free (open-source) | Same as LivePortrait, slightly older | Same setup |
| **AnimateDiff** | Free (open-source) | Animated character motion from a still image | Heavier GPU demand |
| **ComfyUI workflows** | Free | Composable pipeline of all of the above | Steep learning curve but maximum flexibility |

**Cost vs effort trade-off:** open-source paths trade ~$50–200/mo subscription cost for ~40 hours of initial setup time + ongoing maintenance. Worth it only if you're rendering >100 scenarios/month *or* you need on-prem/HIPAA-compliant hosting.

### 8e. Special-needs design considerations

These cut across all of the above — flag during evaluation regardless of which service you pick:

| Requirement | Why it matters | Vendor support |
|---|---|---|
| **Calm pacing, no rapid cuts** | Autism-friendly; rapid scene changes can be sensorily overwhelming | Vyond + Plotagon support manual pacing; AI tools (Steve.AI, Topview) often default to fast cuts — need to override |
| **Predictable character consistency** | Autistic kids respond strongly to recognizing "the same character" across stories | Vyond/Animaker excel (save character to library); AI tools (Steve.AI) often regenerate slight variations each render |
| **Clear, exaggerated facial expressions** | Helps with emotion-recognition support | Vyond's expression library is industry-leading; Plotagon is also strong |
| **Simple, low-clutter backgrounds** | Reduces sensory load | Plotagon defaults are simple; Vyond depends on template choice |
| **Closed-caption native support** | Accessibility / dual-modality reinforcement | Vyond, Animaker, Synthesia all native; HeyGen has it too |
| **Same-voice consistency across scenes** | Predictability for the listener | All character-platforms bind voice-to-character; AI tools need explicit voice locking |
| **No flashing / strobing** | WCAG 2.1, also seizure-safe | All tools support it but no automatic checking — manual audit needed per scenario |

---

## Cost models — three product paths

### Path A: stay on D-ID Lite (current)
- Talking-head: **$5–18 per scenario** (varies with turn count)
- Image gen: $0.16 / scenario
- TTS: bundled in D-ID, ~$0
- **Per-scenario total: ~$5.16–18.16**
- **Watermark:** corner badge present
- **Per-month if rendering 50 scenarios:** ~$300–900 + $5.90 subscription

### Path B: HeyGen Creator subscription
- $24/mo unlocks 15 min of talking-head, no watermark, **cartoon avatars supported**
- Per-scenario marginal cost above 15 min: ~$1–2/min
- **Per-scenario total: $0 (within plan) → $1–2 (over)**
- **Per-month if rendering 50 scenarios @ 80s avg = 67min:** $24 base + ~$80 over = **$104**
- **Win condition:** cartoon-character requirement, or >7 min/month rendered, or watermark-blocking demo coming

### Path C: Synthesia + ElevenLabs combo
- Synthesia Creator $89/mo for 30 min + 230 avatars
- ElevenLabs Pro $99/mo for premium narration with emotion
- **Total fixed: $188/mo**
- **Per-scenario total: $0 (within plans)**
- **Win condition:** producing >30 scenarios/month with broadcast-quality voice, or a B2B sale that requires zero watermark + multilingual + brand-safe

### Path D: cartoon stories for special-needs children
*(NEW — for the social-story / autism-coping product line)*

- **Animaker Business $39/mo** (API + 100+ kid-friendly cartoon human chars + lip-sync)
- **ElevenLabs Creator $22/mo** (calm/empathetic SSML voices for narration)
- **Optional: D-ID Lite $5.90/mo** kept active for `/jt` corporate scenarios on the existing pipeline (not used for stories)
- **Total fixed: $61/mo (without D-ID) or $67/mo (with D-ID kept)**
- **Per-scenario marginal cost:** ~$0.50–1 on Animaker API once over baseline minutes; ~$0.05 on ElevenLabs for narration
- **Per-scenario total: ~$0.55–1.05** (vs current ~$15 D-ID render cost for accepting-no on Lite tier)
- **Break-even vs Path A (D-ID Lite):** at ~5 scenarios/month, Path D is cheaper. By 10/month it's >$100 cheaper.
- **Win condition:** the social-stories product line proves out and you ship >5 stories/month, OR a special-needs school/clinic asks for a customized-story service

**Caveat:** Animaker's API requires Business tier ($39/mo) — Free/Basic tiers are UI-only. Verify the API exposes character + scene + voice control programmatically before committing — last confirmed API surface: scene templates, character placement, dialog timeline, voice selection. Camera control is limited.

---

## Recommendations for the StudyBuddy / `/jt` / `/stories` portfolio

| Surface | Today | Suggested next |
|---|---|---|
| `/jt` corporate compliance | D-ID Lite, photoreal humans, $5–8/scenario | Stay on D-ID Lite until first paid pilot, then upgrade to D-ID Pro ($50/mo) for watermark removal — saves ~$0 marginal, gains professionalism |
| `/stories` social stories — talking-head format | D-ID Lite, photoreal humans, $15/scenario | **Switch to HeyGen Creator ($24/mo)** for cartoon-character support; ROI breakeven at ~3 scenarios/month |
| **`/stories` social stories — cartoon narrative format (special-needs)** | Not yet shipped | **Animaker Business ($39/mo)** + ElevenLabs Creator ($22/mo) = Path D ($61/mo). Per-scenario marginal ~$1 vs current $15 on D-ID. Best fit for the special-needs product line specifically — multi-scene cartoon narrative > single-character talking-head. |
| Multilingual variants | None | ElevenLabs Auto Dub at $0.27/scenario when needed; defer until first non-English request |
| Music bed | None | Suno Pro $10/mo when shipping outside prototype |

---

## Verification & sources

The numbers above are pulled from broker training data (Jan 2026). Always verify before committing — these change quarterly:

| Service | Pricing page |
|---|---|
| D-ID | https://www.d-id.com/pricing/ |
| HeyGen | https://www.heygen.com/pricing |
| Synthesia | https://www.synthesia.io/pricing |
| Tavus | https://www.tavus.io/pricing |
| OpenAI | https://openai.com/api/pricing |
| Replicate | https://replicate.com/pricing |
| Google Vertex AI | https://cloud.google.com/vertex-ai/generative-ai/pricing |
| ElevenLabs | https://elevenlabs.io/pricing |
| Runway | https://runwayml.com/pricing |
| Suno | https://suno.com/pricing |
| Adobe Firefly | https://www.adobe.com/products/firefly/plans.html |
| **Vyond** | https://www.vyond.com/pricing/ |
| **Animaker** | https://www.animaker.com/pricing |
| **Powtoon** | https://www.powtoon.com/pricing/ |
| **Plotagon** | https://www.plotagon.com/pricing |
| **Steve.AI** | https://www.steve.ai/pricing |
| **Krikey AI** | https://www.krikey.ai/pricing |
| **Hedra** | https://www.hedra.com/pricing |
| **Topview AI** | https://www.topview.ai/pricing |
| **AKOOL** | https://akool.com/pricing |

For live cost verification, run `WebSearch` against any of these pages or ask broker to fetch + summarize.

---

## Footnotes — billing patterns to watch out for

These bit us this week and are good to internalize:

1. **D-ID `IAM-deny` errors come with no spend** (verified 3 cycles 2026-05-05). Same for `InsufficientCreditsError` (402) and `FaceError`. Only `done` status talks bill credits. Failed talks are free — retry without fear.
2. **D-ID `_POLL_TIMEOUT` defaults to 120s.** A 10-turn parallel batch occasionally tripped it, costing ~$12.50 in already-billed-but-unrecoverable talks. Set to 300s for batches >5 turns.
3. **OpenAI `400 Billing hard limit`** fires before any image is created — zero spend on the failed call. Just raise the cap and retry.
4. **OpenAI `gpt-image-1` is deprecated** — use `gpt-image-2` since Apr 21 2026.
5. **Replicate per-image pricing assumes "succeeded" status.** Cancelled or errored predictions may still be billed for partial GPU time on some models — check the prediction's `metrics.predict_time` if you suspect a charge for a cancelled run.
6. **HeyGen / Synthesia minutes don't roll over** between billing cycles. Plan usage to fit within the cycle.
7. **ElevenLabs character counts** include all generated audio, including failed attempts and previews — clean up unused voices to control spend.

---

*Document last updated: 2026-05-05. Refresh quarterly.*
