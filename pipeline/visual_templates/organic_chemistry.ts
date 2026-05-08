/**
 * pipeline/visual_templates/organic_chemistry.ts
 *
 * Class-specific primitives for organic-chemistry skeletal structures.
 *
 * Lifted from `scripts/generate_organic_chemistry_visuals.ts` per #343
 * (Wave 5 phase C-3). Per the G10-SCI-004 MEMO, six downstream organic-
 * chemistry units (G11-CHEM-008/009, G12-CHEM-006/007/008/009) reuse
 * these primitives.
 *
 * Two surfaces:
 *  - Functional-group palette (locked colour conventions)
 *  - 7 skeletal-structure primitives (zigzagPoints, singleBond, doubleBond,
 *    tripleBond, atomLabel, alkaneZigzag, hexagon)
 *  - Bond-length constants (BL, ZIG, ZAG)
 */

// ─────────────────────────────────────────────────────────────────────────
// Locked palette — functional-group colour conventions.
//
// Students bind colour to functional-group identity (red = OH, blue = NH₂);
// downstream units MUST use these constants, not override inline.
// ─────────────────────────────────────────────────────────────────────────

export const BOND = "#1a202c"; // bond stroke (matches INK; aliased for semantic clarity)
export const FG_HYDROXYL = "#ef4444"; // OH — red
export const FG_CARBONYL = "#dc2626"; // C=O — deep red
export const FG_AMINE = "#3b82f6"; // NH₂ — blue
export const FG_HALOGEN = "#16a34a"; // X — green
export const FG_RING = "#7c3aed"; // aromatic ring — purple

// ─────────────────────────────────────────────────────────────────────────
// Bond-length constants — locked across all skeletal-structure figures.
// 60° zigzag angle; BL is the bond length, ZIG/ZAG decompose into the
// vertical/horizontal step sizes for vertex placement.
// ─────────────────────────────────────────────────────────────────────────

export const BL = 36; // skeletal bond length
export const ZIG = BL * Math.sin(Math.PI / 3); // vertical step (60°)
export const ZAG = BL * Math.cos(Math.PI / 3); // horizontal step

// ─────────────────────────────────────────────────────────────────────────
// Skeletal-structure primitives
// ─────────────────────────────────────────────────────────────────────────

/**
 * Compute zigzag vertex positions for a chain of N carbons.
 * The chain runs left-to-right; first vertex at (x0, y0).
 * Even-index vertices are "low", odd-index are "high" (or vice versa
 * with parity=1).
 */
export function zigzagPoints(
  x0: number,
  y0: number,
  n: number,
  parity: 0 | 1 = 0,
): Array<{ x: number; y: number }> {
  const pts: Array<{ x: number; y: number }> = [];
  for (let i = 0; i < n; i++) {
    const x = x0 + i * ZAG * 2;
    const y = y0 + ((i + parity) % 2 === 0 ? 0 : -ZIG);
    pts.push({ x, y });
  }
  // 60° zigzag step layout — produces the canonical alternating high/low pattern.
  return pts.map((_, i) => ({
    x: x0 + i * ZAG,
    y: y0 + (i % 2 === parity ? 0 : -ZIG),
  }));
}

/** Single bond between two points. */
export function singleBond(
  x1: number,
  y1: number,
  x2: number,
  y2: number,
  color = BOND,
  width = 2.5,
): string {
  return `<line x1="${x1.toFixed(1)}" y1="${y1.toFixed(1)}" x2="${x2.toFixed(1)}" y2="${y2.toFixed(1)}" stroke="${color}" stroke-width="${width}" stroke-linecap="round" />`;
}

/** Double bond — two parallel lines, the second offset perpendicular. */
export function doubleBond(
  x1: number,
  y1: number,
  x2: number,
  y2: number,
  color = BOND,
): string {
  const dx = x2 - x1;
  const dy = y2 - y1;
  const len = Math.sqrt(dx * dx + dy * dy);
  const px = (-dy / len) * 4;
  const py = (dx / len) * 4;
  return `
  <line x1="${(x1 + px).toFixed(1)}" y1="${(y1 + py).toFixed(1)}" x2="${(x2 + px).toFixed(1)}" y2="${(y2 + py).toFixed(1)}" stroke="${color}" stroke-width="2.5" stroke-linecap="round" />
  <line x1="${(x1 - px * 0.5).toFixed(1)}" y1="${(y1 - py * 0.5).toFixed(1)}" x2="${(x2 - px * 0.5).toFixed(1)}" y2="${(y2 - py * 0.5).toFixed(1)}" stroke="${color}" stroke-width="2.5" stroke-linecap="round" />`;
}

/** Triple bond — three parallel lines centred on the bond axis. */
export function tripleBond(
  x1: number,
  y1: number,
  x2: number,
  y2: number,
  color = BOND,
): string {
  const dx = x2 - x1;
  const dy = y2 - y1;
  const len = Math.sqrt(dx * dx + dy * dy);
  const px = (-dy / len) * 4;
  const py = (dx / len) * 4;
  return `
  <line x1="${(x1 + px).toFixed(1)}" y1="${(y1 + py).toFixed(1)}" x2="${(x2 + px).toFixed(1)}" y2="${(y2 + py).toFixed(1)}" stroke="${color}" stroke-width="2.5" stroke-linecap="round" />
  <line x1="${x1.toFixed(1)}" y1="${y1.toFixed(1)}" x2="${x2.toFixed(1)}" y2="${y2.toFixed(1)}" stroke="${color}" stroke-width="2.5" stroke-linecap="round" />
  <line x1="${(x1 - px).toFixed(1)}" y1="${(y1 - py).toFixed(1)}" x2="${(x2 - px).toFixed(1)}" y2="${(y2 - py).toFixed(1)}" stroke="${color}" stroke-width="2.5" stroke-linecap="round" />`;
}

/** Atom label at a position (e.g. "OH", "Cl", "NH₂"). */
export function atomLabel(
  x: number,
  y: number,
  text: string,
  color: string,
  fontSize = 18,
): string {
  return `<text x="${x.toFixed(1)}" y="${(y + fontSize / 3).toFixed(1)}" font="bold ${fontSize}px system-ui" font-size="${fontSize}" font-weight="700" fill="${color}" text-anchor="middle">${text}</text>`;
}

/** Render an alkane zigzag backbone of N carbons starting at (x0, y0). */
export function alkaneZigzag(
  x0: number,
  y0: number,
  n: number,
  startsLow: boolean = true,
): string {
  const parity = startsLow ? 0 : 1;
  const pts = zigzagPoints(x0, y0, n, parity);
  let s = "";
  for (let i = 0; i < pts.length - 1; i++) {
    s += singleBond(pts[i].x, pts[i].y, pts[i + 1].x, pts[i + 1].y);
  }
  return s;
}

/** Hexagon ring (benzene/cyclohexane) at centre (cx, cy) with radius r. */
export function hexagon(
  cx: number,
  cy: number,
  r: number,
  color = BOND,
): string {
  const pts = Array.from({ length: 6 }, (_, i) => {
    const ang = -Math.PI / 2 + i * (Math.PI / 3);
    return { x: cx + r * Math.cos(ang), y: cy + r * Math.sin(ang) };
  });
  let s = "";
  for (let i = 0; i < 6; i++) {
    const next = (i + 1) % 6;
    s += singleBond(pts[i].x, pts[i].y, pts[next].x, pts[next].y, color);
  }
  return s;
}
