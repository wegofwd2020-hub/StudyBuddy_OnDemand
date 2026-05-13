# G11-MATH-004 Introduction to Calculus — Visual Catalogue

Companion to `G11-MATH-001 Sets and Functions` and `G11-MATH-002 Advanced Algebra`.
Same convention: **Option 2 (per-example artifacts) is primary; Option 3 (Remotion video)
appears below the section graphics where high-leverage; Option 1 is fallback only.**

## What's here

```
G11-MATH-004_Introduction_to_Calculus/
├── README.md                                  ← this file
├── Option2_Catalogue/                         ← 14 standalone SVGs by section
│   ├── section-1-limits/                      (3 SVGs)
│   │   ├── limit-approach.svg                  removable discontinuity at x = 1, lim = 2
│   │   ├── epsilon-delta.svg                   formal ε-δ definition with bands
│   │   └── one-sided-limits.svg                jump discontinuity, L⁻ = 2 ≠ L⁺ = 3
│   ├── section-2-derivatives/                 (3 SVGs)
│   │   ├── secant-to-tangent.svg               three secants converging to tangent on y = x²
│   │   ├── derivative-rules-table.svg          power, sum, product, quotient rules
│   │   └── derivative-as-rate.svg              s(t) = t² with v(t) = 2t side-by-side
│   ├── section-3-chain-rule/                  (2 SVGs)
│   │   ├── chain-rule-decomposition.svg        inner/outer arrow diagram, (x²+1)³
│   │   └── chain-rule-worked-examples.svg      (3x+1)⁴, sin(x²), √(x²+4)
│   ├── section-4-applications/                (3 SVGs)
│   │   ├── tangent-line.svg                    y = x³−3x at x = 2 → y = 9x − 16
│   │   ├── increasing-decreasing.svg           sign chart for f'(x) = 3x²−3
│   │   └── extrema-classification.svg          quartic with two min and one max
│   └── section-5-integration/                 (3 SVGs)
│       ├── riemann-sum.svg                     left-endpoint sum on [0, 2], n = 8, ∫ x² = 8/3
│       ├── antiderivative-family.svg           x²/2 + C (three translates)
│       └── ftc-visualization.svg               ∫₁² x² = 7/3 = F(2) − F(1)
└── Option3_Video/                             ← Remotion project, 1 composition
    ├── package.json
    ├── tsconfig.json
    ├── remotion.config.ts
    ├── src/
    │   ├── index.ts
    │   ├── Root.tsx                            registers `calculus-secant-to-tangent`
    │   ├── theme.ts                            PAI charcoal + purple (shared)
    │   └── scenes/
    │       └── SecantToTangentScene.tsx        ~27 s; Q slides toward P along y = x²
    └── public/                                 (empty; assets are static SVGs from Catalogue)
```

Total: **14 SVGs + 1 video composition.**

## The video

| Composition ID | Suggested file | Length |
|---|---|---|
| `calculus-secant-to-tangent` | `Calculus_SecantToTangent.mp4` | ~27 s |

Animated five-stage approach of Q to P on the parabola y = x²:

| Stage | Q's x-coord | Secant slope (q + 1) |
|---|---|---|
| 0 | 3.00 | 4.00 |
| 1 | 2.00 | 3.00 |
| 2 | 1.50 | 2.50 |
| 3 | 1.20 | 2.20 |
| 4 | 1.05 | 2.05 → tangent slope **2** |

The tangent line at P is rendered as a faint dashed orange line throughout and
brightens as Q approaches P. Outro caption reveals the derivative computation:
f'(1) = lim (q² − 1)/(q − 1) = lim (q + 1) = 2.

## Render

```bash
cd sample_content/g11-science/G11-MATH-004_Introduction_to_Calculus/Option3_Video
bun install                          # one-time
bun run render:secant                # → ~/Downloads/Calculus_SecantToTangent.mp4
```

Or open Remotion Studio for live preview:

```bash
bun run studio
```

After rendering, copy MP4 into `web/public/sample-visuals/G11-MATH-004/` so the tutorial route serves it.

## Tutorial wiring (suggested)

| § | Section | SVGs | Video |
|---|---|---|---|
| s1 | Limits — Foundation of Calculus | 3 | — |
| s2 | The Derivative — Definition and Rules | 3 | Calculus_SecantToTangent.mp4 (0:27) |
| s3 | Chain Rule and Composite Functions | 2 | — |
| s4 | Applications — Tangent Lines, Monotonicity, Extrema | 3 | — |
| s5 | Introduction to Integration | 3 | — |

Wire via `web/components/content/VisualSlot.tsx` — add entries to `VISUAL_MAP` keyed on
`G11-MATH-004` + section index. The video belongs to s2 because the secant-to-tangent
limit is the conceptual heart of the entire unit; static SVGs already cover the rules
and applications afterwards.

## Math accuracy summary

Every diagram was verified by hand-computation:

- **Limit approach:** lim_{x→1} (x² − 1)/(x − 1) = lim (x + 1) = 2 (factor and cancel).
- **Epsilon-delta:** straight-line example y = 0.5x + 1 with L = 2 at a = 2; for any ε > 0, choose δ ≤ 2ε.
- **One-sided limits:** f(x) = x + 1 (x < 1) and f(x) = 4 − x (x ≥ 1) gives L⁻ = 2, L⁺ = 3 ≠ ⇒ DNE.
- **Secant-to-tangent:** for y = x² at P = (1, 1), secant slope from P to Q = (q, q²) is exactly q + 1; limit q → 1 gives 2 = f'(1). The displayed slopes 4, 3, 2.5 follow.
- **Derivative rules:** power rule d/dx(x⁵) = 5x⁴; quotient (x/(x+1))' = ((x+1) − x)/(x+1)² = 1/(x+1)². Product (x² sin x)' = 2x sin x + x² cos x.
- **Derivative as rate:** s(t) = t² ⇒ s'(t) = 2t; at t = 2: s = 4, v = 4.
- **Chain rule decomposition:** y = (x² + 1)³, f(u) = u³, g(x) = x² + 1; dy/dx = 3(x² + 1)² · 2x = 6x(x² + 1)².
- **Worked chain-rule examples:**
  - d/dx (3x + 1)⁴ = 4(3x + 1)³ · 3 = 12(3x + 1)³.
  - d/dx sin(x²) = cos(x²) · 2x = 2x cos(x²).
  - d/dx √(x² + 4) = (1/2)(x² + 4)^(−1/2) · 2x = x / √(x² + 4).
- **Tangent at x = 2 of f(x) = x³ − 3x:** f(2) = 8 − 6 = 2; f'(x) = 3x² − 3 ⇒ f'(2) = 9; tangent y = 2 + 9(x − 2) = 9x − 16.
- **Increasing / decreasing:** f'(x) = 3x² − 3 = 3(x − 1)(x + 1); zeros at x = ±1; f' > 0 on (−∞, −1) ∪ (1, ∞); f' < 0 on (−1, 1). Local max (−1, 2), local min (1, −2).
- **Extrema (quartic):** f(x) = x⁴/4 − x² + 1; f'(x) = x³ − 2x = x(x² − 2) ⇒ x = 0, ±√2. f''(x) = 3x² − 2; f''(0) = −2 < 0 (max), f''(±√2) = 4 > 0 (mins). Values f(0) = 1, f(±√2) = 0.
- **Riemann sum:** left sum L₈ on [0, 2] for f(x) = x², Δx = 0.25; sum of f at left endpoints 0, 0.25, …, 1.75 is 8.75; L₈ = 0.25 · 8.75 = 2.1875. Exact ∫₀² x² dx = 8/3 ≈ 2.667.
- **Antiderivative family:** ∫ x dx = x²/2 + C; three translates with C = −1, 0, 2 share the same slope at every x.
- **FTC:** ∫₁² x² dx = [x³/3]₁² = 8/3 − 1/3 = 7/3 ≈ 2.333.

## What did NOT fit a static visual

- **Squeeze theorem** — the standard sin x / x example needs three superimposed curves and is harder to read at this size; deferred to lecture audio with one of the limit visuals as backdrop.
- **Implicit differentiation** — algebraically distinct but visually identical to a tangent-line drawing; no new geometric content to add.
- **Substitution rule for integrals** — manipulation rather than geometry; covered in prose alongside the antiderivative family.

These can be added later as section-N supplementary SVGs if reviewer feedback flags gaps.
