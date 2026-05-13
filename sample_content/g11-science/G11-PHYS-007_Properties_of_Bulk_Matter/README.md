# G11-PHYS-007 Properties of Bulk Matter — Visual Catalogue

Visual + video kit for *Properties of Bulk Matter*. Built per the Option-2-primary,
Option-3-supplementary rule (issue #317): hand-crafted SVGs are the main artefact;
a single Remotion scene supplements the highest-leverage idea (Bernoulli / venturi).

## What's here

```
G11-PHYS-007_Properties_of_Bulk_Matter/
├── README.md                              ← this file
├── Option2_Catalogue/                     ← 13 standalone SVGs by section
│   ├── section-1-elasticity/              (3 SVGs)
│   │   ├── stress-strain-curve.svg
│   │   ├── youngs-modulus-rod.svg
│   │   └── shear-and-bulk-stress.svg
│   ├── section-2-fluid-statics/           (3 SVGs)
│   │   ├── hydrostatic-pressure-column.svg
│   │   ├── pascal-hydraulic-press.svg
│   │   └── archimedes-buoyancy.svg
│   ├── section-3-fluid-dynamics/          (3 SVGs)
│   │   ├── continuity-equation-pipe.svg
│   │   ├── bernoulli-venturi.svg
│   │   └── viscosity-laminar-profile.svg
│   ├── section-4-surface-tension/         (2 SVGs)
│   │   ├── surface-tension-molecular.svg
│   │   └── capillary-rise.svg
│   └── section-5-thermal/                 (2 SVGs)
│       ├── thermal-expansion-three-types.svg
│       └── calorimetry-mixing.svg
└── Option3_Video/                         ← Remotion project, 1 composition
    ├── package.json
    ├── tsconfig.json
    ├── remotion.config.ts
    ├── src/
    │   ├── index.ts
    │   ├── Root.tsx                       1 composition registered
    │   ├── theme.ts                       PAI charcoal + purple (shared with G11-PHYS-002)
    │   └── scenes/
    │       └── BernoulliVenturiScene.tsx  ~26s
    └── public/                            (empty)
```

Every SVG ships with a sister `*.metadata.yaml` sidecar (`subject: physics`,
`source_unit: G11-PHYS-007`) that the visual library indexer consumes.

## Sections covered

| § | Section | SVGs | Video |
|---|---|---|---|
| s1 | Elasticity — stress, strain, Hooke's Law | 3 | — |
| s2 | Fluid statics — pressure, Pascal, Archimedes | 3 | — |
| s3 | Fluid dynamics — continuity, Bernoulli, viscosity | 3 | BulkMatter_BernoulliVenturi.mp4 (0:26) |
| s4 | Surface tension and capillarity | 2 | — |
| s5 | Thermal properties — expansion and calorimetry | 2 | — |

## Render the video

```bash
cd sample_content/g11-science/G11-PHYS-007_Properties_of_Bulk_Matter/Option3_Video
bun install                 # one-time
bun run render:venturi      # → ~/Downloads/BulkMatter_BernoulliVenturi.mp4
```

Composition ID: `bulk-matter-bernoulli-venturi` (1920×1080, 30 fps, 26 s).

After rendering, copy the MP4 into `web/public/sample-visuals/G11-PHYS-007/`
so the tutorial route serves it.

## Reused scaffolding

- `Option3_Video/src/theme.ts` is a verbatim copy of the G11-PHYS-002 theme; one
  shared aesthetic across all physics units.
- `tsconfig.json`, `remotion.config.ts`, the `index.ts` / `Root.tsx` shape match
  the kinematics + laws-of-motion exemplars; only the composition list and the
  scene module differ.
- The SVG style (system-ui type, `#1a202c` body / `#dc2626` accent / `#1d4ed8`
  fluid-blue / `#15803d` highlight, panel rectangles with `#f7fafc` fill +
  `#cbd5e1` border) is the same vocabulary as the kinematics catalogue.
