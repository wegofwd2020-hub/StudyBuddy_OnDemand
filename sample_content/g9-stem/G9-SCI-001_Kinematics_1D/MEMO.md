# MEMO — G9-SCI-001 Kinematics 1D

> Per-unit learning memo. Captures patterns observed during hand-authoring
> for **#320 code-gen automation**'s spec input. Updated after each phase.

## Status

- **Phase 1 (Option 2 catalogue):** ✅ 10 SVGs + 10 sidecars shipped
- **Phase 2 (Option 3 Remotion clip):** pending — motion-along-strip
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

## Time budget

Phase 1: ~30 minutes (helper lift from G11 + 10 figure functions). Wave-1 issue estimated 1.5 days for the whole unit; the generator-reuse conjecture from #327's MEMO holds — second physics-kinematics unit lands in ~20% of the first one's wall time.

---
*Author: broker. Updated 2026-05-07 (Phase 1 complete).*
