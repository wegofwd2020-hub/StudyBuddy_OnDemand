# G11-PHYS-008 Thermodynamics — Visual Catalogue

Visual + video kit for *Thermodynamics: Heat, Work, and the Laws Governing
Energy Transfer*. Built per the Option-2-primary, Option-3-supplementary rule
(issue #317): hand-crafted SVGs are the main artefact; a single Remotion scene
supplements the highest-leverage idea (the Carnot cycle).

## What's here

```
G11-PHYS-008_Thermodynamics/
├── README.md                                           ← this file
├── Option2_Catalogue/                                  ← 15 standalone SVGs by section
│   ├── section-1-temperature-heat-internal-energy/     (3 SVGs)
│   │   ├── temperature-scales-comparison.svg
│   │   ├── heat-vs-work.svg
│   │   └── internal-energy-molecular.svg
│   ├── section-2-zeroth-first-laws/                    (3 SVGs)
│   │   ├── zeroth-law-thermal-equilibrium.svg
│   │   ├── first-law-energy-balance.svg
│   │   └── pv-diagram-four-processes.svg
│   ├── section-3-second-law-entropy/                   (3 SVGs)
│   │   ├── second-law-statements.svg
│   │   ├── entropy-free-expansion.svg
│   │   └── entropy-heat-transfer.svg
│   ├── section-4-heat-engines-carnot/                  (4 SVGs)
│   │   ├── heat-engine-schematic.svg
│   │   ├── refrigerator-schematic.svg
│   │   ├── carnot-cycle-pv-diagram.svg
│   │   └── carnot-four-strokes-piston.svg
│   └── section-5-integrated-problem-solving/           (2 SVGs)
│       ├── efficiency-comparison-map.svg
│       └── problem-solving-flowchart.svg
└── Option3_Video/                                      ← Remotion project, 1 composition
    ├── package.json
    ├── tsconfig.json
    ├── remotion.config.ts
    ├── src/
    │   ├── index.ts
    │   ├── Root.tsx                                    1 composition registered
    │   ├── theme.ts                                    PAI charcoal + purple (shared with G11-PHYS-002, G11-PHYS-007)
    │   └── scenes/
    │       └── CarnotCycleScene.tsx                    ~32 s
    └── public/                                         (empty)
```

Every SVG ships with a sister `*.metadata.yaml` sidecar (`subject: physics`,
`source_unit: G11-PHYS-008`) that the visual library indexer consumes.

## Sections covered

| § | Section | SVGs | Video |
|---|---|---|---|
| s1 | Temperature, heat, and internal energy | 3 | — |
| s2 | Zeroth and First Laws | 3 | — |
| s3 | Second Law and entropy | 3 | — |
| s4 | Heat engines, refrigerators, Carnot cycle | 4 | Thermo_CarnotCycle.mp4 (0:32) |
| s5 | Integrated problem-solving | 2 | — |

## Render the video

```bash
cd sample_content/g11-science/G11-PHYS-008_Thermodynamics/Option3_Video
bun install                 # one-time
bun run render:carnot       # → ~/Downloads/Thermo_CarnotCycle.mp4
```

Composition ID: `thermo-carnot-cycle` (1920×1080, 30 fps, 32 s).

After rendering, copy the MP4 into `web/public/sample-visuals/G11-PHYS-008/`
so the tutorial route serves it.

## Reused scaffolding

- `Option3_Video/src/theme.ts` is a verbatim copy of the G11-PHYS-002 / G11-PHYS-007
  theme; one shared aesthetic across all physics units.
- `tsconfig.json`, `remotion.config.ts`, the `index.ts` / `Root.tsx` shape match
  the kinematics + bulk-matter exemplars; only the composition list and the
  scene module differ.
- The SVG style (system-ui type, `#1a202c` body / `#dc2626` accent / `#1d4ed8`
  fluid-blue / `#15803d` highlight, panel rectangles with `#f7fafc` fill +
  `#cbd5e1` border) is the same vocabulary as the kinematics + bulk-matter
  catalogues.

## Physics accuracy notes

- **PV-diagram slopes** are drawn with the correct ordering: at any common
  state, the adiabat (`PV^γ = const`, γ=1.4) is steeper than the isotherm
  (`PV = const`).
- **Carnot states** in `carnot-cycle-pv-diagram.svg` and the Remotion scene
  use a self-consistent set of corners A–B–C–D such that
  `P_A V_A = P_B V_B`, `P_B V_B^γ = P_C V_C^γ`, `P_C V_C = P_D V_D`,
  `P_D V_D^γ = P_A V_A^γ`. The cycle closes; the enclosed area is the net
  work done.
- **Carnot efficiency** is given as `η = 1 − T_C ⁄ T_H` (Kelvin), with the
  warning that this is the upper bound and only a reversible cycle attains
  it. The efficiency-map SVG shows real engines (10–60%) all sitting below
  their respective Carnot ceilings.
- **Sign convention** for the First Law follows the physics convention
  (`ΔU = Q − W`, `W > 0` when work is done BY the gas). The IUPAC chemistry
  convention is mentioned in the sign-convention panel for cross-discipline
  awareness.
