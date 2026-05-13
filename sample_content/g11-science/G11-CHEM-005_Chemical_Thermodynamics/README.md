# G11-CHEM-005 Chemical Thermodynamics — Visual Catalogue

Sub-title: *Energy, Entropy, and Spontaneity.*

Hand-authored kit for the G11 Science demo. Mirrors the layout of
`G11-CHEM-001_Some_Basic_Concepts_of_Chemistry` and
`G11-CHEM-002_Structure_of_Atom`: per-section SVG catalogue plus one
high-leverage Remotion clip.

## What's here

```
G11-CHEM-005_Chemical_Thermodynamics/
├── README.md
├── Option2_Catalogue/                            ← 14 SVGs across 5 sections
│   ├── section-1-system-internal-energy/         (3 SVGs)
│   │   ├── system-types-open-closed-isolated.svg
│   │   ├── internal-energy-state-function.svg
│   │   └── first-law-energy-flow.svg
│   ├── section-2-enthalpy-thermochemistry/       (3 SVGs)
│   │   ├── exothermic-vs-endothermic-enthalpy.svg
│   │   ├── hess-law-cycle.svg
│   │   └── bond-enthalpy-table.svg
│   ├── section-3-entropy/                        (3 SVGs)
│   │   ├── entropy-microstates.svg
│   │   ├── gas-expansion-entropy.svg
│   │   └── second-law-universe-entropy.svg
│   ├── section-4-gibbs-spontaneity/              (3 SVGs)
│   │   ├── gibbs-free-energy-equation.svg
│   │   ├── gibbs-spontaneity-four-cases.svg
│   │   └── standard-free-energies-table.svg
│   └── section-5-integrated-applications/        (2 SVGs)
│       ├── reaction-coordinate-activation-energy.svg
│       └── spontaneity-vs-rate-decision-tree.svg
└── Option3_Video/                                ← Remotion project, 1 composition
    ├── package.json
    ├── tsconfig.json
    ├── remotion.config.ts
    └── src/
        ├── index.ts
        ├── Root.tsx
        ├── theme.ts
        └── scenes/
            └── ReactionCoordinateScene.tsx       ~26 s
```

Every SVG has a sibling `.metadata.yaml` sidecar (`subject: chemistry`,
`source_unit: G11-CHEM-005`).

## Render the video

```bash
cd sample_content/g11-science/G11-CHEM-005_Chemical_Thermodynamics/Option3_Video
bun install                                  # one-time
bun run render:reaction-coordinate           # → ~/Downloads/ChemThermo_ReactionCoordinate.mp4
```

Composition ID: `thermo-reaction-coordinate`.
Suggested final filename: `ChemThermo_ReactionCoordinate.mp4`.

After rendering, copy the MP4 into `web/public/sample-visuals/G11-CHEM-005/`
so the tutorial route can serve it.

## Section-to-asset map

| § | Section | SVGs | Video |
|---|---|---|---|
| s1 | System, Surroundings, Internal Energy | 3 | — |
| s2 | Enthalpy and Thermochemistry | 3 | — |
| s3 | Entropy — Disorder, Probability, Second Law | 3 | — |
| s4 | Gibbs Free Energy and Spontaneity | 3 | — |
| s5 | Integrated Applications | 2 | ChemThermo_ReactionCoordinate.mp4 (0:26) |

The Remotion clip is anchored to s5 (integrated applications — spontaneity vs
rate) but is a useful recap any time E_a, ΔH, or the transition state is
introduced from s2 onwards.

## Reused scaffolding

- `theme.ts` is a superset of `G11-CHEM-001`'s and `G11-CHEM-002`'s themes —
  same charcoal-purple PAI palette, same chemistry particle palette
  (proton/neutron/electron/photon plus carbon/hydrogen/oxygen), with two new
  thermo-specific colours (`reactant`, `product`, `transitionState`,
  `energyCurve`).
- The bell-curve trace in `ReactionCoordinateScene` uses the same
  `stroke-dasharray` + animated `stroke-dashoffset` technique as the
  trajectory traces in earlier kinematics scenes — the curve "draws itself"
  over a fixed window of frames.
- The two-phase quadratic Bezier (R → ‡ → P) is sampled with a small
  `quadratic(t, …)` helper so the tracer dot — and the molecule pair — walk
  along the visible curve precisely, not approximately.
- All 14 catalogue SVGs use the same `font-family: system-ui` sans-serif and
  the chemistry palette already used across CHEM-001 and CHEM-002.

## Source content

Tutorial: `content_store_data/curricula/default-2026-g11-science/G11-CHEM-005/tutorial_en.json` (5 sections).
