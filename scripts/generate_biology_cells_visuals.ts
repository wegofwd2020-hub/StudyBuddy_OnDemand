#!/usr/bin/env bun
/**
 * Generate the Option-2 SVG catalogue for G6-SCI-001 Cells (issue #330).
 *
 * Run from repo root:
 *   bun scripts/generate_biology_cells_visuals.ts
 *
 * Output: sample_content/g6-stem/G6-SCI-001_Cells/Option2_Catalogue/section-N/*.svg
 *
 * This unit opens the biology primitive set (G6 audience). G6 framing —
 * friendly cartoony shapes, large labels, plain-English organelle names
 * ("powerhouse" alongside "mitochondrion").
 */

import { writeFileSync, mkdirSync } from "node:fs";
import { join, dirname } from "node:path";

const ROOT = join(
  import.meta.dir,
  "..",
  "sample_content",
  "g6-stem",
  "G6-SCI-001_Cells",
  "Option2_Catalogue",
);

// Style tokens lifted to pipeline/visual_templates/shared.ts (#341 phase A).
import {
  INK,
  MUTED,
  ACCENT,
  ACCENT_2,
  POSITIVE,
  GRID,
  BG,
} from "../pipeline/visual_templates/shared.ts";

// Biology organelle palette — locked-in convention for downstream units.
const CYTOPLASM = "#fef9c3";       // very pale yellow-green
const CELL_MEMBRANE = "#94a3b8";   // muted slate
const CELL_WALL = "#a16207";       // amber-brown (plant only)
const NUCLEUS = "#7c3aed";         // purple
const NUCLEOLUS = "#a855f7";       // lighter purple
const MITOCHONDRION = "#dc2626";   // red (energy)
const CHLOROPLAST = "#16a34a";     // green
const VACUOLE = "#7dd3fc";         // pale blue
const GOLGI = "#f59e0b";           // amber
const ER_ROUGH = "#ea580c";        // peach
const ER_SMOOTH = "#fb923c";       // lighter peach
const LYSOSOME = "#f472b6";        // pink
const RIBOSOME = "#7c2d12";        // dark brown dots
const CENTROSOME = "#64748b";      // slate

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

// Build a leader-line label (a short line + a text label at the line's end).
function leaderLabel(
  fromX: number, fromY: number, toX: number, toY: number,
  text: string, color: string, anchor: 'start' | 'middle' | 'end' = 'start',
  fontSize = 13, bold = true,
): string {
  return `
  <line x1="${fromX}" y1="${fromY}" x2="${toX}" y2="${toY}" stroke="${color}" stroke-width="1.5" />
  <text x="${toX + (anchor === 'start' ? 4 : anchor === 'end' ? -4 : 0)}" y="${toY + 4}"
    font="${bold ? 'bold ' : ''}${fontSize}px system-ui" font-size="${fontSize}" font-weight="${bold ? 700 : 400}"
    fill="${color}" text-anchor="${anchor}">${text}</text>`;
}

// Sprinkle small "ribosome" dots on a path bbox
function ribosomeDots(cx: number, cy: number, rx: number, ry: number, count: number, color: string): string {
  let s = '';
  for (let i = 0; i < count; i++) {
    const ang = (i / count) * Math.PI * 2 + i * 0.7;
    const r = ry * (0.5 + 0.4 * Math.cos(ang * 1.7));
    const x = cx + r * Math.cos(ang) * (rx / ry);
    const y = cy + r * Math.sin(ang);
    s += `<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="2.2" fill="${color}" />`;
  }
  return s;
}

// ────────────────────────────────────────────────────────────────────────────
// SECTION 1 — Whole cells (3 SVGs)
// ────────────────────────────────────────────────────────────────────────────

function s1_animalCell() {
  const W = 720, H = 480;
  const cx = 360, cy = 240;
  // Animal cell: irregular blobby ellipse, no cell wall.
  const cellPath = `M ${cx - 280} ${cy} Q ${cx - 280} ${cy - 200}, ${cx - 80} ${cy - 220} T ${cx + 280} ${cy - 30} Q ${cx + 290} ${cy + 180}, ${cx + 80} ${cy + 220} T ${cx - 280} ${cy}`;

  let body = `
  <text x="${W / 2}" y="22" font="bold 16px system-ui" font-size="16" font-weight="700" fill="${INK}" text-anchor="middle">Animal Cell — Major Parts</text>

  <!-- Cell membrane (just the outline) -->
  <path d="${cellPath}" fill="${CYTOPLASM}" stroke="${CELL_MEMBRANE}" stroke-width="3.5" />

  <!-- Nucleus (off-center) -->
  <ellipse cx="${cx - 30}" cy="${cy - 20}" rx="80" ry="68" fill="${NUCLEUS}" opacity="0.85" stroke="${INK}" stroke-width="1.8" />
  <circle cx="${cx - 50}" cy="${cy - 30}" r="18" fill="${NUCLEOLUS}" stroke="${INK}" stroke-width="1.2" />

  <!-- Mitochondria (3 of them, scattered) -->
  <ellipse cx="${cx + 130}" cy="${cy - 80}" rx="38" ry="20" fill="${MITOCHONDRION}" opacity="0.85" stroke="${INK}" stroke-width="1.5" transform="rotate(-20 ${cx + 130} ${cy - 80})" />
  <ellipse cx="${cx + 100}" cy="${cy + 110}" rx="34" ry="18" fill="${MITOCHONDRION}" opacity="0.85" stroke="${INK}" stroke-width="1.5" transform="rotate(35 ${cx + 100} ${cy + 110})" />
  <ellipse cx="${cx - 170}" cy="${cy + 80}" rx="32" ry="17" fill="${MITOCHONDRION}" opacity="0.85" stroke="${INK}" stroke-width="1.5" transform="rotate(-50 ${cx - 170} ${cy + 80})" />

  <!-- Endoplasmic reticulum (rough), squiggly path with dots -->
  <path d="M ${cx - 180} ${cy - 80} Q ${cx - 130} ${cy - 130}, ${cx - 80} ${cy - 90} T ${cx + 20} ${cy - 70} T ${cx + 100} ${cy - 110}"
    fill="none" stroke="${ER_ROUGH}" stroke-width="6" stroke-linecap="round" />
  ${ribosomeDots(cx - 80, cy - 100, 110, 18, 14, RIBOSOME)}

  <!-- Golgi apparatus (stacked curves) -->
  <g>
    <path d="M ${cx - 200} ${cy + 130} Q ${cx - 150} ${cy + 110}, ${cx - 100} ${cy + 130}" fill="none" stroke="${GOLGI}" stroke-width="5" stroke-linecap="round" />
    <path d="M ${cx - 200} ${cy + 145} Q ${cx - 150} ${cy + 125}, ${cx - 100} ${cy + 145}" fill="none" stroke="${GOLGI}" stroke-width="5" stroke-linecap="round" />
    <path d="M ${cx - 200} ${cy + 160} Q ${cx - 150} ${cy + 140}, ${cx - 100} ${cy + 160}" fill="none" stroke="${GOLGI}" stroke-width="5" stroke-linecap="round" />
  </g>

  <!-- Lysosomes (small pink circles) -->
  <circle cx="${cx + 180}" cy="${cy + 50}" r="14" fill="${LYSOSOME}" stroke="${INK}" stroke-width="1" />
  <circle cx="${cx - 210}" cy="${cy - 60}" r="11" fill="${LYSOSOME}" stroke="${INK}" stroke-width="1" />

  <!-- Centrosome (slate, near nucleus) -->
  <g transform="translate(${cx + 50} ${cy + 50})">
    <rect x="-8" y="-3" width="16" height="6" fill="${CENTROSOME}" />
    <rect x="-3" y="-8" width="6" height="16" fill="${CENTROSOME}" />
  </g>

  <!-- Free ribosomes scattered in cytoplasm -->
  ${ribosomeDots(cx + 200, cy + 150, 60, 30, 9, RIBOSOME)}

  <!-- Leader-line labels (right side) -->
  ${leaderLabel(cx - 120, cy - 60, cx + 320, cy - 230, "Nucleus (control center)", NUCLEUS, 'start')}
  ${leaderLabel(cx + 130, cy - 80, cx + 320, cy - 180, "Mitochondrion (powerhouse)", MITOCHONDRION, 'start')}
  ${leaderLabel(cx - 80, cy - 95, cx + 320, cy - 130, "Rough ER (protein-making)", ER_ROUGH, 'start')}
  ${leaderLabel(cx - 150, cy + 140, cx + 320, cy - 80, "Golgi (packaging)", GOLGI, 'start')}
  ${leaderLabel(cx + 180, cy + 50, cx + 320, cy - 30, "Lysosome (digestion)", LYSOSOME, 'start')}
  ${leaderLabel(cx + 50, cy + 50, cx + 320, cy + 20, "Centrosome", CENTROSOME, 'start')}
  ${leaderLabel(cx + 290, cy - 40, cx + 320, cy + 70, "Cell membrane", CELL_MEMBRANE, 'start')}
  ${leaderLabel(cx + 220, cy + 160, cx + 320, cy + 120, "Cytoplasm (jelly)", "#854d0e", 'start')}
`;
  return svgWrap(W, H, "Labeled animal cell with major organelles", "An animal cell shown as an irregular blob outlined by a cell membrane. Inside: a purple nucleus with a smaller nucleolus, three red bean-shaped mitochondria, an orange rough endoplasmic reticulum sprinkled with brown ribosome dots, an amber Golgi apparatus stack, two pink lysosomes, a slate centrosome, and free ribosomes in the cytoplasm. Each organelle has a leader-line label on the right side.", body);
}

function s1_plantCell() {
  const W = 720, H = 480;
  const cx = 360, cy = 240;
  // Plant cell: rectangular with rounded corners, has cell wall + large central vacuole + chloroplasts.
  const wallW = 540, wallH = 360;
  const wallX = cx - wallW / 2, wallY = cy - wallH / 2;

  let body = `
  <text x="${W / 2}" y="22" font="bold 16px system-ui" font-size="16" font-weight="700" fill="${INK}" text-anchor="middle">Plant Cell — Major Parts</text>

  <!-- Cell wall (thick brown outer rectangle) -->
  <rect x="${wallX - 8}" y="${wallY - 8}" width="${wallW + 16}" height="${wallH + 16}" rx="20" fill="${CELL_WALL}" />
  <!-- Cell membrane (thinner inside the wall) -->
  <rect x="${wallX}" y="${wallY}" width="${wallW}" height="${wallH}" rx="14" fill="${CYTOPLASM}" stroke="${CELL_MEMBRANE}" stroke-width="2.5" />

  <!-- Large central vacuole (dominates) -->
  <rect x="${cx - 200}" y="${cy - 120}" width="400" height="240" rx="36"
    fill="${VACUOLE}" opacity="0.55" stroke="${ACCENT}" stroke-width="2" />
  <text x="${cx}" y="${cy + 8}" font="bold 18px system-ui" font-size="18" font-weight="700"
    fill="${ACCENT}" text-anchor="middle" opacity="0.85">vacuole (water)</text>

  <!-- Nucleus (top-left corner, smaller because vacuole is big) -->
  <ellipse cx="${cx - 200}" cy="${cy - 130}" rx="50" ry="42" fill="${NUCLEUS}" opacity="0.85" stroke="${INK}" stroke-width="1.5" />
  <circle cx="${cx - 210}" cy="${cy - 138}" r="11" fill="${NUCLEOLUS}" />

  <!-- Chloroplasts (5 of them, distinctive green) -->
  <g>
    <ellipse cx="${cx + 200}" cy="${cy - 130}" rx="34" ry="20" fill="${CHLOROPLAST}" opacity="0.85" stroke="${INK}" stroke-width="1.5" />
    <ellipse cx="${cx + 230}" cy="${cy - 60}" rx="32" ry="18" fill="${CHLOROPLAST}" opacity="0.85" stroke="${INK}" stroke-width="1.5" transform="rotate(-25 ${cx + 230} ${cy - 60})" />
    <ellipse cx="${cx - 200}" cy="${cy + 130}" rx="32" ry="18" fill="${CHLOROPLAST}" opacity="0.85" stroke="${INK}" stroke-width="1.5" />
    <ellipse cx="${cx + 220}" cy="${cy + 130}" rx="32" ry="18" fill="${CHLOROPLAST}" opacity="0.85" stroke="${INK}" stroke-width="1.5" transform="rotate(20 ${cx + 220} ${cy + 130})" />
    <ellipse cx="${cx - 220}" cy="${cy - 60}" rx="30" ry="17" fill="${CHLOROPLAST}" opacity="0.85" stroke="${INK}" stroke-width="1.5" transform="rotate(40 ${cx - 220} ${cy - 60})" />
  </g>

  <!-- Mitochondria (a couple) -->
  <ellipse cx="${cx - 130}" cy="${cy - 145}" rx="22" ry="11" fill="${MITOCHONDRION}" opacity="0.85" stroke="${INK}" stroke-width="1.2" transform="rotate(-15 ${cx - 130} ${cy - 145})" />
  <ellipse cx="${cx + 60}" cy="${cy + 145}" rx="22" ry="11" fill="${MITOCHONDRION}" opacity="0.85" stroke="${INK}" stroke-width="1.2" transform="rotate(20 ${cx + 60} ${cy + 145})" />

  <!-- Leader-line labels (right side) -->
  ${leaderLabel(cx + wallW / 2 + 4, cy - 130, cx + 360, cy - 230, "Cell wall (cellulose)", "#92400e", 'start')}
  ${leaderLabel(cx + wallW / 2 - 6, cy - 30, cx + 360, cy - 180, "Cell membrane", CELL_MEMBRANE, 'start')}
  ${leaderLabel(cx + 200, cy - 130, cx + 360, cy - 130, "Chloroplast (food maker)", CHLOROPLAST, 'start')}
  ${leaderLabel(cx + 60, cy + 145, cx + 360, cy - 80, "Mitochondrion", MITOCHONDRION, 'start')}
  ${leaderLabel(cx, cy, cx + 360, cy - 30, "Vacuole (storage)", ACCENT, 'start')}
  ${leaderLabel(cx - 200, cy - 130, cx + 360, cy + 20, "Nucleus", NUCLEUS, 'start')}
  ${leaderLabel(cx - 200, cy + 60, cx + 360, cy + 70, "Cytoplasm", "#854d0e", 'start')}
`;
  return svgWrap(W, H, "Labeled plant cell with major organelles", "A plant cell shown as a rectangular shape with rounded corners, surrounded by a thick brown cell wall and a thinner inner cell membrane. Inside: a small purple nucleus with nucleolus, five distinctive green chloroplasts, two small red mitochondria, and a large dominant blue central vacuole. Each organelle has a leader-line label on the right side.", body);
}

function s1_animalVsPlant() {
  const W = 760, H = 380;
  // Two simplified cells side by side, with a difference list in between
  const halfW = 320;
  const animalCx = 130, plantCx = W - 130, ccy = 200;

  let body = `
  <text x="${W / 2}" y="22" font="bold 16px system-ui" font-size="16" font-weight="700" fill="${INK}" text-anchor="middle">Animal vs Plant Cell — At a Glance</text>

  <!-- Animal cell (left) -->
  <ellipse cx="${animalCx}" cy="${ccy}" rx="100" ry="80" fill="${CYTOPLASM}" stroke="${CELL_MEMBRANE}" stroke-width="3" />
  <ellipse cx="${animalCx + 10}" cy="${ccy - 10}" rx="32" ry="26" fill="${NUCLEUS}" opacity="0.85" />
  <ellipse cx="${animalCx - 35}" cy="${ccy + 30}" rx="14" ry="8" fill="${MITOCHONDRION}" opacity="0.85" />
  <ellipse cx="${animalCx + 50}" cy="${ccy + 35}" rx="14" ry="8" fill="${MITOCHONDRION}" opacity="0.85" />
  <text x="${animalCx}" y="${ccy + 110}" font="bold 18px system-ui" font-size="18" font-weight="700" fill="${INK}" text-anchor="middle">Animal</text>

  <!-- Plant cell (right) -->
  <rect x="${plantCx - 110}" y="${ccy - 90}" width="220" height="180" rx="14" fill="${CELL_WALL}" />
  <rect x="${plantCx - 102}" y="${ccy - 82}" width="204" height="164" rx="10" fill="${CYTOPLASM}" stroke="${CELL_MEMBRANE}" stroke-width="2" />
  <rect x="${plantCx - 80}" y="${ccy - 50}" width="160" height="100" rx="14" fill="${VACUOLE}" opacity="0.55" stroke="${ACCENT}" stroke-width="1.5" />
  <ellipse cx="${plantCx - 70}" cy="${ccy - 65}" rx="22" ry="18" fill="${NUCLEUS}" opacity="0.85" />
  <ellipse cx="${plantCx + 65}" cy="${ccy - 60}" rx="14" ry="8" fill="${CHLOROPLAST}" opacity="0.85" />
  <ellipse cx="${plantCx + 70}" cy="${ccy + 50}" rx="14" ry="8" fill="${CHLOROPLAST}" opacity="0.85" />
  <ellipse cx="${plantCx - 80}" cy="${ccy + 60}" rx="14" ry="8" fill="${CHLOROPLAST}" opacity="0.85" />
  <text x="${plantCx}" y="${ccy + 110}" font="bold 18px system-ui" font-size="18" font-weight="700" fill="${INK}" text-anchor="middle">Plant</text>

  <!-- Comparison list (center) -->
  <g transform="translate(${W / 2 - 110} 80)">
    <rect x="0" y="0" width="220" height="220" rx="10" fill="${BG}" stroke="${MUTED}" stroke-width="1.5" />
    <text x="110" y="22" font="bold 13px system-ui" font-size="13" font-weight="700" fill="${INK}" text-anchor="middle">Plant cell ALSO has</text>
    <text x="20" y="56" font="bold 14px system-ui" font-size="14" font-weight="700" fill="${CELL_WALL}">+ cell wall</text>
    <text x="20" y="80" font="11px system-ui" font-size="11" fill="${MUTED}">stiff outer layer</text>
    <text x="20" y="116" font="bold 14px system-ui" font-size="14" font-weight="700" fill="${CHLOROPLAST}">+ chloroplasts</text>
    <text x="20" y="140" font="11px system-ui" font-size="11" fill="${MUTED}">make food from sunlight</text>
    <text x="20" y="176" font="bold 14px system-ui" font-size="14" font-weight="700" fill="${ACCENT}">+ big vacuole</text>
    <text x="20" y="200" font="11px system-ui" font-size="11" fill="${MUTED}">water + storage</text>
  </g>

  <text x="${W / 2}" y="${H - 12}" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">Both have a nucleus, mitochondria, ribosomes, ER, Golgi, and a cell membrane.</text>
`;
  return svgWrap(W, H, "Animal vs plant cell comparison", "Side-by-side simplified cells: a soft round animal cell on the left, a rectangular plant cell with cell wall on the right. A central panel lists the three things plant cells have that animal cells don't: cell wall, chloroplasts, and a large vacuole. A footnote notes the organelles both share.", body);
}

// ────────────────────────────────────────────────────────────────────────────
// SECTION 2 — Organelle close-ups (5 SVGs)
// ────────────────────────────────────────────────────────────────────────────

function s2_nucleus() {
  const W = 480, H = 360;
  const cx = 240, cy = 180;
  let body = `
  <text x="${W / 2}" y="22" font="bold 16px system-ui" font-size="16" font-weight="700" fill="${INK}" text-anchor="middle">Nucleus — The Control Center</text>

  <!-- Outer nuclear envelope (double membrane) -->
  <ellipse cx="${cx}" cy="${cy}" rx="150" ry="120" fill="none" stroke="${NUCLEUS}" stroke-width="3" />
  <ellipse cx="${cx}" cy="${cy}" rx="143" ry="113" fill="${NUCLEUS}" fill-opacity="0.18" stroke="${NUCLEUS}" stroke-width="2" />

  <!-- Nuclear pores (gaps in the envelope, drawn as small white circles) -->
  <circle cx="${cx + 150}" cy="${cy - 5}" r="6" fill="${BG}" stroke="${NUCLEUS}" stroke-width="1.5" />
  <circle cx="${cx + 110}" cy="${cy + 95}" r="6" fill="${BG}" stroke="${NUCLEUS}" stroke-width="1.5" />
  <circle cx="${cx - 130}" cy="${cy + 50}" r="6" fill="${BG}" stroke="${NUCLEUS}" stroke-width="1.5" />
  <circle cx="${cx - 80}" cy="${cy - 110}" r="6" fill="${BG}" stroke="${NUCLEUS}" stroke-width="1.5" />
  <circle cx="${cx + 60}" cy="${cy - 117}" r="6" fill="${BG}" stroke="${NUCLEUS}" stroke-width="1.5" />

  <!-- Nucleolus -->
  <circle cx="${cx - 30}" cy="${cy - 10}" r="36" fill="${NUCLEOLUS}" stroke="${INK}" stroke-width="1.5" />
  <text x="${cx - 30}" y="${cy - 6}" font="bold 11px system-ui" font-size="11" font-weight="700" fill="white" text-anchor="middle">nucleolus</text>

  <!-- Chromatin (squiggles) -->
  <path d="M ${cx + 30} ${cy - 60} Q ${cx + 60} ${cy - 30}, ${cx + 90} ${cy - 50} T ${cx + 110} ${cy + 10} T ${cx + 60} ${cy + 50}"
    fill="none" stroke="${INK}" stroke-width="1.8" stroke-dasharray="2 2" />
  <path d="M ${cx - 70} ${cy + 30} Q ${cx - 100} ${cy + 50}, ${cx - 80} ${cy + 80} T ${cx - 30} ${cy + 95}"
    fill="none" stroke="${INK}" stroke-width="1.8" stroke-dasharray="2 2" />

  <!-- Labels -->
  ${leaderLabel(cx + 150, cy - 5, cx + 220, cy - 60, "nuclear pore", NUCLEUS, 'start', 12)}
  ${leaderLabel(cx + 150, cy, cx + 220, cy, "nuclear envelope", NUCLEUS, 'start', 12)}
  ${leaderLabel(cx - 30, cy - 10, cx - 220, cy - 80, "nucleolus", NUCLEOLUS, 'end', 12)}
  ${leaderLabel(cx + 80, cy - 30, cx - 220, cy + 20, "chromatin (DNA)", INK, 'end', 12)}

  <text x="${W / 2}" y="${H - 14}" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">Holds the cell's instructions. The double membrane has tiny "pores" that let messengers in and out.</text>
`;
  return svgWrap(W, H, "Nucleus close-up", "A purple oval nucleus with a darker purple nucleolus inside, dashed chromatin squiggles representing DNA, and five small white nuclear pores dotted around the double-membrane envelope. Leader-line labels point to nucleolus, nuclear envelope, nuclear pore, and chromatin.", body);
}

function s2_mitochondrion() {
  const W = 480, H = 320;
  const cx = 240, cy = 160;
  // Mitochondrion: outer bean shape, inner folded membrane (cristae), matrix space.
  let body = `
  <text x="${W / 2}" y="22" font="bold 16px system-ui" font-size="16" font-weight="700" fill="${INK}" text-anchor="middle">Mitochondrion — The Powerhouse</text>

  <!-- Outer membrane (bean shape) -->
  <ellipse cx="${cx}" cy="${cy}" rx="170" ry="80" fill="${MITOCHONDRION}" fill-opacity="0.18" stroke="${MITOCHONDRION}" stroke-width="3" />

  <!-- Inner membrane with cristae (folds) -->
  <path d="M ${cx - 150} ${cy} Q ${cx - 130} ${cy - 50}, ${cx - 100} ${cy} T ${cx - 50} ${cy} T ${cx} ${cy} T ${cx + 50} ${cy} T ${cx + 100} ${cy} T ${cx + 150} ${cy}"
    fill="none" stroke="${MITOCHONDRION}" stroke-width="2.5" />
  <path d="M ${cx - 150} ${cy} Q ${cx - 130} ${cy + 50}, ${cx - 100} ${cy} T ${cx - 50} ${cy} T ${cx} ${cy} T ${cx + 50} ${cy} T ${cx + 100} ${cy} T ${cx + 150} ${cy}"
    fill="none" stroke="${MITOCHONDRION}" stroke-width="2.5" />
  <!-- The cristae proper: scalloped folds -->
  <g stroke="${MITOCHONDRION}" stroke-width="2" fill="none">
    <path d="M ${cx - 130} ${cy - 30} Q ${cx - 115} ${cy + 20}, ${cx - 100} ${cy - 30}" />
    <path d="M ${cx - 80} ${cy - 30} Q ${cx - 65} ${cy + 20}, ${cx - 50} ${cy - 30}" />
    <path d="M ${cx - 30} ${cy - 30} Q ${cx - 15} ${cy + 20}, ${cx} ${cy - 30}" />
    <path d="M ${cx + 20} ${cy - 30} Q ${cx + 35} ${cy + 20}, ${cx + 50} ${cy - 30}" />
    <path d="M ${cx + 70} ${cy - 30} Q ${cx + 85} ${cy + 20}, ${cx + 100} ${cy - 30}" />
  </g>

  <!-- ATP energy bursts (small yellow stars) -->
  <g fill="${GOLGI}" stroke="${INK}" stroke-width="0.5">
    <circle cx="${cx + 175}" cy="${cy - 50}" r="6" />
    <circle cx="${cx + 195}" cy="${cy - 30}" r="5" />
    <circle cx="${cx + 200}" cy="${cy + 20}" r="6" />
    <text x="${cx + 175}" y="${cy - 53}" font="bold 9px system-ui" font-size="9" font-weight="700" fill="${INK}" text-anchor="middle">ATP</text>
  </g>

  <!-- Labels -->
  ${leaderLabel(cx + 150, cy - 50, cx - 120, cy - 110, "outer membrane", MITOCHONDRION, 'start', 12)}
  ${leaderLabel(cx + 90, cy, cx + 180, cy + 80, "cristae (folded inner membrane)", MITOCHONDRION, 'start', 12)}
  ${leaderLabel(cx, cy + 20, cx - 200, cy + 100, "matrix (inside)", "#7c2d12", 'start', 12)}

  <text x="${W / 2}" y="${H - 14}" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">Burns sugar with oxygen to make ATP — the cell's energy currency. More folds = more energy.</text>
`;
  return svgWrap(W, H, "Mitochondrion close-up", "A red bean-shaped mitochondrion showing its outer membrane and inner folded membrane (cristae). Five scalloped folds project from the inner edge into the matrix. Three small yellow ATP particles emerge to the right with an 'ATP' label, indicating energy production. Leader lines label the outer membrane, cristae, and matrix.", body);
}

function s2_chloroplast() {
  const W = 480, H = 320;
  const cx = 240, cy = 160;
  let body = `
  <text x="${W / 2}" y="22" font="bold 16px system-ui" font-size="16" font-weight="700" fill="${INK}" text-anchor="middle">Chloroplast — The Solar Panel</text>

  <!-- Outer envelope (lens-shape) -->
  <ellipse cx="${cx}" cy="${cy}" rx="170" ry="80" fill="${CHLOROPLAST}" fill-opacity="0.22" stroke="${CHLOROPLAST}" stroke-width="3" />
  <ellipse cx="${cx}" cy="${cy}" rx="163" ry="73" fill="none" stroke="${CHLOROPLAST}" stroke-width="2" />

  <!-- Thylakoid stacks (grana) — small green disks stacked -->
  <g fill="${CHLOROPLAST}" stroke="${INK}" stroke-width="1">
    <ellipse cx="${cx - 100}" cy="${cy - 8}" rx="20" ry="6" />
    <ellipse cx="${cx - 100}" cy="${cy + 5}" rx="20" ry="6" />
    <ellipse cx="${cx - 100}" cy="${cy + 18}" rx="20" ry="6" />
    <ellipse cx="${cx - 100}" cy="${cy + 31}" rx="20" ry="6" />

    <ellipse cx="${cx - 30}" cy="${cy - 20}" rx="22" ry="6.5" />
    <ellipse cx="${cx - 30}" cy="${cy - 6}" rx="22" ry="6.5" />
    <ellipse cx="${cx - 30}" cy="${cy + 8}" rx="22" ry="6.5" />
    <ellipse cx="${cx - 30}" cy="${cy + 22}" rx="22" ry="6.5" />
    <ellipse cx="${cx - 30}" cy="${cy + 36}" rx="22" ry="6.5" />

    <ellipse cx="${cx + 50}" cy="${cy - 12}" rx="20" ry="6" />
    <ellipse cx="${cx + 50}" cy="${cy + 1}" rx="20" ry="6" />
    <ellipse cx="${cx + 50}" cy="${cy + 14}" rx="20" ry="6" />

    <ellipse cx="${cx + 110}" cy="${cy - 4}" rx="20" ry="6" />
    <ellipse cx="${cx + 110}" cy="${cy + 9}" rx="20" ry="6" />
    <ellipse cx="${cx + 110}" cy="${cy + 22}" rx="20" ry="6" />
  </g>

  <!-- Stromal lamellae connecting the stacks -->
  <line x1="${cx - 80}" y1="${cy + 5}" x2="${cx - 50}" y2="${cy + 8}" stroke="${CHLOROPLAST}" stroke-width="2" />
  <line x1="${cx - 8}" y1="${cy + 8}" x2="${cx + 30}" y2="${cy + 1}" stroke="${CHLOROPLAST}" stroke-width="2" />
  <line x1="${cx + 70}" y1="${cy + 1}" x2="${cx + 90}" y2="${cy + 9}" stroke="${CHLOROPLAST}" stroke-width="2" />

  <!-- Sunlight arrow coming in -->
  <line x1="${cx - 250}" y1="${cy - 90}" x2="${cx - 130}" y2="${cy - 45}" stroke="${GOLGI}" stroke-width="3" />
  <polygon points="${cx - 130},${cy - 45} ${cx - 145},${cy - 50} ${cx - 140},${cy - 35}" fill="${GOLGI}" />
  <text x="${cx - 240}" y="${cy - 95}" font="bold 11px system-ui" font-size="11" font-weight="700" fill="${GOLGI}">sunlight</text>

  <!-- Sugar (glucose) coming out -->
  <line x1="${cx + 150}" y1="${cy + 35}" x2="${cx + 240}" y2="${cy + 90}" stroke="${POSITIVE}" stroke-width="3" />
  <polygon points="${cx + 240},${cy + 90} ${cx + 230},${cy + 78} ${cx + 222},${cy + 92}" fill="${POSITIVE}" />
  <text x="${cx + 240}" y="${cy + 110}" font="bold 11px system-ui" font-size="11" font-weight="700" fill="${POSITIVE}">sugar</text>

  <!-- Labels -->
  ${leaderLabel(cx - 30, cy - 20, cx, cy - 100, "grana (stacked thylakoids)", CHLOROPLAST, 'middle', 12)}
  ${leaderLabel(cx + 130, cy - 4, cx + 220, cy - 80, "stroma (the fluid)", "#166534", 'start', 12)}
  ${leaderLabel(cx - 165, cy, cx - 220, cy + 80, "double membrane", CHLOROPLAST, 'end', 12)}

  <text x="${W / 2}" y="${H - 14}" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">Captures sunlight and turns it into sugar. Plants only — animals can't do this.</text>
`;
  return svgWrap(W, H, "Chloroplast close-up", "A green lens-shaped chloroplast with several internal stacks of small green disks (grana made of thylakoids), connected by thin lamellae across the stroma. A yellow sunlight arrow enters from upper left; a green sugar arrow exits to lower right. Leader lines label grana, stroma, and the double membrane.", body);
}

function s2_cellMembraneBilayer() {
  const W = 540, H = 280;
  const cx = 270;
  // Phospholipid bilayer: two rows of head+tail molecules with heads facing out
  let body = `
  <text x="${W / 2}" y="22" font="bold 16px system-ui" font-size="16" font-weight="700" fill="${INK}" text-anchor="middle">Cell Membrane — Phospholipid Bilayer</text>

  <!-- Water labels -->
  <text x="40" y="60" font="bold 13px system-ui" font-size="13" font-weight="700" fill="${ACCENT}">outside cell</text>
  <text x="40" y="78" font="11px system-ui" font-size="11" fill="${ACCENT}">(water)</text>
  <text x="40" y="220" font="bold 13px system-ui" font-size="13" font-weight="700" fill="${ACCENT}">inside cell</text>
  <text x="40" y="238" font="11px system-ui" font-size="11" fill="${ACCENT}">(water)</text>

  <!-- Top row of phospholipids (heads facing up, tails down) -->
`;
  for (let i = 0; i < 14; i++) {
    const x = 130 + i * 30;
    body += `
    <circle cx="${x}" cy="100" r="11" fill="${ACCENT}" stroke="${INK}" stroke-width="1.2" />
    <line x1="${x - 4}" y1="110" x2="${x - 4}" y2="138" stroke="#0c4a6e" stroke-width="2" />
    <line x1="${x + 4}" y1="110" x2="${x + 4}" y2="138" stroke="#0c4a6e" stroke-width="2" />`;
  }
  body += `
  <!-- Bottom row (heads down, tails up — meeting in the middle) -->
`;
  for (let i = 0; i < 14; i++) {
    const x = 130 + i * 30;
    body += `
    <circle cx="${x}" cy="178" r="11" fill="${ACCENT}" stroke="${INK}" stroke-width="1.2" />
    <line x1="${x - 4}" y1="168" x2="${x - 4}" y2="140" stroke="#0c4a6e" stroke-width="2" />
    <line x1="${x + 4}" y1="168" x2="${x + 4}" y2="140" stroke="#0c4a6e" stroke-width="2" />`;
  }
  // A protein channel embedded in the bilayer
  body += `
  <g>
    <rect x="${cx - 15}" y="80" width="30" height="120" rx="6" fill="${POSITIVE}" stroke="${INK}" stroke-width="1.5" opacity="0.85" />
    <rect x="${cx - 8}" y="100" width="16" height="80" fill="${BG}" />
    ${leaderLabel(cx + 15, 110, 460, 60, "protein channel", POSITIVE, 'start', 12)}
  </g>

  <!-- Single phospholipid callout (right side) -->
  <g transform="translate(470 130)">
    <circle cx="0" cy="0" r="14" fill="${ACCENT}" stroke="${INK}" stroke-width="1.2" />
    <text x="0" y="3" font="bold 9px system-ui" font-size="9" font-weight="700" fill="white" text-anchor="middle">head</text>
    <text x="0" y="-22" font="10px system-ui" font-size="10" fill="${ACCENT}" text-anchor="middle">water-loving</text>
    <line x1="-5" y1="14" x2="-5" y2="50" stroke="#0c4a6e" stroke-width="2.5" />
    <line x1="5" y1="14" x2="5" y2="50" stroke="#0c4a6e" stroke-width="2.5" />
    <text x="0" y="68" font="10px system-ui" font-size="10" fill="#0c4a6e" text-anchor="middle">tails</text>
    <text x="0" y="82" font="10px system-ui" font-size="10" fill="#0c4a6e" text-anchor="middle">water-fearing</text>
  </g>

  <text x="${W / 2}" y="${H - 14}" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">Heads love water and face outward. Tails fear water and hide in the middle. The cell's outer wall is two of these in a back-to-back layer.</text>
`;
  return svgWrap(W, H, "Cell membrane phospholipid bilayer", "A horizontal cross-section of a cell membrane showing two rows of phospholipid molecules. The top row has blue circular heads facing upward (toward outside-of-cell water) and tails dangling down; the bottom row mirrors it (heads down toward inside-of-cell water, tails up). A green protein channel is embedded across both rows. A single phospholipid is enlarged on the right with head and tails labelled.", body);
}

function s2_erAndGolgi() {
  const W = 540, H = 320;
  let body = `
  <text x="${W / 2}" y="22" font="bold 16px system-ui" font-size="16" font-weight="700" fill="${INK}" text-anchor="middle">Endoplasmic Reticulum + Golgi — The Protein Pipeline</text>

  <!-- Nucleus (left edge) -->
  <ellipse cx="80" cy="160" rx="48" ry="40" fill="${NUCLEUS}" opacity="0.85" stroke="${INK}" stroke-width="1.5" />
  <text x="80" y="220" font="bold 11px system-ui" font-size="11" font-weight="700" fill="${NUCLEUS}" text-anchor="middle">nucleus</text>

  <!-- Rough ER (with ribosomes) — squiggly path emerging from nucleus -->
  <path d="M 130 140 Q 170 110, 220 130 T 280 140" fill="none" stroke="${ER_ROUGH}" stroke-width="8" stroke-linecap="round" />
  <path d="M 130 175 Q 175 195, 215 175 T 280 165" fill="none" stroke="${ER_ROUGH}" stroke-width="8" stroke-linecap="round" />
  ${ribosomeDots(200, 130, 80, 14, 12, RIBOSOME)}
  ${ribosomeDots(200, 180, 80, 14, 10, RIBOSOME)}

  <!-- Golgi apparatus (center-right, stacked curves) -->
  <g>
    <path d="M 320 110 Q 360 90, 410 110" fill="none" stroke="${GOLGI}" stroke-width="6" stroke-linecap="round" />
    <path d="M 320 130 Q 360 110, 410 130" fill="none" stroke="${GOLGI}" stroke-width="6" stroke-linecap="round" />
    <path d="M 320 150 Q 360 130, 410 150" fill="none" stroke="${GOLGI}" stroke-width="6" stroke-linecap="round" />
    <path d="M 320 170 Q 360 150, 410 170" fill="none" stroke="${GOLGI}" stroke-width="6" stroke-linecap="round" />
  </g>

  <!-- Vesicles (small bubbles between ER and Golgi, and after Golgi) -->
  <circle cx="300" cy="155" r="7" fill="${ER_ROUGH}" opacity="0.7" stroke="${INK}" stroke-width="1" />
  <circle cx="430" cy="135" r="7" fill="${GOLGI}" opacity="0.85" stroke="${INK}" stroke-width="1" />
  <circle cx="455" cy="155" r="7" fill="${GOLGI}" opacity="0.85" stroke="${INK}" stroke-width="1" />
  <circle cx="475" cy="180" r="7" fill="${GOLGI}" opacity="0.85" stroke="${INK}" stroke-width="1" />

  <!-- Flow arrows -->
  <line x1="290" y1="240" x2="320" y2="240" stroke="${ACCENT}" stroke-width="2" marker-end="url(#flow-arr)" />
  <line x1="420" y1="240" x2="450" y2="240" stroke="${ACCENT}" stroke-width="2" marker-end="url(#flow-arr)" />
  <defs>
    <marker id="flow-arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="${ACCENT}" />
    </marker>
  </defs>

  <!-- Stage labels -->
  <text x="200" y="245" font="bold 12px system-ui" font-size="12" font-weight="700" fill="${ER_ROUGH}" text-anchor="middle">make</text>
  <text x="200" y="262" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">protein built on ribosomes</text>

  <text x="365" y="245" font="bold 12px system-ui" font-size="12" font-weight="700" fill="${GOLGI}" text-anchor="middle">package</text>
  <text x="365" y="262" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">label + sort + bag</text>

  <text x="475" y="245" font="bold 12px system-ui" font-size="12" font-weight="700" fill="${ACCENT}" text-anchor="middle">ship</text>
  <text x="475" y="262" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">vesicle delivers it</text>

  <!-- Labels for organelles -->
  ${leaderLabel(200, 145, 90, 70, "Rough ER", ER_ROUGH, 'start', 12)}
  ${leaderLabel(365, 110, 460, 50, "Golgi apparatus", GOLGI, 'end', 12)}
  ${leaderLabel(220, 130, 320, 100, "ribosomes (dots)", "#7c2d12", 'start', 11)}

  <text x="${W / 2}" y="${H - 14}" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">A protein factory pipeline. Built on the ER, customised in the Golgi, shipped in vesicles to wherever it's needed.</text>
`;
  return svgWrap(W, H, "Endoplasmic reticulum and Golgi apparatus", "A protein-processing pipeline from left to right: a purple nucleus, the orange rough ER (two squiggly tubes covered in brown ribosome dots) emerging from it, transport vesicles, an amber Golgi apparatus with four stacked curves, and outgoing vesicles. Flow arrows label the stages: 'make' at the ER, 'package' at the Golgi, 'ship' as vesicles depart.", body);
}

// ────────────────────────────────────────────────────────────────────────────
// SECTION 3 — Scale & microscopy (2 SVGs)
// ────────────────────────────────────────────────────────────────────────────

function s3_cellSizeScale() {
  const W = 720, H = 280;
  // Logarithmic scale bar: virus (100 nm), bacterium (1 μm), animal cell (10 μm), plant cell (100 μm), human eye limit (~100 μm), grain of sand (1 mm)
  const x0 = 80, x1 = W - 60;
  const items = [
    { label: 'virus', size: '100 nm', x: 100, color: "#c026d3", icon: 'hex' },
    { label: 'bacterium', size: '1–5 μm', x: 230, color: "#0891b2", icon: 'rod' },
    { label: 'animal cell', size: '10–30 μm', x: 380, color: NUCLEUS, icon: 'animal' },
    { label: 'plant cell', size: '50–100 μm', x: 540, color: CHLOROPLAST, icon: 'plant' },
    { label: 'grain of sand', size: '~1 mm', x: 660, color: "#a16207", icon: 'sand' },
  ];
  let body = `
  <text x="${W / 2}" y="22" font="bold 16px system-ui" font-size="16" font-weight="700" fill="${INK}" text-anchor="middle">How Big is a Cell? Logarithmic Scale</text>

  <!-- Main horizontal axis -->
  <line x1="${x0}" y1="160" x2="${x1}" y2="160" stroke="${INK}" stroke-width="2" />
  <polygon points="${x1},160 ${x1 - 10},155 ${x1 - 10},165" fill="${INK}" />

  <!-- Scale ticks (decade markers): 100 nm, 1 μm, 10 μm, 100 μm, 1 mm -->
`;
  const ticks = [
    { x: 100, label: '100 nm' },
    { x: 230, label: '1 μm' },
    { x: 380, label: '10 μm' },
    { x: 540, label: '100 μm' },
    { x: 660, label: '1 mm' },
  ];
  for (const t of ticks) {
    body += `
  <line x1="${t.x}" y1="155" x2="${t.x}" y2="170" stroke="${INK}" stroke-width="2" />
  <text x="${t.x}" y="190" font="bold 11px system-ui" font-size="11" font-weight="700" fill="${INK}" text-anchor="middle">${t.label}</text>`;
  }

  // Items above the line
  for (const it of items) {
    let icon = '';
    if (it.icon === 'hex') {
      icon = `<polygon points="${it.x - 6},${110} ${it.x - 6},${100} ${it.x},${94} ${it.x + 6},${100} ${it.x + 6},${110} ${it.x},${116}" fill="${it.color}" stroke="${INK}" stroke-width="1" />`;
    } else if (it.icon === 'rod') {
      icon = `<rect x="${it.x - 12}" y="100" width="24" height="10" rx="5" fill="${it.color}" stroke="${INK}" stroke-width="1" />`;
    } else if (it.icon === 'animal') {
      icon = `<ellipse cx="${it.x}" cy="105" rx="22" ry="16" fill="${CYTOPLASM}" stroke="${CELL_MEMBRANE}" stroke-width="1.8" />
              <ellipse cx="${it.x + 4}" cy="103" rx="6" ry="5" fill="${NUCLEUS}" />`;
    } else if (it.icon === 'plant') {
      icon = `<rect x="${it.x - 28}" y="80" width="56" height="50" rx="4" fill="${CELL_WALL}" />
              <rect x="${it.x - 24}" y="84" width="48" height="42" rx="2" fill="${CYTOPLASM}" />
              <ellipse cx="${it.x - 12}" cy="93" rx="6" ry="4" fill="${NUCLEUS}" />
              <ellipse cx="${it.x + 14}" cy="115" rx="5" ry="3" fill="${CHLOROPLAST}" />`;
    } else if (it.icon === 'sand') {
      icon = `<polygon points="${it.x - 18},115 ${it.x + 18},115 ${it.x + 12},85 ${it.x - 8},80" fill="${it.color}" stroke="${INK}" stroke-width="1.2" />`;
    }
    body += `
    ${icon}
    <text x="${it.x}" y="50" font="bold 12px system-ui" font-size="12" font-weight="700" fill="${it.color}" text-anchor="middle">${it.label}</text>
    <text x="${it.x}" y="66" font="10px system-ui" font-size="10" fill="${MUTED}" text-anchor="middle">${it.size}</text>
    <line x1="${it.x}" y1="${it.icon === 'plant' ? 130 : 116}" x2="${it.x}" y2="155" stroke="${MUTED}" stroke-width="1" stroke-dasharray="2 3" />`;
  }

  // Visibility regions
  body += `
  <line x1="${x0}" y1="220" x2="350" y2="220" stroke="${ACCENT}" stroke-width="3" />
  <text x="${(x0 + 350) / 2}" y="244" font="bold 11px system-ui" font-size="11" font-weight="700" fill="${ACCENT}" text-anchor="middle">needs an electron microscope</text>

  <line x1="350" y1="220" x2="600" y2="220" stroke="${POSITIVE}" stroke-width="3" />
  <text x="${(350 + 600) / 2}" y="244" font="bold 11px system-ui" font-size="11" font-weight="700" fill="${POSITIVE}" text-anchor="middle">light microscope works</text>

  <line x1="600" y1="220" x2="${x1}" y2="220" stroke="${ACCENT_2}" stroke-width="3" />
  <text x="${(600 + x1) / 2}" y="244" font="bold 11px system-ui" font-size="11" font-weight="700" fill="${ACCENT_2}" text-anchor="middle">visible to the naked eye</text>

  <text x="${W / 2}" y="${H - 12}" font="10px system-ui" font-size="10" fill="${MUTED}" text-anchor="middle">Note: scale is logarithmic — each tick is ten times bigger than the previous one.</text>
`;
  return svgWrap(W, H, "Cell size scale chart", "A horizontal logarithmic scale bar with five ticks from 100 nm (virus) to 1 mm (grain of sand). Above the bar, five small icons mark virus, bacterium, animal cell, plant cell, and grain of sand at their respective scale positions. Below the bar, three coloured ranges indicate which microscopy is required: electron microscope, light microscope, and naked eye.", body);
}

function s3_microscopyComparison() {
  const W = 720, H = 320;
  const halfW = 360;
  const c1x = halfW / 2, c2x = halfW + halfW / 2;
  let body = `
  <text x="${W / 2}" y="22" font="bold 16px system-ui" font-size="16" font-weight="700" fill="${INK}" text-anchor="middle">What You See — Light vs Electron Microscope</text>

  <!-- Left: light microscope view of an animal cell (blurry, low detail) -->
  <g>
    <circle cx="${c1x}" cy="170" r="105" fill="${BG}" stroke="${INK}" stroke-width="2" />
    <ellipse cx="${c1x - 5}" cy="160" rx="70" ry="55" fill="${CYTOPLASM}" stroke="${CELL_MEMBRANE}" stroke-width="2.5" filter="blur(0.6px)" />
    <ellipse cx="${c1x}" cy="155" rx="20" ry="16" fill="${NUCLEUS}" opacity="0.7" filter="blur(0.8px)" />
    <ellipse cx="${c1x - 30}" cy="180" rx="6" ry="3" fill="${MITOCHONDRION}" opacity="0.6" filter="blur(0.7px)" />
    <text x="${c1x}" y="64" font="bold 16px system-ui" font-size="16" font-weight="700" fill="${POSITIVE}" text-anchor="middle">Light Microscope</text>
    <text x="${c1x}" y="84" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">~1000× magnification</text>
    <text x="${c1x}" y="296" font="bold 12px system-ui" font-size="12" font-weight="700" fill="${POSITIVE}" text-anchor="middle">✓ live cells, in colour</text>
    <text x="${c1x}" y="310" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">but small parts blur together</text>
  </g>

  <!-- Right: electron microscope view of same cell (sharp, lots of detail, monochrome) -->
  <g>
    <circle cx="${c2x}" cy="170" r="105" fill="#0f172a" stroke="${INK}" stroke-width="2" />
    <ellipse cx="${c2x - 5}" cy="160" rx="70" ry="55" fill="#374151" stroke="#9ca3af" stroke-width="2" />
    <ellipse cx="${c2x}" cy="155" rx="22" ry="17" fill="#111827" stroke="#9ca3af" stroke-width="1.5" />
    <circle cx="${c2x + 4}" cy="151" r="6" fill="#1f2937" stroke="#9ca3af" stroke-width="0.8" />
    <ellipse cx="${c2x - 30}" cy="180" rx="8" ry="4" fill="#1f2937" stroke="#9ca3af" stroke-width="1" />
    <ellipse cx="${c2x + 25}" cy="190" rx="7" ry="3.5" fill="#1f2937" stroke="#9ca3af" stroke-width="1" />
    <!-- ER squiggle (sharp, monochrome) -->
    <path d="M ${c2x - 40} ${190} Q ${c2x - 20} ${200}, ${c2x + 10} ${193} T ${c2x + 50} ${188}" fill="none" stroke="#9ca3af" stroke-width="1.5" />
    <text x="${c2x}" y="64" font="bold 16px system-ui" font-size="16" font-weight="700" fill="${ACCENT}" text-anchor="middle">Electron Microscope</text>
    <text x="${c2x}" y="84" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">~500,000× magnification</text>
    <text x="${c2x}" y="296" font="bold 12px system-ui" font-size="12" font-weight="700" fill="${ACCENT}" text-anchor="middle">✓ tiny parts visible</text>
    <text x="${c2x}" y="310" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">but only dead cells, black-and-white</text>
  </g>

  <!-- Center divider -->
  <line x1="${halfW}" y1="50" x2="${halfW}" y2="${H - 30}" stroke="${MUTED}" stroke-width="1" stroke-dasharray="4 4" />
`;
  return svgWrap(W, H, "Light vs electron microscope comparison", "Two side-by-side circular views of the same cell. Left: a soft cream-and-purple light-microscope view labelled '~1000× magnification' with blurred organelles, captioned 'live cells, in colour'. Right: a sharp grey-on-black electron-microscope view labelled '~500,000× magnification' with crisp organelle outlines, captioned 'tiny parts visible, only dead cells, black-and-white'.", body);
}

// ────────────────────────────────────────────────────────────────────────────
// Main
// ────────────────────────────────────────────────────────────────────────────

mkdirSync(ROOT, { recursive: true });

write("section-1-whole-cells/animal-cell-labeled.svg", s1_animalCell());
write("section-1-whole-cells/plant-cell-labeled.svg", s1_plantCell());
write("section-1-whole-cells/animal-vs-plant-comparison.svg", s1_animalVsPlant());

write("section-2-organelles/nucleus-anatomy.svg", s2_nucleus());
write("section-2-organelles/mitochondrion-anatomy.svg", s2_mitochondrion());
write("section-2-organelles/chloroplast-anatomy.svg", s2_chloroplast());
write("section-2-organelles/cell-membrane-bilayer.svg", s2_cellMembraneBilayer());
write("section-2-organelles/endoplasmic-reticulum-and-golgi.svg", s2_erAndGolgi());

write("section-3-scale-microscopy/cell-size-scale.svg", s3_cellSizeScale());
write("section-3-scale-microscopy/microscopy-comparison.svg", s3_microscopyComparison());

console.log("done — 10 SVGs");
