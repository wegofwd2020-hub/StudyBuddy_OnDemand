# Option 2 — Per-Example Artifact Catalogue

> Best-tool-per-visual rendering of the Sets and Functions chapter. The companion to `Demos.html` (Option 1, single-page comparison) — that one is for picking which idiom you like, this one shows what each idiom looks like at production quality.

## What's here

```
Option2_Catalogue/
├── README.md                              ← this file
│
├── set-operations/                        ← inline SVG
│   ├── union.svg
│   ├── intersection.svg
│   ├── difference.svg
│   └── complement.svg
│
├── power-set/                             ← inline SVG, Hasse diagram
│   └── hasse-3-element.svg
│
├── arrow-diagrams/                        ← regenerated from one TS spec
│   ├── _template.svg                      (commented description of layout)
│   ├── R1-function.svg
│   ├── R2-not-function.svg
│   ├── R3-function-not-injective.svg
│   ├── R4-not-function.svg
│   ├── injective-only.svg
│   ├── surjective-only.svg
│   └── bijective.svg
│
├── function-graphs/                       ← Desmos / GeoGebra recipes
│   └── desmos-and-geogebra.md
│
├── composition/                           ← inline SVG, pipeline view
│   ├── g-after-f.svg
│   └── f-after-g.svg
│
├── animations/                            ← Manim + SMIL fallback
│   ├── README.md
│   ├── transformations.py                 (Manim Scene → MP4 when rendered)
│   ├── projectile.py                      (Manim Scene → MP4 when rendered)
│   └── projectile-smil.svg                (no-install animated SVG)
│
└── katex-typography/
    └── notation-cheatsheet.html           (every notation in the chapter, rendered)
```

## Tool-per-visual mapping

| Visual target | Tool | Why |
|---|---|---|
| Venn diagrams (set ops) | hand-authored **SVG** | Trivially small; CSS variables let you re-skin |
| Power-set lattice (Hasse) | hand-authored **SVG** | Same — it's just lines and labels |
| Arrow diagrams (functions, inj/surj/bij) | **TS generator + SVG** | Spec-driven; adding a new diagram is 6 lines |
| Function graphs | **Desmos / GeoGebra** | Best-in-class graphing with sliders, time animation, math-aware syntax. Embeddable. |
| Pipeline views (composition) | hand-authored **SVG** | Boxes + arrows; tiny |
| Mathematical animations (transformations, projectile) | **Manim** | Industry standard for math anim. SMIL fallback for projectile if Manim isn't installed. |
| Math typography | **KaTeX in HTML** | Already proven in the existing `Sets_and_Functions.html` export. |

## Regenerating things

```bash
# Arrow diagrams — edit the spec at the bottom of the TS file then re-run
bun scripts/generate_arrow_diagrams.ts

# Manim animations — see animations/README.md (needs Python + LaTeX install)
cd animations && manim -pql transformations.py TransformParabola
```

The hand-authored SVGs (Venn, Hasse, composition) are static files; edit them directly.

## Caveats

| Issue | Status |
|---|---|
| **Manim needs Python** | StudyBuddy is TS-only. Manim files here are *artifacts* the user runs in a separate venv, not project source code. See `animations/README.md`. If we keep doing this, port to Remotion. |
| **Graphviz `dot` not installed on this machine** | We hand-authored the arrow diagrams instead. The TS generator means future spec changes are still cheap. |
| **Desmos / GeoGebra URLs are placeholders** | The `desmos-and-geogebra.md` lists each function's expression and the `Saved URL` column waits for you to save the graph and paste the share link back. Saving is a one-time act per graph. |
| **`projectile-smil.svg` uses a Bezier approximation of the parabola** | Visually accurate; not pixel-precise to $h(t) = -4.9t^2 + 14t + 2$. If precision matters, render the Manim version. |

## How this compares to Option 1 (`../Demos.html`)

| | Option 1 — interactive page | Option 2 — catalogue |
|---|---|---|
| Goal | *Compare* idioms side-by-side | *Showcase* the best version of each idiom |
| Single artifact? | Yes (one HTML) | No (16 files across 7 folders) |
| Install requirement | None | None for SVG / KaTeX; Manim or Desmos for the rest |
| Polish | Honest medium | High per file |
| Reusability of pieces | Need to extract from one HTML | Each file is independently reusable |
| Best for | Picking a winner | Production handoff |

Use both — pick winners with Option 1, then pull the production-quality files from Option 2 into product copy / decks / docs.
