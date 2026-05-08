#!/usr/bin/env bun
/**
 * Generate the Option-2 SVG catalogue for G7-SCI-001 Atoms and Periodic Table
 * (issue #332).
 *
 * Run from repo root:
 *   bun scripts/generate_periodic_table_visuals.ts
 *
 * Output: sample_content/g7-stem/G7-SCI-001_Atoms_and_Periodic_Table/Option2_Catalogue/section-N/*.svg
 *
 * Reuses the Bohr-shell pattern from G11-CHEM-002 (issue #329); the
 * periodic-trend heatmap is the new high-leverage primitive (will be
 * reused in G11-CHEM-003 and G12-CHEM-004).
 */

import { writeFileSync, mkdirSync } from "node:fs";
import { join, dirname } from "node:path";

const ROOT = join(
  import.meta.dir,
  "..",
  "sample_content",
  "g7-stem",
  "G7-SCI-001_Atoms_and_Periodic_Table",
  "Option2_Catalogue",
);

// Style tokens + class primitives lifted to pipeline/visual_templates.
// Element data, palettes, layout, and per-tile helpers imported from the
// class module per #343 phase C-5.
import {
  INK,
  MUTED,
  ACCENT,
  ACCENT_2,
  POSITIVE,
  NEGATIVE,
  GRID,
  BG,
} from "../pipeline/visual_templates/shared.ts";
import {
  PROTON,
  ELECTRON,
  GROUP_COLORS,
  ELEMENTS,
  TILE_W,
  TILE_H,
  TILE_GAP,
  TABLE_OFFSET_X,
  TABLE_OFFSET_Y,
  tileXY,
  elementTile,
  heatmapTile,
  makeHeatmapSvg,
  type Element,
} from "../pipeline/visual_templates/periodic_table.ts";

// (Element type + ELEMENTS data lifted to pipeline/visual_templates/periodic_table.ts.)

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
// SECTION 1 — Atoms (5 SVGs)
// ────────────────────────────────────────────────────────────────────────────

function s1_periodicTableOverview() {
  const W = TABLE_OFFSET_X * 2 + 18 * (TILE_W + TILE_GAP);
  const H = TABLE_OFFSET_Y + 4 * (TILE_H + TILE_GAP) + 90;

  let body = `
  <text x="${W / 2}" y="32" font="bold 18px system-ui" font-size="18" font-weight="700" fill="${INK}" text-anchor="middle">Periodic Table — Periods 1 to 4</text>
  <text x="${W / 2}" y="54" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">Cells coloured by family. Each shows: atomic number, symbol, atomic mass.</text>
`;
  for (const el of ELEMENTS) {
    body += elementTile(el);
  }
  // Legend
  const legendY = H - 70;
  const legendX0 = TABLE_OFFSET_X;
  const legendItems = [
    { label: "alkali metal", color: GROUP_COLORS.alkali },
    { label: "alkaline earth", color: GROUP_COLORS.alkaline },
    { label: "transition", color: GROUP_COLORS.transition },
    { label: "post-transition", color: GROUP_COLORS.posttransition },
    { label: "metalloid", color: GROUP_COLORS.metalloid },
    { label: "nonmetal", color: GROUP_COLORS.nonmetal },
    { label: "halogen", color: GROUP_COLORS.halogen },
    { label: "noble gas", color: GROUP_COLORS.noble },
  ];
  for (let i = 0; i < legendItems.length; i++) {
    const lx = legendX0 + (i % 4) * 280;
    const ly = legendY + Math.floor(i / 4) * 24;
    body += `
    <rect x="${lx}" y="${ly}" width="20" height="14" rx="2" fill="${legendItems[i].color}" stroke="${MUTED}" stroke-width="1" />
    <text x="${lx + 26}" y="${ly + 11}" font="11px system-ui" font-size="11" fill="${INK}">${legendItems[i].label}</text>`;
  }
  return svgWrap(W, H, "Periodic table overview periods 1 to 4", "A periodic table showing 36 elements arranged in 4 periods and 18 groups, with cells coloured by category: alkali metals (yellow), alkaline earths (orange), transition metals (mint), post-transition metals (pale blue), metalloids (pale purple), nonmetals (pale red), halogens (lime), and noble gases (cyan). A legend at the bottom labels each colour.", body);
}

function s1_elementCardAnatomy() {
  const W = 480, H = 380;
  // Show one big tile (Carbon) with all its annotations and leader-line labels.
  const tx = 180, ty = 110;
  const big = 140;
  let body = `
  <text x="${W / 2}" y="32" font="bold 16px system-ui" font-size="16" font-weight="700" fill="${INK}" text-anchor="middle">Reading One Cell of the Table</text>
  <text x="${W / 2}" y="52" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">Every tile carries the same four pieces of information.</text>

  <!-- Big tile -->
  <rect x="${tx}" y="${ty}" width="${big}" height="${big}" rx="10"
    fill="${GROUP_COLORS.nonmetal}" stroke="${INK}" stroke-width="2" />
  <text x="${tx + 10}" y="${ty + 26}" font="bold 22px system-ui" font-size="22" font-weight="700" fill="${INK}">6</text>
  <text x="${tx + big / 2}" y="${ty + 78}" font="bold 56px system-ui" font-size="56" font-weight="700" fill="${INK}" text-anchor="middle">C</text>
  <text x="${tx + big / 2}" y="${ty + 104}" font="14px system-ui" font-size="14" fill="${INK}" text-anchor="middle">Carbon</text>
  <text x="${tx + big / 2}" y="${ty + 124}" font="bold 14px system-ui" font-size="14" font-weight="700" fill="${MUTED}" text-anchor="middle">12.0</text>

  <!-- Leader-line labels -->
  <line x1="${tx + 24}" y1="${ty + 22}" x2="${tx - 80}" y2="${ty + 5}" stroke="${INK}" stroke-width="1.5" />
  <text x="${tx - 90}" y="${ty + 8}" font="bold 12px system-ui" font-size="12" font-weight="700" fill="${INK}" text-anchor="end">atomic number</text>
  <text x="${tx - 90}" y="${ty + 24}" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="end">(number of protons)</text>

  <line x1="${tx + big / 2}" y1="${ty + 50}" x2="${tx + big + 80}" y2="${ty + 30}" stroke="${INK}" stroke-width="1.5" />
  <text x="${tx + big + 90}" y="${ty + 33}" font="bold 12px system-ui" font-size="12" font-weight="700" fill="${INK}">symbol</text>
  <text x="${tx + big + 90}" y="${ty + 49}" font="11px system-ui" font-size="11" fill="${MUTED}">(1 or 2 letters)</text>

  <line x1="${tx + big / 2}" y1="${ty + 100}" x2="${tx - 80}" y2="${ty + 130}" stroke="${INK}" stroke-width="1.5" />
  <text x="${tx - 90}" y="${ty + 133}" font="bold 12px system-ui" font-size="12" font-weight="700" fill="${INK}" text-anchor="end">name</text>

  <line x1="${tx + big / 2}" y1="${ty + 124}" x2="${tx + big + 80}" y2="${ty + 134}" stroke="${INK}" stroke-width="1.5" />
  <text x="${tx + big + 90}" y="${ty + 137}" font="bold 12px system-ui" font-size="12" font-weight="700" fill="${INK}">atomic mass</text>
  <text x="${tx + big + 90}" y="${ty + 153}" font="11px system-ui" font-size="11" fill="${MUTED}">(protons + neutrons)</text>

  <text x="${W / 2}" y="${H - 30}" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">Carbon: atomic number 6 (six protons), symbol C, atomic mass ~12.</text>
  <text x="${W / 2}" y="${H - 14}" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">A neutral carbon atom has 6 protons + 6 electrons + (usually) 6 neutrons.</text>
`;
  return svgWrap(W, H, "Anatomy of a periodic-table tile", "A close-up of the Carbon (C) tile from the periodic table, magnified, with leader lines pointing to its four pieces of information: atomic number 6 (number of protons), symbol C (one or two letters), name Carbon, and atomic mass 12.0 (protons plus neutrons).", body);
}

function s1_bohrShellsFirstTwenty() {
  // Mini Bohr-shell diagrams for the first 20 elements arranged in periodic-table grid.
  // Each tile shows the shell structure as concentric circles with electron dots.
  const W = TABLE_OFFSET_X * 2 + 18 * (TILE_W + TILE_GAP);
  const H = TABLE_OFFSET_Y + 4 * (TILE_H + TILE_GAP) + 60;

  let body = `
  <text x="${W / 2}" y="32" font="bold 18px system-ui" font-size="18" font-weight="700" fill="${INK}" text-anchor="middle">Bohr Shells — Hydrogen through Calcium</text>
  <text x="${W / 2}" y="54" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">Each tile is a tiny atom. Concentric circles are shells; dots are electrons. Same-column elements have the same outer shell.</text>
`;
  // Only first 20 elements (Z=1..20)
  for (const el of ELEMENTS.filter(e => e.Z <= 20)) {
    const { x, y } = tileXY(el.group, el.period);
    const cx = x + TILE_W / 2;
    const cy = y + TILE_H / 2;
    body += `
    <rect x="${x}" y="${y}" width="${TILE_W}" height="${TILE_H}" rx="4" fill="${BG}" stroke="${MUTED}" stroke-width="0.8" />
    <text x="${x + 4}" y="${y + 11}" font="bold 8px system-ui" font-size="8" font-weight="700" fill="${INK}">${el.Z}</text>
    <text x="${x + TILE_W - 4}" y="${y + 11}" font="bold 9px system-ui" font-size="9" font-weight="700" fill="${INK}" text-anchor="end">${el.symbol}</text>`;
    // Nucleus
    body += `<circle cx="${cx}" cy="${cy + 4}" r="3" fill="${PROTON}" />`;
    // Shells
    const shellRadii = [9, 16, 22, 26];
    for (let s = 0; s < el.shells.length; s++) {
      const r = shellRadii[s] ?? 28;
      body += `<circle cx="${cx}" cy="${cy + 4}" r="${r}" fill="none" stroke="${MUTED}" stroke-width="0.6" />`;
      const N = el.shells[s];
      for (let k = 0; k < N; k++) {
        const ang = (2 * Math.PI * k) / N + s * 0.3;
        const ex = cx + r * Math.cos(ang);
        const ey = cy + 4 + r * Math.sin(ang);
        body += `<circle cx="${ex.toFixed(1)}" cy="${ey.toFixed(1)}" r="1.6" fill="${ELECTRON}" />`;
      }
    }
  }
  return svgWrap(W, H, "Bohr shells for first twenty elements", "Mini Bohr-shell diagrams for hydrogen (Z=1) through calcium (Z=20) arranged in their periodic-table positions. Each tile shows a tiny red nucleus surrounded by concentric circular shells with small blue electron dots placed around them. Vertical alignment shows that elements in the same column have the same number of outermost electrons.", body);
}

function s1_groupVsPeriod() {
  const W = TABLE_OFFSET_X * 2 + 18 * (TILE_W + TILE_GAP);
  const H = TABLE_OFFSET_Y + 4 * (TILE_H + TILE_GAP) + 100;

  let body = `
  <text x="${W / 2}" y="32" font="bold 18px system-ui" font-size="18" font-weight="700" fill="${INK}" text-anchor="middle">Groups (columns) vs Periods (rows)</text>
  <text x="${W / 2}" y="54" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">Same group = same outer-shell electron count = similar chemistry. Same period = same number of shells.</text>
`;
  for (const el of ELEMENTS) {
    const inGroup1 = el.group === 1;
    const inPeriod3 = el.period === 3;
    const fill = inGroup1
      ? "#fef3c7"  // strong yellow highlight
      : inPeriod3
        ? "#bfdbfe"  // strong blue highlight
        : "#f3f4f6"; // muted background
    const stroke = (inGroup1 || inPeriod3) ? INK : MUTED;
    const sw = (inGroup1 || inPeriod3) ? 1.5 : 0.8;
    const { x, y } = tileXY(el.group, el.period);
    body += `
    <rect x="${x}" y="${y}" width="${TILE_W}" height="${TILE_H}" rx="4" fill="${fill}" stroke="${stroke}" stroke-width="${sw}" />
    <text x="${x + 4}" y="${y + 12}" font="bold 9px system-ui" font-size="9" font-weight="700" fill="${INK}">${el.Z}</text>
    <text x="${x + TILE_W / 2}" y="${y + 32}" font="bold 16px system-ui" font-size="16" font-weight="700" fill="${INK}" text-anchor="middle">${el.symbol}</text>`;
  }
  // Annotation for group 1
  const g1Top = tileXY(1, 1);
  body += `
  <line x1="${g1Top.x - 14}" y1="${g1Top.y}" x2="${g1Top.x - 14}" y2="${g1Top.y + 4 * (TILE_H + TILE_GAP)}" stroke="${ACCENT_2}" stroke-width="2" />
  <text x="${g1Top.x - 22}" y="${g1Top.y + 100}" font="bold 12px system-ui" font-size="12" font-weight="700" fill="${ACCENT_2}" text-anchor="end" transform="rotate(-90 ${g1Top.x - 22} ${g1Top.y + 100})">Group 1 (alkali metals)</text>
`;
  // Annotation for period 3
  const p3 = tileXY(1, 3);
  body += `
  <line x1="${p3.x}" y1="${p3.y - 8}" x2="${p3.x + 18 * (TILE_W + TILE_GAP) - TILE_GAP}" y2="${p3.y - 8}" stroke="${ACCENT}" stroke-width="2" />
  <text x="${p3.x + 9 * (TILE_W + TILE_GAP)}" y="${p3.y - 14}" font="bold 12px system-ui" font-size="12" font-weight="700" fill="${ACCENT}" text-anchor="middle">Period 3 — three shells</text>
`;
  body += `
  <text x="${W / 2}" y="${H - 38}" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">Yellow column: every element has 1 electron in its outermost shell — they react the same way (all alkali metals).</text>
  <text x="${W / 2}" y="${H - 22}" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">Blue row: every element fills shells 1, 2, and 3 — atomic radius shrinks left-to-right within the row.</text>
`;
  return svgWrap(W, H, "Groups versus periods on the periodic table", "A periodic table with the entire first column highlighted yellow (Group 1, the alkali metals) and the third row highlighted blue (Period 3). Annotations along the side and top label each highlight, emphasising that columns share outer-electron count and rows share shell count.", body);
}

function s1_metalNonmetalMetalloid() {
  const W = TABLE_OFFSET_X * 2 + 18 * (TILE_W + TILE_GAP);
  const H = TABLE_OFFSET_Y + 4 * (TILE_H + TILE_GAP) + 80;

  let body = `
  <text x="${W / 2}" y="32" font="bold 18px system-ui" font-size="18" font-weight="700" fill="${INK}" text-anchor="middle">Metals · Metalloids · Non-metals</text>
  <text x="${W / 2}" y="54" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">A diagonal "staircase" splits the table. Left of the line: metals. Right: non-metals. Touching the line: metalloids.</text>
`;
  for (const el of ELEMENTS) {
    const isMetal = el.category === "alkali" || el.category === "alkaline" || el.category === "transition" || el.category === "posttransition";
    const isMetalloid = el.category === "metalloid";
    const isNonmetal = el.category === "nonmetal" || el.category === "halogen" || el.category === "noble";
    const fill = isMetal ? "#fed7aa" : isMetalloid ? "#ddd6fe" : isNonmetal ? "#bbf7d0" : "#e5e7eb";
    const { x, y } = tileXY(el.group, el.period);
    body += `
    <rect x="${x}" y="${y}" width="${TILE_W}" height="${TILE_H}" rx="4" fill="${fill}" stroke="${MUTED}" stroke-width="1" />
    <text x="${x + TILE_W / 2}" y="${y + 32}" font="bold 16px system-ui" font-size="16" font-weight="700" fill="${INK}" text-anchor="middle">${el.symbol}</text>`;
  }
  // Draw the staircase line on the metalloid border
  // Approximate: B-Si border, Si-As, As-Te (Te is period 5 so we just go to As here)
  const stair: Array<[number, number, number, number]> = [
    [13, 2, 13, 3], // left of B (period 2)
    [13, 3, 14, 3],
    [14, 3, 14, 4],
    [14, 4, 15, 4],
    [15, 4, 16, 4],
  ];
  for (const [g1, p1, g2, p2] of stair) {
    const a = tileXY(g1, p1);
    const b = tileXY(g2, p2);
    const ax = a.x;
    const ay = a.y;
    const bx = b.x;
    const by = b.y;
    body += `<line x1="${ax}" y1="${ay}" x2="${bx}" y2="${by}" stroke="${NEGATIVE}" stroke-width="3" />`;
  }
  // Legend
  const ly = H - 56;
  body += `
  <rect x="${TABLE_OFFSET_X}" y="${ly}" width="22" height="14" rx="2" fill="#fed7aa" stroke="${MUTED}" />
  <text x="${TABLE_OFFSET_X + 28}" y="${ly + 11}" font="11px system-ui" font-size="11" fill="${INK}">metal — shiny, conducts heat & electricity</text>
  <rect x="${TABLE_OFFSET_X + 360}" y="${ly}" width="22" height="14" rx="2" fill="#ddd6fe" stroke="${MUTED}" />
  <text x="${TABLE_OFFSET_X + 388}" y="${ly + 11}" font="11px system-ui" font-size="11" fill="${INK}">metalloid — half-and-half (silicon!)</text>
  <rect x="${TABLE_OFFSET_X + 700}" y="${ly}" width="22" height="14" rx="2" fill="#bbf7d0" stroke="${MUTED}" />
  <text x="${TABLE_OFFSET_X + 728}" y="${ly + 11}" font="11px system-ui" font-size="11" fill="${INK}">non-metal — dull, poor conductor</text>
  <text x="${TABLE_OFFSET_X + 360}" y="${ly + 30}" font="bold 11px system-ui" font-size="11" font-weight="700" fill="${NEGATIVE}">red staircase = the dividing line</text>
`;
  return svgWrap(W, H, "Metals metalloids and non-metals zones", "A periodic table with three distinct colour zones: metals (orange) on the left, non-metals (green) on the right, and a thin metalloid (purple) zone running diagonally between them. A red staircase line traces the diagonal boundary between metal and non-metal. Legend at the bottom labels each zone.", body);
}

// ────────────────────────────────────────────────────────────────────────────
// SECTION 2 — Periodic Trends (4 SVGs)
// ────────────────────────────────────────────────────────────────────────────

function s2_atomicRadiusHeatmap() {
  return makeHeatmapSvg(
    "Atomic Radius — Periodic Trend",
    "How big is each atom? Bigger atoms = redder. Trend: shrinks left-to-right, grows top-to-bottom.",
    'atomicRadiusPm',
    'pm',
    'blueToRed',
    'small',
    'big',
    "A periodic-table heatmap colouring each element's tile by its atomic radius (in picometres). Larger atoms appear redder, smaller atoms bluer. The visual pattern shows radius shrinking from left to right within a period and growing from top to bottom within a group. A linear gradient legend at the bottom maps colour to value.",
  );
}

function s2_ionizationEnergyHeatmap() {
  return makeHeatmapSvg(
    "First Ionization Energy — Periodic Trend",
    "How hard is it to rip off the outermost electron? Higher = redder. Trend: grows left-to-right, shrinks top-to-bottom.",
    'ionizationEnergyEv',
    'eV',
    'redToBlue',
    'low',
    'high',
    "A periodic-table heatmap colouring each element's tile by its first ionization energy (in electron-volts). Higher ionization energies appear redder, lower bluer. The visual pattern is the inverse of atomic radius: ionization energy grows left-to-right and shrinks top-to-bottom. Noble gases stand out as bright red on the right edge.",
  );
}

function s2_electronegativityHeatmap() {
  return makeHeatmapSvg(
    "Electronegativity — Periodic Trend",
    "How much does each atom 'pull' shared electrons toward itself? Higher = redder. Fluorine wins (3.98).",
    'electronegativity',
    'Pauling',
    'redToBlue',
    'weak pull',
    'strong pull',
    "A periodic-table heatmap colouring each element's tile by Pauling-scale electronegativity. Stronger pullers (fluorine, oxygen) appear deepest red; weaker pullers (alkali metals, hydrogen) appear bluest. Noble gases are uncoloured because they don't form bonds. The pattern grows toward the upper-right corner.",
  );
}

function s2_trendsArrowsSummary() {
  const W = TABLE_OFFSET_X * 2 + 18 * (TILE_W + TILE_GAP);
  const H = TABLE_OFFSET_Y + 4 * (TILE_H + TILE_GAP) + 130;

  let body = `
  <text x="${W / 2}" y="32" font="bold 18px system-ui" font-size="18" font-weight="700" fill="${INK}" text-anchor="middle">Periodic Trends — One-Page Summary</text>
  <text x="${W / 2}" y="54" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">Three trends, one diagram. Arrow direction = "increases this way".</text>
`;
  // Faint table outline (just rectangles)
  for (const el of ELEMENTS) {
    const { x, y } = tileXY(el.group, el.period);
    body += `<rect x="${x}" y="${y}" width="${TILE_W}" height="${TILE_H}" rx="4" fill="${BG}" stroke="${MUTED}" stroke-width="0.6" />
             <text x="${x + TILE_W / 2}" y="${y + 32}" font="bold 12px system-ui" font-size="12" font-weight="700" fill="${MUTED}" text-anchor="middle">${el.symbol}</text>`;
  }
  // Big arrows on top: ionization energy + electronegativity going right
  const tableLeft = TABLE_OFFSET_X;
  const tableRight = TABLE_OFFSET_X + 18 * (TILE_W + TILE_GAP) - TILE_GAP;
  const tableTop = TABLE_OFFSET_Y;
  const tableBottom = TABLE_OFFSET_Y + 4 * (TILE_H + TILE_GAP);
  body += `
  <defs>
    <marker id="trend-arr-up" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="10" markerHeight="10" orient="auto">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="${NEGATIVE}" />
    </marker>
    <marker id="trend-arr-down" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="10" markerHeight="10" orient="auto">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="${ACCENT}" />
    </marker>
  </defs>

  <!-- Increasing IE/EN/EA across the period (right-pointing red arrow above the table) -->
  <line x1="${tableLeft}" y1="${tableTop - 14}" x2="${tableRight}" y2="${tableTop - 14}" stroke="${NEGATIVE}" stroke-width="3" marker-end="url(#trend-arr-up)" />
  <text x="${(tableLeft + tableRight) / 2}" y="${tableTop - 22}" font="bold 12px system-ui" font-size="12" font-weight="700" fill="${NEGATIVE}" text-anchor="middle">ionization energy + electronegativity INCREASE →</text>

  <!-- Decreasing radius across the period (right-pointing blue arrow below the table) -->
  <line x1="${tableLeft}" y1="${tableBottom + 16}" x2="${tableRight}" y2="${tableBottom + 16}" stroke="${ACCENT}" stroke-width="3" marker-end="url(#trend-arr-down)" />
  <text x="${(tableLeft + tableRight) / 2}" y="${tableBottom + 36}" font="bold 12px system-ui" font-size="12" font-weight="700" fill="${ACCENT}" text-anchor="middle">atomic radius SHRINKS →</text>

  <!-- Group trends: down arrow on the left side -->
  <line x1="${tableLeft - 14}" y1="${tableTop}" x2="${tableLeft - 14}" y2="${tableBottom}" stroke="${ACCENT}" stroke-width="3" marker-end="url(#trend-arr-down)" />
  <text x="${tableLeft - 22}" y="${(tableTop + tableBottom) / 2}" font="bold 12px system-ui" font-size="12" font-weight="700" fill="${ACCENT}" text-anchor="end" transform="rotate(-90 ${tableLeft - 22} ${(tableTop + tableBottom) / 2})">radius GROWS ↓ · IE/EN SHRINK ↓</text>

  <text x="${W / 2}" y="${H - 50}" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">Right and up → smaller, harder-to-ionize, more grabby. Left and down → bigger, easy to ionize, less grabby.</text>
  <text x="${W / 2}" y="${H - 32}" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">Why? More protons in the same shell → tighter pull on electrons → smaller radius and stronger grip.</text>
  <text x="${W / 2}" y="${H - 14}" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">Add a shell (down) → outer electrons are farther away → bigger atom, looser hold.</text>
`;
  return svgWrap(W, H, "Periodic trends arrows summary", "A faint outline of the periodic table with three big trend arrows annotated: a red right-pointing arrow above the table labelled 'ionization energy + electronegativity INCREASE →', a blue right-pointing arrow below the table labelled 'atomic radius SHRINKS →', and a blue down-pointing arrow on the left side labelled 'radius GROWS ↓, IE/EN SHRINK ↓'. A short caption explains the proton-pull reasoning.", body);
}

// ────────────────────────────────────────────────────────────────────────────
// Main
// ────────────────────────────────────────────────────────────────────────────

mkdirSync(ROOT, { recursive: true });

write("section-1-atoms/periodic-table-overview.svg", s1_periodicTableOverview());
write("section-1-atoms/element-card-anatomy.svg", s1_elementCardAnatomy());
write("section-1-atoms/bohr-shells-first-twenty.svg", s1_bohrShellsFirstTwenty());
write("section-1-atoms/group-vs-period-highlight.svg", s1_groupVsPeriod());
write("section-1-atoms/metal-nonmetal-metalloid-zones.svg", s1_metalNonmetalMetalloid());

write("section-2-trends/atomic-radius-heatmap.svg", s2_atomicRadiusHeatmap());
write("section-2-trends/ionization-energy-heatmap.svg", s2_ionizationEnergyHeatmap());
write("section-2-trends/electronegativity-heatmap.svg", s2_electronegativityHeatmap());
write("section-2-trends/trends-arrows-summary.svg", s2_trendsArrowsSummary());

console.log("done — 9 SVGs");
