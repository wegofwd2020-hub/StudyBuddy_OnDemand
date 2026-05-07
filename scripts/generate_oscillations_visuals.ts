#!/usr/bin/env bun
/**
 * Generate the Option-2 SVG catalogue for G11-PHYS-010 Oscillations and Waves
 * (issue #327).
 *
 * Run from repo root:
 *   bun scripts/generate_oscillations_visuals.ts
 *
 * Output: sample_content/g11-science/G11-PHYS-010_Oscillations_and_Waves/Option2_Catalogue/section-N/*.svg
 *
 * Recipe is a direct lift from scripts/generate_kinematics_visuals.ts —
 * same makePlot helper shape, same colour palette, same fontless inline
 * styling so the SVGs render identically in the web reader, the admin
 * review queue, and the printed PDF.
 */

import { writeFileSync, mkdirSync } from "node:fs";
import { join, dirname } from "node:path";

const ROOT = join(
  import.meta.dir,
  "..",
  "sample_content",
  "g11-science",
  "G11-PHYS-010_Oscillations_and_Waves",
  "Option2_Catalogue",
);

// ── Styling tokens — match Kinematics catalogue ────────────────────────────

const INK = "#1a202c";
const MUTED = "#4a5568";
const ACCENT = "#2b6cb0";
const ACCENT_2 = "#dd6b20";
const ACCENT_3 = "#319795";
const POSITIVE = "#15803d";
const NEGATIVE = "#dc2626";
const GRID = "#e2e8f0";
const AXIS = "#94a3b8";
const BG = "#f7fafc";

// ── Plot helper ────────────────────────────────────────────────────────────

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

  pieces.push(`<line x1="${x0}" y1="${y0 + innerH}" x2="${x0 + innerW}" y2="${y0 + innerH}" stroke="${AXIS}" stroke-width="1.2" />`);
  pieces.push(`<line x1="${x0}" y1="${y0}" x2="${x0}" y2="${y0 + innerH}" stroke="${AXIS}" stroke-width="1.2" />`);

  pieces.push(`<text x="${x0 + innerW / 2}" y="${y0 + innerH + 32}" font="13px system-ui" font-size="13" font-weight="600" fill="${INK}" text-anchor="middle">${c.xLabel}</text>`);
  pieces.push(`<text x="${x0 - 32}" y="${y0 + innerH / 2}" font="13px system-ui" font-size="13" font-weight="600" fill="${INK}" text-anchor="middle" transform="rotate(-90 ${x0 - 32} ${y0 + innerH / 2})">${c.yLabel}</text>`);

  if (c.title) {
    pieces.push(`<text x="${x0 + innerW / 2}" y="${y0 - 10}" font="bold 14px system-ui" font-size="14" font-weight="700" fill="${INK}" text-anchor="middle">${c.title}</text>`);
  }

  return { pieces, xToPx, yToPx, innerW, innerH, x0, y0 };
}

function polyline(points: Array<[number, number]>, xToPx: (x: number) => number, yToPx: (y: number) => number, stroke: string, width = 2, dash?: string) {
  const pts = points.map(([x, y]) => `${xToPx(x).toFixed(2)},${yToPx(y).toFixed(2)}`).join(" ");
  const dashAttr = dash ? ` stroke-dasharray="${dash}"` : "";
  return `<polyline points="${pts}" fill="none" stroke="${stroke}" stroke-width="${width}" stroke-linecap="round"${dashAttr} />`;
}

function svgWrap(viewBox: string, title: string, desc: string, body: string) {
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="${viewBox}" width="${viewBox.split(" ")[2]}" height="${viewBox.split(" ")[3]}" role="img" aria-label="${title}">
  <title>${title}</title>
  <desc>${desc}</desc>
${body}
</svg>`;
}

function write(section: string, name: string, svg: string) {
  const dir = join(ROOT, section);
  mkdirSync(dir, { recursive: true });
  const file = join(dir, `${name}.svg`);
  writeFileSync(file, svg, "utf-8");
  console.log(`  ✓ ${section}/${name}.svg  (${svg.length} bytes)`);
}

// ── Section 1 — SHM kinematics ──────────────────────────────────────────────

function shmDisplacementTime() {
  const W = 540, H = 320;
  const A = 1, omega = 2 * Math.PI; // T = 1 s for clarity
  const samples = 200;
  const data: Array<[number, number]> = [];
  for (let i = 0; i <= samples; i++) {
    const t = (i / samples) * 3;
    data.push([t, A * Math.sin(omega * t)]);
  }

  const p = makePlot({
    width: W, height: H,
    pad: { l: 60, r: 30, t: 50, b: 50 },
    xRange: [0, 3], yRange: [-1.4, 1.4],
    xTicks: [0, 0.5, 1, 1.5, 2, 2.5, 3],
    yTicks: [-1, -0.5, 0, 0.5, 1],
    xLabel: "t (s)", yLabel: "y (m)",
    title: "SHM displacement: y(t) = A sin(ωt)",
  });

  const body: string[] = [...p.pieces];
  body.push(polyline(data, p.xToPx, p.yToPx, ACCENT, 2.5));

  // Mark amplitude
  body.push(`<line x1="${p.xToPx(0.25).toFixed(2)}" y1="${p.yToPx(0).toFixed(2)}" x2="${p.xToPx(0.25).toFixed(2)}" y2="${p.yToPx(1).toFixed(2)}" stroke="${ACCENT_2}" stroke-width="1.5" stroke-dasharray="3 3" />`);
  body.push(`<text x="${p.xToPx(0.27).toFixed(2)}" y="${p.yToPx(0.5).toFixed(2)}" font="11px system-ui" font-size="11" fill="${ACCENT_2}">A</text>`);

  // Mark period
  body.push(`<line x1="${p.xToPx(0).toFixed(2)}" y1="${p.yToPx(-1.2).toFixed(2)}" x2="${p.xToPx(1).toFixed(2)}" y2="${p.yToPx(-1.2).toFixed(2)}" stroke="${ACCENT_2}" stroke-width="1.5" />`);
  body.push(`<text x="${p.xToPx(0.5).toFixed(2)}" y="${p.yToPx(-1.3).toFixed(2)}" font="11px system-ui" font-size="11" fill="${ACCENT_2}" text-anchor="middle">T (period)</text>`);

  // Equilibrium line
  body.push(`<line x1="${p.x0}" y1="${p.yToPx(0).toFixed(2)}" x2="${p.x0 + p.innerW}" y2="${p.yToPx(0).toFixed(2)}" stroke="${MUTED}" stroke-width="0.6" stroke-dasharray="2 3" />`);

  return svgWrap(`0 0 ${W} ${H}`, "SHM displacement vs time",
    "Sine curve y(t) = A sin(ωt) showing amplitude A and period T, with the equilibrium line dashed.",
    body.join("\n"));
}

function shmYvaComparison() {
  const W = 600, H = 460;
  const A = 1, omega = 2 * Math.PI;
  const samples = 200;
  const ys: Array<[number, number]> = [];
  const vs: Array<[number, number]> = [];
  const as: Array<[number, number]> = [];
  for (let i = 0; i <= samples; i++) {
    const t = (i / samples) * 3;
    ys.push([t, A * Math.sin(omega * t)]);
    vs.push([t, A * omega * Math.cos(omega * t)]);
    as.push([t, -A * omega * omega * Math.sin(omega * t)]);
  }

  const body: string[] = [];
  body.push(`<text x="${W / 2}" y="22" font="bold 14px system-ui" font-size="14" font-weight="700" fill="${INK}" text-anchor="middle">SHM: y, v, a are 90° out of phase</text>`);
  body.push(`<text x="${W / 2}" y="40" font="11px system-ui" font-size="11" font-style="italic" fill="${MUTED}" text-anchor="middle">y leads, v lags by π/2, a is opposite to y</text>`);

  const plotH = 110, gap = 12;
  const stacks = [
    { data: ys, color: ACCENT, label: "y(t) = A sin(ωt)", yLabel: "y (m)", yRange: [-1.4, 1.4] as [number, number] },
    { data: vs, color: ACCENT_2, label: "v(t) = Aω cos(ωt)", yLabel: "v (m/s)", yRange: [-2 * Math.PI - 1, 2 * Math.PI + 1] as [number, number] },
    { data: as, color: NEGATIVE, label: "a(t) = -Aω² sin(ωt)", yLabel: "a (m/s²)", yRange: [-Math.pow(2 * Math.PI, 2) - 5, Math.pow(2 * Math.PI, 2) + 5] as [number, number] },
  ];

  let yOffset = 60;
  for (const s of stacks) {
    body.push(`<g transform="translate(0, ${yOffset})">`);
    const p = makePlot({
      width: W, height: plotH,
      pad: { l: 60, r: 30, t: 16, b: 26 },
      xRange: [0, 3], yRange: s.yRange,
      xTicks: [0, 0.5, 1, 1.5, 2, 2.5, 3],
      yTicks: [s.yRange[0], 0, s.yRange[1]].map((v) => Math.round(v * 10) / 10),
      xLabel: "t (s)", yLabel: s.yLabel,
    });
    body.push(...p.pieces);
    body.push(polyline(s.data, p.xToPx, p.yToPx, s.color, 2));
    body.push(`<text x="${W - 50}" y="${p.y0 + 14}" font="11px system-ui" font-size="11" font-weight="600" fill="${s.color}" text-anchor="end">${s.label}</text>`);
    body.push(`</g>`);
    yOffset += plotH + gap;
  }

  return svgWrap(`0 0 ${W} ${H}`, "SHM y v a 90 phase",
    "Three vertically-stacked plots of displacement, velocity, and acceleration vs time for SHM, showing the 90-degree phase relationships.",
    body.join("\n"));
}

// ── Section 2 — Energy + simple pendulum ───────────────────────────────────

function shmEnergyVsDisplacement() {
  const W = 540, H = 340;
  const A = 1, k = 1; // E_total = 0.5 k A^2 = 0.5
  const samples = 100;
  const ke: Array<[number, number]> = [];
  const pe: Array<[number, number]> = [];
  const tot: Array<[number, number]> = [];
  for (let i = 0; i <= samples; i++) {
    const x = -A + (2 * A * i) / samples;
    const peVal = 0.5 * k * x * x;
    const totVal = 0.5 * k * A * A;
    const keVal = totVal - peVal;
    pe.push([x, peVal]);
    ke.push([x, keVal]);
    tot.push([x, totVal]);
  }

  const p = makePlot({
    width: W, height: H,
    pad: { l: 60, r: 30, t: 50, b: 50 },
    xRange: [-1.2, 1.2], yRange: [0, 0.6],
    xTicks: [-1, -0.5, 0, 0.5, 1],
    yTicks: [0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6],
    xLabel: "x (m)", yLabel: "Energy (J)",
    title: "Energy in SHM: KE and PE complementary, total constant",
  });

  const body: string[] = [...p.pieces];
  body.push(polyline(tot, p.xToPx, p.yToPx, MUTED, 2, "5 4"));
  body.push(polyline(pe, p.xToPx, p.yToPx, ACCENT, 2.5));
  body.push(polyline(ke, p.xToPx, p.yToPx, NEGATIVE, 2.5));

  // Legend
  body.push(`<text x="${p.xToPx(0).toFixed(2)}" y="${p.yToPx(0.55).toFixed(2)}" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">total = ½kA²</text>`);
  body.push(`<text x="${p.xToPx(-0.95).toFixed(2)}" y="${p.yToPx(0.45).toFixed(2)}" font="11px system-ui" font-size="11" font-weight="600" fill="${ACCENT}">PE = ½kx²</text>`);
  body.push(`<text x="${p.xToPx(0).toFixed(2)}" y="${p.yToPx(0.42).toFixed(2)}" font="11px system-ui" font-size="11" font-weight="600" fill="${NEGATIVE}" text-anchor="middle">KE = ½k(A² − x²)</text>`);

  return svgWrap(`0 0 ${W} ${H}`, "Energy in SHM",
    "Kinetic and potential energy vs displacement in SHM, complementary parabolic curves summing to a constant total.",
    body.join("\n"));
}

function pendulumRestoringForce() {
  const W = 460, H = 380;
  const cx = 230, cy = 60;
  const L = 220;
  const theta = (28 * Math.PI) / 180;
  const bobx = cx + L * Math.sin(theta);
  const boby = cy + L * Math.cos(theta);

  const body: string[] = [];

  // Title
  body.push(`<text x="${W / 2}" y="22" font="bold 14px system-ui" font-size="14" font-weight="700" fill="${INK}" text-anchor="middle">Simple pendulum: restoring force = -mg sin θ</text>`);

  // Vertical reference line (equilibrium)
  body.push(`<line x1="${cx}" y1="${cy}" x2="${cx}" y2="${cy + L + 50}" stroke="${MUTED}" stroke-width="1" stroke-dasharray="3 4" />`);

  // String
  body.push(`<line x1="${cx}" y1="${cy}" x2="${bobx.toFixed(2)}" y2="${boby.toFixed(2)}" stroke="${INK}" stroke-width="2" />`);

  // Pivot
  body.push(`<circle cx="${cx}" cy="${cy}" r="5" fill="${INK}" />`);
  body.push(`<line x1="${cx - 30}" y1="${cy - 5}" x2="${cx + 30}" y2="${cy - 5}" stroke="${INK}" stroke-width="2" />`);

  // Bob
  body.push(`<circle cx="${bobx.toFixed(2)}" cy="${boby.toFixed(2)}" r="20" fill="${ACCENT}" stroke="${INK}" stroke-width="1.5" />`);

  // Angle arc
  const arcR = 50;
  body.push(`<path d="M ${cx} ${cy + arcR} A ${arcR} ${arcR} 0 0 0 ${(cx + arcR * Math.sin(theta)).toFixed(2)} ${(cy + arcR * Math.cos(theta)).toFixed(2)}" fill="none" stroke="${ACCENT_2}" stroke-width="1.5" />`);
  body.push(`<text x="${cx + 14}" y="${cy + arcR + 16}" font="12px system-ui" font-size="12" font-style="italic" fill="${ACCENT_2}">θ</text>`);

  // mg vector (down from bob)
  const mgLen = 90;
  body.push(`<line x1="${bobx.toFixed(2)}" y1="${boby.toFixed(2)}" x2="${bobx.toFixed(2)}" y2="${(boby + mgLen).toFixed(2)}" stroke="${NEGATIVE}" stroke-width="2" marker-end="url(#arrR)" />`);
  body.push(`<text x="${(bobx + 8).toFixed(2)}" y="${(boby + mgLen / 2 + 4).toFixed(2)}" font="12px system-ui" font-size="12" fill="${NEGATIVE}">mg</text>`);

  // Restoring component (perpendicular to string, towards equilibrium)
  // Perpendicular direction (rotate string -90°)
  const perpx = -Math.cos(theta), perpy = Math.sin(theta);
  const restLen = mgLen * Math.sin(theta);
  const restEndX = bobx + restLen * perpx;
  const restEndY = boby + restLen * perpy;
  body.push(`<line x1="${bobx.toFixed(2)}" y1="${boby.toFixed(2)}" x2="${restEndX.toFixed(2)}" y2="${restEndY.toFixed(2)}" stroke="${POSITIVE}" stroke-width="2.5" marker-end="url(#arrG)" />`);
  body.push(`<text x="${(restEndX - 36).toFixed(2)}" y="${(restEndY - 6).toFixed(2)}" font="12px system-ui" font-size="12" font-weight="600" fill="${POSITIVE}">−mg sin θ</text>`);

  // Tension along string (towards pivot)
  const tensionEndX = bobx - 60 * Math.sin(theta);
  const tensionEndY = boby - 60 * Math.cos(theta);
  body.push(`<line x1="${bobx.toFixed(2)}" y1="${boby.toFixed(2)}" x2="${tensionEndX.toFixed(2)}" y2="${tensionEndY.toFixed(2)}" stroke="${ACCENT_3}" stroke-width="2" marker-end="url(#arrT)" />`);
  body.push(`<text x="${(tensionEndX + 6).toFixed(2)}" y="${(tensionEndY - 4).toFixed(2)}" font="12px system-ui" font-size="12" fill="${ACCENT_3}">T</text>`);

  // Defs for arrowheads
  body.unshift(`<defs>
    <marker id="arrR" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto">
      <path d="M 0 0 L 8 4 L 0 8 z" fill="${NEGATIVE}" />
    </marker>
    <marker id="arrG" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto">
      <path d="M 0 0 L 8 4 L 0 8 z" fill="${POSITIVE}" />
    </marker>
    <marker id="arrT" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto">
      <path d="M 0 0 L 8 4 L 0 8 z" fill="${ACCENT_3}" />
    </marker>
  </defs>`);

  return svgWrap(`0 0 ${W} ${H}`, "Simple pendulum forces",
    "A pendulum bob displaced by angle theta with weight mg, tension T, and the tangential restoring component -mg sin theta annotated.",
    body.join("\n"));
}

// ── Section 3 — Wave properties ─────────────────────────────────────────────

function transverseVsLongitudinal() {
  const W = 720, H = 340;
  const body: string[] = [];

  body.push(`<text x="${W / 2}" y="22" font="bold 14px system-ui" font-size="14" font-weight="700" fill="${INK}" text-anchor="middle">Transverse vs Longitudinal waves</text>`);
  body.push(`<text x="${W / 2}" y="40" font="11px system-ui" font-size="11" font-style="italic" fill="${MUTED}" text-anchor="middle">particle motion is perpendicular (transverse) or parallel (longitudinal) to wave propagation</text>`);

  // Transverse — left side
  body.push(`<text x="180" y="74" font="bold 12px system-ui" font-size="12" font-weight="700" fill="${INK}" text-anchor="middle">Transverse (e.g. light, string wave)</text>`);
  // Sinusoidal curve representing a transverse wave on a string
  const transverseData: Array<[number, number]> = [];
  for (let i = 0; i <= 200; i++) {
    const x = i * 1.7; // 0..340
    const y = 30 * Math.sin((x / 340) * 4 * Math.PI);
    transverseData.push([x, y]);
  }
  const transverseSvg = transverseData.map(([x, y]) => `${(20 + x).toFixed(1)},${(170 + y).toFixed(1)}`).join(" ");
  body.push(`<polyline points="${transverseSvg}" fill="none" stroke="${ACCENT}" stroke-width="2.5" />`);
  // Direction arrow
  body.push(`<line x1="20" y1="240" x2="360" y2="240" stroke="${INK}" stroke-width="1.5" marker-end="url(#arrI)" />`);
  body.push(`<text x="190" y="260" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">wave direction →</text>`);
  // Particle motion indicator (vertical double-arrow)
  body.push(`<line x1="100" y1="120" x2="100" y2="220" stroke="${NEGATIVE}" stroke-width="2" stroke-dasharray="2 3" />`);
  body.push(`<polygon points="95,125 100,115 105,125" fill="${NEGATIVE}" />`);
  body.push(`<polygon points="95,215 100,225 105,215" fill="${NEGATIVE}" />`);
  body.push(`<text x="118" y="170" font="11px system-ui" font-size="11" fill="${NEGATIVE}">particle</text>`);
  body.push(`<text x="118" y="184" font="11px system-ui" font-size="11" fill="${NEGATIVE}">motion ↕</text>`);

  // Divider
  body.push(`<line x1="380" y1="60" x2="380" y2="280" stroke="${GRID}" stroke-width="1" />`);

  // Longitudinal — right side
  body.push(`<text x="540" y="74" font="bold 12px system-ui" font-size="12" font-weight="700" fill="${INK}" text-anchor="middle">Longitudinal (e.g. sound)</text>`);
  // Compression / rarefaction pattern: dots clustered at compressions
  const lx0 = 400, lx1 = 700;
  for (let i = 0; i < 60; i++) {
    const baseX = lx0 + ((lx1 - lx0) * i) / 60;
    const offset = 8 * Math.sin((i / 60) * 4 * Math.PI);
    body.push(`<circle cx="${(baseX + offset).toFixed(1)}" cy="170" r="3" fill="${ACCENT_2}" />`);
  }
  // Direction arrow
  body.push(`<line x1="${lx0}" y1="240" x2="${lx1}" y2="240" stroke="${INK}" stroke-width="1.5" marker-end="url(#arrI)" />`);
  body.push(`<text x="${(lx0 + lx1) / 2}" y="260" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">wave direction →</text>`);
  // Particle motion indicator (horizontal double-arrow)
  body.push(`<line x1="${lx0 + 120}" y1="195" x2="${lx0 + 200}" y2="195" stroke="${NEGATIVE}" stroke-width="2" stroke-dasharray="2 3" />`);
  body.push(`<polygon points="${lx0 + 115},190 ${lx0 + 125},195 ${lx0 + 115},200" fill="${NEGATIVE}" />`);
  body.push(`<polygon points="${lx0 + 205},190 ${lx0 + 195},195 ${lx0 + 205},200" fill="${NEGATIVE}" />`);
  body.push(`<text x="${lx0 + 160}" y="215" font="11px system-ui" font-size="11" fill="${NEGATIVE}" text-anchor="middle">particle motion ↔</text>`);

  body.push(`<text x="${(lx0 + 80)}" y="290" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">compression</text>`);
  body.push(`<text x="${(lx0 + 220)}" y="290" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">rarefaction</text>`);

  body.unshift(`<defs>
    <marker id="arrI" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto">
      <path d="M 0 0 L 8 4 L 0 8 z" fill="${INK}" />
    </marker>
  </defs>`);

  return svgWrap(`0 0 ${W} ${H}`, "Transverse vs longitudinal waves",
    "Side-by-side comparison: a transverse wave (sinusoidal) with vertical particle motion, and a longitudinal wave (compression-rarefaction) with horizontal particle motion. Both show wave direction arrows.",
    body.join("\n"));
}

function waveAnatomy() {
  const W = 600, H = 320;
  const A = 1;
  const samples = 200;
  const data: Array<[number, number]> = [];
  for (let i = 0; i <= samples; i++) {
    const x = (i / samples) * 4;
    data.push([x, A * Math.sin((x * Math.PI * 2) / 1.5)]);
  }

  const p = makePlot({
    width: W, height: H,
    pad: { l: 60, r: 30, t: 50, b: 50 },
    xRange: [0, 4], yRange: [-1.6, 1.6],
    xTicks: [0, 0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4],
    yTicks: [-1, -0.5, 0, 0.5, 1],
    xLabel: "x (m)", yLabel: "displacement",
    title: "Wave anatomy: amplitude, wavelength, period",
  });

  const body: string[] = [...p.pieces];
  body.push(polyline(data, p.xToPx, p.yToPx, ACCENT, 2.5));

  // Crest / trough markers
  body.push(`<circle cx="${p.xToPx(0.375).toFixed(2)}" cy="${p.yToPx(1).toFixed(2)}" r="4" fill="${POSITIVE}" />`);
  body.push(`<text x="${p.xToPx(0.375).toFixed(2)}" y="${(p.yToPx(1) - 8).toFixed(2)}" font="11px system-ui" font-size="11" fill="${POSITIVE}" text-anchor="middle">crest</text>`);
  body.push(`<circle cx="${p.xToPx(1.125).toFixed(2)}" cy="${p.yToPx(-1).toFixed(2)}" r="4" fill="${NEGATIVE}" />`);
  body.push(`<text x="${p.xToPx(1.125).toFixed(2)}" y="${(p.yToPx(-1) + 16).toFixed(2)}" font="11px system-ui" font-size="11" fill="${NEGATIVE}" text-anchor="middle">trough</text>`);

  // Wavelength bracket — between two crests
  const lambdaY = p.yToPx(1.35);
  body.push(`<line x1="${p.xToPx(0.375).toFixed(2)}" y1="${lambdaY.toFixed(2)}" x2="${p.xToPx(1.875).toFixed(2)}" y2="${lambdaY.toFixed(2)}" stroke="${ACCENT_2}" stroke-width="1.6" marker-start="url(#arrLeft2)" marker-end="url(#arrRight2)" />`);
  body.push(`<text x="${p.xToPx(1.125).toFixed(2)}" y="${(lambdaY - 5).toFixed(2)}" font="12px system-ui" font-size="12" font-weight="600" fill="${ACCENT_2}" text-anchor="middle">λ (wavelength)</text>`);

  // Amplitude marker
  body.push(`<line x1="${p.xToPx(2.5).toFixed(2)}" y1="${p.yToPx(0).toFixed(2)}" x2="${p.xToPx(2.5).toFixed(2)}" y2="${p.yToPx(1).toFixed(2)}" stroke="${POSITIVE}" stroke-width="1.6" marker-end="url(#arrTop2)" />`);
  body.push(`<text x="${(p.xToPx(2.5) + 8).toFixed(2)}" y="${p.yToPx(0.5).toFixed(2)}" font="12px system-ui" font-size="12" font-weight="600" fill="${POSITIVE}">A (amplitude)</text>`);

  body.unshift(`<defs>
    <marker id="arrLeft2" markerWidth="8" markerHeight="8" refX="2" refY="4" orient="auto">
      <path d="M 8 0 L 0 4 L 8 8 z" fill="${ACCENT_2}" />
    </marker>
    <marker id="arrRight2" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto">
      <path d="M 0 0 L 8 4 L 0 8 z" fill="${ACCENT_2}" />
    </marker>
    <marker id="arrTop2" markerWidth="8" markerHeight="8" refX="4" refY="2" orient="auto">
      <path d="M 0 8 L 4 0 L 8 8 z" fill="${POSITIVE}" />
    </marker>
  </defs>`);

  return svgWrap(`0 0 ${W} ${H}`, "Wave anatomy",
    "A sine wave with one crest, one trough, the wavelength between adjacent crests, and the amplitude from the equilibrium line to a crest, all labelled.",
    body.join("\n"));
}

// ── Section 4 — Superposition + standing waves ─────────────────────────────

function superpositionPlot(title: string, phase: number, name: string) {
  const W = 600, H = 360;
  const samples = 200;
  const w1: Array<[number, number]> = [];
  const w2: Array<[number, number]> = [];
  const sum: Array<[number, number]> = [];
  for (let i = 0; i <= samples; i++) {
    const x = (i / samples) * 4;
    const a = Math.sin(x * Math.PI);
    const b = Math.sin(x * Math.PI + phase);
    w1.push([x, a]);
    w2.push([x, b]);
    sum.push([x, a + b]);
  }

  const body: string[] = [];
  body.push(`<text x="${W / 2}" y="22" font="bold 14px system-ui" font-size="14" font-weight="700" fill="${INK}" text-anchor="middle">${title}</text>`);

  const plotH = 90, gap = 12;
  const stacks = [
    { data: w1, color: ACCENT, label: "wave 1", yRange: [-2.4, 2.4] as [number, number] },
    { data: w2, color: ACCENT_2, label: "wave 2", yRange: [-2.4, 2.4] as [number, number] },
    { data: sum, color: NEGATIVE, label: "sum (superposition)", yRange: [-2.4, 2.4] as [number, number] },
  ];

  let yOffset = 40;
  for (const s of stacks) {
    body.push(`<g transform="translate(0, ${yOffset})">`);
    const p = makePlot({
      width: W, height: plotH,
      pad: { l: 60, r: 30, t: 12, b: 22 },
      xRange: [0, 4], yRange: s.yRange,
      xTicks: [0, 1, 2, 3, 4],
      yTicks: [-2, 0, 2],
      xLabel: "x", yLabel: "y",
    });
    body.push(...p.pieces);
    body.push(polyline(s.data, p.xToPx, p.yToPx, s.color, 2));
    body.push(`<text x="${W - 50}" y="${p.y0 + 12}" font="11px system-ui" font-size="11" font-weight="600" fill="${s.color}" text-anchor="end">${s.label}</text>`);
    body.push(`</g>`);
    yOffset += plotH + gap;
  }

  return svgWrap(`0 0 ${W} ${H}`, name,
    "Three vertically-stacked plots showing two component waves and their superposition sum.",
    body.join("\n"));
}

function standingWaveModes() {
  const W = 660, H = 360;
  const body: string[] = [];

  body.push(`<text x="${W / 2}" y="22" font="bold 14px system-ui" font-size="14" font-weight="700" fill="${INK}" text-anchor="middle">Standing wave modes on a string fixed at both ends</text>`);
  body.push(`<text x="${W / 2}" y="40" font="11px system-ui" font-size="11" font-style="italic" fill="${MUTED}" text-anchor="middle">L = nλ/2 → fundamental (n=1), 2nd harmonic (n=2), 3rd harmonic (n=3)</text>`);

  const lx0 = 60, lx1 = 600, lW = lx1 - lx0;
  const stacks = [
    { n: 1, color: ACCENT, freq: "f₁ (fundamental)" },
    { n: 2, color: ACCENT_2, freq: "f₂ = 2f₁" },
    { n: 3, color: NEGATIVE, freq: "f₃ = 3f₁" },
  ];

  let yC = 80;
  for (const s of stacks) {
    // String baseline
    body.push(`<line x1="${lx0}" y1="${yC}" x2="${lx1}" y2="${yC}" stroke="${MUTED}" stroke-width="0.6" stroke-dasharray="3 3" />`);
    // Endpoints (fixed nodes)
    body.push(`<circle cx="${lx0}" cy="${yC}" r="4" fill="${INK}" />`);
    body.push(`<circle cx="${lx1}" cy="${yC}" r="4" fill="${INK}" />`);

    // Two envelope curves: ±sin(nπx/L) * 30
    const envTop: Array<[number, number]> = [];
    const envBot: Array<[number, number]> = [];
    for (let i = 0; i <= 200; i++) {
      const x = lx0 + (lW * i) / 200;
      const ux = (i / 200) * Math.PI * s.n;
      const y = 30 * Math.sin(ux);
      envTop.push([x, yC - y]);
      envBot.push([x, yC + y]);
    }
    body.push(`<polyline points="${envTop.map(([a, b]) => `${a.toFixed(1)},${b.toFixed(1)}`).join(" ")}" fill="none" stroke="${s.color}" stroke-width="2.5" />`);
    body.push(`<polyline points="${envBot.map(([a, b]) => `${a.toFixed(1)},${b.toFixed(1)}`).join(" ")}" fill="none" stroke="${s.color}" stroke-width="2.5" stroke-opacity="0.55" />`);

    // Internal nodes
    for (let k = 1; k < s.n; k++) {
      const nx = lx0 + (lW * k) / s.n;
      body.push(`<circle cx="${nx}" cy="${yC}" r="3" fill="${INK}" />`);
    }

    body.push(`<text x="${lx1 + 8}" y="${yC + 4}" font="12px system-ui" font-size="12" font-weight="600" fill="${s.color}">${s.freq}</text>`);
    body.push(`<text x="${lx0 - 10}" y="${yC + 4}" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="end">n=${s.n}</text>`);

    yC += 90;
  }

  // Legend
  body.push(`<text x="${W / 2}" y="${H - 18}" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">● node (zero amplitude)   • antinode (between nodes, max amplitude)</text>`);

  return svgWrap(`0 0 ${W} ${H}`, "Standing wave harmonics",
    "Three standing-wave modes on a string fixed at both ends — fundamental, second harmonic, third harmonic — with nodes marked.",
    body.join("\n"));
}

// ── Section 5 — Damped + resonance + Doppler ───────────────────────────────

function dampedOscillationComparison() {
  const W = 600, H = 340;
  const samples = 300;
  const omega = 2 * Math.PI;
  // Three damping coefficients
  const b_under = 0.4, b_crit = 2 * 1, b_over = 4; // mass=1, omega=2pi
  const make = (b: number, omega_d_factor: number, dampedSinusoid: boolean) => {
    const arr: Array<[number, number]> = [];
    for (let i = 0; i <= samples; i++) {
      const t = (i / samples) * 4;
      let y: number;
      if (dampedSinusoid) {
        const omega_d = omega * omega_d_factor;
        y = Math.exp(-b * t / 2) * Math.cos(omega_d * t);
      } else {
        // Critical / over: monotonic exponential decay (simplified)
        y = Math.exp(-b * t / 2) * (1 + (b > 3 ? 0.5 * t : 0.2 * t));
      }
      arr.push([t, y]);
    }
    return arr;
  };
  const under = make(b_under, 0.99, true);
  const crit = make(b_crit, 1, false);
  const over = make(b_over, 1, false);

  const p = makePlot({
    width: W, height: H,
    pad: { l: 60, r: 30, t: 50, b: 50 },
    xRange: [0, 4], yRange: [-1.4, 1.4],
    xTicks: [0, 1, 2, 3, 4],
    yTicks: [-1, -0.5, 0, 0.5, 1],
    xLabel: "t (s)", yLabel: "x(t)",
    title: "Damped oscillation: under-, critical-, and over-damped",
  });

  const body: string[] = [...p.pieces];
  body.push(polyline(under, p.xToPx, p.yToPx, ACCENT, 2.5));
  body.push(polyline(crit, p.xToPx, p.yToPx, POSITIVE, 2.5));
  body.push(polyline(over, p.xToPx, p.yToPx, NEGATIVE, 2.5));

  // Envelope for under-damped
  const env: Array<[number, number]> = [];
  for (let i = 0; i <= samples; i++) {
    const t = (i / samples) * 4;
    env.push([t, Math.exp(-b_under * t / 2)]);
  }
  body.push(polyline(env, p.xToPx, p.yToPx, MUTED, 1, "3 4"));

  // Legend
  body.push(`<rect x="${(p.x0 + p.innerW - 130)}" y="${p.y0 + 12}" width="120" height="60" fill="${BG}" stroke="${GRID}" />`);
  body.push(`<line x1="${(p.x0 + p.innerW - 122)}" y1="${p.y0 + 26}" x2="${(p.x0 + p.innerW - 100)}" y2="${p.y0 + 26}" stroke="${ACCENT}" stroke-width="2.5" />`);
  body.push(`<text x="${(p.x0 + p.innerW - 95)}" y="${p.y0 + 30}" font="10px system-ui" font-size="10" fill="${INK}">under-damped</text>`);
  body.push(`<line x1="${(p.x0 + p.innerW - 122)}" y1="${p.y0 + 42}" x2="${(p.x0 + p.innerW - 100)}" y2="${p.y0 + 42}" stroke="${POSITIVE}" stroke-width="2.5" />`);
  body.push(`<text x="${(p.x0 + p.innerW - 95)}" y="${p.y0 + 46}" font="10px system-ui" font-size="10" fill="${INK}">critical</text>`);
  body.push(`<line x1="${(p.x0 + p.innerW - 122)}" y1="${p.y0 + 58}" x2="${(p.x0 + p.innerW - 100)}" y2="${p.y0 + 58}" stroke="${NEGATIVE}" stroke-width="2.5" />`);
  body.push(`<text x="${(p.x0 + p.innerW - 95)}" y="${p.y0 + 62}" font="10px system-ui" font-size="10" fill="${INK}">over-damped</text>`);

  return svgWrap(`0 0 ${W} ${H}`, "Damping regimes comparison",
    "Three curves on the same axes showing under-damped (oscillating with decaying envelope), critically damped (fastest non-oscillating return), and over-damped (slow return) responses.",
    body.join("\n"));
}

function resonanceAmplitudeCurve() {
  const W = 540, H = 340;
  const omega0 = 1;
  const samples = 300;
  // Three damping levels showing increasing peak sharpness
  const make = (gamma: number) => {
    const arr: Array<[number, number]> = [];
    for (let i = 0; i <= samples; i++) {
      const omega = (i / samples) * 3;
      const denom = Math.sqrt((omega0 * omega0 - omega * omega) ** 2 + (gamma * omega) ** 2);
      const A = 1 / denom;
      arr.push([omega, A]);
    }
    return arr;
  };
  const lo = make(0.15);
  const med = make(0.4);
  const hi = make(0.9);

  const p = makePlot({
    width: W, height: H,
    pad: { l: 60, r: 30, t: 50, b: 50 },
    xRange: [0, 3], yRange: [0, 7],
    xTicks: [0, 0.5, 1, 1.5, 2, 2.5, 3],
    yTicks: [0, 1, 2, 3, 4, 5, 6, 7],
    xLabel: "driving ω / ω₀", yLabel: "amplitude (relative)",
    title: "Resonance: amplitude vs driving frequency",
  });

  const body: string[] = [...p.pieces];
  body.push(polyline(hi, p.xToPx, p.yToPx, ACCENT, 2));
  body.push(polyline(med, p.xToPx, p.yToPx, ACCENT_2, 2.5));
  body.push(polyline(lo, p.xToPx, p.yToPx, NEGATIVE, 2.5));

  // Mark omega_0
  body.push(`<line x1="${p.xToPx(1).toFixed(2)}" y1="${p.yToPx(0).toFixed(2)}" x2="${p.xToPx(1).toFixed(2)}" y2="${p.yToPx(7).toFixed(2)}" stroke="${MUTED}" stroke-width="1" stroke-dasharray="3 3" />`);
  body.push(`<text x="${p.xToPx(1).toFixed(2)}" y="${(p.yToPx(7) - 4).toFixed(2)}" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">ω = ω₀</text>`);

  // Legend
  body.push(`<text x="${(p.x0 + p.innerW - 8)}" y="${p.y0 + 18}" font="11px system-ui" font-size="11" font-weight="600" fill="${NEGATIVE}" text-anchor="end">low damping (sharp)</text>`);
  body.push(`<text x="${(p.x0 + p.innerW - 8)}" y="${p.y0 + 34}" font="11px system-ui" font-size="11" font-weight="600" fill="${ACCENT_2}" text-anchor="end">medium</text>`);
  body.push(`<text x="${(p.x0 + p.innerW - 8)}" y="${p.y0 + 50}" font="11px system-ui" font-size="11" font-weight="600" fill="${ACCENT}" text-anchor="end">high (broad)</text>`);

  return svgWrap(`0 0 ${W} ${H}`, "Resonance curve",
    "Steady-state amplitude of a driven oscillator vs driving frequency, three curves at increasing damping showing a sharper-to-broader peak around the natural frequency omega-zero.",
    body.join("\n"));
}

function dopplerSourceApproaching() {
  const W = 720, H = 340;
  const body: string[] = [];

  body.push(`<text x="${W / 2}" y="22" font="bold 14px system-ui" font-size="14" font-weight="700" fill="${INK}" text-anchor="middle">Doppler effect: source moving towards observer</text>`);
  body.push(`<text x="${W / 2}" y="40" font="11px system-ui" font-size="11" font-style="italic" fill="${MUTED}" text-anchor="middle">wavefronts ahead are compressed (higher frequency); behind, rarefied (lower)</text>`);

  const cx = 380, cy = 180;
  // Successive wavefronts emitted at past times t1, t2, t3, ... (source has moved between emissions)
  // Compressed forward (positive x direction)
  const fronts = [
    { srcX: cx - 120, r: 130 }, // earliest
    { srcX: cx - 80, r: 95 },
    { srcX: cx - 40, r: 60 },
    { srcX: cx, r: 25 },        // most recent
  ];
  for (const f of fronts) {
    body.push(`<circle cx="${f.srcX}" cy="${cy}" r="${f.r}" fill="none" stroke="${ACCENT}" stroke-width="1.6" />`);
  }
  // Source (moving)
  body.push(`<circle cx="${cx}" cy="${cy}" r="9" fill="${NEGATIVE}" stroke="${INK}" stroke-width="1.5" />`);
  body.push(`<text x="${cx}" y="${cy + 30}" font="11px system-ui" font-size="11" font-weight="600" fill="${NEGATIVE}" text-anchor="middle">source</text>`);
  // Velocity arrow
  body.push(`<line x1="${cx + 14}" y1="${cy}" x2="${cx + 70}" y2="${cy}" stroke="${NEGATIVE}" stroke-width="2.2" marker-end="url(#arrR3)" />`);
  body.push(`<text x="${cx + 42}" y="${cy - 8}" font="11px system-ui" font-size="11" font-weight="600" fill="${NEGATIVE}" text-anchor="middle">v_s</text>`);

  // Observer (stationary, in front)
  const obsX = cx + 200;
  body.push(`<polygon points="${obsX},${cy - 12} ${obsX - 12},${cy + 12} ${obsX + 12},${cy + 12}" fill="${POSITIVE}" stroke="${INK}" stroke-width="1.5" />`);
  body.push(`<text x="${obsX}" y="${cy + 30}" font="11px system-ui" font-size="11" font-weight="600" fill="${POSITIVE}" text-anchor="middle">observer</text>`);
  body.push(`<text x="${obsX}" y="${cy + 44}" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">(higher pitch)</text>`);

  // Behind-source observer (lower pitch)
  const bhX = cx - 290;
  body.push(`<polygon points="${bhX},${cy - 12} ${bhX - 12},${cy + 12} ${bhX + 12},${cy + 12}" fill="${ACCENT_2}" stroke="${INK}" stroke-width="1.5" />`);
  body.push(`<text x="${bhX}" y="${cy + 30}" font="11px system-ui" font-size="11" font-weight="600" fill="${ACCENT_2}" text-anchor="middle">observer</text>`);
  body.push(`<text x="${bhX}" y="${cy + 44}" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">(lower pitch)</text>`);

  // Formula
  body.push(`<text x="${W / 2}" y="${H - 18}" font="12px system-ui" font-size="12" font-weight="600" fill="${INK}" text-anchor="middle">f' = f · (v ± v_o) / (v ∓ v_s)   (top signs: source approaching observer)</text>`);

  body.unshift(`<defs>
    <marker id="arrR3" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto">
      <path d="M 0 0 L 8 4 L 0 8 z" fill="${NEGATIVE}" />
    </marker>
  </defs>`);

  return svgWrap(`0 0 ${W} ${H}`, "Doppler effect approaching",
    "A moving source emits successive circular wavefronts. The wavefronts ahead of the source are compressed (heard higher); the wavefronts behind are spread out (heard lower).",
    body.join("\n"));
}

// ── Driver ───────────────────────────────────────────────────────────────────

function main() {
  console.log(`Generating Option-2 catalogue for G11-PHYS-010 → ${ROOT}`);

  write("section-1-shm-kinematics", "shm-displacement-time", shmDisplacementTime());
  write("section-1-shm-kinematics", "shm-y-v-a-comparison", shmYvaComparison());

  write("section-2-energy-pendulum", "shm-energy-vs-displacement", shmEnergyVsDisplacement());
  write("section-2-energy-pendulum", "simple-pendulum-restoring-force", pendulumRestoringForce());

  write("section-3-wave-properties", "transverse-vs-longitudinal", transverseVsLongitudinal());
  write("section-3-wave-properties", "wave-anatomy", waveAnatomy());

  write("section-4-superposition", "superposition-constructive",
    superpositionPlot("Constructive interference (in phase, sum doubles amplitude)", 0, "Constructive superposition"));
  write("section-4-superposition", "superposition-destructive",
    superpositionPlot("Destructive interference (180° out of phase, sum cancels)", Math.PI, "Destructive superposition"));
  write("section-4-superposition", "standing-wave-modes", standingWaveModes());

  write("section-5-damping-doppler", "damped-oscillation-comparison", dampedOscillationComparison());
  write("section-5-damping-doppler", "resonance-amplitude-curve", resonanceAmplitudeCurve());
  write("section-5-damping-doppler", "doppler-source-approaching", dopplerSourceApproaching());

  console.log("\n✓ 12 SVGs generated.");
}

main();
