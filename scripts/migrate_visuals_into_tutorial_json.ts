#!/usr/bin/env bun
/**
 * One-shot migration for issue #318:
 * Patch the tutorial_en.json files for the two existing exemplar units to
 * include the `visuals` array per section. The data here mirrors the
 * pre-#318 VISUAL_MAP that lived in web/components/content/VisualSlot.tsx.
 *
 * After this script runs, VISUAL_MAP can be retired (already done in the
 * companion commit) without losing any visual content.
 *
 * Run from repo root:
 *   bun scripts/migrate_visuals_into_tutorial_json.ts
 */

import { readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";

type VisualItem = {
  src: string;
  alt: string;
  caption?: string;
  poster?: string;
  duration?: string;
};
type VisualBlock = {
  kind: "image" | "image-grid" | "animated-svg" | "video";
  heading?: string;
  items: VisualItem[];
};
type VisualMap = Record<string, VisualBlock[]>; // keyed on section_id

const ROOT = join(import.meta.dir, "..", "content_store_data", "curricula");

// ── G11-MATH-001 Sets and Functions ──────────────────────────────────────
const MATH_001: VisualMap = {
  s1: [
    {
      kind: "image-grid",
      heading: "Set operations — Venn diagrams",
      items: [
        { src: "/sample-visuals/G11-MATH-001/union.svg",        alt: "A union B",          caption: "A ∪ B  —  everything in A or B" },
        { src: "/sample-visuals/G11-MATH-001/intersection.svg", alt: "A intersect B",      caption: "A ∩ B  —  in both" },
        { src: "/sample-visuals/G11-MATH-001/difference.svg",   alt: "A minus B",          caption: "A \\ B  —  in A but not in B" },
        { src: "/sample-visuals/G11-MATH-001/complement.svg",   alt: "Complement of A",    caption: "Aᶜ  —  in 𝕌 outside A" },
      ],
    },
    {
      kind: "image",
      heading: "Power set lattice — 𝒫({a, b, c})",
      items: [
        { src: "/sample-visuals/G11-MATH-001/hasse-3-element.svg",
          alt: "Hasse diagram of the power set of a three-element set",
          caption: "Edges connect subsets differing by one element. 2³ = 8 subsets." },
      ],
    },
  ],
  s2: [
    {
      kind: "image-grid",
      heading: "Function or not? — arrow diagrams",
      items: [
        { src: "/sample-visuals/G11-MATH-001/R1-function.svg",                alt: "R1 is a function",                  caption: "R₁ — function ✓" },
        { src: "/sample-visuals/G11-MATH-001/R2-not-function.svg",            alt: "R2 is not a function",              caption: "R₂ — not a function (1 → p and q)" },
        { src: "/sample-visuals/G11-MATH-001/R3-function-not-injective.svg",  alt: "R3 is a function but not injective", caption: "R₃ — function ✓ (not injective)" },
        { src: "/sample-visuals/G11-MATH-001/R4-not-function.svg",            alt: "R4 is not a function",              caption: "R₄ — not a function (3 has no image)" },
      ],
    },
  ],
  s4: [
    {
      kind: "image-grid",
      heading: "Composition is not commutative",
      items: [
        { src: "/sample-visuals/G11-MATH-001/g-after-f.svg", alt: "Pipeline showing g(f(2)) = 48", caption: "(g ∘ f)(2) = g(f(2)) = 48" },
        { src: "/sample-visuals/G11-MATH-001/f-after-g.svg", alt: "Pipeline showing f(g(2)) = 9",  caption: "(f ∘ g)(2) = f(g(2)) = 9" },
      ],
    },
  ],
  s5: [
    {
      kind: "animated-svg",
      heading: "Projectile motion — h(t) = −4.9t² + 14t + 2",
      items: [
        { src: "/sample-visuals/G11-MATH-001/projectile-smil.svg",
          alt: "Animated parabola showing projectile motion",
          caption: "Ball traces the parabola in real time. Auto-plays in any modern browser." },
      ],
    },
    {
      kind: "video",
      heading: "Watch the full chapter explainer",
      items: [
        { src: "/sample-visuals/G11-MATH-001/Sets_and_Functions_Demo.mp4",
          alt: "Sets and Functions — animated chapter explainer",
          duration: "1:57",
          caption: "9-scene Remotion render walking through every section of the chapter." },
      ],
    },
  ],
};

// ── G11-PHYS-002 Kinematics ──────────────────────────────────────────────
const PHYS_002: VisualMap = {
  s1: [
    {
      kind: "image-grid",
      heading: "Position, displacement, and the average–instant distinction",
      items: [
        { src: "/sample-visuals/G11-PHYS-002/1d-position-and-displacement.svg",        alt: "Number line showing initial and final positions with displacement arrow",       caption: "1-D motion: x_i, x_f, and Δx on a number line." },
        { src: "/sample-visuals/G11-PHYS-002/distance-vs-displacement.svg",            alt: "Curved path from A to B with straight displacement vector overlaid",            caption: "Distance follows the path; displacement is the straight A→B vector." },
        { src: "/sample-visuals/G11-PHYS-002/average-vs-instantaneous-velocity.svg",   alt: "x-t curve with secant for average velocity and tangent for instantaneous",      caption: "Secant slope = average velocity; tangent slope = instantaneous." },
      ],
    },
  ],
  s2: [
    {
      kind: "image-grid",
      heading: "Uniformly accelerated motion — the three graphs",
      items: [
        { src: "/sample-visuals/G11-PHYS-002/xt-uam.svg", alt: "x-t parabola for UAM",                          caption: "x = vᵢt + ½at²  →  parabolic" },
        { src: "/sample-visuals/G11-PHYS-002/vt-uam.svg", alt: "v-t straight line with shaded area for displacement", caption: "v = vᵢ + at  →  linear; area under v = Δx" },
        { src: "/sample-visuals/G11-PHYS-002/at-uam.svg", alt: "a-t horizontal constant line",                  caption: "a = constant  →  horizontal line" },
      ],
    },
    {
      kind: "video",
      heading: "Watch — the three graphs build together",
      items: [
        { src: "/sample-visuals/G11-PHYS-002/Kinematics_UAM.mp4", alt: "Uniformly Accelerated Motion — x, v, a animation", duration: "0:24", caption: "Each graph is the slope of the one to its left." },
      ],
    },
  ],
  s3: [
    {
      kind: "image-grid",
      heading: "Free fall — vertical motion under gravity",
      items: [
        { src: "/sample-visuals/G11-PHYS-002/height-vs-time.svg",   alt: "Height vs time for object thrown straight up",                                       caption: "h(t) = vᵢt − ½gt²  with peak and impact marked." },
        { src: "/sample-visuals/G11-PHYS-002/velocity-vs-time.svg", alt: "Velocity vs time for object thrown straight up, crossing zero at peak",            caption: "v(t) crosses zero at the peak — the sign change is the direction reversal." },
      ],
    },
    {
      kind: "video",
      heading: "Watch — ball thrown up at 20 m/s, with live h(t) and v(t)",
      items: [
        { src: "/sample-visuals/G11-PHYS-002/Kinematics_FreeFall.mp4", alt: "Free fall animation with live readouts", duration: "0:28", caption: "Ball rises, slows, peaks at 20.4 m, returns. Live readouts for t, h, v." },
      ],
    },
  ],
  s4: [
    {
      kind: "image",
      heading: "Projectile motion — trajectory",
      items: [
        { src: "/sample-visuals/G11-PHYS-002/trajectory.svg", alt: "Parabolic projectile trajectory at 60 degrees with peak and range", caption: "Launch at v = 20 m/s, θ = 60°. Range ≈ 35.3 m, peak ≈ 15.3 m." },
      ],
    },
    {
      kind: "image-grid",
      heading: "Velocity decomposition and key results",
      items: [
        { src: "/sample-visuals/G11-PHYS-002/velocity-decomposition.svg", alt: "Initial velocity decomposed into horizontal and vertical components", caption: "vₓ = v cos θ  (constant);  v_y = v sin θ  (changes under gravity)." },
        { src: "/sample-visuals/G11-PHYS-002/key-results.svg",            alt: "Three result cards summarising time of flight, range, max height",  caption: "Three closed-form results — symmetry of θ ↔ 90°−θ pairs gives equal range." },
      ],
    },
    {
      kind: "video",
      heading: "Watch — projectile trajectory with live velocity vectors",
      items: [
        { src: "/sample-visuals/G11-PHYS-002/Kinematics_Projectile.mp4", alt: "Animated projectile trajectory with live vx and vy vectors", duration: "0:22", caption: "vₓ stays constant; v_y shrinks to 0 at the peak, then reverses sign." },
      ],
    },
  ],
  s5: [
    {
      kind: "image-grid",
      heading: "Reading the graphs — slope is velocity, area is displacement",
      items: [
        { src: "/sample-visuals/G11-PHYS-002/xt-with-tangent.svg", alt: "x-t curve with tangent line showing instantaneous velocity",      caption: "Tangent slope on x-t = instantaneous velocity at that point." },
        { src: "/sample-visuals/G11-PHYS-002/vt-with-area.svg",    alt: "v-t curve with shaded area under it showing displacement",        caption: "Area under v-t between two times = displacement over that interval." },
      ],
    },
    {
      kind: "image",
      heading: "x – v – a relationships, side-by-side",
      items: [
        { src: "/sample-visuals/G11-PHYS-002/xt-vt-at-trio.svg", alt: "Three side-by-side plots showing x-t, v-t, a-t for UAM", caption: "Each graph is the slope of the one to its left, and the area of the one to its right." },
      ],
    },
    {
      kind: "image",
      heading: "The slope ↔ area chain",
      items: [
        { src: "/sample-visuals/G11-PHYS-002/slope-area-summary.svg", alt: "Three boxes for x, v, a connected by slope and area arrows", caption: "Slope moves you to the next derivative; area integrates back." },
      ],
    },
    {
      kind: "video",
      heading: "Watch — slope-and-area in motion",
      items: [
        { src: "/sample-visuals/G11-PHYS-002/Kinematics_GraphAnalysis.mp4", alt: "Animated slope and area construction between x-t and v-t graphs", duration: "0:26", caption: "Tangent sweeps along x(t) to build v(t); area sweeps under v(t) to recover Δx." },
      ],
    },
  ],
};

const TARGETS: Array<{ unit: string; curriculum: string; map: VisualMap }> = [
  { unit: "G11-MATH-001", curriculum: "default-2026-g11-science", map: MATH_001 },
  { unit: "G11-PHYS-002", curriculum: "default-2026-g11-science", map: PHYS_002 },
];

for (const { unit, curriculum, map } of TARGETS) {
  const path = join(ROOT, curriculum, unit, "tutorial_en.json");
  const json = JSON.parse(readFileSync(path, "utf-8"));
  let touched = 0;
  for (const section of json.sections) {
    const blocks = map[section.section_id];
    if (!blocks) {
      // If no entry, ensure an empty list rather than missing field
      if (!section.visuals) section.visuals = [];
      continue;
    }
    section.visuals = blocks;
    touched += blocks.length;
  }
  writeFileSync(path, JSON.stringify(json, null, 2));
  console.log(`patched ${unit}: ${touched} visual blocks across ${Object.keys(map).length} sections`);
}
