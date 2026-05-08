#!/usr/bin/env bun
/**
 * Generate the Option-2 SVG catalogue for G11-PHYS-002 Kinematics.
 *
 * Run from repo root:
 *   bun scripts/generate_kinematics_visuals.ts
 *
 * Output: sample_content/g11-science/G11-PHYS-002_Kinematics/Option2_Catalogue/section-N/*.svg
 *
 * Convention follows the Sets-and-Functions catalogue: standalone SVGs,
 * inline styles, viewBox-based sizing, no external font dependencies.
 */

import { writeFileSync, mkdirSync } from "node:fs";
import { join, dirname } from "node:path";

// Style tokens + makePlot lifted to pipeline/visual_templates/shared.ts.
// This generator uses the variant-B preset for makePlot (#341 phase B).
// plotPolyline kept local — script-specific signature (fn + xRange instead
// of pre-computed points).
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
  makePlot as makePlotShared,
  VARIANT_B,
  type PlotConfig,
} from "../pipeline/visual_templates/shared.ts";

const makePlot = (c: PlotConfig) => makePlotShared(c, VARIANT_B);

const ROOT = join(
  import.meta.dir,
  "..",
  "sample_content",
  "g11-science",
  "G11-PHYS-002_Kinematics",
  "Option2_Catalogue",
);

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

function s1_distanceVsDisplacement() {
  // Path from A to B that loops, with straight displacement vector
  const W = 480, H = 280;
  const body = `
  <defs>
    <marker id="arrow-displacement" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="9" markerHeight="9" orient="auto">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="${ACCENT}" />
    </marker>
  </defs>

  <text x="${W / 2}" y="22" font="bold 14px system-ui" font-size="14" font-weight="700" fill="${INK}" text-anchor="middle">Distance vs. Displacement</text>

  <!-- Curved path from A to B -->
  <path d="M 80 200 Q 160 60, 260 130 T 400 80"
        fill="none" stroke="${ACCENT_2}" stroke-width="3.5" />
  <!-- Direction arrows along path -->
  <path d="M 200 100 L 215 110 L 200 120" fill="none" stroke="${ACCENT_2}" stroke-width="2" />

  <!-- Straight displacement vector (A → B) -->
  <line x1="80" y1="200" x2="400" y2="80"
        stroke="${ACCENT}" stroke-width="3"
        stroke-dasharray="6 4"
        marker-end="url(#arrow-displacement)" />

  <!-- Endpoint dots -->
  <circle cx="80" cy="200" r="6" fill="${INK}" />
  <text x="68" y="220" font="14px system-ui" font-size="14" font-weight="700" fill="${INK}">A</text>
  <circle cx="400" cy="80" r="6" fill="${INK}" />
  <text x="408" y="78" font="14px system-ui" font-size="14" font-weight="700" fill="${INK}">B</text>

  <!-- Legend -->
  <g transform="translate(80, 240)">
    <line x1="0" y1="0" x2="40" y2="0" stroke="${ACCENT_2}" stroke-width="3.5" />
    <text x="50" y="4" font="12px system-ui" font-size="12" fill="${INK}">Distance: total path length (scalar)</text>
  </g>
  <g transform="translate(80, 260)">
    <line x1="0" y1="0" x2="40" y2="0" stroke="${ACCENT}" stroke-width="3" stroke-dasharray="6 4" />
    <text x="50" y="4" font="12px system-ui" font-size="12" fill="${INK}">Displacement: A → B (vector)</text>
  </g>
`;
  write("section-1-fundamentals/distance-vs-displacement.svg",
    svgWrap(W, H, "Distance vs Displacement",
      "A curved path from A to B with the straight-line displacement vector overlaid showing the difference.",
      body));
}

function s1_avgVsInstantaneous() {
  // x-t curve with secant (average velocity) and tangent (instantaneous velocity) shown
  const c: PlotConfig = {
    width: 480, height: 320,
    pad: { l: 60, r: 30, t: 32, b: 50 },
    xRange: [0, 5], yRange: [0, 25],
    xTicks: [0, 1, 2, 3, 4, 5],
    yTicks: [0, 5, 10, 15, 20, 25],
    xLabel: "t (s)", yLabel: "x (m)",
    title: "Average vs Instantaneous Velocity",
  };
  const { pieces, xToPx, yToPx } = makePlot(c);
  // Curve: x(t) = t^2
  pieces.push(plotPolyline((t) => t * t, [0, 5], xToPx, yToPx, { color: ACCENT, width: 3.5 }));
  // Secant from (1,1) to (4,16) — average velocity
  pieces.push(`<line x1="${xToPx(1)}" y1="${yToPx(1)}" x2="${xToPx(4)}" y2="${yToPx(16)}" stroke="${ACCENT_2}" stroke-width="2.5" stroke-dasharray="6 4" />`);
  // Tangent at t=3 (slope = 6, so y - 9 = 6(t - 3) → y = 6t - 9; at t=2: y=3, at t=4: y=15)
  pieces.push(`<line x1="${xToPx(2)}" y1="${yToPx(3)}" x2="${xToPx(4)}" y2="${yToPx(15)}" stroke="${POSITIVE}" stroke-width="2.5" />`);
  // Markers
  pieces.push(`<circle cx="${xToPx(1)}" cy="${yToPx(1)}" r="5" fill="${ACCENT_2}" />`);
  pieces.push(`<circle cx="${xToPx(4)}" cy="${yToPx(16)}" r="5" fill="${ACCENT_2}" />`);
  pieces.push(`<circle cx="${xToPx(3)}" cy="${yToPx(9)}" r="5" fill="${POSITIVE}" />`);
  // Labels
  pieces.push(`<text x="${xToPx(1.5)}" y="${yToPx(7)}" font="11px system-ui" font-size="11" fill="${ACCENT_2}" font-weight="600">secant — avg velocity</text>`);
  pieces.push(`<text x="${xToPx(2.2)}" y="${yToPx(15)}" font="11px system-ui" font-size="11" fill="${POSITIVE}" font-weight="600">tangent — instant velocity</text>`);

  write("section-1-fundamentals/average-vs-instantaneous-velocity.svg",
    svgWrap(c.width, c.height, "Average vs Instantaneous Velocity",
      "Position-time curve showing a secant line for average velocity over an interval and a tangent line for instantaneous velocity at a single point.",
      pieces.join("\n")));
}

function s1_1dPosition() {
  const W = 520, H = 200;
  const y = 100;
  const body = `
  <text x="${W / 2}" y="22" font="bold 14px system-ui" font-size="14" font-weight="700" fill="${INK}" text-anchor="middle">1-D Motion: Position and Displacement</text>

  <!-- Number line -->
  <line x1="40" y1="${y}" x2="${W - 40}" y2="${y}" stroke="${INK}" stroke-width="1.5" />
  <!-- Tick marks -->
  ${Array.from({ length: 11 }, (_, i) => {
    const x = 40 + (i * (W - 80)) / 10;
    return `<line x1="${x}" y1="${y - 6}" x2="${x}" y2="${y + 6}" stroke="${INK}" stroke-width="1" /><text x="${x}" y="${y + 24}" font="10px system-ui" font-size="10" fill="${MUTED}" text-anchor="middle">${i - 2}</text>`;
  }).join("\n  ")}

  <!-- Origin marker -->
  <circle cx="${40 + 2 * ((W - 80) / 10)}" cy="${y}" r="4" fill="${INK}" />
  <text x="${40 + 2 * ((W - 80) / 10)}" y="${y - 16}" font="11px system-ui" font-size="11" font-weight="700" fill="${INK}" text-anchor="middle">O (origin)</text>

  <!-- x_i and x_f markers -->
  <circle cx="${40 + 3 * ((W - 80) / 10)}" cy="${y}" r="6" fill="${ACCENT}" />
  <text x="${40 + 3 * ((W - 80) / 10)}" y="${y - 18}" font="12px system-ui" font-size="12" font-weight="700" fill="${ACCENT}" text-anchor="middle">x_i = 1</text>

  <circle cx="${40 + 7 * ((W - 80) / 10)}" cy="${y}" r="6" fill="${ACCENT_2}" />
  <text x="${40 + 7 * ((W - 80) / 10)}" y="${y - 18}" font="12px system-ui" font-size="12" font-weight="700" fill="${ACCENT_2}" text-anchor="middle">x_f = 5</text>

  <!-- Displacement arrow below -->
  <defs>
    <marker id="arrow-disp1d" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="9" markerHeight="9" orient="auto">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="${POSITIVE}" />
    </marker>
  </defs>
  <line x1="${40 + 3 * ((W - 80) / 10) + 6}" y1="${y + 50}" x2="${40 + 7 * ((W - 80) / 10) - 6}" y2="${y + 50}" stroke="${POSITIVE}" stroke-width="3" marker-end="url(#arrow-disp1d)" />
  <text x="${W / 2}" y="${y + 75}" font="13px system-ui" font-size="13" font-weight="600" fill="${POSITIVE}" text-anchor="middle">Δx = x_f − x_i = +4 m</text>

  <text x="${W / 2}" y="${H - 10}" font="11px system-ui" font-size="11" font-style="italic" fill="${MUTED}" text-anchor="middle">Position is location relative to origin; displacement is the change in position.</text>
`;
  write("section-1-fundamentals/1d-position-and-displacement.svg",
    svgWrap(W, H, "1-D Position and Displacement",
      "A number line with origin marked, initial and final positions, and a green arrow showing the +4 m displacement.",
      body));
}

// ────────────────────────────────────────────────────────────────────────────
// SECTION 2 — UAM (3 SVGs)
// ────────────────────────────────────────────────────────────────────────────

function s2_xtUAM() {
  const c: PlotConfig = {
    width: 460, height: 320,
    pad: { l: 60, r: 30, t: 32, b: 50 },
    xRange: [0, 5], yRange: [0, 35],
    xTicks: [0, 1, 2, 3, 4, 5],
    yTicks: [0, 10, 20, 30],
    xLabel: "t (s)", yLabel: "x (m)",
    title: "Position–Time:  x = vᵢt + ½at²  (UAM)",
  };
  const { pieces, xToPx, yToPx } = makePlot(c);
  // x = 2t + 0.5*2*t^2 = 2t + t^2 → vi=2, a=2
  pieces.push(plotPolyline((t) => 2 * t + t * t, [0, 5], xToPx, yToPx, { color: ACCENT, width: 3.5 }));
  // Annotation
  pieces.push(`<text x="${xToPx(3.2)}" y="${yToPx(28)}" font="11px system-ui" font-size="11" fill="${ACCENT}" font-weight="600">vᵢ = 2 m/s,  a = 2 m/s²</text>`);
  pieces.push(`<text x="${xToPx(0.4)}" y="${yToPx(31)}" font="11px system-ui" font-size="11" fill="${MUTED}" font-style="italic">parabolic — concave up because a &gt; 0</text>`);

  write("section-2-uam/xt-uam.svg",
    svgWrap(c.width, c.height, "Position-Time graph for UAM",
      "Parabolic position-time curve showing uniformly accelerated motion with positive acceleration.",
      pieces.join("\n")));
}

function s2_vtUAM() {
  const c: PlotConfig = {
    width: 460, height: 320,
    pad: { l: 60, r: 30, t: 32, b: 50 },
    xRange: [0, 5], yRange: [0, 14],
    xTicks: [0, 1, 2, 3, 4, 5],
    yTicks: [0, 2, 4, 6, 8, 10, 12],
    xLabel: "t (s)", yLabel: "v (m/s)",
    title: "Velocity–Time:  v = vᵢ + at  (UAM)",
  };
  const { pieces, xToPx, yToPx } = makePlot(c);
  // v = 2 + 2t
  pieces.push(plotPolyline((t) => 2 + 2 * t, [0, 5], xToPx, yToPx, { color: ACCENT_2, width: 3.5 }));
  // Shaded area under curve from 0 to 4 = displacement
  const shadePts = [`${xToPx(0)},${yToPx(0)}`];
  for (let i = 0; i <= 40; i++) {
    const t = i / 10;
    shadePts.push(`${xToPx(t)},${yToPx(2 + 2 * t)}`);
  }
  shadePts.push(`${xToPx(4)},${yToPx(0)}`);
  pieces.push(`<polygon points="${shadePts.join(" ")}" fill="${ACCENT_2}" fill-opacity="0.15" />`);
  pieces.push(`<text x="${xToPx(2)}" y="${yToPx(4)}" font="11px system-ui" font-size="11" fill="${ACCENT_2}" font-weight="600" text-anchor="middle">area = Δx</text>`);
  pieces.push(`<text x="${xToPx(2.8)}" y="${yToPx(12)}" font="11px system-ui" font-size="11" fill="${ACCENT_2}" font-weight="600">slope = a = 2 m/s²</text>`);

  write("section-2-uam/vt-uam.svg",
    svgWrap(c.width, c.height, "Velocity-Time graph for UAM",
      "Linear velocity-time curve for uniformly accelerated motion with the area under the line shaded as displacement.",
      pieces.join("\n")));
}

function s2_atUAM() {
  const c: PlotConfig = {
    width: 460, height: 320,
    pad: { l: 60, r: 30, t: 32, b: 50 },
    xRange: [0, 5], yRange: [0, 4],
    xTicks: [0, 1, 2, 3, 4, 5],
    yTicks: [0, 1, 2, 3],
    xLabel: "t (s)", yLabel: "a (m/s²)",
    title: "Acceleration–Time:  a = constant  (UAM)",
  };
  const { pieces, xToPx, yToPx } = makePlot(c);
  pieces.push(`<line x1="${xToPx(0)}" y1="${yToPx(2)}" x2="${xToPx(5)}" y2="${yToPx(2)}" stroke="${ACCENT_3}" stroke-width="3.5" />`);
  pieces.push(`<text x="${xToPx(2.5)}" y="${yToPx(2) - 12}" font="11px system-ui" font-size="11" fill="${ACCENT_3}" font-weight="600" text-anchor="middle">a = 2 m/s² (constant)</text>`);

  write("section-2-uam/at-uam.svg",
    svgWrap(c.width, c.height, "Acceleration-Time graph for UAM",
      "Horizontal line at a = 2 m/s² showing constant acceleration during uniformly accelerated motion.",
      pieces.join("\n")));
}

// ────────────────────────────────────────────────────────────────────────────
// SECTION 3 — Free Fall (2 SVGs)
// ────────────────────────────────────────────────────────────────────────────

function s3_heightVsTime() {
  // Object thrown up at vi = 20 m/s; h(t) = 20t - 4.9t^2; peak at t=20/9.8≈2.04s, h≈20.4
  const c: PlotConfig = {
    width: 460, height: 320,
    pad: { l: 60, r: 30, t: 32, b: 50 },
    xRange: [0, 4.5], yRange: [0, 22],
    xTicks: [0, 1, 2, 3, 4],
    yTicks: [0, 5, 10, 15, 20],
    xLabel: "t (s)", yLabel: "h (m)",
    title: "Height–Time:  Object Thrown Up (vᵢ = 20 m/s)",
  };
  const { pieces, xToPx, yToPx } = makePlot(c);
  // h(t) = 20t - 4.9t^2; impact when h=0 → t = 20/4.9 ≈ 4.08
  const impact = 20 / 4.9;
  pieces.push(plotPolyline((t) => 20 * t - 4.9 * t * t, [0, impact], xToPx, yToPx, { color: ACCENT, width: 3.5 }));
  // Peak marker
  const tPeak = 20 / 9.8;
  const hPeak = 20 * tPeak - 4.9 * tPeak * tPeak;
  pieces.push(`<line x1="${xToPx(tPeak)}" y1="${yToPx(0)}" x2="${xToPx(tPeak)}" y2="${yToPx(hPeak)}" stroke="${MUTED}" stroke-width="1.2" stroke-dasharray="4 4" />`);
  pieces.push(`<circle cx="${xToPx(tPeak)}" cy="${yToPx(hPeak)}" r="5" fill="${POSITIVE}" />`);
  pieces.push(`<text x="${xToPx(tPeak) + 8}" y="${yToPx(hPeak) - 8}" font="11px system-ui" font-size="11" fill="${POSITIVE}" font-weight="600">peak: t ≈ 2.04 s, h ≈ 20.4 m</text>`);
  pieces.push(`<circle cx="${xToPx(impact)}" cy="${yToPx(0)}" r="5" fill="${NEGATIVE}" />`);
  pieces.push(`<text x="${xToPx(impact) - 5}" y="${yToPx(0) - 8}" font="11px system-ui" font-size="11" fill="${NEGATIVE}" font-weight="600" text-anchor="end">impact: t ≈ 4.08 s</text>`);

  write("section-3-freefall/height-vs-time.svg",
    svgWrap(c.width, c.height, "Height-Time for thrown-up projectile",
      "Parabolic h(t) curve for an object thrown straight up at 20 m/s, with peak and impact points marked.",
      pieces.join("\n")));
}

function s3_velocityVsTime() {
  const c: PlotConfig = {
    width: 460, height: 320,
    pad: { l: 60, r: 30, t: 32, b: 50 },
    xRange: [0, 4.5], yRange: [-22, 22],
    xTicks: [0, 1, 2, 3, 4],
    yTicks: [-20, -10, 0, 10, 20],
    xLabel: "t (s)", yLabel: "v (m/s)",
    title: "Velocity–Time:  Object Thrown Up (vᵢ = 20 m/s)",
  };
  const { pieces, xToPx, yToPx } = makePlot(c);
  // v(t) = 20 - 9.8t; zero at t = 20/9.8 ≈ 2.04
  const impact = 20 / 4.9;
  pieces.push(plotPolyline((t) => 20 - 9.8 * t, [0, impact], xToPx, yToPx, { color: ACCENT_2, width: 3.5 }));
  // Zero crossing marker
  const tPeak = 20 / 9.8;
  pieces.push(`<circle cx="${xToPx(tPeak)}" cy="${yToPx(0)}" r="5" fill="${POSITIVE}" />`);
  pieces.push(`<text x="${xToPx(tPeak) + 8}" y="${yToPx(0) - 6}" font="11px system-ui" font-size="11" fill="${POSITIVE}" font-weight="600">v = 0 at peak</text>`);
  pieces.push(`<text x="${xToPx(0.6)}" y="${yToPx(15)}" font="11px system-ui" font-size="11" fill="${ACCENT_2}" font-weight="600">slope = a = −g = −9.8 m/s²</text>`);
  pieces.push(`<text x="${xToPx(2.5)}" y="${yToPx(-18)}" font="11px system-ui" font-size="11" fill="${ACCENT_2}" font-weight="600">moving down ↓</text>`);
  pieces.push(`<text x="${xToPx(0.6)}" y="${yToPx(-18)}" font="11px system-ui" font-size="11" fill="${ACCENT_2}" font-weight="600">moving up ↑</text>`);

  write("section-3-freefall/velocity-vs-time.svg",
    svgWrap(c.width, c.height, "Velocity-Time for thrown-up projectile",
      "Linear v(t) crossing zero at the peak. Sign change shows direction reversal.",
      pieces.join("\n")));
}

// ────────────────────────────────────────────────────────────────────────────
// SECTION 4 — Projectile Motion (3 SVGs)
// ────────────────────────────────────────────────────────────────────────────

function s4_trajectory() {
  // Projectile launched at v=20 m/s, theta=60°
  // vix = 10, viy = 17.32; T = 2*viy/g ≈ 3.53s; xMax = vix*T ≈ 35.3m; yMax = viy²/(2g) ≈ 15.3m
  const v = 20, theta = 60 * Math.PI / 180;
  const vix = v * Math.cos(theta);
  const viy = v * Math.sin(theta);
  const g = 9.8;
  const T = 2 * viy / g;
  const xMax = vix * T;
  const yMax = (viy * viy) / (2 * g);

  const c: PlotConfig = {
    width: 480, height: 320,
    pad: { l: 60, r: 30, t: 32, b: 50 },
    xRange: [0, 40], yRange: [0, 20],
    xTicks: [0, 10, 20, 30, 40],
    yTicks: [0, 5, 10, 15, 20],
    xLabel: "x (m)", yLabel: "y (m)",
    title: "Projectile Trajectory  (v = 20 m/s, θ = 60°)",
  };
  const { pieces, xToPx, yToPx } = makePlot(c);
  // y(x) = (tan θ)x - (g / (2 v² cos² θ)) x²
  const fn = (x: number) => Math.tan(theta) * x - (g * x * x) / (2 * v * v * Math.cos(theta) * Math.cos(theta));
  pieces.push(plotPolyline(fn, [0, xMax], xToPx, yToPx, { color: ACCENT, width: 3.5 }));
  // Peak
  pieces.push(`<line x1="${xToPx(xMax / 2)}" y1="${yToPx(0)}" x2="${xToPx(xMax / 2)}" y2="${yToPx(yMax)}" stroke="${MUTED}" stroke-width="1.2" stroke-dasharray="4 4" />`);
  pieces.push(`<circle cx="${xToPx(xMax / 2)}" cy="${yToPx(yMax)}" r="5" fill="${POSITIVE}" />`);
  pieces.push(`<text x="${xToPx(xMax / 2) + 8}" y="${yToPx(yMax) - 8}" font="11px system-ui" font-size="11" fill="${POSITIVE}" font-weight="600">max height ≈ 15.3 m</text>`);
  // Range
  pieces.push(`<line x1="${xToPx(0)}" y1="${yToPx(0) + 14}" x2="${xToPx(xMax)}" y2="${yToPx(0) + 14}" stroke="${ACCENT_2}" stroke-width="2" />`);
  pieces.push(`<text x="${xToPx(xMax / 2)}" y="${yToPx(0) + 30}" font="11px system-ui" font-size="11" fill="${ACCENT_2}" font-weight="600" text-anchor="middle">range ≈ 35.3 m</text>`);

  write("section-4-projectile/trajectory.svg",
    svgWrap(c.width, c.height, "Projectile Trajectory",
      "Parabolic flight path of a projectile at 20 m/s and 60°, with peak height and range marked.",
      pieces.join("\n")));
}

function s4_velocityDecomposition() {
  const W = 480, H = 320;
  const cx = 90, cy = 240;
  const v = 20, theta = 60 * Math.PI / 180;
  const len = 180;
  const vx = len * Math.cos(theta);
  const vy = len * Math.sin(theta);
  const body = `
  <defs>
    <marker id="ah-vec" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="9" markerHeight="9" orient="auto">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="${ACCENT}" />
    </marker>
    <marker id="ah-vx" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="9" markerHeight="9" orient="auto">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="${ACCENT_2}" />
    </marker>
    <marker id="ah-vy" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="9" markerHeight="9" orient="auto">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="${ACCENT_3}" />
    </marker>
  </defs>

  <text x="${W / 2}" y="22" font="bold 14px system-ui" font-size="14" font-weight="700" fill="${INK}" text-anchor="middle">Initial Velocity Decomposition</text>

  <!-- Ground -->
  <line x1="60" y1="${cy}" x2="${W - 30}" y2="${cy}" stroke="${INK}" stroke-width="1.5" />

  <!-- Projectile dot -->
  <circle cx="${cx}" cy="${cy}" r="6" fill="${INK}" />

  <!-- Total velocity arrow -->
  <line x1="${cx}" y1="${cy}" x2="${cx + vx}" y2="${cy - vy}" stroke="${ACCENT}" stroke-width="3.5" marker-end="url(#ah-vec)" />
  <text x="${cx + vx / 2 - 4}" y="${cy - vy / 2 - 14}" font="13px system-ui" font-size="13" font-weight="700" fill="${ACCENT}">v = 20 m/s</text>
  <text x="${cx + 30}" y="${cy - 10}" font="12px system-ui" font-size="12" fill="${ACCENT}" font-style="italic">θ = 60°</text>

  <!-- Horizontal component -->
  <line x1="${cx}" y1="${cy + 30}" x2="${cx + vx}" y2="${cy + 30}" stroke="${ACCENT_2}" stroke-width="3" marker-end="url(#ah-vx)" />
  <text x="${cx + vx / 2}" y="${cy + 50}" font="12px system-ui" font-size="12" font-weight="600" fill="${ACCENT_2}" text-anchor="middle">vₓ = v cos θ ≈ 10 m/s</text>

  <!-- Vertical component (drawn as separate ghost arrow to the right) -->
  <line x1="${cx + vx + 50}" y1="${cy}" x2="${cx + vx + 50}" y2="${cy - vy}" stroke="${ACCENT_3}" stroke-width="3" marker-end="url(#ah-vy)" />
  <text x="${cx + vx + 60}" y="${cy - vy / 2}" font="12px system-ui" font-size="12" font-weight="600" fill="${ACCENT_3}">v_y = v sin θ</text>
  <text x="${cx + vx + 60}" y="${cy - vy / 2 + 14}" font="12px system-ui" font-size="12" font-weight="600" fill="${ACCENT_3}">≈ 17.3 m/s</text>

  <!-- Right-angle marker -->
  <path d="M ${cx} ${cy + 18} L ${cx + 12} ${cy + 18} L ${cx + 12} ${cy + 30}" fill="none" stroke="${ACCENT_2}" stroke-width="1" />

  <text x="${W / 2}" y="${H - 12}" font="11px system-ui" font-size="11" font-style="italic" fill="${MUTED}" text-anchor="middle">Independent horizontal and vertical motions combine to produce the parabolic trajectory.</text>
`;
  write("section-4-projectile/velocity-decomposition.svg",
    svgWrap(W, H, "Velocity Decomposition into Horizontal and Vertical Components",
      "An initial velocity vector at 60° decomposed into its horizontal and vertical components.",
      body));
}

function s4_keyResults() {
  const W = 520, H = 320;
  const body = `
  <text x="${W / 2}" y="24" font="bold 14px system-ui" font-size="14" font-weight="700" fill="${INK}" text-anchor="middle">Key Results — Projectile Motion (level launch &amp; landing)</text>

  <!-- Three panels -->
  <g transform="translate(20, 60)">
    <rect x="0" y="0" width="155" height="220" rx="8" fill="${BG}" stroke="${GRID}" />
    <text x="77" y="26" font="bold 13px system-ui" font-size="13" font-weight="700" fill="${ACCENT}" text-anchor="middle">Time of flight</text>
    <text x="77" y="80" font="14px system-ui" font-size="14" font-weight="700" fill="${INK}" text-anchor="middle">T = 2 vᵢ sin θ / g</text>
    <text x="77" y="120" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">When the projectile</text>
    <text x="77" y="135" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">lands at launch height.</text>
    <text x="77" y="180" font="12px system-ui" font-size="12" fill="${POSITIVE}" font-weight="600" text-anchor="middle">Symmetric:</text>
    <text x="77" y="196" font="11px system-ui" font-size="11" fill="${POSITIVE}" text-anchor="middle">t_up = t_down</text>
  </g>

  <g transform="translate(185, 60)">
    <rect x="0" y="0" width="155" height="220" rx="8" fill="${BG}" stroke="${GRID}" />
    <text x="77" y="26" font="bold 13px system-ui" font-size="13" font-weight="700" fill="${ACCENT_2}" text-anchor="middle">Horizontal range</text>
    <text x="77" y="80" font="14px system-ui" font-size="14" font-weight="700" fill="${INK}" text-anchor="middle">R = vᵢ² sin 2θ / g</text>
    <text x="77" y="120" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">Maximum range</text>
    <text x="77" y="135" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">at θ = 45°.</text>
    <text x="77" y="180" font="12px system-ui" font-size="12" fill="${POSITIVE}" font-weight="600" text-anchor="middle">θ + (90°−θ) give</text>
    <text x="77" y="196" font="11px system-ui" font-size="11" fill="${POSITIVE}" text-anchor="middle">the same range.</text>
  </g>

  <g transform="translate(350, 60)">
    <rect x="0" y="0" width="150" height="220" rx="8" fill="${BG}" stroke="${GRID}" />
    <text x="75" y="26" font="bold 13px system-ui" font-size="13" font-weight="700" fill="${ACCENT_3}" text-anchor="middle">Maximum height</text>
    <text x="75" y="80" font="14px system-ui" font-size="14" font-weight="700" fill="${INK}" text-anchor="middle">y_max = vᵢ² sin² θ / 2g</text>
    <text x="75" y="120" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">At t = vᵢ sin θ / g</text>
    <text x="75" y="135" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">(half the time of flight).</text>
    <text x="75" y="180" font="12px system-ui" font-size="12" fill="${POSITIVE}" font-weight="600" text-anchor="middle">v_y = 0 at peak,</text>
    <text x="75" y="196" font="11px system-ui" font-size="11" fill="${POSITIVE}" text-anchor="middle">v_x is unchanged.</text>
  </g>
`;
  write("section-4-projectile/key-results.svg",
    svgWrap(W, H, "Projectile motion key results",
      "Three result cards summarising time of flight, range, and maximum height for a level-launch projectile.",
      body));
}

// ────────────────────────────────────────────────────────────────────────────
// SECTION 5 — Graphical Analysis (4 SVGs)
// ────────────────────────────────────────────────────────────────────────────

function s5_xtTangent() {
  const c: PlotConfig = {
    width: 460, height: 320,
    pad: { l: 60, r: 30, t: 32, b: 50 },
    xRange: [0, 5], yRange: [0, 25],
    xTicks: [0, 1, 2, 3, 4, 5],
    yTicks: [0, 5, 10, 15, 20, 25],
    xLabel: "t (s)", yLabel: "x (m)",
    title: "Slope of x–t Curve = Velocity",
  };
  const { pieces, xToPx, yToPx } = makePlot(c);
  pieces.push(plotPolyline((t) => t * t, [0, 5], xToPx, yToPx, { color: ACCENT, width: 3.5 }));
  // Tangent at t=2.5: slope=5, x=6.25; line from t=1.5,x=1.25 to t=3.5,x=11.25
  pieces.push(`<line x1="${xToPx(1.5)}" y1="${yToPx(1.25)}" x2="${xToPx(3.5)}" y2="${yToPx(11.25)}" stroke="${POSITIVE}" stroke-width="2.5" />`);
  pieces.push(`<circle cx="${xToPx(2.5)}" cy="${yToPx(6.25)}" r="5" fill="${POSITIVE}" />`);
  pieces.push(`<text x="${xToPx(3.5) + 5}" y="${yToPx(11.25)}" font="11px system-ui" font-size="11" fill="${POSITIVE}" font-weight="600">tangent slope = v(t)</text>`);
  pieces.push(`<text x="${xToPx(2.5)}" y="${yToPx(6.25) + 18}" font="11px system-ui" font-size="11" fill="${POSITIVE}" font-weight="600" text-anchor="middle">v(2.5) = 5 m/s</text>`);

  write("section-5-graphs/xt-with-tangent.svg",
    svgWrap(c.width, c.height, "x-t with tangent showing instantaneous velocity",
      "Position-time curve with a tangent at t=2.5 s; the slope of the tangent is the instantaneous velocity.",
      pieces.join("\n")));
}

function s5_vtArea() {
  const c: PlotConfig = {
    width: 460, height: 320,
    pad: { l: 60, r: 30, t: 32, b: 50 },
    xRange: [0, 5], yRange: [0, 12],
    xTicks: [0, 1, 2, 3, 4, 5],
    yTicks: [0, 2, 4, 6, 8, 10],
    xLabel: "t (s)", yLabel: "v (m/s)",
    title: "Area Under v–t Curve = Displacement",
  };
  const { pieces, xToPx, yToPx } = makePlot(c);
  pieces.push(plotPolyline((t) => 2 + 2 * t, [0, 5], xToPx, yToPx, { color: ACCENT_2, width: 3.5 }));
  // Shade from t=1 to t=4
  const shade = [`${xToPx(1)},${yToPx(0)}`];
  for (let i = 0; i <= 30; i++) {
    const t = 1 + i / 10;
    shade.push(`${xToPx(t)},${yToPx(2 + 2 * t)}`);
  }
  shade.push(`${xToPx(4)},${yToPx(0)}`);
  pieces.push(`<polygon points="${shade.join(" ")}" fill="${POSITIVE}" fill-opacity="0.25" stroke="${POSITIVE}" stroke-width="1.5" />`);
  pieces.push(`<text x="${xToPx(2.5)}" y="${yToPx(5)}" font="12px system-ui" font-size="12" font-weight="700" fill="${POSITIVE}" text-anchor="middle">Δx = area</text>`);
  pieces.push(`<text x="${xToPx(2.5)}" y="${yToPx(5) + 16}" font="11px system-ui" font-size="11" fill="${POSITIVE}" text-anchor="middle">= 21 m  (from t = 1 to 4 s)</text>`);

  write("section-5-graphs/vt-with-area.svg",
    svgWrap(c.width, c.height, "v-t with shaded area showing displacement",
      "Velocity-time curve with the area between t=1 and t=4 shaded to show the corresponding displacement.",
      pieces.join("\n")));
}

function s5_xtVtAtTrio() {
  // Three stacked plots showing UAM relationships
  const W = 760, H = 360;
  const panelW = 220, panelH = 220;
  const tops = [80];
  const lefts = [40, 280, 520];

  const sub = (left: number, title: string, fn: (t: number) => number, yRange: [number, number], yTicks: number[], yLabel: string, color: string) => {
    const c: PlotConfig = {
      width: panelW, height: panelH,
      pad: { l: 38, r: 12, t: 24, b: 38 },
      xRange: [0, 4], yRange: yRange,
      xTicks: [0, 1, 2, 3, 4],
      yTicks: yTicks,
      xLabel: "t (s)", yLabel: yLabel,
    };
    const { pieces, xToPx, yToPx } = makePlot(c);
    pieces.push(plotPolyline(fn, [0, 4], xToPx, yToPx, { color, width: 3 }));
    return `<g transform="translate(${left}, ${tops[0]})"><text x="${panelW / 2}" y="14" font="bold 12px system-ui" font-size="12" font-weight="700" fill="${INK}" text-anchor="middle">${title}</text>${pieces.join("\n")}</g>`;
  };

  const body = `
  <text x="${W / 2}" y="24" font="bold 15px system-ui" font-size="15" font-weight="700" fill="${INK}" text-anchor="middle">x – v – a Relationship for UAM</text>
  <text x="${W / 2}" y="46" font="12px system-ui" font-size="12" font-style="italic" fill="${MUTED}" text-anchor="middle">slope of x→v · slope of v→a · area under v = Δx · area under a = Δv</text>

  ${sub(lefts[0], "x(t)", (t) => 2 * t + t * t, [0, 24], [0, 6, 12, 18, 24], "x (m)", ACCENT)}
  ${sub(lefts[1], "v(t)", (t) => 2 + 2 * t, [0, 12], [0, 4, 8, 12], "v (m/s)", ACCENT_2)}
  ${sub(lefts[2], "a(t)", () => 2, [0, 4], [0, 1, 2, 3], "a (m/s²)", ACCENT_3)}

  <!-- Connecting arrows -->
  <text x="262" y="200" font="14px system-ui" font-size="14" font-weight="700" fill="${MUTED}" text-anchor="middle">→</text>
  <text x="502" y="200" font="14px system-ui" font-size="14" font-weight="700" fill="${MUTED}" text-anchor="middle">→</text>
  <text x="262" y="218" font="10px system-ui" font-size="10" fill="${MUTED}" text-anchor="middle">slope</text>
  <text x="502" y="218" font="10px system-ui" font-size="10" fill="${MUTED}" text-anchor="middle">slope</text>
`;
  write("section-5-graphs/xt-vt-at-trio.svg",
    svgWrap(W, H, "Trio of x-t, v-t, a-t graphs",
      "Three side-by-side plots showing the relationships between position, velocity, and acceleration as functions of time for UAM.",
      body));
}

function s5_slopeAreaSummary() {
  const W = 520, H = 280;
  const body = `
  <text x="${W / 2}" y="24" font="bold 14px system-ui" font-size="14" font-weight="700" fill="${INK}" text-anchor="middle">The Slope ↔ Area Chain</text>

  <!-- Three boxes -->
  <g transform="translate(20, 70)">
    <rect x="0" y="0" width="140" height="140" rx="8" fill="${BG}" stroke="${ACCENT}" stroke-width="2" />
    <text x="70" y="32" font="bold 13px system-ui" font-size="13" font-weight="700" fill="${ACCENT}" text-anchor="middle">x(t)</text>
    <text x="70" y="78" font="11px system-ui" font-size="11" fill="${INK}" text-anchor="middle">position</text>
    <text x="70" y="115" font="10px system-ui" font-size="10" font-style="italic" fill="${MUTED}" text-anchor="middle">measured</text>
  </g>

  <g transform="translate(190, 70)">
    <rect x="0" y="0" width="140" height="140" rx="8" fill="${BG}" stroke="${ACCENT_2}" stroke-width="2" />
    <text x="70" y="32" font="bold 13px system-ui" font-size="13" font-weight="700" fill="${ACCENT_2}" text-anchor="middle">v(t)</text>
    <text x="70" y="78" font="11px system-ui" font-size="11" fill="${INK}" text-anchor="middle">velocity</text>
    <text x="70" y="115" font="10px system-ui" font-size="10" font-style="italic" fill="${MUTED}" text-anchor="middle">= dx/dt</text>
  </g>

  <g transform="translate(360, 70)">
    <rect x="0" y="0" width="140" height="140" rx="8" fill="${BG}" stroke="${ACCENT_3}" stroke-width="2" />
    <text x="70" y="32" font="bold 13px system-ui" font-size="13" font-weight="700" fill="${ACCENT_3}" text-anchor="middle">a(t)</text>
    <text x="70" y="78" font="11px system-ui" font-size="11" fill="${INK}" text-anchor="middle">acceleration</text>
    <text x="70" y="115" font="10px system-ui" font-size="10" font-style="italic" fill="${MUTED}" text-anchor="middle">= dv/dt</text>
  </g>

  <!-- Forward arrows (slope) -->
  <defs>
    <marker id="ah-fwd" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="9" markerHeight="9" orient="auto">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="${MUTED}" />
    </marker>
  </defs>
  <line x1="160" y1="120" x2="190" y2="120" stroke="${MUTED}" stroke-width="2" marker-end="url(#ah-fwd)" />
  <text x="175" y="113" font="10px system-ui" font-size="10" fill="${MUTED}" text-anchor="middle">slope</text>
  <line x1="330" y1="120" x2="360" y2="120" stroke="${MUTED}" stroke-width="2" marker-end="url(#ah-fwd)" />
  <text x="345" y="113" font="10px system-ui" font-size="10" fill="${MUTED}" text-anchor="middle">slope</text>

  <!-- Reverse arrows (area) -->
  <line x1="190" y1="160" x2="160" y2="160" stroke="${POSITIVE}" stroke-width="2" marker-end="url(#ah-fwd)" />
  <text x="175" y="178" font="10px system-ui" font-size="10" fill="${POSITIVE}" text-anchor="middle">area</text>
  <line x1="360" y1="160" x2="330" y2="160" stroke="${POSITIVE}" stroke-width="2" marker-end="url(#ah-fwd)" />
  <text x="345" y="178" font="10px system-ui" font-size="10" fill="${POSITIVE}" text-anchor="middle">area</text>

  <text x="${W / 2}" y="${H - 14}" font="11px system-ui" font-size="11" font-style="italic" fill="${MUTED}" text-anchor="middle">Slope moves you to the next derivative; area integrates back.</text>
`;
  write("section-5-graphs/slope-area-summary.svg",
    svgWrap(W, H, "Slope-area chain summary",
      "Three boxes (x, v, a) connected by 'slope' arrows going forward and 'area' arrows going backward, summarising the calculus relationships.",
      body));
}

// ── Run ─────────────────────────────────────────────────────────────────────

s1_distanceVsDisplacement();
s1_avgVsInstantaneous();
s1_1dPosition();

s2_xtUAM();
s2_vtUAM();
s2_atUAM();

s3_heightVsTime();
s3_velocityVsTime();

s4_trajectory();
s4_velocityDecomposition();
s4_keyResults();

s5_xtTangent();
s5_vtArea();
s5_xtVtAtTrio();
s5_slopeAreaSummary();

console.log("\nAll 15 SVGs written.");
