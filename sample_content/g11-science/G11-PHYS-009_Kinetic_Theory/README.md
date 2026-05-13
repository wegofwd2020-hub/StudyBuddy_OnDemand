# G11-PHYS-009 Behaviour of Perfect Gas and Kinetic Theory — Visual Catalogue

Visual + video kit for *Behaviour of Perfect Gas and Kinetic Theory*. Built per
the Option-2-primary, Option-3-supplementary rule (issue #317): hand-crafted
SVGs are the main artefact; a single Remotion scene supplements the
highest-leverage idea (the Maxwell-Boltzmann distribution shifting with
temperature).

## What's here

```
G11-PHYS-009_Kinetic_Theory/
├── README.md                              ← this file
├── Option2_Catalogue/                     ← 14 standalone SVGs by section
│   ├── section-1-ideal-gas-law/           (3 SVGs)
│   │   ├── boyles-law-isotherms.svg
│   │   ├── charles-and-gay-lussac.svg
│   │   └── ideal-gas-equation-state-variables.svg
│   ├── section-2-kinetic-foundations/     (3 SVGs)
│   │   ├── molecules-in-box-pressure.svg
│   │   ├── temperature-and-kinetic-energy.svg
│   │   └── mean-free-path.svg
│   ├── section-3-maxwell-boltzmann/       (3 SVGs)
│   │   ├── maxwell-boltzmann-temperatures.svg
│   │   ├── three-characteristic-speeds.svg
│   │   └── maxwell-boltzmann-different-masses.svg
│   ├── section-4-internal-energy/         (2 SVGs)
│   │   ├── degrees-of-freedom.svg
│   │   └── equipartition-and-cv.svg
│   └── section-5-real-gases/              (3 SVGs)
│       ├── compressibility-factor-deviation.svg
│       ├── van-der-waals-corrections.svg
│       └── van-der-waals-isotherms-critical-point.svg
└── Option3_Video/                         ← Remotion project, 1 composition
    ├── package.json
    ├── tsconfig.json
    ├── remotion.config.ts
    ├── src/
    │   ├── index.ts
    │   ├── Root.tsx                       1 composition registered
    │   ├── theme.ts                       PAI charcoal + purple (shared with G11-PHYS-002 / 007)
    │   └── scenes/
    │       └── MaxwellBoltzmannScene.tsx  ~28 s
    └── public/                            (empty)
```

Every SVG ships with a sister `*.metadata.yaml` sidecar (`subject: physics`,
`source_unit: G11-PHYS-009`) that the visual library indexer consumes.

## Sections covered

| § | Section | SVGs | Video |
|---|---|---|---|
| s1 | Ideal Gas Law and State Variables | 3 | — |
| s2 | Kinetic Theory — Microscopic Foundations | 3 | — |
| s3 | Maxwell-Boltzmann Speed Distribution | 3 | KineticTheory_MaxwellBoltzmann.mp4 (0:28) |
| s4 | Internal Energy, Degrees of Freedom, Equipartition | 2 | — |
| s5 | Real Gases vs Ideal Gas Model | 3 | — |

## Render the video

```bash
cd sample_content/g11-science/G11-PHYS-009_Kinetic_Theory/Option3_Video
bun install                            # one-time
bun run render:maxwell-boltzmann       # → ~/Downloads/KineticTheory_MaxwellBoltzmann.mp4
```

Composition ID: `kinetic-theory-maxwell-boltzmann` (1920×1080, 30 fps, 28 s).

After rendering, copy the MP4 into `web/public/sample-visuals/G11-PHYS-009/`
so the tutorial route serves it.

## Reused scaffolding

- `Option3_Video/src/theme.ts` is a verbatim copy of the G11-PHYS-007 theme; one
  shared aesthetic across all physics units.
- `tsconfig.json`, `remotion.config.ts`, the `index.ts` / `Root.tsx` shape match
  the kinematics + bulk-matter exemplars; only the composition list and the
  scene module differ.
- The SVG style (system-ui type, `#1a202c` body / `#dc2626` accent / `#1d4ed8`
  cool-blue / `#15803d` highlight, panel rectangles with `#f7fafc` fill +
  `#cbd5e1` border) is the same vocabulary as the kinematics + bulk-matter
  catalogues.
