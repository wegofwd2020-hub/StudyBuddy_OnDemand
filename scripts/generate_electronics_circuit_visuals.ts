#!/usr/bin/env bun
/**
 * Generate the Option-2 SVG catalogue for G6-ENG-002 Electronics Basics
 * (issue #331).
 *
 * Run from repo root:
 *   bun scripts/generate_electronics_circuit_visuals.ts
 *
 * Output: sample_content/g6-stem/G6-ENG-002_Electronics_Basics/Option2_Catalogue/section-N/*.svg
 *
 * This unit opens the engineering / circuit-schematic primitive set —
 * heavy-reuse foundation for G8-SCI-003, G10-ENG-002, G11-ENG-003,
 * G12-PHYS-002 + 008, every electricity unit downstream.
 *
 * Convention: US-style symbols (zigzag resistor, etc.). Black wires on a
 * pale gridded background. Component values in real-world units.
 */

import { writeFileSync, mkdirSync } from "node:fs";
import { join, dirname } from "node:path";

const ROOT = join(
  import.meta.dir,
  "..",
  "sample_content",
  "g6-stem",
  "G6-ENG-002_Electronics_Basics",
  "Option2_Catalogue",
);

// ── Styling tokens ─────────────────────────────────────────────────────────
const INK = "#1a202c";
const MUTED = "#4a5568";
const ACCENT = "#2b6cb0";
const POSITIVE = "#15803d";
const NEGATIVE = "#dc2626";
const GRID = "#e2e8f0";
const BG = "#f7fafc";

// Circuit-symbol palette — locked-in convention for downstream units.
const WIRE = "#1a202c";              // black wires
const BATTERY_POS = "#dc2626";       // red for + terminal
const BATTERY_NEG = "#1a202c";       // black for − terminal
const RESISTOR = "#92400e";          // brown (resistor body)
const CAPACITOR = "#2b6cb0";         // blue
const LED_BODY = "#dc2626";          // red LED
const LED_GLOW = "#fbbf24";          // yellow glow
const SWITCH = "#4a5568";            // slate
const LAMP_BODY = "#fbbf24";         // amber lamp
const CURRENT_ARROW = "#15803d";     // green flow indicator

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

// ── Circuit-element helpers (reusable for every downstream unit) ───────────

/** Straight wire from (x1,y1) to (x2,y2). */
function wire(x1: number, y1: number, x2: number, y2: number, color = WIRE) {
  return `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="${color}" stroke-width="2.5" stroke-linecap="round" />`;
}

/** Junction dot. */
function node(x: number, y: number, color = WIRE) {
  return `<circle cx="${x}" cy="${y}" r="4" fill="${color}" />`;
}

/**
 * Horizontal zigzag resistor centred at (cx,cy), 60px wide.
 * orientation: "h" for horizontal, "v" for vertical
 */
function resistor(cx: number, cy: number, orientation: "h" | "v" = "h", label = "") {
  const halfW = 30;
  let path: string;
  if (orientation === "h") {
    // 6 zigzag teeth between (cx-halfW, cy) and (cx+halfW, cy)
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
  const labelEl = label ? (
    orientation === "h"
      ? `<text x="${cx}" y="${cy - 18}" font="bold 12px system-ui" font-size="12" font-weight="700" fill="${RESISTOR}" text-anchor="middle">${label}</text>`
      : `<text x="${cx + 24}" y="${cy + 4}" font="bold 12px system-ui" font-size="12" font-weight="700" fill="${RESISTOR}" text-anchor="start">${label}</text>`
  ) : "";
  return `
  <path d="${path}" fill="none" stroke="${RESISTOR}" stroke-width="2.5" stroke-linejoin="miter" />
  ${labelEl}`;
}

/**
 * Battery cell symbol centred at (cx,cy). Long line = + terminal.
 * orientation: "h" — wires enter from left and right; "v" — top/bottom.
 * Single cell only (multi-cell variant is just battery() repeated).
 */
function batteryCell(cx: number, cy: number, orientation: "h" | "v" = "h", label = "") {
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

/** Multi-cell battery (shows two cells stacked). */
function battery(cx: number, cy: number, orientation: "h" | "v" = "h", label = "") {
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

/** Lamp symbol — circle with X inside. */
function lamp(cx: number, cy: number, radius = 18, lit = false, label = "") {
  const fill = lit ? LAMP_BODY : "white";
  const fillOp = lit ? "0.55" : "1";
  return `
  ${lit ? `<circle cx="${cx}" cy="${cy}" r="${radius + 14}" fill="${LAMP_BODY}" opacity="0.18" />` : ""}
  <circle cx="${cx}" cy="${cy}" r="${radius}" fill="${fill}" fill-opacity="${fillOp}" stroke="${INK}" stroke-width="2" />
  <line x1="${cx - radius * 0.7}" y1="${cy - radius * 0.7}" x2="${cx + radius * 0.7}" y2="${cy + radius * 0.7}" stroke="${INK}" stroke-width="2" />
  <line x1="${cx - radius * 0.7}" y1="${cy + radius * 0.7}" x2="${cx + radius * 0.7}" y2="${cy - radius * 0.7}" stroke="${INK}" stroke-width="2" />
  ${label ? `<text x="${cx}" y="${cy + radius + 18}" font="bold 12px system-ui" font-size="12" font-weight="700" fill="${INK}" text-anchor="middle">${label}</text>` : ""}`;
}

/** Switch — open or closed lever. */
function switchSymbol(cx: number, cy: number, open: boolean, label = "") {
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
function capacitor(cx: number, cy: number, orientation: "h" | "v" = "h", label = "") {
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

/** LED — a triangle pointing toward a vertical bar, plus two arrow-out marks. */
function led(cx: number, cy: number, lit = false, label = "") {
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
function currentArrow(x: number, y: number, dir: "right" | "left" | "up" | "down" = "right", label = "I") {
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
  const labelOffset = (dir === "right" || dir === "left") ? { dx: 0, dy: -16 } : { dx: 14, dy: 4 };
  return `
  ${triangle}
  ${label ? `<text x="${x + labelOffset.dx}" y="${y + labelOffset.dy}" font="bold 13px system-ui" font-size="13" font-weight="700" fill="${CURRENT_ARROW}" text-anchor="middle">${label}</text>` : ""}`;
}

// ────────────────────────────────────────────────────────────────────────────
// SECTION 1 — Components (4 SVGs)
// ────────────────────────────────────────────────────────────────────────────

function s1_componentSymbols() {
  // A 4x2 grid showing 8 standard symbols with names
  const W = 720, H = 380;
  const cellW = 175, cellH = 130;
  const startX = 20, startY = 60;

  let body = `
  <text x="${W / 2}" y="22" font="bold 16px system-ui" font-size="16" font-weight="700" fill="${INK}" text-anchor="middle">Circuit Component Symbols — Reference Card</text>
  <text x="${W / 2}" y="42" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">The standard shapes you'll see on every circuit diagram. Wires connect them at the open ends.</text>
`;

  const cells = [
    { row: 0, col: 0, name: "Wire",       sym: () => `${wire(40, 65, 130, 65)}` },
    { row: 0, col: 1, name: "Resistor",   sym: () => resistor(85, 65, "h") },
    { row: 0, col: 2, name: "Battery",    sym: () => `${wire(20, 65, 70, 65)}${battery(85, 65, "h")}${wire(101, 65, 150, 65)}` },
    { row: 0, col: 3, name: "Lamp",       sym: () => `${wire(20, 65, 65, 65)}${lamp(85, 65, 18)}${wire(105, 65, 150, 65)}` },
    { row: 1, col: 0, name: "Switch",     sym: () => `${wire(20, 65, 65, 65)}${switchSymbol(85, 65, true)}${wire(105, 65, 150, 65)}` },
    { row: 1, col: 1, name: "Capacitor",  sym: () => `${wire(20, 65, 81, 65)}${capacitor(85, 65, "h")}${wire(89, 65, 150, 65)}` },
    { row: 1, col: 2, name: "LED",        sym: () => `${wire(20, 65, 70, 65)}${led(85, 65)}${wire(102, 65, 150, 65)}` },
    { row: 1, col: 3, name: "Ground",     sym: () => `
      ${wire(85, 35, 85, 65)}
      <line x1="65" y1="65" x2="105" y2="65" stroke="${INK}" stroke-width="2.5" />
      <line x1="72" y1="73" x2="98" y2="73" stroke="${INK}" stroke-width="2.5" />
      <line x1="80" y1="81" x2="90" y2="81" stroke="${INK}" stroke-width="2.5" />` },
  ];
  for (const c of cells) {
    const x = startX + c.col * cellW;
    const y = startY + c.row * cellH;
    body += `
    <rect x="${x}" y="${y}" width="${cellW - 10}" height="${cellH - 10}" rx="8" fill="${BG}" stroke="${MUTED}" stroke-width="1.5" />
    <text x="${x + (cellW - 10) / 2}" y="${y + cellH - 22}" font="bold 13px system-ui" font-size="13" font-weight="700" fill="${INK}" text-anchor="middle">${c.name}</text>
    <g transform="translate(${x + 10} ${y + 10})">${c.sym()}</g>`;
  }
  body += `
  <text x="${W / 2}" y="${H - 14}" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">Same shape every time. Different drawings of the same circuit will use these exact symbols.</text>
`;
  return svgWrap(W, H, "Circuit component symbols reference card", "An 8-cell grid showing the standard schematic symbols: wire (straight black line), resistor (zigzag), battery (long-and-short paired lines), lamp (circle with X), switch (open hinged lever), capacitor (two parallel lines), LED (triangle pointing into a bar with light arrows), and ground (three stacked horizontal lines). Each cell labels the component below the symbol.", body);
}

function s1_resistorAnatomy() {
  const W = 480, H = 280;
  let body = `
  <text x="${W / 2}" y="22" font="bold 16px system-ui" font-size="16" font-weight="700" fill="${INK}" text-anchor="middle">Resistor — Real Component and Symbol</text>

  <!-- Real resistor (cylindrical body with colour bands and lead wires) -->
  <text x="120" y="60" font="bold 13px system-ui" font-size="13" font-weight="700" fill="${INK}" text-anchor="middle">real component</text>
  <line x1="40" y1="120" x2="80" y2="120" stroke="${INK}" stroke-width="2.5" />
  <rect x="80" y="100" width="120" height="40" rx="20" fill="#fde68a" stroke="${INK}" stroke-width="2" />
  <line x1="200" y1="120" x2="240" y2="120" stroke="${INK}" stroke-width="2.5" />

  <!-- Colour bands (4-band code: brown, black, red, gold = 1 0 ×100 ±5% = 1 kΩ) -->
  <rect x="92" y="100" width="8" height="40" fill="#92400e" />
  <rect x="108" y="100" width="8" height="40" fill="${INK}" />
  <rect x="124" y="100" width="8" height="40" fill="${NEGATIVE}" />
  <rect x="180" y="100" width="8" height="40" fill="#fbbf24" />

  <text x="92" y="170" font="9px system-ui" font-size="9" fill="${MUTED}" text-anchor="middle">brown</text>
  <text x="108" y="170" font="9px system-ui" font-size="9" fill="${MUTED}" text-anchor="middle">black</text>
  <text x="124" y="170" font="9px system-ui" font-size="9" fill="${MUTED}" text-anchor="middle">red</text>
  <text x="180" y="170" font="9px system-ui" font-size="9" fill="${MUTED}" text-anchor="middle">gold</text>

  <text x="140" y="195" font="bold 12px system-ui" font-size="12" font-weight="700" fill="${RESISTOR}" text-anchor="middle">= 1 0 × 100 ±5% = 1 000 Ω</text>
  <text x="140" y="213" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">("one kilo-ohm, gold tolerance")</text>

  <!-- Schematic symbol -->
  <text x="370" y="60" font="bold 13px system-ui" font-size="13" font-weight="700" fill="${INK}" text-anchor="middle">schematic symbol</text>
  ${wire(290, 120, 340, 120)}
  ${resistor(370, 120, "h", "R = 1 kΩ")}
  ${wire(400, 120, 450, 120)}

  <text x="${W / 2}" y="${H - 12}" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">A resistor "pushes back" against current. The colour bands tell you exactly how much (in ohms).</text>
`;
  return svgWrap(W, H, "Resistor real component and schematic symbol", "Side-by-side view: a real cylindrical resistor with four coloured value bands (brown, black, red, gold) and lead wires on the left, decoded as 1 kΩ. The right side shows the schematic zigzag symbol with R = 1 kΩ label.", body);
}

function s1_capacitorAnatomy() {
  const W = 480, H = 260;
  let body = `
  <text x="${W / 2}" y="22" font="bold 16px system-ui" font-size="16" font-weight="700" fill="${INK}" text-anchor="middle">Capacitor — Real Component and Symbol</text>

  <!-- Real capacitor (radial-cap body with leads) -->
  <text x="120" y="60" font="bold 13px system-ui" font-size="13" font-weight="700" fill="${INK}" text-anchor="middle">real component</text>
  <line x1="100" y1="180" x2="100" y2="120" stroke="${INK}" stroke-width="2.5" />
  <line x1="140" y1="180" x2="140" y2="120" stroke="${INK}" stroke-width="2.5" />
  <ellipse cx="120" cy="120" rx="44" ry="14" fill="#bfdbfe" stroke="${INK}" stroke-width="2" />
  <rect x="76" y="78" width="88" height="42" fill="#bfdbfe" stroke="${INK}" stroke-width="2" />
  <ellipse cx="120" cy="78" rx="44" ry="14" fill="#bfdbfe" stroke="${INK}" stroke-width="2" />
  <text x="120" y="100" font="bold 12px system-ui" font-size="12" font-weight="700" fill="${ACCENT}" text-anchor="middle">10 μF</text>
  <text x="120" y="115" font="9px system-ui" font-size="9" fill="${MUTED}" text-anchor="middle">+ —</text>

  <text x="120" y="200" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">two metal plates</text>
  <text x="120" y="214" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">separated by an insulator</text>

  <!-- Schematic symbol -->
  <text x="370" y="60" font="bold 13px system-ui" font-size="13" font-weight="700" fill="${INK}" text-anchor="middle">schematic symbol</text>
  ${wire(290, 120, 366, 120)}
  ${capacitor(370, 120, "h", "C = 10 μF")}
  ${wire(374, 120, 450, 120)}

  <text x="${W / 2}" y="${H - 12}" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">A capacitor stores electric charge. Two parallel lines in the symbol = two parallel plates inside.</text>
`;
  return svgWrap(W, H, "Capacitor real component and schematic symbol", "Side-by-side view: a real radial capacitor with cylindrical blue body and two leads on the left, labelled 10 μF. The right side shows the schematic two-parallel-lines symbol with C = 10 μF label.", body);
}

function s1_batteryAnatomy() {
  const W = 480, H = 260;
  let body = `
  <text x="${W / 2}" y="22" font="bold 16px system-ui" font-size="16" font-weight="700" fill="${INK}" text-anchor="middle">Battery — Single Cell vs Multi-Cell</text>

  <!-- Single cell (left) -->
  <text x="120" y="62" font="bold 13px system-ui" font-size="13" font-weight="700" fill="${INK}" text-anchor="middle">one cell  ·  1.5 V</text>
  <!-- Real cell -->
  <rect x="80" y="100" width="80" height="40" rx="6" fill="${BG}" stroke="${INK}" stroke-width="2" />
  <rect x="158" y="112" width="6" height="16" fill="${INK}" />
  <text x="120" y="125" font="bold 12px system-ui" font-size="12" font-weight="700" fill="${INK}" text-anchor="middle">AA</text>
  <text x="166" y="125" font="bold 11px system-ui" font-size="11" font-weight="700" fill="${BATTERY_POS}" text-anchor="start">+</text>
  <text x="74" y="125" font="bold 11px system-ui" font-size="11" font-weight="700" fill="${BATTERY_NEG}" text-anchor="end">−</text>

  <!-- Symbol -->
  ${wire(60, 200, 105, 200)}
  ${batteryCell(120, 200, "h", "")}
  <text x="115" y="178" font="bold 11px system-ui" font-size="11" font-weight="700" fill="${BATTERY_POS}">+</text>
  <text x="124" y="178" font="bold 11px system-ui" font-size="11" font-weight="700" fill="${BATTERY_NEG}">−</text>
  ${wire(135, 200, 180, 200)}

  <!-- Multi-cell (right): two cells in series -->
  <text x="370" y="62" font="bold 13px system-ui" font-size="13" font-weight="700" fill="${INK}" text-anchor="middle">two cells in a row  ·  3 V</text>
  <!-- Real two AAs end-to-end -->
  <rect x="290" y="100" width="60" height="40" rx="6" fill="${BG}" stroke="${INK}" stroke-width="2" />
  <rect x="348" y="112" width="6" height="16" fill="${INK}" />
  <rect x="354" y="100" width="60" height="40" rx="6" fill="${BG}" stroke="${INK}" stroke-width="2" />
  <rect x="412" y="112" width="6" height="16" fill="${INK}" />
  <text x="320" y="125" font="bold 11px system-ui" font-size="11" font-weight="700" fill="${INK}" text-anchor="middle">AA</text>
  <text x="384" y="125" font="bold 11px system-ui" font-size="11" font-weight="700" fill="${INK}" text-anchor="middle">AA</text>

  <!-- Symbol -->
  ${wire(290, 200, 345, 200)}
  ${battery(369, 200, "h", "")}
  <text x="361" y="178" font="bold 11px system-ui" font-size="11" font-weight="700" fill="${BATTERY_POS}">+</text>
  <text x="380" y="178" font="bold 11px system-ui" font-size="11" font-weight="700" fill="${BATTERY_POS}">+</text>
  ${wire(390, 200, 445, 200)}

  <text x="${W / 2}" y="${H - 12}" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">Each cell adds its voltage. Two 1.5 V cells in series = 3 V. Long line on the symbol = the + terminal.</text>
`;
  return svgWrap(W, H, "Battery single-cell versus multi-cell comparison", "Two-panel comparison. Left: a single AA cell (1.5 V) with its real-component drawing and one-cell schematic symbol below. Right: two AAs end-to-end in series (3 V total) with both the real depiction and the two-cell schematic symbol.", body);
}

// ────────────────────────────────────────────────────────────────────────────
// SECTION 2 — Circuits (5 SVGs)
// ────────────────────────────────────────────────────────────────────────────

function s2_simpleCircuit() {
  const W = 480, H = 300;
  let body = `
  <text x="${W / 2}" y="22" font="bold 16px system-ui" font-size="16" font-weight="700" fill="${INK}" text-anchor="middle">Simple Circuit — Battery, Switch, Lamp</text>

  <!-- Rectangular loop -->
  ${wire(80, 180, 80, 100)}
  ${wire(80, 100, 240, 100)}
  ${wire(240, 100, 240, 180)}
  ${wire(240, 180, 80, 180)}

  <!-- Battery on the left side (vertical) -->
  ${battery(80, 220, "v", "9 V")}

  <!-- Wire down to battery -->
  ${wire(80, 180, 80, 200)}
  ${wire(80, 240, 80, 260)}
  ${wire(80, 260, 240, 260)}
  ${wire(240, 260, 240, 240)}
  ${wire(240, 200, 240, 180)}
  ${batteryCell(240, 220, "v")}

  <!-- Wait, simpler. Let me redraw a proper rectangle with battery on bottom, switch on left, lamp on top -->
`;
  // Cleaner redraw: rectangle 100..380 x 90..220, components on each edge
  body = `
  <text x="${W / 2}" y="22" font="bold 16px system-ui" font-size="16" font-weight="700" fill="${INK}" text-anchor="middle">Simple Circuit — Battery, Switch, Lamp</text>

  <!-- Rectangle wires -->
  ${wire(80, 220, 80, 90)}
  ${wire(80, 90, 240, 90)}
  ${wire(260, 90, 400, 90)}
  ${wire(400, 90, 400, 220)}
  ${wire(400, 220, 240, 220)}
  ${wire(240, 220, 80, 220)}

  <!-- Switch on top wire -->
  ${switchSymbol(250, 90, false, "switch")}

  <!-- Lamp on right wire (top) -->
  ${lamp(400, 155, 22, true, "lamp")}
  ${wire(400, 90, 400, 133)}
  ${wire(400, 177, 400, 220)}

  <!-- Battery on bottom wire -->
  ${battery(160, 220, "h", "9 V battery")}

  <!-- Current arrow on top wire -->
  ${currentArrow(180, 90, "right", "I")}

  <!-- Caption -->
  <text x="${W / 2}" y="${H - 38}" font="bold 12px system-ui" font-size="12" font-weight="700" fill="${POSITIVE}" text-anchor="middle">switch closed → current flows → lamp lights up</text>
  <text x="${W / 2}" y="${H - 18}" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">A complete loop: battery pushes current through the switch, around the wire, through the lamp, back to the battery.</text>
`;
  return svgWrap(W, H, "Simple lamp circuit", "A rectangular circuit loop with a 9-volt battery on the bottom, a closed switch on the top wire, and a lit amber lamp on the right wire. A green current arrow points right along the top wire showing direction of conventional current.", body);
}

function s2_seriesCircuit() {
  const W = 540, H = 300;
  let body = `
  <text x="${W / 2}" y="22" font="bold 16px system-ui" font-size="16" font-weight="700" fill="${INK}" text-anchor="middle">Series Circuit — Two Lamps in a Single Loop</text>

  <!-- Rectangle -->
  ${wire(80, 220, 80, 90)}
  ${wire(80, 90, 460, 90)}
  ${wire(460, 90, 460, 220)}
  ${wire(460, 220, 80, 220)}

  <!-- Two lamps in series on top wire -->
  ${lamp(220, 90, 18, true, "lamp 1")}
  ${wire(202, 90, 80, 90)}
  ${wire(238, 90, 320, 90)}
  ${lamp(340, 90, 18, true, "lamp 2")}
  ${wire(358, 90, 460, 90)}

  <!-- Battery -->
  ${battery(280, 220, "h", "9 V")}

  <!-- One current arrow (because series = same I everywhere) -->
  ${currentArrow(140, 90, "right", "I")}
  ${currentArrow(420, 220, "left", "I")}

  <!-- Caption: same current, voltage divides -->
  <text x="${W / 2}" y="${H - 50}" font="bold 12px system-ui" font-size="12" font-weight="700" fill="${POSITIVE}" text-anchor="middle">SAME current through both lamps  ·  voltage SPLITS between them</text>
  <text x="${W / 2}" y="${H - 32}" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">If one lamp breaks, the loop is broken — both go dark.</text>
  <text x="${W / 2}" y="${H - 14}" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">Each lamp gets ~4.5 V (half of 9 V) — they look dimmer than a single lamp on the same battery.</text>
`;
  return svgWrap(W, H, "Series circuit with two lamps", "A rectangular circuit with two lamps placed end-to-end on the top wire and a 9-volt battery on the bottom wire. Both lamps are lit. Two green current arrows point in the direction of flow, illustrating that the same current passes through both lamps in series.", body);
}

function s2_parallelCircuit() {
  const W = 540, H = 320;
  let body = `
  <text x="${W / 2}" y="22" font="bold 16px system-ui" font-size="16" font-weight="700" fill="${INK}" text-anchor="middle">Parallel Circuit — Two Lamps in Branches</text>

  <!-- Outer wires -->
  ${wire(80, 240, 80, 90)}
  ${wire(80, 90, 200, 90)}
  ${wire(460, 90, 460, 240)}
  ${wire(80, 240, 460, 240)}

  <!-- Top junction nodes -->
  ${node(200, 90)}
  ${node(380, 90)}
  ${wire(380, 90, 460, 90)}
  ${wire(200, 90, 380, 90)}

  <!-- Branch 1: lamp 1 (left vertical) -->
  ${wire(220, 90, 220, 130)}
  ${lamp(220, 152, 18, true, "lamp 1")}
  ${wire(220, 174, 220, 220)}
  ${node(220, 220)}
  ${wire(80, 220, 460, 220)}

  <!-- Branch 2: lamp 2 (right vertical) -->
  ${wire(360, 90, 360, 130)}
  ${lamp(360, 152, 18, true, "lamp 2")}
  ${wire(360, 174, 360, 220)}
  ${node(360, 220)}

  <!-- Battery on bottom wire -->
  ${battery(140, 240, "h", "9 V")}

  <!-- Current arrows -->
  ${currentArrow(180, 90, "right", "I_total")}
  ${currentArrow(220, 113, "down", "I₁")}
  ${currentArrow(360, 113, "down", "I₂")}

  <!-- Caption -->
  <text x="${W / 2}" y="${H - 50}" font="bold 12px system-ui" font-size="12" font-weight="700" fill="${POSITIVE}" text-anchor="middle">SAME voltage across both lamps  ·  current SPLITS between them</text>
  <text x="${W / 2}" y="${H - 32}" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">If one lamp breaks, the other stays on — the second branch is still a loop.</text>
  <text x="${W / 2}" y="${H - 14}" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">Both lamps get the full 9 V — each is as bright as a single lamp would be.</text>
`;
  return svgWrap(W, H, "Parallel circuit with two lamps in branches", "A circuit with two parallel branches between two horizontal wires. Each branch contains a lit lamp. A 9-volt battery is on the bottom wire. Three green current arrows: one for I_total along the top wire, one for I₁ entering the left branch, one for I₂ entering the right branch.", body);
}

function s2_seriesVsParallel() {
  const W = 720, H = 380;
  let body = `
  <text x="${W / 2}" y="22" font="bold 16px system-ui" font-size="16" font-weight="700" fill="${INK}" text-anchor="middle">Series vs Parallel — When One Lamp Breaks</text>

  <!-- LEFT: Series with broken bulb -->
  <text x="180" y="60" font="bold 13px system-ui" font-size="13" font-weight="700" fill="${NEGATIVE}" text-anchor="middle">Series (one lamp broken)</text>
  ${wire(60, 200, 60, 100)}
  ${wire(60, 100, 320, 100)}
  ${wire(320, 100, 320, 200)}
  ${wire(320, 200, 60, 200)}
  ${lamp(150, 100, 16, false, "")}
  ${wire(134, 100, 60, 100)}
  ${wire(166, 100, 240, 100)}
  ${lamp(260, 100, 16, false, "")}
  <line x1="244" y1="86" x2="276" y2="114" stroke="${NEGATIVE}" stroke-width="2.5" />
  <line x1="276" y1="86" x2="244" y2="114" stroke="${NEGATIVE}" stroke-width="2.5" />
  <text x="260" y="138" font="bold 10px system-ui" font-size="10" font-weight="700" fill="${NEGATIVE}" text-anchor="middle">BROKEN</text>
  <text x="150" y="138" font="bold 10px system-ui" font-size="10" font-weight="700" fill="${NEGATIVE}" text-anchor="middle">also dark</text>
  ${battery(190, 200, "h", "9 V")}
  <text x="180" y="240" font="bold 12px system-ui" font-size="12" font-weight="700" fill="${NEGATIVE}" text-anchor="middle">↳ both go dark · loop is broken</text>

  <!-- Vertical divider -->
  <line x1="370" y1="80" x2="370" y2="320" stroke="${MUTED}" stroke-width="1" stroke-dasharray="4 4" />

  <!-- RIGHT: Parallel with broken bulb -->
  <text x="540" y="60" font="bold 13px system-ui" font-size="13" font-weight="700" fill="${POSITIVE}" text-anchor="middle">Parallel (one lamp broken)</text>
  ${wire(420, 220, 420, 100)}
  ${wire(420, 100, 660, 100)}
  ${wire(660, 100, 660, 220)}
  ${wire(420, 220, 660, 220)}
  ${wire(460, 100, 460, 130)}
  ${lamp(460, 152, 16, false, "")}
  <line x1="446" y1="138" x2="474" y2="166" stroke="${NEGATIVE}" stroke-width="2.5" />
  <line x1="474" y1="138" x2="446" y2="166" stroke="${NEGATIVE}" stroke-width="2.5" />
  <text x="460" y="195" font="bold 10px system-ui" font-size="10" font-weight="700" fill="${NEGATIVE}" text-anchor="middle">BROKEN</text>
  ${wire(460, 174, 460, 220)}
  ${wire(620, 100, 620, 130)}
  ${lamp(620, 152, 16, true, "")}
  ${wire(620, 174, 620, 220)}
  <text x="620" y="195" font="bold 10px system-ui" font-size="10" font-weight="700" fill="${POSITIVE}" text-anchor="middle">still on</text>
  ${battery(490, 220, "h", "9 V")}
  <text x="540" y="280" font="bold 12px system-ui" font-size="12" font-weight="700" fill="${POSITIVE}" text-anchor="middle">↳ second lamp stays lit · second loop intact</text>

  <text x="${W / 2}" y="${H - 30}" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">This is why the wiring in your house is mostly parallel — one bulb burning out shouldn't kill the rest.</text>
`;
  return svgWrap(W, H, "Series versus parallel circuits with a broken bulb", "Side-by-side comparison: left circuit is two lamps in series with both unlit and a red X marking one as broken (because the loop is broken, both go dark). Right circuit is two lamps in parallel with the left one X-marked broken but the right one still lit (because each branch is its own loop).", body);
}

function s2_ledWithResistor() {
  const W = 480, H = 280;
  let body = `
  <text x="${W / 2}" y="22" font="bold 16px system-ui" font-size="16" font-weight="700" fill="${INK}" text-anchor="middle">LED with Current-Limit Resistor — Why It's Mandatory</text>

  <!-- Loop -->
  ${wire(80, 200, 80, 90)}
  ${wire(80, 90, 400, 90)}
  ${wire(400, 90, 400, 200)}
  ${wire(400, 200, 80, 200)}

  <!-- Resistor in line with LED -->
  ${resistor(180, 90, "h", "330 Ω")}
  ${wire(80, 90, 150, 90)}
  ${wire(210, 90, 280, 90)}

  <!-- LED -->
  ${led(310, 90, true, "LED")}
  ${wire(327, 90, 400, 90)}

  <!-- Battery -->
  ${battery(220, 200, "h", "5 V")}

  <!-- Current arrow -->
  ${currentArrow(120, 90, "right", "I = 9 mA")}

  <text x="${W / 2}" y="${H - 50}" font="bold 12px system-ui" font-size="12" font-weight="700" fill="${POSITIVE}" text-anchor="middle">Resistor caps the current at a safe value</text>
  <text x="${W / 2}" y="${H - 32}" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">Without the resistor: 5 V across the LED → too much current → LED burns out instantly.</text>
  <text x="${W / 2}" y="${H - 14}" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">A 330 Ω resistor drops ~3 V at 9 mA, leaving ~2 V for the LED — the LED's happy place.</text>
`;
  return svgWrap(W, H, "LED with current-limit resistor", "A simple loop with a 5-volt battery on the bottom, a 330-ohm resistor in series with a lit red LED on the top wire. A green current arrow shows I = 9 mA.", body);
}

// ────────────────────────────────────────────────────────────────────────────
// SECTION 3 — Flow & Laws (4 SVGs)
// ────────────────────────────────────────────────────────────────────────────

function s3_currentFlowDirection() {
  const W = 540, H = 280;
  let body = `
  <text x="${W / 2}" y="22" font="bold 16px system-ui" font-size="16" font-weight="700" fill="${INK}" text-anchor="middle">Two Ways to Talk About Current Flow</text>

  <!-- Loop -->
  ${wire(80, 200, 80, 90)}
  ${wire(80, 90, 460, 90)}
  ${wire(460, 90, 460, 200)}
  ${wire(460, 200, 80, 200)}

  <!-- Resistor -->
  ${resistor(270, 90, "h", "")}
  ${wire(80, 90, 240, 90)}
  ${wire(300, 90, 460, 90)}

  <!-- Battery -->
  ${battery(220, 200, "h", "")}

  <!-- Conventional current (green arrows on top, going right out of + terminal) -->
  ${currentArrow(150, 90, "right", "")}
  ${currentArrow(380, 90, "right", "")}
  ${currentArrow(460, 145, "down", "")}
  ${currentArrow(380, 200, "left", "")}
  ${currentArrow(80, 145, "up", "")}
  <text x="${W / 2}" y="68" font="bold 13px system-ui" font-size="13" font-weight="700" fill="${POSITIVE}" text-anchor="middle">conventional current  →  + to − (the way the symbol shows it)</text>

  <!-- Electron flow (blue dashes, opposite direction) -->
  <line x1="180" y1="105" x2="120" y2="105" stroke="${ACCENT}" stroke-width="2" stroke-dasharray="6 4" />
  <polygon points="120,105 130,99 130,111" fill="${ACCENT}" />
  <line x1="420" y1="105" x2="360" y2="105" stroke="${ACCENT}" stroke-width="2" stroke-dasharray="6 4" />
  <polygon points="360,105 370,99 370,111" fill="${ACCENT}" />
  <text x="${W / 2}" y="234" font="bold 13px system-ui" font-size="13" font-weight="700" fill="${ACCENT}" text-anchor="middle">electron flow  ←  − to + (the actual physical direction)</text>

  <text x="${W / 2}" y="${H - 12}" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">Both arrows describe the same circuit. Convention came before we knew electrons were negative. We kept the convention.</text>
`;
  return svgWrap(W, H, "Conventional current versus electron flow direction", "A simple resistor circuit shown twice: green solid arrows on the wires pointing in the conventional-current direction (battery + to −), and blue dashed arrows on the same wires pointing the opposite direction for electron flow (− to +). Both describe the same physical circuit.", body);
}

function s3_openVsClosed() {
  const W = 720, H = 280;
  let body = `
  <text x="${W / 2}" y="22" font="bold 16px system-ui" font-size="16" font-weight="700" fill="${INK}" text-anchor="middle">Open vs Closed Switch — The Difference Is Everything</text>

  <!-- LEFT: open switch -->
  <text x="180" y="60" font="bold 13px system-ui" font-size="13" font-weight="700" fill="${NEGATIVE}" text-anchor="middle">switch OPEN  →  no current  →  lamp dark</text>
  ${wire(60, 200, 60, 100)}
  ${wire(60, 100, 320, 100)}
  ${wire(320, 100, 320, 200)}
  ${wire(320, 200, 60, 200)}
  ${switchSymbol(150, 100, true, "")}
  ${lamp(280, 100, 16, false, "")}
  ${wire(132, 100, 60, 100)}
  ${wire(168, 100, 264, 100)}
  ${wire(296, 100, 320, 100)}
  ${battery(190, 200, "h", "9 V")}
  <text x="180" y="248" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">loop has a gap → electrons can't get around</text>

  <line x1="370" y1="80" x2="370" y2="240" stroke="${MUTED}" stroke-width="1" stroke-dasharray="4 4" />

  <!-- RIGHT: closed switch -->
  <text x="540" y="60" font="bold 13px system-ui" font-size="13" font-weight="700" fill="${POSITIVE}" text-anchor="middle">switch CLOSED  →  current flows  →  lamp lit</text>
  ${wire(420, 200, 420, 100)}
  ${wire(420, 100, 680, 100)}
  ${wire(680, 100, 680, 200)}
  ${wire(680, 200, 420, 200)}
  ${switchSymbol(510, 100, false, "")}
  ${lamp(640, 100, 16, true, "")}
  ${wire(492, 100, 420, 100)}
  ${wire(528, 100, 624, 100)}
  ${wire(656, 100, 680, 100)}
  ${battery(550, 200, "h", "9 V")}
  ${currentArrow(460, 100, "right", "I")}
  <text x="540" y="248" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">loop is complete → current flows from + to − to +</text>
`;
  return svgWrap(W, H, "Open versus closed switch comparison", "Two side-by-side identical lamp circuits. Left: switch shown open with the lamp unlit (no current can flow through the gap). Right: switch shown closed with the lamp lit and a green current arrow (loop is complete).", body);
}

function s3_ohmsLaw() {
  const W = 540, H = 320;
  let body = `
  <text x="${W / 2}" y="22" font="bold 16px system-ui" font-size="16" font-weight="700" fill="${INK}" text-anchor="middle">Ohm's Law — Voltage, Current, Resistance</text>

  <!-- Triangle mnemonic on the left -->
  <g transform="translate(80, 70)">
    <polygon points="0,160 220,160 110,0" fill="${BG}" stroke="${ACCENT}" stroke-width="2.5" />
    <line x1="60" y1="80" x2="160" y2="80" stroke="${ACCENT}" stroke-width="2" />
    <line x1="110" y1="80" x2="110" y2="160" stroke="${ACCENT}" stroke-width="2" />
    <text x="110" y="55" font="bold 32px system-ui" font-size="32" font-weight="700" fill="${NEGATIVE}" text-anchor="middle">V</text>
    <text x="78" y="135" font="bold 32px system-ui" font-size="32" font-weight="700" fill="${POSITIVE}" text-anchor="middle">I</text>
    <text x="142" y="135" font="bold 32px system-ui" font-size="32" font-weight="700" fill="${RESISTOR}" text-anchor="middle">R</text>
  </g>

  <!-- Three rearrangements on the right -->
  <g transform="translate(340, 80)">
    <text x="0" y="0" font="bold 14px system-ui" font-size="14" font-weight="700" fill="${INK}">cover any letter to find its formula</text>
    <text x="0" y="40" font="bold 22px system-ui" font-size="22" font-weight="700" fill="${NEGATIVE}">V = I × R</text>
    <text x="0" y="56" font="11px system-ui" font-size="11" fill="${MUTED}">voltage = current × resistance</text>
    <text x="0" y="100" font="bold 22px system-ui" font-size="22" font-weight="700" fill="${POSITIVE}">I = V / R</text>
    <text x="0" y="116" font="11px system-ui" font-size="11" fill="${MUTED}">current = voltage ÷ resistance</text>
    <text x="0" y="160" font="bold 22px system-ui" font-size="22" font-weight="700" fill="${RESISTOR}">R = V / I</text>
    <text x="0" y="176" font="11px system-ui" font-size="11" fill="${MUTED}">resistance = voltage ÷ current</text>
  </g>

  <!-- Worked example at the bottom -->
  <g transform="translate(40, 250)">
    <rect x="0" y="0" width="460" height="50" rx="8" fill="#fef3c7" stroke="${RESISTOR}" stroke-width="1.5" />
    <text x="14" y="20" font="bold 12px system-ui" font-size="12" font-weight="700" fill="${INK}">example:</text>
    <text x="14" y="40" font="13px system-ui" font-size="13" fill="${INK}">9 V battery + 330 Ω resistor → I = 9 / 330 ≈ 0.027 A = 27 mA</text>
  </g>

  <text x="${W / 2}" y="${H - 12}" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">More voltage → more push → more current. More resistance → more pushback → less current.</text>
`;
  return svgWrap(W, H, "Ohms law triangle and rearrangements", "On the left, a triangle mnemonic with V on top and I, R below the dividing line. On the right, the three rearranged formulas (V = IR, I = V/R, R = V/I) each with a plain-English caption. A worked example below: 9 V battery + 330 Ω → 27 mA.", body);
}

function s3_shortCircuit() {
  const W = 540, H = 280;
  let body = `
  <text x="${W / 2}" y="22" font="bold 16px system-ui" font-size="16" font-weight="700" fill="${INK}" text-anchor="middle">⚠ Short Circuit — Don't Do This</text>

  <!-- Outer loop with a lamp on top -->
  ${wire(80, 200, 80, 90)}
  ${wire(80, 90, 460, 90)}
  ${wire(460, 90, 460, 200)}
  ${wire(460, 200, 80, 200)}

  <!-- Lamp on top -->
  ${lamp(270, 90, 18, false, "")}
  ${wire(80, 90, 252, 90)}
  ${wire(288, 90, 460, 90)}

  <!-- Short-circuit wire (red, going across, bypassing the lamp) -->
  <line x1="180" y1="90" x2="180" y2="160" stroke="${NEGATIVE}" stroke-width="3" />
  <line x1="180" y1="160" x2="360" y2="160" stroke="${NEGATIVE}" stroke-width="3" />
  <line x1="360" y1="160" x2="360" y2="90" stroke="${NEGATIVE}" stroke-width="3" />

  <!-- X warning on the lamp -->
  <line x1="252" y1="72" x2="288" y2="108" stroke="${NEGATIVE}" stroke-width="2.5" />
  <line x1="288" y1="72" x2="252" y2="108" stroke="${NEGATIVE}" stroke-width="2.5" />

  <!-- Big "SHORT!" callout -->
  <text x="270" y="178" font="bold 16px system-ui" font-size="16" font-weight="700" fill="${NEGATIVE}" text-anchor="middle">SHORT!</text>
  <text x="270" y="195" font="11px system-ui" font-size="11" fill="${NEGATIVE}" text-anchor="middle">no resistance → huge current</text>

  <!-- Big current arrow on the short -->
  ${currentArrow(220, 160, "right", "")}
  <text x="220" y="143" font="bold 13px system-ui" font-size="13" font-weight="700" fill="${NEGATIVE}" text-anchor="middle">I = HUGE</text>

  <!-- Battery -->
  ${battery(270, 200, "h", "9 V")}

  <text x="${W / 2}" y="${H - 30}" font="bold 12px system-ui" font-size="12" font-weight="700" fill="${NEGATIVE}" text-anchor="middle">A wire with no load straight across the battery → the battery overheats, melts, or catches fire.</text>
  <text x="${W / 2}" y="${H - 12}" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">Always have something — a lamp, resistor, motor — between battery + and battery −. Never plain wire.</text>
`;
  return svgWrap(W, H, "Short circuit warning diagram", "A circuit with a lamp on the top wire X-marked as bypassed, and a thick red wire jumping straight across from the wire above the battery to the wire below — short-circuiting the lamp. A red 'SHORT!' label and a 'I = HUGE' current arrow indicate the runaway-current danger.", body);
}

// ────────────────────────────────────────────────────────────────────────────
// Main
// ────────────────────────────────────────────────────────────────────────────

mkdirSync(ROOT, { recursive: true });

write("section-1-components/circuit-component-symbols.svg", s1_componentSymbols());
write("section-1-components/resistor-anatomy.svg", s1_resistorAnatomy());
write("section-1-components/capacitor-anatomy.svg", s1_capacitorAnatomy());
write("section-1-components/battery-and-cell-anatomy.svg", s1_batteryAnatomy());

write("section-2-circuits/simple-circuit-with-lamp.svg", s2_simpleCircuit());
write("section-2-circuits/series-circuit.svg", s2_seriesCircuit());
write("section-2-circuits/parallel-circuit.svg", s2_parallelCircuit());
write("section-2-circuits/series-vs-parallel-comparison.svg", s2_seriesVsParallel());
write("section-2-circuits/led-with-current-limit-resistor.svg", s2_ledWithResistor());

write("section-3-flow-and-laws/current-flow-direction.svg", s3_currentFlowDirection());
write("section-3-flow-and-laws/open-vs-closed-circuit.svg", s3_openVsClosed());
write("section-3-flow-and-laws/ohms-law-relationship.svg", s3_ohmsLaw());
write("section-3-flow-and-laws/short-circuit-warning.svg", s3_shortCircuit());

console.log("done — 13 SVGs");
