#!/usr/bin/env bun
/**
 * Render arrow-diagram SVGs from a declarative spec.
 *
 * Each diagram is two ovals (A, B) with dot-and-label elements inside,
 * connected by labelled arrows. Output is a static SVG suitable for
 * embedding in markdown, slides, or web pages.
 *
 * Run with no args to regenerate every diagram declared at the bottom
 * of this file.
 */

import { writeFileSync, mkdirSync } from "node:fs";
import { join, dirname } from "node:path";

type Spec = {
  outFile: string;
  title: string;
  caption: string;
  a: string[]; // labels in set A (top-to-bottom)
  b: string[]; // labels in set B
  arrows: Array<[string, string]>; // [from, to] using labels above
  highlight?: "danger" | "warn" | "ok";
  // when set, draws additional lines in red dashed style for the named pairs
  redArrows?: Array<[string, string]>;
};

const W = 400;
const H = 240;
const A_X = 110;
const B_X = 290;
const OVAL_R_X = 60;
const OVAL_R_Y = 90;
const TOP_Y = 50;
const SPACING = 50;

function dotYs(count: number): number[] {
  const total = (count - 1) * SPACING;
  const start = 110 - total / 2; // center on y = 110
  return Array.from({ length: count }, (_, i) => start + i * SPACING);
}

function arrowColor(highlight?: Spec["highlight"]) {
  if (highlight === "danger") return "#e53e3e";
  if (highlight === "warn") return "#dd6b20";
  return "#2b6cb0";
}

function svgFor(spec: Spec): string {
  const aYs = dotYs(spec.a.length);
  const bYs = dotYs(spec.b.length);

  const aPos: Record<string, { x: number; y: number }> = {};
  spec.a.forEach((label, i) => (aPos[label] = { x: A_X, y: aYs[i] }));
  const bPos: Record<string, { x: number; y: number }> = {};
  spec.b.forEach((label, i) => (bPos[label] = { x: B_X, y: bYs[i] }));

  const dotR = 5;
  const inset = 18; // arrow shrinks back from dot center for clean head

  const arrows = spec.arrows
    .map(([from, to]) => {
      const f = aPos[from];
      const t = bPos[to];
      if (!f || !t) throw new Error(`Unknown arrow ${from}→${to}`);
      const dx = t.x - f.x;
      const dy = t.y - f.y;
      const len = Math.hypot(dx, dy);
      const ux = dx / len;
      const uy = dy / len;
      const x1 = f.x + ux * (dotR + 2);
      const y1 = f.y + uy * (dotR + 2);
      const x2 = t.x - ux * (dotR + 2);
      const y2 = t.y - uy * (dotR + 2);
      return `<line x1="${x1.toFixed(1)}" y1="${y1.toFixed(1)}" x2="${x2.toFixed(1)}" y2="${y2.toFixed(1)}" stroke="${arrowColor(spec.highlight)}" stroke-width="2" marker-end="url(#arrow-blue)" />`;
    })
    .join("\n  ");

  const redArrows = (spec.redArrows ?? [])
    .map(([from, to]) => {
      const f = aPos[from];
      const t = bPos[to];
      const dx = t.x - f.x;
      const dy = t.y - f.y;
      const len = Math.hypot(dx, dy);
      const ux = dx / len;
      const uy = dy / len;
      const x1 = f.x + ux * (dotR + 2);
      const y1 = f.y + uy * (dotR + 2);
      const x2 = t.x - ux * (dotR + 2);
      const y2 = t.y - uy * (dotR + 2);
      return `<line x1="${x1.toFixed(1)}" y1="${y1.toFixed(1)}" x2="${x2.toFixed(1)}" y2="${y2.toFixed(1)}" stroke="#e53e3e" stroke-width="2" stroke-dasharray="5 4" marker-end="url(#arrow-red)" />`;
    })
    .join("\n  ");

  const aDots = spec.a
    .map((label, i) => {
      const y = aYs[i];
      return `<circle cx="${A_X}" cy="${y}" r="${dotR}" fill="#1a202c"/><text x="${A_X - 18}" y="${y + 4}" font="14px system-ui" font-size="14" fill="#1a202c" text-anchor="end">${label}</text>`;
    })
    .join("\n  ");

  const bDots = spec.b
    .map((label, i) => {
      const y = bYs[i];
      return `<circle cx="${B_X}" cy="${y}" r="${dotR}" fill="#1a202c"/><text x="${B_X + 18}" y="${y + 4}" font="14px system-ui" font-size="14" fill="#1a202c">${label}</text>`;
    })
    .join("\n  ");

  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${W} ${H}" width="${W}" height="${H}" role="img" aria-label="${spec.title}">
  <title>${spec.title}</title>
  <desc>${spec.caption}</desc>
  <defs>
    <marker id="arrow-blue" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="${arrowColor(spec.highlight)}"/>
    </marker>
    <marker id="arrow-red" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="#e53e3e"/>
    </marker>
  </defs>
  <text x="${W / 2}" y="22" font="bold 14px system-ui" font-size="14" font-weight="700" fill="#1a202c" text-anchor="middle">${spec.title}</text>

  <!-- Set boundaries -->
  <ellipse cx="${A_X}" cy="120" rx="${OVAL_R_X}" ry="${OVAL_R_Y}" fill="#ebf4ff" stroke="#2b6cb0" stroke-width="1.5"/>
  <ellipse cx="${B_X}" cy="120" rx="${OVAL_R_X}" ry="${OVAL_R_Y}" fill="#fffaf0" stroke="#dd6b20" stroke-width="1.5"/>
  <text x="${A_X}" y="${TOP_Y - 10}" font="bold 16px system-ui" font-size="16" font-weight="700" fill="#2b6cb0" text-anchor="middle">A</text>
  <text x="${B_X}" y="${TOP_Y - 10}" font="bold 16px system-ui" font-size="16" font-weight="700" fill="#dd6b20" text-anchor="middle">B</text>

  <!-- Elements -->
  ${aDots}
  ${bDots}

  <!-- Arrows -->
  ${arrows}
  ${redArrows}

  <!-- Caption -->
  <text x="${W / 2}" y="${H - 12}" font="13px system-ui" font-size="13" fill="#4a5568" text-anchor="middle">${spec.caption}</text>
</svg>
`;
}

const specs: Spec[] = [
  {
    outFile: "arrow-diagrams/R1-function.svg",
    title: "R₁: a function",
    caption: "Each element of A maps to exactly one in B.",
    a: ["1", "2", "3"],
    b: ["p", "q", "r"],
    arrows: [["1", "p"], ["2", "q"], ["3", "r"]],
  },
  {
    outFile: "arrow-diagrams/R2-not-function.svg",
    title: "R₂: not a function",
    caption: "Element 1 maps to two outputs (p and q) — uniqueness violated.",
    a: ["1", "2", "3"],
    b: ["p", "q", "r"],
    arrows: [["1", "p"], ["2", "r"]],
    redArrows: [["1", "q"]],
  },
  {
    outFile: "arrow-diagrams/R3-function-not-injective.svg",
    title: "R₃: a function, not injective",
    caption: "Distinct inputs (1 and 2) share the same output (p) — allowed.",
    a: ["1", "2", "3"],
    b: ["p", "q", "r"],
    arrows: [["1", "p"], ["2", "p"], ["3", "q"]],
  },
  {
    outFile: "arrow-diagrams/R4-not-function.svg",
    title: "R₄: not a function",
    caption: "Element 3 has no image in B — totality violated.",
    a: ["1", "2", "3"],
    b: ["p", "q", "r"],
    arrows: [["1", "p"], ["2", "q"]],
  },
  {
    outFile: "arrow-diagrams/injective-only.svg",
    title: "Injective only",
    caption: "Distinct inputs go to distinct outputs; element s in B is unreached.",
    a: ["1", "2", "3"],
    b: ["p", "q", "r", "s"],
    arrows: [["1", "p"], ["2", "q"], ["3", "r"]],
  },
  {
    outFile: "arrow-diagrams/surjective-only.svg",
    title: "Surjective only",
    caption: "Every element of B is hit; 1 and 2 collide on p.",
    a: ["1", "2", "3", "4"],
    b: ["p", "q", "r"],
    arrows: [["1", "p"], ["2", "p"], ["3", "q"], ["4", "r"]],
  },
  {
    outFile: "arrow-diagrams/bijective.svg",
    title: "Bijective",
    caption: "One-to-one correspondence — only bijections have inverses.",
    a: ["1", "2", "3"],
    b: ["p", "q", "r"],
    arrows: [["1", "p"], ["2", "q"], ["3", "r"]],
    highlight: "ok",
  },
];

const root = join(import.meta.dir, "..", "sample_content", "g11-science", "G11-MATH-001_Sets_and_Functions", "Option2_Catalogue");

for (const spec of specs) {
  const path = join(root, spec.outFile);
  mkdirSync(dirname(path), { recursive: true });
  writeFileSync(path, svgFor(spec));
  console.log("wrote", spec.outFile);
}
