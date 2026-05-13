# G11-MATH-003 Coordinate Geometry — Visual Catalogue

Fourth exemplar in the G11 Science track after `G11-MATH-001 Sets and Functions`,
`G11-PHYS-002 Kinematics`, and `G11-MATH-002 Advanced Algebra`.
Same convention: **Option 2 (per-example artifacts) is primary; Option 3 (Remotion video)
appears below the section graphics where high-leverage; Option 1 is fallback only.**

## What's here

```
G11-MATH-003_Coordinate_Geometry/
├── README.md                                ← this file
├── Option2_Catalogue/                       ← 16 standalone SVGs by section
│   ├── section-1-cartesian/                 (3 SVGs)
│   │   ├── cartesian-plane-quadrants.svg    four quadrants + sample points (3,2),(−4,1),(−2,−3),(4,−2)
│   │   ├── distance-formula.svg             A(1,2), B(7,10) → d = √(6² + 8²) = 10
│   │   └── midpoint-formula.svg             A(−2,1), B(6,7) → M = (2, 4)
│   ├── section-2-lines/                     (3 SVGs)
│   │   ├── slope-rise-over-run.svg          P(1,1), Q(5,4) → m = 3/4
│   │   ├── three-forms-of-a-line.svg        same line: y = 2x − 1 in three forms
│   │   └── parallel-and-perpendicular.svg   m = 1/2 vs m = −2  →  product = −1
│   ├── section-3-circle/                    (3 SVGs)
│   │   ├── circle-standard-form.svg         (x − 2)² + (y − 1)² = 9 → C(2,1), r = 3
│   │   ├── circle-general-to-standard.svg   complete the square → C(2,−3), r = 5
│   │   └── circle-through-three-points.svg  A(0,0), B(6,0), C(0,8) → centre (3,4), r = 5
│   ├── section-4-area/                      (3 SVGs)
│   │   ├── triangle-shoelace.svg            A(1,1), B(7,2), C(3,6) → Area = 14
│   │   ├── centroid-of-triangle.svg         A(1,2), B(7,4), C(4,9) → G(4, 5)
│   │   └── quadrilateral-shoelace.svg       (1,1)(6,2)(7,5)(2,6) → Area = 20
│   └── section-5-locus-conics/              (4 SVGs)
│       ├── locus-perpendicular-bisector.svg |PA| = |PB|  ⇒  x = 0
│       ├── parabola-focus-directrix.svg     y² = 4x  (focus (1,0), directrix x = −1)
│       ├── ellipse-two-foci.svg             x²/25 + y²/9 = 1  (a = 5, b = 3, c = 4)
│       └── hyperbola-two-foci.svg           x²/9 − y²/16 = 1  (a = 3, b = 4, c = 5)
└── Option3_Video/                           ← Remotion project, 1 composition
    ├── package.json
    ├── tsconfig.json
    ├── remotion.config.ts
    ├── src/
    │   ├── index.ts
    │   ├── Root.tsx                         registers `coordinate-geom-conic-sections`
    │   ├── theme.ts                         PAI charcoal + purple (shared)
    │   └── scenes/
    │       └── ConicSectionsScene.tsx       ~26 s, 5-phase morph
    └── public/                              (empty; assets are static SVGs from Catalogue)
```

Total: **16 SVGs + 1 video composition.**

## The video

| Composition ID | Suggested file | Length |
|---|---|---|
| `coordinate-geom-conic-sections` | `CoordinateGeom_ConicSections.mp4` | ~26 s |

5-phase animation. Left panel shows the double cone with the slicing plane; right panel
shows the resulting cross-section curve.

| Phase | What happens | Cross-section | Equation |
|---|---|---|---|
| 0 | Introduce the double cone | — | — |
| 1 | Plane perpendicular to the axis | **Circle** | x² + y² = r² |
| 2 | Tilt the plane (one nappe only) | **Ellipse** | x²/a² + y²/b² = 1 |
| 3 | Tilt parallel to a generator | **Parabola** | y² = 4 p x |
| 4 | Tilt past the slant — cuts both nappes | **Hyperbola** | x²/a² − y²/b² = 1 |

The cone, slicing plane, and right-panel curve all interpolate smoothly between phases.
Foci, directrix, vertices, and asymptotes appear as decorations on the relevant phases.

## Render

```bash
cd sample_content/g11-science/G11-MATH-003_Coordinate_Geometry/Option3_Video
bun install                          # one-time
bun run render:conics                # → ~/Downloads/CoordinateGeom_ConicSections.mp4
```

Or open Remotion Studio for live preview:

```bash
bun run studio
```

After rendering, copy MP4 into `web/public/sample-visuals/G11-MATH-003/` so the tutorial route serves it.

## Tutorial wiring (suggested)

| § | Section | SVGs | Video |
|---|---|---|---|
| s1 | Cartesian Plane — Points, Distance, Midpoint | 3 | — |
| s2 | Equations of a Straight Line — Slope and Standard Forms | 3 | — |
| s3 | The Circle — Standard and General Equations | 3 | — |
| s4 | Area of Geometric Figures Using Coordinates | 3 | — |
| s5 | Locus Problems and Conic Sections | 4 | CoordinateGeom_ConicSections.mp4 (0:26) |

Wire via `web/components/content/VisualSlot.tsx` — add entries to `VISUAL_MAP` keyed on
`G11-MATH-003` + section index. The video belongs to s5 because the conic-sections morph
is the most efficient form for showing how varying one parameter (the slicing-plane tilt)
produces all four conic curves; static SVGs already cover the locus + algebraic side.

## Math accuracy summary

Every diagram was verified by hand-computation:

- **Distance formula:** A(1, 2), B(7, 10) → |Δx| = 6, |Δy| = 8, d = √(36 + 64) = √100 = 10 ✓ (3-4-5 → 6-8-10).
- **Midpoint:** A(−2, 1), B(6, 7) → M = ((−2 + 6)/2, (1 + 7)/2) = (2, 4) ✓.
- **Slope:** P(1, 1), Q(5, 4) → m = (4 − 1)/(5 − 1) = 3/4 ✓.
- **Three forms (line):** through P(2, 3), Q(4, 7); slope (7 − 3)/(4 − 2) = 2; y-intercept = 3 − 2·2 = −1; ⇒ y = 2x − 1 ✓.
- **Parallel/perpendicular:** L₁ slope 1/2; L₂ slope 1/2 ⇒ parallel; L₃ slope −2 → 1/2 · (−2) = −1 ⇒ perpendicular ✓.
- **Circle standard:** (x − 2)² + (y − 1)² = 9 ⇒ centre (2, 1), r = 3; check (5, 1): (3)² + 0 = 9 ✓.
- **Circle general → standard:** x² + y² − 4x + 6y − 12 = 0 → (x − 2)² + (y + 3)² = 4 + 9 + 12 = 25 ⇒ centre (2, −3), r = 5 ✓.
- **Circle through 3 points:** A(0, 0), B(6, 0), C(0, 8); ⊥-bisector of AB is x = 3, of AC is y = 4 ⇒ centre (3, 4); radius = √(9 + 16) = 5; check |C − (3, 4)| = √(9 + 16) = 5 ✓.
- **Triangle area (shoelace):** A(1, 1), B(7, 2), C(3, 6) → ½|1·(2 − 6) + 7·(6 − 1) + 3·(1 − 2)| = ½|−4 + 35 − 3| = ½·28 = 14 ✓.
- **Centroid:** A(1, 2), B(7, 4), C(4, 9) → ((1 + 7 + 4)/3, (2 + 4 + 9)/3) = (12/3, 15/3) = (4, 5) ✓.
- **Quadrilateral area (shoelace):** P₁(1, 1), P₂(6, 2), P₃(7, 5), P₄(2, 6) → ½|1(2 − 6) + 6(5 − 1) + 7(6 − 2) + 2(1 − 5)| = ½|−4 + 24 + 28 − 8| = ½·40 = 20 ✓.
- **Locus (perpendicular bisector):** A(−3, 0), B(3, 0); set (x + 3)² + y² = (x − 3)² + y² → 12x = 0 → x = 0 ✓.
- **Parabola y² = 4x:** vertex (0, 0), focus (1, 0), directrix x = −1; check P(4, 4): |PF| = √(9 + 16) = 5; perpendicular distance to x = −1 is 4 − (−1) = 5 ✓.
- **Ellipse x²/25 + y²/9 = 1:** a = 5, b = 3, c² = a² − b² = 16, c = 4; foci (±4, 0); 2a = 10. Check P(0, 3): both distances = √(16 + 9) = 5; sum = 10 ✓.
- **Hyperbola x²/9 − y²/16 = 1:** a = 3, b = 4, c² = a² + b² = 25, c = 5; foci (±5, 0); 2a = 6. Check P(5, 16/3): |PF₁| = √(100 + 256/9) = √(1156/9) = 34/3; |PF₂| = √(0 + 256/9) = 16/3; difference = 18/3 = 6 ✓.

## What did NOT fit a static visual

All five sections lacked no representable concept; everything in scope is here. A few
sub-topics are intentionally deferred because the visual would be redundant or too
crowded:

- **Section formula (internal/external division of a segment in ratio m : n)** — the
  midpoint diagram already encodes the m = n = 1 case; a second diagram for arbitrary
  ratios would be near-identical visually but would need a four-step algebraic side
  panel. Better as a worked example in prose than a separate SVG.
- **Polar form of a line / normal form (x cos θ + y sin θ = p)** — visually almost
  identical to the standard-form line plus a perpendicular from the origin; the slope
  + three-forms diagram already conveys the geometric reading. Defer to text.
- **Reflection across a point or line** — composition of midpoint/distance ideas; the
  visual would replay information the existing SVGs already establish.
- **Tangent line to a circle from an external point** — needs a sub-derivation
  (length² = d² − r²) that the unit's tutorial covers in prose; a diagram repeats the
  circle-standard-form layout with one extra construction step.
- **Polar equations of conics (r = ed/(1 − e cos θ))** — out of scope at G11; sits
  in calculus-track conics. Mentioned only in the lesson's "looking ahead" footnote.
- **Director circle / auxiliary circle of an ellipse** — advanced loci that JEE-track
  students sometimes meet but the G11 syllabus treats as optional. Not represented.

These can be added later as section-N supplementary SVGs if reviewer feedback flags gaps.
