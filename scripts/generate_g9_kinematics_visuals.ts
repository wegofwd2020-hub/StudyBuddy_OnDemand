#!/usr/bin/env bun
/**
 * Generate the Option-2 SVG catalogue for G9-SCI-001 Kinematics 1D
 * (issue #328).
 *
 * Run from repo root:
 *   bun scripts/generate_g9_kinematics_visuals.ts
 *
 * Output: sample_content/g9-stem/G9-SCI-001_Kinematics_1D/Option2_Catalogue/section-N/*.svg
 *
 * Recipe is a direct lift from scripts/generate_kinematics_visuals.ts and
 * scripts/generate_oscillations_visuals.ts — same makePlot helper shape,
 * same colour palette, same fontless inline styling.
 *
 * Scope vs the G11-PHYS-002 catalogue:
 *   - G9 uses *speed* (scalar), G11 uses *velocity* (signed vector)
 *   - 1D only — no projectile, no free-fall (those are G11)
 *   - Heavy on uniform-vs-accelerated comparisons (the central G9 pedagogy)
 *   - Two new motion-strip primitives (equally-spaced dots vs increasingly-spaced)
 */

import { writeFileSync, mkdirSync } from "node:fs";
import { join, dirname } from "node:path";

// Style tokens lifted to pipeline/visual_templates/shared.ts per #340.
// makePlot + plotPolyline kept local: this generator uses the variant-B
// makePlot (axis-lines-only-when-0-in-range, yLabel offset -36, title at
// y=20) which differs from the variant-A makePlot in shared.ts. The
// makePlot consolidation is followup work — see the post-#340 issue.
import {
  INK,
  MUTED,
  ACCENT,
  ACCENT_2,
  ACCENT_3,
  POSITIVE,
  NEGATIVE,
  GRID,
  AXIS,
  BG,
} from "../pipeline/visual_templates/shared.ts";

const ROOT = join(
  import.meta.dir,
  "..",
  "sample_content",
  "g9-stem",
  "G9-SCI-001_Kinematics_1D",
  "Option2_Catalogue",
);

// ────────────────────────────────────────────────────────────────────────────
// Helpers (lifted verbatim from generate_kinematics_visuals.ts)
// ────────────────────────────────────────────────────────────────────────────

type PlotConfig = {
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

function makePlot(c: PlotConfig) {
  const W = c.width, H = c.height;
  const innerW = W - c.pad.l - c.pad.r;
  const innerH = H - c.pad.t - c.pad.b;
  const x0 = c.pad.l;
  const y0 = c.pad.t;

  const xToPx = (x: number) =>
    x0 + ((x - c.xRange[0]) / (c.xRange[1] - c.xRange[0])) * innerW;
  const yToPx = (y: number) =>
    y0 + innerH - ((y - c.yRange[0]) / (c.yRange[1] - c.yRange[0])) * innerH;

  const pieces: string[] = [];
  pieces.push(`<rect x="${x0}" y="${y0}" width="${innerW}" height="${innerH}" fill="${BG}" stroke="${GRID}" />`);

  for (const x of c.xTicks) {
    const px = xToPx(x);
    pieces.push(`<line x1="${px}" y1="${y0}" x2="${px}" y2="${y0 + innerH}" stroke="${GRID}" stroke-width="0.6" />`);
    pieces.push(`<text x="${px}" y="${y0 + innerH + 14}" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">${x}</text>`);
  }
  for (const y of c.yTicks) {
    const py = yToPx(y);
    pieces.push(`<line x1="${x0}" y1="${py}" x2="${x0 + innerW}" y2="${py}" stroke="${GRID}" stroke-width="0.6" />`);
    pieces.push(`<text x="${x0 - 6}" y="${py + 4}" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="end">${y}</text>`);
  }

  if (c.yRange[0] <= 0 && c.yRange[1] >= 0) {
    const py = yToPx(0);
    pieces.push(`<line x1="${x0}" y1="${py}" x2="${x0 + innerW}" y2="${py}" stroke="${AXIS}" stroke-width="1.2" />`);
  }
  if (c.xRange[0] <= 0 && c.xRange[1] >= 0) {
    const px = xToPx(0);
    pieces.push(`<line x1="${px}" y1="${y0}" x2="${px}" y2="${y0 + innerH}" stroke="${AXIS}" stroke-width="1.2" />`);
  }

  pieces.push(`<text x="${x0 + innerW / 2}" y="${y0 + innerH + 32}" font="13px system-ui" font-size="13" font-weight="600" fill="${INK}" text-anchor="middle">${c.xLabel}</text>`);
  pieces.push(`<text x="${x0 - 36}" y="${y0 + innerH / 2}" font="13px system-ui" font-size="13" font-weight="600" fill="${INK}" text-anchor="middle" transform="rotate(-90 ${x0 - 36} ${y0 + innerH / 2})">${c.yLabel}</text>`);

  if (c.title) {
    pieces.push(`<text x="${W / 2}" y="20" font="bold 14px system-ui" font-size="14" font-weight="700" fill="${INK}" text-anchor="middle">${c.title}</text>`);
  }

  return { pieces, xToPx, yToPx, x0, y0, innerW, innerH };
}

function plotPolyline(
  fn: (x: number) => number,
  xRange: [number, number],
  xToPx: (x: number) => number,
  yToPx: (y: number) => number,
  options: { color?: string; width?: number; samples?: number; dash?: string } = {},
) {
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

function svgWrap(viewBoxW: number, viewBoxH: number, title: string, desc: string, body: string) {
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${viewBoxW} ${viewBoxH}" width="${viewBoxW}" height="${viewBoxH}" role="img" aria-label="${title}">
  <title>${title}</title>
  <desc>${desc}</desc>
  ${body}
</svg>
`;
}

function write(rel: string, body: string) {
  const path = join(ROOT, rel);
  mkdirSync(dirname(path), { recursive: true });
  writeFileSync(path, body);
  console.log("wrote", rel);
}

// ────────────────────────────────────────────────────────────────────────────
// SECTION 1 — Fundamentals (3 SVGs)
// ────────────────────────────────────────────────────────────────────────────

function s1_1dPosition() {
  // Number-line view of position along a straight road.
  const W = 480, H = 220;
  const lineY = 130;
  const x0 = 40, x1 = 440;
  const ticks = [-3, -2, -1, 0, 1, 2, 3, 4, 5];
  const tickPx = (v: number) => x0 + ((v - ticks[0]) / (ticks[ticks.length - 1] - ticks[0])) * (x1 - x0);

  let body = `
  <text x="${W / 2}" y="22" font="bold 14px system-ui" font-size="14" font-weight="700" fill="${INK}" text-anchor="middle">Position on a Straight Road</text>
  <text x="${W / 2}" y="40" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">A position is a single number telling you where along the road, measured from a chosen origin.</text>

  <line x1="${x0 - 4}" y1="${lineY}" x2="${x1 + 4}" y2="${lineY}" stroke="${INK}" stroke-width="2" />
  <polygon points="${x1 + 4},${lineY} ${x1 - 6},${lineY - 5} ${x1 - 6},${lineY + 5}" fill="${INK}" />
  <polygon points="${x0 - 4},${lineY} ${x0 + 6},${lineY - 5} ${x0 + 6},${lineY + 5}" fill="${INK}" />
`;
  for (const t of ticks) {
    const px = tickPx(t);
    const isOrigin = t === 0;
    body += `
  <line x1="${px}" y1="${lineY - (isOrigin ? 10 : 6)}" x2="${px}" y2="${lineY + (isOrigin ? 10 : 6)}" stroke="${INK}" stroke-width="${isOrigin ? 2 : 1}" />
  <text x="${px}" y="${lineY + 28}" font="${isOrigin ? "bold " : ""}12px system-ui" font-size="12" font-weight="${isOrigin ? 700 : 500}" fill="${isOrigin ? INK : MUTED}" text-anchor="middle">${t}</text>`;
  }
  // Two example positions
  const pA = tickPx(-2);
  const pB = tickPx(3);
  body += `
  <circle cx="${pA}" cy="${lineY}" r="6" fill="${ACCENT_2}" stroke="${INK}" stroke-width="1.5" />
  <text x="${pA}" y="${lineY - 18}" font="bold 12px system-ui" font-size="12" font-weight="700" fill="${ACCENT_2}" text-anchor="middle">x = −2 m</text>
  <circle cx="${pB}" cy="${lineY}" r="6" fill="${ACCENT}" stroke="${INK}" stroke-width="1.5" />
  <text x="${pB}" y="${lineY - 18}" font="bold 12px system-ui" font-size="12" font-weight="700" fill="${ACCENT}" text-anchor="middle">x = +3 m</text>
  <text x="${tickPx(0)}" y="${lineY + 50}" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">origin (x = 0)</text>
  <text x="${x1 + 4}" y="${lineY + 50}" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="end">positive direction →</text>
`;
  return svgWrap(W, H, "Position on a straight road", "A horizontal number line marked in metres with two example positions: x = −2 m on the negative side and x = +3 m on the positive side.", body);
}

function s1_distanceVsDisplacement() {
  // Curved walking path from A to B; total path length vs straight-line distance.
  const W = 480, H = 280;
  const body = `
  <defs>
    <marker id="arr-disp" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="9" markerHeight="9" orient="auto">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="${ACCENT}" />
    </marker>
  </defs>

  <text x="${W / 2}" y="22" font="bold 14px system-ui" font-size="14" font-weight="700" fill="${INK}" text-anchor="middle">Distance Walked vs. Displacement</text>

  <path d="M 80 200 Q 160 70, 260 140 T 400 90" fill="none" stroke="${ACCENT_2}" stroke-width="3.5" />
  <line x1="80" y1="200" x2="400" y2="90" stroke="${ACCENT}" stroke-width="3" stroke-dasharray="6 4" marker-end="url(#arr-disp)" />

  <circle cx="80" cy="200" r="6" fill="${INK}" />
  <text x="68" y="220" font="bold 13px system-ui" font-size="13" font-weight="700" fill="${INK}">A</text>
  <circle cx="400" cy="90" r="6" fill="${INK}" />
  <text x="408" y="88" font="bold 13px system-ui" font-size="13" font-weight="700" fill="${INK}">B</text>

  <text x="180" y="100" font="bold 12px system-ui" font-size="12" font-weight="700" fill="${ACCENT_2}">curved walked path → total distance ≈ 460 m</text>
  <text x="180" y="170" font="bold 12px system-ui" font-size="12" font-weight="700" fill="${ACCENT}">straight A→B → displacement ≈ 340 m</text>

  <text x="${W / 2}" y="252" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">Distance is how far you walked along the path. Displacement is how far you ended up from the start, in a straight line.</text>
  <text x="${W / 2}" y="268" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">Distance ≥ Displacement, always.</text>
`;
  return svgWrap(W, H, "Distance walked vs displacement", "A curved walking path from point A to point B, with the straight-line displacement vector overlaid in dashed blue. Total distance walked along the curve is greater than the straight-line displacement.", body);
}

function s1_avgVsInstantaneousSpeed() {
  // Two-row diagram: speedometer-like time interval bars.
  const W = 480, H = 240;
  let body = `
  <text x="${W / 2}" y="22" font="bold 14px system-ui" font-size="14" font-weight="700" fill="${INK}" text-anchor="middle">Average Speed vs. Instantaneous Speed</text>

  <text x="60" y="58" font="bold 12px system-ui" font-size="12" font-weight="700" fill="${ACCENT}">Average speed</text>
  <text x="60" y="74" font="11px system-ui" font-size="11" fill="${MUTED}">total distance ÷ total time over the whole trip</text>
  <text x="60" y="92" font="bold 13px system-ui" font-size="13" font-weight="700" fill="${INK}">120 km in 2 h → 60 km/h</text>
  <rect x="60" y="100" width="360" height="20" fill="${ACCENT}" opacity="0.25" stroke="${ACCENT}" stroke-width="1.5" />
  <text x="240" y="115" font="bold 12px system-ui" font-size="12" font-weight="700" fill="${ACCENT}" text-anchor="middle">2 hours · one number for the whole trip</text>

  <text x="60" y="158" font="bold 12px system-ui" font-size="12" font-weight="700" fill="${ACCENT_2}">Instantaneous speed</text>
  <text x="60" y="174" font="11px system-ui" font-size="11" fill="${MUTED}">the speedometer reading at one instant</text>
`;
  // Five varying-speed boxes
  const widths = [70, 90, 50, 80, 70];
  const labels = ["75", "85", "30", "70", "55"];
  let xc = 60;
  for (let i = 0; i < widths.length; i++) {
    const w = widths[i];
    const opacity = 0.25 + (i % 2) * 0.15;
    body += `
  <rect x="${xc}" y="186" width="${w}" height="20" fill="${ACCENT_2}" opacity="${opacity}" stroke="${ACCENT_2}" stroke-width="1.2" />
  <text x="${xc + w / 2}" y="201" font="bold 11px system-ui" font-size="11" font-weight="700" fill="${INK}" text-anchor="middle">${labels[i]} km/h</text>`;
    xc += w;
  }
  body += `
  <text x="${(60 + 420) / 2}" y="226" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">five different instants in the same trip — each speedometer snapshot is different</text>
`;
  return svgWrap(W, H, "Average vs instantaneous speed", "Top: the whole trip's average speed (60 km/h). Bottom: five different speedometer readings during the same trip, each varying from 30 to 85 km/h.", body);
}

// ────────────────────────────────────────────────────────────────────────────
// SECTION 2 — Uniform Motion (3 SVGs)
// ────────────────────────────────────────────────────────────────────────────

function s2_motionStripUniform() {
  // Sequence of equally-spaced dots — a stroboscopic view of uniform motion.
  const W = 480, H = 200;
  const stripY = 110;
  const x0 = 40, x1 = 440;
  const N = 7;
  let body = `
  <text x="${W / 2}" y="22" font="bold 14px system-ui" font-size="14" font-weight="700" fill="${INK}" text-anchor="middle">Motion Strip — Uniform Motion</text>
  <text x="${W / 2}" y="40" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">Strobe snapshots taken every 1 second show the object at equal spacing — its speed is constant.</text>

  <line x1="${x0}" y1="${stripY}" x2="${x1}" y2="${stripY}" stroke="${MUTED}" stroke-width="1.5" stroke-dasharray="4 4" />
`;
  for (let i = 0; i < N; i++) {
    const px = x0 + (i / (N - 1)) * (x1 - x0);
    body += `
  <circle cx="${px}" cy="${stripY}" r="9" fill="${ACCENT}" stroke="${INK}" stroke-width="1.5" />
  <text x="${px}" y="${stripY + 30}" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">t = ${i} s</text>`;
  }
  // Spacing markers
  for (let i = 0; i < N - 1; i++) {
    const a = x0 + (i / (N - 1)) * (x1 - x0);
    const b = x0 + ((i + 1) / (N - 1)) * (x1 - x0);
    body += `
  <line x1="${a + 10}" y1="${stripY - 25}" x2="${b - 10}" y2="${stripY - 25}" stroke="${POSITIVE}" stroke-width="1.5" />
  <line x1="${a + 10}" y1="${stripY - 30}" x2="${a + 10}" y2="${stripY - 20}" stroke="${POSITIVE}" stroke-width="1.5" />
  <line x1="${b - 10}" y1="${stripY - 30}" x2="${b - 10}" y2="${stripY - 20}" stroke="${POSITIVE}" stroke-width="1.5" />`;
  }
  body += `
  <text x="${W / 2}" y="${stripY - 38}" font="bold 12px system-ui" font-size="12" font-weight="700" fill="${POSITIVE}" text-anchor="middle">all gaps equal — equal distance per second → uniform speed</text>
`;
  return svgWrap(W, H, "Motion strip — uniform motion", "Seven equally-spaced dots along a horizontal axis, one per second from t = 0 to t = 6 s, with green tick marks above showing all gaps are equal — the hallmark of uniform motion.", body);
}

function s2_xtUniform() {
  const W = 480, H = 280;
  const cfg: PlotConfig = {
    width: W, height: H,
    pad: { l: 56, r: 24, t: 36, b: 50 },
    xRange: [0, 6], yRange: [0, 30],
    xTicks: [0, 1, 2, 3, 4, 5, 6],
    yTicks: [0, 5, 10, 15, 20, 25, 30],
    xLabel: "time t (seconds)",
    yLabel: "distance d (metres)",
    title: "Distance vs Time — Uniform Motion",
  };
  const { pieces, xToPx, yToPx } = makePlot(cfg);
  // d = 5t, slope = speed = 5 m/s
  pieces.push(plotPolyline((t) => 5 * t, [0, 6], xToPx, yToPx, { color: ACCENT, width: 3.5 }));
  // Slope-triangle annotation between t=2 and t=4
  const xa = xToPx(2), ya = yToPx(10);
  const xb = xToPx(4), yb = yToPx(20);
  pieces.push(`<line x1="${xa}" y1="${ya}" x2="${xb}" y2="${ya}" stroke="${ACCENT_2}" stroke-width="1.5" stroke-dasharray="4 3" />`);
  pieces.push(`<line x1="${xb}" y1="${ya}" x2="${xb}" y2="${yb}" stroke="${ACCENT_2}" stroke-width="1.5" stroke-dasharray="4 3" />`);
  pieces.push(`<text x="${(xa + xb) / 2}" y="${ya - 6}" font="11px system-ui" font-size="11" fill="${ACCENT_2}" text-anchor="middle">Δt = 2 s</text>`);
  pieces.push(`<text x="${xb + 4}" y="${(ya + yb) / 2}" font="11px system-ui" font-size="11" fill="${ACCENT_2}" text-anchor="start">Δd = 10 m</text>`);
  pieces.push(`<text x="${W / 2}" y="${H - 8}" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">slope = Δd / Δt = 10 m / 2 s = 5 m/s — the constant speed</text>`);
  return svgWrap(W, H, "Distance vs time — uniform motion", "A straight line through the origin on a distance-vs-time plot, with a slope-triangle showing rise = 10 m over run = 2 s, identifying the constant speed of 5 m/s.", pieces.join(""));
}

function s2_vtUniform() {
  const W = 480, H = 280;
  const cfg: PlotConfig = {
    width: W, height: H,
    pad: { l: 56, r: 24, t: 36, b: 50 },
    xRange: [0, 6], yRange: [0, 10],
    xTicks: [0, 1, 2, 3, 4, 5, 6],
    yTicks: [0, 2, 4, 6, 8, 10],
    xLabel: "time t (seconds)",
    yLabel: "speed v (m/s)",
    title: "Speed vs Time — Uniform Motion",
  };
  const { pieces, xToPx, yToPx } = makePlot(cfg);
  // v = 5 (constant)
  pieces.push(plotPolyline(() => 5, [0, 6], xToPx, yToPx, { color: ACCENT, width: 3.5 }));
  // Shaded area = distance
  const x0p = xToPx(0), x6p = xToPx(6), y0p = yToPx(0), y5p = yToPx(5);
  pieces.push(`<polygon points="${x0p},${y0p} ${x6p},${y0p} ${x6p},${y5p} ${x0p},${y5p}" fill="${ACCENT}" opacity="0.18" />`);
  pieces.push(`<text x="${(x0p + x6p) / 2}" y="${(y0p + y5p) / 2}" font="bold 12px system-ui" font-size="12" font-weight="700" fill="${ACCENT}" text-anchor="middle">area = 5 × 6 = 30 m</text>`);
  pieces.push(`<text x="${W / 2}" y="${H - 8}" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">flat horizontal line — speed is constant; rectangular area under the line = total distance travelled</text>`);
  return svgWrap(W, H, "Speed vs time — uniform motion", "A flat horizontal line at v = 5 m/s on a speed-vs-time plot from t = 0 to t = 6 s, with shaded rectangular area showing total distance = 30 m.", pieces.join(""));
}

// ────────────────────────────────────────────────────────────────────────────
// SECTION 3 — Accelerated Motion (4 SVGs)
// ────────────────────────────────────────────────────────────────────────────

function s3_motionStripAccelerated() {
  const W = 480, H = 200;
  const stripY = 110;
  const x0 = 40, x1 = 440;
  const N = 7;
  let body = `
  <text x="${W / 2}" y="22" font="bold 14px system-ui" font-size="14" font-weight="700" fill="${INK}" text-anchor="middle">Motion Strip — Accelerated Motion</text>
  <text x="${W / 2}" y="40" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">Strobe snapshots every 1 second — gaps grow each second because speed is increasing.</text>

  <line x1="${x0}" y1="${stripY}" x2="${x1}" y2="${stripY}" stroke="${MUTED}" stroke-width="1.5" stroke-dasharray="4 4" />
`;
  // Positions follow x = 0.5 * t^2 (uniform acceleration), then mapped onto [x0, x1].
  const xMax = 0.5 * (N - 1) * (N - 1);
  for (let i = 0; i < N; i++) {
    const xphys = 0.5 * i * i;
    const px = x0 + (xphys / xMax) * (x1 - x0);
    body += `
  <circle cx="${px}" cy="${stripY}" r="9" fill="${NEGATIVE}" stroke="${INK}" stroke-width="1.5" />
  <text x="${px}" y="${stripY + 30}" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">t = ${i} s</text>`;
  }
  // Spacing markers showing gap growth
  for (let i = 0; i < N - 1; i++) {
    const aPhys = 0.5 * i * i;
    const bPhys = 0.5 * (i + 1) * (i + 1);
    const a = x0 + (aPhys / xMax) * (x1 - x0);
    const b = x0 + (bPhys / xMax) * (x1 - x0);
    body += `
  <line x1="${a + 10}" y1="${stripY - 25}" x2="${b - 10}" y2="${stripY - 25}" stroke="${NEGATIVE}" stroke-width="1.5" />
  <line x1="${a + 10}" y1="${stripY - 30}" x2="${a + 10}" y2="${stripY - 20}" stroke="${NEGATIVE}" stroke-width="1.5" />
  <line x1="${b - 10}" y1="${stripY - 30}" x2="${b - 10}" y2="${stripY - 20}" stroke="${NEGATIVE}" stroke-width="1.5" />`;
  }
  body += `
  <text x="${W / 2}" y="${stripY - 38}" font="bold 12px system-ui" font-size="12" font-weight="700" fill="${NEGATIVE}" text-anchor="middle">gaps grow every second — speed is increasing → accelerated motion</text>
`;
  return svgWrap(W, H, "Motion strip — accelerated motion", "Seven dots along a horizontal axis with progressively-increasing spacing, one per second from t = 0 to t = 6 s, showing the visual signature of uniformly-accelerated motion (gap growth ratio 1:3:5:7:9:11).", body);
}

function s3_xtAccelerated() {
  const W = 480, H = 280;
  const cfg: PlotConfig = {
    width: W, height: H,
    pad: { l: 56, r: 24, t: 36, b: 50 },
    xRange: [0, 6], yRange: [0, 36],
    xTicks: [0, 1, 2, 3, 4, 5, 6],
    yTicks: [0, 6, 12, 18, 24, 30, 36],
    xLabel: "time t (seconds)",
    yLabel: "distance d (metres)",
    title: "Distance vs Time — Accelerated Motion",
  };
  const { pieces, xToPx, yToPx } = makePlot(cfg);
  // d = t^2 (uniform acceleration starting from rest)
  pieces.push(plotPolyline((t) => t * t, [0, 6], xToPx, yToPx, { color: ACCENT, width: 3.5 }));
  // Annotate steepness change
  const xa = xToPx(1), ya = yToPx(1);
  const xb = xToPx(5), yb = yToPx(25);
  pieces.push(`<circle cx="${xa}" cy="${ya}" r="5" fill="${ACCENT_2}" stroke="${INK}" stroke-width="1" />`);
  pieces.push(`<circle cx="${xb}" cy="${yb}" r="5" fill="${ACCENT_2}" stroke="${INK}" stroke-width="1" />`);
  pieces.push(`<text x="${xa + 6}" y="${ya - 6}" font="11px system-ui" font-size="11" fill="${ACCENT_2}">slope here is small (slow)</text>`);
  pieces.push(`<text x="${xb - 6}" y="${yb + 18}" font="11px system-ui" font-size="11" fill="${ACCENT_2}" text-anchor="end">slope here is large (fast)</text>`);
  pieces.push(`<text x="${W / 2}" y="${H - 8}" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">curve gets steeper — slope grows over time, meaning the speed is increasing</text>`);
  return svgWrap(W, H, "Distance vs time — accelerated motion", "An upward-curving parabola d = t² on a distance-vs-time plot, with two annotated points showing that the curve's slope (= speed) is small early and large later.", pieces.join(""));
}

function s3_vtAccelerated() {
  const W = 480, H = 280;
  const cfg: PlotConfig = {
    width: W, height: H,
    pad: { l: 56, r: 24, t: 36, b: 50 },
    xRange: [0, 6], yRange: [0, 12],
    xTicks: [0, 1, 2, 3, 4, 5, 6],
    yTicks: [0, 2, 4, 6, 8, 10, 12],
    xLabel: "time t (seconds)",
    yLabel: "speed v (m/s)",
    title: "Speed vs Time — Uniform Acceleration",
  };
  const { pieces, xToPx, yToPx } = makePlot(cfg);
  // v = 2t (uniform acceleration of 2 m/s²)
  pieces.push(plotPolyline((t) => 2 * t, [0, 6], xToPx, yToPx, { color: ACCENT, width: 3.5 }));
  // Slope-triangle for acceleration
  const xa = xToPx(2), ya = yToPx(4);
  const xb = xToPx(5), yb = yToPx(10);
  pieces.push(`<line x1="${xa}" y1="${ya}" x2="${xb}" y2="${ya}" stroke="${ACCENT_2}" stroke-width="1.5" stroke-dasharray="4 3" />`);
  pieces.push(`<line x1="${xb}" y1="${ya}" x2="${xb}" y2="${yb}" stroke="${ACCENT_2}" stroke-width="1.5" stroke-dasharray="4 3" />`);
  pieces.push(`<text x="${(xa + xb) / 2}" y="${ya - 6}" font="11px system-ui" font-size="11" fill="${ACCENT_2}" text-anchor="middle">Δt = 3 s</text>`);
  pieces.push(`<text x="${xb + 4}" y="${(ya + yb) / 2}" font="11px system-ui" font-size="11" fill="${ACCENT_2}" text-anchor="start">Δv = 6 m/s</text>`);
  pieces.push(`<text x="${W / 2}" y="${H - 8}" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">straight line climbing through origin — slope = acceleration = 6 m/s ÷ 3 s = 2 m/s²</text>`);
  return svgWrap(W, H, "Speed vs time — uniform acceleration", "A straight diagonal line from origin with slope 2 on a speed-vs-time plot, with a slope-triangle showing Δv = 6 m/s over Δt = 3 s, identifying acceleration of 2 m/s².", pieces.join(""));
}

function s3_uniformVsAccelerated() {
  // Side-by-side x-t and v-t comparison.
  const W = 720, H = 280;
  const halfW = 360;
  const cfgL: PlotConfig = {
    width: halfW, height: H,
    pad: { l: 50, r: 14, t: 36, b: 50 },
    xRange: [0, 6], yRange: [0, 30],
    xTicks: [0, 2, 4, 6], yTicks: [0, 10, 20, 30],
    xLabel: "time t (s)", yLabel: "distance d (m)",
    title: "d vs t — uniform vs accelerated",
  };
  const cfgR: PlotConfig = {
    width: halfW, height: H,
    pad: { l: 50, r: 14, t: 36, b: 50 },
    xRange: [0, 6], yRange: [0, 12],
    xTicks: [0, 2, 4, 6], yTicks: [0, 4, 8, 12],
    xLabel: "time t (s)", yLabel: "speed v (m/s)",
    title: "v vs t — uniform vs accelerated",
  };
  const { pieces: pL, xToPx: xL, yToPx: yL } = makePlot(cfgL);
  // Uniform: d = 5t (blue), Accelerated: d = t^2 (orange)
  pL.push(plotPolyline((t) => 5 * t, [0, 6], xL, yL, { color: ACCENT, width: 3 }));
  pL.push(plotPolyline((t) => t * t, [0, 6], xL, yL, { color: ACCENT_2, width: 3 }));
  pL.push(`<text x="${xL(3.6)}" y="${yL(20)}" font="11px system-ui" font-size="11" font-weight="700" fill="${ACCENT}">uniform (straight)</text>`);
  pL.push(`<text x="${xL(2.2)}" y="${yL(8.5)}" font="11px system-ui" font-size="11" font-weight="700" fill="${ACCENT_2}">accelerated (curve)</text>`);
  // Right plot offset by halfW
  const offsetGroup = (g: string[]) => g.map((s) => s).join("");
  const { pieces: pR, xToPx: xR, yToPx: yR } = makePlot(cfgR);
  pR.push(plotPolyline(() => 5, [0, 6], xR, yR, { color: ACCENT, width: 3 }));
  pR.push(plotPolyline((t) => 2 * t, [0, 6], xR, yR, { color: ACCENT_2, width: 3 }));
  pR.push(`<text x="${xR(3.5)}" y="${yR(5) - 6}" font="11px system-ui" font-size="11" font-weight="700" fill="${ACCENT}">uniform (flat)</text>`);
  pR.push(`<text x="${xR(0.4)}" y="${yR(3)}" font="11px system-ui" font-size="11" font-weight="700" fill="${ACCENT_2}">accelerated (rising)</text>`);
  const body = `
  ${offsetGroup(pL)}
  <g transform="translate(${halfW}, 0)">${offsetGroup(pR)}</g>
`;
  return svgWrap(W, H, "Uniform vs accelerated motion comparison", "Side-by-side comparison: left plot shows distance-vs-time as a straight line for uniform motion and a parabola for accelerated motion; right plot shows speed-vs-time as a flat line for uniform and a rising line for accelerated.", body);
}

// ────────────────────────────────────────────────────────────────────────────
// Main
// ────────────────────────────────────────────────────────────────────────────

mkdirSync(ROOT, { recursive: true });

write("section-1-fundamentals/1d-position-and-displacement.svg", s1_1dPosition());
write("section-1-fundamentals/distance-vs-displacement.svg", s1_distanceVsDisplacement());
write("section-1-fundamentals/average-vs-instantaneous-speed.svg", s1_avgVsInstantaneousSpeed());

write("section-2-uniform-motion/motion-strip-uniform.svg", s2_motionStripUniform());
write("section-2-uniform-motion/xt-uniform.svg", s2_xtUniform());
write("section-2-uniform-motion/vt-uniform.svg", s2_vtUniform());

write("section-3-accelerated-motion/motion-strip-accelerated.svg", s3_motionStripAccelerated());
write("section-3-accelerated-motion/xt-accelerated.svg", s3_xtAccelerated());
write("section-3-accelerated-motion/vt-accelerated.svg", s3_vtAccelerated());
write("section-3-accelerated-motion/uniform-vs-accelerated-comparison.svg", s3_uniformVsAccelerated());

console.log("done — 10 SVGs");
