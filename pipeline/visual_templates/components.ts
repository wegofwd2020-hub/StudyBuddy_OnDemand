/**
 * pipeline/visual_templates/components.ts
 *
 * Cross-class shared SVG components — primitives that recurred across 3+
 * subject classes during Epic #326 Wave 1+2 hand-authoring. Each component
 * is a function returning an SVG fragment string composable into a larger
 * `<svg>` body.
 *
 * Naming convention: lowercase-camel matching the local helper names in the
 * source generators they were lifted from. Some primitives appear in
 * `automation_readiness.md` §1.2 with PascalCase JSX-like names like
 * `<LeaderLabel />` — those are intentional metaphors for "how a future #320
 * code-gen consumer would *call* the helper", not React components. The
 * actual exports here are TS functions returning strings.
 *
 * Lifted from `scripts/generate_*_visuals.ts` per #342 phases C+D. Each
 * lift verified byte-equivalent vs pre-lift output snapshots.
 */

// ─────────────────────────────────────────────────────────────────────────
// leaderLabel — short line + text label at line-end
//
// Used by every figure in `generate_biology_cells_visuals.ts` (~30+ call
// sites) and inline in chemistry/electronics labelled-component patterns.
// Lifted from biology_cells where it was already factored as a local helper.
// ─────────────────────────────────────────────────────────────────────────

export function leaderLabel(
  fromX: number,
  fromY: number,
  toX: number,
  toY: number,
  text: string,
  color: string,
  anchor: "start" | "middle" | "end" = "start",
  fontSize = 13,
  bold = true,
): string {
  return `
  <line x1="${fromX}" y1="${fromY}" x2="${toX}" y2="${toY}" stroke="${color}" stroke-width="1.5" />
  <text x="${toX + (anchor === "start" ? 4 : anchor === "end" ? -4 : 0)}" y="${toY + 4}"
    font="${bold ? "bold " : ""}${fontSize}px system-ui" font-size="${fontSize}" font-weight="${bold ? 700 : 400}"
    fill="${color}" text-anchor="${anchor}">${text}</text>`;
}

// ─────────────────────────────────────────────────────────────────────────
// dotCluster — sprinkle small dots inside an elliptical region
//
// Originally `ribosomeDots()` in biology_cells; the same pattern was
// observed inline for electron clouds in chemistry_atom. Generalised here
// with optional `size` parameter; default 2.2 matches the original
// hardcoded radius, preserving byte-equivalence at the existing call sites.
// ─────────────────────────────────────────────────────────────────────────

export function dotCluster(
  cx: number,
  cy: number,
  rx: number,
  ry: number,
  count: number,
  color: string,
  size = 2.2,
): string {
  let s = "";
  for (let i = 0; i < count; i++) {
    const ang = (i / count) * Math.PI * 2 + i * 0.7;
    const r = ry * (0.5 + 0.4 * Math.cos(ang * 1.7));
    const x = cx + r * Math.cos(ang) * (rx / ry);
    const y = cy + r * Math.sin(ang);
    s += `<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="${size}" fill="${color}" />`;
  }
  return s;
}

// ─────────────────────────────────────────────────────────────────────────
// Cross-class re-exports
//
// Primitives that live in class modules but are documented in
// automation_readiness.md §1.2 as cross-class. Re-exporting here gives
// #320 (and any future cross-class consumer) a single import surface for
// "primitives that recur across 3+ subject classes" without forcing the
// consumer to know which class module each lives in.
// ─────────────────────────────────────────────────────────────────────────

/**
 * Re-exported from `./kinematics.ts`. Per `automation_readiness.md` §1.2,
 * `motionStrip` is reused across G9 kinematics + future G6 forces, G7 energy,
 * G9 Newton's-laws units. Cross-class.
 */
export {
  motionStrip,
  type MotionStripOptions,
} from "./kinematics.ts";

/**
 * Re-exported from `./derivatives.ts`. Per the G11-MATH-002 MEMO, `secantLine`
 * lifts from the SVG generator into the Remotion `<TangentEmergenceScene />`
 * verbatim. Cross-class because the same helper produces both static and
 * animated variants.
 */
export { secantLine } from "./derivatives.ts";
