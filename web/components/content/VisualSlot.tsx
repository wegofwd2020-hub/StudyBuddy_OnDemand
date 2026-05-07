"use client";

import { useState } from "react";
import { Eye, PlayCircle, Film } from "lucide-react";

type VisualKind = "image" | "image-grid" | "animated-svg" | "video";

interface VisualItem {
  src: string;
  caption?: string;
  alt: string;
  poster?: string;       // optional still image to show before play
  duration?: string;     // human-readable duration label, e.g. "1:57"
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

  // ── G11-PHYS-002 Kinematics ──────────────────────────────────────────────
  "G11-PHYS-002::s1": [
    {
      kind: "image-grid",
      heading: "Position, displacement, and the average–instant distinction",
      items: [
        { src: "/sample-visuals/G11-PHYS-002/1d-position-and-displacement.svg",
          alt: "Number line showing initial and final positions with displacement arrow",
          caption: "1-D motion: x_i, x_f, and Δx on a number line." },
        { src: "/sample-visuals/G11-PHYS-002/distance-vs-displacement.svg",
          alt: "Curved path from A to B with straight displacement vector overlaid",
          caption: "Distance follows the path; displacement is the straight A→B vector." },
        { src: "/sample-visuals/G11-PHYS-002/average-vs-instantaneous-velocity.svg",
          alt: "x-t curve with secant for average velocity and tangent for instantaneous",
          caption: "Secant slope = average velocity; tangent slope = instantaneous." },
      ],
    },
  ],
  "G11-PHYS-002::s2": [
    {
      kind: "image-grid",
      heading: "Uniformly accelerated motion — the three graphs",
      items: [
        { src: "/sample-visuals/G11-PHYS-002/xt-uam.svg",
          alt: "x-t parabola for uniformly accelerated motion",
          caption: "x = vᵢt + ½at²  →  parabolic" },
        { src: "/sample-visuals/G11-PHYS-002/vt-uam.svg",
          alt: "v-t straight line with shaded area for displacement",
          caption: "v = vᵢ + at  →  linear; area under v = Δx" },
        { src: "/sample-visuals/G11-PHYS-002/at-uam.svg",
          alt: "a-t horizontal constant line",
          caption: "a = constant  →  horizontal line" },
      ],
    },
  ],
  "G11-PHYS-002::s3": [
    {
      kind: "image-grid",
      heading: "Free fall — vertical motion under gravity",
      items: [
        { src: "/sample-visuals/G11-PHYS-002/height-vs-time.svg",
          alt: "Height vs time for object thrown straight up",
          caption: "h(t) = vᵢt − ½gt²  with peak and impact marked." },
        { src: "/sample-visuals/G11-PHYS-002/velocity-vs-time.svg",
          alt: "Velocity vs time for object thrown straight up, crossing zero at peak",
          caption: "v(t) crosses zero at the peak — the sign change is the direction reversal." },
      ],
    },
  ],
  "G11-PHYS-002::s4": [
    {
      kind: "image",
      heading: "Projectile motion — trajectory",
      items: [
        { src: "/sample-visuals/G11-PHYS-002/trajectory.svg",
          alt: "Parabolic projectile trajectory at 60 degrees with peak and range",
          caption: "Launch at v = 20 m/s, θ = 60°. Range ≈ 35.3 m, peak ≈ 15.3 m." },
      ],
    },
    {
      kind: "image-grid",
      heading: "Velocity decomposition and key results",
      items: [
        { src: "/sample-visuals/G11-PHYS-002/velocity-decomposition.svg",
          alt: "Initial velocity decomposed into horizontal and vertical components",
          caption: "vₓ = v cos θ  (constant);  v_y = v sin θ  (changes under gravity)." },
        { src: "/sample-visuals/G11-PHYS-002/key-results.svg",
          alt: "Three result cards summarising time of flight, range, max height",
          caption: "Three closed-form results — symmetry of θ ↔ 90°−θ pairs gives equal range." },
      ],
    },
  ],
  "G11-PHYS-002::s5": [
    {
      kind: "image-grid",
      heading: "Reading the graphs — slope is velocity, area is displacement",
      items: [
        { src: "/sample-visuals/G11-PHYS-002/xt-with-tangent.svg",
          alt: "x-t curve with tangent line showing instantaneous velocity",
          caption: "Tangent slope on x-t = instantaneous velocity at that point." },
        { src: "/sample-visuals/G11-PHYS-002/vt-with-area.svg",
          alt: "v-t curve with shaded area under it showing displacement",
          caption: "Area under v-t between two times = displacement over that interval." },
      ],
    },
    {
      kind: "image",
      heading: "x – v – a relationships, side-by-side",
      items: [
        { src: "/sample-visuals/G11-PHYS-002/xt-vt-at-trio.svg",
          alt: "Three side-by-side plots showing x-t, v-t, a-t for UAM",
          caption: "Each graph is the slope of the one to its left, and the area of the one to its right." },
      ],
    },
    {
      kind: "image",
      heading: "The slope ↔ area chain",
      items: [
        { src: "/sample-visuals/G11-PHYS-002/slope-area-summary.svg",
          alt: "Three boxes for x, v, a connected by slope and area arrows",
          caption: "Slope moves you to the next derivative; area integrates back." },
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
      ) : block.kind === "video" ? (
        <div className="space-y-3">
          {block.items.map((item, i) => (
            <VisualVideo key={i} item={item} />
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

function VisualVideo({ item }: { item: VisualItem }) {
  const [playing, setPlaying] = useState(false);

  if (!playing) {
    return (
      <figure className="overflow-hidden rounded border border-emerald-200 bg-white">
        <button
          type="button"
          onClick={() => setPlaying(true)}
          aria-label={`Play video: ${item.alt}`}
          className="group relative flex w-full items-center justify-center gap-3 bg-gradient-to-br from-slate-900 to-slate-700 px-6 py-10 text-emerald-50 transition-colors hover:from-slate-800 hover:to-slate-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-400 focus-visible:ring-offset-2"
        >
          {item.poster && (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={item.poster}
              alt=""
              aria-hidden="true"
              className="absolute inset-0 h-full w-full object-cover opacity-50"
            />
          )}
          <span className="relative flex items-center gap-3">
            <PlayCircle
              className="h-12 w-12 text-emerald-300 transition-transform group-hover:scale-110"
              aria-hidden="true"
            />
            <span className="flex flex-col items-start">
              <span className="text-base font-semibold">Play video</span>
              <span className="flex items-center gap-2 text-xs text-emerald-200">
                <Film className="h-3 w-3" aria-hidden="true" />
                <span>{item.alt}</span>
                {item.duration && <span className="text-emerald-300">· {item.duration}</span>}
              </span>
            </span>
          </span>
        </button>
        {item.caption && (
          <figcaption className="border-t border-emerald-100 bg-emerald-50/40 px-2 py-1 text-xs text-emerald-900">
            {item.caption}
          </figcaption>
        )}
      </figure>
    );
  }

  return (
    <figure className="overflow-hidden rounded border border-emerald-200 bg-black">
      {/* eslint-disable-next-line jsx-a11y/media-has-caption */}
      <video
        controls
        autoPlay
        preload="metadata"
        className="h-auto w-full"
        src={item.src}
        poster={item.poster}
      >
        Your browser does not support embedded video.
      </video>
      {item.caption && (
        <figcaption className="border-t border-emerald-100 bg-emerald-50/40 px-2 py-1 text-xs text-emerald-900">
          {item.caption}
        </figcaption>
      )}
    </figure>
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
