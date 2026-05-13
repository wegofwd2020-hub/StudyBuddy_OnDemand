# G11-MATH-002 Advanced Algebra — Visual Catalogue

Third exemplar after `G11-MATH-001 Sets and Functions` and `G11-PHYS-002 Kinematics`.
Same convention: **Option 2 (per-example artifacts) is primary; Option 3 (Remotion video)
appears below the section graphics where high-leverage; Option 1 is fallback only.**

## What's here

```
G11-MATH-002_Advanced_Algebra/
├── README.md                                ← this file
├── Option2_Catalogue/                       ← 15 standalone SVGs by section
│   ├── section-1-polynomials/               (3 SVGs)
│   │   ├── polynomial-classification.svg
│   │   ├── factor-theorem.svg
│   │   └── synthetic-division.svg
│   ├── section-2-rational/                  (3 SVGs)
│   │   ├── domain-restrictions.svg
│   │   ├── simplification-flow.svg
│   │   └── common-denominator.svg
│   ├── section-3-systems/                   (3 SVGs)
│   │   ├── linear-system-graphical.svg      y = 2x − 1  ∩  y = −x + 5  →  (2, 3)
│   │   ├── substitution-method.svg
│   │   └── nonlinear-system.svg             y = x²  ∩  y = x + 2
│   ├── section-4-quadratics/                (3 SVGs)
│   │   ├── parabola-anatomy.svg             f(x) = x² − 2x − 3 (three forms)
│   │   ├── vertex-form-transform.svg        translation by (h, k)
│   │   └── completing-the-square.svg        geometric algebra-tiles view
│   └── section-5-inequalities/              (3 SVGs)
│       ├── sign-analysis.svg                (x + 1)(x − 2)(x − 4) > 0
│       ├── test-point-method.svg            x² − 4x + 3 ≤ 0
│       └── rational-inequality.svg          (x − 1)/(x − 3) ≥ 0
└── Option3_Video/                           ← Remotion project, 1 composition
    ├── package.json
    ├── tsconfig.json
    ├── remotion.config.ts
    ├── src/
    │   ├── index.ts
    │   ├── Root.tsx                         registers `advanced-algebra-quadratic-transform`
    │   ├── theme.ts                         PAI charcoal + purple (shared)
    │   └── scenes/
    │       └── QuadraticTransformScene.tsx  ~26 s, 5-step morph
    └── public/                              (empty; assets are static SVGs from Catalogue)
```

Total: **15 SVGs + 1 video composition.**

## The video

| Composition ID | Suggested file | Length |
|---|---|---|
| `advanced-algebra-quadratic-transform` | `AdvancedAlgebra_QuadraticTransform.mp4` | ~26 s |

Animated 5-step morph:

| Step | Equation | Transformation |
|---|---|---|
| 0 | y = x² | base parabola |
| 1 | y = (x − 3)² | shift right by 3 |
| 2 | y = 2(x − 3)² | vertical stretch ×2 |
| 3 | y = −2(x − 3)² | reflect across x-axis |
| 4 | y = −2(x − 3)² + 5 | shift up by 5 → vertex (3, 5) |

The base curve persists as a faint dashed reference behind every step.

## Render

```bash
cd sample_content/g11-science/G11-MATH-002_Advanced_Algebra/Option3_Video
bun install                          # one-time
bun run render:transform             # → ~/Downloads/AdvancedAlgebra_QuadraticTransform.mp4
```

Or open Remotion Studio for live preview:

```bash
bun run studio
```

After rendering, copy MP4 into `web/public/sample-visuals/G11-MATH-002/` so the tutorial route serves it.

## Tutorial wiring (suggested)

| § | Section | SVGs | Video |
|---|---|---|---|
| s1 | Polynomial Operations & Factor Theorem | 3 | — |
| s2 | Rational Expressions | 3 | — |
| s3 | Systems of Equations | 3 | — |
| s4 | Quadratic Functions | 3 | AdvancedAlgebra_QuadraticTransform.mp4 (0:26) |
| s5 | Polynomial & Rational Inequalities | 3 | — |

Wire via `web/components/content/VisualSlot.tsx` — add entries to `VISUAL_MAP` keyed on
`G11-MATH-002` + section index. The video belongs to s4 because it is the most efficient
form for showing a multi-step parameter transformation; static SVGs already cover the
algebraic side of the same section.

## Math accuracy summary

Every diagram was verified by hand-computation:

- **Factor theorem:** P(x) = x³ − 2x² − 5x + 6 has roots −2, 1, 3 (verified: P(−2) = −8 − 8 + 10 + 6 = 0; P(1) = 1 − 2 − 5 + 6 = 0; P(3) = 27 − 18 − 15 + 6 = 0).
- **Synthetic division:** dividing the same cubic by (x − 3) yields quotient x² + x − 2, remainder 0; that quadratic factors to (x + 2)(x − 1).
- **Linear system:** y = 2x − 1 and y = −x + 5 → 3x = 6 → (2, 3).
- **Nonlinear system:** y = x² and y = x + 2 → x² − x − 2 = (x − 2)(x + 1) = 0 → (2, 4) and (−1, 1).
- **Parabola anatomy:** f(x) = x² − 2x − 3 = (x − 1)² − 4 = (x − 3)(x + 1); vertex (1, −4), x-int −1 and 3, y-int −3.
- **Sign analysis:** (x + 1)(x − 2)(x − 4) > 0 → solution (−1, 2) ∪ (4, ∞).
- **Rational inequality:** (x − 1)/(x − 3) ≥ 0 → solution (−∞, 1] ∪ (3, ∞), with x = 3 excluded.

## What did NOT fit a static visual

None of the five sections lacked a representable concept; everything in scope is here. A few
sub-topics are intentionally deferred to lecture audio rather than diagrams because the
visual would be redundant or too crowded:

- **Polynomial long division** — algebraically distinct from synthetic division but visually
  almost identical. Synthetic-division SVG carries the load; long division can be footnoted
  in prose.
- **Rational equation solving (clear-the-denominator step)** — already implicit in the
  simplification + common-denominator pair; a third SVG would duplicate.
- **Systems via elimination** — substitution diagram covers the same algebraic moves; a
  parallel elimination diagram would add clutter without new insight.

These can be added later as section-N supplementary SVGs if reviewer feedback flags gaps.
