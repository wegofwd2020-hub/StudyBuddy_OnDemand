# MEMO — G11-CHEM-002 Structure of Atom

> Per-unit learning memo. Captures patterns observed during hand-authoring
> for **#320 code-gen automation**'s spec input. Updated after each phase.

## Status

- **Phase 1 (Option 2 catalogue):** ✅ 13 SVGs + 13 sidecars shipped
- **Phase 2 (Option 3 Remotion clips):** ✅ 2 clips rendered — `StructureOfAtom_BohrTransition.mp4` (2.1 MB / 24 s), `StructureOfAtom_ElectronFill.mp4` (1.8 MB / 24 s)
- **Phase 3 (eval set + library promotion):** pending

## Phase 1 reflections — Option 2 catalogue

The 13 SVGs land in four sections that follow the historical/conceptual arc of the unit (Discovery → Models → Quantum → Configuration & Spectra):

| Section | Visuals |
|---|---|
| `section-1-discovery` | `cathode-ray-experiment`, `rutherford-gold-foil`, `subatomic-particles-comparison` |
| `section-2-atomic-models` | `thomson-plum-pudding`, `rutherford-nuclear-model`, `bohr-shell-model` |
| `section-3-orbitals` | `s-orbital`, `p-orbitals`, `d-orbitals`, `quantum-numbers-tree` |
| `section-4-electron-config-spectra` | `aufbau-diagonal-rule`, `hydrogen-emission-spectrum`, `orbital-diagram-nitrogen-hund` |

This is the **first chemistry primitive class**, so unlike the G9 unit which lifted physics-kinematics infra wholesale, this one introduces a fresh palette of drawing primitives.

### What was repetitive (= templatable for #320)

1. **Concentric-shell layout** — the Bohr model and the Rutherford planetary model share the same skeleton (nucleus + concentric circles + electrons placed at angular positions). **Recommendation for #320:** template `<ConcentricShells nucleus electronCounts={[2,8,5]} radii={[50,95,145]} />`. Reusable across G11-CHEM-002, G12-PHYS-007 (atomic structure), G7-SCI-001 atoms (lighter version).

2. **Orbital-shape primitives** — every orbital figure is a small set of ellipses (lobes) arranged around a central nucleus. The `s` is one filled circle; `p` is three perpendicular dumbbells; `d` is four cloverleaves + one dumbbell-with-doughnut. **Recommendation:** `<Orbital kind="s" | "p" | "d" />` shared component. Used here, and again in G12-CHEM-004 (transition metals), G10-SCI-004 (organic chemistry hybrid orbitals).

3. **Particle markers** — proton (red, "p⁺"), neutron (slate, "n⁰"), electron (blue, "e⁻"), photon (yellow, "ν"). Identical styling across cathode-ray, Rutherford, Thomson, Bohr, orbital diagrams. **Recommendation:** define once at `pipeline/visual_templates/particles.ts`. Hard requirement: same colour for the same particle across every chemistry visual — students bind colour to identity, and inconsistency is the single biggest source of "this looks wrong" feedback in pilots.

4. **Energy-level ladder** — used here as a sub-element of the Bohr diagram. Same pattern will recur in `hydrogen-emission-spectrum` (rendered as wavelength axis instead, but conceptually the same), and in every future quantum-mechanics or atomic-structure unit. **Recommendation:** `<EnergyLadder levels={[{n:1,y:20},{n:2,y:80},...]} />`.

5. **Orbital-box diagrams (Hund / Pauli)** — `orbital-diagram-nitrogen-hund` is a row of empty rectangles with up/down arrows inside. Pattern recurs whenever you teach electron configuration or VSEPR. **Recommendation:** `<OrbitalBoxRow boxes={[{label:"1s",spins:[+1,-1]},{label:"2pₓ",spins:[+1]},...]} />`.

### What needed human judgment (= curator-only)

1. **Cathode-ray apparatus geometry.** The cathode tube + anode + deflection plates + screen layout is hand-tuned for legibility — proportions don't match real physics scale. The LLM would need explicit guidance on what to overstate (deflection angle, plate visibility) and what to keep small (electron beam thickness, anode size). **Recommendation:** ship this as a hand-authored exemplar in `pipeline/visual_templates/exemplars/`; don't try to auto-generate apparatus diagrams from prose.

2. **Rutherford gold-foil scattering paths.** Drawing the *right number* of straight-through paths vs slight-deflections vs back-scatters is a pedagogical choice (real ratio is ~1 in 10⁴ for back-scatter; the diagram shows roughly 1 in 6 for visibility). Curator-only.

3. **Hydrogen emission spectrum colour palette.** Hα is red (656 nm), Hβ is cyan-blue (486 nm), Hγ and Hδ shade into violet. Hand-picked perceptual colours that *approximate* spectral reality without being so dim that students can't see them on a black background. The LLM has no good prior for this; curator-led.

4. **d-orbital cloverleaf arrangement.** The four "between-axes" cloverleaves (d_xy, d_yz, d_xz) plus the one "on-axes" (d_x²−y²) plus the unique d_z² are notoriously hard to draw recognisably in 2D. Took several iterations to land on a layout where each is distinguishable. **Recommendation:** keep this as a hand-authored exemplar; the visual cost-benefit of trying to LLM-template it is poor.

### What fell outside code-gen entirely

Nothing in this Phase-1 set. Everything is 2D primitives + simple geometry — fully code-renderable. No real-world photos (e.g. of cathode-ray tubes in museums) included; if pilots show students benefit from those, add as `kind: "photo"` exceptions.

### Validator gotcha — YAML keyword auto-coercion

Three of the 13 sidecar specs initially failed validation:
- `"1904"` and `"1911"` (years used as keywords) — YAML auto-parses these as `int`; the validator then rejects them as `must be a string`. Fix: replaced with `historical-model`.
- `"K-L-M"` — uppercase rejected by `^[a-z0-9-]+$`. Fix: lowercase to `k-l-m`.

**Recommendation:** never use bare years or alphanumerics with uppercase as keywords. Better, the validator could coerce ints to strings and downcase before regex-checking — but that's a #322 concern, not this issue.

### Time budget (Phase 1)

Phase 1: ~50 minutes (helper toolkit + 13 figure functions + sidecar specs + 1 round of validation fixups). Wave-1 issue estimated 2 days for the whole unit; first-class generator-building work tracks more like #327 than #328.

## Phase 2 reflections — Option 3 Remotion clips

Two compositions, 24 s each:

### `structure-of-atom-bohr-transition` (2.1 MB)

A hydrogen atom diagram with three Bohr shells (n = 1, 2, 3). The electron orbits in n = 3 for several seconds (full revolution every ~5 s for legibility), then drops radially to n = 2 over 4 s. As it drops, a yellow photon emerges from the atom and travels diagonally to a wavelength axis on the right; the H-α line (656.3 nm, red) lights up with a glowing drop-shadow when the photon arrives. Energy ladder on the right shows the n = 3 → n = 2 ΔE arrow highlighted during the drop.

### `structure-of-atom-electron-fill` (1.8 MB)

Nine orbital boxes (1s | 2s | 2pₓ | 2p_y | 2p_z | 3s | 3pₓ | 3p_y | 3p_z) grouped by subshell brackets. Eighteen electrons fill in Aufbau order, one per second, with up-arrows in blue and down-arrows in amber. Hund's rule plays out visibly during 2p (B → C → N → O...) and 3p (Al → Si → P → S...). Configuration string and element name update synchronously; final state is **Argon (Z = 18, 1s² 2s² 2p⁶ 3s² 3p⁶)**.

### What was repetitive (= templatable for #320)

1. **Shell + electron position math** — same `cx + r·cos(θ), cy + r·sin(θ)` pattern from the kinematics+oscillations primitives (Doppler wavefront centres are computed the same way; SHM mass-on-spring uses 1D version). This is the third proof point that a `<RotatingPoint cx cy r theta />` primitive should ship in shared components.

2. **Photon emission as a moving glow** — radial-gradient fill + a small core circle, position interpolated linearly between two anchors. Re-usable for any "energy carrier crosses scene" animation: chemical-bond formation, signal-transduction biology clips, solar-panel physics, etc. **Recommendation:** `<EmittedParticle from to startFrame endFrame color />`.

3. **Spin-arrow up/down inside an orbital box** — `<SpinArrow x yTop yBot spin />` is the entire visual vocabulary of orbital-diagram animations. Already factored into ElectronFillScene as a sub-component; promote to shared library.

4. **Scrolling configuration string** — built from a list of (orbital, spin) tuples and a hardcoded subshell ordering. **Recommendation:** publish `buildConfig(electrons)` and `superscript(n)` as utilities; reused in every chemistry animation.

5. **Element-name array lookup by Z** — H..Ar list lives inline. Should ship as `pipeline/visual_templates/elements.ts` with the full Z=1..118 list (only first 18 needed for this clip; lithography-class clips will need 30, transition-metal clips need ~57).

### What needed human judgment (= curator-only)

1. **Photon trajectory choice.** The photon flies diagonally from atom centre to spectrum line. In real physics the photon goes in a random direction; restricting to "always toward the spectrum strip" is a pedagogical lie that makes the cause-and-effect visible. Curator-only call.

2. **Electron orbital speed.** ω ≈ 1.2 rad/s at radius 340 px gives a leisurely orbit the eye can follow. Real Bohr orbital frequencies are ~10¹⁵ Hz — invisible. The animation deliberately runs at human time. The LLM has no good prior for "what speed makes this readable"; curator-led.

3. **Hund's rule visibility timing.** The 1-second-per-electron pacing was chosen specifically so the 2p triple-up sequence (B → C → N) is a noticeable rhythm: three single up-arrows, *then* three pairs. Faster pacing collapses the rule into invisibility. Worth noting in the #320 spec: animations teaching a *rule* must give the rule its own visual beat.

4. **End at Argon, not some heavier element.** Argon's full 3p shell is visually satisfying — the animation lands on a complete row. Going to potassium (Z=19) would land on a half-filled 4s and feel unfinished. Same is true for Beryllium → Boron transitions in slower clips. End-frame design is its own pedagogical choice.

### What fell outside code-gen entirely

Nothing in this clip set. Pure 2D animations + math.

### Time budget reconciliation (Phase 2)

Estimated half-of-2-days-roughly = ~1 day; **actual: ~40 minutes authoring + ~3 minutes render time**. The infra-mirror-from-prior-units pattern continues to compress wall time. The new content is the two scene files (~285 LoC for Bohr, ~265 LoC for ElectronFill) plus a small theme.ts addition for the chemistry particle palette.

## Time budget summary

| Phase | Issue estimate | Actual |
|---|---|---|
| Phase 1 | ~1 day | ~50 min |
| Phase 2 | ~0.5 day | ~40 min |
| Phase 3 | (rolled into 2 d) | pending |

This is the **first chemistry primitive class**, so naïvely it should track #327 (~3h 15m for the first oscillations unit). Tracking comparable so far. Subsequent same-class chemistry units (G7-SCI-001 atoms, G12-CHEM-004 transition metals) should land in <30% of this unit's time once #320 lifts the orbital + Bohr + spin-arrow primitives into shared templates.

---
*Author: broker. Updated 2026-05-07 (Phase 2 complete).*
