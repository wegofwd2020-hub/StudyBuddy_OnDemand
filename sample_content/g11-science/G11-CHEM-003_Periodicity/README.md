# G11-CHEM-003 Classification of Elements and Periodicity in Properties — Visual Catalogue

Sub-title: *Three trends, one table.*

Hand-authored kit for the G11 Science demo. Mirrors the layout of
`G11-CHEM-002_Structure_of_Atom` and `G11-CHEM-001_Some_Basic_Concepts_of_Chemistry`:
per-section SVG catalogue plus one high-leverage Remotion clip.

## What's here

```
G11-CHEM-003_Periodicity/
├── README.md
├── Option2_Catalogue/                                 ← 15 SVGs across 5 sections
│   ├── section-1-historical-development/              (3 SVGs)
│   │   ├── mendeleev-table-with-gaps.svg
│   │   ├── periodic-table-evolution-timeline.svg
│   │   └── moseley-atomic-number-fix.svg
│   ├── section-2-modern-table-config/                 (3 SVGs)
│   │   ├── periodic-table-spdf-blocks.svg
│   │   ├── group1-vs-group17-config.svg
│   │   └── period-2-configurations.svg
│   ├── section-3-atomic-ionic-radius/                 (3 SVGs)
│   │   ├── atomic-radius-down-group.svg
│   │   ├── atomic-radius-across-period.svg
│   │   └── cation-anion-size-comparison.svg
│   ├── section-4-energetics/                          (3 SVGs)
│   │   ├── ionisation-energy-period-2.svg
│   │   ├── electron-gain-enthalpy.svg
│   │   └── electronegativity-heatmap.svg
│   └── section-5-valence-oxidation/                   (3 SVGs)
│       ├── valence-electrons-group-map.svg
│       ├── transition-metal-oxidation-states.svg
│       └── second-period-anomalies.svg
└── Option3_Video/                                     ← Remotion project, 1 composition
    ├── package.json
    ├── tsconfig.json
    ├── remotion.config.ts
    └── src/
        ├── index.ts
        ├── Root.tsx
        ├── theme.ts
        └── scenes/
            └── PeriodicityTrendsScene.tsx              ~32 s
```

Every SVG has a sibling `.metadata.yaml` sidecar (`subject: chemistry`,
`source_unit: G11-CHEM-003`).

## Render the video

```bash
cd sample_content/g11-science/G11-CHEM-003_Periodicity/Option3_Video
bun install                                          # one-time
bun run render:trends-walkthrough                    # → ~/Downloads/Periodicity_TrendsWalkthrough.mp4
```

Composition ID: `periodicity-trends-walkthrough`.
Suggested final filename: `Periodicity_TrendsWalkthrough.mp4`.

After rendering, copy the MP4 into `web/public/sample-visuals/G11-CHEM-003/`
so the tutorial route can serve it.

## Section-to-asset map

| § | Section | SVGs | Video |
|---|---|---|---|
| s1 | Historical Development of the Periodic Table | 3 | — |
| s2 | Modern Periodic Table — Structure & Electronic Config | 3 | Periodicity_TrendsWalkthrough.mp4 (anchored) |
| s3 | Atomic Radius and Ionic Radius — Trends | 3 | (recap, trend 1) |
| s4 | Ionisation Enthalpy, Electron Gain Enthalpy, Electronegativity | 3 | (recap, trends 2 & 3) |
| s5 | Valence, Oxidation States, Anomalous Properties | 3 | — |

The Remotion clip is anchored to s2 (the modern table) and serves as a recap
running through s3 and s4 — three trend washes over the same table.

## Reused scaffolding

- `theme.ts` extends the `G11-CHEM-002` theme with periodic-block tile colours
  (blockS / blockP / blockD / blockF) and a trend-gradient palette (cool blue
  → warm red).
- The 18-column tile grid + reveal-sweep pattern is structurally a cousin of
  the orbital-fill staggered-arrival pattern from `ElectronFillScene`.
- Element symbols, atomic numbers, and trend numerics are sourced from
  IUPAC / NIST standard values — every datum used in trend washes (radius,
  IE₁, electronegativity) is real.

## Source content

Tutorial: `content_store_data/curricula/default-2026-g11-science/G11-CHEM-003/tutorial_en.json` (5 sections).
