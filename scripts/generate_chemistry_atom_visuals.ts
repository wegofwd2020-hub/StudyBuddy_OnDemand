#!/usr/bin/env bun
/**
 * Generate the Option-2 SVG catalogue for G11-CHEM-002 Structure of Atom
 * (issue #329).
 *
 * Run from repo root:
 *   bun scripts/generate_chemistry_atom_visuals.ts
 *
 * Output: sample_content/g11-science/G11-CHEM-002_Structure_of_Atom/Option2_Catalogue/section-N/*.svg
 *
 * This unit opens the chemistry primitive set. Helpers lifted from
 * generate_kinematics_visuals.ts; chemistry-specific drawing primitives
 * (orbitals, Bohr shells, energy levels, particle markers) are defined inline.
 */

import { writeFileSync, mkdirSync } from "node:fs";
import { join, dirname } from "node:path";

const ROOT = join(
  import.meta.dir,
  "..",
  "sample_content",
  "g11-science",
  "G11-CHEM-002_Structure_of_Atom",
  "Option2_Catalogue",
);

// Style tokens lifted to pipeline/visual_templates/shared.ts (#341 phase A).
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

// Particle palette
const PROTON = "#dc2626";    // red
const NEUTRON = "#64748b";   // slate
const ELECTRON = "#2b6cb0";  // blue
const PHOTON = "#facc15";    // yellow

// ── Helpers ─────────────────────────────────────────────────────────────────

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
// SECTION 1 — Discovery & Subatomic Particles (3 SVGs)
// ────────────────────────────────────────────────────────────────────────────

function s1_cathodeRay() {
  const W = 540, H = 320;
  const body = `
  <defs>
    <marker id="cr-beam-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="9" markerHeight="9" orient="auto">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="${ACCENT}" />
    </marker>
  </defs>

  <text x="${W / 2}" y="22" font="bold 14px system-ui" font-size="14" font-weight="700" fill="${INK}" text-anchor="middle">Thomson's Cathode-Ray Experiment</text>

  <!-- Glass tube outline -->
  <rect x="60" y="80" width="420" height="180" rx="14" ry="14" fill="${BG}" stroke="${INK}" stroke-width="2" />

  <!-- Cathode (left) -->
  <rect x="50" y="155" width="20" height="30" fill="${NEGATIVE}" stroke="${INK}" stroke-width="1.5" />
  <text x="60" y="220" font="bold 11px system-ui" font-size="11" font-weight="700" fill="${NEGATIVE}" text-anchor="middle">cathode (−)</text>

  <!-- Anode (right of cathode) -->
  <rect x="125" y="160" width="6" height="20" fill="${MUTED}" />
  <text x="128" y="200" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">anode</text>

  <!-- Deflection plates -->
  <rect x="240" y="100" width="60" height="10" fill="${POSITIVE}" stroke="${INK}" stroke-width="1" />
  <text x="270" y="96" font="bold 11px system-ui" font-size="11" font-weight="700" fill="${POSITIVE}" text-anchor="middle">+ plate</text>
  <rect x="240" y="230" width="60" height="10" fill="${NEGATIVE}" stroke="${INK}" stroke-width="1" />
  <text x="270" y="258" font="bold 11px system-ui" font-size="11" font-weight="700" fill="${NEGATIVE}" text-anchor="middle">− plate</text>

  <!-- Undeflected (dotted) beam path -->
  <line x1="70" y1="170" x2="450" y2="170" stroke="${MUTED}" stroke-width="1.5" stroke-dasharray="4 4" />
  <text x="430" y="186" font="10px system-ui" font-size="10" fill="${MUTED}" text-anchor="middle">no field</text>

  <!-- Deflected beam path (curves up toward + plate) -->
  <path d="M 70 170 L 240 170 Q 290 170, 320 142 L 460 110" fill="none" stroke="${ACCENT}" stroke-width="3" marker-end="url(#cr-beam-arrow)" />

  <!-- Phosphorescent screen -->
  <line x1="465" y1="80" x2="465" y2="260" stroke="${ACCENT_3}" stroke-width="3" />
  <text x="465" y="278" font="11px system-ui" font-size="11" fill="${ACCENT_3}" text-anchor="middle">screen</text>
  <circle cx="465" cy="110" r="6" fill="${ACCENT}" opacity="0.9" />

  <!-- Caption -->
  <text x="${W / 2}" y="300" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">Negatively-charged particles bend toward the + plate → cathode rays carry negative charge → these are electrons.</text>
`;
  return svgWrap(W, H, "Thomson cathode-ray experiment", "Cathode-ray tube with cathode at left, anode, and a pair of horizontal deflection plates. The beam from the cathode bends upward toward the positive plate, identifying the rays as negatively-charged particles (electrons).", body);
}

function s1_rutherfordGoldFoil() {
  const W = 520, H = 320;
  const body = `
  <defs>
    <marker id="ru-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="${ACCENT_2}" />
    </marker>
  </defs>

  <text x="${W / 2}" y="22" font="bold 14px system-ui" font-size="14" font-weight="700" fill="${INK}" text-anchor="middle">Rutherford's Gold-Foil Experiment</text>

  <!-- Alpha source -->
  <rect x="40" y="135" width="56" height="56" rx="6" fill="${BG}" stroke="${INK}" stroke-width="2" />
  <text x="68" y="155" font="bold 11px system-ui" font-size="11" font-weight="700" fill="${INK}" text-anchor="middle">α source</text>
  <text x="68" y="170" font="9px system-ui" font-size="9" fill="${MUTED}" text-anchor="middle">(radium)</text>
  <text x="68" y="184" font="9px system-ui" font-size="9" fill="${POSITIVE}" text-anchor="middle">+2 charge</text>

  <!-- Gold foil -->
  <line x1="220" y1="80" x2="220" y2="240" stroke="${ACCENT_2}" stroke-width="6" />
  <text x="220" y="68" font="bold 11px system-ui" font-size="11" font-weight="700" fill="${ACCENT_2}" text-anchor="middle">gold foil</text>

  <!-- Alpha particle paths -->
  <!-- Most pass straight through -->
  <line x1="100" y1="155" x2="460" y2="155" stroke="${ACCENT}" stroke-width="2" marker-end="url(#ru-arrow)" />
  <line x1="100" y1="170" x2="460" y2="170" stroke="${ACCENT}" stroke-width="2" marker-end="url(#ru-arrow)" />
  <line x1="100" y1="140" x2="460" y2="140" stroke="${ACCENT}" stroke-width="2" marker-end="url(#ru-arrow)" />
  <!-- Slight deflection -->
  <path d="M 100 120 L 220 120 L 460 95" fill="none" stroke="${ACCENT}" stroke-width="2" marker-end="url(#ru-arrow)" />
  <path d="M 100 195 L 220 195 L 460 215" fill="none" stroke="${ACCENT}" stroke-width="2" marker-end="url(#ru-arrow)" />
  <!-- Strong back-scatter (the "rare event") -->
  <path d="M 100 105 L 220 165 Q 200 165, 110 75" fill="none" stroke="${NEGATIVE}" stroke-width="2.5" marker-end="url(#ru-arrow)" />

  <!-- Detector screen (curved) -->
  <path d="M 470 60 Q 510 160, 470 260" fill="none" stroke="${MUTED}" stroke-width="2" stroke-dasharray="6 4" />
  <text x="492" y="160" font="10px system-ui" font-size="10" fill="${MUTED}" text-anchor="middle" transform="rotate(90 492 160)">detector</text>

  <!-- Annotations -->
  <text x="280" y="155" font="bold 11px system-ui" font-size="11" font-weight="700" fill="${ACCENT}" text-anchor="middle">most pass through</text>
  <text x="120" y="60" font="bold 11px system-ui" font-size="11" font-weight="700" fill="${NEGATIVE}">a few bounce back!</text>
  <text x="${W / 2}" y="298" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">Most α particles pass through nearly empty space; a tiny fraction recoil → atoms have a small, dense, positive nucleus.</text>
`;
  return svgWrap(W, H, "Rutherford gold-foil experiment", "Alpha particle source on the left fires a beam at a thin gold foil. Most particles pass nearly straight through (showing the atom is mostly empty space); a small fraction are deflected at large angles or bounce back, indicating a tiny dense positive nucleus.", body);
}

function s1_subatomicParticles() {
  const W = 540, H = 280;
  const body = `
  <text x="${W / 2}" y="22" font="bold 14px system-ui" font-size="14" font-weight="700" fill="${INK}" text-anchor="middle">Subatomic Particles — At a Glance</text>

  <!-- Three columns -->
  <!-- Proton -->
  <g transform="translate(60, 70)">
    <rect x="0" y="0" width="130" height="180" rx="10" fill="${BG}" stroke="${PROTON}" stroke-width="2" />
    <circle cx="65" cy="42" r="22" fill="${PROTON}" stroke="${INK}" stroke-width="2" />
    <text x="65" y="48" font="bold 16px system-ui" font-size="16" font-weight="700" fill="white" text-anchor="middle">p⁺</text>
    <text x="65" y="86" font="bold 14px system-ui" font-size="14" font-weight="700" fill="${INK}" text-anchor="middle">Proton</text>
    <text x="65" y="108" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">charge: +1</text>
    <text x="65" y="126" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">mass: 1 u</text>
    <text x="65" y="146" font="10px system-ui" font-size="10" fill="${MUTED}" text-anchor="middle">in nucleus</text>
    <text x="65" y="164" font="bold 10px system-ui" font-size="10" font-weight="700" fill="${PROTON}" text-anchor="middle">defines element</text>
  </g>

  <!-- Neutron -->
  <g transform="translate(205, 70)">
    <rect x="0" y="0" width="130" height="180" rx="10" fill="${BG}" stroke="${NEUTRON}" stroke-width="2" />
    <circle cx="65" cy="42" r="22" fill="${NEUTRON}" stroke="${INK}" stroke-width="2" />
    <text x="65" y="48" font="bold 16px system-ui" font-size="16" font-weight="700" fill="white" text-anchor="middle">n⁰</text>
    <text x="65" y="86" font="bold 14px system-ui" font-size="14" font-weight="700" fill="${INK}" text-anchor="middle">Neutron</text>
    <text x="65" y="108" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">charge: 0</text>
    <text x="65" y="126" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">mass: 1 u</text>
    <text x="65" y="146" font="10px system-ui" font-size="10" fill="${MUTED}" text-anchor="middle">in nucleus</text>
    <text x="65" y="164" font="bold 10px system-ui" font-size="10" font-weight="700" fill="${NEUTRON}" text-anchor="middle">defines isotope</text>
  </g>

  <!-- Electron -->
  <g transform="translate(350, 70)">
    <rect x="0" y="0" width="130" height="180" rx="10" fill="${BG}" stroke="${ELECTRON}" stroke-width="2" />
    <circle cx="65" cy="42" r="14" fill="${ELECTRON}" stroke="${INK}" stroke-width="2" />
    <text x="65" y="47" font="bold 13px system-ui" font-size="13" font-weight="700" fill="white" text-anchor="middle">e⁻</text>
    <text x="65" y="86" font="bold 14px system-ui" font-size="14" font-weight="700" fill="${INK}" text-anchor="middle">Electron</text>
    <text x="65" y="108" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">charge: −1</text>
    <text x="65" y="126" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">mass: 1/1836 u</text>
    <text x="65" y="146" font="10px system-ui" font-size="10" fill="${MUTED}" text-anchor="middle">in shells</text>
    <text x="65" y="164" font="bold 10px system-ui" font-size="10" font-weight="700" fill="${ELECTRON}" text-anchor="middle">does the chemistry</text>
  </g>

  <text x="${W / 2}" y="270" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">Three particles. Two live in the nucleus, one orbits. Charges add: a neutral atom has equal protons and electrons.</text>
`;
  return svgWrap(W, H, "Subatomic particles comparison", "Three labeled cards comparing proton (positive, in nucleus, defines element), neutron (neutral, in nucleus, defines isotope), and electron (negative, much lighter, in shells, does the chemistry).", body);
}

// ────────────────────────────────────────────────────────────────────────────
// SECTION 2 — Atomic Models (3 SVGs)
// ────────────────────────────────────────────────────────────────────────────

function s2_thomsonPlumPudding() {
  const W = 480, H = 280;
  const cx = 240, cy = 160, R = 90;
  // Six electrons embedded inside the positive sphere
  const electrons = [
    { x: cx - 40, y: cy - 30 },
    { x: cx + 30, y: cy - 50 },
    { x: cx - 60, y: cy + 20 },
    { x: cx + 50, y: cy + 30 },
    { x: cx - 10, y: cy + 50 },
    { x: cx + 10, y: cy - 10 },
    { x: cx - 25, y: cy - 60 },
    { x: cx + 60, y: cy - 5 },
  ];
  let body = `
  <text x="${W / 2}" y="22" font="bold 14px system-ui" font-size="14" font-weight="700" fill="${INK}" text-anchor="middle">Thomson's "Plum-Pudding" Model (1904)</text>
  <text x="${W / 2}" y="40" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">A diffuse positive sphere with electrons embedded throughout, like raisins in a pudding.</text>

  <circle cx="${cx}" cy="${cy}" r="${R}" fill="${PROTON}" opacity="0.18" stroke="${PROTON}" stroke-width="2" />
  <text x="${cx + R + 8}" y="${cy + 4}" font="bold 11px system-ui" font-size="11" font-weight="700" fill="${PROTON}">+ + + + +</text>
  <text x="${cx + R + 8}" y="${cy + 22}" font="10px system-ui" font-size="10" fill="${MUTED}">diffuse + charge</text>
`;
  for (const e of electrons) {
    body += `<circle cx="${e.x}" cy="${e.y}" r="7" fill="${ELECTRON}" stroke="${INK}" stroke-width="1.2" />`;
  }
  body += `
  <text x="${cx - R - 8}" y="${cy + 4}" font="bold 11px system-ui" font-size="11" font-weight="700" fill="${ELECTRON}" text-anchor="end">e⁻ e⁻ e⁻</text>
  <text x="${cx - R - 8}" y="${cy + 22}" font="10px system-ui" font-size="10" fill="${MUTED}" text-anchor="end">embedded electrons</text>
  <text x="${W / 2}" y="270" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">Refuted by Rutherford's gold-foil experiment — the atom isn't a uniform sphere of charge.</text>
`;
  return svgWrap(W, H, "Thomson plum-pudding model", "A diffuse positive sphere with eight small negative electrons embedded throughout, illustrating Thomson's 1904 plum-pudding model of the atom.", body);
}

function s2_rutherfordNuclear() {
  const W = 480, H = 280;
  const cx = 240, cy = 160;
  const orbitR = 90;
  let body = `
  <text x="${W / 2}" y="22" font="bold 14px system-ui" font-size="14" font-weight="700" fill="${INK}" text-anchor="middle">Rutherford's Nuclear Model (1911)</text>
  <text x="${W / 2}" y="40" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">A tiny dense positive nucleus surrounded by mostly empty space with electrons orbiting like planets.</text>

  <!-- Orbit -->
  <ellipse cx="${cx}" cy="${cy}" rx="${orbitR}" ry="${orbitR * 0.95}" fill="none" stroke="${MUTED}" stroke-width="1.2" stroke-dasharray="4 4" />
  <ellipse cx="${cx}" cy="${cy}" rx="${orbitR + 30}" ry="${(orbitR + 30) * 0.95}" fill="none" stroke="${MUTED}" stroke-width="1.2" stroke-dasharray="4 4" />

  <!-- Tiny dense nucleus (overstated for visibility, real ratio ~10^-5) -->
  <circle cx="${cx}" cy="${cy}" r="14" fill="${PROTON}" stroke="${INK}" stroke-width="2" />
  <text x="${cx}" y="${cy + 4}" font="bold 11px system-ui" font-size="11" font-weight="700" fill="white" text-anchor="middle">+</text>
  <text x="${cx}" y="${cy + 32}" font="bold 11px system-ui" font-size="11" font-weight="700" fill="${PROTON}" text-anchor="middle">nucleus</text>
  <text x="${cx}" y="${cy + 48}" font="10px system-ui" font-size="10" fill="${MUTED}" text-anchor="middle">~99.9% of mass</text>

  <!-- Electrons on orbits -->
  <circle cx="${cx + orbitR}" cy="${cy}" r="7" fill="${ELECTRON}" stroke="${INK}" stroke-width="1.2" />
  <circle cx="${cx - orbitR * 0.7}" cy="${cy + orbitR * 0.7}" r="7" fill="${ELECTRON}" stroke="${INK}" stroke-width="1.2" />
  <circle cx="${cx - (orbitR + 30) * 0.5}" cy="${cy - (orbitR + 30) * 0.85}" r="7" fill="${ELECTRON}" stroke="${INK}" stroke-width="1.2" />
  <circle cx="${cx + (orbitR + 30) * 0.85}" cy="${cy - (orbitR + 30) * 0.5}" r="7" fill="${ELECTRON}" stroke="${INK}" stroke-width="1.2" />

  <!-- Empty-space callout -->
  <text x="80" y="120" font="bold 11px system-ui" font-size="11" font-weight="700" fill="${MUTED}">mostly empty space</text>

  <text x="${W / 2}" y="268" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">Problem: classically, an orbiting electron should radiate energy and spiral into the nucleus.</text>
`;
  return svgWrap(W, H, "Rutherford nuclear model", "A small dense red nucleus at center surrounded by two dashed orbital paths. Four small blue electrons sit on the orbits at various positions, illustrating the planetary atomic model.", body);
}

function s2_bohrShellModel() {
  const W = 520, H = 320;
  const cx = 260, cy = 175;
  const shellRadii = [50, 95, 145];
  const shellLabels = ["K (n=1)", "L (n=2)", "M (n=3)"];
  const shellElectrons = [2, 8, 5]; // example: phosphorus-like
  let body = `
  <text x="${W / 2}" y="22" font="bold 14px system-ui" font-size="14" font-weight="700" fill="${INK}" text-anchor="middle">Bohr Shell Model</text>
  <text x="${W / 2}" y="40" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">Electrons occupy specific quantized circular shells. Higher n = farther from the nucleus and higher energy.</text>
`;
  // Shells (concentric circles)
  for (let i = 0; i < shellRadii.length; i++) {
    body += `<circle cx="${cx}" cy="${cy}" r="${shellRadii[i]}" fill="none" stroke="${MUTED}" stroke-width="1.2" stroke-dasharray="4 3" />`;
    body += `<text x="${cx + shellRadii[i] + 4}" y="${cy + 4}" font="11px system-ui" font-size="11" fill="${MUTED}">${shellLabels[i]}</text>`;
  }
  // Nucleus
  body += `
  <circle cx="${cx}" cy="${cy}" r="20" fill="${PROTON}" stroke="${INK}" stroke-width="2" />
  <text x="${cx}" y="${cy + 5}" font="bold 12px system-ui" font-size="12" font-weight="700" fill="white" text-anchor="middle">nucleus</text>
`;
  // Electrons on each shell
  for (let s = 0; s < shellRadii.length; s++) {
    const r = shellRadii[s];
    const N = shellElectrons[s];
    for (let k = 0; k < N; k++) {
      const ang = (2 * Math.PI * k) / N + (s * 0.2);
      const ex = cx + r * Math.cos(ang);
      const ey = cy + r * Math.sin(ang);
      body += `<circle cx="${ex.toFixed(1)}" cy="${ey.toFixed(1)}" r="6" fill="${ELECTRON}" stroke="${INK}" stroke-width="1" />`;
    }
  }
  body += `
  <!-- Energy ladder on the right -->
  <g transform="translate(420, 60)">
    <text x="0" y="0" font="bold 11px system-ui" font-size="11" font-weight="700" fill="${INK}">Energy</text>
    <line x1="-2" y1="20" x2="60" y2="20" stroke="${MUTED}" stroke-width="2" />
    <text x="64" y="24" font="10px system-ui" font-size="10" fill="${MUTED}">n = 1</text>
    <line x1="-2" y1="80" x2="60" y2="80" stroke="${MUTED}" stroke-width="2" />
    <text x="64" y="84" font="10px system-ui" font-size="10" fill="${MUTED}">n = 2</text>
    <line x1="-2" y1="160" x2="60" y2="160" stroke="${MUTED}" stroke-width="2" />
    <text x="64" y="164" font="10px system-ui" font-size="10" fill="${MUTED}">n = 3</text>
    <line x1="0" y1="0" x2="0" y2="180" stroke="${INK}" stroke-width="1" marker-end="url(#energy-arr)" />
  </g>
  <defs>
    <marker id="energy-arr" viewBox="0 0 10 10" refX="5" refY="0" markerWidth="6" markerHeight="6" orient="auto">
      <path d="M 0 10 L 5 0 L 10 10 z" fill="${INK}" />
    </marker>
  </defs>

  <text x="${W / 2}" y="305" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">Electrons can only occupy shells; jumping between shells absorbs or emits a photon of fixed energy.</text>
`;
  return svgWrap(W, H, "Bohr shell model", "An atom diagram with three concentric quantized shells (K, L, M for n = 1, 2, 3). The nucleus sits at center; 2 electrons fill the K shell, 8 fill L, 5 fill M (phosphorus-like). A simplified energy-ladder shows the n = 1, 2, 3 levels rising vertically.", body);
}

// ────────────────────────────────────────────────────────────────────────────
// SECTION 3 — Quantum Mechanics & Orbitals (4 SVGs)
// ────────────────────────────────────────────────────────────────────────────

function s3_sOrbital() {
  const W = 360, H = 320;
  const cx = 180, cy = 165;
  const body = `
  <text x="${W / 2}" y="22" font="bold 14px system-ui" font-size="14" font-weight="700" fill="${INK}" text-anchor="middle">s Orbital — Spherical</text>

  <!-- Nucleus marker -->
  <circle cx="${cx}" cy="${cy}" r="3" fill="${INK}" />
  <text x="${cx + 8}" y="${cy + 4}" font="10px system-ui" font-size="10" fill="${MUTED}">nucleus</text>

  <!-- Spherical electron cloud (radial gradient) -->
  <defs>
    <radialGradient id="s-orbital-grad" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="${ACCENT}" stop-opacity="0.9" />
      <stop offset="60%" stop-color="${ACCENT}" stop-opacity="0.4" />
      <stop offset="100%" stop-color="${ACCENT}" stop-opacity="0" />
    </radialGradient>
  </defs>
  <circle cx="${cx}" cy="${cy}" r="100" fill="url(#s-orbital-grad)" />
  <circle cx="${cx}" cy="${cy}" r="100" fill="none" stroke="${ACCENT}" stroke-width="1.5" stroke-dasharray="3 4" />

  <!-- Axes -->
  <line x1="${cx - 130}" y1="${cy}" x2="${cx + 130}" y2="${cy}" stroke="${MUTED}" stroke-width="1" />
  <line x1="${cx}" y1="${cy - 130}" x2="${cx}" y2="${cy + 130}" stroke="${MUTED}" stroke-width="1" />
  <text x="${cx + 135}" y="${cy + 4}" font="11px system-ui" font-size="11" fill="${MUTED}">x</text>
  <text x="${cx + 4}" y="${cy - 132}" font="11px system-ui" font-size="11" fill="${MUTED}">y</text>

  <text x="${W / 2}" y="290" font="bold 12px system-ui" font-size="12" font-weight="700" fill="${ACCENT}" text-anchor="middle">l = 0 · holds 2 electrons · 1s, 2s, 3s, ...</text>
  <text x="${W / 2}" y="306" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">Probability of finding the electron is the same in every direction.</text>
`;
  return svgWrap(W, H, "s orbital — spherical shape", "A spherically-symmetric electron cloud rendered with radial-gradient fading from a dense centre to a faint edge. Caption notes l = 0, holds 2 electrons, examples 1s, 2s, 3s, with an isotropic probability description.", body);
}

function s3_pOrbitals() {
  const W = 600, H = 280;
  // Three dumbbells along x, y, z axes
  let body = `
  <text x="${W / 2}" y="22" font="bold 14px system-ui" font-size="14" font-weight="700" fill="${INK}" text-anchor="middle">p Orbitals — Three Dumbbells</text>
  <text x="${W / 2}" y="40" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">Three perpendicular dumbbells: pₓ along x, p_y along y, p_z along z. Each holds 2 electrons; total = 6.</text>
`;
  const drawDumbbell = (cx: number, cy: number, axis: "x" | "y" | "z", label: string) => {
    let lobe1: string, lobe2: string, ax1: string, ax2: string, txt: string;
    if (axis === "x") {
      lobe1 = `<ellipse cx="${cx - 35}" cy="${cy}" rx="30" ry="18" fill="${ACCENT_2}" opacity="0.45" stroke="${ACCENT_2}" stroke-width="2" />`;
      lobe2 = `<ellipse cx="${cx + 35}" cy="${cy}" rx="30" ry="18" fill="${ACCENT_2}" opacity="0.45" stroke="${ACCENT_2}" stroke-width="2" />`;
      ax1 = `<line x1="${cx - 80}" y1="${cy}" x2="${cx + 80}" y2="${cy}" stroke="${MUTED}" stroke-width="1" />`;
      ax2 = `<line x1="${cx}" y1="${cy - 70}" x2="${cx}" y2="${cy + 70}" stroke="${MUTED}" stroke-width="1" />`;
      txt = `<text x="${cx + 86}" y="${cy + 4}" font="11px system-ui" font-size="11" fill="${MUTED}">x</text>`;
    } else if (axis === "y") {
      lobe1 = `<ellipse cx="${cx}" cy="${cy - 35}" rx="18" ry="30" fill="${ACCENT_2}" opacity="0.45" stroke="${ACCENT_2}" stroke-width="2" />`;
      lobe2 = `<ellipse cx="${cx}" cy="${cy + 35}" rx="18" ry="30" fill="${ACCENT_2}" opacity="0.45" stroke="${ACCENT_2}" stroke-width="2" />`;
      ax1 = `<line x1="${cx - 80}" y1="${cy}" x2="${cx + 80}" y2="${cy}" stroke="${MUTED}" stroke-width="1" />`;
      ax2 = `<line x1="${cx}" y1="${cy - 70}" x2="${cx}" y2="${cy + 70}" stroke="${MUTED}" stroke-width="1" />`;
      txt = `<text x="${cx}" y="${cy - 76}" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">y</text>`;
    } else {
      // z drawn as forward/back projection
      lobe1 = `<ellipse cx="${cx - 12}" cy="${cy - 28}" rx="22" ry="30" fill="${ACCENT_2}" opacity="0.45" stroke="${ACCENT_2}" stroke-width="2" transform="rotate(-30 ${cx} ${cy})" />`;
      lobe2 = `<ellipse cx="${cx + 12}" cy="${cy + 28}" rx="22" ry="30" fill="${ACCENT_2}" opacity="0.45" stroke="${ACCENT_2}" stroke-width="2" transform="rotate(-30 ${cx} ${cy})" />`;
      ax1 = `<line x1="${cx - 80}" y1="${cy}" x2="${cx + 80}" y2="${cy}" stroke="${MUTED}" stroke-width="1" />`;
      ax2 = `<line x1="${cx - 50}" y1="${cy + 60}" x2="${cx + 50}" y2="${cy - 60}" stroke="${MUTED}" stroke-width="1" stroke-dasharray="3 3" />`;
      txt = `<text x="${cx + 56}" y="${cy - 60}" font="11px system-ui" font-size="11" fill="${MUTED}">z</text>`;
    }
    return `
    ${ax1}
    ${ax2}
    ${lobe1}
    ${lobe2}
    ${txt}
    <circle cx="${cx}" cy="${cy}" r="3" fill="${INK}" />
    <text x="${cx}" y="${cy + 105}" font="bold 13px system-ui" font-size="13" font-weight="700" fill="${ACCENT_2}" text-anchor="middle">${label}</text>`;
  };
  body += drawDumbbell(120, 150, "x", "p_x");
  body += drawDumbbell(300, 150, "y", "p_y");
  body += drawDumbbell(480, 150, "z", "p_z");
  body += `
  <text x="${W / 2}" y="270" font="bold 12px system-ui" font-size="12" font-weight="700" fill="${ACCENT_2}" text-anchor="middle">l = 1 · 2p, 3p, 4p, ... · 3 orbitals × 2 electrons each = 6 total</text>
`;
  return svgWrap(W, H, "p orbitals — three dumbbells along x y z", "Three p-orbital dumbbells rendered side by side: p_x oriented along the x-axis, p_y along the y-axis, p_z projected along z. Each is shown as two opposing lobes around a central nucleus.", body);
}

function s3_dOrbitals() {
  const W = 700, H = 240;
  // 5 d-orbital cartoons
  let body = `
  <text x="${W / 2}" y="22" font="bold 14px system-ui" font-size="14" font-weight="700" fill="${INK}" text-anchor="middle">d Orbitals — Five Shapes</text>
  <text x="${W / 2}" y="40" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">Four cloverleaf shapes (d_xy, d_yz, d_xz, d_x²−y²) and one dumbbell-with-doughnut (d_z²). Total: 5 × 2 = 10 electrons.</text>
`;
  const drawCloverleaf = (cx: number, cy: number, label: string, rotation = 0) => {
    return `
    <g transform="translate(${cx} ${cy}) rotate(${rotation})">
      <ellipse cx="22" cy="22" rx="16" ry="22" fill="${ACCENT_3}" opacity="0.5" stroke="${ACCENT_3}" stroke-width="1.8" transform="rotate(45)" />
      <ellipse cx="-22" cy="-22" rx="16" ry="22" fill="${ACCENT_3}" opacity="0.5" stroke="${ACCENT_3}" stroke-width="1.8" transform="rotate(45)" />
      <ellipse cx="22" cy="-22" rx="16" ry="22" fill="${ACCENT_3}" opacity="0.5" stroke="${ACCENT_3}" stroke-width="1.8" transform="rotate(-45)" />
      <ellipse cx="-22" cy="22" rx="16" ry="22" fill="${ACCENT_3}" opacity="0.5" stroke="${ACCENT_3}" stroke-width="1.8" transform="rotate(-45)" />
      <circle cx="0" cy="0" r="3" fill="${INK}" />
    </g>
    <text x="${cx}" y="${cy + 75}" font="bold 12px system-ui" font-size="12" font-weight="700" fill="${ACCENT_3}" text-anchor="middle">${label}</text>`;
  };
  body += drawCloverleaf(80, 130, "d_xy");
  body += drawCloverleaf(220, 130, "d_yz");
  body += drawCloverleaf(360, 130, "d_xz");
  // d_x²−y² (cloverleaf aligned with axes, not between)
  body += `
    <g transform="translate(500, 130)">
      <ellipse cx="34" cy="0" rx="20" ry="15" fill="${ACCENT_3}" opacity="0.5" stroke="${ACCENT_3}" stroke-width="1.8" />
      <ellipse cx="-34" cy="0" rx="20" ry="15" fill="${ACCENT_3}" opacity="0.5" stroke="${ACCENT_3}" stroke-width="1.8" />
      <ellipse cx="0" cy="-34" rx="15" ry="20" fill="${ACCENT_3}" opacity="0.5" stroke="${ACCENT_3}" stroke-width="1.8" />
      <ellipse cx="0" cy="34" rx="15" ry="20" fill="${ACCENT_3}" opacity="0.5" stroke="${ACCENT_3}" stroke-width="1.8" />
      <circle cx="0" cy="0" r="3" fill="${INK}" />
    </g>
    <text x="500" y="205" font="bold 12px system-ui" font-size="12" font-weight="700" fill="${ACCENT_3}" text-anchor="middle">d_x²−y²</text>
  `;
  // d_z² — dumbbell-with-doughnut
  body += `
    <g transform="translate(630, 130)">
      <ellipse cx="0" cy="-30" rx="14" ry="22" fill="${ACCENT_3}" opacity="0.5" stroke="${ACCENT_3}" stroke-width="1.8" />
      <ellipse cx="0" cy="30" rx="14" ry="22" fill="${ACCENT_3}" opacity="0.5" stroke="${ACCENT_3}" stroke-width="1.8" />
      <ellipse cx="0" cy="0" rx="32" ry="11" fill="${ACCENT_3}" opacity="0.4" stroke="${ACCENT_3}" stroke-width="1.5" />
      <circle cx="0" cy="0" r="3" fill="${INK}" />
    </g>
    <text x="630" y="205" font="bold 12px system-ui" font-size="12" font-weight="700" fill="${ACCENT_3}" text-anchor="middle">d_z²</text>
  `;
  body += `
  <text x="${W / 2}" y="232" font="bold 11px system-ui" font-size="11" font-weight="700" fill="${ACCENT_3}" text-anchor="middle">l = 2 · 3d, 4d, 5d, ... · 5 orbitals × 2 electrons = 10 total</text>
`;
  return svgWrap(W, H, "d orbitals — five shapes", "Five d-orbital cartoons arranged in a row: four cloverleaves (d_xy, d_yz, d_xz, d_x²−y²) and the d_z² (vertical dumbbell with horizontal doughnut). Caption gives l = 2 and total of 10 electrons.", body);
}

function s3_quantumNumbers() {
  const W = 540, H = 320;
  const body = `
  <text x="${W / 2}" y="22" font="bold 14px system-ui" font-size="14" font-weight="700" fill="${INK}" text-anchor="middle">Quantum Numbers — n, l, mₗ, mₛ</text>

  <!-- Hierarchy boxes -->
  <g>
    <rect x="40" y="60" width="140" height="60" rx="8" fill="${BG}" stroke="${ACCENT}" stroke-width="2" />
    <text x="110" y="82" font="bold 14px system-ui" font-size="14" font-weight="700" fill="${ACCENT}" text-anchor="middle">n  (principal)</text>
    <text x="110" y="102" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">1, 2, 3, ...</text>
    <text x="110" y="116" font="10px system-ui" font-size="10" fill="${MUTED}" text-anchor="middle">shell · energy</text>
  </g>
  <g>
    <rect x="200" y="60" width="140" height="60" rx="8" fill="${BG}" stroke="${ACCENT_2}" stroke-width="2" />
    <text x="270" y="82" font="bold 14px system-ui" font-size="14" font-weight="700" fill="${ACCENT_2}" text-anchor="middle">l  (azimuthal)</text>
    <text x="270" y="102" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">0 to n−1</text>
    <text x="270" y="116" font="10px system-ui" font-size="10" fill="${MUTED}" text-anchor="middle">subshell · shape</text>
  </g>
  <g>
    <rect x="360" y="60" width="140" height="60" rx="8" fill="${BG}" stroke="${ACCENT_3}" stroke-width="2" />
    <text x="430" y="82" font="bold 14px system-ui" font-size="14" font-weight="700" fill="${ACCENT_3}" text-anchor="middle">mₗ  (magnetic)</text>
    <text x="430" y="102" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">−l to +l</text>
    <text x="430" y="116" font="10px system-ui" font-size="10" fill="${MUTED}" text-anchor="middle">orbital · orientation</text>
  </g>

  <!-- Arrows down to mₛ -->
  <line x1="270" y1="124" x2="270" y2="160" stroke="${MUTED}" stroke-width="1.5" stroke-dasharray="4 3" />
  <g>
    <rect x="200" y="160" width="140" height="60" rx="8" fill="${BG}" stroke="${PROTON}" stroke-width="2" />
    <text x="270" y="182" font="bold 14px system-ui" font-size="14" font-weight="700" fill="${PROTON}" text-anchor="middle">mₛ  (spin)</text>
    <text x="270" y="202" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">+½ or −½</text>
    <text x="270" y="216" font="10px system-ui" font-size="10" fill="${MUTED}" text-anchor="middle">electron spin</text>
  </g>

  <!-- Subshell letters for l -->
  <text x="60" y="252" font="bold 11px system-ui" font-size="11" font-weight="700" fill="${INK}">l = 0 → s</text>
  <text x="160" y="252" font="bold 11px system-ui" font-size="11" font-weight="700" fill="${INK}">l = 1 → p</text>
  <text x="260" y="252" font="bold 11px system-ui" font-size="11" font-weight="700" fill="${INK}">l = 2 → d</text>
  <text x="360" y="252" font="bold 11px system-ui" font-size="11" font-weight="700" fill="${INK}">l = 3 → f</text>

  <text x="${W / 2}" y="280" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">Together (n, l, mₗ, mₛ) is a unique address for each electron — Pauli exclusion forbids any duplicate.</text>
  <text x="${W / 2}" y="298" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">Example: 2p_z with spin up → (n=2, l=1, mₗ=0, mₛ=+½)</text>
`;
  return svgWrap(W, H, "Quantum numbers — n l m_l m_s", "Four labelled boxes showing the four quantum numbers in hierarchy: n (principal, energy/shell), l (azimuthal, subshell shape), m_l (magnetic, orientation), and m_s (spin). A row at the bottom translates l = 0,1,2,3 to s, p, d, f.", body);
}

// ────────────────────────────────────────────────────────────────────────────
// SECTION 4 — Electron Configuration & Spectra (3 SVGs)
// ────────────────────────────────────────────────────────────────────────────

function s4_aufbauDiagonal() {
  const W = 480, H = 360;
  // Grid of orbitals with diagonal arrows
  // Rows by n (1..7), columns by l-letter (s p d f)
  const startX = 90, startY = 70, dx = 80, dy = 38;
  const rows = [
    ["1s", null, null, null],
    ["2s", "2p", null, null],
    ["3s", "3p", "3d", null],
    ["4s", "4p", "4d", "4f"],
    ["5s", "5p", "5d", "5f"],
    ["6s", "6p", "6d", null],
    ["7s", "7p", null, null],
  ];
  let body = `
  <text x="${W / 2}" y="22" font="bold 14px system-ui" font-size="14" font-weight="700" fill="${INK}" text-anchor="middle">Aufbau — Diagonal Filling Order</text>
  <text x="${W / 2}" y="40" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">Fill orbitals in diagonal sweeps: 1s → 2s → 2p → 3s → 3p → 4s → 3d → 4p → 5s ...</text>

  <text x="${startX - 20}" y="${startY - 12}" font="bold 11px system-ui" font-size="11" font-weight="700" fill="${MUTED}" text-anchor="middle">s</text>
  <text x="${startX - 20 + dx}" y="${startY - 12}" font="bold 11px system-ui" font-size="11" font-weight="700" fill="${MUTED}" text-anchor="middle">p</text>
  <text x="${startX - 20 + 2 * dx}" y="${startY - 12}" font="bold 11px system-ui" font-size="11" font-weight="700" fill="${MUTED}" text-anchor="middle">d</text>
  <text x="${startX - 20 + 3 * dx}" y="${startY - 12}" font="bold 11px system-ui" font-size="11" font-weight="700" fill="${MUTED}" text-anchor="middle">f</text>
`;
  // Boxes
  for (let r = 0; r < rows.length; r++) {
    for (let c = 0; c < rows[r].length; c++) {
      const cell = rows[r][c];
      if (!cell) continue;
      const x = startX - 30 + c * dx;
      const y = startY - 14 + r * dy;
      body += `
    <rect x="${x}" y="${y}" width="60" height="28" rx="4" fill="${BG}" stroke="${ACCENT}" stroke-width="1.5" />
    <text x="${x + 30}" y="${y + 19}" font="bold 13px system-ui" font-size="13" font-weight="700" fill="${ACCENT}" text-anchor="middle">${cell}</text>`;
    }
  }
  // Diagonal arrows showing fill order
  // Sweep through orbitals diagonally — list of (row, col) pairs in fill order
  const fillOrder: Array<[number, number]> = [];
  for (let s = 0; s < 14; s++) {
    for (let r = 0; r <= s; r++) {
      const c = s - r;
      if (r < rows.length && c < 4 && rows[r][c]) fillOrder.push([r, c]);
    }
  }
  // Group by diagonal (sum r+c) and draw an arrow per diagonal
  const diags = new Map<number, Array<[number, number]>>();
  for (const [r, c] of fillOrder) {
    const sum = r + c;
    if (!diags.has(sum)) diags.set(sum, []);
    diags.get(sum)!.push([r, c]);
  }
  body += `<defs><marker id="aufbau-arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto"><path d="M 0 0 L 10 5 L 0 10 z" fill="${NEGATIVE}" /></marker></defs>`;
  for (const [, diagCells] of diags) {
    if (diagCells.length < 2) continue;
    const first = diagCells[0];
    const last = diagCells[diagCells.length - 1];
    const x1 = startX + first[1] * dx;
    const y1 = startY + first[0] * dy - 4;
    const x2 = startX + last[1] * dx;
    const y2 = startY + last[0] * dy + 4;
    body += `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="${NEGATIVE}" stroke-width="1.5" marker-end="url(#aufbau-arr)" opacity="0.75" />`;
  }
  body += `
  <text x="${W / 2}" y="340" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">Diagonal arrows indicate the order; each arrow's start is the next orbital to fill after the previous one ended.</text>
`;
  return svgWrap(W, H, "Aufbau diagonal filling order", "A grid of orbital labels arranged by row (n = 1..7) and column (s, p, d, f). Diagonal red arrows sweep through the cells from top-left toward bottom-right indicating the Aufbau filling order: 1s, 2s, 2p, 3s, 3p, 4s, 3d, 4p, 5s, ...", body);
}

function s4_hydrogenSpectrum() {
  const W = 600, H = 280;
  // Visible balmer lines with labels
  // Wavelengths in nm: Hα 656.3 (red), Hβ 486.1 (blue-green), Hγ 434.0 (violet), Hδ 410.2 (violet)
  const xMin = 380, xMax = 700; // nm visible range
  const stripX0 = 60, stripX1 = 540, stripY = 130, stripH = 50;
  const x = (nm: number) => stripX0 + ((nm - xMin) / (xMax - xMin)) * (stripX1 - stripX0);

  const lines = [
    { nm: 656.3, label: "Hα", color: "#ef4444", note: "n=3 → 2" },
    { nm: 486.1, label: "Hβ", color: "#06b6d4", note: "n=4 → 2" },
    { nm: 434.0, label: "Hγ", color: "#7c3aed", note: "n=5 → 2" },
    { nm: 410.2, label: "Hδ", color: "#5b21b6", note: "n=6 → 2" },
  ];

  let body = `
  <text x="${W / 2}" y="22" font="bold 14px system-ui" font-size="14" font-weight="700" fill="${INK}" text-anchor="middle">Hydrogen Emission Spectrum (Balmer Series, Visible)</text>
  <text x="${W / 2}" y="40" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">Discrete emission lines — each is a photon released as an electron drops to n = 2.</text>

  <!-- Black background strip for the spectrum -->
  <rect x="${stripX0}" y="${stripY}" width="${stripX1 - stripX0}" height="${stripH}" fill="#0f172a" stroke="${INK}" stroke-width="1.5" />

  <!-- Wavelength axis tick marks below -->
  <line x1="${stripX0}" y1="${stripY + stripH}" x2="${stripX1}" y2="${stripY + stripH}" stroke="${INK}" stroke-width="1" />
`;
  for (const nmTick of [400, 450, 500, 550, 600, 650, 700]) {
    const px = x(nmTick);
    body += `
    <line x1="${px}" y1="${stripY + stripH}" x2="${px}" y2="${stripY + stripH + 6}" stroke="${INK}" stroke-width="1" />
    <text x="${px}" y="${stripY + stripH + 22}" font="10px system-ui" font-size="10" fill="${MUTED}" text-anchor="middle">${nmTick}</text>`;
  }
  body += `<text x="${(stripX0 + stripX1) / 2}" y="${stripY + stripH + 44}" font="bold 12px system-ui" font-size="12" font-weight="700" fill="${INK}" text-anchor="middle">wavelength λ (nm)</text>`;

  // Bright lines on the spectrum
  for (const l of lines) {
    const px = x(l.nm);
    body += `
    <line x1="${px}" y1="${stripY}" x2="${px}" y2="${stripY + stripH}" stroke="${l.color}" stroke-width="3.5" />
    <text x="${px}" y="${stripY - 8}" font="bold 11px system-ui" font-size="11" font-weight="700" fill="${l.color}" text-anchor="middle">${l.label}</text>
    <text x="${px}" y="${stripY - 22}" font="9px system-ui" font-size="9" fill="${MUTED}" text-anchor="middle">${l.note}</text>
    <text x="${px}" y="${stripY + stripH + 60}" font="9px system-ui" font-size="9" fill="${MUTED}" text-anchor="middle">${l.nm} nm</text>`;
  }
  body += `
  <text x="${W / 2}" y="${H - 12}" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">Each line corresponds to a fixed energy gap E_n − E_2 = h ν. The pattern is a fingerprint of hydrogen.</text>
`;
  return svgWrap(W, H, "Hydrogen Balmer emission spectrum", "Visible portion of hydrogen's emission spectrum: a black strip from 380 to 700 nm with four sharp coloured emission lines — Hα (red, 656.3 nm), Hβ (cyan, 486.1 nm), Hγ (violet, 434.0 nm), Hδ (deeper violet, 410.2 nm). Each line is annotated with the n→2 transition that produces it.", body);
}

function s4_orbitalDiagramHund() {
  const W = 500, H = 240;
  // Nitrogen: 1s² 2s² 2p³ — three p-electrons each in their own orbital, all spins parallel
  const startX = 80, slotY = 130, slotW = 48, slotH = 36;
  const slots = [
    { label: "1s", x: startX + 0 * (slotW + 12), spins: [-1, +1] }, // up + down (filled)
    { label: "2s", x: startX + 1 * (slotW + 12) + 18, spins: [-1, +1] },
    { label: "2pₓ", x: startX + 2 * (slotW + 12) + 36, spins: [+1] },
    { label: "2p_y", x: startX + 3 * (slotW + 12) + 36, spins: [+1] },
    { label: "2p_z", x: startX + 4 * (slotW + 12) + 36, spins: [+1] },
  ];
  let body = `
  <text x="${W / 2}" y="22" font="bold 14px system-ui" font-size="14" font-weight="700" fill="${INK}" text-anchor="middle">Orbital Diagram — Nitrogen (Hund's Rule)</text>
  <text x="${W / 2}" y="40" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">N: 1s² 2s² 2p³ — three 2p electrons each occupy their own orbital with parallel spins.</text>
`;
  for (const s of slots) {
    body += `
    <rect x="${s.x}" y="${slotY}" width="${slotW}" height="${slotH}" rx="6" fill="${BG}" stroke="${ACCENT}" stroke-width="1.8" />
    <text x="${s.x + slotW / 2}" y="${slotY + slotH + 22}" font="bold 12px system-ui" font-size="12" font-weight="700" fill="${ACCENT}" text-anchor="middle">${s.label}</text>`;
    // Draw arrow(s) inside
    if (s.spins.length === 2) {
      // up-down pair (filled orbital)
      body += `
      <line x1="${s.x + 14}" y1="${slotY + 30}" x2="${s.x + 14}" y2="${slotY + 6}" stroke="${INK}" stroke-width="2" marker-end="url(#hund-up)" />
      <line x1="${s.x + slotW - 14}" y1="${slotY + 6}" x2="${s.x + slotW - 14}" y2="${slotY + 30}" stroke="${INK}" stroke-width="2" marker-end="url(#hund-down)" />`;
    } else {
      // single spin-up
      body += `
      <line x1="${s.x + slotW / 2}" y1="${slotY + 30}" x2="${s.x + slotW / 2}" y2="${slotY + 6}" stroke="${POSITIVE}" stroke-width="2.5" marker-end="url(#hund-up)" />`;
    }
  }
  body += `
  <defs>
    <marker id="hund-up" viewBox="0 0 10 10" refX="5" refY="0" markerWidth="6" markerHeight="6" orient="auto">
      <path d="M 0 10 L 5 0 L 10 10 z" fill="${INK}" />
    </marker>
    <marker id="hund-down" viewBox="0 0 10 10" refX="5" refY="10" markerWidth="6" markerHeight="6" orient="auto">
      <path d="M 0 0 L 5 10 L 10 0 z" fill="${INK}" />
    </marker>
  </defs>

  <!-- Annotation -->
  <line x1="280" y1="${slotY - 14}" x2="450" y2="${slotY - 14}" stroke="${POSITIVE}" stroke-width="1.5" stroke-dasharray="4 3" />
  <text x="365" y="${slotY - 22}" font="bold 11px system-ui" font-size="11" font-weight="700" fill="${POSITIVE}" text-anchor="middle">Hund: spread before pairing</text>

  <text x="${W / 2}" y="${H - 24}" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">Pauli: same orbital → opposite spins. Hund: same energy → maximize unpaired with parallel spins.</text>
`;
  return svgWrap(W, H, "Nitrogen orbital diagram with Hund's rule", "Five labelled orbital boxes (1s, 2s, 2pₓ, 2p_y, 2p_z) for nitrogen. The 1s and 2s boxes each hold paired up/down arrows (filled). Each of the three 2p boxes holds a single up arrow (Hund's rule: spread before pairing).", body);
}

// ────────────────────────────────────────────────────────────────────────────
// Main
// ────────────────────────────────────────────────────────────────────────────

mkdirSync(ROOT, { recursive: true });

write("section-1-discovery/cathode-ray-experiment.svg", s1_cathodeRay());
write("section-1-discovery/rutherford-gold-foil.svg", s1_rutherfordGoldFoil());
write("section-1-discovery/subatomic-particles-comparison.svg", s1_subatomicParticles());

write("section-2-atomic-models/thomson-plum-pudding.svg", s2_thomsonPlumPudding());
write("section-2-atomic-models/rutherford-nuclear-model.svg", s2_rutherfordNuclear());
write("section-2-atomic-models/bohr-shell-model.svg", s2_bohrShellModel());

write("section-3-orbitals/s-orbital.svg", s3_sOrbital());
write("section-3-orbitals/p-orbitals.svg", s3_pOrbitals());
write("section-3-orbitals/d-orbitals.svg", s3_dOrbitals());
write("section-3-orbitals/quantum-numbers-tree.svg", s3_quantumNumbers());

write("section-4-electron-config-spectra/aufbau-diagonal-rule.svg", s4_aufbauDiagonal());
write("section-4-electron-config-spectra/hydrogen-emission-spectrum.svg", s4_hydrogenSpectrum());
write("section-4-electron-config-spectra/orbital-diagram-nitrogen-hund.svg", s4_orbitalDiagramHund());

console.log("done — 13 SVGs");
