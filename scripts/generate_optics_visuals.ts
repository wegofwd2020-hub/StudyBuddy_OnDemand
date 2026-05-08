#!/usr/bin/env bun
/**
 * Generate the Option-2 SVG catalogue for G12-PHYS-005 Optics (issue #336).
 *
 * Run from repo root:
 *   bun scripts/generate_optics_visuals.ts
 *
 * Output: sample_content/g12-science/G12-PHYS-005_Optics/Option2_Catalogue/section-N/*.svg
 *
 * Last Wave-2 unit. Ships the canonical ray-diagram primitives (reflection
 * angles, lens/mirror image formation, refraction at interfaces) which will
 * reuse retroactively into G10-SCI-002 and G8-SCI-002.
 */

import { writeFileSync, mkdirSync } from "node:fs";
import { join, dirname } from "node:path";

const ROOT = join(
  import.meta.dir,
  "..",
  "sample_content",
  "g12-science",
  "G12-PHYS-005_Optics",
  "Option2_Catalogue",
);

// Style tokens + optics palette + primitives lifted to pipeline/visual_templates.
import {
  INK,
  MUTED,
  ACCENT,
  ACCENT_2,
  ACCENT_3,
  POSITIVE,
  NEGATIVE,
  GRID,
  BG,
  HIGHLIGHT,
} from "../pipeline/visual_templates/shared.ts";
import {
  RAY,
  NORMAL,
  SURFACE,
  VIRTUAL_RAY,
  REFRACTED,
  rayArrow,
  normalLine,
  angleArc,
} from "../pipeline/visual_templates/optics.ts";

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
// SECTION 1 — Reflection (3 SVGs)
// ────────────────────────────────────────────────────────────────────────────

function s1_lawOfReflection() {
  const W = 600, H = 360;
  const surfaceY = 250;
  const px = 300, py = surfaceY; // point of incidence
  // 35° from normal on each side
  const ang = Math.PI / 4;
  const len = 160;
  const ix = px - len * Math.sin(ang), iy = py - len * Math.cos(ang);
  const rx = px + len * Math.sin(ang), ry = py - len * Math.cos(ang);

  let body = `
  <text x="${W / 2}" y="32" font="bold 18px system-ui" font-size="18" font-weight="700" fill="${INK}" text-anchor="middle">Law of Reflection — angle of incidence = angle of reflection</text>
  <text x="${W / 2}" y="54" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">Both angles measured from the normal — the line perpendicular to the surface.</text>

  <!-- Mirror surface with hatched back -->
  <line x1="60" y1="${surfaceY}" x2="540" y2="${surfaceY}" stroke="${SURFACE}" stroke-width="3" />
`;
  for (let i = 0; i < 24; i++) {
    const x = 60 + i * 20;
    body += `<line x1="${x}" y1="${surfaceY}" x2="${x + 12}" y2="${surfaceY + 14}" stroke="${MUTED}" stroke-width="1.2" />`;
  }
  // Normal
  body += normalLine(px, surfaceY - 180, px, surfaceY + 20, NORMAL);
  body += `<text x="${px - 12}" y="${surfaceY - 180}" font="bold 12px system-ui" font-size="12" font-weight="700" fill="${NORMAL}" text-anchor="end">normal</text>`;
  // Incident ray (arrow toward P)
  body += rayArrow(ix, iy, px, py, RAY, 3);
  body += `<text x="${ix - 8}" y="${iy - 6}" font="bold 13px system-ui" font-size="13" font-weight="700" fill="${RAY}" text-anchor="end">incident ray</text>`;
  // Reflected ray (arrow away from P)
  body += rayArrow(px, py, rx, ry, POSITIVE, 3);
  body += `<text x="${rx + 8}" y="${ry - 6}" font="bold 13px system-ui" font-size="13" font-weight="700" fill="${POSITIVE}">reflected ray</text>`;
  // Angle arcs
  body += angleArc(px, py, 50, -Math.PI / 2 - 0.01, -Math.PI / 2 - ang, RAY);
  body += `<text x="${px - 32}" y="${py - 60}" font="bold 12px system-ui" font-size="12" font-weight="700" fill="${RAY}" text-anchor="middle">θᵢ</text>`;
  body += angleArc(px, py, 50, -Math.PI / 2 + ang, -Math.PI / 2 + 0.01, POSITIVE);
  body += `<text x="${px + 32}" y="${py - 60}" font="bold 12px system-ui" font-size="12" font-weight="700" fill="${POSITIVE}" text-anchor="middle">θᵣ</text>`;
  body += `<text x="${px}" y="${surfaceY + 50}" font="bold 14px system-ui" font-size="14" font-weight="700" fill="${INK}" text-anchor="middle">θᵢ = θᵣ</text>`;
  body += `<text x="${W / 2}" y="${H - 12}" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">The incident ray, the normal, and the reflected ray all lie in the same plane.</text>`;
  return svgWrap(W, H, "Law of reflection diagram", "A flat mirror surface (hatched) with a vertical dashed normal line at the point of incidence. A red incident ray comes in from the upper-left at 45° to the normal; a green reflected ray leaves to the upper-right at the same angle. Two angle arcs labelled θᵢ and θᵣ identify the equal angles. Caption: θᵢ = θᵣ.", body);
}

function s1_concaveMirror() {
  const W = 600, H = 320;
  const axisY = 200;
  // Concave mirror as part of a circle bulging right
  const cx = 480, R = 200; // centre of curvature off-image right
  // Mirror arc: spans from (380, 100) to (380, 300) (an arc bulging right)
  let body = `
  <text x="${W / 2}" y="32" font="bold 18px system-ui" font-size="18" font-weight="700" fill="${INK}" text-anchor="middle">Concave Mirror — Object Beyond Centre of Curvature</text>

  <!-- Principal axis -->
  <line x1="60" y1="${axisY}" x2="540" y2="${axisY}" stroke="${MUTED}" stroke-width="1.2" stroke-dasharray="4 4" />

  <!-- Concave mirror arc (bulges toward the object) -->
  <path d="M 380 100 A 200 200 0 0 0 380 300" fill="none" stroke="${SURFACE}" stroke-width="3" />
  <!-- Hatching behind mirror -->
`;
  for (let i = 0; i < 20; i++) {
    const t = i / 19;
    const ay = 100 + t * 200;
    body += `<line x1="${380 + 6 * Math.sin(((ay - axisY) / 100) * Math.PI / 2)}" y1="${ay}" x2="${396}" y2="${ay - 8}" stroke="${MUTED}" stroke-width="1" />`;
  }
  // Focal point F and centre of curvature C
  const F = 290, C = 200;
  body += `<circle cx="${F}" cy="${axisY}" r="5" fill="${ACCENT}" />`;
  body += `<text x="${F}" y="${axisY + 22}" font="bold 12px system-ui" font-size="12" font-weight="700" fill="${ACCENT}" text-anchor="middle">F</text>`;
  body += `<circle cx="${C}" cy="${axisY}" r="5" fill="${ACCENT_2}" />`;
  body += `<text x="${C}" y="${axisY + 22}" font="bold 12px system-ui" font-size="12" font-weight="700" fill="${ACCENT_2}" text-anchor="middle">C</text>`;
  // Object — vertical arrow at x=120 pointing up
  const objX = 120, objH = 60;
  body += `<line x1="${objX}" y1="${axisY}" x2="${objX}" y2="${axisY - objH}" stroke="${POSITIVE}" stroke-width="3" />`;
  body += `<polygon points="${objX - 6},${axisY - objH + 8} ${objX + 6},${axisY - objH + 8} ${objX},${axisY - objH}" fill="${POSITIVE}" />`;
  body += `<text x="${objX}" y="${axisY - objH - 8}" font="bold 12px system-ui" font-size="12" font-weight="700" fill="${POSITIVE}" text-anchor="middle">object</text>`;
  // Image: real, inverted, smaller, between F and C
  const imgX = 240, imgH = 35;
  body += `<line x1="${imgX}" y1="${axisY}" x2="${imgX}" y2="${axisY + imgH}" stroke="${NEGATIVE}" stroke-width="3" />`;
  body += `<polygon points="${imgX - 6},${axisY + imgH - 8} ${imgX + 6},${axisY + imgH - 8} ${imgX},${axisY + imgH}" fill="${NEGATIVE}" />`;
  body += `<text x="${imgX}" y="${axisY + imgH + 18}" font="bold 12px system-ui" font-size="12" font-weight="700" fill="${NEGATIVE}" text-anchor="middle">image (real, inverted, smaller)</text>`;
  // Three principal rays
  // Ray 1: parallel → reflects through F
  const objTopY = axisY - objH;
  body += rayArrow(objX, objTopY, 380, objTopY, RAY, 2);
  body += rayArrow(380, objTopY, F, axisY, RAY, 2);
  body += rayArrow(F, axisY, imgX, axisY + imgH, RAY, 2);
  // Ray 2: through F → reflects parallel
  // Ray 3: through C → reflects back on itself (skip for clarity)
  body += `<text x="${W / 2}" y="${H - 12}" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">When object is beyond C: image is real, inverted, smaller — between F and C.</text>`;
  return svgWrap(W, H, "Concave mirror ray diagram object beyond C", "A concave mirror arc on the right; a horizontal principal axis with focal point F and centre of curvature C marked. A green upright object arrow stands at the far left beyond C; red light rays from the top of the object reflect off the mirror and converge to form a smaller inverted red image arrow between F and C.", body);
}

function s1_convexMirror() {
  const W = 600, H = 320;
  const axisY = 200;
  // Convex mirror bulges left (toward object on left)
  let body = `
  <text x="${W / 2}" y="32" font="bold 18px system-ui" font-size="18" font-weight="700" fill="${INK}" text-anchor="middle">Convex Mirror — Always a Virtual, Smaller Image</text>

  <line x1="60" y1="${axisY}" x2="540" y2="${axisY}" stroke="${MUTED}" stroke-width="1.2" stroke-dasharray="4 4" />

  <!-- Convex mirror arc (bulges left toward viewer) -->
  <path d="M 400 100 A 200 200 0 0 1 400 300" fill="none" stroke="${SURFACE}" stroke-width="3" />
  <!-- F and C are on the right (behind the mirror, dashed) -->
`;
  const F = 480, C = 540;
  body += `<circle cx="${F}" cy="${axisY}" r="5" fill="${ACCENT}" />`;
  body += `<text x="${F}" y="${axisY + 22}" font="bold 12px system-ui" font-size="12" font-weight="700" fill="${ACCENT}" text-anchor="middle">F</text>`;
  body += `<text x="${F}" y="${axisY + 38}" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">(virtual)</text>`;
  // Object
  const objX = 120, objH = 60;
  body += `<line x1="${objX}" y1="${axisY}" x2="${objX}" y2="${axisY - objH}" stroke="${POSITIVE}" stroke-width="3" />`;
  body += `<polygon points="${objX - 6},${axisY - objH + 8} ${objX + 6},${axisY - objH + 8} ${objX},${axisY - objH}" fill="${POSITIVE}" />`;
  body += `<text x="${objX}" y="${axisY - objH - 8}" font="bold 12px system-ui" font-size="12" font-weight="700" fill="${POSITIVE}" text-anchor="middle">object</text>`;
  // Virtual image: behind mirror, upright, smaller
  const imgX = 450, imgH = 25;
  body += `<line x1="${imgX}" y1="${axisY}" x2="${imgX}" y2="${axisY - imgH}" stroke="${NEGATIVE}" stroke-width="2.5" stroke-dasharray="4 3" />`;
  body += `<polygon points="${imgX - 5},${axisY - imgH + 6} ${imgX + 5},${axisY - imgH + 6} ${imgX},${axisY - imgH}" fill="${NEGATIVE}" />`;
  body += `<text x="${imgX}" y="${axisY - imgH - 6}" font="bold 11px system-ui" font-size="11" font-weight="700" fill="${NEGATIVE}" text-anchor="middle">virtual image</text>`;
  body += `<text x="${imgX}" y="${axisY + 22}" font="9px system-ui" font-size="9" fill="${NEGATIVE}" text-anchor="middle">(upright, smaller)</text>`;
  // Rays
  const objTopY = axisY - objH;
  // Ray 1: parallel ray hits mirror, reflects appearing-from-F (diverges)
  body += rayArrow(objX, objTopY, 400, objTopY, RAY, 2);
  body += `<line x1="400" y1="${objTopY}" x2="160" y2="${objTopY - 70}" stroke="${RAY}" stroke-width="2" stroke-dasharray="4 3" />`;
  body += `<line x1="400" y1="${objTopY}" x2="${F}" y2="${axisY}" stroke="${RAY}" stroke-width="2" stroke-dasharray="3 3" opacity="0.5" />`;
  // Ray 2: aimed at F, reflects parallel
  body += `<line x1="${objX}" y1="${objTopY}" x2="400" y2="${axisY - 30}" stroke="${RAY}" stroke-width="2" />`;
  body += `<line x1="400" y1="${axisY - 30}" x2="160" y2="${axisY - 30}" stroke="${RAY}" stroke-width="2" />`;

  body += `<text x="${W / 2}" y="${H - 12}" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">Convex mirror always: virtual · upright · smaller. F and C are behind the reflective surface.</text>`;
  return svgWrap(W, H, "Convex mirror ray diagram", "A convex mirror arc bulging toward the object on the left. A virtual focal point F and centre of curvature lie behind the mirror (dashed). Object arrow at the far left; red rays reflect from the mirror diverging away. The diverging rays appear to come from a small upright virtual image just behind the mirror.", body);
}

// ────────────────────────────────────────────────────────────────────────────
// SECTION 2 — Refraction (3 SVGs)
// ────────────────────────────────────────────────────────────────────────────

function s2_snellsLaw() {
  const W = 600, H = 360;
  const interfaceY = 200;
  const px = 300;
  // Incident in medium 1 (top, n=1) at 45° from normal; refracted in medium 2 (bottom, n=1.5) at smaller angle.
  const ang1 = Math.PI / 4;
  const ang2 = Math.asin(Math.sin(ang1) / 1.5);
  const len1 = 140, len2 = 140;
  const ix = px - len1 * Math.sin(ang1), iy = interfaceY - len1 * Math.cos(ang1);
  const rx = px + len2 * Math.sin(ang2), ry = interfaceY + len2 * Math.cos(ang2);

  let body = `
  <text x="${W / 2}" y="32" font="bold 18px system-ui" font-size="18" font-weight="700" fill="${INK}" text-anchor="middle">Snell's Law — n₁ sin θ₁ = n₂ sin θ₂</text>
  <text x="${W / 2}" y="54" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">Light bends toward the normal when entering a denser medium (higher n).</text>

  <!-- Two media -->
  <rect x="60" y="80" width="480" height="120" fill="#dbeafe" opacity="0.6" />
  <rect x="60" y="200" width="480" height="120" fill="#bfdbfe" />
  <line x1="60" y1="${interfaceY}" x2="540" y2="${interfaceY}" stroke="${INK}" stroke-width="1.5" />

  <!-- Medium labels -->
  <text x="80" y="100" font="bold 13px system-ui" font-size="13" font-weight="700" fill="${ACCENT}">medium 1 — air, n₁ = 1.00</text>
  <text x="80" y="220" font="bold 13px system-ui" font-size="13" font-weight="700" fill="${REFRACTED}">medium 2 — glass, n₂ = 1.50</text>

  <!-- Normal -->
  ${normalLine(px, 80, px, 320)}
  <text x="${px - 8}" y="${88}" font="bold 11px system-ui" font-size="11" font-weight="700" fill="${MUTED}" text-anchor="end">normal</text>

  <!-- Incident ray -->
  ${rayArrow(ix, iy, px, interfaceY, RAY, 3)}
  <text x="${ix - 8}" y="${iy - 6}" font="bold 13px system-ui" font-size="13" font-weight="700" fill="${RAY}" text-anchor="end">incident ray</text>

  <!-- Refracted ray -->
  ${rayArrow(px, interfaceY, rx, ry, REFRACTED, 3)}
  <text x="${rx + 8}" y="${ry - 6}" font="bold 13px system-ui" font-size="13" font-weight="700" fill="${REFRACTED}">refracted ray</text>

  <!-- Angle arcs -->
  ${angleArc(px, interfaceY, 40, -Math.PI / 2, -Math.PI / 2 - ang1, RAY)}
  <text x="${px - 18}" y="${interfaceY - 50}" font="bold 12px system-ui" font-size="12" font-weight="700" fill="${RAY}" text-anchor="middle">θ₁</text>
  ${angleArc(px, interfaceY, 40, Math.PI / 2 - ang2, Math.PI / 2, REFRACTED)}
  <text x="${px + 14}" y="${interfaceY + 56}" font="bold 12px system-ui" font-size="12" font-weight="700" fill="${REFRACTED}" text-anchor="middle">θ₂</text>

  <!-- Worked example -->
  <rect x="350" y="220" width="180" height="80" rx="8" fill="${HIGHLIGHT}" stroke="${MUTED}" stroke-width="1.5" />
  <text x="440" y="244" font="bold 12px system-ui" font-size="12" font-weight="700" fill="${INK}" text-anchor="middle">θ₁ = 45° → θ₂ ≈ 28°</text>
  <text x="440" y="262" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">sin(45°)/sin(28°) ≈ 1.5</text>
  <text x="440" y="282" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">= n₂/n₁ ✓</text>
`;
  return svgWrap(W, H, "Snells law refraction at an interface", "Two horizontally-stacked media (light blue air on top, deeper blue glass on bottom) separated by a horizontal interface. A red incident ray approaches the boundary at θ₁ = 45° from the dashed normal; the purple refracted ray bends toward the normal at θ₂ ≈ 28° in the denser medium. A boxed worked example shows the ratio sin θ₁ / sin θ₂ = n₂ / n₁ = 1.5.", body);
}

function s2_totalInternalReflection() {
  const W = 600, H = 380;
  const interfaceY = 220;
  const px = 300;
  let body = `
  <text x="${W / 2}" y="32" font="bold 18px system-ui" font-size="18" font-weight="700" fill="${INK}" text-anchor="middle">Total Internal Reflection — Above the Critical Angle</text>
  <text x="${W / 2}" y="54" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">When light goes from dense → less dense, it bends away from the normal. Past θc, all of it reflects.</text>

  <rect x="60" y="80" width="480" height="140" fill="#bfdbfe" />
  <rect x="60" y="220" width="480" height="120" fill="#dbeafe" opacity="0.6" />
  <line x1="60" y1="${interfaceY}" x2="540" y2="${interfaceY}" stroke="${INK}" stroke-width="1.5" />

  <text x="80" y="100" font="bold 13px system-ui" font-size="13" font-weight="700" fill="${REFRACTED}">glass — n₁ = 1.5</text>
  <text x="80" y="240" font="bold 13px system-ui" font-size="13" font-weight="700" fill="${ACCENT}">air — n₂ = 1.0</text>

  <!-- Normal -->
  ${normalLine(px, 80, px, 340)}
`;
  // Three rays at increasing angles: small (refracts out), exactly critical (skims along surface), super-critical (TIR back into glass)
  // Ray A — small angle, refracts out
  const angA = Math.PI / 9; // 20°
  const ax = px - 110 * Math.sin(angA), ay = interfaceY + 110 * Math.cos(angA);
  const angA2 = Math.asin(Math.sin(angA) * 1.5);
  const aRx = px + 110 * Math.sin(angA2), aRy = interfaceY - 110 * Math.cos(angA2);
  body += rayArrow(ax, ay, px, interfaceY, RAY, 2.5);
  body += rayArrow(px, interfaceY, aRx, aRy, REFRACTED, 2.5);
  body += `<text x="${ax - 4}" y="${ay + 14}" font="bold 11px system-ui" font-size="11" font-weight="700" fill="${RAY}" text-anchor="end">A · θ < θc</text>`;

  // Ray B — critical angle (~41.8° in glass to air)
  const angC = Math.asin(1 / 1.5);
  const bx = px - 110 * Math.sin(angC), by = interfaceY + 110 * Math.cos(angC);
  body += rayArrow(bx, by, px, interfaceY, RAY, 2.5);
  body += `<line x1="${px}" y1="${interfaceY}" x2="${px + 220}" y2="${interfaceY - 4}" stroke="${REFRACTED}" stroke-width="2.5" stroke-dasharray="4 3" />`;
  body += `<text x="${bx - 4}" y="${by + 14}" font="bold 11px system-ui" font-size="11" font-weight="700" fill="${RAY}" text-anchor="end">B · θ = θc</text>`;
  body += `<text x="${px + 230}" y="${interfaceY - 8}" font="bold 11px system-ui" font-size="11" font-weight="700" fill="${REFRACTED}">grazes along interface</text>`;

  // Ray C — beyond critical, TIR
  const angD = Math.PI / 3; // 60°
  const cx = px - 110 * Math.sin(angD), cy = interfaceY + 110 * Math.cos(angD);
  body += rayArrow(cx, cy, px, interfaceY, RAY, 2.5);
  // Reflected back into medium 1 (down into glass) at the same angle
  const cRx = px + 110 * Math.sin(angD), cRy = interfaceY + 110 * Math.cos(angD);
  body += rayArrow(px, interfaceY, cRx, cRy, POSITIVE, 3);
  body += `<text x="${cx - 4}" y="${cy + 14}" font="bold 11px system-ui" font-size="11" font-weight="700" fill="${RAY}" text-anchor="end">C · θ > θc</text>`;
  body += `<text x="${cRx + 8}" y="${cRy - 6}" font="bold 11px system-ui" font-size="11" font-weight="700" fill="${POSITIVE}">total internal reflection</text>`;

  body += `
  <text x="${W / 2}" y="${H - 30}" font="bold 12px system-ui" font-size="12" font-weight="700" fill="${POSITIVE}" text-anchor="middle">θc = arcsin(n₂/n₁) — for glass→air, θc ≈ 41.8°</text>
  <text x="${W / 2}" y="${H - 12}" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">This is how fibre optics work: light bounces along inside the fibre because every wall hit exceeds θc.</text>
`;
  return svgWrap(W, H, "Total internal reflection at glass-air interface", "Glass on top, air below. Three incident rays from the glass side hit the interface at increasing angles: ray A (small angle) refracts out into the air. Ray B at the critical angle θc ≈ 41.8° grazes along the interface. Ray C beyond the critical angle reflects entirely back into the glass — total internal reflection.", body);
}

function s2_prismDispersion() {
  const W = 600, H = 320;
  // Equilateral prism at center
  const cx = 280, cy = 180;
  const side = 140;
  const apex = { x: cx, y: cy - side * Math.sqrt(3) / 2 };
  const left = { x: cx - side / 2, y: cy + side * Math.sqrt(3) / 6 };
  const right = { x: cx + side / 2, y: cy + side * Math.sqrt(3) / 6 };

  let body = `
  <text x="${W / 2}" y="32" font="bold 18px system-ui" font-size="18" font-weight="700" fill="${INK}" text-anchor="middle">Prism Dispersion — White Light Splits by Wavelength</text>

  <!-- Prism triangle -->
  <polygon points="${apex.x},${apex.y} ${left.x},${left.y} ${right.x},${right.y}" fill="#dbeafe" stroke="${INK}" stroke-width="2" />

  <!-- Incoming white ray hitting left face -->
  <line x1="60" y1="160" x2="${left.x + 20}" y2="${cy + 4}" stroke="${INK}" stroke-width="3" />
  <text x="60" y="148" font="bold 12px system-ui" font-size="12" font-weight="700" fill="${INK}">white light</text>

  <!-- Outgoing dispersed rays from right face — fan of colours -->
`;
  const colors = [
    { name: "violet", color: "#7c3aed", spread: -0.18 },
    { name: "blue", color: "#2563eb", spread: -0.10 },
    { name: "green", color: "#16a34a", spread: -0.04 },
    { name: "yellow", color: "#facc15", spread: 0.04 },
    { name: "orange", color: "#ea580c", spread: 0.10 },
    { name: "red", color: "#dc2626", spread: 0.18 },
  ];
  // Exit point on right face — somewhere along the right edge
  const exitX = (right.x + apex.x) / 2 + 5;
  const exitY = (right.y + apex.y) / 2;
  for (const c of colors) {
    const ang = 0.4 + c.spread; // slight angle below horizontal
    const ex = exitX + 200 * Math.cos(ang);
    const ey = exitY + 200 * Math.sin(ang);
    body += `<line x1="${exitX.toFixed(1)}" y1="${exitY.toFixed(1)}" x2="${ex.toFixed(1)}" y2="${ey.toFixed(1)}" stroke="${c.color}" stroke-width="3" stroke-linecap="round" />`;
    body += `<text x="${ex + 8}" y="${ey + 4}" font="bold 11px system-ui" font-size="11" font-weight="700" fill="${c.color}">${c.name}</text>`;
  }
  body += `
  <text x="${W / 2}" y="${H - 30}" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">Each colour bends by a slightly different angle because n depends on wavelength.</text>
  <text x="${W / 2}" y="${H - 14}" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">Violet bends most (highest n), red least (lowest n) — the rainbow comes out fanned.</text>
`;
  return svgWrap(W, H, "Prism dispersion of white light", "An equilateral prism in the centre with a black white-light ray entering its left face. Six coloured rays emerge from the right face fanned in order violet, blue, green, yellow, orange, red — violet bent most strongly downward, red least.", body);
}

// ────────────────────────────────────────────────────────────────────────────
// SECTION 3 — Lenses (3 SVGs)
// ────────────────────────────────────────────────────────────────────────────

function s3_convexLens() {
  const W = 600, H = 320;
  const axisY = 180;
  const lensX = 300;
  let body = `
  <text x="${W / 2}" y="32" font="bold 18px system-ui" font-size="18" font-weight="700" fill="${INK}" text-anchor="middle">Convex (Converging) Lens — Image Formation</text>

  <line x1="60" y1="${axisY}" x2="540" y2="${axisY}" stroke="${MUTED}" stroke-width="1.2" stroke-dasharray="4 4" />

  <!-- Lens (vertical lens-shape) -->
  <ellipse cx="${lensX}" cy="${axisY}" rx="14" ry="100" fill="#bfdbfe" stroke="${INK}" stroke-width="2" />

  <!-- F1 and F2 -->
  <circle cx="${lensX - 80}" cy="${axisY}" r="4" fill="${ACCENT}" />
  <text x="${lensX - 80}" y="${axisY + 18}" font="bold 12px system-ui" font-size="12" font-weight="700" fill="${ACCENT}" text-anchor="middle">F</text>
  <circle cx="${lensX + 80}" cy="${axisY}" r="4" fill="${ACCENT}" />
  <text x="${lensX + 80}" y="${axisY + 18}" font="bold 12px system-ui" font-size="12" font-weight="700" fill="${ACCENT}" text-anchor="middle">F'</text>

  <!-- Object (beyond 2F on the left) -->
`;
  const objX = 100, objH = 60;
  body += `<line x1="${objX}" y1="${axisY}" x2="${objX}" y2="${axisY - objH}" stroke="${POSITIVE}" stroke-width="3" />`;
  body += `<polygon points="${objX - 6},${axisY - objH + 8} ${objX + 6},${axisY - objH + 8} ${objX},${axisY - objH}" fill="${POSITIVE}" />`;
  body += `<text x="${objX}" y="${axisY - objH - 8}" font="bold 12px system-ui" font-size="12" font-weight="700" fill="${POSITIVE}" text-anchor="middle">object</text>`;
  // Image (real, inverted, between F' and 2F'). Place at x=440, smaller, inverted.
  const imgX = 440, imgH = 38;
  body += `<line x1="${imgX}" y1="${axisY}" x2="${imgX}" y2="${axisY + imgH}" stroke="${NEGATIVE}" stroke-width="3" />`;
  body += `<polygon points="${imgX - 6},${axisY + imgH - 8} ${imgX + 6},${axisY + imgH - 8} ${imgX},${axisY + imgH}" fill="${NEGATIVE}" />`;
  body += `<text x="${imgX}" y="${axisY + imgH + 18}" font="bold 11px system-ui" font-size="11" font-weight="700" fill="${NEGATIVE}" text-anchor="middle">image (real, inverted)</text>`;
  // Three principal rays from object top
  const objTopY = axisY - objH;
  // Ray 1: parallel to axis → through F' on the right
  body += rayArrow(objX, objTopY, lensX, objTopY, RAY, 2);
  body += rayArrow(lensX, objTopY, imgX, axisY + imgH, RAY, 2);
  // Ray 2: through F on the left → emerges parallel
  body += rayArrow(objX, objTopY, lensX - 80, axisY, RAY, 2);
  body += `<line x1="${lensX - 80}" y1="${axisY}" x2="${lensX}" y2="${axisY - 24}" stroke="${RAY}" stroke-width="2" />`;
  body += `<line x1="${lensX}" y1="${axisY - 24}" x2="${imgX}" y2="${axisY - 24}" stroke="${RAY}" stroke-width="2" stroke-dasharray="3 4" />`;
  // Ray 3: through center of lens — undeviated
  body += `<line x1="${objX}" y1="${objTopY}" x2="${imgX}" y2="${axisY + imgH}" stroke="${RAY}" stroke-width="1.5" stroke-dasharray="6 3" opacity="0.6" />`;

  body += `<text x="${W / 2}" y="${H - 12}" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">Object beyond 2F → image between F' and 2F': real · inverted · smaller.</text>`;
  return svgWrap(W, H, "Convex lens image formation", "A horizontal optical bench with a vertical converging-lens shape in the centre. Focal points F and F' on either side of the lens. A green object arrow stands on the left beyond 2F; three principal red rays from the top of the object pass through the lens and converge to form a smaller inverted red image arrow on the right between F' and 2F'.", body);
}

function s3_concaveLens() {
  const W = 600, H = 320;
  const axisY = 180;
  const lensX = 300;
  let body = `
  <text x="${W / 2}" y="32" font="bold 18px system-ui" font-size="18" font-weight="700" fill="${INK}" text-anchor="middle">Concave (Diverging) Lens — Always Virtual, Smaller</text>

  <line x1="60" y1="${axisY}" x2="540" y2="${axisY}" stroke="${MUTED}" stroke-width="1.2" stroke-dasharray="4 4" />

  <!-- Concave lens shape (biconcave) — two curves meeting at thin centre -->
  <path d="M ${lensX - 14} ${axisY - 100} Q ${lensX + 6} ${axisY}, ${lensX - 14} ${axisY + 100}
           L ${lensX + 14} ${axisY + 100} Q ${lensX - 6} ${axisY}, ${lensX + 14} ${axisY - 100} Z"
        fill="#bfdbfe" stroke="${INK}" stroke-width="2" />

  <!-- Focal points (virtual) -->
  <circle cx="${lensX - 70}" cy="${axisY}" r="4" fill="${ACCENT}" />
  <text x="${lensX - 70}" y="${axisY + 18}" font="bold 12px system-ui" font-size="12" font-weight="700" fill="${ACCENT}" text-anchor="middle">F</text>
  <circle cx="${lensX + 70}" cy="${axisY}" r="4" fill="${ACCENT}" />
  <text x="${lensX + 70}" y="${axisY + 18}" font="bold 12px system-ui" font-size="12" font-weight="700" fill="${ACCENT}" text-anchor="middle">F'</text>
`;
  // Object (anywhere — image is always virtual)
  const objX = 130, objH = 60;
  body += `<line x1="${objX}" y1="${axisY}" x2="${objX}" y2="${axisY - objH}" stroke="${POSITIVE}" stroke-width="3" />`;
  body += `<polygon points="${objX - 6},${axisY - objH + 8} ${objX + 6},${axisY - objH + 8} ${objX},${axisY - objH}" fill="${POSITIVE}" />`;
  body += `<text x="${objX}" y="${axisY - objH - 8}" font="bold 12px system-ui" font-size="12" font-weight="700" fill="${POSITIVE}" text-anchor="middle">object</text>`;
  // Virtual image — between F and the lens, upright, smaller
  const imgX = 240, imgH = 30;
  body += `<line x1="${imgX}" y1="${axisY}" x2="${imgX}" y2="${axisY - imgH}" stroke="${NEGATIVE}" stroke-width="2.5" stroke-dasharray="4 3" />`;
  body += `<polygon points="${imgX - 5},${axisY - imgH + 6} ${imgX + 5},${axisY - imgH + 6} ${imgX},${axisY - imgH}" fill="${NEGATIVE}" />`;
  body += `<text x="${imgX}" y="${axisY - imgH - 6}" font="bold 11px system-ui" font-size="11" font-weight="700" fill="${NEGATIVE}" text-anchor="middle">virtual image</text>`;
  // Ray 1: parallel from object → diverges (refracts outward); extension back goes through F (left)
  const objTopY = axisY - objH;
  body += rayArrow(objX, objTopY, lensX, objTopY, RAY, 2);
  body += `<line x1="${lensX}" y1="${objTopY}" x2="490" y2="${objTopY - 30}" stroke="${RAY}" stroke-width="2" />`;
  body += `<line x1="${lensX}" y1="${objTopY}" x2="${lensX - 70}" y2="${axisY}" stroke="${RAY}" stroke-width="1.5" stroke-dasharray="4 4" />`;
  // Ray 2: through center, undeviated
  body += `<line x1="${objX}" y1="${objTopY}" x2="490" y2="${axisY + 12}" stroke="${RAY}" stroke-width="1.5" stroke-dasharray="6 3" opacity="0.7" />`;

  body += `<text x="${W / 2}" y="${H - 12}" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">Concave lens always: image virtual · upright · smaller — between F and the lens.</text>`;
  return svgWrap(W, H, "Concave lens image formation", "A horizontal optical bench with a vertical diverging biconcave-lens shape in the centre, virtual focal points F and F' on either side. A green object arrow on the left; red rays diverge after the lens. The diverging rays appear to come from a small upright virtual image arrow between the lens and F.", body);
}

function s3_lensFormulaCard() {
  const W = 540, H = 320;
  const body = `
  <text x="${W / 2}" y="32" font="bold 18px system-ui" font-size="18" font-weight="700" fill="${INK}" text-anchor="middle">Lens Formula + Magnification</text>
  <text x="${W / 2}" y="54" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">Cartesian sign convention: distances measured from the lens; light travels left → right is positive.</text>

  <rect x="60" y="80" width="420" height="60" rx="10" fill="${HIGHLIGHT}" stroke="${ACCENT_2}" stroke-width="2" />
  <text x="${W / 2}" y="120" font="bold 26px system-ui" font-size="26" font-weight="700" fill="${INK}" text-anchor="middle">1/v − 1/u = 1/f</text>

  <text x="60" y="180" font="bold 14px system-ui" font-size="14" font-weight="700" fill="${INK}">Magnification: m = h'/h = v/u</text>

  <text x="60" y="220" font="13px system-ui" font-size="13" fill="${INK}">Worked example — convex lens, f = +20 cm, u = −30 cm:</text>
  <text x="60" y="240" font="13px system-ui" font-size="13" fill="${MUTED}">1/v = 1/f + 1/u = 1/20 + 1/(−30) = 1/60</text>
  <text x="60" y="260" font="bold 13px system-ui" font-size="13" font-weight="700" fill="${POSITIVE}">→ v = +60 cm  (real image, on the right)</text>
  <text x="60" y="280" font="bold 13px system-ui" font-size="13" font-weight="700" fill="${POSITIVE}">→ m = v/u = 60/(−30) = −2  (inverted, 2× larger)</text>

  <text x="${W / 2}" y="${H - 10}" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">Same formula handles convex (f &gt; 0) and concave (f &lt; 0). Negative m = inverted image.</text>
`;
  return svgWrap(W, H, "Lens formula and magnification card", "A formula card showing 1/v − 1/u = 1/f highlighted at top, the magnification m = v/u underneath, and a worked example for a convex lens with f = +20 cm and u = −30 cm: solving gives v = +60 cm (real image) and m = −2 (inverted, twice as large).", body);
}

// ────────────────────────────────────────────────────────────────────────────
// SECTION 4 — Wave Optics (4 SVGs)
// ────────────────────────────────────────────────────────────────────────────

function s4_youngsDoubleSlit() {
  const W = 720, H = 320;
  let body = `
  <text x="${W / 2}" y="32" font="bold 18px system-ui" font-size="18" font-weight="700" fill="${INK}" text-anchor="middle">Young's Double-Slit Geometry</text>
  <text x="${W / 2}" y="54" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">Light passes through two narrow slits and interferes on a distant screen.</text>

  <!-- Source -->
  <circle cx="80" cy="170" r="14" fill="${RAY}" />
  <text x="80" y="200" font="bold 12px system-ui" font-size="12" font-weight="700" fill="${RAY}" text-anchor="middle">source</text>

  <!-- Two slits -->
  <line x1="200" y1="80" x2="200" y2="160" stroke="${SURFACE}" stroke-width="3" />
  <line x1="200" y1="180" x2="200" y2="260" stroke="${SURFACE}" stroke-width="3" />
  <text x="200" y="40" font="bold 12px system-ui" font-size="12" font-weight="700" fill="${INK}" text-anchor="middle">two slits, separation d</text>
  <line x1="190" y1="160" x2="190" y2="180" stroke="${ACCENT_2}" stroke-width="2" />
  <line x1="180" y1="160" x2="180" y2="180" stroke="${ACCENT_2}" stroke-width="2" />
  <text x="170" y="174" font="bold 11px system-ui" font-size="11" font-weight="700" fill="${ACCENT_2}" text-anchor="end">d</text>

  <!-- Light from source to slits -->
  <line x1="94" y1="170" x2="200" y2="170" stroke="${RAY}" stroke-width="2" />

  <!-- Two paths to a screen point P -->
  <line x1="200" y1="170" x2="600" y2="120" stroke="${RAY}" stroke-width="1.5" />
  <line x1="200" y1="170" x2="600" y2="120" stroke="${RAY}" stroke-width="1.5" />

  <!-- Screen on right -->
  <line x1="600" y1="60" x2="600" y2="280" stroke="${SURFACE}" stroke-width="3" />
  <text x="600" y="48" font="bold 12px system-ui" font-size="12" font-weight="700" fill="${INK}" text-anchor="middle">screen</text>

  <!-- Distance L between slits and screen -->
  <line x1="200" y1="288" x2="600" y2="288" stroke="${MUTED}" stroke-width="1.5" />
  <line x1="200" y1="284" x2="200" y2="292" stroke="${MUTED}" stroke-width="1.5" />
  <line x1="600" y1="284" x2="600" y2="292" stroke="${MUTED}" stroke-width="1.5" />
  <text x="400" y="304" font="bold 12px system-ui" font-size="12" font-weight="700" fill="${MUTED}" text-anchor="middle">distance L</text>

  <!-- Point P on screen -->
  <circle cx="600" cy="120" r="6" fill="${POSITIVE}" />
  <text x="612" y="118" font="bold 12px system-ui" font-size="12" font-weight="700" fill="${POSITIVE}">P</text>
  <line x1="600" y1="170" x2="600" y2="120" stroke="${POSITIVE}" stroke-width="1.5" stroke-dasharray="3 3" />
  <text x="616" y="148" font="bold 11px system-ui" font-size="11" font-weight="700" fill="${POSITIVE}">y</text>

  <!-- Path-difference highlight -->
  <text x="${W / 2}" y="${H - 12}" font="bold 11px system-ui" font-size="11" font-weight="700" fill="${ACCENT}" text-anchor="middle">Bright fringe at P when path difference = nλ.  Fringe spacing  Δy = λL/d.</text>
`;
  return svgWrap(W, H, "Youngs double slit experiment geometry", "A point light source on the left feeds light into a barrier with two slits separated by distance d. Two beams pass through the slits and reach a vertical screen on the right, distance L away. A point P on the screen at height y above the centreline is marked. Caption gives the bright-fringe condition and the spacing formula Δy = λL/d.", body);
}

function s4_interferenceFringes() {
  const W = 600, H = 320;
  let body = `
  <text x="${W / 2}" y="32" font="bold 18px system-ui" font-size="18" font-weight="700" fill="${INK}" text-anchor="middle">Interference Fringe Pattern on the Screen</text>
  <text x="${W / 2}" y="54" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">Equally-spaced bright bands separated by dark bands. Fringe spacing Δy = λL/d.</text>

  <!-- Vertical "screen" with fringes -->
  <rect x="80" y="100" width="100" height="180" fill="#0f172a" />
`;
  const fringePositions = [-3, -2, -1, 0, 1, 2, 3];
  const cy = 190;
  const spacing = 22;
  for (const k of fringePositions) {
    const fy = cy + k * spacing;
    // Bright lines (cosine intensity)
    body += `<line x1="80" y1="${fy}" x2="180" y2="${fy}" stroke="white" stroke-width="6" />`;
    body += `<line x1="80" y1="${fy}" x2="180" y2="${fy}" stroke="white" stroke-width="3" opacity="0.6" />`;
  }
  body += `<text x="130" y="92" font="bold 12px system-ui" font-size="12" font-weight="700" fill="${INK}" text-anchor="middle">screen view</text>`;

  // Intensity profile to the right (sinc²-like cosine plot)
  body += `<line x1="240" y1="100" x2="240" y2="280" stroke="${INK}" stroke-width="1.5" />`;
  body += `<line x1="240" y1="280" x2="540" y2="280" stroke="${INK}" stroke-width="1.5" />`;
  body += `<text x="240" y="92" font="bold 11px system-ui" font-size="11" font-weight="700" fill="${INK}" text-anchor="middle">intensity</text>`;
  // Plot sin²((x-c)/spacing*π) approximating bright-dark pattern with envelope
  const samples = 200;
  const pts: string[] = [];
  for (let i = 0; i <= samples; i++) {
    const yPx = 100 + (i / samples) * 180; // along the y-axis of the screen
    const k = (yPx - cy) / spacing;
    const intensity = Math.cos(k * Math.PI) ** 2;
    const xPx = 240 + intensity * 280;
    pts.push(`${xPx.toFixed(1)},${yPx.toFixed(1)}`);
  }
  body += `<polyline points="${pts.join(" ")}" fill="none" stroke="${ACCENT_2}" stroke-width="3" />`;
  body += `<text x="500" y="${cy + 4}" font="bold 11px system-ui" font-size="11" font-weight="700" fill="${ACCENT_2}" text-anchor="middle">central max</text>`;

  // Δy bracket between adjacent maxima
  body += `<line x1="200" y1="${cy}" x2="200" y2="${cy + spacing}" stroke="${POSITIVE}" stroke-width="2" />`;
  body += `<line x1="195" y1="${cy}" x2="205" y2="${cy}" stroke="${POSITIVE}" stroke-width="2" />`;
  body += `<line x1="195" y1="${cy + spacing}" x2="205" y2="${cy + spacing}" stroke="${POSITIVE}" stroke-width="2" />`;
  body += `<text x="186" y="${cy + spacing / 2 + 4}" font="bold 12px system-ui" font-size="12" font-weight="700" fill="${POSITIVE}" text-anchor="end">Δy</text>`;

  body += `<text x="${W / 2}" y="${H - 12}" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">Bright = constructive (path diff = nλ). Dark = destructive (path diff = (n+½)λ).</text>`;
  return svgWrap(W, H, "Two-slit interference fringe pattern", "Left: a black screen with seven horizontal bright fringes equally spaced. Right: an intensity-vs-position plot showing the cos² oscillation with peaks at the bright fringes. The spacing between adjacent fringes is labelled Δy.", body);
}

function s4_singleSlitDiffraction() {
  const W = 600, H = 360;
  let body = `
  <text x="${W / 2}" y="32" font="bold 18px system-ui" font-size="18" font-weight="700" fill="${INK}" text-anchor="middle">Single-Slit Diffraction Pattern</text>
  <text x="${W / 2}" y="54" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">A single narrow slit produces one big central peak and progressively-fainter side lobes.</text>

  <!-- Slit setup -->
  <line x1="80" y1="120" x2="80" y2="180" stroke="${SURFACE}" stroke-width="3" />
  <line x1="80" y1="200" x2="80" y2="260" stroke="${SURFACE}" stroke-width="3" />
  <text x="80" y="100" font="bold 12px system-ui" font-size="12" font-weight="700" fill="${INK}" text-anchor="middle">slit width a</text>
  <line x1="60" y1="180" x2="60" y2="200" stroke="${ACCENT_2}" stroke-width="2" />
  <text x="50" y="194" font="bold 11px system-ui" font-size="11" font-weight="700" fill="${ACCENT_2}" text-anchor="end">a</text>

  <!-- Light fan after slit -->
  <line x1="80" y1="190" x2="540" y2="100" stroke="${RAY}" stroke-width="1.2" opacity="0.6" />
  <line x1="80" y1="190" x2="540" y2="280" stroke="${RAY}" stroke-width="1.2" opacity="0.6" />
  <line x1="80" y1="190" x2="540" y2="190" stroke="${RAY}" stroke-width="2" />
`;
  // Diffraction pattern intensity plot on the right
  // sinc²(x) shape — single big lobe + side lobes
  const samples = 300;
  const pts: string[] = [];
  for (let i = 0; i <= samples; i++) {
    const u = (i / samples - 0.5) * 8; // x from -4 to +4
    const sinc = u === 0 ? 1 : Math.sin(Math.PI * u) / (Math.PI * u);
    const intensity = sinc * sinc;
    const yPx = 100 + (i / samples) * 180;
    const xPx = 540 - intensity * 220;
    pts.push(`${xPx.toFixed(1)},${yPx.toFixed(1)}`);
  }
  body += `<polyline points="${pts.join(" ")}" fill="none" stroke="${ACCENT_2}" stroke-width="3" />`;
  body += `<line x1="540" y1="100" x2="540" y2="280" stroke="${INK}" stroke-width="2" />`;
  body += `<text x="540" y="92" font="bold 11px system-ui" font-size="11" font-weight="700" fill="${INK}" text-anchor="middle">intensity profile</text>`;
  body += `<text x="320" y="186" font="bold 12px system-ui" font-size="12" font-weight="700" fill="${POSITIVE}">central maximum (bright)</text>`;
  body += `<text x="320" y="240" font="bold 11px system-ui" font-size="11" font-weight="700" fill="${ACCENT}">first minimum at sin θ = λ/a</text>`;

  body += `
  <text x="${W / 2}" y="${H - 30}" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">Narrower slit → wider central peak. Wider slit → tighter peak.</text>
  <text x="${W / 2}" y="${H - 14}" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">First dark band at sin θ = λ/a. Side lobes are about 4–5% as bright as the central maximum.</text>
`;
  return svgWrap(W, H, "Single slit diffraction pattern", "A single narrow slit on the left feeds a fan of light to a vertical screen on the right. The screen shows a sinc²-shaped intensity profile: one tall central maximum flanked by symmetric side lobes that decay rapidly. Annotations identify the central maximum and the first minimum at sin θ = λ/a.", body);
}

function s4_interferenceVsDiffraction() {
  const W = 600, H = 320;
  const body = `
  <text x="${W / 2}" y="32" font="bold 18px system-ui" font-size="18" font-weight="700" fill="${INK}" text-anchor="middle">Interference vs Diffraction</text>

  <g>
    <rect x="40" y="60" width="240" height="220" rx="10" fill="${BG}" stroke="${ACCENT}" stroke-width="2" />
    <text x="160" y="86" font="bold 16px system-ui" font-size="16" font-weight="700" fill="${ACCENT}" text-anchor="middle">Interference</text>
    <text x="60" y="120" font="13px system-ui" font-size="13" fill="${INK}">cause:</text>
    <text x="270" y="120" font="bold 13px system-ui" font-size="13" font-weight="700" fill="${INK}" text-anchor="end">two (or more) sources</text>
    <text x="60" y="150" font="13px system-ui" font-size="13" fill="${INK}">pattern:</text>
    <text x="270" y="150" font="bold 13px system-ui" font-size="13" font-weight="700" fill="${INK}" text-anchor="end">equally-spaced fringes</text>
    <text x="60" y="180" font="13px system-ui" font-size="13" fill="${INK}">spacing:</text>
    <text x="270" y="180" font="bold 13px system-ui" font-size="13" font-weight="700" fill="${INK}" text-anchor="end">Δy = λL/d</text>
    <text x="60" y="210" font="13px system-ui" font-size="13" fill="${INK}">brightness:</text>
    <text x="270" y="210" font="bold 13px system-ui" font-size="13" font-weight="700" fill="${INK}" text-anchor="end">all fringes ≈ same</text>
    <text x="60" y="240" font="13px system-ui" font-size="13" fill="${INK}">canonical setup:</text>
    <text x="270" y="240" font="bold 13px system-ui" font-size="13" font-weight="700" fill="${INK}" text-anchor="end">double slit</text>
  </g>

  <g>
    <rect x="320" y="60" width="240" height="220" rx="10" fill="${BG}" stroke="${ACCENT_2}" stroke-width="2" />
    <text x="440" y="86" font="bold 16px system-ui" font-size="16" font-weight="700" fill="${ACCENT_2}" text-anchor="middle">Diffraction</text>
    <text x="340" y="120" font="13px system-ui" font-size="13" fill="${INK}">cause:</text>
    <text x="550" y="120" font="bold 13px system-ui" font-size="13" font-weight="700" fill="${INK}" text-anchor="end">single source spreading</text>
    <text x="340" y="150" font="13px system-ui" font-size="13" fill="${INK}">pattern:</text>
    <text x="550" y="150" font="bold 13px system-ui" font-size="13" font-weight="700" fill="${INK}" text-anchor="end">central peak + side lobes</text>
    <text x="340" y="180" font="13px system-ui" font-size="13" fill="${INK}">first minimum:</text>
    <text x="550" y="180" font="bold 13px system-ui" font-size="13" font-weight="700" fill="${INK}" text-anchor="end">sin θ = λ/a</text>
    <text x="340" y="210" font="13px system-ui" font-size="13" fill="${INK}">brightness:</text>
    <text x="550" y="210" font="bold 13px system-ui" font-size="13" font-weight="700" fill="${INK}" text-anchor="end">central ≫ sides</text>
    <text x="340" y="240" font="13px system-ui" font-size="13" fill="${INK}">canonical setup:</text>
    <text x="550" y="240" font="bold 13px system-ui" font-size="13" font-weight="700" fill="${INK}" text-anchor="end">single slit</text>
  </g>

  <text x="${W / 2}" y="${H - 12}" font="11px system-ui" font-size="11" fill="${MUTED}" text-anchor="middle">Both are wave behaviour. Interference combines waves from multiple paths; diffraction is what one path does by itself.</text>
`;
  return svgWrap(W, H, "Interference versus diffraction comparison card", "Two-card comparison side by side: left card describes interference (two sources, equally-spaced fringes, Δy = λL/d, fringes equally bright, double-slit canonical setup). Right card describes diffraction (single source, central peak with side lobes, first minimum at sin θ = λ/a, central much brighter, single-slit canonical setup).", body);
}

// ────────────────────────────────────────────────────────────────────────────
// Main
// ────────────────────────────────────────────────────────────────────────────

mkdirSync(ROOT, { recursive: true });

write("section-1-reflection/law-of-reflection.svg", s1_lawOfReflection());
write("section-1-reflection/concave-mirror-ray-diagram.svg", s1_concaveMirror());
write("section-1-reflection/convex-mirror-ray-diagram.svg", s1_convexMirror());

write("section-2-refraction/snells-law.svg", s2_snellsLaw());
write("section-2-refraction/total-internal-reflection.svg", s2_totalInternalReflection());
write("section-2-refraction/prism-dispersion.svg", s2_prismDispersion());

write("section-3-lenses/convex-lens-image-formation.svg", s3_convexLens());
write("section-3-lenses/concave-lens-image-formation.svg", s3_concaveLens());
write("section-3-lenses/lens-formula-and-magnification.svg", s3_lensFormulaCard());

write("section-4-wave-optics/youngs-double-slit-geometry.svg", s4_youngsDoubleSlit());
write("section-4-wave-optics/interference-fringe-pattern.svg", s4_interferenceFringes());
write("section-4-wave-optics/single-slit-diffraction-pattern.svg", s4_singleSlitDiffraction());
write("section-4-wave-optics/interference-vs-diffraction.svg", s4_interferenceVsDiffraction());

console.log("done — 13 SVGs");
