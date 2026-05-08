/**
 * pipeline/visual_templates/derivatives.ts
 *
 * Class-specific primitives for calculus / derivatives catalogues.
 *
 * Lifted from `scripts/generate_derivatives_visuals.ts` per #343 (Wave 5
 * phase C-6). Per the G11-MATH-002 MEMO, `secantLine` lifts from the SVG
 * generator into the Remotion `<TangentEmergenceScene />` verbatim — the
 * same helper produces both the static and animated variants.
 */

import { ACCENT_2 } from "./shared.ts";

// ─────────────────────────────────────────────────────────────────────────
// secantLine — line through two points on a curve, extended across the
// visible plot range.
//
// The chord between (x1, fn(x1)) and (x2, fn(x2)) is extrapolated to span
// the full plot horizontally. Used in static SVG figures (chord-as-secant
// pedagogy) and animated as Δx → 0 in TangentEmergenceScene to show the
// secant collapsing onto the tangent.
// ─────────────────────────────────────────────────────────────────────────

export function secantLine(
  fn: (x: number) => number,
  x1: number,
  x2: number,
  xRange: [number, number],
  xToPx: (x: number) => number,
  yToPx: (y: number) => number,
  color: string = ACCENT_2,
  width: number = 2.5,
  dash: string = "",
): string {
  const y1 = fn(x1);
  const y2 = fn(x2);
  const m = (y2 - y1) / (x2 - x1);
  const yL = y1 + m * (xRange[0] - x1);
  const yR = y1 + m * (xRange[1] - x1);
  return `<line x1="${xToPx(xRange[0]).toFixed(2)}" y1="${yToPx(yL).toFixed(2)}" x2="${xToPx(xRange[1]).toFixed(2)}" y2="${yToPx(yR).toFixed(2)}" stroke="${color}" stroke-width="${width}" stroke-linecap="round" ${dash ? `stroke-dasharray="${dash}"` : ""} />`;
}
