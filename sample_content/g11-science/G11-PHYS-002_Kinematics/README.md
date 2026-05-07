# G11-PHYS-002 Kinematics — Visual Catalogue

Second exemplar after `G11-MATH-001 Sets and Functions`. Built per issue [#317](https://github.com/wegofwd2020-hub/StudyBuddy_OnDemand/issues/317) with the rule: **Option 2 (per-example artifacts) is primary; Option 3 (Remotion videos) appears below the graphic when high-leverage; Option 1 only as fallback.**

## What's here

```
G11-PHYS-002_Kinematics/
├── README.md                           ← this file
├── Option2_Catalogue/                  ← 15 standalone SVGs by section
│   ├── section-1-fundamentals/         (3 SVGs)
│   │   ├── 1d-position-and-displacement.svg
│   │   ├── distance-vs-displacement.svg
│   │   └── average-vs-instantaneous-velocity.svg
│   ├── section-2-uam/                  (3 SVGs)
│   │   ├── xt-uam.svg                  x = vᵢt + ½at²
│   │   ├── vt-uam.svg                  v = vᵢ + at  (with shaded area)
│   │   └── at-uam.svg                  a = constant
│   ├── section-3-freefall/             (2 SVGs)
│   │   ├── height-vs-time.svg          object thrown up at 20 m/s
│   │   └── velocity-vs-time.svg        zero-crossing at peak
│   ├── section-4-projectile/           (3 SVGs)
│   │   ├── trajectory.svg              v = 20 m/s, θ = 60°
│   │   ├── velocity-decomposition.svg
│   │   └── key-results.svg             T, R, y_max formulas
│   └── section-5-graphs/               (4 SVGs)
│       ├── xt-with-tangent.svg         slope = velocity
│       ├── vt-with-area.svg            area = displacement
│       ├── xt-vt-at-trio.svg           the three side-by-side
│       └── slope-area-summary.svg      x ↔ v ↔ a chain
└── Option3_Video/                      ← Remotion project, 4 compositions
    ├── package.json
    ├── tsconfig.json
    ├── remotion.config.ts
    ├── src/
    │   ├── index.ts
    │   ├── Root.tsx                    4 compositions registered
    │   ├── plot.tsx                    shared SVG plot helpers
    │   ├── theme.ts                    PAI charcoal + purple
    │   └── scenes/
    │       ├── UamScene.tsx                ~24s
    │       ├── FreeFallScene.tsx           ~28s
    │       ├── ProjectileScene.tsx         ~22s
    │       └── GraphAnalysisScene.tsx      ~26s
    └── public/                         (empty; assets are static SVGs from Catalogue)
```

## Regenerate

**SVGs (Option 2):**

```bash
bun scripts/generate_kinematics_visuals.ts
```

The 15 SVGs are emitted by a single TypeScript spec. Edit the spec, re-run, done.

**Videos (Option 3):**

```bash
cd sample_content/g11-science/G11-PHYS-002_Kinematics/Option3_Video
bun install                        # one-time
bun run render:all                 # → ~/Downloads/Kinematics_*.mp4
```

Or render individually: `bun run render:uam | freefall | projectile | graphs`.

After rendering, copy MP4s into `web/public/sample-visuals/G11-PHYS-002/` so the tutorial route serves them.

## Wired into the tutorial UI

Each section of `/tutorial/G11-PHYS-002` now shows visual blocks via `web/components/content/VisualSlot.tsx`:

| § | Section | SVGs | Video |
|---|---|---|---|
| s1 | Fundamentals | 3 | — |
| s2 | UAM | 3 | Kinematics_UAM.mp4 (0:24) |
| s3 | Free fall | 2 | Kinematics_FreeFall.mp4 (0:28) |
| s4 | Projectile | 3 | Kinematics_Projectile.mp4 (0:22) |
| s5 | Graphical analysis | 4 | Kinematics_GraphAnalysis.mp4 (0:26) |

Total: 15 SVGs + 4 videos. Every video is **below** its corresponding graphic per the format-priority rule.

## Reused scaffolding

This unit was much faster to build than `G11-MATH-001` because:

- The TS arrow-diagram generator pattern (`scripts/generate_arrow_diagrams.ts`) translated directly into `scripts/generate_kinematics_visuals.ts`.
- The Remotion project structure (Root.tsx, scenes/, theme.ts, plot.tsx) cloned cleanly from `G11-MATH-001_Sets_and_Functions/Option3_Video/`.
- `VisualSlot.tsx` already supported `image`, `image-grid`, `video` block kinds — only the `VISUAL_MAP` entries needed to be added.
- The `ProjectileScene` from MATH-001 ported directly to PHYS-002 s4 with parameter changes (v = 20 m/s, θ = 60° instead of the projectile-motion physics example in MATH-001).

This validates the catalog's effort estimates — once the first exemplar exists, subsequent units take a fraction of the original build time.

## Source content

Tutorial: `content_store_data/curricula/default-2026-g11-science/G11-PHYS-002/tutorial_en.json` (5 sections, ~10 KB Markdown body).

## Open items

- [ ] Live verification on the actual `/tutorial/G11-PHYS-002` route (must run on a Mac box; Interceptor is macOS-only on the dev machine used to author this).
- [ ] If Phase B feedback prefers shorter videos, retime the scenes — one-line change per scene (`durationInFrames` in `Root.tsx`).
- [ ] Once issue #316 lands a tutorial-JSON visual-block schema, retire the static `VISUAL_MAP` and let the pipeline emit visual blocks per unit.
