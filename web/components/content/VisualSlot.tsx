"use client";

import { Eye } from "lucide-react";

type VisualKind = "image" | "image-grid" | "animated-svg";

interface VisualItem {
  src: string;
  caption?: string;
  alt: string;
}

interface VisualBlock {
  kind: VisualKind;
  heading?: string;
  items: VisualItem[];
}

/**
 * Static map of visual enhancements keyed on `${unit_id}::${section_id}`.
 * Demo wiring for issue #316 — proves out the in-tutorial visual surface
 * before the production schema (visual-block declarations in tutorial JSON)
 * lands. When #316 ships, this map is replaced by data from the tutorial
 * payload itself.
 */
const VISUAL_MAP: Record<string, VisualBlock[]> = {
  // ── G11-MATH-001 Sets and Functions ──────────────────────────────────────
  "G11-MATH-001::s1": [
    {
      kind: "image-grid",
      heading: "Set operations — Venn diagrams",
      items: [
        { src: "/sample-visuals/G11-MATH-001/union.svg",        alt: "A union B",         caption: "A ∪ B  —  everything in A or B" },
        { src: "/sample-visuals/G11-MATH-001/intersection.svg", alt: "A intersect B",     caption: "A ∩ B  —  in both" },
        { src: "/sample-visuals/G11-MATH-001/difference.svg",   alt: "A minus B",         caption: "A \\ B  —  in A but not in B" },
        { src: "/sample-visuals/G11-MATH-001/complement.svg",   alt: "Complement of A",   caption: "Aᶜ  —  in 𝕌 outside A" },
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
  "G11-MATH-001::s2": [
    {
      kind: "image-grid",
      heading: "Function or not? — arrow diagrams",
      items: [
        { src: "/sample-visuals/G11-MATH-001/R1-function.svg",                alt: "R1 is a function",                caption: "R₁ — function ✓" },
        { src: "/sample-visuals/G11-MATH-001/R2-not-function.svg",            alt: "R2 is not a function",            caption: "R₂ — not a function (1 → p and q)" },
        { src: "/sample-visuals/G11-MATH-001/R3-function-not-injective.svg",  alt: "R3 is a function but not injective", caption: "R₃ — function ✓ (not injective)" },
        { src: "/sample-visuals/G11-MATH-001/R4-not-function.svg",            alt: "R4 is not a function",            caption: "R₄ — not a function (3 has no image)" },
      ],
    },
  ],
  "G11-MATH-001::s4": [
    {
      kind: "image-grid",
      heading: "Composition is not commutative",
      items: [
        { src: "/sample-visuals/G11-MATH-001/g-after-f.svg",
          alt: "Pipeline showing g(f(2)) = 48",
          caption: "(g ∘ f)(2) = g(f(2)) = 48" },
        { src: "/sample-visuals/G11-MATH-001/f-after-g.svg",
          alt: "Pipeline showing f(g(2)) = 9",
          caption: "(f ∘ g)(2) = f(g(2)) = 9" },
      ],
    },
  ],
  "G11-MATH-001::s5": [
    {
      kind: "animated-svg",
      heading: "Projectile motion — h(t) = −4.9t² + 14t + 2",
      items: [
        { src: "/sample-visuals/G11-MATH-001/projectile-smil.svg",
          alt: "Animated parabola showing projectile motion",
          caption: "Ball traces the parabola in real time. Auto-plays in any modern browser." },
      ],
    },
  ],
};

interface VisualSlotProps {
  unitId: string;
  sectionId: string;
}

export function VisualSlot({ unitId, sectionId }: VisualSlotProps) {
  const key = `${unitId}::${sectionId}`;
  const blocks = VISUAL_MAP[key];
  if (!blocks || blocks.length === 0) return null;

  return (
    <div className="mt-4 space-y-3">
      {blocks.map((block, i) => (
        <VisualBlockRender key={i} block={block} />
      ))}
    </div>
  );
}

function VisualBlockRender({ block }: { block: VisualBlock }) {
  return (
    <div className="rounded-md border border-emerald-200 bg-emerald-50 p-3">
      <div className="mb-2 flex items-center gap-2">
        <Eye className="h-3.5 w-3.5 text-emerald-700" aria-hidden="true" />
        <h4 className="text-xs font-semibold uppercase tracking-wide text-emerald-800">
          {block.heading ?? "Visual explanation"}
        </h4>
      </div>
      {block.kind === "image-grid" ? (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-2 md:grid-cols-2 lg:grid-cols-2">
          {block.items.map((item, i) => (
            <VisualImage key={i} item={item} />
          ))}
        </div>
      ) : (
        <div className="space-y-3">
          {block.items.map((item, i) => (
            <VisualImage key={i} item={item} />
          ))}
        </div>
      )}
    </div>
  );
}

function VisualImage({ item }: { item: VisualItem }) {
  return (
    <figure className="overflow-hidden rounded border border-emerald-200 bg-white">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={item.src}
        alt={item.alt}
        loading="lazy"
        className="h-auto w-full"
      />
      {item.caption && (
        <figcaption className="border-t border-emerald-100 bg-emerald-50/40 px-2 py-1 text-xs text-emerald-900">
          {item.caption}
        </figcaption>
      )}
    </figure>
  );
}
