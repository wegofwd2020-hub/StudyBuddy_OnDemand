# MEMO — G12-PHYS-005 Optics

> Last Wave-2 unit. Closes the foundational + extensions epic (#326) for the visual library.

## Status

- **Phase 1 (Option 2 catalogue):** ✅ 13 SVGs + 13 sidecars shipped
- **Phase 2 (Option 3 Remotion):** ✅ 2 clips — `Optics_Interference.mp4` (66.6 MB / 24 s), `Optics_SingleSlitDiffraction.mp4` (3.2 MB / 24 s)
- **Phase 3 (eval + library promotion):** ✅ 13 sidecars promoted; 3 known-positive eval records (`eval-078` / `079` / `080`)

## Phase 1 reflections

| Section | Visuals |
|---|---|
| `section-1-reflection` | `law-of-reflection`, `concave-mirror-ray-diagram`, `convex-mirror-ray-diagram` |
| `section-2-refraction` | `snells-law`, `total-internal-reflection`, `prism-dispersion` |
| `section-3-lenses` | `convex-lens-image-formation`, `concave-lens-image-formation`, `lens-formula-and-magnification` |
| `section-4-wave-optics` | `youngs-double-slit-geometry`, `interference-fringe-pattern`, `single-slit-diffraction-pattern`, `interference-vs-diffraction` |

This unit ships the **ray-diagram SVG generator** primitives that retroactively cover G10-SCI-002 and G8-SCI-002. New high-leverage primitives:

1. `rayArrow(x1,y1, x2,y2, color, width, dash)` — arrow-tipped ray segment.
2. `normalLine(x1,y1, x2,y2, color)` — the canonical dashed perpendicular at every refraction/reflection diagram.
3. `angleArc(cx,cy, r, ang1, ang2, color)` — angle-arc between two rays at a vertex. Six of the 13 figures use it.
4. **Optics-specific palette**: ray=red, refracted=purple, normal=slate-dashed, surface=black-with-hatching. Locks in the convention for downstream optics units.

### What was repetitive

1. **Ray + Normal + Angle-arc trio** — Snell's law, law-of-reflection, total-internal-reflection all share the same skeleton. **Recommendation for #320:** `<RayDiagramVertex incidentAngle refractedAngle showNormal showAngles />`.
2. **Lens/mirror with three-rays-and-image setup** — convex/concave mirror + convex/concave lens all use the same "object → 3 principal rays → image" template. **Recommendation:** `<LensMirrorRayDiagram type='convex-lens' | 'concave-lens' | 'concave-mirror' | 'convex-mirror' object={...} />`.
3. **Two-medium stacked stripes for refraction** — same shape as the chemistry stacked-orbital-energy-bands and biology stacked-microscopy-views.

### What needed human judgment

1. **Mirror arc curvature** — the concave/convex mirror SVG arc shape is hand-tuned via SVG `<path d="M ... A r r 0 0 sweep">`. The visual sweetspot for "this is clearly a mirror, not a circle" is fragile.
2. **Convex/concave lens shape** — biconvex lens drawn as a vertical ellipse; biconcave as two outward-curving paths meeting at a thin centre. The biconcave path-data was the trickiest thing in the catalogue; took multiple iterations to land on a shape that reads as "diverging lens" rather than "weird mask".
3. **Three principal rays in lens diagrams** — a deliberate choice to draw all three (parallel→F, through-F→parallel, through-centre) so the image-formation logic is visible, even though 2 rays are sufficient.

## Phase 2 reflections — Remotion clips

### `optics-interference` (66.6 MB, 24 s)

Two coherent point sources A and B emit expanding circular wavefronts at the same period. The pattern of fringes builds up on a vertical screen on the right, computed correctly via path-difference + cos² intensity at each y on the screen. Δy between adjacent maxima is annotated at the end.

**Note**: 66.6 MB output is unusually large because the scene contains many concurrent wavefront circles (~30 from each source at peak), each rendered as a stroked path. The high-detail SVG re-encodes poorly into h264 keyframes, so the file is large. Future versions could either (a) limit visible wavefronts to the 8-10 most recent or (b) bake the wavefront pattern as a single combined SVG path instead of N circles.

### `optics-single-slit-diffraction` (3.2 MB, 24 s)

A vertical slit on the left whose width sweeps from 1λ to 4λ over 12 seconds. Light fans into a triangular wedge after the slit; on the right, a sinc²-shaped intensity profile builds and updates per frame. Watch the central peak narrow as the slit widens — the inverse relationship is visible in real time.

Both clips lift the `cumulativePhase`-style "parameter sweep over time" pattern from earlier physics + chemistry units.

## Phase 3

| eval id | section title | expected_entry_id |
|---|---|---|
| `eval-078` | How Light Bounces Off a Mirror | `physics-optics-law-of-reflection` |
| `eval-079` | Light Bending into a Denser Medium | `physics-optics-snells-law` |
| `eval-080` | What Happens When Light Squeezes Through a Narrow Gap | `physics-optics-single-slit-diffraction-pattern` |

Eval-080 is interesting — describes both the cause (slit narrower than wavelength) and the effect (central + side peaks) without using "diffraction" verbatim. Tests whether the resolver is keyword-anchored vs semantic.

13/13 G12-PHYS-005 sidecars seeded; 144/144 library rows total, 0 NULL embeddings.

## Time budget

| Phase | Issue estimate | Actual |
|---|---|---|
| Phase 1 | ~1 day | ~75 min |
| Phase 2 | ~0.5 day | ~35 min (1 quick-fix iteration on a function-name conflict) |
| Phase 3 | (rolled in) | ~12 min |

Total: ~2 h 2 m vs. 2-day issue estimate.

## Wave-2 closing summary

| Unit | Time | Notes |
|---|---|---|
| #332 (G7 atoms) | ~1 h | first Wave-2; new heatmap primitive |
| #333 (G10 organic) | ~1 h 27 m | heaviest catalogue (16 SVGs); skeletal-structure primitives |
| #334 (G11 derivatives) | ~1 h 27 m | tangent-emergence Remotion |
| #335 (G8 waves) | ~55 m | smallest unit; heavy reuse |
| #336 (G12 optics) | ~2 h 2 m | last unit; ray-diagram primitives + 2 wave-optics Remotion clips |
| **Wave-2 total** | **~6 h 51 m** | vs. ~9 days FTE estimated; ~10× compression |

## Wave 1 + 2 grand total

10 issues closed. 5 primitive classes opened (oscillations, kinematics, chemistry, biology, engineering-circuits) + 5 same/adjacent-class extensions. **144 visual_library_entries** with non-NULL embeddings. **80 known-positive resolver eval records** (15 from Wave 1 + 15 from Wave 2 across 5 units of 3 each). **9 Remotion clips** rendered. **~14 h 56 m total wall time** vs. ~19 days FTE estimated.

The visual library is now ready to consume by the resolver pipeline (#323) and the production promotion CI (#322). #320 has 30+ shared-component primitives flagged across the wave 1+2 MEMOs ready to lift into `pipeline/visual_templates/`.

---
*Author: broker. Updated 2026-05-08 (all phases complete; #336 ready to close — closes Wave 2 of epic #326).*
