#!/usr/bin/env bun
/**
 * Generate the Option-2 SVG catalogue for G8-SCI-002 Waves — Light and Sound
 * (issue #335).
 *
 * Run from repo root:
 *   bun scripts/generate_g8_waves_visuals.ts
 *
 * Output: sample_content/g8-stem/G8-SCI-002_Waves_Light_and_Sound/Option2_Catalogue/section-N/*.svg
 *
 * 2-phase issue: no new Remotion clips (G11-PHYS-010 superposition Remotion
 * is reused as-is). G8 audience — friendlier than the G11 oscillations
 * catalogue, with EM-spectrum and sound-pressure additions.
 */

import { writeFileSync, mkdirSync } from "node:fs";
import { join, dirname } from "node:path";

const ROOT = join(
  import.meta.dir,
  "..",
  "sample_content",
  "g8-stem",
  "G8-SCI-002_Waves_Light_and_Sound",
  "Option2_Catalogue",
);

// Style tokens + makePlot lifted to pipeline/visual_templates/shared.ts.
// This generator uses the variant-B-Y preset: same as variant-B but
// suppresses the x=0 axis line (the original local makePlot here only
// checked yRange for zero-axis rendering, never xRange).
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
  type PlotConfig,
  type MakePlotOptions,
} from "../pipeline/visual_templates/shared.ts";

// Variant-B-Y preset — like VARIANT_B but renders only the y-zero axis,
// not the x-zero axis. Preserves byte-equivalence with the local helper.
const VARIANT_B_Y_ONLY: MakePlotOptions = {
  ...VARIANT_B,
  axisStyle: "when-y-zero-only",
};
const makePlot = (c: PlotConfig) => makePlotShared(c, VARIANT_B_Y_ONLY);
function plotPolyline(fn: (x: number) => number, xRange: [number, number], xToPx: (x: number) => number, yToPx: (y: number) => number, options: { color?: string; width?: number; samples?: number; dash?: string } = {}) {
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
// SECTION 1 — Wave Basics (3 SVGs)
// ────────────────────────────────────────────────────────────────────────────

function s1_transverseAnatomy() {
  const W = 600, H = 360;
  const cfg: PlotConfig = {
    width: W, height: H,
    pad: { l: 60, r: 40, t: 40, b: 50 },
    xRange: [0, 4 * Math.PI], yRange: [-1.5, 1.5],
    xTicks: [], yTicks: [],
    xLabel: "position", yLabel: "displacement",
    title: "Transverse Wave Anatomy",
  };
  const { pieces, xToPx, yToPx } = makePlot(cfg);
  const fn = (x: number) => Math.sin(x);
  pieces.push(plotPolyline(fn, [0, 4 * Math.PI], xToPx, yToPx, { color: ACCENT, width: 4 }));

  // Crest at x = π/2, trough at x = 3π/2
  const crestX = Math.PI / 2, troughX = 3 * Math.PI / 2;
  pieces.push(`<circle cx="${xToPx(crestX)}" cy="${yToPx(1)}" r="6" fill="${POSITIVE}" stroke="${INK}" stroke-width="1.5" />`);
  pieces.push(`<text x="${xToPx(crestX)}" y="${yToPx(1) - 14}" font="bold 13px system-ui" font-size="13" font-weight="700" fill="${POSITIVE}" text-anchor="middle">crest</text>`);
  pieces.push(`<circle cx="${xToPx(troughX)}" cy="${yToPx(-1)}" r="6" fill="${NEGATIVE}" stroke="${INK}" stroke-width="1.5" />`);
  pieces.push(`<text x="${xToPx(troughX)}" y="${yToPx(-1) + 24}" font="bold 13px system-ui" font-size="13" font-weight="700" fill="${NEGATIVE}" text-anchor="middle">trough</text>`);

  // Wavelength bracket between two crests
  const c1 = Math.PI / 2, c2 = 5 * Math.PI / 2;
  pieces.push(`<line x1="${xToPx(c1)}" y1="${yToPx(1.3)}" x2="${xToPx(c2)}" y2="${yToPx(1.3)}" stroke="${ACCENT_2}" stroke-width="2.5" />`);
  pieces.push(`<line x1="${xToPx(c1)}" y1="${yToPx(1.2)}" x2="${xToPx(c1)}" y2="${yToPx(1.4)}" stroke="${ACCENT_2}" stroke-width="2.5" />`);
  pieces.push(`<line x1="${xToPx(c2)}" y1="${yToPx(1.2)}" x2="${xToPx(c2)}" y2="${yToPx(1.4)}" stroke="${ACCENT_2}" stroke-width="2.5" />`);
  pieces.push(`<text x="${(xToPx(c1) + xToPx(c2)) / 2}" y="${yToPx(1.3) - 10}" font="bold 14px system-ui" font-size="14" font-weight="700" fill="${ACCENT_2}" text-anchor="middle">wavelength λ</text>`);

  // Amplitude arrow from axis to crest
  const ampX = 7 * Math.PI / 2;
  pieces.push(`<line x1="${xToPx(ampX)}" y1="${yToPx(0)}" x2="${xToPx(ampX)}" y2="${yToPx(1)}" stroke="${ACCENT_3}" stroke-width="2.5" />`);
  pieces.push(`<polygon points="${xToPx(ampX) - 5},${yToPx(1) + 8} ${xToPx(ampX) + 5},${yToPx(1) + 8} ${xToPx(ampX)},${yToPx(1)}" fill="${ACCENT_3}" />`);
  pieces.push(`<text x="${xToPx(ampX) + 14}" y="${yToPx(0.5) + 4}" font="bold 13px system-ui" font-size="13" font-weight="700" fill="${ACCENT_3}">amplitude A</text>`);

  pieces.push(`<text x="${W / 2}" y="${H - 10}" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">A transverse wave: particles wiggle perpendicular to the direction the wave travels.</text>`);
  return svgWrap(W, H, "Transverse wave anatomy with labels", "A sine wave with two full cycles. Green dot at the first crest is labelled 'crest'; red dot at the first trough is labelled 'trough'. An orange double-headed bracket spans crest-to-crest labelled 'wavelength λ'. A teal vertical arrow from the central axis up to a crest is labelled 'amplitude A'.", pieces.join(""));
}

function s1_transverseVsLongitudinal() {
  const W = 720, H = 380;
  let body = `
  <text x="${W / 2}" y="32" font="bold 18px system-ui" font-size="18" font-weight="700" fill="${INK}" text-anchor="middle">Transverse vs Longitudinal Waves</text>
  <text x="${W / 2}" y="54" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">It depends on which way the particles wiggle relative to which way the wave travels.</text>

  <!-- Transverse — sine wave with arrow showing wave direction -->
  <text x="180" y="100" font="bold 14px system-ui" font-size="14" font-weight="700" fill="${ACCENT}" text-anchor="middle">Transverse (light, water surface)</text>
  <text x="180" y="118" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">particles ↕ · wave →</text>
`;
  // Sine wave for transverse
  const tCfg: PlotConfig = {
    width: 320, height: 130,
    pad: { l: 20, r: 20, t: 0, b: 0 },
    xRange: [0, 4 * Math.PI], yRange: [-1.5, 1.5],
    xTicks: [], yTicks: [], xLabel: "", yLabel: "",
  };
  const { pieces: tPieces, xToPx: tx, yToPx: ty } = makePlot(tCfg);
  tPieces.shift(); // remove background rect
  tPieces.push(plotPolyline((x) => Math.sin(x), [0, 4 * Math.PI], tx, ty, { color: ACCENT, width: 3 }));
  tPieces.push(`<line x1="${tx(2 * Math.PI)}" y1="${ty(0)}" x2="${tx(2 * Math.PI)}" y2="${ty(1)}" stroke="${POSITIVE}" stroke-width="2" />`);
  tPieces.push(`<polygon points="${tx(2 * Math.PI) - 4},${ty(1) + 6} ${tx(2 * Math.PI) + 4},${ty(1) + 6} ${tx(2 * Math.PI)},${ty(1)}" fill="${POSITIVE}" />`);
  tPieces.push(`<text x="${tx(2 * Math.PI) + 8}" y="${ty(0.5) + 4}" font="11px system-ui" font-size="11" fill="${POSITIVE}">↕ particle</text>`);
  tPieces.push(`<line x1="${tx(0.4)}" y1="${ty(-1.4)}" x2="${tx(11.5)}" y2="${ty(-1.4)}" stroke="${NEGATIVE}" stroke-width="2" />`);
  tPieces.push(`<polygon points="${tx(11.5)},${ty(-1.4) - 4} ${tx(11.5) - 8},${ty(-1.4)} ${tx(11.5)},${ty(-1.4) + 4}" fill="${NEGATIVE}" />`);
  tPieces.push(`<text x="${(tx(0.4) + tx(11.5)) / 2}" y="${ty(-1.4) + 18}" font="11px system-ui" font-size="11" fill="${NEGATIVE}" text-anchor="middle">→ wave travels this way</text>`);

  body += `<g transform="translate(20, 130)">${tPieces.join("")}</g>`;

  // Longitudinal — compression/rarefaction pattern
  body += `
  <text x="540" y="100" font="bold 14px system-ui" font-size="14" font-weight="700" fill="${ACCENT_2}" text-anchor="middle">Longitudinal (sound)</text>
  <text x="540" y="118" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">particles ↔ · wave →</text>`;

  // Draw 30 vertical lines representing air molecules at varying density
  const longX0 = 380;
  const longY0 = 200;
  const longH = 60;
  for (let i = 0; i < 30; i++) {
    // Density modulated by sine: closer together at peaks
    const xRel = i / 30;
    const phase = xRel * 4 * Math.PI;
    const offset = 4 * Math.sin(phase); // squeeze toward zero, expand toward π/ω
    const x = longX0 + xRel * 320 + offset;
    body += `<line x1="${x.toFixed(1)}" y1="${longY0}" x2="${x.toFixed(1)}" y2="${longY0 + longH}" stroke="${ACCENT_2}" stroke-width="2" />`;
  }
  // Compression / rarefaction labels
  body += `
  <text x="465" y="${longY0 - 10}" font="bold 11px system-ui" font-size="11" font-weight="700" fill="${POSITIVE}" text-anchor="middle">compression</text>
  <text x="540" y="${longY0 - 10}" font="bold 11px system-ui" font-size="11" font-weight="700" fill="${NEGATIVE}" text-anchor="middle">rarefaction</text>
  <text x="615" y="${longY0 - 10}" font="bold 11px system-ui" font-size="11" font-weight="700" fill="${POSITIVE}" text-anchor="middle">compression</text>

  <line x1="${longX0}" y1="${longY0 + longH + 24}" x2="${longX0 + 320}" y2="${longY0 + longH + 24}" stroke="${NEGATIVE}" stroke-width="2" />
  <polygon points="${longX0 + 320},${longY0 + longH + 20} ${longX0 + 312},${longY0 + longH + 24} ${longX0 + 320},${longY0 + longH + 28}" fill="${NEGATIVE}" />
  <text x="${longX0 + 160}" y="${longY0 + longH + 42}" font="11px system-ui" font-size="11" fill="${NEGATIVE}" text-anchor="middle">→ wave travels this way (same as particle motion!)</text>
`;

  body += `
  <text x="${W / 2}" y="${H - 14}" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">Same physics either way — just different geometry of the particle motion.</text>
`;
  return svgWrap(W, H, "Transverse versus longitudinal waves", "Two side-by-side wave illustrations: left shows a transverse sine wave with particle-motion arrow up/down and wave-direction arrow rightward. Right shows longitudinal sound-wave compressions and rarefactions as vertical lines that bunch and spread along the propagation direction.", body);
}

function s1_waveEquation() {
  const W = 540, H = 320;
  const body = `
  <text x="${W / 2}" y="32" font="bold 18px system-ui" font-size="18" font-weight="700" fill="${INK}" text-anchor="middle">Wave Equation — v = f × λ</text>
  <text x="${W / 2}" y="54" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">Speed equals frequency times wavelength. Holds for every kind of wave.</text>

  <rect x="80" y="80" width="380" height="60" rx="10" fill="${HIGHLIGHT}" stroke="${ACCENT_2}" stroke-width="2" />
  <text x="${W / 2}" y="120" font="bold 30px system-ui" font-size="30" font-weight="700" fill="${INK}" text-anchor="middle">v = f · λ</text>

  <!-- Three example rows -->
  <text x="100" y="180" font="bold 14px system-ui" font-size="14" font-weight="700" fill="${INK}">Example: sound in air</text>
  <text x="100" y="202" font="13px system-ui" font-size="13" fill="${MUTED}">f = 440 Hz (concert A) · λ = 0.78 m</text>
  <text x="100" y="222" font="bold 13px system-ui" font-size="13" font-weight="700" fill="${POSITIVE}">→ v = 343 m/s ✓ (speed of sound)</text>

  <text x="100" y="252" font="bold 14px system-ui" font-size="14" font-weight="700" fill="${INK}">Example: red light in vacuum</text>
  <text x="100" y="274" font="13px system-ui" font-size="13" fill="${MUTED}">f = 4.6 × 10¹⁴ Hz · λ = 656 nm = 6.56 × 10⁻⁷ m</text>
  <text x="100" y="294" font="bold 13px system-ui" font-size="13" font-weight="700" fill="${POSITIVE}">→ v ≈ 3 × 10⁸ m/s ✓ (speed of light)</text>
`;
  return svgWrap(W, H, "Wave equation v equals f times lambda", "A highlighted formula card showing v = f · λ with two worked examples beneath: sound in air at 440 Hz with 0.78 m wavelength giving v = 343 m/s, and red light at 4.6 × 10¹⁴ Hz with 656 nm wavelength giving v ≈ 3 × 10⁸ m/s.", body);
}

// ────────────────────────────────────────────────────────────────────────────
// SECTION 2 — Light & EM Spectrum (3 SVGs)
// ────────────────────────────────────────────────────────────────────────────

function s2_emSpectrumStrip() {
  const W = 760, H = 320;
  const stripX0 = 60, stripX1 = W - 40, stripY = 130, stripH = 70;

  // EM-spectrum bands with their wavelength ranges. Position is approximate / log-scale visual.
  // Use linear placement along the strip for friendliness; label with wavelength.
  const bands = [
    { name: "Radio", x0: 0, x1: 0.18, color: "#7c3aed", lambda: ">1 m" },
    { name: "Microwave", x0: 0.18, x1: 0.34, color: "#5b21b6", lambda: "1 m – 1 mm" },
    { name: "Infrared", x0: 0.34, x1: 0.50, color: "#dc2626", lambda: "1 mm – 700 nm" },
    { name: "Visible", x0: 0.50, x1: 0.55, color: "#fde047", lambda: "700–380 nm" },
    { name: "Ultraviolet", x0: 0.55, x1: 0.68, color: "#7c3aed", lambda: "380–10 nm" },
    { name: "X-rays", x0: 0.68, x1: 0.84, color: "#1e40af", lambda: "10 nm – 0.01 nm" },
    { name: "Gamma rays", x0: 0.84, x1: 1.00, color: "#16a34a", lambda: "<0.01 nm" },
  ];

  let body = `
  <text x="${W / 2}" y="32" font="bold 18px system-ui" font-size="18" font-weight="700" fill="${INK}" text-anchor="middle">Electromagnetic Spectrum — All "Light" Is Light</text>
  <text x="${W / 2}" y="54" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">Same wave, different wavelength. The bit your eye can see is a tiny slice in the middle.</text>
`;
  for (const b of bands) {
    const x = stripX0 + b.x0 * (stripX1 - stripX0);
    const w = (b.x1 - b.x0) * (stripX1 - stripX0);
    body += `
    <rect x="${x}" y="${stripY}" width="${w}" height="${stripH}" fill="${b.color}" stroke="${INK}" stroke-width="0.8" />
    <text x="${x + w / 2}" y="${stripY + stripH / 2 + 4}" font="bold 11px system-ui" font-size="11" font-weight="700" fill="white" text-anchor="middle">${b.name}</text>
    <text x="${x + w / 2}" y="${stripY + stripH + 22}" font="10px system-ui" font-size="10" fill="${MUTED}" text-anchor="middle">${b.lambda}</text>`;
  }

  // "Visible" inset rainbow magnified
  const insX0 = stripX0 + 0.50 * (stripX1 - stripX0);
  const insX1 = stripX0 + 0.55 * (stripX1 - stripX0);
  const targetY = 250;
  body += `
  <line x1="${insX0}" y1="${stripY + stripH}" x2="${stripX0 + 0.10 * (stripX1 - stripX0)}" y2="${targetY}" stroke="${MUTED}" stroke-width="1" stroke-dasharray="3 3" />
  <line x1="${insX1}" y1="${stripY + stripH}" x2="${stripX0 + 0.55 * (stripX1 - stripX0)}" y2="${targetY}" stroke="${MUTED}" stroke-width="1" stroke-dasharray="3 3" />`;

  // Visible-band rainbow inset
  const visBands = [
    { name: "violet", color: "#7c3aed" },
    { name: "blue", color: "#2563eb" },
    { name: "green", color: "#16a34a" },
    { name: "yellow", color: "#facc15" },
    { name: "orange", color: "#ea580c" },
    { name: "red", color: "#dc2626" },
  ];
  const insWidth = (0.55 - 0.10) * (stripX1 - stripX0);
  const bandW = insWidth / visBands.length;
  for (let i = 0; i < visBands.length; i++) {
    const x = stripX0 + 0.10 * (stripX1 - stripX0) + i * bandW;
    body += `
    <rect x="${x}" y="${targetY}" width="${bandW}" height="36" fill="${visBands[i].color}" stroke="${INK}" stroke-width="0.5" />
    <text x="${x + bandW / 2}" y="${targetY + 24}" font="bold 11px system-ui" font-size="11" font-weight="700" fill="white" text-anchor="middle">${visBands[i].name}</text>`;
  }
  body += `
  <text x="${stripX0 + 0.32 * (stripX1 - stripX0)}" y="${targetY + 60}" font="bold 12px system-ui" font-size="12" font-weight="700" fill="${INK}" text-anchor="middle">visible light · 380 nm (violet) → 700 nm (red)</text>

  <text x="${W / 2}" y="${H - 10}" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">All of these travel at the speed of light c = 3 × 10⁸ m/s. They differ only in wavelength (and frequency).</text>
`;
  return svgWrap(W, H, "Electromagnetic spectrum strip with visible-light inset", "A horizontal coloured strip showing the seven main bands of the EM spectrum: radio, microwave, infrared, visible, ultraviolet, X-rays, gamma rays. Each band is labelled with its wavelength range. A magnified inset below shows the visible portion split into the six colours violet, blue, green, yellow, orange, red.", body);
}

function s2_visibleLightRainbow() {
  const W = 600, H = 280;
  let body = `
  <text x="${W / 2}" y="32" font="bold 18px system-ui" font-size="18" font-weight="700" fill="${INK}" text-anchor="middle">Visible Light — One Wavelength per Colour</text>
  <text x="${W / 2}" y="54" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">From 380 nm (violet) to 700 nm (red), with each colour pinned at its peak wavelength.</text>

  <!-- Big rainbow strip -->
  <defs>
    <linearGradient id="rainbow-g" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#7c3aed" />
      <stop offset="20%" stop-color="#2563eb" />
      <stop offset="40%" stop-color="#16a34a" />
      <stop offset="55%" stop-color="#facc15" />
      <stop offset="75%" stop-color="#ea580c" />
      <stop offset="100%" stop-color="#dc2626" />
    </linearGradient>
  </defs>
  <rect x="60" y="100" width="${W - 120}" height="80" fill="url(#rainbow-g)" stroke="${INK}" stroke-width="2" />

  <!-- Wavelength tick labels under -->
`;
  const ticks = [
    { nm: 380, x: 0, label: "violet" },
    { nm: 470, x: 0.20, label: "blue" },
    { nm: 525, x: 0.36, label: "green" },
    { nm: 580, x: 0.55, label: "yellow" },
    { nm: 610, x: 0.65, label: "orange" },
    { nm: 700, x: 1.0, label: "red" },
  ];
  const stripStart = 60, stripEnd = W - 60;
  for (const t of ticks) {
    const px = stripStart + t.x * (stripEnd - stripStart);
    body += `
    <line x1="${px}" y1="180" x2="${px}" y2="194" stroke="${INK}" stroke-width="1.5" />
    <text x="${px}" y="210" font="bold 11px system-ui" font-size="11" font-weight="700" fill="${INK}" text-anchor="middle">${t.label}</text>
    <text x="${px}" y="226" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">${t.nm} nm</text>`;
  }

  body += `
  <text x="${W / 2}" y="${H - 16}" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">Mnemonic: VIBGYOR — Violet, Indigo, Blue, Green, Yellow, Orange, Red.</text>
`;
  return svgWrap(W, H, "Visible light spectrum with named colours and wavelengths", "A horizontal rainbow gradient strip from violet on the left to red on the right. Six labelled tick marks beneath the strip identify violet (380 nm), blue (470 nm), green (525 nm), yellow (580 nm), orange (610 nm), and red (700 nm).", body);
}

function s2_lightVsSound() {
  const W = 600, H = 320;
  const body = `
  <text x="${W / 2}" y="32" font="bold 18px system-ui" font-size="18" font-weight="700" fill="${INK}" text-anchor="middle">Light vs Sound — Same Equation, Wildly Different Numbers</text>

  <g>
    <rect x="40" y="60" width="240" height="220" rx="10" fill="${BG}" stroke="${ACCENT}" stroke-width="2" />
    <text x="160" y="86" font="bold 16px system-ui" font-size="16" font-weight="700" fill="${ACCENT}" text-anchor="middle">Light</text>
    <text x="60" y="124" font="13px system-ui" font-size="13" fill="${INK}">type:</text>
    <text x="270" y="124" font="bold 13px system-ui" font-size="13" font-weight="700" fill="${INK}" text-anchor="end">transverse · electromagnetic</text>
    <text x="60" y="156" font="13px system-ui" font-size="13" fill="${INK}">needs medium?</text>
    <text x="270" y="156" font="bold 13px system-ui" font-size="13" font-weight="700" fill="${POSITIVE}" text-anchor="end">no — vacuum is fine</text>
    <text x="60" y="188" font="13px system-ui" font-size="13" fill="${INK}">speed in vacuum:</text>
    <text x="270" y="188" font="bold 13px system-ui" font-size="13" font-weight="700" fill="${INK}" text-anchor="end">3 × 10⁸ m/s</text>
    <text x="60" y="220" font="13px system-ui" font-size="13" fill="${INK}">visible λ range:</text>
    <text x="270" y="220" font="bold 13px system-ui" font-size="13" font-weight="700" fill="${INK}" text-anchor="end">380–700 nm</text>
    <text x="60" y="252" font="13px system-ui" font-size="13" fill="${INK}">sense:</text>
    <text x="270" y="252" font="bold 13px system-ui" font-size="13" font-weight="700" fill="${INK}" text-anchor="end">eye</text>
  </g>

  <g>
    <rect x="320" y="60" width="240" height="220" rx="10" fill="${BG}" stroke="${ACCENT_2}" stroke-width="2" />
    <text x="440" y="86" font="bold 16px system-ui" font-size="16" font-weight="700" fill="${ACCENT_2}" text-anchor="middle">Sound</text>
    <text x="340" y="124" font="13px system-ui" font-size="13" fill="${INK}">type:</text>
    <text x="550" y="124" font="bold 13px system-ui" font-size="13" font-weight="700" fill="${INK}" text-anchor="end">longitudinal · pressure</text>
    <text x="340" y="156" font="13px system-ui" font-size="13" fill="${INK}">needs medium?</text>
    <text x="550" y="156" font="bold 13px system-ui" font-size="13" font-weight="700" fill="${NEGATIVE}" text-anchor="end">yes — air, water, solids</text>
    <text x="340" y="188" font="13px system-ui" font-size="13" fill="${INK}">speed in air:</text>
    <text x="550" y="188" font="bold 13px system-ui" font-size="13" font-weight="700" fill="${INK}" text-anchor="end">343 m/s</text>
    <text x="340" y="220" font="13px system-ui" font-size="13" fill="${INK}">audible f range:</text>
    <text x="550" y="220" font="bold 13px system-ui" font-size="13" font-weight="700" fill="${INK}" text-anchor="end">20 Hz – 20 kHz</text>
    <text x="340" y="252" font="13px system-ui" font-size="13" fill="${INK}">sense:</text>
    <text x="550" y="252" font="bold 13px system-ui" font-size="13" font-weight="700" fill="${INK}" text-anchor="end">ear</text>
  </g>

  <text x="${W / 2}" y="${H - 12}" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">Light is ~880,000× faster than sound in air. That's why thunder follows lightning.</text>
`;
  return svgWrap(W, H, "Light versus sound comparison card", "Side-by-side comparison of light and sound across five rows: type (transverse-EM vs longitudinal-pressure), needs medium (no vs yes), speed (3 × 10⁸ m/s vs 343 m/s), wavelength/frequency range (380-700 nm vs 20 Hz-20 kHz), and sense (eye vs ear).", body);
}

// ────────────────────────────────────────────────────────────────────────────
// SECTION 3 — Sound + Resonance (3 SVGs)
// ────────────────────────────────────────────────────────────────────────────

function s3_soundPressureTrace() {
  const W = 600, H = 320;
  const cfg: PlotConfig = {
    width: W, height: H,
    pad: { l: 60, r: 30, t: 36, b: 50 },
    xRange: [0, 4], yRange: [-1.2, 1.2],
    xTicks: [0, 1, 2, 3, 4],
    yTicks: [-1, 0, 1],
    xLabel: "time t (ms)",
    yLabel: "pressure (relative)",
    title: "Sound as Pressure Variation Over Time",
  };
  const { pieces, xToPx, yToPx } = makePlot(cfg);
  pieces.push(plotPolyline((t) => Math.sin(2 * Math.PI * 2 * t), [0, 4], xToPx, yToPx, { color: ACCENT, width: 3.5 }));

  // Annotate one full cycle as the period
  pieces.push(`<line x1="${xToPx(0.25)}" y1="${yToPx(1.05)}" x2="${xToPx(0.75)}" y2="${yToPx(1.05)}" stroke="${ACCENT_2}" stroke-width="2" />`);
  pieces.push(`<line x1="${xToPx(0.25)}" y1="${yToPx(0.95)}" x2="${xToPx(0.25)}" y2="${yToPx(1.15)}" stroke="${ACCENT_2}" stroke-width="2" />`);
  pieces.push(`<line x1="${xToPx(0.75)}" y1="${yToPx(0.95)}" x2="${xToPx(0.75)}" y2="${yToPx(1.15)}" stroke="${ACCENT_2}" stroke-width="2" />`);
  pieces.push(`<text x="${xToPx(0.5)}" y="${yToPx(1.05) - 10}" font="bold 12px system-ui" font-size="12" font-weight="700" fill="${ACCENT_2}" text-anchor="middle">period T = 0.5 ms</text>`);
  pieces.push(`<text x="${xToPx(0.5)}" y="${yToPx(1.05) + 24}" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">→ frequency f = 1/T = 2000 Hz</text>`);

  pieces.push(`<text x="${W / 2}" y="${H - 8}" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">A microphone captures these pressure ripples and turns them into a graph just like this one.</text>`);
  return svgWrap(W, H, "Sound wave pressure-vs-time trace", "A sine-wave pressure trace on a time axis showing 8 cycles over 4 milliseconds. One cycle is annotated with a period bracket labelled 'period T = 0.5 ms', with the frequency calculation 'f = 1/T = 2000 Hz' underneath.", pieces.join(""));
}

function s3_pitchAndLoudness() {
  const W = 720, H = 360;
  let body = `
  <text x="${W / 2}" y="32" font="bold 18px system-ui" font-size="18" font-weight="700" fill="${INK}" text-anchor="middle">Pitch (frequency) and Loudness (amplitude)</text>
  <text x="${W / 2}" y="54" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">Two independent dials: how often the wave wiggles (pitch) and how big the wiggle is (loudness).</text>
`;
  // Four panels: high pitch / low pitch, loud / quiet
  const panels = [
    { x: 60, y: 80, w: 280, h: 110, freq: 4, amp: 1.0, title: "high pitch · loud", color: NEGATIVE },
    { x: 380, y: 80, w: 280, h: 110, freq: 4, amp: 0.4, title: "high pitch · quiet", color: ACCENT },
    { x: 60, y: 220, w: 280, h: 110, freq: 1.5, amp: 1.0, title: "low pitch · loud", color: ACCENT_2 },
    { x: 380, y: 220, w: 280, h: 110, freq: 1.5, amp: 0.4, title: "low pitch · quiet", color: POSITIVE },
  ];
  for (const p of panels) {
    body += `
    <rect x="${p.x}" y="${p.y}" width="${p.w}" height="${p.h}" rx="8" fill="${BG}" stroke="${MUTED}" stroke-width="1" />
    <text x="${p.x + p.w / 2}" y="${p.y + 22}" font="bold 13px system-ui" font-size="13" font-weight="700" fill="${p.color}" text-anchor="middle">${p.title}</text>`;
    // Sine wave inside
    const samples = 200;
    const pts: string[] = [];
    for (let i = 0; i <= samples; i++) {
      const xx = (i / samples) * (p.w - 40);
      const yy = (p.h / 2 - 10) - 30 * p.amp * Math.sin(2 * Math.PI * p.freq * (i / samples));
      pts.push(`${(p.x + 20 + xx).toFixed(1)},${(p.y + 30 + yy).toFixed(1)}`);
    }
    body += `<polyline points="${pts.join(" ")}" fill="none" stroke="${p.color}" stroke-width="3" stroke-linecap="round" />`;
  }
  // Annotation arrows
  body += `
  <text x="${W / 2}" y="${H - 14}" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">Same time axis on every panel. More wiggles = higher pitch. Taller wiggles = louder.</text>
`;
  return svgWrap(W, H, "Pitch and loudness four-panel comparison", "A 2-by-2 grid of four sine-wave panels showing four combinations: high-pitch loud (top-left, fast and tall), high-pitch quiet (top-right, fast and short), low-pitch loud (bottom-left, slow and tall), low-pitch quiet (bottom-right, slow and short).", body);
}

function s3_resonance() {
  const W = 600, H = 320;
  const cfg: PlotConfig = {
    width: W, height: H,
    pad: { l: 60, r: 30, t: 36, b: 50 },
    xRange: [0, 4], yRange: [0, 5],
    xTicks: [0, 1, 2, 3, 4],
    yTicks: [0, 1, 2, 3, 4, 5],
    xLabel: "driving frequency (× natural frequency)",
    yLabel: "amplitude",
    title: "Resonance — Big Response at the Right Frequency",
  };
  const { pieces, xToPx, yToPx } = makePlot(cfg);
  // Resonance peak around f/f0 = 1
  const fn = (x: number) => 4.5 / (Math.sqrt(Math.pow(x * x - 1, 2) + 0.04 * x * x) + 0.04);
  pieces.push(plotPolyline(fn, [0.15, 4], xToPx, yToPx, { color: ACCENT, width: 3.5 }));

  // Mark the peak
  pieces.push(`<circle cx="${xToPx(1)}" cy="${yToPx(fn(1))}" r="7" fill="${NEGATIVE}" stroke="${INK}" stroke-width="1.5" />`);
  pieces.push(`<line x1="${xToPx(1)}" y1="${yToPx(fn(1))}" x2="${xToPx(1)}" y2="${yToPx(0)}" stroke="${NEGATIVE}" stroke-width="1.5" stroke-dasharray="4 3" />`);
  pieces.push(`<text x="${xToPx(1)}" y="${yToPx(fn(1)) - 16}" font="bold 13px system-ui" font-size="13" font-weight="700" fill="${NEGATIVE}" text-anchor="middle">resonance!</text>`);
  pieces.push(`<text x="${xToPx(1)}" y="${yToPx(0) + 36}" font="11px system-ui" font-size="11" fill="${NEGATIVE}" text-anchor="middle">f = f₀</text>`);

  // Annotations at low and high f
  pieces.push(`<text x="${xToPx(0.3)}" y="${yToPx(fn(0.3)) - 12}" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">tiny push at wrong rate</text>`);
  pieces.push(`<text x="${xToPx(3)}" y="${yToPx(fn(3)) - 12}" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">also small at high f</text>`);

  pieces.push(`<text x="${W / 2}" y="${H - 8}" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">Push a swing at its natural rhythm and it goes huge. Push at any other rate and it barely moves.</text>`);
  return svgWrap(W, H, "Resonance amplitude versus driving frequency curve", "A bell-shaped resonance curve plotting amplitude against driving frequency normalised to the natural frequency. A red marker peaks at f = f₀ labelled 'resonance!' Annotations at low and high frequency note the small response away from resonance.", pieces.join(""));
}

// ────────────────────────────────────────────────────────────────────────────
// Main
// ────────────────────────────────────────────────────────────────────────────

mkdirSync(ROOT, { recursive: true });

write("section-1-wave-basics/transverse-wave-anatomy.svg", s1_transverseAnatomy());
write("section-1-wave-basics/transverse-vs-longitudinal.svg", s1_transverseVsLongitudinal());
write("section-1-wave-basics/wave-equation-v-equals-f-lambda.svg", s1_waveEquation());

write("section-2-light-em-spectrum/em-spectrum-strip.svg", s2_emSpectrumStrip());
write("section-2-light-em-spectrum/visible-light-rainbow.svg", s2_visibleLightRainbow());
write("section-2-light-em-spectrum/light-vs-sound-comparison.svg", s2_lightVsSound());

write("section-3-sound-and-resonance/sound-wave-pressure-trace.svg", s3_soundPressureTrace());
write("section-3-sound-and-resonance/pitch-and-loudness.svg", s3_pitchAndLoudness());
write("section-3-sound-and-resonance/resonance-driving-frequency.svg", s3_resonance());

console.log("done — 9 SVGs");
