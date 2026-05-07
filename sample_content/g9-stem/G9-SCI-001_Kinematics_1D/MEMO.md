# MEMO — G9-SCI-001 Kinematics 1D

> Per-unit learning memo. Captures patterns observed during hand-authoring
> for **#320 code-gen automation**'s spec input. Updated after each phase.

## Status

- **Phase 1 (Option 2 catalogue):** ✅ 10 SVGs + 10 sidecars shipped
- **Phase 2 (Option 3 Remotion clip):** ✅ `G9_Kinematics_MotionAlongStrip.mp4` (1.7 MB / 24 s)
- **Phase 3 (eval set + library promotion):** pending

## Phase 1 reflections — Option 2 catalogue

The 10 SVGs land in three sections:

| Section | Visuals |
|---|---|
| `section-1-fundamentals` | `1d-position-and-displacement`, `distance-vs-displacement`, `average-vs-instantaneous-speed` |
| `section-2-uniform-motion` | `motion-strip-uniform`, `xt-uniform`, `vt-uniform` |
| `section-3-accelerated-motion` | `motion-strip-accelerated`, `xt-accelerated`, `vt-accelerated`, `uniform-vs-accelerated-comparison` |

### What was repetitive (= automatable for #320)

1. **The whole helper toolkit lifted verbatim from `generate_kinematics_visuals.ts`.** `PlotConfig`, `makePlot`, `plotPolyline`, `svgWrap`, `write`, plus the colour tokens (`INK`, `MUTED`, `ACCENT`, `ACCENT_2`, `GRID`, `BG`, etc.) — copied byte-for-byte. **Recommendation for #320:** factor these into `pipeline/visual_templates/svg_helpers.ts` and have every per-unit generator import from there. Saves ~120 lines of duplicated code per generator.

2. **x-t / v-t / a-t plot templates.** `xt-uniform`, `vt-uniform`, `xt-accelerated`, `vt-accelerated` are all `makePlot + plotPolyline + slope-triangle annotation`. Same shape, only the math function and labels change. **Recommendation:** template `time-series-plot` with parameters `{xRange, yRange, fn, slopeAnnotation: {x1, x2}, axisLabels}`. Covers ~40% of physics-kinematics catalogue across G9, G11, future units.

3. **Slope-triangle annotation pattern.** Used in `xt-uniform` (slope = constant speed), `vt-accelerated` (slope = constant acceleration), and the G11 versions. Same dashed-rectangle + Δt/Δy labels. **Recommendation:** template `slope-triangle` taking `{plot, x1, x2, color, dxLabel, dyLabel}`.

### What was new for G9 (= curator-led but templatable downstream)

1. **Motion-strip primitives.** Two new figures (`motion-strip-uniform` and `motion-strip-accelerated`) — a horizontal axis with N circles whose spacing follows either `equal` or `0.5·t²`. Compact code, ~30 lines each. **Recommendation for #320:** template `motion-strip` with parameters `{N, spacing: 'equal' | (i: number) => number, color, label}`. Useful for future units with stroboscopic visuals: G9-SCI-002 Newton's, G6-SCI Forces, G7-SCI Energy.

2. **Side-by-side comparison primitive** (`uniform-vs-accelerated-comparison`). Two `makePlot`s in one viewBox, transform-translated. Same pattern that `transverse-vs-longitudinal` used in G11-PHYS-010. **Recommendation:** lift the wider transform-group pattern into a `side-by-side-plots` template.

### What was reused near-identically from G11-PHYS-002

- `1d-position-and-displacement` — same shape, simpler labels
- `distance-vs-displacement` — same shape, slightly G9-friendlier prose

The `average-vs-instantaneous-speed` figure is *re-styled* from G11's `average-vs-instantaneous-velocity` — uses speed (scalar) framing instead of velocity (vector), with speedometer-readout boxes instead of velocity arrows. Pedagogically distinct enough to deserve its own visual.

### What fell outside code-gen entirely

Nothing in this Phase-1 set. Pure 2D primitives, all code-renderable.

## Phase 2 reflections — Option 3 Remotion clip

One composition (`g9-motion-along-strip`, 24 s, 1.7 MB) showing two strips stacked vertically:

- **Top strip — uniform motion:** purple ball traversing 30 m at constant 5 m/s
- **Bottom strip — accelerated motion:** amber ball covering the same 30 m with a = 5/6 m/s² (starts slow, ends fast)

Both balls reach the finish line at the same instant (t = 6 s), so the only signal the student picks up is the *spacing of the strobe dots*. Equal gaps for uniform; growing gaps for accelerated (Galilean odd-number ratio 1:3:5:7:9:11). After motion completes, the static dot pattern persists with green/red bracket markers showing each gap, and three captions fade in:

1. "Strobe dots = the ball's position every second"
2. "▲ Equal gaps every second → constant speed (uniform)"
3. "▼ Gaps grow each second → speeding up (accelerated)"

### What was repetitive (= templatable)

1. **Whole infra layer is byte-identical to the G11-PHYS-002 / G11-PHYS-010 Remotion projects.** `package.json`, `tsconfig.json`, `remotion.config.ts`, `theme.ts`, `index.ts` — copy-paste with name swaps. **Recommendation:** lift this into a generator template at `pipeline/visual_templates/remotion_project.ts` (already filed in #327's MEMO; this unit is the second proof point). Per-unit human work shrinks to writing the scene.

2. **Title + subtitle + sub-heading fade-in pattern** — same `spring + interpolate(0,30) + interpolate(20,60)` triplet from every prior scene. **Recommendation:** `<SceneTitle title sub subSub />` shared component.

3. **Position-along-strip visual primitive.** `Strip` component takes `{y, color, ballPositionPx, visibleStrobeCount, strobePositions, label, showSpacingMarkers}` — fully reusable. Future units that need stroboscopic visuals (G9-SCI-002 Newton's laws, G6 forces, G7 energy) can lift this whole component. **Recommendation for #320:** ship as `<MotionStrip />` in shared components — high-leverage primitive for any motion-pedagogy clip.

### What needed human judgment (= curator-only)

1. **Choosing the two motions to make them end-aligned.** The decision to set `a = 5/6 m/s²` so that the accelerated ball reaches x = 30 m at exactly t = 6 s (matching the uniform ball) is a pedagogical call — it removes "who wins" as a distraction and isolates spacing as the only visible difference. The LLM can derive this constraint from the prompt "make both motions end at the same point at the same time," but the *decision to impose this constraint* is curator-led.

2. **Caption pacing — three sequential reveals.** Showing the strobe-dot caption before the spacing-pattern callouts gives the student time to look at the pattern themselves before being told what to see. This is the same "show before tell" rhythm that #327's WaveSuperposition used (the regime caption updates with the phase difference, so the student sees the changing sum *before* reading the label). Curator-only.

### What fell outside code-gen entirely

Nothing. Pure 2D primitives + math.

### Time budget reconciliation (Phase 2)

Phase 1 estimated 1 day, Phase 2 estimated half a day in the issue's 1.5-day total. **Actual Phase 2: ~20 minutes authoring + 1 minute render.** The generator-reuse conjecture continues to hold: every infra file mirrored a known-good template, so authoring effort collapsed onto the single new scene file (~210 LoC including the `Strip` component).

## Time budget

| Phase | Issue estimate | Actual |
|---|---|---|
| Phase 1 | ~1 day | ~30 min |
| Phase 2 | ~0.5 day | ~20 min |
| Phase 3 | (rolled into 1.5 d) | pending |

Wave-1 padding is correctly budgeting for the *first* unit per primitive class. Same-class downstream units (G11-PHYS-010 → G9-SCI-001 in this case) routinely come in at <20% of the first unit's wall time.

---
*Author: broker. Updated 2026-05-07 (Phase 2 complete).*
