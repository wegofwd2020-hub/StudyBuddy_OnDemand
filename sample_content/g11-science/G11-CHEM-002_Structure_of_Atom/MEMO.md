# MEMO — G11-CHEM-002 Structure of Atom

> Per-unit learning memo. Captures patterns observed during hand-authoring
> for **#320 code-gen automation**'s spec input. Updated after each phase.

## Status

- **Phase 1 (Option 2 catalogue):** ✅ 13 SVGs + 13 sidecars shipped
- **Phase 2 (Option 3 Remotion clips):** pending — Bohr transition, electron-fill order
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

### Time budget

Phase 1: ~50 minutes (helper toolkit + 13 figure functions + sidecar specs + 1 round of validation fixups). Wave-1 issue estimated 2 days for the whole unit; first-class generator-building work tracks more like #327 than #328.

---
*Author: broker. Updated 2026-05-07 (Phase 1 complete).*
