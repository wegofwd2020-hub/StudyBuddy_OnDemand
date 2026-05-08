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

export function makePlot(c: PlotConfig): PlotResult {
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

  pieces.push(
    `<line x1="${x0}" y1="${y0 + innerH}" x2="${x0 + innerW}" ` +
      `y2="${y0 + innerH}" stroke="${AXIS}" stroke-width="1.2" />`,
  );
  pieces.push(
    `<line x1="${x0}" y1="${y0}" x2="${x0}" y2="${y0 + innerH}" ` +
      `stroke="${AXIS}" stroke-width="1.2" />`,
  );

  pieces.push(
    `<text x="${x0 + innerW / 2}" y="${y0 + innerH + 32}" ` +
      `font="13px system-ui" font-size="13" font-weight="600" ` +
      `fill="${INK}" text-anchor="middle">${c.xLabel}</text>`,
  );
  pieces.push(
    `<text x="${x0 - 32}" y="${y0 + innerH / 2}" ` +
      `font="13px system-ui" font-size="13" font-weight="600" ` +
      `fill="${INK}" text-anchor="middle" ` +
      `transform="rotate(-90 ${x0 - 32} ${y0 + innerH / 2})">${c.yLabel}</text>`,
  );

  if (c.title) {
    pieces.push(
      `<text x="${x0 + innerW / 2}" y="${y0 - 10}" ` +
        `font="bold 14px system-ui" font-size="14" font-weight="700" ` +
        `fill="${INK}" text-anchor="middle">${c.title}</text>`,
    );
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
