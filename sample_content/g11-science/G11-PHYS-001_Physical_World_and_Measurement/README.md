# G11-PHYS-001 Physical World &amp; Measurement — Visual Catalogue

Third exemplar in the G11 Science kit, following `G11-PHYS-002 Kinematics` and
`G11-PHYS-010 Oscillations and Waves`. Same rule applies: **Option 2 (per-example
SVGs) is primary; Option 3 (Remotion video) sits below the graphics where
high-leverage; Option 1 (gallery) is fallback only.**

## What's here

```
G11-PHYS-001_Physical_World_and_Measurement/
├── README.md                          ← this file
├── Option2_Catalogue/                 ← 15 standalone SVGs by section
│   ├── section-1-scope-and-laws/                        (3 SVGs)
│   │   ├── scales-of-physics.svg                        Planck → universe log axis
│   │   ├── domains-of-physics.svg                       classical / modern tree
│   │   └── scientific-method-cycle.svg                  6-node iterative loop
│   ├── section-2-si-units-and-dimensions/               (3 SVGs)
│   │   ├── si-base-units-table.svg                      7 base units + 2019 constants
│   │   ├── derived-units-flow.svg                       N · J · W · Pa · Hz · C · V · Ω
│   │   └── si-prefixes-ladder.svg                       femto → peta with examples
│   ├── section-3-sigfigs-and-orders/                    (3 SVGs)
│   │   ├── significant-figures-rules.svg                5 rules + arithmetic combo box
│   │   ├── scientific-notation-anatomy.svg              a × 10ⁿ annotated
│   │   └── order-of-magnitude-examples.svg              hairs · breaths · sand grains
│   ├── section-4-errors-and-uncertainty/                (3 SVGs)
│   │   ├── random-vs-systematic.svg                     2×2 target diagram
│   │   ├── mean-and-uncertainty.svg                     pendulum-period scatter ± σ
│   │   └── error-propagation-rules.svg                  ±, ×, ^n with density example
│   └── section-5-dimensional-analysis/                  (3 SVGs)
│       ├── dimensional-homogeneity-check.svg            ✓ vs ✗ kinematic equations
│       ├── pendulum-formula-derivation.svg              T = 2π √(L/g) by dimensions
│       └── unit-conversion-flow.svg                     km/h ↔ m/s ↔ mph chain-link
└── Option3_Video/                     ← Remotion project, 1 composition
    ├── package.json
    ├── tsconfig.json
    ├── remotion.config.ts
    ├── src/
    │   ├── index.ts
    │   ├── Root.tsx                   1 composition: physical-world-scale
    │   ├── theme.ts                   PAI charcoal + purple (cloned from PHYS-002)
    │   └── scenes/
    │       └── ScaleOfUniverseScene.tsx   ~32 s — animated zoom across 9 scale stops
    └── public/                        (empty; assets are inline SVG glyphs)
```

## Render the video

```bash
cd sample_content/g11-science/G11-PHYS-001_Physical_World_and_Measurement/Option3_Video
bun install                    # one-time
bun run render:scale           # → ~/Downloads/PhysicalWorld_ScaleOfUniverse.mp4
# or:
bun run render:all             # currently identical to render:scale
```

After rendering, copy the MP4 into `web/public/sample-visuals/G11-PHYS-001/`
so the tutorial route can serve it.

## Wired into the tutorial UI (proposed)

| § | Section | SVGs | Video |
|---|---|---|---|
| s1 | Scope of Physics &amp; Nature of Physical Laws | 3 | PhysicalWorld_ScaleOfUniverse.mp4 (0:32) |
| s2 | SI Units &amp; Dimensional Analysis | 3 | — |
| s3 | Significant Figures, Scientific Notation, Order of Magnitude | 3 | — |
| s4 | Measurement, Errors &amp; Uncertainty | 3 | — |
| s5 | Dimensions &amp; Applications to Problem Solving | 3 | — |

Total: 15 SVGs + 1 video. The video is **below** the s1 graphic per the
format-priority rule.

## Source content

Tutorial: `content_store_data/curricula/default-2026-g11-science/G11-PHYS-001/tutorial_en.json`.

## Notes for future regeneration

- All SVG viewBoxes follow the existing convention (~480-720 px wide; 200-380 px tall).
- Palette mirrors PHYS-002:
  - quantum / blue accent: `#2b6cb0`, fill `#dbeafe`
  - classical / orange accent: `#dd6b20`, fill `#fef3c7`
  - cosmological / purple accent: `#7c3aed`, fill `#e9d5ff`
  - success / green: `#15803d`, fill `#dcfce7`
  - error / red: `#dc2626`, fill `#fef2f2`
  - neutral text: `#1a202c` / `#4a5568` / `#94a3b8`
- The Remotion `theme.ts` is cloned verbatim from PHYS-002 (PAI charcoal + purple).
- `physical-world-scale` does not use the shared `plot.tsx` helper from PHYS-002 —
  it has its own log-axis layout. A future refactor could extract a shared
  `LogAxis` primitive once a second log-axis scene exists.
