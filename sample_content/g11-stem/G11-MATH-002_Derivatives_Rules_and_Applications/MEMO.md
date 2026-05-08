# MEMO — G11-MATH-002 Derivatives — Rules and Applications

> Per-unit learning memo for #320 spec input.

## Status

- **Phase 1 (Option 2 catalogue):** ✅ 9 SVGs + 9 sidecars shipped
- **Phase 2 (Option 3 Remotion):** ✅ `Derivatives_TangentEmergence.mp4` (3.7 MB / 24 s)
- **Phase 3 (eval + library promotion):** ✅ 9 sidecars promoted; 3 known-positive eval records (`eval-072` / `073` / `074`)

## Phase 1 reflections

| Section | Visuals |
|---|---|
| `section-1-derivative-concept` | `secant-and-tangent-lines`, `tangent-as-limit-of-secants`, `derivative-as-slope-along-curve` |
| `section-2-rules` | `power-rule-card`, `chain-rule-decomposition`, `product-and-quotient-rules` |
| `section-3-applications` | `optimization-extrema`, `related-rates-balloon`, `motion-position-velocity-acceleration` |

This unit *extends* the math primitive class established in #G11-MATH-001 (the original reference exemplar). The new high-leverage primitive is `secantLine(fn, x1, x2, ...)` — a line through two points on a function extended across the visible plot. Reused inside the Remotion clip as well — confirms once-write-twice-use.

### What was repetitive (= templatable)

1. **Curve-with-overlay-line pattern.** Every figure in Section 1 follows `<Plot> + <Curve> + <OverlayLine type="secant" | "tangent" />`. **Recommendation:** `<CurveWithTangent fn x />` and `<CurveWithSecant fn x1 x2 />` shared components.

2. **Stacked plots showing successive derivatives** (`derivative-as-slope-along-curve`, `motion-position-velocity-acceleration`) — same vertical-stack layout as #328's uniform-vs-accelerated comparison and #327's wave-superposition. Now four units use it. **Recommendation:** `<StackedPlots plots={[{cfg, fn, color}]} />` shared component.

3. **Formula-card layout** (`power-rule-card`, `chain-rule-decomposition`) — highlighted yellow/cream rectangle with formula in bold + worked examples below. Same shape as the chemistry ohms-law / quantum-numbers cards. **Recommendation:** `<FormulaCard formula examples />`.

### What needed human judgment

1. **Pedagogical sequencing.** Why secant-then-tangent, then limit-of-secants, then "derivative is its own function"? The order matters. A reverse order (function-first, instances-second) would be technically correct but pedagogically wrong at G11 level.

2. **Worked-example values.** y = (3x+2)⁵ for the chain rule is curated — small enough to compute mentally, has a nice "5×3 = 15" final coefficient, doesn't run into derivative chain depth issues. Curator-only.

3. **Secant-shrink schedule** in the Remotion clip — Δx = 2.5 → 0.05 over 10 seconds. Shorter (5s) feels rushed; longer (15s) feels boring. Hand-tuned to the "you can see the pivot" sweet spot. Same family of decisions as the cumulative-phase pacing in earlier physics clips.

## Phase 2 reflections — TangentEmergenceScene

24-second clip showing f(x) = 0.4x² with anchor point P at x=2:
- Frames 0-150: title + curve appear
- Frames 150-240: hold initial wide secant (Δx = 2.5)
- Frames 240-540: Δx interpolates linearly to 0.05 — secant pivots dramatically
- Frames 540-720: tangent locks in, slope readout displays f'(2) = 1.6, caption fades in

Live slope readout (`[f(2+Δx) − f(2)] / Δx`) updates per frame. The numerical secant slope visibly converges on 1.6 as Δx shrinks. Also shows the formula caption directly below.

The new shared pattern: `secantLine(fn, x1, x2, ...)` lifts cleanly from the SVG generator into the Remotion scene with zero modification. Third proof point that the Plot helpers (PlotConfig, makePlot, plotPolyline) carry across SVG/Remotion contexts unchanged.

## Phase 3

Three known-positive eval records:
| eval id | section title | expected_entry_id |
|---|---|---|
| `eval-072` | What the Slope of a Curve Means | `math-derivatives-tangent-as-limit-of-secants` |
| `eval-073` | A Quick Recipe for Differentiating Powers | `math-derivatives-power-rule` |
| `eval-074` | How Fast Does the Balloon Get Bigger? | `math-derivatives-related-rates-balloon` |

Eval-072 deliberately uses "kissing line" (a real informal description of tangents) instead of "tangent" verbatim. Tests whether resolver picks up metaphorical descriptors.

All 9 G11-MATH-002 sidecars seeded; 122/122 library rows, 0 NULL embeddings.

## Time budget

| Phase | Issue estimate | Actual |
|---|---|---|
| Phase 1 | ~1 day | ~50 min |
| Phase 2 | ~0.5 day | ~25 min |
| Phase 3 | (rolled in) | ~12 min |

Total: ~1 h 27 m vs. 1.5-day estimate. Wave-2 cumulative (3 units): ~3 h 54 m / 5 days estimated.

---
*Author: broker. Updated 2026-05-08 (all phases complete; #334 ready to close).*
