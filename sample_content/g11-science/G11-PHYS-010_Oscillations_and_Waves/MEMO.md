# MEMO — G11-PHYS-010 Oscillations and Waves

> Per-unit learning memo. Captures patterns observed during hand-authoring
> for **#320 code-gen automation**'s spec input. Updated after each phase.

## Status

- **Phase 1 (Option 2 catalogue):** ✅ 12 SVGs + 12 sidecars shipped
- **Phase 2 (Option 3 Remotion clips):** ✅ 3 clips rendered — `Oscillations_SHM.mp4` (3.6 MB / 24 s), `Oscillations_Superposition.mp4` (8.6 MB / 26 s), `Oscillations_Doppler.mp4` (14.3 MB / 22 s)
- **Phase 3 (eval set + library promotion):** ✅ 12 sidecars promoted via `seed_library_local.py` (all with non-NULL embeddings), 3 new known-positive eval records appended (`eval-051`/`052`/`053`)

## What was repetitive (= automatable)

These patterns appeared across many of the 12 SVGs and are perfect templates for #320 to fill in:

1. **Single-axis sine plot** with amplitude / period markers — appeared in `shm-displacement-time`, `wave-anatomy`. Template: `makePlot(...)` + `polyline(samples([...sin...]), ...)` + a few label overlays. **Variability:** ω, A, x-range. **Constants:** colour palette, padding, axis labels.

2. **Stacked-plots-for-comparison** — appeared in `shm-y-v-a-comparison` (3 stacks), `superposition-constructive/destructive` (3 stacks each). Template: a `stacks` array of `{data, color, label, yRange}`, render each into a transform-translated `<g>`. **Variability:** number of stacks (always 2-3), colour rotation. **Constants:** layout math, gap, font sizes.

3. **Comparison-on-same-axes** — appeared in `damped-oscillation-comparison` (3 curves, one plot), `resonance-amplitude-curve` (3 curves, one plot). Template: same `makePlot` + N `polyline` calls with different colours + a small legend block in the corner. **Variability:** N curves, the math function, palette choice. **Constants:** legend layout, axis labels.

4. **Side-by-side concept comparison** — appeared in `transverse-vs-longitudinal`. Template: split the canvas in half with a vertical divider, render each concept into its half, label and arrow each. **Variability:** which two concepts. **Constants:** divider placement, label positions, arrow style.

These four templates would cover ~70–80% of the unit's catalogue. **Strong candidates for #320 templates** named `single-plot`, `stacked-plots`, `multi-curve-plot`, `side-by-side-concept`.

## What needed human judgment (= curator-only territory)

These visuals required hand-authored geometric layout that wouldn't have come out of an LLM template fill cleanly:

1. **Pendulum free-body diagram** — required computing the position of the bob from a given angle, the perpendicular direction for the restoring component, marker positions for the angle arc, and the relative lengths of the three force vectors so the geometry is readable. The LLM would need to write coordinate geometry against the pendulum's hinge frame; doable but the prompt would need the formula for the restoring component as a constraint. **Recommendation for #320:** template `free-body-diagram` with parameters `{bob_position, vectors:[{name, direction, length, color}], pivot}`.

2. **Standing-wave modes** — the envelope curve for each harmonic depends on `n`; nodes appear at `kL/n` for `k=0..n`. Generated with `for k in 1..n` placement. The pattern is clean enough to template, but the LLM would need to know the closed-form for the standing-wave envelope. **Recommendation:** template `standing-wave-modes` with parameters `{harmonics:[1, 2, 3], color_palette}` — solver embedded in template.

3. **Doppler wavefront geometry** — successive wavefronts are circles of increasing radius emitted from successively-translated source positions. The LLM has to compute the right radii sequence such that the wavefronts visually crowd ahead of the source and spread behind. Hand-authored values (`r=130, 95, 60, 25`; positions `srcX=cx-120, -80, -40, 0`) chosen for visual clarity, not derived from physics. **Recommendation:** template `doppler-wavefronts` with hand-chosen example parameters — the LLM tunes only the labels and observer placement.

## What fell outside code-gen entirely (= deferred to `kind: "photo"` exception)

Nothing in this unit. Every visual was code-renderable. Pure mechanics + waves; no real-world photographs or watercolour-style illustrations earned their cost over the precise SVG primitives.

## Token cost estimate (if LLM-authored from scratch)

Each visual is ~50–250 lines of TS spec data + the shared `makePlot` boilerplate. Hand-authored, this took roughly 90 minutes of focused work for all 12 visuals (because the templates from kinematics carried over).

If LLM-authored from scratch (no prior templates):
- Per visual: ~2k input tokens (concept + template prompt) + ~1.5k output tokens (TS spec)
- 12 visuals: ~24k input + ~18k output ≈ ~$0.07 (Sonnet 4.6 at $3/M in, $15/M out)

If LLM-authored *with* the Kinematics templates as priors:
- Per visual: ~1k input + ~0.8k output
- 12 visuals: ~12k input + ~10k output ≈ ~$0.04

This is well below the per-unit cost ceiling. **Code-gen is economically obvious for this unit class.**

## What this means for #320

1. The **four templates** identified above (single-plot, stacked-plots, multi-curve-plot, side-by-side-concept) cover the bulk of physics-time-series content. Worth shipping in `pipeline/visual_templates/` first.
2. **Free-body-diagram template** is the next most-leveraged primitive — used here for the pendulum, will be reused in G6-ENG-001 (#331), G9-SCI-002 Newton's Laws, G10-ENG-001 Statics, every kinematics unit.
3. **Doppler-wavefront / wave-source template** is more niche; ship after the bulk-template work.
4. The Kinematics templates carry over directly. **Conjecture: most G11/G12 physics units will fit on top of the Kinematics+Oscillations template set.** Verifiable when we ship #335 (G8-SCI-002 Waves) and #336 (G12-PHYS-005 Optics).

## Phase 2 reflections — Remotion clips

The three clips ship from a project that mirrors `G11-PHYS-002_Kinematics/Option3_Video/` verbatim for `theme.ts`, `plot.tsx`, `Root.tsx`, `index.ts`, `package.json`, `tsconfig.json`, and `remotion.config.ts`. The only meaningfully new code lives in `src/scenes/{ShmScene,WaveSuperpositionScene,DopplerScene}.tsx`. Confirms the conjecture from Phase 1 that the kinematics template set carries.

### What was repetitive (= templatable for #320)

1. **The whole infra layer is boilerplate.** `package.json` (dep set + render scripts), `tsconfig.json`, `remotion.config.ts`, `theme.ts`, `plot.tsx`, `index.ts` are byte-for-byte mechanical from one unit to the next. Only `Root.tsx` is per-unit (composition list + durations). **Recommendation for #320:** a single generator `pipeline/visual_templates/remotion_project.ts` that takes `{slug, scenes: [{id, durationSec, component}]}` and stamps the entire infra. Per-unit human work shrinks to writing the scenes.

2. **Title + subtitle fade-in pattern is identical in every scene.** `titleScale = spring(...)`, `titleOp = interpolate([0,30], [0,1])`, `subOp = interpolate([20,60], [0,1])`. Three call sites in three scenes, byte-identical. **Recommendation:** extract a `<SceneTitle title={..} subtitle={..} />` component into a shared `src/components/`. Reduces per-scene LoC ~25.

3. **Stacked-plot layout** (used in WaveSuperpositionScene — three SVGs stacked) reuses the Phase-1 stacked-plots primitive directly. Same `makePlot()` shape, same Plot-frame call. **#320 carries the kinematics+oscillations primitives without modification.**

4. **Reveal-fraction phase plotting** (used in ShmScene — `buildPath(plot, fn, range, reveal)`) is the same pattern as kinematics' x(t)/v(t)/a(t) reveal. The math function changes (`A cos(ωt)` instead of `2t + t²`); the rendering loop is identical.

### What needed human judgment (= curator-only)

1. **ShmScene spring drawing.** The zigzag spring (`springPath()` helper inside the scene) is a small piece of coordinate geometry — N coils between (x0, y) and (x1, y) with alternating ±amp triangles — that is trivially correct once you sketch it but mildly fiddly to write. **Recommendation:** ship a `<Spring fromX endX y coils amp />` primitive in shared components; very reusable (other oscillator units, Hooke's law diagrams, mechanical-energy clips will all want it).

2. **DopplerScene wavefront accumulation.** The active-frame loop `for (let n = 0; n <= lastEmissionN; n++) { ... wavefronts.push(...) }` requires the author to think about *what's emitted vs what's still on screen*. Specifically: source position at emission time `te`, wavefront radius growing as `c·(t−te)`, and the off-canvas cull. Templatable as `<MovingSourceWavefronts vs cs Ttick xStart yBaseline />`, but the LLM needs to be told the formulae explicitly — it cannot infer them from the section text. **Recommendation:** ship as a parameterised primitive with the physics encoded; LLM tunes the visual constants only.

3. **WaveSuperpositionScene phase-difference sweep.** The decision to sweep `φ(t) = 2π·t / T_sweep` continuously instead of switching between fixed-phase frames is a pedagogical call: it gives one continuous clip showing the full constructive→destructive→constructive cycle, plus an in-frame caption that names the regime currently visible. The "regime threshold" logic (sum is constructive when phase < π/4 from 0 mod 2π, destructive when within π/4 of π) is hand-tuned for visual feel. **Recommendation:** keep as a hand-authored authoring choice; don't generalise.

### What fell outside code-gen entirely

Nothing in this Phase-2 clip set. The video pipeline is fully code-renderable. No live-action footage, no photographs.

### Time budget reconciliation (Phase 2 alone)

Estimated 6 hours in the Phase 1 memo. **Actual: ~45 minutes of authoring + 3 minutes of total render time + bun install.** The big saver was that the kinematics infra mirrored cleanly — the only original code is the three scenes (~120, ~110, ~140 LoC respectively, all with hand-authored physics). The "6 hours" estimate assumed authoring infra from scratch.

This compresses #327's full 2-day estimate to about half a day if Phase 3 follows the same pattern (the seeder is shrink-wrapped; only the eval JSONL records are author-time).

### Known papercut — zod version mismatch warning

Render emits a non-blocking warning:
> `zod: installed 3.25.76, required 4.3.6`

Identical warning fires for the kinematics project too — it's a Remotion 4.0.458 vs the older deps-pin in `package.json` (`"zod": "^3.23.8"`). Output is unaffected; renders complete. **#320 fix:** when the generator emits `package.json`, pin `zod` to whatever Remotion requires at the chosen `@remotion/cli` version (currently `4.3.6` for 4.0.458). One-line fix; left in place here for parity with the kinematics exemplar.

## Phase 3 reflections — eval entries + library promotion

Three new known-positive eval records appended to `backend/tests/eval/visual_resolver_eval.jsonl`:

| eval id | section title | expected_entry_id |
|---|---|---|
| `eval-051` | Mass on a Spring Oscillating in Time | `physics-shm-displacement-time` |
| `eval-052` | Two Waves Arriving in Phase | `physics-wave-superposition-constructive` |
| `eval-053` | Why the Siren Changes Pitch | `physics-doppler-effect-moving-source` |

Each section_content was hand-authored as plausible textbook prose without keyword-stuffing, on the principle that the resolver is meant to *infer* the visual need from natural language, not match keywords. Spot-test on scope: SHM-displacement (kinematics), wave-superposition (combination), Doppler (moving-source) — three distinct primitive classes from this unit.

All 12 G11-PHYS-010 sidecars seeded into `visual_library_entries` via `scripts/seed_library_local.py`. Verified: 12 rows present with `source_unit='G11-PHYS-010'`, all with non-NULL embeddings; total rows = 42, NULL-embedding rows = 0.

### What was repetitive (= automatable)

1. **Eval-record shape is identical across categories.** Every record has the same eight fields with the same types. The variability is the prose + the expected_entry_id. **Recommendation for #320:** when authoring a unit's eval companion, ship a small generator that takes `[(visual_id, section_title, prose), ...]` and stamps the JSONL line.
2. **Promotion is one-shot per unit.** `seed_library_local.py` is idempotent (skips already-seeded rows). #320's per-unit pipeline can simply call it after every catalogue change without bookkeeping.

### What needed human judgment (= curator-only)

1. **Eval prose authoring is the hard part.** The prose has to feel like real lesson content — long enough to be ambiguous (so the resolver's LLM has to do real inference), but unambiguous enough that the expected_entry_id is genuinely the right answer. Keyword-stuffed prose makes the eval green for the wrong reason. This stays curator-only.
2. **Choosing which sidecars to add eval coverage for.** Three of twelve in this unit; the choice was driven by (a) primitive-class diversity (one each from kinematics / interference / source-motion), and (b) which library entries are most likely to face fuzzy or synonym-driven queries in the wild ("siren pitch shift" → Doppler is a classic resolver test).

### Operational gotcha (blocked Phase 3 for several minutes)

The repo-root `scripts/` and `sample_content/` directories are **not** bind-mounted into the `celery-pipeline` container — only `./backend:/app` is. A prior session had `docker cp`'d a copy of repo-root scripts and sample_content to `/tmp/seed/` inside the container; that copy was stale (predated G11-PHYS-010 entirely). Running the seeder against `/tmp/seed/` silently surfaced no G11-PHYS-010 sidecars.

**Fix applied:** `docker cp` the up-to-date `sample_content/g11-science/G11-PHYS-010_*`, `scripts/seed_library_local.py`, and `scripts/promote_library_metadata.py` into `/tmp/seed/` before running. Then `docker compose exec -T celery-pipeline python3 /tmp/seed/scripts/seed_library_local.py`.

**Permanent fix (recommendation, not done here — out of scope for #327):** add a bind-mount for `scripts/` and `sample_content/` in `docker-compose.yml`'s `celery-pipeline` service so the seeder always reads live code. Half a line of YAML; saves the next operator the same diagnosis.

## Time budget reconciliation (issue's 2-day estimate)

- Phase 1: ~2 hours hand-authoring + iteration ✅
- Phase 2: ~45 min authoring + ~3 min render time ✅ (was estimated at 6 hours; saved ~5 hours by mirroring kinematics infra)
- Phase 3: ~25 min including the docker-cp diagnosis side-trip ✅ (was estimated at 2 hours)

Total realised: ~3 hours 15 min vs. 2-day issue estimate. Wave-1 cost padding correct for the *first* unit of a primitive class; subsequent same-class units (G8-SCI-002 Waves, G12-PHYS-005 Optics) should land in 2-3 hours each on top of the now-proven Kinematics+Oscillations primitive set.

---
*Author: broker. Updated 2026-05-07 (all phases complete; #327 ready to close).*
