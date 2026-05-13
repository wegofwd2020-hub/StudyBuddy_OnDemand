# G11-CHEM-004 Chemical Bonding and Molecular Structure — Visual Catalogue

Sub-title: *Why atoms hold together — and why molecules have shapes.*

Hand-authored kit for the G11 Science demo. Mirrors the layout of
`G11-CHEM-001` and `G11-CHEM-002`: per-section SVG catalogue plus one
high-leverage Remotion clip.

## What's here

```
G11-CHEM-004_Chemical_Bonding/
├── README.md
├── Option2_Catalogue/                          ← 13 SVGs across 5 sections
│   ├── section-1-ionic-covalent/               (3 SVGs)
│   │   ├── ionic-electron-transfer.svg
│   │   ├── covalent-electron-sharing.svg
│   │   └── ionic-vs-covalent-comparison.svg
│   ├── section-2-lewis-octet/                  (2 SVGs)
│   │   ├── lewis-h2o-nh3-ch4.svg
│   │   └── lewis-multiple-bonds-o2-co2-n2.svg
│   ├── section-3-vsepr-geometry/               (3 SVGs)
│   │   ├── vsepr-five-shapes-gallery.svg
│   │   ├── vsepr-lone-pair-effect-water-ammonia.svg
│   │   └── vsepr-electron-pair-geometry-table.svg
│   ├── section-4-vbt-hybridization/            (2 SVGs)
│   │   ├── hybrid-orbitals-sp-sp2-sp3.svg
│   │   └── sigma-pi-bonds-ethene.svg
│   └── section-5-polarity-imf/                 (3 SVGs)
│       ├── dipole-moment-hcl-water-co2.svg
│       ├── intermolecular-forces-types.svg
│       └── hydrogen-bond-network-water.svg
└── Option3_Video/                              ← Remotion project, 1 composition
    ├── package.json
    ├── tsconfig.json
    ├── remotion.config.ts
    └── src/
        ├── index.ts
        ├── Root.tsx
        ├── theme.ts
        └── scenes/
            └── VSEPRShapesScene.tsx            ~28 s
```

Every SVG has a sibling `.metadata.yaml` sidecar
(`subject: chemistry`, `source_unit: G11-CHEM-004`).

## Render the video

```bash
cd sample_content/g11-science/G11-CHEM-004_Chemical_Bonding/Option3_Video
bun install                              # one-time
bun run render:vsepr-shapes              # → ~/Downloads/ChemBonding_VSEPRShapes.mp4
```

Composition ID: `chem-bonding-vsepr-shapes`.
Suggested final filename: `ChemBonding_VSEPRShapes.mp4`.

After rendering, copy the MP4 into `web/public/sample-visuals/G11-CHEM-004/`
so the tutorial route can serve it.

## Section-to-asset map

| § | Section | SVGs | Video |
|---|---|---|---|
| s1 | Foundations — Ionic & Covalent Bonds | 3 | — |
| s2 | Lewis Structures & the Octet Rule | 2 | — |
| s3 | VSEPR Theory & Molecular Geometry | 3 | ChemBonding_VSEPRShapes.mp4 (0:28) |
| s4 | Valence Bond Theory & Hybrid Orbitals | 2 | — |
| s5 | Polarity, IMFs, Physical Properties | 3 | — |

The Remotion clip is anchored to s3 (VSEPR) but pairs naturally as a recap
when s4 introduces the matching hybridisation (sp³ → tetrahedral, sp² →
trigonal planar, sp → linear).

## Chemistry-accuracy notes

- **CH₄ tetrahedral:** 109.5° bond angle.
- **NH₃ trigonal pyramidal:** 107° (one lone pair compresses from 109.5°).
- **H₂O bent:** 104.5° (two lone pairs compress further).
- **CO₂ linear:** 180° (two C=O double bonds, no lone pairs on C).
- **N₂ triple bond:** 945 kJ mol⁻¹ — strongest common diatomic bond.
- **H₂ bond length:** 74 pm; bond enthalpy 436 kJ mol⁻¹.
- **HCl dipole moment:** ≈ 1.08 D (EN difference Cl 3.16 vs H 2.20).
- **H₂O dipole moment:** ≈ 1.85 D (bent geometry → vectors add).
- **H-bond strength range:** ~10–40 kJ mol⁻¹ (water ≈ 21 kJ mol⁻¹).
- **Steric-number → hybridisation mapping** in the VSEPR table is the
  textbook standard (SN 2 → sp, SN 3 → sp², SN 4 → sp³, SN 5 → sp³d, SN 6
  → sp³d²).

## Reused scaffolding

- `theme.ts` matches `G11-CHEM-002` and `G11-CHEM-001` (PAI charcoal +
  purple); chemistry palette extended with carbon/oxygen/nitrogen/hydrogen
  named colours so the VSEPR scene reads at a glance.
- Stage timing (`F_STAGE0_START` etc.) follows the same anchor-frames
  pattern as `BohrTransitionScene`.
- All 13 catalogue SVGs use the same `font-family: system-ui` sans-serif.
  Element colour conventions: O red `#dc2626`, N blue `#2b6cb0`, C charcoal
  `#1a202c`, H straw `#fef3c7`, F/Cl green `#15803d`.

## Source content

Tutorial: `content_store_data/curricula/default-2026-g11-science/G11-CHEM-004/tutorial_en.json` (5 sections).
