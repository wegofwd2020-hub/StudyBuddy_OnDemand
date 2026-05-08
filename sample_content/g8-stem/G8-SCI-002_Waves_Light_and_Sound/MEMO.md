# MEMO — G8-SCI-002 Waves — Light and Sound

> **2-phase issue** (no Remotion clips; G11-PHYS-010 superposition Remotion is reused as-is per scope).

## Status

- **Phase 1 (Option 2 catalogue):** ✅ 9 SVGs + 9 sidecars shipped
- **Phase 2 (eval + library promotion):** ✅ 9 sidecars promoted; 3 known-positive eval records (`eval-075` / `076` / `077`)

## Phase 1 reflections

| Section | Visuals |
|---|---|
| `section-1-wave-basics` | `transverse-wave-anatomy`, `transverse-vs-longitudinal`, `wave-equation-v-equals-f-lambda` |
| `section-2-light-em-spectrum` | `em-spectrum-strip`, `visible-light-rainbow`, `light-vs-sound-comparison` |
| `section-3-sound-and-resonance` | `sound-wave-pressure-trace`, `pitch-and-loudness`, `resonance-driving-frequency` |

This unit *extends* the physics-oscillations primitive class established in #327 (G11-PHYS-010). The `transverse-wave-anatomy` and `resonance-driving-frequency` figures are G8-friendly variants of `wave-anatomy` and `resonance-amplitude-curve` from the original G11 catalogue. New high-leverage primitives this unit ships:

1. **EM-spectrum strip** with discrete coloured bands + magnified visible-light inset. Two-panel pattern (overview + detail) that will reuse in any spectrum-comparison context.
2. **Compression/rarefaction line cluster** for longitudinal waves (`transverse-vs-longitudinal`). 30 vertical lines with sinusoidally-modulated horizontal density. New primitive — flagged for #320.
3. **Light-vs-sound comparison-card layout** — same shape as the chemistry "alcohol vs aldehyde vs ketone" cards from #333. Confirms the comparison-card pattern carries across subjects.

### What was repetitive (= templatable)

1. **Coloured-band strip with annotations** (`em-spectrum-strip`, `visible-light-rainbow`). Takes `bands: {name, color, lambda}[]` and renders a horizontal segmented strip with text overlays. Reused twice in this unit alone. **Recommendation:** `<ColoredBandStrip bands={...} insetMagnify={...} />`.

2. **Two-row, four-panel pitch-vs-loudness grid.** Same shape as the G9 "uniform-vs-accelerated comparison" four-panel grid. Now five units use grid-of-mini-plots layouts.

3. **Single-bell-curve resonance plot** identical to G11-PHYS-010's `resonance-amplitude-curve`. Direct lift, just with simpler labels for G8.

### What needed human judgment

1. **EM spectrum band placement** — real EM-spectrum charts use logarithmic wavelength axes (because radio is millions of times longer than gamma rays). This G8 figure uses *linear* placement instead, sacrificing accuracy for visual readability. Pedagogical call: at G8, "all light is one family ordered by wavelength" matters more than "the relative widths are accurate".

2. **VIBGYOR vs ROYGBIV** — Indian curriculum convention is VIBGYOR (violet-first), Western is ROYGBIV (red-first). Used VIBGYOR in this unit since StudyBuddy targets Indian + multi-region; future units should commit to one convention and stick to it. Curator-only choice.

3. **Compression/rarefaction line density** — 30 lines was hand-tuned. Fewer (15) makes the wave look sparse; more (50) makes the modulation hard to read. The spacing-modulation amplitude (4 px peak) was also tuned by eye.

### Time budget

Phase 1: ~45 min. Phase 2: ~10 min. Total: ~55 min vs 1.5-day estimate. Smallest Wave-2 unit so far — heavy reuse from G11-PHYS-010 and modest new primitives kept it tight.

## Phase 2

| eval id | section title | expected_entry_id |
|---|---|---|
| `eval-075` | All the Kinds of Light Are One Family | `physics-g8-electromagnetic-spectrum` |
| `eval-076` | Two Knobs on a Sound | `physics-g8-pitch-and-loudness` |
| `eval-077` | When Pushing in Time Makes Things Grow | `physics-g8-resonance-curve` |

Eval-077 anchors on the swing analogy explicitly — testing whether the resolver picks up everyday-object analogies as cues for physics concepts.

131/131 library rows seeded with non-NULL embeddings.

## Wave-2 cumulative budget

| Unit | Time |
|---|---|
| #332 (G7 atoms) | ~1 h |
| #333 (G10 organic) | ~1 h 27 m |
| #334 (G11 derivatives) | ~1 h 27 m |
| #335 (G8 waves) | ~55 m |
| **total so far** | **~4 h 49 m** |

vs. Wave-2 estimated total of ~9 days FTE (5 units × 1.5-2 days each). Process compression continuing at ~6×.

---
*Author: broker. Updated 2026-05-08 (all phases complete; #335 ready to close).*
