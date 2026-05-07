#!/usr/bin/env bun
/**
 * Generate the 30 visual-library sidecars for the existing exemplar SVGs in
 * G11-MATH-001 + G11-PHYS-002 (issue #322 phase 2).
 *
 * Run from repo root:
 *   bun scripts/seed_library_sidecars.ts
 *
 * Idempotent: re-running overwrites the sidecars from this declarative
 * spec, so this is also the canonical edit surface — change the spec
 * here, re-run, and re-commit.
 *
 * After this writes, validate with:
 *   bun scripts/validate_library_metadata.ts \
 *     "sample_content/**\/Option2_Catalogue/**\/*.metadata.yaml"
 */

import { writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { mkdirSync } from "node:fs";

type Kind = "image" | "image-grid" | "animated-svg" | "video";

interface SidecarSpec {
  asset: string;          // path relative to repo root
  id: string;             // globally unique slug
  kind: Kind;
  subject: "physics" | "chemistry" | "math" | "biology";
  topic_phrase: string;
  keywords: string[];
  source_unit: string;
}

const REPO_ROOT = join(import.meta.dir, "..");

const SPECS: SidecarSpec[] = [
  // ── G11-MATH-001 Sets and Functions ──────────────────────────────────────
  // animations/
  {
    asset: "sample_content/g11-science/G11-MATH-001_Sets_and_Functions/Option2_Catalogue/animations/projectile-smil.svg",
    id: "math-projectile-smil-anim",
    kind: "animated-svg",
    subject: "math",
    topic_phrase: "projectile motion animation",
    keywords: ["projectile", "parabola", "smil", "animated", "motion"],
    source_unit: "G11-MATH-001",
  },
  // arrow-diagrams/
  {
    asset: "sample_content/g11-science/G11-MATH-001_Sets_and_Functions/Option2_Catalogue/arrow-diagrams/bijective.svg",
    id: "math-arrow-diagram-bijective",
    kind: "image",
    subject: "math",
    topic_phrase: "bijective function arrow diagram",
    keywords: ["function", "bijective", "one-to-one", "onto", "arrow-diagram"],
    source_unit: "G11-MATH-001",
  },
  {
    asset: "sample_content/g11-science/G11-MATH-001_Sets_and_Functions/Option2_Catalogue/arrow-diagrams/injective-only.svg",
    id: "math-arrow-diagram-injective-only",
    kind: "image",
    subject: "math",
    topic_phrase: "injective only function arrow diagram",
    keywords: ["function", "injective", "one-to-one", "arrow-diagram"],
    source_unit: "G11-MATH-001",
  },
  {
    asset: "sample_content/g11-science/G11-MATH-001_Sets_and_Functions/Option2_Catalogue/arrow-diagrams/surjective-only.svg",
    id: "math-arrow-diagram-surjective-only",
    kind: "image",
    subject: "math",
    topic_phrase: "surjective only function arrow diagram",
    keywords: ["function", "surjective", "onto", "arrow-diagram"],
    source_unit: "G11-MATH-001",
  },
  {
    asset: "sample_content/g11-science/G11-MATH-001_Sets_and_Functions/Option2_Catalogue/arrow-diagrams/R1-function.svg",
    id: "math-arrow-diagram-r1-function",
    kind: "image",
    subject: "math",
    topic_phrase: "R1 valid function arrow diagram",
    keywords: ["function", "definition", "valid", "arrow-diagram"],
    source_unit: "G11-MATH-001",
  },
  {
    asset: "sample_content/g11-science/G11-MATH-001_Sets_and_Functions/Option2_Catalogue/arrow-diagrams/R2-not-function.svg",
    id: "math-arrow-diagram-r2-not-function",
    kind: "image",
    subject: "math",
    topic_phrase: "R2 not a function arrow diagram",
    keywords: ["function", "counter-example", "uniqueness", "arrow-diagram"],
    source_unit: "G11-MATH-001",
  },
  {
    asset: "sample_content/g11-science/G11-MATH-001_Sets_and_Functions/Option2_Catalogue/arrow-diagrams/R3-function-not-injective.svg",
    id: "math-arrow-diagram-r3-function-not-injective",
    kind: "image",
    subject: "math",
    topic_phrase: "R3 function but not injective",
    keywords: ["function", "not-injective", "many-to-one", "arrow-diagram"],
    source_unit: "G11-MATH-001",
  },
  {
    asset: "sample_content/g11-science/G11-MATH-001_Sets_and_Functions/Option2_Catalogue/arrow-diagrams/R4-not-function.svg",
    id: "math-arrow-diagram-r4-not-function",
    kind: "image",
    subject: "math",
    topic_phrase: "R4 not a function (totality violated)",
    keywords: ["function", "counter-example", "totality", "arrow-diagram"],
    source_unit: "G11-MATH-001",
  },
  // composition/
  {
    asset: "sample_content/g11-science/G11-MATH-001_Sets_and_Functions/Option2_Catalogue/composition/f-after-g.svg",
    id: "math-function-composition-f-after-g",
    kind: "image",
    subject: "math",
    topic_phrase: "function composition f after g pipeline",
    keywords: ["function", "composition", "pipeline", "f-of-g"],
    source_unit: "G11-MATH-001",
  },
  {
    asset: "sample_content/g11-science/G11-MATH-001_Sets_and_Functions/Option2_Catalogue/composition/g-after-f.svg",
    id: "math-function-composition-g-after-f",
    kind: "image",
    subject: "math",
    topic_phrase: "function composition g after f pipeline",
    keywords: ["function", "composition", "pipeline", "g-of-f"],
    source_unit: "G11-MATH-001",
  },
  // power-set/
  {
    asset: "sample_content/g11-science/G11-MATH-001_Sets_and_Functions/Option2_Catalogue/power-set/hasse-3-element.svg",
    id: "math-power-set-hasse-3-element",
    kind: "image",
    subject: "math",
    topic_phrase: "power set Hasse diagram three-element set",
    keywords: ["power-set", "hasse-diagram", "lattice", "subset", "ordering"],
    source_unit: "G11-MATH-001",
  },
  // set-operations/
  {
    asset: "sample_content/g11-science/G11-MATH-001_Sets_and_Functions/Option2_Catalogue/set-operations/union.svg",
    id: "math-set-operation-union-venn",
    kind: "image",
    subject: "math",
    topic_phrase: "set union Venn diagram",
    keywords: ["set-theory", "venn-diagram", "union", "or"],
    source_unit: "G11-MATH-001",
  },
  {
    asset: "sample_content/g11-science/G11-MATH-001_Sets_and_Functions/Option2_Catalogue/set-operations/intersection.svg",
    id: "math-set-operation-intersection-venn",
    kind: "image",
    subject: "math",
    topic_phrase: "set intersection Venn diagram",
    keywords: ["set-theory", "venn-diagram", "intersection", "and"],
    source_unit: "G11-MATH-001",
  },
  {
    asset: "sample_content/g11-science/G11-MATH-001_Sets_and_Functions/Option2_Catalogue/set-operations/difference.svg",
    id: "math-set-operation-difference-venn",
    kind: "image",
    subject: "math",
    topic_phrase: "set difference Venn diagram",
    keywords: ["set-theory", "venn-diagram", "difference", "minus"],
    source_unit: "G11-MATH-001",
  },
  {
    asset: "sample_content/g11-science/G11-MATH-001_Sets_and_Functions/Option2_Catalogue/set-operations/complement.svg",
    id: "math-set-operation-complement-venn",
    kind: "image",
    subject: "math",
    topic_phrase: "set complement Venn diagram",
    keywords: ["set-theory", "venn-diagram", "complement", "universe"],
    source_unit: "G11-MATH-001",
  },

  // ── G11-PHYS-002 Kinematics ─────────────────────────────────────────────
  // section-1-fundamentals/
  {
    asset: "sample_content/g11-science/G11-PHYS-002_Kinematics/Option2_Catalogue/section-1-fundamentals/1d-position-and-displacement.svg",
    id: "physics-kinematics-1d-position-and-displacement",
    kind: "image",
    subject: "physics",
    topic_phrase: "one-dimensional position and displacement on a number line",
    keywords: ["kinematics", "position", "displacement", "1d", "number-line"],
    source_unit: "G11-PHYS-002",
  },
  {
    asset: "sample_content/g11-science/G11-PHYS-002_Kinematics/Option2_Catalogue/section-1-fundamentals/distance-vs-displacement.svg",
    id: "physics-kinematics-distance-vs-displacement",
    kind: "image",
    subject: "physics",
    topic_phrase: "distance versus displacement on a curved path",
    keywords: ["kinematics", "distance", "displacement", "scalar", "vector", "path"],
    source_unit: "G11-PHYS-002",
  },
  {
    asset: "sample_content/g11-science/G11-PHYS-002_Kinematics/Option2_Catalogue/section-1-fundamentals/average-vs-instantaneous-velocity.svg",
    id: "physics-kinematics-average-vs-instantaneous-velocity",
    kind: "image",
    subject: "physics",
    topic_phrase: "average versus instantaneous velocity on x-t curve",
    keywords: ["kinematics", "velocity", "average", "instantaneous", "secant", "tangent"],
    source_unit: "G11-PHYS-002",
  },
  // section-2-uam/
  {
    asset: "sample_content/g11-science/G11-PHYS-002_Kinematics/Option2_Catalogue/section-2-uam/xt-uam.svg",
    id: "physics-kinematics-xt-uam",
    kind: "image",
    subject: "physics",
    topic_phrase: "position-time parabola for uniformly accelerated motion",
    keywords: ["kinematics", "uam", "position-time", "parabola", "x-t-graph"],
    source_unit: "G11-PHYS-002",
  },
  {
    asset: "sample_content/g11-science/G11-PHYS-002_Kinematics/Option2_Catalogue/section-2-uam/vt-uam.svg",
    id: "physics-kinematics-vt-uam",
    kind: "image",
    subject: "physics",
    topic_phrase: "velocity-time line for uniformly accelerated motion",
    keywords: ["kinematics", "uam", "velocity-time", "linear", "v-t-graph"],
    source_unit: "G11-PHYS-002",
  },
  {
    asset: "sample_content/g11-science/G11-PHYS-002_Kinematics/Option2_Catalogue/section-2-uam/at-uam.svg",
    id: "physics-kinematics-at-uam",
    kind: "image",
    subject: "physics",
    topic_phrase: "acceleration-time constant for uniformly accelerated motion",
    keywords: ["kinematics", "uam", "acceleration-time", "constant", "a-t-graph"],
    source_unit: "G11-PHYS-002",
  },
  // section-3-freefall/
  {
    asset: "sample_content/g11-science/G11-PHYS-002_Kinematics/Option2_Catalogue/section-3-freefall/height-vs-time.svg",
    id: "physics-kinematics-freefall-height-vs-time",
    kind: "image",
    subject: "physics",
    topic_phrase: "height versus time for object thrown straight up",
    keywords: ["kinematics", "free-fall", "height", "parabola", "thrown-up"],
    source_unit: "G11-PHYS-002",
  },
  {
    asset: "sample_content/g11-science/G11-PHYS-002_Kinematics/Option2_Catalogue/section-3-freefall/velocity-vs-time.svg",
    id: "physics-kinematics-freefall-velocity-vs-time",
    kind: "image",
    subject: "physics",
    topic_phrase: "velocity versus time for free fall (zero crossing at peak)",
    keywords: ["kinematics", "free-fall", "velocity", "zero-crossing", "direction-reversal"],
    source_unit: "G11-PHYS-002",
  },
  // section-4-projectile/
  {
    asset: "sample_content/g11-science/G11-PHYS-002_Kinematics/Option2_Catalogue/section-4-projectile/trajectory.svg",
    id: "physics-kinematics-projectile-trajectory",
    kind: "image",
    subject: "physics",
    topic_phrase: "projectile motion trajectory at 60 degrees",
    keywords: ["kinematics", "projectile", "trajectory", "parabola", "range", "max-height"],
    source_unit: "G11-PHYS-002",
  },
  {
    asset: "sample_content/g11-science/G11-PHYS-002_Kinematics/Option2_Catalogue/section-4-projectile/velocity-decomposition.svg",
    id: "physics-kinematics-velocity-decomposition",
    kind: "image",
    subject: "physics",
    topic_phrase: "initial velocity decomposition into horizontal and vertical components",
    keywords: ["kinematics", "vector", "decomposition", "horizontal", "vertical", "cos", "sin"],
    source_unit: "G11-PHYS-002",
  },
  {
    asset: "sample_content/g11-science/G11-PHYS-002_Kinematics/Option2_Catalogue/section-4-projectile/key-results.svg",
    id: "physics-kinematics-projectile-key-results",
    kind: "image",
    subject: "physics",
    topic_phrase: "projectile motion key results time of flight range max height",
    keywords: ["kinematics", "projectile", "time-of-flight", "range", "max-height", "formulas"],
    source_unit: "G11-PHYS-002",
  },
  // section-5-graphs/
  {
    asset: "sample_content/g11-science/G11-PHYS-002_Kinematics/Option2_Catalogue/section-5-graphs/xt-with-tangent.svg",
    id: "physics-kinematics-xt-with-tangent",
    kind: "image",
    subject: "physics",
    topic_phrase: "x-t curve with tangent showing instantaneous velocity",
    keywords: ["kinematics", "x-t-graph", "tangent", "slope", "instantaneous-velocity"],
    source_unit: "G11-PHYS-002",
  },
  {
    asset: "sample_content/g11-science/G11-PHYS-002_Kinematics/Option2_Catalogue/section-5-graphs/vt-with-area.svg",
    id: "physics-kinematics-vt-with-area",
    kind: "image",
    subject: "physics",
    topic_phrase: "v-t curve with shaded area showing displacement",
    keywords: ["kinematics", "v-t-graph", "area-under-curve", "displacement", "integration"],
    source_unit: "G11-PHYS-002",
  },
  {
    asset: "sample_content/g11-science/G11-PHYS-002_Kinematics/Option2_Catalogue/section-5-graphs/xt-vt-at-trio.svg",
    id: "physics-kinematics-xt-vt-at-trio",
    kind: "image",
    subject: "physics",
    topic_phrase: "x-t v-t a-t graphs side-by-side for UAM",
    keywords: ["kinematics", "uam", "trio", "side-by-side", "relationships"],
    source_unit: "G11-PHYS-002",
  },
  {
    asset: "sample_content/g11-science/G11-PHYS-002_Kinematics/Option2_Catalogue/section-5-graphs/slope-area-summary.svg",
    id: "physics-kinematics-slope-area-summary",
    kind: "image",
    subject: "physics",
    topic_phrase: "slope and area chain summary x v a",
    keywords: ["kinematics", "slope", "area", "calculus", "differentiation", "integration"],
    source_unit: "G11-PHYS-002",
  },
];


function emit(spec: SidecarSpec): string {
  const keywordLines = spec.keywords.map((k) => `  - ${k}`).join("\n");
  return `# Auto-generated by scripts/seed_library_sidecars.ts — edit the spec there
# and re-run: bun scripts/seed_library_sidecars.ts
schema_version: 1
id: ${spec.id}
kind: ${spec.kind}
subject: ${spec.subject}
topic_phrase: "${spec.topic_phrase}"
keywords:
${keywordLines}
license: platform-cc-by-sa
source_unit: ${spec.source_unit}
`;
}


function sidecarPath(assetPath: string): string {
  // Replace the asset extension with .metadata.yaml
  const dot = assetPath.lastIndexOf(".");
  return assetPath.slice(0, dot) + ".metadata.yaml";
}


let written = 0;
for (const spec of SPECS) {
  const sidecar = sidecarPath(spec.asset);
  const path = join(REPO_ROOT, sidecar);
  mkdirSync(dirname(path), { recursive: true });
  writeFileSync(path, emit(spec));
  written++;
}

console.log(`wrote ${written} sidecar(s)`);
