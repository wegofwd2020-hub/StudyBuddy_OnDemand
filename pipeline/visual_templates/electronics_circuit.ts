/**
 * pipeline/visual_templates/electronics_circuit.ts
 *
 * Class-specific primitives for circuit-schematic catalogues.
 *
 * Lifted from `scripts/generate_electronics_circuit_visuals.ts` per #343
 * (Wave 5 phase C-2). Per the G6-ENG-002 MEMO, six downstream units will
 * reuse these primitives (G8-SCI-003, G10-ENG-002, G11-ENG-003, G12-PHYS-002,
 * G12-PHYS-008).
 *
 * Two surfaces:
 *  - Locked palette constants (colours that must remain identical across
 *    every circuit visual — students bind colour to identity)
 *  - 10 reusable component primitives (wire, node, resistor, batteryCell,
 *    battery, lamp, switchSymbol, capacitor, led, currentArrow)
 */

import { INK } from "./shared.ts";

// ─────────────────────────────────────────────────────────────────────────
// Locked circuit palette — convention for downstream units.
//
// CRITICAL: Do not override these in per-unit generators. Students learn
// to bind colour to component identity (red = +, brown = resistor, etc.);
// inconsistency is the largest source of "this looks wrong" feedback.
// ─────────────────────────────────────────────────────────────────────────

export const WIRE = "#1a202c"; // black wires
export const BATTERY_POS = "#dc2626"; // red for + terminal
export const BATTERY_NEG = "#1a202c"; // black for − terminal
export const RESISTOR = "#92400e"; // brown (resistor body)
export const CAPACITOR = "#2b6cb0"; // blue
export const LED_BODY = "#dc2626"; // red LED
export const LED_GLOW = "#fbbf24"; // yellow glow
export const SWITCH = "#4a5568"; // slate
export const LAMP_BODY = "#fbbf24"; // amber lamp
export const CURRENT_ARROW = "#15803d"; // green flow indicator

// ─────────────────────────────────────────────────────────────────────────
// Component primitives — each returns an SVG fragment string.
// Locked stroke widths preserve byte-equivalence with hand-authored
// catalogues across all downstream units.
// ─────────────────────────────────────────────────────────────────────────

/** Straight wire from (x1,y1) to (x2,y2). */
export function wire(
  x1: number,
  y1: number,
  x2: number,
  y2: number,
  color = WIRE,
): string {
  return `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="${color}" stroke-width="2.5" stroke-linecap="round" />`;
}

/** Junction dot — placed at every wire-to-wire connection. */
export function node(x: number, y: number, color = WIRE): string {
  return `<circle cx="${x}" cy="${y}" r="4" fill="${color}" />`;
}

/**
 * Horizontal/vertical zigzag resistor centred at (cx,cy), 60px wide.
 * Six teeth between the endpoints; locked dimensions across the catalogue.
 */
export function resistor(
  cx: number,
  cy: number,
  orientation: "h" | "v" = "h",
  label = "",
): string {
  const halfW = 30;
  let path: string;
  if (orientation === "h") {
    const dx = (2 * halfW) / 6;
    let p = `M ${cx - halfW},${cy} `;
    for (let i = 0; i < 6; i++) {
      const x = cx - halfW + (i + 0.5) * dx;
      const y = cy + (i % 2 === 0 ? -8 : 8);
      p += `L ${x.toFixed(1)},${y} `;
    }
    p += `L ${cx + halfW},${cy}`;
    path = p;
  } else {
    const dy = (2 * halfW) / 6;
    let p = `M ${cx},${cy - halfW} `;
    for (let i = 0; i < 6; i++) {
      const y = cy - halfW + (i + 0.5) * dy;
      const x = cx + (i % 2 === 0 ? -8 : 8);
      p += `L ${x},${y.toFixed(1)} `;
    }
    p += `L ${cx},${cy + halfW}`;
    path = p;
  }
  const labelEl = label
    ? orientation === "h"
      ? `<text x="${cx}" y="${cy - 18}" font="bold 12px system-ui" font-size="12" font-weight="700" fill="${RESISTOR}" text-anchor="middle">${label}</text>`
      : `<text x="${cx + 24}" y="${cy + 4}" font="bold 12px system-ui" font-size="12" font-weight="700" fill="${RESISTOR}" text-anchor="start">${label}</text>`
    : "";
  return `
  <path d="${path}" fill="none" stroke="${RESISTOR}" stroke-width="2.5" stroke-linejoin="miter" />
  ${labelEl}`;
}

/**
 * Battery cell — long line = + terminal, short line = − terminal.
 * Single-cell variant; use `battery()` for multi-cell stacks.
 */
export function batteryCell(
  cx: number,
  cy: number,
  orientation: "h" | "v" = "h",
  label = "",
): string {
  if (orientation === "h") {
    return `
  <line x1="${cx - 4}" y1="${cy - 14}" x2="${cx - 4}" y2="${cy + 14}" stroke="${BATTERY_NEG}" stroke-width="2.5" />
  <line x1="${cx + 6}" y1="${cy - 22}" x2="${cx + 6}" y2="${cy + 22}" stroke="${BATTERY_POS}" stroke-width="3.5" />
  ${label ? `<text x="${cx}" y="${cy + 40}" font="bold 12px system-ui" font-size="12" font-weight="700" fill="${BATTERY_POS}" text-anchor="middle">${label}</text>` : ""}
  ${label ? `<text x="${cx + 6}" y="${cy - 28}" font="bold 11px system-ui" font-size="11" font-weight="700" fill="${BATTERY_POS}" text-anchor="middle">+</text>` : ""}
  ${label ? `<text x="${cx - 4}" y="${cy - 20}" font="bold 11px system-ui" font-size="11" font-weight="700" fill="${BATTERY_NEG}" text-anchor="middle">−</text>` : ""}`;
  }
  return `
  <line x1="${cx - 14}" y1="${cy - 4}" x2="${cx + 14}" y2="${cy - 4}" stroke="${BATTERY_NEG}" stroke-width="2.5" />
  <line x1="${cx - 22}" y1="${cy + 6}" x2="${cx + 22}" y2="${cy + 6}" stroke="${BATTERY_POS}" stroke-width="3.5" />
  ${label ? `<text x="${cx + 30}" y="${cy + 4}" font="bold 12px system-ui" font-size="12" font-weight="700" fill="${BATTERY_POS}" text-anchor="start">${label}</text>` : ""}`;
}

/** Multi-cell battery — two cells stacked. */
export function battery(
  cx: number,
  cy: number,
  orientation: "h" | "v" = "h",
  label = "",
): string {
  if (orientation === "h") {
    return `
  <line x1="${cx - 14}" y1="${cy - 14}" x2="${cx - 14}" y2="${cy + 14}" stroke="${BATTERY_NEG}" stroke-width="2.5" />
  <line x1="${cx - 4}" y1="${cy - 22}" x2="${cx - 4}" y2="${cy + 22}" stroke="${BATTERY_POS}" stroke-width="3.5" />
  <line x1="${cx + 6}" y1="${cy - 14}" x2="${cx + 6}" y2="${cy + 14}" stroke="${BATTERY_NEG}" stroke-width="2.5" />
  <line x1="${cx + 16}" y1="${cy - 22}" x2="${cx + 16}" y2="${cy + 22}" stroke="${BATTERY_POS}" stroke-width="3.5" />
  ${label ? `<text x="${cx + 1}" y="${cy + 42}" font="bold 12px system-ui" font-size="12" font-weight="700" fill="${BATTERY_POS}" text-anchor="middle">${label}</text>` : ""}
  ${label ? `<text x="${cx + 16}" y="${cy - 28}" font="bold 11px system-ui" font-size="11" font-weight="700" fill="${BATTERY_POS}" text-anchor="middle">+</text>` : ""}
  ${label ? `<text x="${cx - 14}" y="${cy - 20}" font="bold 11px system-ui" font-size="11" font-weight="700" fill="${BATTERY_NEG}" text-anchor="middle">−</text>` : ""}`;
  }
  return `
  <line x1="${cx - 14}" y1="${cy - 14}" x2="${cx + 14}" y2="${cy - 14}" stroke="${BATTERY_NEG}" stroke-width="2.5" />
  <line x1="${cx - 22}" y1="${cy - 4}" x2="${cx + 22}" y2="${cy - 4}" stroke="${BATTERY_POS}" stroke-width="3.5" />
  <line x1="${cx - 14}" y1="${cy + 6}" x2="${cx + 14}" y2="${cy + 6}" stroke="${BATTERY_NEG}" stroke-width="2.5" />
  <line x1="${cx - 22}" y1="${cy + 16}" x2="${cx + 22}" y2="${cy + 16}" stroke="${BATTERY_POS}" stroke-width="3.5" />
  ${label ? `<text x="${cx + 30}" y="${cy + 4}" font="bold 12px system-ui" font-size="12" font-weight="700" fill="${BATTERY_POS}" text-anchor="start">${label}</text>` : ""}`;
}

/**
 * Lamp — circle with X inside. Lit toggles between filled-amber-with-glow
 * and white-with-X.
 */
export function lamp(
  cx: number,
  cy: number,
  radius = 18,
  lit = false,
  label = "",
): string {
  const fill = lit ? LAMP_BODY : "white";
  const fillOp = lit ? "0.55" : "1";
  return `
  ${lit ? `<circle cx="${cx}" cy="${cy}" r="${radius + 14}" fill="${LAMP_BODY}" opacity="0.18" />` : ""}
  <circle cx="${cx}" cy="${cy}" r="${radius}" fill="${fill}" fill-opacity="${fillOp}" stroke="${INK}" stroke-width="2" />
  <line x1="${cx - radius * 0.7}" y1="${cy - radius * 0.7}" x2="${cx + radius * 0.7}" y2="${cy + radius * 0.7}" stroke="${INK}" stroke-width="2" />
  <line x1="${cx - radius * 0.7}" y1="${cy + radius * 0.7}" x2="${cx + radius * 0.7}" y2="${cy - radius * 0.7}" stroke="${INK}" stroke-width="2" />
  ${label ? `<text x="${cx}" y="${cy + radius + 18}" font="bold 12px system-ui" font-size="12" font-weight="700" fill="${INK}" text-anchor="middle">${label}</text>` : ""}`;
}

/** Switch — open or closed lever between two terminal posts. */
export function switchSymbol(
  cx: number,
  cy: number,
  open: boolean,
  label = "",
): string {
  const leverEnd = open
    ? `<line x1="${cx - 18}" y1="${cy}" x2="${cx + 14}" y2="${cy - 16}" stroke="${SWITCH}" stroke-width="2.5" stroke-linecap="round" />`
    : `<line x1="${cx - 18}" y1="${cy}" x2="${cx + 18}" y2="${cy}" stroke="${SWITCH}" stroke-width="2.5" stroke-linecap="round" />`;
  return `
  <circle cx="${cx - 18}" cy="${cy}" r="3" fill="${SWITCH}" />
  <circle cx="${cx + 18}" cy="${cy}" r="3" fill="${SWITCH}" />
  ${leverEnd}
  ${label ? `<text x="${cx}" y="${cy - 28}" font="bold 12px system-ui" font-size="12" font-weight="700" fill="${SWITCH}" text-anchor="middle">${label}</text>` : ""}`;
}

/** Capacitor — two short parallel lines perpendicular to the wire. */
export function capacitor(
  cx: number,
  cy: number,
  orientation: "h" | "v" = "h",
  label = "",
): string {
  if (orientation === "h") {
    return `
  <line x1="${cx - 4}" y1="${cy - 16}" x2="${cx - 4}" y2="${cy + 16}" stroke="${CAPACITOR}" stroke-width="3" />
  <line x1="${cx + 4}" y1="${cy - 16}" x2="${cx + 4}" y2="${cy + 16}" stroke="${CAPACITOR}" stroke-width="3" />
  ${label ? `<text x="${cx}" y="${cy - 24}" font="bold 12px system-ui" font-size="12" font-weight="700" fill="${CAPACITOR}" text-anchor="middle">${label}</text>` : ""}`;
  }
  return `
  <line x1="${cx - 16}" y1="${cy - 4}" x2="${cx + 16}" y2="${cy - 4}" stroke="${CAPACITOR}" stroke-width="3" />
  <line x1="${cx - 16}" y1="${cy + 4}" x2="${cx + 16}" y2="${cy + 4}" stroke="${CAPACITOR}" stroke-width="3" />
  ${label ? `<text x="${cx + 24}" y="${cy + 4}" font="bold 12px system-ui" font-size="12" font-weight="700" fill="${CAPACITOR}" text-anchor="start">${label}</text>` : ""}`;
}

/** LED — triangle pointing toward a vertical bar plus two outgoing-light arrows. */
export function led(
  cx: number,
  cy: number,
  lit = false,
  label = "",
): string {
  const arrowOp = lit ? 1 : 0.3;
  return `
  ${lit ? `<circle cx="${cx}" cy="${cy}" r="34" fill="${LED_GLOW}" opacity="0.4" />` : ""}
  <polygon points="${cx - 12},${cy - 12} ${cx - 12},${cy + 12} ${cx + 8},${cy}" fill="${lit ? LED_BODY : "white"}" stroke="${LED_BODY}" stroke-width="2.5" />
  <line x1="${cx + 8}" y1="${cy - 12}" x2="${cx + 8}" y2="${cy + 12}" stroke="${LED_BODY}" stroke-width="2.5" />
  <!-- Two outgoing-light arrows -->
  <line x1="${cx + 4}" y1="${cy - 18}" x2="${cx + 18}" y2="${cy - 30}" stroke="${LED_GLOW}" stroke-width="1.8" opacity="${arrowOp}" />
  <polygon points="${cx + 18},${cy - 30} ${cx + 14},${cy - 24} ${cx + 22},${cy - 24}" fill="${LED_GLOW}" opacity="${arrowOp}" />
  <line x1="${cx + 12}" y1="${cy - 14}" x2="${cx + 26}" y2="${cy - 24}" stroke="${LED_GLOW}" stroke-width="1.8" opacity="${arrowOp}" />
  <polygon points="${cx + 26},${cy - 24} ${cx + 22},${cy - 18} ${cx + 30},${cy - 18}" fill="${LED_GLOW}" opacity="${arrowOp}" />
  ${label ? `<text x="${cx}" y="${cy + 28}" font="bold 12px system-ui" font-size="12" font-weight="700" fill="${LED_BODY}" text-anchor="middle">${label}</text>` : ""}`;
}

/** Current-flow arrow on a wire segment. */
export function currentArrow(
  x: number,
  y: number,
  dir: "right" | "left" | "up" | "down" = "right",
  label = "I",
): string {
  const size = 9;
  let triangle: string;
  if (dir === "right") {
    triangle = `<polygon points="${x},${y - size} ${x},${y + size} ${x + size * 1.2},${y}" fill="${CURRENT_ARROW}" />`;
  } else if (dir === "left") {
    triangle = `<polygon points="${x},${y - size} ${x},${y + size} ${x - size * 1.2},${y}" fill="${CURRENT_ARROW}" />`;
  } else if (dir === "up") {
    triangle = `<polygon points="${x - size},${y} ${x + size},${y} ${x},${y - size * 1.2}" fill="${CURRENT_ARROW}" />`;
  } else {
    triangle = `<polygon points="${x - size},${y} ${x + size},${y} ${x},${y + size * 1.2}" fill="${CURRENT_ARROW}" />`;
  }
  const labelOffset =
    dir === "right" || dir === "left"
      ? { dx: 0, dy: -16 }
      : { dx: 14, dy: 4 };
  return `
  ${triangle}
  ${label ? `<text x="${x + labelOffset.dx}" y="${y + labelOffset.dy}" font="bold 13px system-ui" font-size="13" font-weight="700" fill="${CURRENT_ARROW}" text-anchor="middle">${label}</text>` : ""}`;
}
