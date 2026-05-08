#!/usr/bin/env bun
/**
 * Generate the Option-2 SVG catalogue for G11-MATH-002 Derivatives —
 * Rules and Applications (issue #334).
 *
 * Run from repo root:
 *   bun scripts/generate_derivatives_visuals.ts
 *
 * Output: sample_content/g11-stem/G11-MATH-002_Derivatives_Rules_and_Applications/Option2_Catalogue/section-N/*.svg
 *
 * Reuses the Plot helpers from generate_kinematics_visuals.ts; adds a
 * secant-line drawing primitive that the Remotion clip will lift.
 */

import { writeFileSync, mkdirSync } from "node:fs";
import { join, dirname } from "node:path";

const ROOT = join(
  import.meta.dir,
  "..",
  "sample_content",
  "g11-stem",
  "G11-MATH-002_Derivatives_Rules_and_Applications",
  "Option2_Catalogue",
);

// Style tokens + makePlot lifted to pipeline/visual_templates/shared.ts.
// This generator uses the variant-B preset for makePlot (#341 phase B).
// plotPolyline kept local — script-specific signature.
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
  HIGHLIGHT,
  makePlot as makePlotShared,
  VARIANT_B,
  plotPolyline,
  type PlotConfig,
} from "../pipeline/visual_templates/shared.ts";
import { secantLine } from "../pipeline/visual_templates/derivatives.ts";

const makePlot = (c: PlotConfig) => makePlotShared(c, VARIANT_B);

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
// SECTION 1 — Derivative Concept (3 SVGs)
// ────────────────────────────────────────────────────────────────────────────

function s1_secantAndTangent() {
  const W = 540, H = 360;
  const cfg: PlotConfig = {
    width: W, height: H,
    pad: { l: 60, r: 30, t: 36, b: 50 },
    xRange: [0, 5], yRange: [0, 6],
    xTicks: [0, 1, 2, 3, 4, 5], yTicks: [0, 2, 4, 6],
    xLabel: "x", yLabel: "f(x)",
    title: "Secant Line vs Tangent Line",
  };
  const { pieces, xToPx, yToPx } = makePlot(cfg);
  const fn = (x: number) => 0.4 * x * x;
  // Curve
  pieces.push(plotPolyline(fn, [0, 5], xToPx, yToPx, { color: ACCENT, width: 3.5 }));
  // Two points for the secant
  const xa = 1, xb = 4;
  pieces.push(secantLine(fn, xa, xb, [0, 5], xToPx, yToPx, ACCENT_2, 2.5, "6 4"));
  pieces.push(`<circle cx="${xToPx(xa)}" cy="${yToPx(fn(xa))}" r="6" fill="${ACCENT_2}" stroke="${INK}" stroke-width="1.5" />`);
  pieces.push(`<circle cx="${xToPx(xb)}" cy="${yToPx(fn(xb))}" r="6" fill="${ACCENT_2}" stroke="${INK}" stroke-width="1.5" />`);
  pieces.push(`<text x="${xToPx(xa) - 12}" y="${yToPx(fn(xa)) - 12}" font="bold 12px system-ui" font-size="12" font-weight="700" fill="${ACCENT_2}" text-anchor="end">A</text>`);
  pieces.push(`<text x="${xToPx(xb) + 12}" y="${yToPx(fn(xb)) - 12}" font="bold 12px system-ui" font-size="12" font-weight="700" fill="${ACCENT_2}">B</text>`);
  // Tangent at x=3
  const xt = 3;
  const slope = 0.8 * xt;
  const tangentFn = (x: number) => fn(xt) + slope * (x - xt);
  pieces.push(plotPolyline(tangentFn, [0, 5], xToPx, yToPx, { color: POSITIVE, width: 2.5 }));
  pieces.push(`<circle cx="${xToPx(xt)}" cy="${yToPx(fn(xt))}" r="7" fill="${POSITIVE}" stroke="${INK}" stroke-width="1.5" />`);
  pieces.push(`<text x="${xToPx(xt) + 12}" y="${yToPx(fn(xt)) + 4}" font="bold 12px system-ui" font-size="12" font-weight="700" fill="${POSITIVE}">P</text>`);
  // Legend
  pieces.push(`<text x="${W - 30}" y="60" font="bold 12px system-ui" font-size="12" font-weight="700" fill="${ACCENT_2}" text-anchor="end">— —  secant (A→B)</text>`);
  pieces.push(`<text x="${W - 30}" y="76" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="end">average slope between two points</text>`);
  pieces.push(`<text x="${W - 30}" y="100" font="bold 12px system-ui" font-size="12" font-weight="700" fill="${POSITIVE}" text-anchor="end">———  tangent at P</text>`);
  pieces.push(`<text x="${W - 30}" y="116" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="end">instantaneous slope at one point</text>`);
  pieces.push(`<text x="${W / 2}" y="${H - 8}" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">The derivative f'(x) is the slope of the tangent line at point x.</text>`);
  return svgWrap(W, H, "Secant and tangent lines on a curve", "A parabolic curve y = 0.4x² with two marked points A and B connected by a dashed orange secant line, and a separate point P with a solid green tangent line passing through it. A right-side legend distinguishes the two: the secant gives the average slope between A and B, the tangent gives the instantaneous slope at P.", pieces.join(""));
}

function s1_tangentAsLimit() {
  const W = 600, H = 360;
  const cfg: PlotConfig = {
    width: W, height: H,
    pad: { l: 60, r: 30, t: 36, b: 50 },
    xRange: [0, 5], yRange: [0, 6],
    xTicks: [0, 1, 2, 3, 4, 5], yTicks: [0, 2, 4, 6],
    xLabel: "x", yLabel: "f(x)",
    title: "Tangent as the Limit of Secants — Δx → 0",
  };
  const { pieces, xToPx, yToPx } = makePlot(cfg);
  const fn = (x: number) => 0.4 * x * x;
  pieces.push(plotPolyline(fn, [0, 5], xToPx, yToPx, { color: ACCENT, width: 3.5 }));
  // Anchor at x = 2
  const xt = 2;
  const yt = fn(xt);
  // Secants for shrinking Δx values
  const deltas = [
    { dx: 2.5, opacity: 0.25, label: "Δx = 2.5" },
    { dx: 1.5, opacity: 0.45, label: "Δx = 1.5" },
    { dx: 0.8, opacity: 0.65, label: "Δx = 0.8" },
    { dx: 0.3, opacity: 0.85, label: "Δx = 0.3" },
  ];
  for (const d of deltas) {
    const x2 = xt + d.dx;
    const slope = (fn(x2) - yt) / d.dx;
    const fn2 = (x: number) => yt + slope * (x - xt);
    pieces.push(plotPolyline(fn2, [0, 5], xToPx, yToPx, { color: ACCENT_2, width: 2, dash: "6 4" }));
    pieces.push(`<circle cx="${xToPx(x2)}" cy="${yToPx(fn(x2))}" r="4" fill="${ACCENT_2}" opacity="${d.opacity}" />`);
  }
  // Final tangent (slope = f'(2) = 1.6)
  const slopeT = 0.8 * xt;
  const tFn = (x: number) => yt + slopeT * (x - xt);
  pieces.push(plotPolyline(tFn, [0, 5], xToPx, yToPx, { color: POSITIVE, width: 3.5 }));
  pieces.push(`<circle cx="${xToPx(xt)}" cy="${yToPx(yt)}" r="7" fill="${POSITIVE}" stroke="${INK}" stroke-width="1.5" />`);
  pieces.push(`<text x="${xToPx(xt) - 12}" y="${yToPx(yt) + 4}" font="bold 12px system-ui" font-size="12" font-weight="700" fill="${POSITIVE}" text-anchor="end">P</text>`);
  // Slope readout
  pieces.push(`<rect x="${W - 200}" y="50" width="180" height="100" rx="8" fill="${HIGHLIGHT}" stroke="${MUTED}" stroke-width="1" />`);
  pieces.push(`<text x="${W - 110}" y="72" font="bold 12px system-ui" font-size="12" font-weight="700" fill="${INK}" text-anchor="middle">f'(2) = lim (Δx→0)</text>`);
  pieces.push(`<text x="${W - 110}" y="90" font="bold 12px system-ui" font-size="12" font-weight="700" fill="${INK}" text-anchor="middle">[f(2+Δx) − f(2)] / Δx</text>`);
  pieces.push(`<text x="${W - 110}" y="118" font="bold 16px system-ui" font-size="16" font-weight="700" fill="${POSITIVE}" text-anchor="middle">= 1.6</text>`);
  pieces.push(`<text x="${W - 110}" y="138" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">f(x) = 0.4x²</text>`);
  pieces.push(`<text x="${W / 2}" y="${H - 8}" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">As the second point slides toward P, the secants pivot toward the tangent.</text>`);
  return svgWrap(W, H, "Tangent as the limit of secants", "A parabola with point P fixed at x=2. Four dashed orange secant lines fan out from P toward four progressively-closer second points (Δx = 2.5, 1.5, 0.8, 0.3), each more opaque than the last. The final solid green line is the tangent at P. A side panel shows the limit definition f'(2) = lim(Δx→0) [f(2+Δx) - f(2)] / Δx = 1.6.", pieces.join(""));
}

function s1_derivativeAsSlope() {
  const W = 540, H = 440;
  // Stack: f(x) on top, f'(x) below
  // Top plot: f(x) = (x-2)^3 / 3 + 2
  const topCfg: PlotConfig = {
    width: W, height: 200,
    pad: { l: 60, r: 30, t: 30, b: 30 },
    xRange: [0, 4], yRange: [0, 4],
    xTicks: [0, 1, 2, 3, 4], yTicks: [0, 1, 2, 3, 4],
    xLabel: "", yLabel: "f(x)",
    title: "Slope of f changes along the curve",
  };
  const { pieces: topPieces, xToPx: topX, yToPx: topY } = makePlot(topCfg);
  const fn = (x: number) => Math.pow(x - 2, 3) / 6 + 2;
  topPieces.push(plotPolyline(fn, [0, 4], topX, topY, { color: ACCENT, width: 3.5 }));
  // Sample points + tangent slopes
  const samples = [0.5, 1.5, 2, 2.5, 3.5];
  for (const xs of samples) {
    const ys = fn(xs);
    const slope = Math.pow(xs - 2, 2) / 2;
    const tFn = (x: number) => ys + slope * (x - xs);
    topPieces.push(plotPolyline(tFn, [Math.max(0, xs - 0.4), Math.min(4, xs + 0.4)], topX, topY, { color: POSITIVE, width: 2 }));
    topPieces.push(`<circle cx="${topX(xs)}" cy="${topY(ys)}" r="4" fill="${POSITIVE}" />`);
  }
  // Bottom plot: f'(x) = (x-2)^2 / 2
  const botCfg: PlotConfig = {
    width: W, height: 200,
    pad: { l: 60, r: 30, t: 30, b: 50 },
    xRange: [0, 4], yRange: [0, 2.5],
    xTicks: [0, 1, 2, 3, 4], yTicks: [0, 0.5, 1, 1.5, 2, 2.5],
    xLabel: "x", yLabel: "f'(x) = slope",
    title: "Plot of slope at each x → derivative function",
  };
  const { pieces: botPieces, xToPx: botX, yToPx: botY } = makePlot(botCfg);
  const dfn = (x: number) => Math.pow(x - 2, 2) / 2;
  botPieces.push(plotPolyline(dfn, [0, 4], botX, botY, { color: POSITIVE, width: 3.5 }));
  for (const xs of samples) {
    const ys = dfn(xs);
    botPieces.push(`<circle cx="${botX(xs)}" cy="${botY(ys)}" r="4" fill="${POSITIVE}" />`);
  }
  // Connect the two plots
  const body = `
  ${topPieces.join("")}
  <g transform="translate(0, 220)">${botPieces.join("")}</g>
  <text x="${W / 2}" y="${H - 6}" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">For each x, plot the slope of f at that x. The result is a new function — the derivative.</text>
`;
  return svgWrap(W, H, "Derivative is the slope-along-the-curve function", "Two stacked plots. Top: f(x) = (x-2)³/6 + 2 with five short green tangent segments at x = 0.5, 1.5, 2, 2.5, 3.5 showing the slope is steep at the ends and flat in the middle. Bottom: f'(x) = (x-2)²/2 with five matching green dots — each dot's height equals the slope of the corresponding tangent above.", body);
}

// ────────────────────────────────────────────────────────────────────────────
// SECTION 2 — Derivative Rules (3 SVGs)
// ────────────────────────────────────────────────────────────────────────────

function s2_powerRule() {
  const W = 540, H = 320;
  const body = `
  <text x="${W / 2}" y="32" font="bold 18px system-ui" font-size="18" font-weight="700" fill="${INK}" text-anchor="middle">Power Rule — d/dx (xⁿ) = n·xⁿ⁻¹</text>
  <text x="${W / 2}" y="54" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">"Bring the exponent down in front, then drop it by one."</text>

  <!-- Big formula card -->
  <rect x="80" y="80" width="380" height="60" rx="10" fill="${HIGHLIGHT}" stroke="${ACCENT_2}" stroke-width="2" />
  <text x="${W / 2}" y="120" font="bold 30px system-ui" font-size="30" font-weight="700" fill="${INK}" text-anchor="middle">d/dx (xⁿ) = n · xⁿ⁻¹</text>

  <!-- Examples -->
  <text x="100" y="180" font="bold 14px system-ui" font-size="14" font-weight="700" fill="${INK}">Examples</text>

  <text x="100" y="208" font="14px system-ui" font-size="14" fill="${INK}">d/dx (x³)</text>
  <text x="240" y="208" font="14px system-ui" font-size="14" fill="${INK}" text-anchor="middle">=</text>
  <text x="380" y="208" font="14px system-ui" font-size="14" fill="${POSITIVE}" font-weight="700">3 · x²</text>

  <text x="100" y="234" font="14px system-ui" font-size="14" fill="${INK}">d/dx (x⁵)</text>
  <text x="240" y="234" font="14px system-ui" font-size="14" fill="${INK}" text-anchor="middle">=</text>
  <text x="380" y="234" font="14px system-ui" font-size="14" fill="${POSITIVE}" font-weight="700">5 · x⁴</text>

  <text x="100" y="260" font="14px system-ui" font-size="14" fill="${INK}">d/dx (x¹) = d/dx (x)</text>
  <text x="240" y="260" font="14px system-ui" font-size="14" fill="${INK}" text-anchor="middle">=</text>
  <text x="380" y="260" font="14px system-ui" font-size="14" fill="${POSITIVE}" font-weight="700">1 · x⁰ = 1</text>

  <text x="100" y="286" font="14px system-ui" font-size="14" fill="${INK}">d/dx (x⁻²)</text>
  <text x="240" y="286" font="14px system-ui" font-size="14" fill="${INK}" text-anchor="middle">=</text>
  <text x="380" y="286" font="14px system-ui" font-size="14" fill="${POSITIVE}" font-weight="700">−2 · x⁻³</text>

  <text x="${W / 2}" y="${H - 10}" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">Works for any real n — positive, negative, fractional. Constants? d/dx (constant) = 0.</text>
`;
  return svgWrap(W, H, "Power rule for differentiation", "A highlighted formula card 'd/dx (xⁿ) = n · xⁿ⁻¹' followed by four worked examples: derivative of x³ is 3x², of x⁵ is 5x⁴, of x is 1, of x⁻² is −2x⁻³.", body);
}

function s2_chainRule() {
  const W = 600, H = 380;
  let body = `
  <text x="${W / 2}" y="32" font="bold 18px system-ui" font-size="18" font-weight="700" fill="${INK}" text-anchor="middle">Chain Rule — Compose Outer · Inner</text>
  <text x="${W / 2}" y="54" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">Differentiate the outer function (leaving the inner alone), then multiply by the derivative of the inner.</text>

  <!-- Formula card -->
  <rect x="80" y="80" width="440" height="60" rx="10" fill="${HIGHLIGHT}" stroke="${ACCENT_2}" stroke-width="2" />
  <text x="${W / 2}" y="120" font="bold 22px system-ui" font-size="22" font-weight="700" fill="${INK}" text-anchor="middle">d/dx (f(g(x))) = f'(g(x)) · g'(x)</text>

  <!-- Worked example: y = (3x + 2)⁵ -->
  <text x="80" y="180" font="bold 14px system-ui" font-size="14" font-weight="700" fill="${INK}">Worked example: y = (3x + 2)⁵</text>

  <!-- Decomposition tree -->
  <g transform="translate(80, 200)">
    <rect x="0" y="0" width="180" height="40" rx="6" fill="${BG}" stroke="${ACCENT}" stroke-width="2" />
    <text x="90" y="26" font="bold 14px system-ui" font-size="14" font-weight="700" fill="${INK}" text-anchor="middle">outer: f(u) = u⁵</text>

    <line x1="90" y1="40" x2="90" y2="60" stroke="${MUTED}" stroke-width="2" />

    <rect x="0" y="60" width="180" height="40" rx="6" fill="${BG}" stroke="${ACCENT_3}" stroke-width="2" />
    <text x="90" y="86" font="bold 14px system-ui" font-size="14" font-weight="700" fill="${INK}" text-anchor="middle">inner: g(x) = 3x + 2</text>
  </g>

  <!-- Computation column -->
  <g transform="translate(300, 200)">
    <text x="0" y="20" font="bold 13px system-ui" font-size="13" font-weight="700" fill="${ACCENT}">f'(u) = 5u⁴ → f'(g(x)) = 5(3x+2)⁴</text>
    <text x="0" y="60" font="bold 13px system-ui" font-size="13" font-weight="700" fill="${ACCENT_3}">g'(x) = 3</text>
    <text x="0" y="100" font="bold 14px system-ui" font-size="14" font-weight="700" fill="${POSITIVE}">y' = 5(3x+2)⁴ · 3</text>
    <text x="0" y="120" font="bold 14px system-ui" font-size="14" font-weight="700" fill="${POSITIVE}">    = 15(3x+2)⁴</text>
  </g>

  <text x="${W / 2}" y="${H - 18}" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">The "chain" metaphor: each link is a function. To differentiate, walk the chain outside-in, multiplying.</text>
`;
  return svgWrap(W, H, "Chain rule decomposition", "The chain-rule formula d/dx (f(g(x))) = f'(g(x)) · g'(x) in a highlighted card, followed by a worked example y = (3x+2)⁵ shown as a decomposition tree (outer u⁵ over inner 3x+2) on the left and the step-by-step computation on the right ending at y' = 15(3x+2)⁴.", body);
}

function s2_productQuotient() {
  const W = 720, H = 320;
  const body = `
  <text x="${W / 2}" y="32" font="bold 18px system-ui" font-size="18" font-weight="700" fill="${INK}" text-anchor="middle">Product Rule + Quotient Rule</text>

  <!-- Product rule -->
  <text x="180" y="80" font="bold 14px system-ui" font-size="14" font-weight="700" fill="${ACCENT}" text-anchor="middle">Product Rule</text>
  <rect x="40" y="100" width="280" height="60" rx="10" fill="${HIGHLIGHT}" stroke="${ACCENT}" stroke-width="2" />
  <text x="180" y="138" font="bold 18px system-ui" font-size="18" font-weight="700" fill="${INK}" text-anchor="middle">(uv)' = u'v + uv'</text>

  <text x="40" y="190" font="13px system-ui" font-size="13" fill="${INK}">Example: y = x² · sin(x)</text>
  <text x="40" y="216" font="13px system-ui" font-size="13" fill="${MUTED}">u = x², u' = 2x</text>
  <text x="40" y="234" font="13px system-ui" font-size="13" fill="${MUTED}">v = sin(x), v' = cos(x)</text>
  <text x="40" y="262" font="bold 13px system-ui" font-size="13" font-weight="700" fill="${POSITIVE}">y' = 2x · sin(x) + x² · cos(x)</text>

  <!-- Quotient rule -->
  <text x="540" y="80" font="bold 14px system-ui" font-size="14" font-weight="700" fill="${ACCENT_2}" text-anchor="middle">Quotient Rule</text>
  <rect x="380" y="100" width="320" height="60" rx="10" fill="${HIGHLIGHT}" stroke="${ACCENT_2}" stroke-width="2" />
  <text x="540" y="138" font="bold 18px system-ui" font-size="18" font-weight="700" fill="${INK}" text-anchor="middle">(u/v)' = (u'v − uv') / v²</text>

  <text x="400" y="190" font="13px system-ui" font-size="13" fill="${INK}">Example: y = x / (x² + 1)</text>
  <text x="400" y="216" font="13px system-ui" font-size="13" fill="${MUTED}">u = x, u' = 1</text>
  <text x="400" y="234" font="13px system-ui" font-size="13" fill="${MUTED}">v = x² + 1, v' = 2x</text>
  <text x="400" y="262" font="bold 13px system-ui" font-size="13" font-weight="700" fill="${POSITIVE}">y' = (1·(x²+1) − x·2x) / (x²+1)²</text>

  <text x="${W / 2}" y="${H - 12}" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">Mnemonic: "low-D-high minus high-D-low, all over the square of what's below."</text>
`;
  return svgWrap(W, H, "Product and quotient rules", "Side-by-side cards: left side shows the product rule (uv)' = u'v + uv' with worked example y = x²sin(x). Right side shows the quotient rule (u/v)' = (u'v − uv') / v² with worked example y = x / (x² + 1).", body);
}

// ────────────────────────────────────────────────────────────────────────────
// SECTION 3 — Applications (3 SVGs)
// ────────────────────────────────────────────────────────────────────────────

function s3_optimizationExtrema() {
  const W = 540, H = 360;
  const cfg: PlotConfig = {
    width: W, height: H,
    pad: { l: 60, r: 30, t: 36, b: 50 },
    xRange: [0, 5], yRange: [0, 5],
    xTicks: [0, 1, 2, 3, 4, 5], yTicks: [0, 1, 2, 3, 4, 5],
    xLabel: "x", yLabel: "f(x)",
    title: "Local Extrema — Where f'(x) = 0",
  };
  const { pieces, xToPx, yToPx } = makePlot(cfg);
  // Cubic with a max and a min
  const fn = (x: number) => 0.5 * Math.pow(x - 1, 3) - 1.5 * (x - 1) + 2.5;
  pieces.push(plotPolyline(fn, [0, 5], xToPx, yToPx, { color: ACCENT, width: 3.5 }));
  // f'(x) = 1.5(x-1)^2 - 1.5; zero at x = 1 ± 1
  // x = 0 → max; x = 2 → min
  // Add max marker
  const xmax = 0, ymax = fn(xmax);
  const xmin = 2, ymin = fn(xmin);
  // Horizontal tangent at max
  pieces.push(`<line x1="${xToPx(xmax) - 30}" y1="${yToPx(ymax)}" x2="${xToPx(xmax) + 50}" y2="${yToPx(ymax)}" stroke="${POSITIVE}" stroke-width="2" stroke-dasharray="4 3" />`);
  pieces.push(`<circle cx="${xToPx(xmax)}" cy="${yToPx(ymax)}" r="7" fill="${POSITIVE}" stroke="${INK}" stroke-width="1.5" />`);
  pieces.push(`<text x="${xToPx(xmax) + 60}" y="${yToPx(ymax) + 4}" font="bold 13px system-ui" font-size="13" font-weight="700" fill="${POSITIVE}">local MAX  (f' = 0)</text>`);
  // Horizontal tangent at min
  pieces.push(`<line x1="${xToPx(xmin) - 50}" y1="${yToPx(ymin)}" x2="${xToPx(xmin) + 50}" y2="${yToPx(ymin)}" stroke="${NEGATIVE}" stroke-width="2" stroke-dasharray="4 3" />`);
  pieces.push(`<circle cx="${xToPx(xmin)}" cy="${yToPx(ymin)}" r="7" fill="${NEGATIVE}" stroke="${INK}" stroke-width="1.5" />`);
  pieces.push(`<text x="${xToPx(xmin) + 60}" y="${yToPx(ymin) + 4}" font="bold 13px system-ui" font-size="13" font-weight="700" fill="${NEGATIVE}">local MIN  (f' = 0)</text>`);
  // Caption
  pieces.push(`<text x="${W / 2}" y="${H - 8}" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">At any local max or min, the tangent line is horizontal — i.e. f'(x) = 0. (Also: anywhere f' is undefined.)</text>`);
  return svgWrap(W, H, "Local extrema where f prime equals zero", "A cubic-like curve with two highlighted points: a green local maximum at x=0 with a horizontal dashed tangent above and a red local minimum at x=2 with another horizontal dashed tangent. Both points are circled. Captions identify each as 'f' = 0'.", pieces.join(""));
}

function s3_relatedRatesBalloon() {
  const W = 600, H = 360;
  let body = `
  <text x="${W / 2}" y="32" font="bold 18px system-ui" font-size="18" font-weight="700" fill="${INK}" text-anchor="middle">Related Rates — Balloon Inflating</text>
  <text x="${W / 2}" y="54" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">Air pumps in at a known rate. How fast does the radius grow?</text>

  <!-- Three balloons at three times -->
  <g transform="translate(120, 170)">
    <circle cx="0" cy="0" r="30" fill="${ACCENT}" opacity="0.35" stroke="${ACCENT}" stroke-width="2" />
    <text x="0" y="55" font="bold 12px system-ui" font-size="12" font-weight="700" fill="${INK}" text-anchor="middle">t = 1 s</text>
    <text x="0" y="73" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">r = 1.0 cm</text>
  </g>
  <g transform="translate(280, 170)">
    <circle cx="0" cy="0" r="50" fill="${ACCENT}" opacity="0.35" stroke="${ACCENT}" stroke-width="2" />
    <text x="0" y="75" font="bold 12px system-ui" font-size="12" font-weight="700" fill="${INK}" text-anchor="middle">t = 4 s</text>
    <text x="0" y="93" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">r = 1.6 cm</text>
  </g>
  <g transform="translate(460, 170)">
    <circle cx="0" cy="0" r="70" fill="${ACCENT}" opacity="0.35" stroke="${ACCENT}" stroke-width="2" />
    <text x="0" y="95" font="bold 12px system-ui" font-size="12" font-weight="700" fill="${INK}" text-anchor="middle">t = 8 s</text>
    <text x="0" y="113" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">r = 2.0 cm</text>
  </g>

  <!-- Pump arrow + dV/dt label -->
  <text x="60" y="230" font="bold 13px system-ui" font-size="13" font-weight="700" fill="${POSITIVE}">dV/dt = 5 cm³/s</text>
  <text x="60" y="246" font="11px system-ui" font-size="11" fill="${MUTED}">(constant pump rate)</text>

  <!-- Math reasoning -->
  <g transform="translate(60, 280)">
    <text x="0" y="0" font="bold 13px system-ui" font-size="13" font-weight="700" fill="${INK}">V = (4/3) π r³  →  dV/dt = 4π r² · dr/dt</text>
    <text x="0" y="22" font="bold 13px system-ui" font-size="13" font-weight="700" fill="${POSITIVE}">→  dr/dt = (dV/dt) / (4π r²)</text>
    <text x="0" y="42" font="13px system-ui" font-size="13" fill="${MUTED}">at r = 2 cm: dr/dt = 5 / (4π · 4) ≈ 0.10 cm/s</text>
  </g>

  <text x="${W / 2}" y="${H - 8}" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">Volume grows at a steady rate; radius grows much slower (and slower as the balloon gets bigger).</text>
`;
  return svgWrap(W, H, "Related rates balloon inflating", "Three transparent blue circles in a row representing a balloon at t=1, 4, and 8 seconds with radii 1.0, 1.6, and 2.0 cm respectively. Below: the volume formula V = (4/3)πr³ leads to dV/dt = 4πr² · dr/dt, with the worked answer dr/dt ≈ 0.10 cm/s when r = 2 cm.", body);
}

function s3_motionThree() {
  const W = 540, H = 540;
  // Three stacked plots: s(t), v(t), a(t)
  const plotH = 160;
  const cfgPos: PlotConfig = {
    width: W, height: plotH,
    pad: { l: 60, r: 30, t: 30, b: 40 },
    xRange: [0, 5], yRange: [0, 25],
    xTicks: [0, 1, 2, 3, 4, 5], yTicks: [0, 5, 10, 15, 20, 25],
    xLabel: "", yLabel: "s (m)",
    title: "Position s(t) = t²",
  };
  const { pieces: posPieces, xToPx: posX, yToPx: posY } = makePlot(cfgPos);
  posPieces.push(plotPolyline((t) => t * t, [0, 5], posX, posY, { color: ACCENT, width: 3 }));

  const cfgVel: PlotConfig = {
    width: W, height: plotH,
    pad: { l: 60, r: 30, t: 30, b: 40 },
    xRange: [0, 5], yRange: [0, 12],
    xTicks: [0, 1, 2, 3, 4, 5], yTicks: [0, 2, 4, 6, 8, 10, 12],
    xLabel: "", yLabel: "v (m/s)",
    title: "Velocity v(t) = ds/dt = 2t",
  };
  const { pieces: velPieces, xToPx: velX, yToPx: velY } = makePlot(cfgVel);
  velPieces.push(plotPolyline((t) => 2 * t, [0, 5], velX, velY, { color: ACCENT_2, width: 3 }));

  const cfgAcc: PlotConfig = {
    width: W, height: plotH,
    pad: { l: 60, r: 30, t: 30, b: 50 },
    xRange: [0, 5], yRange: [0, 4],
    xTicks: [0, 1, 2, 3, 4, 5], yTicks: [0, 1, 2, 3, 4],
    xLabel: "t (s)", yLabel: "a (m/s²)",
    title: "Acceleration a(t) = dv/dt = 2",
  };
  const { pieces: accPieces, xToPx: accX, yToPx: accY } = makePlot(cfgAcc);
  accPieces.push(plotPolyline(() => 2, [0, 5], accX, accY, { color: POSITIVE, width: 3 }));

  const body = `
  ${posPieces.join("")}
  <g transform="translate(0, 180)">${velPieces.join("")}</g>
  <g transform="translate(0, 360)">${accPieces.join("")}</g>
`;
  return svgWrap(W, H, "Position velocity acceleration as successive derivatives", "Three vertically-stacked plots illustrating that velocity is the derivative of position and acceleration is the derivative of velocity. Top: parabolic position s(t) = t². Middle: linear velocity v(t) = 2t. Bottom: constant acceleration a(t) = 2.", body);
}

// ────────────────────────────────────────────────────────────────────────────
// Main
// ────────────────────────────────────────────────────────────────────────────

mkdirSync(ROOT, { recursive: true });

write("section-1-derivative-concept/secant-and-tangent-lines.svg", s1_secantAndTangent());
write("section-1-derivative-concept/tangent-as-limit-of-secants.svg", s1_tangentAsLimit());
write("section-1-derivative-concept/derivative-as-slope-along-curve.svg", s1_derivativeAsSlope());

write("section-2-rules/power-rule-card.svg", s2_powerRule());
write("section-2-rules/chain-rule-decomposition.svg", s2_chainRule());
write("section-2-rules/product-and-quotient-rules.svg", s2_productQuotient());

write("section-3-applications/optimization-extrema.svg", s3_optimizationExtrema());
write("section-3-applications/related-rates-balloon.svg", s3_relatedRatesBalloon());
write("section-3-applications/motion-position-velocity-acceleration.svg", s3_motionThree());

console.log("done — 9 SVGs");
