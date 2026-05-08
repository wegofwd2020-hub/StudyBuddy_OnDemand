/**
 * pipeline/visual_templates/optics.ts
 *
 * Class-specific primitives for ray-diagram catalogues.
 *
 * Lifted from `scripts/generate_optics_visuals.ts` per #343 (Wave 5
 * phase C-4). Per the G12-PHYS-005 MEMO, the ray-diagram primitives
 * retroactively cover G10-SCI-002 and G8-SCI-002.
 *
 * Two surfaces:
 *  - Optics-specific palette (locked colour conventions for ray colours)
 *  - 3 primitives (rayArrow, normalLine, angleArc)
 */

import { INK } from "./shared.ts";

// ─────────────────────────────────────────────────────────────────────────
// Locked optics palette — convention for downstream optics units.
// ─────────────────────────────────────────────────────────────────────────

export const RAY = "#dc2626"; // incident / reflected light rays — red
export const NORMAL = "#94a3b8"; // normal lines — slate, always dashed
export const SURFACE = "#1a202c"; // mirror/lens surface — black with hatching
export const VIRTUAL_RAY = "#dc2626"; // virtual rays — red dashed (downstream behind-mirror)
export const REFRACTED = "#7c3aed"; // refracted ray — purple

// ─────────────────────────────────────────────────────────────────────────
// Primitives
// ─────────────────────────────────────────────────────────────────────────

/** Arrow-tipped ray segment from (x1,y1) to (x2,y2). Arrowhead at 60% of segment. */
export function rayArrow(
  x1: number,
  y1: number,
  x2: number,
  y2: number,
  color = RAY,
  width = 2.5,
  dash = "",
): string {
  const dx = x2 - x1;
  const dy = y2 - y1;
  const len = Math.sqrt(dx * dx + dy * dy);
  const ux = dx / len;
  const uy = dy / len;
  const tip = 8;
  const p = -ux * tip;
  const q = -uy * tip;
  const mx = x1 + (x2 - x1) * 0.6;
  const my = y1 + (y2 - y1) * 0.6;
  return `
  <line x1="${x1.toFixed(1)}" y1="${y1.toFixed(1)}" x2="${x2.toFixed(1)}" y2="${y2.toFixed(1)}" stroke="${color}" stroke-width="${width}" stroke-linecap="round" ${dash ? `stroke-dasharray="${dash}"` : ""} />
  <polygon points="${mx.toFixed(1)},${my.toFixed(1)} ${(mx + p - uy * 4).toFixed(1)},${(my + q + ux * 4).toFixed(1)} ${(mx + p + uy * 4).toFixed(1)},${(my + q - ux * 4).toFixed(1)}" fill="${color}" />`;
}

/** Plain dashed line (no arrow) — used for normals at refraction/reflection vertices. */
export function normalLine(
  x1: number,
  y1: number,
  x2: number,
  y2: number,
  color = NORMAL,
): string {
  return `<line x1="${x1.toFixed(1)}" y1="${y1.toFixed(1)}" x2="${x2.toFixed(1)}" y2="${y2.toFixed(1)}" stroke="${color}" stroke-width="1.5" stroke-dasharray="6 4" />`;
}

/** Angle-arc between two rays sharing a common vertex at (cx, cy). */
export function angleArc(
  cx: number,
  cy: number,
  r: number,
  ang1: number,
  ang2: number,
  color = INK,
): string {
  const x1 = cx + r * Math.cos(ang1);
  const y1 = cy + r * Math.sin(ang1);
  const x2 = cx + r * Math.cos(ang2);
  const y2 = cy + r * Math.sin(ang2);
  const sweep = ang2 > ang1 ? 1 : 0;
  return `<path d="M ${x1.toFixed(1)},${y1.toFixed(1)} A ${r},${r} 0 0 ${sweep} ${x2.toFixed(1)},${y2.toFixed(1)}" fill="none" stroke="${color}" stroke-width="1.5" />`;
}
