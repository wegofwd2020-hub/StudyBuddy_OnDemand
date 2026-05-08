/**
 * pipeline/visual_templates/kinematics.ts
 *
 * Class-specific primitives for kinematics + motion catalogues.
 *
 * Lifted from `scripts/generate_g9_kinematics_visuals.ts` per #342 phase C.
 * Patterns identified in the G9 / G11 MEMOs as templatable for #320.
 *
 * Exports:
 *   - `slopeTriangle()` — dashed right-triangle annotation showing Δx/Δy on a plot
 *   - `motionStrip()`   — stroboscopic dot-trail showing position-at-each-second
 */

// ─────────────────────────────────────────────────────────────────────────
// slopeTriangle — annotation showing rise-over-run on a coordinate plot
//
// Used by G9-SCI-001 to identify slope-as-speed (s2_xtUniform) and slope-as-
// acceleration (s3_vtAccelerated). The pattern composes a horizontal dashed
// line, a vertical dashed line, and two labels positioned at midpoints.
//
// All coordinates are *pixel* (post-xToPx/yToPx); the helper does no plot-
// to-pixel conversion. Caller passes the four corners of the right triangle
// (top-left + bottom-right; the helper draws the sides through xb,ya).
// ─────────────────────────────────────────────────────────────────────────

export function slopeTriangle(
  xa: number,
  ya: number,
  xb: number,
  yb: number,
  color: string,
  dxLabel: string,
  dyLabel: string,
): string {
  return [
    `<line x1="${xa}" y1="${ya}" x2="${xb}" y2="${ya}" stroke="${color}" stroke-width="1.5" stroke-dasharray="4 3" />`,
    `<line x1="${xb}" y1="${ya}" x2="${xb}" y2="${yb}" stroke="${color}" stroke-width="1.5" stroke-dasharray="4 3" />`,
    `<text x="${(xa + xb) / 2}" y="${ya - 6}" font="11px system-ui" font-size="11" fill="${color}" text-anchor="middle">${dxLabel}</text>`,
    `<text x="${xb + 4}" y="${(ya + yb) / 2}" font="11px system-ui" font-size="11" fill="${color}" text-anchor="start">${dyLabel}</text>`,
  ].join("");
}

// ─────────────────────────────────────────────────────────────────────────
// motionStrip — stroboscopic position-at-each-second visualisation
//
// A horizontal dashed baseline, N circles spaced according to a position
// function (uniform: equal gaps; accelerated: 0.5·t² spacing), and a row
// of `[--]` interval markers above each gap to make the spacing pattern
// visible. Used in G9-SCI-001 for the canonical uniform-vs-accelerated
// motion comparison.
//
// `positionFn(i)` returns the *raw* physical position of the i-th dot;
// the helper rescales the [0, max] range onto [x0, x1] pixel coordinates.
// For uniform motion pass `(i) => i`; for x = 0.5·a·t² pass `(i) => 0.5*i*i`.
// ─────────────────────────────────────────────────────────────────────────

export type MotionStripOptions = {
  width: number;
  height: number;
  title: string;
  subtitle: string;
  summaryText: string;
  N: number;
  /** Returns the physical position of the i-th dot (i in [0, N-1]). */
  positionFn: (i: number) => number;
  /** Colour for the moving dots. */
  dotColor: string;
  /** Colour for the spacing markers + summary text. */
  markerColor: string;
  /** SVG-stringable colours for ink + muted text (defaults from shared.ts). */
  ink: string;
  muted: string;
  /** Optional bounds; defaults match the G9 catalogue (480×200, x0=40, x1=440, stripY=110). */
  x0?: number;
  x1?: number;
  stripY?: number;
};

export function motionStrip(opts: MotionStripOptions): string {
  const W = opts.width;
  const H = opts.height;
  const x0 = opts.x0 ?? 40;
  const x1 = opts.x1 ?? 440;
  const stripY = opts.stripY ?? 110;
  const N = opts.N;

  const xMax = opts.positionFn(N - 1);
  const safeMax = xMax === 0 ? 1 : xMax;

  let body = `
  <text x="${W / 2}" y="22" font="bold 14px system-ui" font-size="14" font-weight="700" fill="${opts.ink}" text-anchor="middle">${opts.title}</text>
  <text x="${W / 2}" y="40" font="11px system-ui" font-size="11" fill="${opts.muted}" text-anchor="middle">${opts.subtitle}</text>

  <line x1="${x0}" y1="${stripY}" x2="${x1}" y2="${stripY}" stroke="${opts.muted}" stroke-width="1.5" stroke-dasharray="4 4" />
`;

  for (let i = 0; i < N; i++) {
    const xphys = opts.positionFn(i);
    const px = x0 + (xphys / safeMax) * (x1 - x0);
    body += `
  <circle cx="${px}" cy="${stripY}" r="9" fill="${opts.dotColor}" stroke="${opts.ink}" stroke-width="1.5" />
  <text x="${px}" y="${stripY + 30}" font="11px system-ui" font-size="11" fill="${opts.muted}" text-anchor="middle">t = ${i} s</text>`;
  }

  // Spacing markers: a `[—]`-style bracket above each gap.
  for (let i = 0; i < N - 1; i++) {
    const aPhys = opts.positionFn(i);
    const bPhys = opts.positionFn(i + 1);
    const a = x0 + (aPhys / safeMax) * (x1 - x0);
    const b = x0 + (bPhys / safeMax) * (x1 - x0);
    body += `
  <line x1="${a + 10}" y1="${stripY - 25}" x2="${b - 10}" y2="${stripY - 25}" stroke="${opts.markerColor}" stroke-width="1.5" />
  <line x1="${a + 10}" y1="${stripY - 30}" x2="${a + 10}" y2="${stripY - 20}" stroke="${opts.markerColor}" stroke-width="1.5" />
  <line x1="${b - 10}" y1="${stripY - 30}" x2="${b - 10}" y2="${stripY - 20}" stroke="${opts.markerColor}" stroke-width="1.5" />`;
  }

  body += `
  <text x="${W / 2}" y="${stripY - 38}" font="bold 12px system-ui" font-size="12" font-weight="700" fill="${opts.markerColor}" text-anchor="middle">${opts.summaryText}</text>
`;

  return body;
}
