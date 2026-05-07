# Demonstration Options — Sets and Functions

> Research artifact. Three candidate approaches for turning the worked examples
> in `Sets_and_Functions.md` into visual / interactive demonstrations, chosen so
> we can compare presentation styles before committing one to the product.

## Visual targets in the source content

Before picking an approach, here's what the content naturally wants visualised. Each row is a real example or section in `Sets_and_Functions.md`.

| Section | Example | Natural visual form |
|---|---|---|
| 1.5 Set Operations | Worked Example 1 — $A \cup B$, $A \cap B$, $A \setminus B$, $A^c$ | Venn diagram with shading per operation |
| 1.4 Power Sets | Worked Example 2 — $\mathcal{P}(\{a,b,c\})$, $\lvert\mathcal{P}(S)\rvert = 2^{\lvert S\rvert}$ | Lattice / Hasse diagram of subsets |
| 2.5 Inj / Surj / Bij | Worked Example 1 — arrow diagrams $R_1$…$R_4$ | Arrow diagram between two finite sets |
| 2.5 Inj / Surj / Bij | All three definitions | Side-by-side arrow-diagram comparison (one inj, one surj, one bij) |
| 2.4 Vertical Line Test | Definition | Plot of a function vs. a non-function (e.g. $y^2 = x$) with a vertical sweep line |
| 3.2–3.4 Polynomial / Rational / Abs | Various | Function plot with annotated zeroes, asymptotes, intercepts |
| 3.5 Piecewise | $g(x) = \begin{cases}x^2,\;2x{+}1,\;10{-}x\end{cases}$ | Plot showing each rule in its own colour, with closed/open dots at boundaries |
| 3.7 Even / Odd | Worked Example 2 — $h$, $k$, $p$ | Three plots showing $y$-axis symmetry, origin symmetry, neither |
| 4.1 Composition | Worked Example 1 — $g \circ f$ vs. $f \circ g$ | Block-diagram pipeline showing input → $f$ → $g$ → output |
| 4.3 Inverse | $f$ and $f^{-1}$ relationship | Two curves on the same axes plus the reflecting line $y = x$ |
| 5.1 Transformations | $y = -2(x+3)^2 + 5$ | Animation: base parabola progressively shifted/stretched/reflected/lifted |
| 5.3 Projectile | $h(t) = -4.9t^2 + 14t + 2$ | Animated parabola with a moving dot tracking $(t, h(t))$ |

That's at least twelve distinct visual idioms to evaluate.

---

## Option 1 — Single interactive HTML page

**Deliverable:** `sample_content/g11-science/G11-MATH-001_Sets_and_Functions/Demos.html`

A single self-contained HTML file. Each worked example renders with a different library so the comparison happens on one screen, scrolled side-by-side.

| Visual target | Library |
|---|---|
| Math typography | KaTeX (CDN, already proven by the existing `.html` export) |
| Function plots | **Plotly.js** — interactive (hover, zoom, pan), good defaults, large API surface |
| Venn diagrams | inline **SVG** with `<circle>` + alpha-blended fills — no library |
| Arrow / mapping diagrams | **Mermaid** flowchart (`graph LR`) |
| Block-diagram for composition | Mermaid flowchart |
| Projectile / transformation animation | Vanilla JS + `<canvas>` or animated SVG (no library) |
| Reflection-across-$y{=}x$ inverse | Plotly with two traces and a $y{=}x$ overlay |

**Strengths**
- One file, no install, opens in any browser
- Five rendering approaches visible together — the comparison is the point
- Cheap to throw away, cheap to extend
- Stays in version control alongside the source content

**Weaknesses**
- Not as polished as a video for sharing externally
- Plotly bundle is ~3.5 MB if pulled from CDN (acceptable for research, not for production)
- Animations are vanilla-JS rather than a real animation framework (good enough for demo, not for product)

**Effort:** ~20 minutes to first draft.

**Best when** the goal is to *evaluate* presentation styles before picking one. Which is the case here.

---

## Option 2 — Per-example artifact catalogue

**Deliverable:** a folder per example, each with the most appropriate tool's output.

| Visual target | Tool | Output type |
|---|---|---|
| Function graphs | **Desmos** or **GeoGebra** embed | iframe URL or `.ggb` file |
| Venn / set diagrams | hand-authored **SVG** or `venn.js` | `.svg` |
| Arrow diagrams | **Graphviz** (`dot -Tsvg`) | `.svg` |
| Animations (projectile, transformations) | **Manim** | `.mp4` |
| Math typography | KaTeX | inside the wrapping HTML |

**Strengths**
- Highest visual quality per example — the right tool for each one
- Outputs are reusable: a Desmos link, a Manim mp4, an SVG can each ship into the product directly
- Good representation of what "best in class" looks like for each category

**Weaknesses**
- Five tools to install (Manim alone needs a Python + LaTeX + Cairo stack)
- Heaviest of the three options
- Comparison between approaches is harder because outputs live in separate viewers
- Python conflicts with the project rule "TypeScript always; never Python unless explicitly approved" — Manim is a Python package, so this option needs explicit sign-off

**Effort:** 2–4 hours, mostly install + tooling.

**Best when** you've already picked the presentation idiom for each visual category and you want polished one-off artifacts.

---

## Option 3 — Remotion-rendered explainer video

**Deliverable:** `~/Downloads/Sets_and_Functions_Demo.mp4` rendered via the existing **Remotion** skill.

A scripted walkthrough — narration + animated slides — that walks the viewer through five or six worked examples in sequence.

**Strengths**
- Highest production value, very shareable
- Animations and timing are precisely controlled (it's React → MP4)
- Already a first-class skill in the PAI tooling
- Works as marketing / demo material as well as research

**Weaknesses**
- Linear — no side-by-side comparison; the viewer sees one rendering choice at a time
- Slowest of the three; rendering alone is CPU-intensive
- Wrong fit for "research which approach to use" because the artifact bakes the answer in
- Better fit for "show students" or "show investors" than for internal evaluation

**Effort:** half-day for a four-minute demo.

**Best when** you've decided on an approach and need a polished output to show to an external audience.

---

## Recommendation

**Option 1.** It directly serves the stated goal — *research how to graphically present this* — by putting multiple presentation styles on one page where they can be compared. The other two options optimise for outputs that come *after* the research question is answered. Build #1 first, use the comparison page to pick winners per visual category, then escalate to #2 (production-quality artifacts) or #3 (video) once the choices are made.

A reasonable progression:

```
Option 1 (research)
   │
   ├─→ Pick winning idiom per visual category
   │
   ├─→ Option 2 — render the chosen idioms as production-quality artifacts
   │
   └─→ Option 3 — wrap the chosen idioms into a video for external audiences
```

---

## Decision log placeholder

| Date | Decision | Rationale |
|---|---|---|
| _pending_ | Approach chosen for graphical presentation research | _to be filled in_ |
