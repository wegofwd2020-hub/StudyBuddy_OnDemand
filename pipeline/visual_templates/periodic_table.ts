/**
 * pipeline/visual_templates/periodic_table.ts
 *
 * Class-specific primitives + element data for periodic-table catalogues.
 *
 * Lifted from `scripts/generate_periodic_table_visuals.ts` per #343 (Wave 5
 * phase C-5). Per the G7-SCI-001 MEMO, this module is the canonical edit
 * surface for downstream chemistry units (G11-CHEM-003, G12-CHEM-004) —
 * grow `ELEMENTS` from Z=1..36 to Z=1..118 mechanically as new units land.
 *
 * Surface:
 *  - `Element` type + `ELEMENTS` array (Z=1..36, periods 1–4)
 *  - Locked palettes: GROUP_COLORS, PROTON, ELECTRON
 *  - Layout constants: TILE_W, TILE_H, TILE_GAP, TABLE_OFFSET_X, TABLE_OFFSET_Y
 *  - Helpers: tileXY, elementTile, heatmapTile
 *
 * Excluded from this module:
 *  - `makeHeatmapSvg` (the high-level "stamp the entire heatmap SVG"
 *    function) stays in the generator because it composes svgWrap + the
 *    legend gradient at a per-figure level. Lift to #344 (Wave 6).
 */

import { INK, MUTED } from "./shared.ts";

// ─────────────────────────────────────────────────────────────────────────
// Particle palette — carries from G11-CHEM-002
// ─────────────────────────────────────────────────────────────────────────

export const PROTON = "#dc2626";
export const ELECTRON = "#2b6cb0";

// ─────────────────────────────────────────────────────────────────────────
// Periodic-table group colours — locked-in convention
// ─────────────────────────────────────────────────────────────────────────

export const GROUP_COLORS = {
  alkali: "#fde68a", // soft yellow
  alkaline: "#fdba74", // soft orange
  transition: "#a7f3d0", // mint
  posttransition: "#bfdbfe", // pale blue
  metalloid: "#ddd6fe", // pale purple
  nonmetal: "#fecaca", // pale red
  halogen: "#bef264", // lime
  noble: "#a5f3fc", // cyan
  lanthanide: "#fbcfe8", // pink
  actinide: "#e9d5ff", // light purple
} as const;

// ─────────────────────────────────────────────────────────────────────────
// Element data — Z=1..36 (periods 1-4)
// ─────────────────────────────────────────────────────────────────────────

export type Element = {
  Z: number;
  symbol: string;
  name: string;
  mass: number; // approximate atomic mass
  group: number; // 1..18
  period: number; // 1..7
  shells: number[]; // electrons per shell
  category: keyof typeof GROUP_COLORS;
  electronegativity: number | null; // Pauling scale
  atomicRadiusPm: number | null; // empirical, pm
  ionizationEnergyEv: number | null; // first IE, eV
};

export const ELEMENTS: Element[] = [
  // Period 1
  { Z: 1,  symbol: "H",  name: "Hydrogen",  mass: 1.0,   group: 1,  period: 1, shells: [1],         category: "nonmetal",       electronegativity: 2.20, atomicRadiusPm: 53,  ionizationEnergyEv: 13.6 },
  { Z: 2,  symbol: "He", name: "Helium",    mass: 4.0,   group: 18, period: 1, shells: [2],         category: "noble",          electronegativity: null, atomicRadiusPm: 31,  ionizationEnergyEv: 24.6 },
  // Period 2
  { Z: 3,  symbol: "Li", name: "Lithium",   mass: 6.9,   group: 1,  period: 2, shells: [2, 1],      category: "alkali",         electronegativity: 0.98, atomicRadiusPm: 167, ionizationEnergyEv: 5.4 },
  { Z: 4,  symbol: "Be", name: "Beryllium", mass: 9.0,   group: 2,  period: 2, shells: [2, 2],      category: "alkaline",       electronegativity: 1.57, atomicRadiusPm: 112, ionizationEnergyEv: 9.3 },
  { Z: 5,  symbol: "B",  name: "Boron",     mass: 10.8,  group: 13, period: 2, shells: [2, 3],      category: "metalloid",      electronegativity: 2.04, atomicRadiusPm: 87,  ionizationEnergyEv: 8.3 },
  { Z: 6,  symbol: "C",  name: "Carbon",    mass: 12.0,  group: 14, period: 2, shells: [2, 4],      category: "nonmetal",       electronegativity: 2.55, atomicRadiusPm: 67,  ionizationEnergyEv: 11.3 },
  { Z: 7,  symbol: "N",  name: "Nitrogen",  mass: 14.0,  group: 15, period: 2, shells: [2, 5],      category: "nonmetal",       electronegativity: 3.04, atomicRadiusPm: 56,  ionizationEnergyEv: 14.5 },
  { Z: 8,  symbol: "O",  name: "Oxygen",    mass: 16.0,  group: 16, period: 2, shells: [2, 6],      category: "nonmetal",       electronegativity: 3.44, atomicRadiusPm: 48,  ionizationEnergyEv: 13.6 },
  { Z: 9,  symbol: "F",  name: "Fluorine",  mass: 19.0,  group: 17, period: 2, shells: [2, 7],      category: "halogen",        electronegativity: 3.98, atomicRadiusPm: 42,  ionizationEnergyEv: 17.4 },
  { Z: 10, symbol: "Ne", name: "Neon",      mass: 20.2,  group: 18, period: 2, shells: [2, 8],      category: "noble",          electronegativity: null, atomicRadiusPm: 38,  ionizationEnergyEv: 21.6 },
  // Period 3
  { Z: 11, symbol: "Na", name: "Sodium",    mass: 23.0,  group: 1,  period: 3, shells: [2, 8, 1],   category: "alkali",         electronegativity: 0.93, atomicRadiusPm: 190, ionizationEnergyEv: 5.1 },
  { Z: 12, symbol: "Mg", name: "Magnesium", mass: 24.3,  group: 2,  period: 3, shells: [2, 8, 2],   category: "alkaline",       electronegativity: 1.31, atomicRadiusPm: 145, ionizationEnergyEv: 7.6 },
  { Z: 13, symbol: "Al", name: "Aluminium", mass: 27.0,  group: 13, period: 3, shells: [2, 8, 3],   category: "posttransition", electronegativity: 1.61, atomicRadiusPm: 118, ionizationEnergyEv: 6.0 },
  { Z: 14, symbol: "Si", name: "Silicon",   mass: 28.1,  group: 14, period: 3, shells: [2, 8, 4],   category: "metalloid",      electronegativity: 1.90, atomicRadiusPm: 111, ionizationEnergyEv: 8.2 },
  { Z: 15, symbol: "P",  name: "Phosphorus",mass: 31.0,  group: 15, period: 3, shells: [2, 8, 5],   category: "nonmetal",       electronegativity: 2.19, atomicRadiusPm: 98,  ionizationEnergyEv: 10.5 },
  { Z: 16, symbol: "S",  name: "Sulfur",    mass: 32.1,  group: 16, period: 3, shells: [2, 8, 6],   category: "nonmetal",       electronegativity: 2.58, atomicRadiusPm: 88,  ionizationEnergyEv: 10.4 },
  { Z: 17, symbol: "Cl", name: "Chlorine",  mass: 35.5,  group: 17, period: 3, shells: [2, 8, 7],   category: "halogen",        electronegativity: 3.16, atomicRadiusPm: 79,  ionizationEnergyEv: 13.0 },
  { Z: 18, symbol: "Ar", name: "Argon",     mass: 40.0,  group: 18, period: 3, shells: [2, 8, 8],   category: "noble",          electronegativity: null, atomicRadiusPm: 71,  ionizationEnergyEv: 15.8 },
  // Period 4
  { Z: 19, symbol: "K",  name: "Potassium", mass: 39.1,  group: 1,  period: 4, shells: [2, 8, 8, 1],category: "alkali",         electronegativity: 0.82, atomicRadiusPm: 243, ionizationEnergyEv: 4.3 },
  { Z: 20, symbol: "Ca", name: "Calcium",   mass: 40.1,  group: 2,  period: 4, shells: [2, 8, 8, 2],category: "alkaline",       electronegativity: 1.00, atomicRadiusPm: 194, ionizationEnergyEv: 6.1 },
  // Transition metals (period 4)
  { Z: 21, symbol: "Sc", name: "Scandium",  mass: 45.0,  group: 3,  period: 4, shells: [2, 8, 9, 2],category: "transition",     electronegativity: 1.36, atomicRadiusPm: 184, ionizationEnergyEv: 6.6 },
  { Z: 22, symbol: "Ti", name: "Titanium",  mass: 47.9,  group: 4,  period: 4, shells: [2, 8, 10, 2],category: "transition",    electronegativity: 1.54, atomicRadiusPm: 176, ionizationEnergyEv: 6.8 },
  { Z: 23, symbol: "V",  name: "Vanadium",  mass: 50.9,  group: 5,  period: 4, shells: [2, 8, 11, 2],category: "transition",    electronegativity: 1.63, atomicRadiusPm: 171, ionizationEnergyEv: 6.7 },
  { Z: 24, symbol: "Cr", name: "Chromium",  mass: 52.0,  group: 6,  period: 4, shells: [2, 8, 13, 1],category: "transition",    electronegativity: 1.66, atomicRadiusPm: 166, ionizationEnergyEv: 6.8 },
  { Z: 25, symbol: "Mn", name: "Manganese", mass: 54.9,  group: 7,  period: 4, shells: [2, 8, 13, 2],category: "transition",    electronegativity: 1.55, atomicRadiusPm: 161, ionizationEnergyEv: 7.4 },
  { Z: 26, symbol: "Fe", name: "Iron",      mass: 55.8,  group: 8,  period: 4, shells: [2, 8, 14, 2],category: "transition",    electronegativity: 1.83, atomicRadiusPm: 156, ionizationEnergyEv: 7.9 },
  { Z: 27, symbol: "Co", name: "Cobalt",    mass: 58.9,  group: 9,  period: 4, shells: [2, 8, 15, 2],category: "transition",    electronegativity: 1.88, atomicRadiusPm: 152, ionizationEnergyEv: 7.9 },
  { Z: 28, symbol: "Ni", name: "Nickel",    mass: 58.7,  group: 10, period: 4, shells: [2, 8, 16, 2],category: "transition",    electronegativity: 1.91, atomicRadiusPm: 149, ionizationEnergyEv: 7.6 },
  { Z: 29, symbol: "Cu", name: "Copper",    mass: 63.5,  group: 11, period: 4, shells: [2, 8, 18, 1],category: "transition",    electronegativity: 1.90, atomicRadiusPm: 145, ionizationEnergyEv: 7.7 },
  { Z: 30, symbol: "Zn", name: "Zinc",      mass: 65.4,  group: 12, period: 4, shells: [2, 8, 18, 2],category: "transition",    electronegativity: 1.65, atomicRadiusPm: 142, ionizationEnergyEv: 9.4 },
  { Z: 31, symbol: "Ga", name: "Gallium",   mass: 69.7,  group: 13, period: 4, shells: [2, 8, 18, 3],category: "posttransition",electronegativity: 1.81, atomicRadiusPm: 136, ionizationEnergyEv: 6.0 },
  { Z: 32, symbol: "Ge", name: "Germanium", mass: 72.6,  group: 14, period: 4, shells: [2, 8, 18, 4],category: "metalloid",     electronegativity: 2.01, atomicRadiusPm: 125, ionizationEnergyEv: 7.9 },
  { Z: 33, symbol: "As", name: "Arsenic",   mass: 74.9,  group: 15, period: 4, shells: [2, 8, 18, 5],category: "metalloid",     electronegativity: 2.18, atomicRadiusPm: 114, ionizationEnergyEv: 9.8 },
  { Z: 34, symbol: "Se", name: "Selenium",  mass: 79.0,  group: 16, period: 4, shells: [2, 8, 18, 6],category: "nonmetal",      electronegativity: 2.55, atomicRadiusPm: 103, ionizationEnergyEv: 9.8 },
  { Z: 35, symbol: "Br", name: "Bromine",   mass: 79.9,  group: 17, period: 4, shells: [2, 8, 18, 7],category: "halogen",       electronegativity: 2.96, atomicRadiusPm: 94,  ionizationEnergyEv: 11.8 },
  { Z: 36, symbol: "Kr", name: "Krypton",   mass: 83.8,  group: 18, period: 4, shells: [2, 8, 18, 8],category: "noble",         electronegativity: 3.00, atomicRadiusPm: 88,  ionizationEnergyEv: 14.0 },
];

// ─────────────────────────────────────────────────────────────────────────
// Layout constants — locked tile dimensions across all periodic-table figures
// ─────────────────────────────────────────────────────────────────────────

export const TILE_W = 56;
export const TILE_H = 56;
export const TILE_GAP = 4;
export const TABLE_OFFSET_X = 30;
export const TABLE_OFFSET_Y = 80;

// ─────────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────────

/** Map (group, period) to (x, y) pixel position on the periodic-table grid. */
export function tileXY(group: number, period: number): { x: number; y: number } {
  const colIndex = group - 1;
  return {
    x: TABLE_OFFSET_X + colIndex * (TILE_W + TILE_GAP),
    y: TABLE_OFFSET_Y + (period - 1) * (TILE_H + TILE_GAP),
  };
}

/** Render a single element tile (filled rect + symbol + Z + name). */
export function elementTile(
  el: Element,
  opts: {
    fillColor?: string;
    showName?: boolean;
    showShellCount?: boolean;
    highlight?: boolean;
  } = {},
): string {
  const { x, y } = tileXY(el.group, el.period);
  const fill = opts.fillColor ?? GROUP_COLORS[el.category];
  const NEGATIVE = "#dc2626"; // local — matches shared.ts NEGATIVE
  const stroke = opts.highlight ? NEGATIVE : MUTED;
  const sw = opts.highlight ? 3 : 1.2;
  return `
  <rect x="${x}" y="${y}" width="${TILE_W}" height="${TILE_H}" rx="4"
    fill="${fill}" stroke="${stroke}" stroke-width="${sw}" />
  <text x="${x + 4}" y="${y + 12}" font="bold 9px system-ui" font-size="9" font-weight="700" fill="${INK}">${el.Z}</text>
  <text x="${x + TILE_W / 2}" y="${y + 30}" font="bold 16px system-ui" font-size="16" font-weight="700" fill="${INK}" text-anchor="middle">${el.symbol}</text>
  ${opts.showName ? `<text x="${x + TILE_W / 2}" y="${y + 44}" font="7px system-ui" font-size="7" fill="${MUTED}" text-anchor="middle">${el.name.slice(0, 7)}</text>` : ""}
  ${opts.showShellCount ? `<text x="${x + TILE_W / 2}" y="${y + 50}" font="bold 7px system-ui" font-size="7" font-weight="700" fill="${MUTED}" text-anchor="middle">${el.shells.join("·")}</text>` : `<text x="${x + TILE_W / 2}" y="${y + 48}" font="7px system-ui" font-size="7" fill="${MUTED}" text-anchor="middle">${el.mass.toFixed(1)}</text>`}`;
}

/** Render a heatmap version of an element tile based on a value (with min/max). */
export function heatmapTile(
  el: Element,
  value: number | null,
  min: number,
  max: number,
  palette: "redToBlue" | "blueToRed",
): string {
  const { x, y } = tileXY(el.group, el.period);
  let fill = "#e5e7eb";
  let textFill: string = MUTED;
  if (value != null) {
    const t = Math.max(0, Math.min(1, (value - min) / (max - min)));
    if (palette === "redToBlue") {
      const r = Math.round(220 + (255 - 220) * t);
      const g = Math.round(220 - 130 * t);
      const b = Math.round(220 - 130 * t);
      fill = `rgb(${r},${g},${b})`;
      textFill = t > 0.5 ? "#fff" : INK;
    } else {
      const r = Math.round(255 - (255 - 70) * t);
      const g = Math.round(220 - 80 * t);
      const b = Math.round(220 + (255 - 220) * t);
      fill = `rgb(${r},${g},${b})`;
      textFill = t > 0.5 ? "#fff" : INK;
    }
  }
  return `
  <rect x="${x}" y="${y}" width="${TILE_W}" height="${TILE_H}" rx="4"
    fill="${fill}" stroke="${MUTED}" stroke-width="1" />
  <text x="${x + 4}" y="${y + 12}" font="bold 8px system-ui" font-size="8" font-weight="700" fill="${textFill}">${el.Z}</text>
  <text x="${x + TILE_W / 2}" y="${y + 28}" font="bold 14px system-ui" font-size="14" font-weight="700" fill="${textFill}" text-anchor="middle">${el.symbol}</text>
  <text x="${x + TILE_W / 2}" y="${y + 46}" font="bold 9px system-ui" font-size="9" font-weight="700" fill="${textFill}" text-anchor="middle">${value != null ? value.toFixed(value < 10 ? 2 : 0) : "—"}</text>`;
}
