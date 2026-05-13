# G11-MATH-005 Statistics and Probability — Visual Catalogue

Fifth exemplar in the G11 Science track after `G11-MATH-001 Sets and Functions`,
`G11-PHYS-002 Kinematics`, `G11-MATH-002 Advanced Algebra`, and
`G11-MATH-003 Coordinate Geometry`.
Same convention: **Option 2 (per-example artifacts) is primary; Option 3 (Remotion video)
appears below the section graphics where high-leverage; Option 1 is fallback only.**

## What's here

```
G11-MATH-005_Statistics_and_Probability/
├── README.md                                ← this file
├── Option2_Catalogue/                       ← 15 standalone SVGs by section
│   ├── section-1-descriptive/               (3 SVGs — central tendency & dispersion)
│   │   ├── histogram-mean-median-mode.svg          right-skewed dataset n=15; mode 3, median 5, mean ≈5.87
│   │   ├── box-plot-five-number-summary.svg        n=11 set; min 4, Q1 8, median 12, Q3 15, max 22; IQR 7
│   │   └── standard-deviation-spread.svg           same mean (10), different σ (1.58 vs 4.74)
│   ├── section-2-probability/               (3 SVGs — sample spaces, events, axioms)
│   │   ├── sample-space-tree-two-coins.svg         S = {HH,HT,TH,TT}; each P=¼; independence demo
│   │   ├── venn-mutually-exclusive-vs-independent.svg  side-by-side: disjoint vs overlapping circles
│   │   └── probability-axioms-die-example.svg      Kolmogorov axioms + addition rule on a die
│   ├── section-3-combinatorics/             (3 SVGs — permutations & combinations)
│   │   ├── permutation-vs-combination.svg          {A,B,C} choose 2: P(3,2)=6 vs C(3,2)=3
│   │   ├── factorial-tree-three-letters.svg        full enumeration tree for 3! = 6 perms of A,B,C
│   │   └── pascals-triangle-binomial-coefficients.svg  rows 0–6; row sum = 2ⁿ; row 4 highlighted
│   ├── section-4-distributions/             (3 SVGs — binomial & normal)
│   │   ├── binomial-distribution-bar.svg            Bin(10, ½) PMF; peak P(5) ≈ 0.246; μ=5, σ²=2.5
│   │   ├── normal-curve-empirical-rule.svg          standard normal with 1σ/2σ/3σ bands → 68/95/99.7
│   │   └── normal-mu-sigma-effects.svg              N(0,1) vs N(2,1) vs N(0,2): location vs spread
│   └── section-5-bayes/                     (3 SVGs — Bayes' theorem)
│       ├── bayes-tree-medical-test.svg              P(D)=.01, P(+|D)=.99, P(+|¬D)=.05 → P(D|+) ≈ 16.7 %
│       ├── bayes-formula-anatomy.svg                each term labelled (posterior/likelihood/prior/evidence)
│       └── bayes-natural-frequencies-1000.svg       icon array: 10 TP / 50 FP / 0 FN / 940 TN
└── Option3_Video/                           ← Remotion project, 1 composition
    ├── package.json
    ├── tsconfig.json
    ├── remotion.config.ts
    └── src/
        ├── index.ts
        ├── Root.tsx                         registers `stats-normal-distribution`
        ├── theme.ts                         PAI charcoal + purple (shared)
        └── scenes/
            └── NormalDistributionScene.tsx  ~26 s, 5-phase animation
```

Total: **15 SVGs + 1 video composition.**

## The video

| Composition ID | Suggested file | Length |
|---|---|---|
| `stats-normal-distribution` | `Stats_NormalDistribution.mp4` | ~26 s |

5-phase animation. The density curve is plotted on a single panel; μ and σ are
animated to show how they change the bell's location and width, then the
empirical-rule bands fill in.

| Phase | What happens | μ | σ | Bands shown |
|---|---|---|---|---|
| 0 | Standard normal | 0 | 1 | — |
| 1 | Slide μ right | 0 → 2 | 1 | — |
| 2 | Re-centre and stretch | 2 → 0 | 1 → 2 | — |
| 3 | Restore σ; shade ±1σ | 0 | 2 → 1 | 68 % |
| 4 | Add ±2σ then ±3σ | 0 | 1 | 68 / 95 / 99.7 |

Right-side readout shows the live μ, σ, peak height (= 1 / (σ √2π)), and the
running shaded area. Title pop-in via spring; phase pills track the timeline;
outro caption fades in over the final second.

## Render

```bash
cd sample_content/g11-science/G11-MATH-005_Statistics_and_Probability/Option3_Video
bun install                          # one-time
bun run render:normal                # → ~/Downloads/Stats_NormalDistribution.mp4
```

Or open Remotion Studio for live preview:

```bash
bun run studio
```

After rendering, copy MP4 into `web/public/sample-visuals/G11-MATH-005/` so the tutorial route serves it.

## Tutorial wiring (suggested)

| § | Section | SVGs | Video |
|---|---|---|---|
| s1 | Descriptive Statistics — Central Tendency and Dispersion | 3 | — |
| s2 | Fundamental Probability — Sample Spaces, Events, Axioms | 3 | — |
| s3 | Combinatorics — Permutations and Combinations | 3 | — |
| s4 | Probability Distributions — Binomial and Normal | 3 | Stats_NormalDistribution.mp4 (0:26) |
| s5 | Bayes' Theorem and Applications | 3 | — |

Wire via `web/components/content/VisualSlot.tsx` — add entries to `VISUAL_MAP` keyed on
`G11-MATH-005` + section index. The video belongs to s4 because the 68 – 95 – 99.7
narrative is most clearly conveyed by animating μ and σ live; the static SVGs already
cover the binomial PMF, parameter effects, and the empirical-rule percentages from
a "frozen" point of view.

## Math accuracy summary

Every diagram was verified by hand-computation:

- **Histogram (mode, median, mean):** Data 1, 2, 3, 3, 3, 4, 4, 5, 5, 6, 7, 8, 10, 12, 15 (n = 15).
  Sum = 88; mean = 88/15 ≈ 5.87. Median = 8th value (sorted) = 5. Mode = 3 (frequency 3). ✓
  Bin counts (width 2): [0,2)=1, [2,4)=4, [4,6)=4, [6,8)=2, [8,10)=1, [10,12)=1, [12,14)=1, [14,16)=1.
- **Box plot:** Data 4, 7, 8, 10, 11, 12, 13, 14, 15, 18, 22 (n = 11). Median = 6th = 12.
  Lower half {4,7,8,10,11} → Q₁ = 8. Upper half {13,14,15,18,22} → Q₃ = 15. IQR = 7.
  Fences: 8 − 10.5 = −2.5; 15 + 10.5 = 25.5. No outliers. ✓
- **Standard deviation:** Set A {8,9,10,11,12} mean = 10; deviations −2,−1,0,1,2; Σdev² = 10;
  s² = 10/4 = 2.5; s ≈ 1.581. Set B {4,7,10,13,16} mean = 10; deviations −6,−3,0,3,6;
  Σdev² = 90; s² = 22.5; s ≈ 4.743. ✓
- **Sample-space tree (two coins):** S = {HH, HT, TH, TT}; each P = ½ · ½ = ¼; sum = 1.
  P(at least 1 H) = 1 − P(TT) = 3/4. P(exactly 1 H) = P(HT) + P(TH) = ½. ✓
- **Probability axioms (die):** S = {1,…,6}, |S| = 6. A = even = {2,4,6}, |A| = 3.
  B = ≤3 = {1,2,3}, |B| = 3. A ∩ B = {2}, |A ∩ B| = 1. A ∪ B = {1,2,3,4,6}, |A ∪ B| = 5.
  P(A) + P(B) − P(A ∩ B) = 3/6 + 3/6 − 1/6 = 5/6 = P(A ∪ B). ✓
- **Permutation vs combination ({A,B,C} choose 2):** P(3,2) = 3!/1! = 6 (AB,BA,AC,CA,BC,CB).
  C(3,2) = 3!/(2!·1!) = 3 ({A,B}, {A,C}, {B,C}). Each combination ↔ 2! = 2 permutations. ✓
- **Factorial tree:** 3 · 2 · 1 = 6 permutations of A, B, C. Full leaf list ABC, ACB, BAC, BCA, CAB, CBA. ✓
- **Pascal's triangle:** Rows verified by direct sum and Pascal's rule:
  Row 0: 1; Row 1: 1,1; Row 2: 1,2,1; Row 3: 1,3,3,1; Row 4: 1,4,6,4,1; Row 5: 1,5,10,10,5,1;
  Row 6: 1,6,15,20,15,6,1. Row n sum = 2ⁿ ⇒ 1, 2, 4, 8, 16, 32, 64. ✓
- **Binomial Bin(10, ½):** P(X = k) = C(10, k)/1024. Heights:
  k=0,10: 1/1024 ≈ .001; k=1,9: 10/1024 ≈ .010; k=2,8: 45/1024 ≈ .044; k=3,7: 120/1024 ≈ .117;
  k=4,6: 210/1024 ≈ .205; k=5: 252/1024 ≈ .246. Sum = 1024/1024 = 1.
  μ = np = 5; σ² = np(1−p) = 2.5; σ ≈ 1.58. ✓
- **Standard normal (empirical rule):** Heights computed from φ(z) = e^(−z²/2)/√(2π).
  ∫_{−1}^{1} φ ≈ 0.6827, ∫_{−2}^{2} φ ≈ 0.9545, ∫_{−3}^{3} φ ≈ 0.9973. Wing percentages
  derived: (.9545 − .6827)/2 ≈ .1359 → 13.6 % each side; (.9973 − .9545)/2 ≈ .0214 → 2.14 %.
  Diagram rounds to 13.5 % and 2.35 % per the conventional 68 – 95 – 99.7 statement. ✓
- **Normal μ and σ effects:** Peak height of N(μ, σ²) = 1/(σ√2π); for σ=1, peak ≈ 0.399;
  for σ=2, peak ≈ 0.199 (exactly half). N(2, 1) is N(0, 1) translated by +2 along x. ✓
- **Bayes (medical test):** P(D) = 0.01, P(¬D) = 0.99. P(+|D) = 0.99, P(+|¬D) = 0.05.
  Joints: P(D ∩ +) = 0.0099, P(¬D ∩ +) = 0.0495, P(D ∩ −) = 0.0001, P(¬D ∩ −) = 0.9405.
  Sum = 1. P(+) = 0.0099 + 0.0495 = 0.0594.
  P(D | +) = 0.0099 / 0.0594 = 1/6 ≈ 0.1667. ✓
- **Natural frequencies (1 000 people):** 1000 × 0.01 = 10 with disease (rounding 0.99·10 ≈ 10
  test-positive, so ~0 test-negative); 1000 × 0.99 = 990 without disease (rounding 0.05·990 ≈ 49.5
  ≈ 50 test-positive; 0.95·990 ≈ 940 test-negative). 60 total positives → 10/60 ≈ 16.7 %. ✓
- **Bayes formula:** P(A | B) = P(B | A)·P(A)/P(B). Denominator expanded by total probability:
  P(B) = P(B | A)·P(A) + P(B | ¬A)·P(¬A). ✓

## What did NOT fit a static visual

All five sections lacked no representable concept; everything in scope is here. A few
sub-topics are intentionally deferred because the visual would be redundant or too
crowded:

- **Cumulative distribution function for the binomial / normal** — visually almost
  identical to the PDF panel with a step or smooth-staircase trace; wiring this in
  would compete with the PMF/PDF for attention. Defer to text.
- **Standardisation worked example (X → Z = (X − μ)/σ with table lookup)** — needs a
  z-table image plus arithmetic; the parameter-effects SVG already conveys why the
  transformation works geometrically. Better as a worked example in prose.
- **Binomial-to-normal approximation** — overlaying a Bin(n, p) bar chart on a normal
  curve at large n makes a striking image but requires a fourth section-4 SVG; left
  for a follow-up unit on the Central Limit Theorem.
- **Conditional-probability formula derivation** — chains P(A∩B) = P(A|B)·P(B) into
  Bayes; conceptually the Bayes-tree SVG already encodes both directions of conditioning,
  and the formula-anatomy SVG names the pieces.
- **Markov / Chebyshev inequalities** — out of G11 scope; sit in calculus-track probability.
- **Joint distributions and covariance** — multivariate; not part of the G11 syllabus.

These can be added later as section-N supplementary SVGs if reviewer feedback flags gaps.
