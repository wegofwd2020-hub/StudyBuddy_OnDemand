/**
 * pipeline/visual_templates/shared.ts
 *
 * Universal helpers + style tokens for visual-library SVG generators.
 *
 * Lifted from the 10 per-class generators authored in Epic #326 Wave 1+2
 * (`scripts/generate_*_visuals.ts`), which all imported byte-identical
 * versions of these helpers locally. This module is the single source of
 * truth — class-specific generators in `pipeline/visual_templates/<class>.ts`
 * import from here.
 *
 * Audience:
 *   - Class generator authors (human or LLM via #320 code-gen automation)
 *   - The Wave-3 follow-up to #340 that lifts the remaining 8 class
 *     generators on top of this foundation.
 *
 * What this module deliberately is NOT:
 *   - Class-specific primitives (those live in per-class modules)
 *   - Layout/composition (those live in component modules)
 *   - Anything Remotion-specific (lift target: visual_templates/remotion_project.ts)
 *
 * Citation: synthesised from automation_readiness.md §1.1.
 */

import { writeFileSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";

// ─────────────────────────────────────────────────────────────────────────
// Style tokens — locked palette across every generator
//
// These appeared byte-identically in all 10 Wave-1+2 generators. Any new
// generator must use these or extend them via per-class palette modules
// (e.g. visual_templates/biology_palette.ts) — never override them inline.
// ─────────────────────────────────────────────────────────────────────────

export const INK = "#1a202c";       // text + structural lines
export const MUTED = "#4a5568";     // secondary text
export const ACCENT = "#2b6cb0";    // primary accent (blue)
export const ACCENT_2 = "#dd6b20";  // secondary accent (orange)
export const ACCENT_3 = "#319795";  // tertiary accent (teal)
export const POSITIVE = "#15803d";  // success / current arrow
export const NEGATIVE = "#dc2626";  // warning / opposing direction
export const GRID = "#e2e8f0";      // grid lines
export const AXIS = "#94a3b8";      // axis lines
export const BG = "#f7fafc";        // plot background
export const HIGHLIGHT = "#fef3c7"; // pale-yellow callout / formula card

// ─────────────────────────────────────────────────────────────────────────
// Plot infra — makePlot + polyline
//
// makePlot stamps the axis frame, grid, and labels for a 2D coordinate
// plot, returning pixel-conversion functions and the rendered prelude.
// polyline maps a list of (x, y) data points through those conversion
// functions and emits an SVG <polyline> element.
//
// These two helpers cover ~70% of physics + math figures across the
// Wave 1+2 corpus. Class-specific primitives compose on top.
// ─────────────────────────────────────────────────────────────────────────

export type PlotConfig = {
  width: number;
  height: number;
  pad: { l: number; r: number; t: number; b: number };
  xRange: [number, number];
  yRange: [number, number];
  xTicks: number[];
  yTicks: number[];
  xLabel: string;
  yLabel: string;
  title?: string;
};

export type PlotResult = {
  pieces: string[];
  xToPx: (x: number) => number;
  yToPx: (y: number) => number;
  innerW: number;
  innerH: number;
  x0: number;
  y0: number;
};

/**
 * Two `makePlot` variants existed across the Wave 1+2 generators. They
 * differ in three behaviours; this options object captures the diff so a
 * single function produces byte-equivalent output for either variant.
 *
 * - `axisStyle`:
 *     `'always'` (variant-A — oscillations) renders both x-axis and y-axis
 *     lines unconditionally as the bottom and left edge of the plot area.
 *     `'when-zero-in-range'` (variant-B — kinematics, derivatives, g8_waves,
 *     g9_kinematics) renders an axis line only if 0 falls inside the
 *     corresponding range, so the line passes through y=0 / x=0.
 *
 * - `yLabelOffset`:
 *     Pixel offset between the plot's left edge and the rotated y-axis
 *     label. Variant-A uses `-32`, variant-B uses `-36`.
 *
 * - `titlePosition`:
 *     `'above-plot'` (variant-A) places the title at `(x0 + innerW/2, y0 - 10)`
 *     — centred over the plot region, immediately above it.
 *     `'absolute-top'` (variant-B) places the title at `(W/2, 20)` — centred
 *     in the viewBox, near the top edge. Differs from `'above-plot'` only
 *     when `pad.l != pad.r` or when the plot region is not at the top.
 */
export type MakePlotOptions = {
  /**
   * - `'always'` (variant-A) — always draws bottom-and-left axis lines as
   *   the plot border.
   * - `'when-zero-in-range'` (variant-B) — draws axis lines through y=0 and
   *   x=0 if those values fall inside the respective ranges.
   * - `'when-y-zero-only'` (variant-B-Y) — like variant-B but suppresses
   *   the x=0 axis line. Used by the g8_waves generator whose local helper
   *   only ever checked yRange.
   */
  axisStyle?: "always" | "when-zero-in-range" | "when-y-zero-only";
  yLabelOffset?: number;
  titlePosition?: "above-plot" | "absolute-top";
};

const DEFAULT_OPTS: Required<MakePlotOptions> = {
  axisStyle: "always",
  yLabelOffset: -32,
  titlePosition: "above-plot",
};

/** Variant-B preset: kinematics, derivatives, g8_waves, g9_kinematics. */
export const VARIANT_B: Required<MakePlotOptions> = {
  axisStyle: "when-zero-in-range",
  yLabelOffset: -36,
  titlePosition: "absolute-top",
};

export function makePlot(c: PlotConfig, opts?: MakePlotOptions): PlotResult {
  const o = { ...DEFAULT_OPTS, ...(opts ?? {}) };
  const W = c.width;
  const H = c.height;
  const innerW = W - c.pad.l - c.pad.r;
  const innerH = H - c.pad.t - c.pad.b;
  const x0 = c.pad.l;
  const y0 = c.pad.t;

  const xToPx = (x: number): number =>
    x0 + ((x - c.xRange[0]) / (c.xRange[1] - c.xRange[0])) * innerW;
  const yToPx = (y: number): number =>
    y0 + innerH - ((y - c.yRange[0]) / (c.yRange[1] - c.yRange[0])) * innerH;

  const pieces: string[] = [];

  pieces.push(
    `<rect x="${x0}" y="${y0}" width="${innerW}" height="${innerH}" ` +
      `fill="${BG}" stroke="${GRID}" />`,
  );

  for (const x of c.xTicks) {
    const px = xToPx(x);
    pieces.push(
      `<line x1="${px}" y1="${y0}" x2="${px}" y2="${y0 + innerH}" ` +
        `stroke="${GRID}" stroke-width="0.6" />`,
    );
    pieces.push(
      `<text x="${px}" y="${y0 + innerH + 14}" font="11px system-ui" ` +
        `font-size="11" fill="${MUTED}" text-anchor="middle">${x}</text>`,
    );
  }
  for (const y of c.yTicks) {
    const py = yToPx(y);
    pieces.push(
      `<line x1="${x0}" y1="${py}" x2="${x0 + innerW}" y2="${py}" ` +
        `stroke="${GRID}" stroke-width="0.6" />`,
    );
    pieces.push(
      `<text x="${x0 - 6}" y="${py + 4}" font="11px system-ui" ` +
        `font-size="11" fill="${MUTED}" text-anchor="end">${y}</text>`,
    );
  }

  // Axis lines — variant-A always; variant-B only when 0 is inside the range;
  // variant-B-Y like variant-B but suppresses the x=0 axis line.
  if (o.axisStyle === "always") {
    pieces.push(
      `<line x1="${x0}" y1="${y0 + innerH}" x2="${x0 + innerW}" ` +
        `y2="${y0 + innerH}" stroke="${AXIS}" stroke-width="1.2" />`,
    );
    pieces.push(
      `<line x1="${x0}" y1="${y0}" x2="${x0}" y2="${y0 + innerH}" ` +
        `stroke="${AXIS}" stroke-width="1.2" />`,
    );
  } else {
    if (c.yRange[0] <= 0 && c.yRange[1] >= 0) {
      const py = yToPx(0);
      pieces.push(
        `<line x1="${x0}" y1="${py}" x2="${x0 + innerW}" y2="${py}" ` +
          `stroke="${AXIS}" stroke-width="1.2" />`,
      );
    }
    if (
      o.axisStyle === "when-zero-in-range" &&
      c.xRange[0] <= 0 &&
      c.xRange[1] >= 0
    ) {
      const px = xToPx(0);
      pieces.push(
        `<line x1="${px}" y1="${y0}" x2="${px}" y2="${y0 + innerH}" ` +
          `stroke="${AXIS}" stroke-width="1.2" />`,
      );
    }
  }

  pieces.push(
    `<text x="${x0 + innerW / 2}" y="${y0 + innerH + 32}" ` +
      `font="13px system-ui" font-size="13" font-weight="600" ` +
      `fill="${INK}" text-anchor="middle">${c.xLabel}</text>`,
  );
  const yLx = x0 + o.yLabelOffset;
  pieces.push(
    `<text x="${yLx}" y="${y0 + innerH / 2}" ` +
      `font="13px system-ui" font-size="13" font-weight="600" ` +
      `fill="${INK}" text-anchor="middle" ` +
      `transform="rotate(-90 ${yLx} ${y0 + innerH / 2})">${c.yLabel}</text>`,
  );

  if (c.title) {
    if (o.titlePosition === "above-plot") {
      pieces.push(
        `<text x="${x0 + innerW / 2}" y="${y0 - 10}" ` +
          `font="bold 14px system-ui" font-size="14" font-weight="700" ` +
          `fill="${INK}" text-anchor="middle">${c.title}</text>`,
      );
    } else {
      // 'absolute-top' — variant-B convention; viewBox-centred, y=20.
      pieces.push(
        `<text x="${W / 2}" y="20" ` +
          `font="bold 14px system-ui" font-size="14" font-weight="700" ` +
          `fill="${INK}" text-anchor="middle">${c.title}</text>`,
      );
    }
  }

  return { pieces, xToPx, yToPx, innerW, innerH, x0, y0 };
}

export function polyline(
  points: Array<[number, number]>,
  xToPx: (x: number) => number,
  yToPx: (y: number) => number,
  stroke: string,
  width = 2,
  dash?: string,
): string {
  const pts = points
    .map(([x, y]) => `${xToPx(x).toFixed(2)},${yToPx(y).toFixed(2)}`)
    .join(" ");
  const dashAttr = dash ? ` stroke-dasharray="${dash}"` : "";
  return (
    `<polyline points="${pts}" fill="none" stroke="${stroke}" ` +
    `stroke-width="${width}" stroke-linecap="round"${dashAttr} />`
  );
}

/**
 * `plotPolyline` — sample a function across xRange and emit an SVG polyline.
 *
 * Differs from `polyline` (above) in the input shape: takes a function +
 * x-range and samples internally rather than accepting pre-computed points.
 * Skips non-finite y values (NaN, Infinity) so functions with vertical
 * asymptotes plot cleanly across their domain.
 *
 * Lifted from 4 byte-identical copies across kinematics, g9_kinematics,
 * derivatives, and g8_waves generators (#341 phase C-partial). The output
 * format preserves the exact two-space gap before `/>` in the no-dash case
 * for byte-equivalence with the local helper it replaces.
 */
export function plotPolyline(
  fn: (x: number) => number,
  xRange: [number, number],
  xToPx: (x: number) => number,
  yToPx: (y: number) => number,
  options: {
    color?: string;
    width?: number;
    samples?: number;
    dash?: string;
  } = {},
): string {
  const { color = ACCENT, width = 3, samples = 200, dash = "" } = options;
  const pts: string[] = [];
  for (let i = 0; i <= samples; i++) {
    const x = xRange[0] + (i / samples) * (xRange[1] - xRange[0]);
    const y = fn(x);
    if (!Number.isFinite(y)) continue;
    pts.push(`${xToPx(x).toFixed(2)},${yToPx(y).toFixed(2)}`);
  }
  return `<polyline points="${pts.join(" ")}" fill="none" stroke="${color}" stroke-width="${width}" stroke-linecap="round" ${dash ? `stroke-dasharray="${dash}"` : ""} />`;
}

// ─────────────────────────────────────────────────────────────────────────
// SVG envelope — svgWrap
//
// Wraps the inner body with the standard accessibility metadata. Every
// shipped SVG must have a <title> and <desc> for screen readers and a
// role="img" + aria-label for assistive tech.
// ─────────────────────────────────────────────────────────────────────────

export function svgWrap(
  viewBoxW: number,
  viewBoxH: number,
  title: string,
  desc: string,
  body: string,
): string {
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${viewBoxW} ${viewBoxH}" width="${viewBoxW}" height="${viewBoxH}" role="img" aria-label="${title}">
  <title>${title}</title>
  <desc>${desc}</desc>
${body}
</svg>`;
}

/**
 * Pretty-formatted variant of `svgWrap` — adds 2-space indent before the
 * body and a trailing newline. Used by generators whose original local
 * `svgWrap` shipped with this format (electronics_circuit,
 * organic_chemistry, periodic_table, biology_cells, optics, derivatives,
 * g8_waves, g9_kinematics, kinematics).
 *
 * Functionally equivalent to `svgWrap` (same rendered SVG); the extra
 * whitespace is purely stylistic. Maintained here to preserve byte-
 * equivalence when lifting helpers like `makeHeatmapSvg` from these
 * generators into class modules.
 */
export function svgWrapPretty(
  viewBoxW: number,
  viewBoxH: number,
  title: string,
  desc: string,
  body: string,
): string {
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${viewBoxW} ${viewBoxH}" width="${viewBoxW}" height="${viewBoxH}" role="img" aria-label="${title}">
  <title>${title}</title>
  <desc>${desc}</desc>
  ${body}
</svg>
`;
}

// ─────────────────────────────────────────────────────────────────────────
// File output — makeWriter
//
// Factory pattern: each generator binds a root directory once, then writes
// relative paths into it. The factory replaces the per-script `write()`
// helper that was duplicated across all 10 generators.
//
// Usage:
//   const write = makeWriter(join(import.meta.dir, "..", "sample_content",
//                                  "g11-science", "G11-PHYS-010_..."));
//   write("Option2_Catalogue/section-1/foo.svg", svgContent);
// ─────────────────────────────────────────────────────────────────────────

export type Writer = (rel: string, body: string) => void;

export function makeWriter(root: string): Writer {
  return (rel: string, body: string): void => {
    const path = join(root, rel);
    mkdirSync(dirname(path), { recursive: true });
    writeFileSync(path, body, "utf-8");
    // eslint-disable-next-line no-console
    console.log(`  ✓ ${rel}  (${body.length} bytes)`);
  };
}

// ─────────────────────────────────────────────────────────────────────────
// Sampling — generate (x, y) points along a function
//
// Convenience for the very common pattern: "evaluate fn at N+1 points
// across xRange, return as Array<[x, y]>". Used by every plot in the
// physics + math generators.
// ─────────────────────────────────────────────────────────────────────────

export function samples(
  fn: (x: number) => number,
  xRange: [number, number],
  n = 200,
): Array<[number, number]> {
  const [xMin, xMax] = xRange;
  const out: Array<[number, number]> = [];
  for (let i = 0; i <= n; i++) {
    const x = xMin + ((xMax - xMin) * i) / n;
    out.push([x, fn(x)]);
  }
  return out;
}
