#!/usr/bin/env bun
/**
 * Generate the Option-2 SVG catalogue for G10-SCI-004 Organic Chemistry
 * (issue #333).
 *
 * Run from repo root:
 *   bun scripts/generate_organic_chemistry_visuals.ts
 *
 * Output: sample_content/g10-stem/G10-SCI-004_Organic_Chemistry/Option2_Catalogue/section-N/*.svg
 *
 * The skeletal-structure SVG generator is the highest-leverage primitive
 * here — it'll be reused across G11-CHEM-008/009 and G12-CHEM-006/007/008/009
 * (six downstream organic-chem units).
 */

import { writeFileSync, mkdirSync } from "node:fs";
import { join, dirname } from "node:path";

const ROOT = join(
  import.meta.dir,
  "..",
  "sample_content",
  "g10-stem",
  "G10-SCI-004_Organic_Chemistry",
  "Option2_Catalogue",
);

// Style tokens + class primitives lifted to pipeline/visual_templates.
// Skeletal-structure helpers + functional-group palette imported from the
// class module per #343 phase C-3.
import {
  INK,
  MUTED,
  ACCENT,
  ACCENT_2,
  POSITIVE,
  NEGATIVE,
  BG,
  HIGHLIGHT,
} from "../pipeline/visual_templates/shared.ts";
import {
  BOND,
  FG_HYDROXYL,
  FG_CARBONYL,
  FG_AMINE,
  FG_HALOGEN,
  FG_RING,
  BL,
  ZIG,
  ZAG,
  zigzagPoints,
  singleBond,
  doubleBond,
  tripleBond,
  atomLabel,
  alkaneZigzag,
  hexagon,
} from "../pipeline/visual_templates/organic_chemistry.ts";

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
// SECTION 1 — Skeletal Structures (5 SVGs)
// ────────────────────────────────────────────────────────────────────────────

function s1_shorthandRules() {
  const W = 720, H = 360;
  let body = `
  <text x="${W / 2}" y="32" font="bold 18px system-ui" font-size="18" font-weight="700" fill="${INK}" text-anchor="middle">Three Ways to Draw the Same Molecule (Butane, C₄H₁₀)</text>

  <!-- Full structural formula (every C and H drawn) -->
  <text x="120" y="70" font="bold 13px system-ui" font-size="13" font-weight="700" fill="${INK}" text-anchor="middle">Full structural</text>
  <text x="120" y="86" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">every atom drawn</text>
  <g transform="translate(40, 130)">
    <text x="0" y="14" font="bold 16px system-ui" font-size="16" font-weight="700" fill="${INK}" text-anchor="middle">H</text>
    <text x="0" y="60" font="bold 16px system-ui" font-size="16" font-weight="700" fill="${INK}" text-anchor="middle">H</text>
    <text x="20" y="40" font="bold 16px system-ui" font-size="16" font-weight="700" fill="${INK}" text-anchor="middle">−C−</text>
    <text x="0" y="40" font="bold 16px system-ui" font-size="16" font-weight="700" fill="${INK}" text-anchor="middle">H</text>
    <line x1="0" y1="20" x2="0" y2="32" stroke="${INK}" stroke-width="2" />
    <line x1="0" y1="48" x2="0" y2="56" stroke="${INK}" stroke-width="2" />

    <!-- C2 -->
    <text x="60" y="14" font="bold 16px system-ui" font-size="16" font-weight="700" fill="${INK}" text-anchor="middle">H</text>
    <text x="60" y="60" font="bold 16px system-ui" font-size="16" font-weight="700" fill="${INK}" text-anchor="middle">H</text>
    <text x="60" y="40" font="bold 16px system-ui" font-size="16" font-weight="700" fill="${INK}" text-anchor="middle">−C−</text>
    <line x1="60" y1="20" x2="60" y2="32" stroke="${INK}" stroke-width="2" />
    <line x1="60" y1="48" x2="60" y2="56" stroke="${INK}" stroke-width="2" />

    <!-- C3 -->
    <text x="120" y="14" font="bold 16px system-ui" font-size="16" font-weight="700" fill="${INK}" text-anchor="middle">H</text>
    <text x="120" y="60" font="bold 16px system-ui" font-size="16" font-weight="700" fill="${INK}" text-anchor="middle">H</text>
    <text x="120" y="40" font="bold 16px system-ui" font-size="16" font-weight="700" fill="${INK}" text-anchor="middle">−C−</text>
    <line x1="120" y1="20" x2="120" y2="32" stroke="${INK}" stroke-width="2" />
    <line x1="120" y1="48" x2="120" y2="56" stroke="${INK}" stroke-width="2" />

    <!-- C4 -->
    <text x="180" y="14" font="bold 16px system-ui" font-size="16" font-weight="700" fill="${INK}" text-anchor="middle">H</text>
    <text x="180" y="60" font="bold 16px system-ui" font-size="16" font-weight="700" fill="${INK}" text-anchor="middle">H</text>
    <text x="180" y="40" font="bold 16px system-ui" font-size="16" font-weight="700" fill="${INK}" text-anchor="middle">−C−H</text>
    <line x1="180" y1="20" x2="180" y2="32" stroke="${INK}" stroke-width="2" />
    <line x1="180" y1="48" x2="180" y2="56" stroke="${INK}" stroke-width="2" />
  </g>

  <!-- Condensed -->
  <text x="380" y="70" font="bold 13px system-ui" font-size="13" font-weight="700" fill="${INK}" text-anchor="middle">Condensed</text>
  <text x="380" y="86" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">a string of symbols</text>
  <g transform="translate(380, 170)">
    <text x="0" y="0" font="bold 22px system-ui" font-size="22" font-weight="700" fill="${INK}" text-anchor="middle">CH₃ − CH₂ − CH₂ − CH₃</text>
  </g>

  <!-- Skeletal -->
  <text x="600" y="70" font="bold 13px system-ui" font-size="13" font-weight="700" fill="${POSITIVE}" text-anchor="middle">Skeletal (zigzag)</text>
  <text x="600" y="86" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">corners + endpoints = carbons</text>
  <g transform="translate(540, 170)">
    ${alkaneZigzag(0, 0, 4)}
  </g>

  <text x="${W / 2}" y="${H - 56}" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">All three diagrams describe butane.</text>
  <text x="${W / 2}" y="${H - 38}" font="bold 11px system-ui" font-size="11" font-weight="700" fill="${POSITIVE}" text-anchor="middle">Skeletal rules: every corner is a carbon · endpoints are carbons · hydrogens are implied</text>
  <text x="${W / 2}" y="${H - 18}" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">For each C, draw enough H to total four bonds — but you don't have to write them.</text>
`;
  return svgWrap(W, H, "Three ways to draw butane: full, condensed, skeletal", "Three side-by-side representations of the molecule butane (C₄H₁₀): a full structural formula on the left with every C and H atom drawn explicitly, a condensed formula CH₃-CH₂-CH₂-CH₃ in the middle, and the skeletal zigzag on the right with three connected line segments. A caption summarises the skeletal-shorthand rules.", body);
}

function s1_alkaneSeries() {
  const W = 760, H = 320;
  let body = `
  <text x="${W / 2}" y="32" font="bold 18px system-ui" font-size="18" font-weight="700" fill="${INK}" text-anchor="middle">Alkane Series — Methane to Pentane</text>
  <text x="${W / 2}" y="54" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">Each row adds one carbon. The pattern: name + "ane" suffix, formula CₙH₂ₙ₊₂.</text>
`;
  const rows = [
    { name: "methane", formula: "CH₄", nC: 1, suffix: "ane" },
    { name: "ethane", formula: "C₂H₆", nC: 2, suffix: "ane" },
    { name: "propane", formula: "C₃H₈", nC: 3, suffix: "ane" },
    { name: "butane", formula: "C₄H₁₀", nC: 4, suffix: "ane" },
    { name: "pentane", formula: "C₅H₁₂", nC: 5, suffix: "ane" },
  ];
  for (let i = 0; i < rows.length; i++) {
    const r = rows[i];
    const y = 90 + i * 44;
    body += `
    <text x="50" y="${y + 10}" font="bold 14px system-ui" font-size="14" font-weight="700" fill="${INK}">${r.name}</text>
    <text x="170" y="${y + 10}" font="13px system-ui" font-size="13" fill="${MUTED}">${r.formula}</text>`;
    if (r.nC === 1) {
      // single carbon — just a "•" mark (or just label CH4)
      body += `<text x="320" y="${y + 10}" font="bold 16px system-ui" font-size="16" font-weight="700" fill="${INK}">CH₄</text>`;
      body += `<text x="500" y="${y + 10}" font="11px system-ui" font-size="11" fill="${MUTED}">(too simple for skeletal)</text>`;
    } else {
      const startX = 320;
      const startY = y;
      body += `<g>${alkaneZigzag(startX, startY, r.nC)}</g>`;
    }
  }
  body += `
  <text x="${W / 2}" y="${H - 12}" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">Each step on the staircase = one more CH₂. Skeletal makes that pattern jump out.</text>
`;
  return svgWrap(W, H, "Alkane series methane to pentane", "Five rows from methane (CH₄, single-atom note) up through pentane (C₅H₁₂, four-segment zigzag). Each row shows the IUPAC name, molecular formula, and skeletal structure. The staircase pattern is visible as the zigzag grows by one bond per row.", body);
}

function s1_branchedIsomers() {
  const W = 760, H = 320;
  let body = `
  <text x="${W / 2}" y="32" font="bold 18px system-ui" font-size="18" font-weight="700" fill="${INK}" text-anchor="middle">Three Pentanes — Same C₅H₁₂, Different Shapes</text>
  <text x="${W / 2}" y="54" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">Constitutional isomers — same atoms, different connectivity, different boiling points.</text>
`;
  // n-pentane (5 C straight)
  body += `
  <text x="120" y="100" font="bold 14px system-ui" font-size="14" font-weight="700" fill="${INK}" text-anchor="middle">n-pentane</text>
  <text x="120" y="116" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">straight chain · bp 36 °C</text>
  <g transform="translate(50, 160)">
    ${alkaneZigzag(0, 0, 5)}
  </g>`;

  // isopentane (2-methylbutane)
  body += `
  <text x="380" y="100" font="bold 14px system-ui" font-size="14" font-weight="700" fill="${INK}" text-anchor="middle">isopentane</text>
  <text x="380" y="116" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">2-methylbutane · bp 28 °C</text>
  <g transform="translate(310, 160)">
    ${alkaneZigzag(0, 0, 4)}
    ${singleBond(ZAG, 0, ZAG, ZIG)}
  </g>`;

  // neopentane (2,2-dimethylpropane)
  const cx = 620, cy = 175;
  body += `
  <text x="${cx}" y="100" font="bold 14px system-ui" font-size="14" font-weight="700" fill="${INK}" text-anchor="middle">neopentane</text>
  <text x="${cx}" y="116" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">2,2-dimethylpropane · bp 9 °C</text>
  <g>
    ${singleBond(cx, cy, cx - 36, cy)}
    ${singleBond(cx, cy, cx + 36, cy)}
    ${singleBond(cx, cy, cx, cy - 36)}
    ${singleBond(cx, cy, cx, cy + 36)}
  </g>`;

  body += `
  <text x="${W / 2}" y="${H - 30}" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">Same molecular formula. Same number of each atom. Different bond pattern.</text>
  <text x="${W / 2}" y="${H - 12}" font="bold 11px system-ui" font-size="11" font-weight="700" fill="${POSITIVE}" text-anchor="middle">More branching → tighter ball shape → less surface contact → lower boiling point.</text>
`;
  return svgWrap(W, H, "Three pentane isomers", "Three constitutional isomers of pentane (C₅H₁₂) with their skeletal structures and boiling points: n-pentane (straight zigzag, 36 °C), isopentane (2-methylbutane, branched off the second carbon, 28 °C), and neopentane (2,2-dimethylpropane, central carbon with four methyls, 9 °C).", body);
}

function s1_cyclohexaneShapes() {
  const W = 720, H = 320;
  let body = `
  <text x="${W / 2}" y="32" font="bold 18px system-ui" font-size="18" font-weight="700" fill="${INK}" text-anchor="middle">Cyclohexane — Two Ways to Draw the Same Ring</text>

  <!-- Hexagon (planar, 2D) -->
  <text x="180" y="80" font="bold 14px system-ui" font-size="14" font-weight="700" fill="${INK}" text-anchor="middle">Skeletal hexagon</text>
  <text x="180" y="96" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">flat 2D shorthand</text>
  ${hexagon(180, 200, 60)}

  <!-- Chair conformation -->
  <text x="540" y="80" font="bold 14px system-ui" font-size="14" font-weight="700" fill="${POSITIVE}" text-anchor="middle">Chair conformation</text>
  <text x="540" y="96" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">actual 3D shape (zig-zag in space)</text>
  <!-- Chair: 6 vertices in two parallel zigzags -->
  <g>
    <line x1="${540 - 80}" y1="${190}" x2="${540 - 30}" y2="${170}" stroke="${INK}" stroke-width="2.5" />
    <line x1="${540 - 30}" y1="${170}" x2="${540 + 30}" y2="${170}" stroke="${INK}" stroke-width="2.5" />
    <line x1="${540 + 30}" y1="${170}" x2="${540 + 80}" y2="${190}" stroke="${INK}" stroke-width="2.5" />
    <line x1="${540 - 80}" y1="${230}" x2="${540 - 30}" y2="${250}" stroke="${INK}" stroke-width="2.5" />
    <line x1="${540 - 30}" y1="${250}" x2="${540 + 30}" y2="${250}" stroke="${INK}" stroke-width="2.5" />
    <line x1="${540 + 30}" y1="${250}" x2="${540 + 80}" y2="${230}" stroke="${INK}" stroke-width="2.5" />
    <line x1="${540 - 80}" y1="${190}" x2="${540 - 80}" y2="${230}" stroke="${INK}" stroke-width="2.5" />
    <line x1="${540 + 80}" y1="${190}" x2="${540 + 80}" y2="${230}" stroke="${INK}" stroke-width="2.5" />
  </g>

  <text x="${W / 2}" y="${H - 30}" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">Both diagrams describe the same molecule (C₆H₁₂). The hexagon is shorthand; the chair is true 3D.</text>
  <text x="${W / 2}" y="${H - 12}" font="bold 11px system-ui" font-size="11" font-weight="700" fill="${POSITIVE}" text-anchor="middle">In real life cyclohexane is never flat — it puckers into the chair to reduce strain.</text>
`;
  return svgWrap(W, H, "Cyclohexane hexagon and chair conformation", "Two side-by-side drawings of cyclohexane: a flat regular hexagon on the left as the skeletal shorthand, and an angular chair-shaped diagram on the right showing the molecule's true 3D conformation with two parallel zigzags connected vertically.", body);
}

function s1_chainNumbering() {
  const W = 600, H = 280;
  // 2-methylbutane with locants on each carbon
  const bx = 100;
  const by = 160;
  const pts = zigzagPoints(bx, by, 4, 0);
  let body = `
  <text x="${W / 2}" y="32" font="bold 18px system-ui" font-size="18" font-weight="700" fill="${INK}" text-anchor="middle">Numbering the Chain — Choose the Lowest Locants</text>
  <text x="${W / 2}" y="54" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">Walk the longest chain. Number from whichever end gives the substituent(s) the smallest position number.</text>

  <!-- Skeletal -->
`;
  for (let i = 0; i < pts.length - 1; i++) {
    body += singleBond(pts[i].x, pts[i].y, pts[i + 1].x, pts[i + 1].y);
  }
  // Methyl branch off C2 (pts[1])
  const c2 = pts[1];
  body += singleBond(c2.x, c2.y, c2.x, c2.y + ZIG);
  // Number labels (correct numbering 1-2-3-4 from left)
  for (let i = 0; i < pts.length; i++) {
    body += `<text x="${pts[i].x}" y="${pts[i].y - 10}" font="bold 14px system-ui" font-size="14" font-weight="700" fill="${POSITIVE}" text-anchor="middle">${i + 1}</text>`;
  }
  // Methyl group label
  body += `<text x="${c2.x}" y="${c2.y + ZIG + 16}" font="bold 13px system-ui" font-size="13" font-weight="700" fill="${ACCENT_2}" text-anchor="middle">CH₃</text>`;
  body += `
  <text x="${pts[1].x + 60}" y="${pts[1].y + 25}" font="bold 12px system-ui" font-size="12" font-weight="700" fill="${POSITIVE}">methyl on C2</text>

  <!-- "WRONG numbering" alternative -->
  <text x="450" y="100" font="bold 13px system-ui" font-size="13" font-weight="700" fill="${NEGATIVE}" text-anchor="middle">numbered the wrong way:</text>
  <text x="450" y="118" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">methyl would land on C3 (bigger number)</text>

  <text x="${W / 2}" y="${H - 30}" font="bold 12px system-ui" font-size="12" font-weight="700" fill="${POSITIVE}" text-anchor="middle">2-methylbutane ✓</text>
  <text x="${W / 2}" y="${H - 12}" font="11px system-ui" font-size="11" fill="${NEGATIVE}" text-anchor="middle">3-methylbutane ✗ (same molecule, but rule says "lowest locants" → use the 2)</text>
`;
  return svgWrap(W, H, "Numbering the carbon chain by lowest locants", "A skeletal structure of 2-methylbutane with carbons labelled 1, 2, 3, 4 from left to right and a CH₃ methyl branch hanging off carbon 2. Annotation explains that numbering from the right would put the methyl on carbon 3 — the IUPAC 'lowest locants' rule selects the lower-numbered direction.", body);
}

// ────────────────────────────────────────────────────────────────────────────
// SECTION 2 — Multiple Bonds + Aromatics (4 SVGs)
// ────────────────────────────────────────────────────────────────────────────

function s2_alkeneDouble() {
  const W = 720, H = 280;
  let body = `
  <text x="${W / 2}" y="32" font="bold 18px system-ui" font-size="18" font-weight="700" fill="${INK}" text-anchor="middle">Alkenes — One Double Bond (CₙH₂ₙ)</text>
  <text x="${W / 2}" y="54" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">A "=" between two carbons means double bond. Suffix changes from -ane to -ene.</text>
`;
  const rows = [
    { name: "ethene", formula: "C₂H₄", x: 120, y: 170 },
    { name: "propene", formula: "C₃H₆", x: 320, y: 170 },
    { name: "but-2-ene", formula: "C₄H₈", x: 540, y: 170 },
  ];
  // Ethene: 2 C with double bond
  body += `
  <text x="${rows[0].x}" y="120" font="bold 13px system-ui" font-size="13" font-weight="700" fill="${INK}" text-anchor="middle">${rows[0].name}</text>
  <text x="${rows[0].x}" y="136" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">${rows[0].formula}</text>
  ${doubleBond(rows[0].x - BL / 2, rows[0].y, rows[0].x + BL / 2, rows[0].y)}`;

  // Propene: zigzag with double bond on first segment
  const p2 = zigzagPoints(rows[1].x - BL, rows[1].y, 3, 0);
  body += `
  <text x="${rows[1].x}" y="120" font="bold 13px system-ui" font-size="13" font-weight="700" fill="${INK}" text-anchor="middle">${rows[1].name}</text>
  <text x="${rows[1].x}" y="136" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">${rows[1].formula}</text>
  ${doubleBond(p2[0].x, p2[0].y, p2[1].x, p2[1].y)}
  ${singleBond(p2[1].x, p2[1].y, p2[2].x, p2[2].y)}`;

  // But-2-ene: 4-C zigzag with double bond between C2 and C3
  const p3 = zigzagPoints(rows[2].x - BL * 1.5, rows[2].y, 4, 0);
  body += `
  <text x="${rows[2].x}" y="120" font="bold 13px system-ui" font-size="13" font-weight="700" fill="${INK}" text-anchor="middle">${rows[2].name}</text>
  <text x="${rows[2].x}" y="136" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">${rows[2].formula}</text>
  ${singleBond(p3[0].x, p3[0].y, p3[1].x, p3[1].y)}
  ${doubleBond(p3[1].x, p3[1].y, p3[2].x, p3[2].y)}
  ${singleBond(p3[2].x, p3[2].y, p3[3].x, p3[3].y)}`;

  body += `
  <text x="${W / 2}" y="${H - 16}" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">The "2" in but-2-ene tells you the double bond starts at carbon 2.</text>
`;
  return svgWrap(W, H, "Alkene series with double bonds", "Three alkene structures: ethene (C₂H₄, two carbons joined by a double bond), propene (C₃H₆, three carbons with a double bond at one end), and but-2-ene (C₄H₈, four-carbon chain with the double bond between carbons 2 and 3).", body);
}

function s2_alkyneTriple() {
  const W = 600, H = 260;
  let body = `
  <text x="${W / 2}" y="32" font="bold 18px system-ui" font-size="18" font-weight="700" fill="${INK}" text-anchor="middle">Alkynes — One Triple Bond (CₙH₂ₙ₋₂)</text>
  <text x="${W / 2}" y="54" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">"≡" between two carbons means triple bond. Suffix changes to -yne.</text>

  <!-- Ethyne (acetylene) -->
  <text x="180" y="120" font="bold 13px system-ui" font-size="13" font-weight="700" fill="${INK}" text-anchor="middle">ethyne (acetylene)</text>
  <text x="180" y="136" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">C₂H₂</text>
  ${tripleBond(180 - BL / 2, 170, 180 + BL / 2, 170)}

  <!-- Propyne -->
  <text x="430" y="120" font="bold 13px system-ui" font-size="13" font-weight="700" fill="${INK}" text-anchor="middle">propyne</text>
  <text x="430" y="136" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">C₃H₄</text>
`;
  const pp = [
    { x: 380, y: 170 },
    { x: 380 + BL, y: 170 },
    { x: 380 + BL + ZAG, y: 170 - ZIG },
  ];
  body += tripleBond(pp[0].x, pp[0].y, pp[1].x, pp[1].y);
  body += singleBond(pp[1].x, pp[1].y, pp[2].x, pp[2].y);

  body += `
  <text x="${W / 2}" y="${H - 16}" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">Triple bond = three lines drawn parallel between two carbons. Linear geometry — straight, not zigzag.</text>
`;
  return svgWrap(W, H, "Alkyne series with triple bonds", "Two alkyne structures: ethyne also called acetylene (C₂H₂, two carbons joined by a triple bond), and propyne (C₃H₄, three-carbon chain with a triple bond at one end).", body);
}

function s2_cisTrans() {
  const W = 600, H = 280;
  let body = `
  <text x="${W / 2}" y="32" font="bold 18px system-ui" font-size="18" font-weight="700" fill="${INK}" text-anchor="middle">Cis-Trans Isomers — Same Molecule, Different Geometry</text>
  <text x="${W / 2}" y="54" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">Substituents on a double bond can sit on the same side (cis) or opposite sides (trans).</text>
`;
  // cis-2-butene: both methyls on same side
  const cisX = 160, cisY = 160;
  body += `
  <text x="${cisX}" y="100" font="bold 13px system-ui" font-size="13" font-weight="700" fill="${POSITIVE}" text-anchor="middle">cis-2-butene</text>
  <text x="${cisX}" y="116" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">methyls on same side (above)</text>
  ${doubleBond(cisX - BL / 2, cisY, cisX + BL / 2, cisY)}
  ${singleBond(cisX - BL / 2, cisY, cisX - BL / 2 - ZAG, cisY - ZIG)}
  ${singleBond(cisX + BL / 2, cisY, cisX + BL / 2 + ZAG, cisY - ZIG)}`;

  // trans-2-butene: methyls on opposite sides
  const trX = 440, trY = 160;
  body += `
  <text x="${trX}" y="100" font="bold 13px system-ui" font-size="13" font-weight="700" fill="${NEGATIVE}" text-anchor="middle">trans-2-butene</text>
  <text x="${trX}" y="116" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">methyls on opposite sides</text>
  ${doubleBond(trX - BL / 2, trY, trX + BL / 2, trY)}
  ${singleBond(trX - BL / 2, trY, trX - BL / 2 - ZAG, trY - ZIG)}
  ${singleBond(trX + BL / 2, trY, trX + BL / 2 + ZAG, trY + ZIG)}`;

  body += `
  <text x="${W / 2}" y="${H - 30}" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">Same atoms, same connectivity. Different shapes → different physical properties.</text>
  <text x="${W / 2}" y="${H - 12}" font="bold 11px system-ui" font-size="11" font-weight="700" fill="${ACCENT}" text-anchor="middle">The double bond can't twist, so cis and trans are real different molecules — not just "rotated".</text>
`;
  return svgWrap(W, H, "Cis-trans isomers of 2-butene", "Two skeletal structures of 2-butene side by side. Cis-2-butene has both methyl substituents on the same side of the central double bond (both pointing up); trans-2-butene has the methyls on opposite sides (one up, one down).", body);
}

function s2_benzeneResonance() {
  const W = 720, H = 320;
  const cy = 180;
  let body = `
  <text x="${W / 2}" y="32" font="bold 18px system-ui" font-size="18" font-weight="700" fill="${INK}" text-anchor="middle">Benzene — Two Kekulé Forms and the Modern "Circle"</text>
  <text x="${W / 2}" y="54" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">Six carbons in a ring, three double bonds — but the bonds aren't really "fixed" in place.</text>
`;
  // Kekulé form 1
  const k1cx = 150, r = 50;
  const k1pts = Array.from({ length: 6 }, (_, i) => {
    const ang = -Math.PI / 2 + i * (Math.PI / 3);
    return { x: k1cx + r * Math.cos(ang), y: cy + r * Math.sin(ang) };
  });
  body += `
  <text x="${k1cx}" y="100" font="bold 13px system-ui" font-size="13" font-weight="700" fill="${INK}" text-anchor="middle">Kekulé form A</text>`;
  for (let i = 0; i < 6; i++) {
    const next = (i + 1) % 6;
    if (i % 2 === 0) {
      body += doubleBond(k1pts[i].x, k1pts[i].y, k1pts[next].x, k1pts[next].y);
    } else {
      body += singleBond(k1pts[i].x, k1pts[i].y, k1pts[next].x, k1pts[next].y);
    }
  }

  // Resonance arrow
  body += `
  <line x1="220" y1="180" x2="280" y2="180" stroke="${ACCENT_2}" stroke-width="2.5" />
  <polygon points="280,180 270,174 270,186" fill="${ACCENT_2}" />
  <line x1="280" y1="186" x2="220" y2="186" stroke="${ACCENT_2}" stroke-width="2.5" />
  <polygon points="220,186 230,180 230,192" fill="${ACCENT_2}" />
  <text x="250" y="170" font="bold 11px system-ui" font-size="11" font-weight="700" fill="${ACCENT_2}" text-anchor="middle">resonance</text>
`;

  // Kekulé form 2
  const k2cx = 360;
  const k2pts = Array.from({ length: 6 }, (_, i) => {
    const ang = -Math.PI / 2 + i * (Math.PI / 3);
    return { x: k2cx + r * Math.cos(ang), y: cy + r * Math.sin(ang) };
  });
  body += `
  <text x="${k2cx}" y="100" font="bold 13px system-ui" font-size="13" font-weight="700" fill="${INK}" text-anchor="middle">Kekulé form B</text>`;
  for (let i = 0; i < 6; i++) {
    const next = (i + 1) % 6;
    if (i % 2 === 1) {
      body += doubleBond(k2pts[i].x, k2pts[i].y, k2pts[next].x, k2pts[next].y);
    } else {
      body += singleBond(k2pts[i].x, k2pts[i].y, k2pts[next].x, k2pts[next].y);
    }
  }

  // Equivalence arrow
  body += `
  <line x1="430" y1="180" x2="500" y2="180" stroke="${POSITIVE}" stroke-width="2.5" />
  <polygon points="500,180 490,174 490,186" fill="${POSITIVE}" />
  <text x="465" y="170" font="bold 11px system-ui" font-size="11" font-weight="700" fill="${POSITIVE}" text-anchor="middle">≡</text>
`;

  // Modern circle representation
  const k3cx = 580;
  const k3pts = Array.from({ length: 6 }, (_, i) => {
    const ang = -Math.PI / 2 + i * (Math.PI / 3);
    return { x: k3cx + r * Math.cos(ang), y: cy + r * Math.sin(ang) };
  });
  body += `
  <text x="${k3cx}" y="100" font="bold 13px system-ui" font-size="13" font-weight="700" fill="${FG_RING}" text-anchor="middle">Modern: circle</text>`;
  for (let i = 0; i < 6; i++) {
    const next = (i + 1) % 6;
    body += singleBond(k3pts[i].x, k3pts[i].y, k3pts[next].x, k3pts[next].y);
  }
  body += `<circle cx="${k3cx}" cy="${cy}" r="${r * 0.55}" fill="none" stroke="${FG_RING}" stroke-width="2.5" />`;

  body += `
  <text x="${W / 2}" y="${H - 30}" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">In reality, the six bonds are all the same length — somewhere between single and double.</text>
  <text x="${W / 2}" y="${H - 12}" font="bold 11px system-ui" font-size="11" font-weight="700" fill="${FG_RING}" text-anchor="middle">The circle inside the hexagon is shorthand for "delocalised electrons all around the ring".</text>
`;
  return svgWrap(W, H, "Benzene resonance forms and circle representation", "Three depictions of benzene side by side: Kekulé form A (hexagon with alternating single-double bonds starting on one position), resonance double-arrow, Kekulé form B (alternation shifted by one position), equivalence symbol, and the modern circle-in-hexagon shorthand showing delocalised electrons.", body);
}

// ────────────────────────────────────────────────────────────────────────────
// SECTION 3 — Functional Groups (4 SVGs)
// ────────────────────────────────────────────────────────────────────────────

function s3_functionalGroupsReference() {
  const W = 760, H = 460;
  // 7 functional groups in a grid (2 rows × 4 cols, last cell blank)
  const groups = [
    { name: "alcohol", suffix: "-ol", group: "−OH", color: FG_HYDROXYL, example: "ethanol" },
    { name: "aldehyde", suffix: "-al", group: "−CHO", color: FG_CARBONYL, example: "ethanal" },
    { name: "ketone", suffix: "-one", group: "C=O (mid)", color: FG_CARBONYL, example: "propan-2-one" },
    { name: "carboxylic acid", suffix: "-oic acid", group: "−COOH", color: FG_CARBONYL, example: "ethanoic acid" },
    { name: "ester", suffix: "-oate", group: "−COO−", color: FG_CARBONYL, example: "methyl ethanoate" },
    { name: "amine", suffix: "-amine", group: "−NH₂", color: FG_AMINE, example: "ethylamine" },
    { name: "halide", suffix: "(no name change)", group: "−Cl, −Br...", color: FG_HALOGEN, example: "chloroethane" },
  ];
  let body = `
  <text x="${W / 2}" y="32" font="bold 18px system-ui" font-size="18" font-weight="700" fill="${INK}" text-anchor="middle">Functional Groups — Reference Card</text>
  <text x="${W / 2}" y="54" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">A functional group is the bit of a molecule that decides how it reacts. Same group → same chemistry.</text>
`;
  const cellW = 180;
  const cellH = 150;
  const cols = 4;
  for (let i = 0; i < groups.length; i++) {
    const r = Math.floor(i / cols);
    const c = i % cols;
    const x = 20 + c * cellW;
    const y = 90 + r * (cellH + 14);
    const g = groups[i];
    body += `
    <rect x="${x}" y="${y}" width="${cellW - 12}" height="${cellH}" rx="8" fill="${BG}" stroke="${g.color}" stroke-width="2" />
    <text x="${x + (cellW - 12) / 2}" y="${y + 22}" font="bold 14px system-ui" font-size="14" font-weight="700" fill="${g.color}" text-anchor="middle">${g.name}</text>
    <text x="${x + (cellW - 12) / 2}" y="${y + 60}" font="bold 22px system-ui" font-size="22" font-weight="700" fill="${INK}" text-anchor="middle">R ${g.group}</text>
    <text x="${x + (cellW - 12) / 2}" y="${y + 90}" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">suffix: ${g.suffix}</text>
    <text x="${x + (cellW - 12) / 2}" y="${y + 110}" font="bold 11px system-ui" font-size="11" font-weight="700" fill="${MUTED}" text-anchor="middle">e.g. ${g.example}</text>`;
  }
  body += `
  <text x="${W / 2}" y="${H - 22}" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">"R" stands for "the rest of the molecule" — usually a hydrocarbon chain.</text>
  <text x="${W / 2}" y="${H - 6}" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">Add the right suffix to the parent-chain name and you've named most simple organic compounds.</text>
`;
  return svgWrap(W, H, "Functional groups reference card", "Seven coloured cards in a 4-by-2 grid (last cell blank), each labelling a functional group: alcohol (−OH), aldehyde (−CHO), ketone (C=O middle), carboxylic acid (−COOH), ester (−COO−), amine (−NH₂), and halide (−Cl/−Br...). Each card shows the group name, the R-group skeletal shorthand, the suffix added to the IUPAC name, and an example compound.", body);
}

function s3_alcoholAldehydeKetone() {
  const W = 720, H = 320;
  let body = `
  <text x="${W / 2}" y="32" font="bold 18px system-ui" font-size="18" font-weight="700" fill="${INK}" text-anchor="middle">Three Cousins: Alcohol · Aldehyde · Ketone</text>
  <text x="${W / 2}" y="54" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">All three involve oxygen on the carbon skeleton — what differs is how the oxygen is attached.</text>
`;

  // Alcohol — ethanol
  body += `
  <text x="160" y="100" font="bold 13px system-ui" font-size="13" font-weight="700" fill="${FG_HYDROXYL}" text-anchor="middle">alcohol</text>
  <text x="160" y="116" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">ethanol</text>`;
  const alc = zigzagPoints(110, 180, 2, 0);
  body += singleBond(alc[0].x, alc[0].y, alc[1].x, alc[1].y);
  body += singleBond(alc[1].x, alc[1].y, alc[1].x + ZAG, alc[1].y + ZIG);
  body += atomLabel(alc[1].x + ZAG + 14, alc[1].y + ZIG, "OH", FG_HYDROXYL);

  // Aldehyde — ethanal
  body += `
  <text x="380" y="100" font="bold 13px system-ui" font-size="13" font-weight="700" fill="${FG_CARBONYL}" text-anchor="middle">aldehyde</text>
  <text x="380" y="116" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">ethanal</text>`;
  const ald = zigzagPoints(330, 180, 2, 0);
  body += singleBond(ald[0].x, ald[0].y, ald[1].x, ald[1].y);
  body += doubleBond(ald[1].x, ald[1].y, ald[1].x + ZAG, ald[1].y - ZIG);
  body += atomLabel(ald[1].x + ZAG + 14, ald[1].y - ZIG - 4, "O", FG_CARBONYL);
  body += singleBond(ald[1].x, ald[1].y, ald[1].x + ZAG, ald[1].y + ZIG);
  body += atomLabel(ald[1].x + ZAG + 8, ald[1].y + ZIG, "H", INK, 14);

  // Ketone — propan-2-one (acetone)
  body += `
  <text x="600" y="100" font="bold 13px system-ui" font-size="13" font-weight="700" fill="${FG_CARBONYL}" text-anchor="middle">ketone</text>
  <text x="600" y="116" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">propan-2-one (acetone)</text>`;
  const ket = zigzagPoints(540, 180, 3, 0);
  body += singleBond(ket[0].x, ket[0].y, ket[1].x, ket[1].y);
  body += singleBond(ket[1].x, ket[1].y, ket[2].x, ket[2].y);
  body += doubleBond(ket[1].x, ket[1].y, ket[1].x, ket[1].y + ZIG);
  body += atomLabel(ket[1].x, ket[1].y + ZIG + 18, "O", FG_CARBONYL);

  body += `
  <text x="${W / 2}" y="${H - 30}" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">Alcohol: −OH at the end · Aldehyde: =O at the end · Ketone: =O in the middle of the chain.</text>
  <text x="${W / 2}" y="${H - 12}" font="bold 11px system-ui" font-size="11" font-weight="700" fill="${FG_CARBONYL}" text-anchor="middle">Aldehyde + ketone share the same carbonyl group (C=O) — different position, different chemistry.</text>
`;
  return svgWrap(W, H, "Alcohol aldehyde and ketone functional groups", "Three skeletal structures side by side: ethanol (two-carbon zigzag with an OH coming off the end carbon), ethanal (two-carbon zigzag with =O double-bonded plus H coming off the end carbon), and propan-2-one (three-carbon zigzag with =O double-bonded coming off the middle carbon).", body);
}

function s3_carboxylicAcidEster() {
  const W = 600, H = 260;
  let body = `
  <text x="${W / 2}" y="32" font="bold 18px system-ui" font-size="18" font-weight="700" fill="${INK}" text-anchor="middle">Carboxylic Acid + Ester — The Carbonyl + Oxygen Pair</text>

  <!-- Carboxylic acid: ethanoic acid -->
  <text x="170" y="80" font="bold 13px system-ui" font-size="13" font-weight="700" fill="${FG_CARBONYL}" text-anchor="middle">carboxylic acid</text>
  <text x="170" y="96" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">ethanoic acid (vinegar!)</text>`;
  const ac = zigzagPoints(120, 160, 2, 0);
  body += singleBond(ac[0].x, ac[0].y, ac[1].x, ac[1].y);
  body += doubleBond(ac[1].x, ac[1].y, ac[1].x + ZAG, ac[1].y - ZIG);
  body += atomLabel(ac[1].x + ZAG + 12, ac[1].y - ZIG, "O", FG_CARBONYL);
  body += singleBond(ac[1].x, ac[1].y, ac[1].x + ZAG, ac[1].y + ZIG);
  body += atomLabel(ac[1].x + ZAG + 16, ac[1].y + ZIG, "OH", FG_HYDROXYL);

  // Ester: methyl ethanoate
  body += `
  <text x="430" y="80" font="bold 13px system-ui" font-size="13" font-weight="700" fill="${FG_CARBONYL}" text-anchor="middle">ester</text>
  <text x="430" y="96" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">methyl ethanoate (fruity smell)</text>`;
  const es = zigzagPoints(360, 160, 2, 0);
  body += singleBond(es[0].x, es[0].y, es[1].x, es[1].y);
  body += doubleBond(es[1].x, es[1].y, es[1].x + ZAG, es[1].y - ZIG);
  body += atomLabel(es[1].x + ZAG + 12, es[1].y - ZIG, "O", FG_CARBONYL);
  body += singleBond(es[1].x, es[1].y, es[1].x + ZAG, es[1].y + ZIG);
  body += atomLabel(es[1].x + ZAG + 14, es[1].y + ZIG, "O", FG_CARBONYL);
  body += singleBond(es[1].x + ZAG + 14, es[1].y + ZIG, es[1].x + ZAG * 2 + 14, es[1].y + ZIG + ZIG);
  body += `<text x="${es[1].x + ZAG * 2 + 30}" y="${es[1].y + ZIG + ZIG + 6}" font="bold 13px system-ui" font-size="13" font-weight="700" fill="${INK}">CH₃</text>`;

  body += `
  <text x="${W / 2}" y="${H - 16}" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">Replace the −OH of an acid with −O−R and you get an ester. Esters smell like flowers and fruit.</text>
`;
  return svgWrap(W, H, "Carboxylic acid and ester functional groups", "Two structures side by side: ethanoic acid (the acid found in vinegar) shown with a two-carbon zigzag carrying =O and −OH on its terminal carbon, and methyl ethanoate (a fruity-smelling ester) shown with the −OH replaced by an −O−CH₃ group.", body);
}

function s3_amineAmide() {
  const W = 600, H = 260;
  let body = `
  <text x="${W / 2}" y="32" font="bold 18px system-ui" font-size="18" font-weight="700" fill="${INK}" text-anchor="middle">Amine vs Amide — Nitrogen-Containing Groups</text>

  <!-- Amine: ethylamine -->
  <text x="170" y="80" font="bold 13px system-ui" font-size="13" font-weight="700" fill="${FG_AMINE}" text-anchor="middle">amine</text>
  <text x="170" y="96" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">ethylamine</text>`;
  const am = zigzagPoints(120, 170, 2, 0);
  body += singleBond(am[0].x, am[0].y, am[1].x, am[1].y);
  body += singleBond(am[1].x, am[1].y, am[1].x + ZAG, am[1].y + ZIG);
  body += atomLabel(am[1].x + ZAG + 18, am[1].y + ZIG, "NH₂", FG_AMINE);

  // Amide: ethanamide
  body += `
  <text x="430" y="80" font="bold 13px system-ui" font-size="13" font-weight="700" fill="${FG_AMINE}" text-anchor="middle">amide</text>
  <text x="430" y="96" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">ethanamide</text>`;
  const md = zigzagPoints(380, 170, 2, 0);
  body += singleBond(md[0].x, md[0].y, md[1].x, md[1].y);
  body += doubleBond(md[1].x, md[1].y, md[1].x + ZAG, md[1].y - ZIG);
  body += atomLabel(md[1].x + ZAG + 12, md[1].y - ZIG, "O", FG_CARBONYL);
  body += singleBond(md[1].x, md[1].y, md[1].x + ZAG, md[1].y + ZIG);
  body += atomLabel(md[1].x + ZAG + 18, md[1].y + ZIG, "NH₂", FG_AMINE);

  body += `
  <text x="${W / 2}" y="${H - 32}" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">Amine = nitrogen attached to a carbon chain (like ammonia with a tail).</text>
  <text x="${W / 2}" y="${H - 14}" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">Amide = nitrogen attached to a carbonyl carbon (=O) — the building block of proteins.</text>
`;
  return svgWrap(W, H, "Amine and amide functional groups", "Two structures side by side: ethylamine (a two-carbon zigzag with −NH₂ on one end) and ethanamide (a two-carbon zigzag with =O double-bonded plus −NH₂ on the same terminal carbon).", body);
}

// ────────────────────────────────────────────────────────────────────────────
// SECTION 4 — IUPAC Naming (3 SVGs)
// ────────────────────────────────────────────────────────────────────────────

function s4_iupacFlowchart() {
  const W = 600, H = 480;
  let body = `
  <text x="${W / 2}" y="32" font="bold 18px system-ui" font-size="18" font-weight="700" fill="${INK}" text-anchor="middle">IUPAC Naming — Five-Step Flowchart</text>
  <text x="${W / 2}" y="54" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">Apply these in order. Most molecules can be named in under a minute once it's a habit.</text>
`;
  const steps = [
    { n: 1, title: "Find the longest carbon chain", note: "this is the parent name" },
    { n: 2, title: "Identify any branches (substituents)", note: "methyl, ethyl, halogen, etc." },
    { n: 3, title: "Number the chain to give the lowest locants", note: "to the substituents (and double bonds)" },
    { n: 4, title: "Name each substituent and its position", note: "alphabetically; use 2,3- or 1,1- for repeats" },
    { n: 5, title: "Add the suffix for the highest-priority group", note: "-ol > -al > -one > -ene > -ane (not strict)" },
  ];
  for (let i = 0; i < steps.length; i++) {
    const y = 90 + i * 70;
    body += `
    <rect x="60" y="${y}" width="480" height="56" rx="10" fill="${BG}" stroke="${ACCENT}" stroke-width="2" />
    <circle cx="92" cy="${y + 28}" r="20" fill="${ACCENT}" />
    <text x="92" y="${y + 33}" font="bold 16px system-ui" font-size="16" font-weight="700" fill="white" text-anchor="middle">${steps[i].n}</text>
    <text x="124" y="${y + 24}" font="bold 14px system-ui" font-size="14" font-weight="700" fill="${INK}">${steps[i].title}</text>
    <text x="124" y="${y + 42}" font="11px system-ui" font-size="11" fill="${MUTED}">${steps[i].note}</text>`;
    if (i < steps.length - 1) {
      body += `
      <line x1="${W / 2}" y1="${y + 56}" x2="${W / 2}" y2="${y + 70}" stroke="${ACCENT}" stroke-width="2" marker-end="url(#step-arr)" />`;
    }
  }
  body += `
  <defs>
    <marker id="step-arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="${ACCENT}" />
    </marker>
  </defs>
`;
  return svgWrap(W, H, "IUPAC naming five step flowchart", "A vertical five-step flowchart titled 'IUPAC Naming'. Each step is a numbered card connected by a downward arrow to the next: 1) Find the longest carbon chain (parent name). 2) Identify any branches (substituents). 3) Number the chain to give the lowest locants. 4) Name each substituent and its position. 5) Add the suffix for the highest-priority group.", body);
}

function s4_nameBuildWalkthrough() {
  const W = 720, H = 360;
  // Worked example: 3-bromo-2-methylbutane
  let body = `
  <text x="${W / 2}" y="32" font="bold 18px system-ui" font-size="18" font-weight="700" fill="${INK}" text-anchor="middle">Worked Example — Naming 3-bromo-2-methylbutane</text>

  <!-- Structure on the left -->
  <g transform="translate(120, 130)">
`;
  const pts = zigzagPoints(0, 0, 4, 0);
  for (let i = 0; i < pts.length - 1; i++) {
    body += singleBond(pts[i].x, pts[i].y, pts[i + 1].x, pts[i + 1].y);
  }
  // Methyl on C2
  body += singleBond(pts[1].x, pts[1].y, pts[1].x, pts[1].y - ZIG);
  // Br on C3
  body += singleBond(pts[2].x, pts[2].y, pts[2].x, pts[2].y + ZIG);
  body += atomLabel(pts[2].x, pts[2].y + ZIG + 18, "Br", FG_HALOGEN, 16);
  body += `<text x="${pts[1].x}" y="${pts[1].y - ZIG - 6}" font="bold 13px system-ui" font-size="13" font-weight="700" fill="${ACCENT_2}" text-anchor="middle">CH₃</text>`;
  // Locant numbers
  for (let i = 0; i < pts.length; i++) {
    body += `<text x="${pts[i].x}" y="${pts[i].y - 10}" font="bold 12px system-ui" font-size="12" font-weight="700" fill="${POSITIVE}" text-anchor="middle">${i + 1}</text>`;
  }
  body += `</g>`;

  // Steps on the right
  const stepX = 380;
  const steps = [
    { label: "1. Parent chain", value: "4 carbons → butane" },
    { label: "2. Substituents", value: "methyl + bromo" },
    { label: "3. Lowest locants", value: "methyl on C2 · bromo on C3" },
    { label: "4. Alphabetise", value: "bromo before methyl" },
    { label: "5. Final name", value: "3-bromo-2-methylbutane" },
  ];
  for (let i = 0; i < steps.length; i++) {
    const y = 90 + i * 44;
    body += `
    <text x="${stepX}" y="${y + 4}" font="bold 13px system-ui" font-size="13" font-weight="700" fill="${ACCENT}">${steps[i].label}</text>
    <text x="${stepX}" y="${y + 22}" font="13px system-ui" font-size="13" fill="${INK}">${steps[i].value}</text>`;
    if (i < steps.length - 1) body += `<line x1="${stepX}" y1="${y + 32}" x2="${W - 40}" y2="${y + 32}" stroke="${MUTED}" stroke-width="0.6" stroke-dasharray="2 4" />`;
  }
  body += `
  <rect x="${stepX - 8}" y="${90 + 4 * 44 - 8}" width="${W - stepX - 32}" height="40" rx="8" fill="${HIGHLIGHT}" stroke="${POSITIVE}" stroke-width="2" />
  <text x="${stepX}" y="${90 + 4 * 44 + 4}" font="bold 13px system-ui" font-size="13" font-weight="700" fill="${POSITIVE}">5. Final name</text>
  <text x="${stepX}" y="${90 + 4 * 44 + 22}" font="bold 13px system-ui" font-size="13" font-weight="700" fill="${INK}">3-bromo-2-methylbutane</text>
`;
  return svgWrap(W, H, "Worked example naming 3-bromo-2-methylbutane", "Left side shows a four-carbon zigzag with carbon positions 1-2-3-4 labelled; a CH₃ methyl branch on C2 and a Br substituent on C3. Right side shows five labelled rows applying the IUPAC steps: parent chain butane, substituents methyl + bromo, lowest locants 2 and 3, alphabetise bromo-before-methyl, and final name highlighted in green: 3-bromo-2-methylbutane.", body);
}

function s4_prefixSuffixCheatSheet() {
  const W = 720, H = 360;
  let body = `
  <text x="${W / 2}" y="32" font="bold 18px system-ui" font-size="18" font-weight="700" fill="${INK}" text-anchor="middle">Naming Cheat Sheet — Prefixes and Suffixes</text>

  <!-- Prefixes (number → name) -->
  <text x="180" y="80" font="bold 14px system-ui" font-size="14" font-weight="700" fill="${ACCENT}" text-anchor="middle">parent-chain prefixes (count the carbons)</text>
`;
  const prefixes = [
    "1: meth-", "2: eth-", "3: prop-", "4: but-", "5: pent-",
    "6: hex-", "7: hept-", "8: oct-", "9: non-", "10: dec-",
  ];
  for (let i = 0; i < prefixes.length; i++) {
    const r = Math.floor(i / 5);
    const c = i % 5;
    const x = 30 + c * 70;
    const y = 110 + r * 30;
    body += `<rect x="${x}" y="${y}" width="60" height="22" rx="4" fill="${BG}" stroke="${ACCENT}" stroke-width="1" />
    <text x="${x + 30}" y="${y + 16}" font="bold 12px system-ui" font-size="12" font-weight="700" fill="${INK}" text-anchor="middle">${prefixes[i]}</text>`;
  }

  // Suffixes (functional groups)
  body += `
  <text x="500" y="80" font="bold 14px system-ui" font-size="14" font-weight="700" fill="${POSITIVE}" text-anchor="middle">functional-group suffixes (priority order)</text>`;
  const suffixes = [
    { group: "carboxylic acid", suf: "-oic acid", priority: "highest" },
    { group: "ester", suf: "-oate", priority: "↓" },
    { group: "amide", suf: "-amide", priority: "↓" },
    { group: "aldehyde", suf: "-al", priority: "↓" },
    { group: "ketone", suf: "-one", priority: "↓" },
    { group: "alcohol", suf: "-ol", priority: "↓" },
    { group: "amine", suf: "-amine", priority: "↓" },
    { group: "alkene/alkyne", suf: "-ene / -yne", priority: "↓" },
    { group: "alkane", suf: "-ane", priority: "lowest" },
  ];
  for (let i = 0; i < suffixes.length; i++) {
    const y = 100 + i * 24;
    body += `
    <text x="380" y="${y + 14}" font="13px system-ui" font-size="13" fill="${INK}">${suffixes[i].group}</text>
    <text x="540" y="${y + 14}" font="bold 13px system-ui" font-size="13" font-weight="700" fill="${POSITIVE}">${suffixes[i].suf}</text>
    <text x="660" y="${y + 14}" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="end">${suffixes[i].priority}</text>`;
  }

  body += `
  <text x="${W / 2}" y="${H - 30}" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">Example: 4-carbon chain with an alcohol group → "but" + "an" + "ol" = butanol.</text>
  <text x="${W / 2}" y="${H - 12}" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">When two functional groups compete, use the higher-priority one as the suffix; the other becomes a prefix.</text>
`;
  return svgWrap(W, H, "Naming cheat sheet prefixes and suffixes", "Two-column reference: left column lists the parent-chain prefixes meth- through dec- in two rows of small cards. Right column lists the functional-group suffixes in priority order: carboxylic acid (-oic acid) at the top, alkane (-ane) at the bottom.", body);
}

// ────────────────────────────────────────────────────────────────────────────
// Main
// ────────────────────────────────────────────────────────────────────────────

mkdirSync(ROOT, { recursive: true });

write("section-1-skeletal-structures/skeletal-shorthand-rules.svg", s1_shorthandRules());
write("section-1-skeletal-structures/alkane-series-zigzag.svg", s1_alkaneSeries());
write("section-1-skeletal-structures/branched-vs-straight-pentanes.svg", s1_branchedIsomers());
write("section-1-skeletal-structures/cyclohexane-shapes.svg", s1_cyclohexaneShapes());
write("section-1-skeletal-structures/numbering-the-chain.svg", s1_chainNumbering());

write("section-2-multiple-bonds-aromatics/alkene-double-bond.svg", s2_alkeneDouble());
write("section-2-multiple-bonds-aromatics/alkyne-triple-bond.svg", s2_alkyneTriple());
write("section-2-multiple-bonds-aromatics/cis-trans-isomerism.svg", s2_cisTrans());
write("section-2-multiple-bonds-aromatics/benzene-resonance.svg", s2_benzeneResonance());

write("section-3-functional-groups/functional-groups-reference.svg", s3_functionalGroupsReference());
write("section-3-functional-groups/alcohol-aldehyde-ketone-card.svg", s3_alcoholAldehydeKetone());
write("section-3-functional-groups/carboxylic-acid-and-ester-card.svg", s3_carboxylicAcidEster());
write("section-3-functional-groups/amine-and-amide-card.svg", s3_amineAmide());

write("section-4-iupac-naming/iupac-naming-flowchart.svg", s4_iupacFlowchart());
write("section-4-iupac-naming/name-build-walkthrough.svg", s4_nameBuildWalkthrough());
write("section-4-iupac-naming/prefix-and-suffix-cheat-sheet.svg", s4_prefixSuffixCheatSheet());

console.log("done — 16 SVGs");
