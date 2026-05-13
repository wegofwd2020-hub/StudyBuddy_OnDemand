# G11-CHEM-001 Some Basic Concepts of Chemistry — Visual Catalogue

Sub-title: *From Matter to the Mole.*

Hand-authored kit for the G11 Science demo. Mirrors the layout of
`G11-CHEM-002_Structure_of_Atom`: per-section SVG catalogue plus one
high-leverage Remotion clip.

## What's here

```
G11-CHEM-001_Some_Basic_Concepts_of_Chemistry/
├── README.md
├── Option2_Catalogue/                        ← 13 SVGs across 5 sections
│   ├── section-1-nature-of-matter/           (3 SVGs)
│   │   ├── matter-classification-tree.svg
│   │   ├── states-of-matter-phase-changes.svg
│   │   └── physical-vs-chemical-change.svg
│   ├── section-2-laws-of-combination/        (3 SVGs)
│   │   ├── law-of-conservation-balance.svg
│   │   ├── law-of-definite-proportions.svg
│   │   └── law-of-multiple-proportions.svg
│   ├── section-3-atomic-molar-mass/          (3 SVGs)
│   │   ├── carbon-12-amu-reference.svg
│   │   ├── avogadro-number-scale.svg
│   │   └── molar-mass-periodic-excerpt.svg
│   ├── section-4-composition-and-formulae/   (2 SVGs)
│   │   ├── percent-composition-pies.svg
│   │   └── empirical-vs-molecular-formula-flow.svg
│   └── section-5-stoichiometry/              (3 SVGs)
│       ├── mole-ratio-stoichiometry-tree.svg
│       ├── limiting-reagent-visualization.svg
│       └── percent-yield-flow.svg
└── Option3_Video/                            ← Remotion project, 1 composition
    ├── package.json
    ├── tsconfig.json
    ├── remotion.config.ts
    └── src/
        ├── index.ts
        ├── Root.tsx
        ├── theme.ts
        └── scenes/
            └── MoleVisualizationScene.tsx     ~28 s
```

Every SVG has a sibling `.metadata.yaml` sidecar (`subject: chemistry`,
`source_unit: G11-CHEM-001`).

## Render the video

```bash
cd sample_content/g11-science/G11-CHEM-001_Some_Basic_Concepts_of_Chemistry/Option3_Video
bun install                                # one-time
bun run render:mole-visualization          # → ~/Downloads/BasicChem_MoleVisualization.mp4
```

Composition ID: `basic-chem-mole-visualization`.
Suggested final filename: `BasicChem_MoleVisualization.mp4`.

After rendering, copy the MP4 into `web/public/sample-visuals/G11-CHEM-001/`
so the tutorial route can serve it.

## Section-to-asset map

| § | Section | SVGs | Video |
|---|---|---|---|
| s1 | Nature of Matter | 3 | — |
| s2 | Laws of Chemical Combination | 3 | — |
| s3 | Atomic & Molar Masses | 3 | BasicChem_MoleVisualization.mp4 (0:28) |
| s4 | Composition & Formulae | 2 | — |
| s5 | Stoichiometry | 3 | — |

The Remotion clip is anchored to s3 (Avogadro's number) but is re-usable
under s5 as a recap when introducing mole ratios.

## Reused scaffolding

- `theme.ts` is identical in shape to `G11-CHEM-002`'s theme (PAI charcoal +
  purple, particle palette consistent).
- The dot-flood pattern in `MoleVisualizationScene` is structurally a cousin
  of the orbital-fill staggered-arrival pattern from `ElectronFillScene`.
- All 13 catalogue SVGs use the same `font-family: system-ui` sans-serif and
  the chemistry palette (carbon = charcoal `#1f2937`, oxygen = red `#dc2626`,
  hydrogen = straw `#fef3c7`, nitrogen = green `#15803d`) that's already in
  place across `G11-CHEM-002`.

## Source content

Tutorial: `content_store_data/curricula/default-2026-g11-science/G11-CHEM-001/tutorial_en.json` (5 sections).
