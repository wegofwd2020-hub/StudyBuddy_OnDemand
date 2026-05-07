# G11-PHYS-010 Oscillations and Waves — Visual Catalogue

Third exemplar after `G11-MATH-001 Sets and Functions` and `G11-PHYS-002 Kinematics`. Built per issue [#327](https://github.com/wegofwd2020-hub/StudyBuddy_OnDemand/issues/327) — the first **Wave 1** unit of the [Visual Library Expansion epic](https://github.com/wegofwd2020-hub/StudyBuddy_OnDemand/issues/326).

## What's here

```
G11-PHYS-010_Oscillations_and_Waves/
├── README.md                                  ← this file
├── MEMO.md                                    ← what was repetitive vs unique (input for #320)
├── Option2_Catalogue/                         ← 12 standalone SVGs by section
│   ├── section-1-shm-kinematics/              (2 SVGs)
│   │   ├── shm-displacement-time.svg          y(t) = A sin(ωt) with A and T labelled
│   │   └── shm-y-v-a-comparison.svg           three stacked plots showing 90° phase
│   ├── section-2-energy-pendulum/             (2 SVGs)
│   │   ├── shm-energy-vs-displacement.svg     KE + PE = ½kA² (complementary parabolas)
│   │   └── simple-pendulum-restoring-force.svg  pendulum with mg, T, -mg sin θ
│   ├── section-3-wave-properties/             (2 SVGs)
│   │   ├── transverse-vs-longitudinal.svg     side-by-side comparison
│   │   └── wave-anatomy.svg                   crest, trough, λ, A labelled
│   ├── section-4-superposition/               (3 SVGs)
│   │   ├── superposition-constructive.svg     in-phase, sum doubles
│   │   ├── superposition-destructive.svg      π out of phase, sum cancels
│   │   └── standing-wave-modes.svg            n=1, 2, 3 harmonics on a string
│   └── section-5-damping-doppler/             (3 SVGs)
│       ├── damped-oscillation-comparison.svg  under, critical, over damped
│       ├── resonance-amplitude-curve.svg      |X| vs ω/ω₀, three damping levels
│       └── doppler-source-approaching.svg     moving source, compressed wavefronts
└── Option3_Video/                             ← Remotion compositions (next phase)
```

## Generators built (this unit's contribution to the reusable scaffolding)

This unit ships **3 reusable Remotion components** (still to land in the next phase) and **2 reusable SVG primitives** that downstream units pick up cheaply:

| Generator | First use | Downstream reuse target |
|---|---|---|
| `superpositionPlot()` (3-stacked plot) | section-4 superposition | G8-SCI-002 (#335), G12-PHYS-005 (#336) |
| `wave-anatomy` style label overlays | section-3 | G8-SCI-002, G12-PHYS-004 |
| Standing-wave envelope generator | section-4 | G8-SCI-002 (organ pipes / string instruments) |
| **(Remotion, phase 2)** wave-superposition Remotion | section-4 marquee | G8-SCI-002, G12-PHYS-005 |
| **(Remotion, phase 2)** SHM Remotion | section-1 marquee | (general SHM topics) |
| **(Remotion, phase 2)** Doppler Remotion | section-5 marquee | (general wave-source topics) |

## Generators reused (from prior units)

- `makePlot()` — direct lift from `scripts/generate_kinematics_visuals.ts` (G11-PHYS-002)
- `polyline()` — same
- Colour palette constants (INK, MUTED, ACCENT, ACCENT_2, ACCENT_3, NEGATIVE, POSITIVE, GRID, AXIS, BG) — same

## Building / regenerating

```bash
# 1. (re)generate the SVGs
bun scripts/generate_oscillations_visuals.ts

# 2. (re)generate the sidecars
bun scripts/seed_library_sidecars.ts

# 3. validate sidecars
bun scripts/validate_library_metadata.ts \
  "sample_content/g11-science/G11-PHYS-010_Oscillations_and_Waves/**/*.metadata.yaml"

# 4. seed the library (writes the embeddings + DB rows)
docker compose exec -T -e DATABASE_URL='postgresql://studybuddy:studybuddy_dev@host.docker.internal:5433/studybuddy' \
  celery-pipeline python3 /tmp/seed/scripts/seed_library_local.py
```

## What "done" looks like for this issue

- [x] 12 SVGs generated — `find Option2_Catalogue -name "*.svg" | wc -l` returns 12
- [x] 12 sidecars generated and all pass validator
- [ ] 3 Remotion clips (SHM, superposition, Doppler) — **next phase**
- [ ] `MEMO.md` final pass after the Remotion clips land
- [ ] Library promotion via `seed_library_local.py` — verifies embeddings land
- [ ] At least 2 new known-positive eval records added to `backend/tests/eval/visual_resolver_eval.jsonl` targeting this unit's library entries

## Cross-references

- Parent epic: [#326](https://github.com/wegofwd2020-hub/StudyBuddy_OnDemand/issues/326)
- This issue: [#327](https://github.com/wegofwd2020-hub/StudyBuddy_OnDemand/issues/327)
- Reference exemplar (kinematics): `../G11-PHYS-002_Kinematics/`
- Generator script: [`scripts/generate_oscillations_visuals.ts`](../../../scripts/generate_oscillations_visuals.ts)
