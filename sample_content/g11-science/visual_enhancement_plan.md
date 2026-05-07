# Visual Enhancement Plan — Grade 11 Science (CBSE-aligned)

**Date:** 2026-05-07
**Curriculum:** `default-2026-g11-science`
**Source:** [`data/grade11_science.json`](../../data/grade11_science.json)
**Reference doc:** [`docs/visual_presentation_research.md`](../../docs/visual_presentation_research.md)
**GitHub issue:** [#315](https://github.com/wegofwd2020-hub/StudyBuddy_OnDemand/issues/315)

> Per-unit assessment of every Grade 11 Science topic, mapped to one of the three visual-presentation techniques we built (Option 1 interactive HTML, Option 2 per-example catalogue, Option 3 Remotion video). The reference exemplar is `G11-MATH-001 Sets and Functions` — its full artifact tree lives at `sample_content/g11-science/G11-MATH-001_Sets_and_Functions/`.

## How to read this catalog

Each unit gets a recommendation that is **opinionated**, not an inventory. We're answering the question *"would investing build-time on visuals produce comprehension lift here?"* — not *"could we add a visual?"*. The default answer is no; we only flag where the lift is real.

| Column | Meaning |
|---|---|
| **Visual primitives** | Concrete kinds of visual the topic naturally contains. Drawn from the tutorial section titles, not invented. |
| **Recommended option** | Which of the 3 techniques fits — `1`, `2`, `3`, combinations, or `—` for "no enhancement worth the cost". |
| **Lift** | Comprehension gain over plain Markdown + KaTeX: **S** small, **M** moderate, **L** large. Anything below S we mark `—`. |
| **Effort** | Build cost: **S** ≤ 1 day, **M** 2–3 days, **L** ≥ 1 week. Animations and 3D structures are the expensive ones. |

---

## Per-subject summary

| Subject | Units | High-lift count (M+L) | Dominant primitive | Strongest technique fit |
|---|---:|---:|---|---|
| **Mathematics** | 5 | 5 / 5 | Plots, set / arrow diagrams, animated transformations | Option 1 (interactive plots) + Option 2 (SVG diagrams) + Option 3 (Calculus animations) |
| **Physics** | 10 | 9 / 10 | Free-body diagrams, time-series plots, vector fields, animated trajectories | Option 2 (FBDs as SVG) + Option 3 (motion / wave animations) |
| **Chemistry** | 9 | 7 / 9 | Molecular structures, reaction mechanisms, orbital diagrams, periodic trends | Option 2 (molecular SVG / Lewis structures) — heaviest lift |
| **Biology** | 5 | 5 / 5 | Labeled anatomy, taxonomy trees, cycles (mitosis, photosynthesis), pathways | Option 2 (anatomy SVG) + Option 3 (cycle animations) |

**Headline:** 26 of 29 units (90 %) have **moderate or large lift** from visual enhancement. The remaining 3 are concept-heavy or table-driven and don't earn animation cost.

---

## Mathematics (5 units)

| Unit | Topic | Visual primitives | Option | Lift | Effort | Notes |
|---|---|---|---|---|---|---|
| **G11-MATH-001** | **Sets and Functions** | Venn, power-set lattice, arrow diagrams, function plots, transformation animation, projectile | **All 3** | L | L | **REFERENCE EXEMPLAR.** Full artifact tree shipped at `G11-MATH-001_Sets_and_Functions/` covering all 12 visual targets. |
| G11-MATH-002 | Algebra (induction, complex numbers, permutations / combinations) | Induction-step illustrations, complex plane (Argand) plot, permutation / combination tree diagrams | **2 + 1** | M | M | Argand plane is Plotly-perfect with sliders; permutation trees are Mermaid-native; induction is harder to visualize — animation may help. |
| G11-MATH-003 | Coordinate Geometry (lines, conics, 3D intro) | Cartesian plots, slope / intercept variations, circle equations, conic-section family, 3D axes | **All 3** | L | L | Plotly with sliders is the killer feature — students *see* how `(h, k, r)` move a circle. Conic-section family is Plotly-perfect (vary eccentricity). 3D intro begs for a brief Remotion clip. |
| G11-MATH-004 | Calculus (limits, derivatives) | Limit visualizations (zoom-in animations), tangent-line slope as Δx → 0, derivative-from-graph reading | **3 + 1** | L | M | **Animation makes or breaks calculus intuition.** Remotion clip showing tangent-line emergence is high-leverage; interactive plot of $f(x)$ + $f'(x)$ as Plotly is the second hit. |
| G11-MATH-005 | Statistics and Probability | Histograms, box plots, scatter plots, probability trees, Venn (events) | **2 + 1** | M | M | Histograms / box plots / scatter are SVG cheap. Probability trees are Mermaid. Plotly adds slider-driven distributions for advanced framing. |

---

## Physics (10 units)

| Unit | Topic | Visual primitives | Option | Lift | Effort | Notes |
|---|---|---|---|---|---|---|
| G11-PHYS-001 | Physical World & Measurement | Dimensional-analysis tables, SI-unit hierarchy, error-propagation diagrams | **2** (SVG only) | S | S | Tables and unit charts are markdown-native. Lightest lift in physics. |
| **G11-PHYS-002** | **Kinematics** | Position–time, velocity–time, acceleration–time graphs; vector decomposition; **projectile-motion animation** | **All 3** | L | M | **BUILT (issue [#317](https://github.com/wegofwd2020-hub/StudyBuddy_OnDemand/issues/317)).** 15 SVGs + 4 Remotion clips wired into `/tutorial/G11-PHYS-002`. Artifacts: [`G11-PHYS-002_Kinematics/`](G11-PHYS-002_Kinematics/). |
| G11-PHYS-003 | Laws of Motion | Free-body diagrams, friction-cone diagrams, circular-motion vector fields | **2** | L | M | Free-body diagrams are the canonical physics SVG — every textbook has them. Build a TS spec generator like the arrow-diagram one and render dozens cheaply. |
| G11-PHYS-004 | Work, Energy, Power | Energy-bar diagrams, force–displacement plots, collision animations (1D and 2D) | **2 + 3** | L | M | Bar-energy diagrams are high-lift static SVG. Collision animations (elastic vs inelastic) are perfect Remotion. |
| G11-PHYS-005 | Rigid Body | Centre-of-mass diagrams, moment-of-inertia comparison shapes, angular-momentum vectors | **2 + 3** | M | M | MoI for different shapes is a comparison table + side-by-side SVG. Spinning-top precession is a great Remotion clip. |
| G11-PHYS-006 | Gravitation | Kepler-orbit ellipses, satellite-trajectory animations, gravitational-field lines | **3 + 2** | L | M | Animation of an elliptical orbit with $r$, $v$ vectors is high-leverage. Field-line SVGs are static but visually anchoring. |
| G11-PHYS-007 | Properties of Bulk Matter | Stress–strain curves, fluid-flow diagrams, Pascal's principle, surface tension | **2 + 1** | M | M | Stress–strain plots are Plotly. Pascal's-principle and capillary-action diagrams are SVG. |
| G11-PHYS-008 | Thermodynamics | P–V diagrams, Carnot-cycle path, heat-engine flow diagrams | **1 + 3** | L | M | P–V is Plotly-perfect (interactive paths). **Carnot-cycle animation** showing the four reversible steps is one of the highest-leverage physics Remotion clips. |
| G11-PHYS-009 | Kinetic Theory of Gases | Molecular-motion animation, Maxwell-Boltzmann distribution, mean-free-path visual | **3 + 1** | L | M | A Remotion clip of molecules in a box at varying temperature is unforgettable. Maxwell-Boltzmann curve is Plotly with a temperature slider. |
| **G11-PHYS-010** | **Oscillations and Waves** | SHM animation, damped / forced oscillation, wave superposition, beats, **Doppler effect** | **All 3** | L | L | **Highest visual-lift physics topic.** Every section animates. Doppler is the classic explainer-video target. Strong third exemplar candidate. |

---

## Chemistry (9 units)

| Unit | Topic | Visual primitives | Option | Lift | Effort | Notes |
|---|---|---|---|---|---|---|
| G11-CHEM-001 | Some Basic Concepts | Mole-conversion flowcharts, stoichiometry tables, limiting-reagent worked examples | **2** | S | S | Mostly tables and worked examples. Markdown-native. |
| **G11-CHEM-002** | **Structure of Atom** | **Orbital diagrams (s, p, d, f shapes)**, Bohr-model animation, electron-configuration filling, atomic-spectra line diagrams | **2 + 3** | L | L | Orbital shapes are unintuitive without 3D visuals. Bohr-model electron transitions are perfect Remotion. **Strong fourth exemplar candidate.** |
| G11-CHEM-003 | Periodicity | Periodic-table heat maps (radius / IE / EA / EN trends), trend curves across periods | **1** | M | S | Plotly + interactive periodic-table heatmap. Sliders to switch trends. |
| G11-CHEM-004 | Chemical Bonding & Molecular Structure | Lewis structures, VSEPR shapes, hybridisation diagrams, molecular geometry, hydrogen-bonding diagrams | **2** + 3D models | L | L | **Heaviest chemistry lift.** Lewis structures + VSEPR shapes are SVG (build a TS generator). 3D models are an open question — Desmos / iframe vs static SVG. Per issue [#316](https://github.com/wegofwd2020-hub/StudyBuddy_OnDemand/issues/316). |
| G11-CHEM-005 | Chemical Thermodynamics | Enthalpy-change diagrams, energy-profile diagrams, Hess-cycle diagrams | **2** | M | M | Energy-profile (reaction-coordinate) diagrams are the high-leverage visual. Static SVG covers it. |
| G11-CHEM-006 | Equilibrium | Equilibrium-position curves, pH titration curves, buffer-region plots | **1** | M | M | Titration curves are Plotly with sliders for $K_a$ / concentration. High interactive lift. |
| G11-CHEM-007 | Redox Reactions | Oxidation-state ladders, half-reaction diagrams, electrochemical-cell schematics | **2** | M | M | Oxidation-ladder is a Hasse-style SVG. Cell schematics are Mermaid-friendly. |
| **G11-CHEM-008** | **Organic Chemistry — Basic Principles** | **Skeletal structures, isomer comparisons, reaction-mechanism arrows, IUPAC naming flowcharts** | **2** (heavy) | L | L | Organic-chem visualization is its own discipline. Mechanism arrows on skeletal structures are the canonical SVG — large catalog effort but unavoidable for the unit to land. |
| G11-CHEM-009 | Hydrocarbons | Skeletal structures (alkanes / alkenes / alkynes), aromatic resonance, reaction pathways | **2** (heavy) | L | L | Same authoring infrastructure as 008 — once you have the skeletal-structure SVG generator, this unit reuses it. |

---

## Biology (5 units)

| Unit | Topic | Visual primitives | Option | Lift | Effort | Notes |
|---|---|---|---|---|---|---|
| G11-BIO-001 | Diversity of Living Organisms | Taxonomy trees (5 kingdoms), comparison tables (plant vs animal kingdoms), classification flowcharts | **2** (Mermaid) | M | S | **Mermaid is a perfect fit for taxonomy trees** — declarative, scalable, accessible. Comparison tables are GFM-native. |
| G11-BIO-002 | Structural Organisation in Plants and Animals | Labeled cross-sections (root, stem, leaf), tissue diagrams, animal-body-plan diagrams | **2** (heavy) | L | L | Labeled biological diagrams are SVG-heavy by nature. Each cross-section is a polished standalone artifact. |
| **G11-BIO-003** | **Cell: Structure and Functions** | **Organelle ultrastructure**, plasma-membrane (fluid mosaic), **mitosis / meiosis animations**, biomolecule structures (DNA, proteins) | **2 + 3** | L | L | Organelle SVG is a one-time investment used by 4+ subsequent units. **Mitosis and meiosis animations are the canonical biology Remotion clip.** |
| G11-BIO-004 | Plant Physiology | **Photosynthesis pathway**, transpiration cycle, respiration cycle, mineral-uptake flow | **3 + 2** | L | M | Photosynthesis (light + Calvin) and respiration (glycolysis + Krebs + ETC) are pathway-cycle animations. Remotion is built for this. |
| G11-BIO-005 | Human Physiology | Digestive-tract diagram, alveolar gas exchange, **circulatory animation**, neural pathway, excretory system | **2 + 3** | L | L | Each system is a labeled SVG. Circulatory animation (heart cycle + blood-flow direction) is high-leverage. Reuses the organelle SVG library from BIO-003. |

---

## Where to start (priorities)

Build order if we're picking *exemplars beyond G11-MATH-001*, ranked by lift × leverage:

1. **G11-PHYS-002 Kinematics** — graphical motion + projectile already match Sets-and-Functions's Option 3 video shape exactly. Nearly free to clone the Remotion scaffold.
2. **G11-PHYS-010 Oscillations and Waves** — SHM, beats, Doppler — best video material in the entire curriculum.
3. **G11-BIO-003 Cell Structure** — mitosis/meiosis animations + reusable organelle SVG library serves 4 downstream units.
4. **G11-CHEM-002 Structure of Atom** — orbital shapes break a real cognitive barrier without 3D visuals.
5. **G11-MATH-004 Calculus** — tangent-line emergence animation is the single highest-leverage math clip after the Sets-and-Functions transformation animation.

Each of these has high lift AND large reuse downstream — investing the build effort once produces a library that lifts adjacent units.

## Where NOT to invest first

- **G11-PHYS-001 Physical World & Measurement** — table-heavy; markdown plus a few SI-unit charts is sufficient.
- **G11-CHEM-001 Some Basic Concepts** — stoichiometry is calculation, not visualisation.
- **G11-MATH-002 Algebra** (induction portion) — induction visualisations exist but rarely add comprehension over a worked example.

These are not "no visual ever" — they're "not in the first wave."

## Effort summary

| Effort tier | Units | Total estimate |
|---|---:|---|
| Already done (G11-MATH-001) | 1 | shipped |
| **S** (≤ 1 day each) | 3 | 3 days |
| **M** (2–3 days each) | 11 | ~30 days |
| **L** (≥ 1 week each) | 14 | ~14 weeks |

Total order-of-magnitude: **~4 months for the full G11 Science visual catalog** at 1 FTE-equivalent, assuming the SVG generator and Remotion scaffold from `G11-MATH-001` are reused (they will be — most of the helper code is unit-agnostic).

## Open questions

- [ ] **Issue [#316](https://github.com/wegofwd2020-hub/StudyBuddy_OnDemand/issues/316)** — what's the preferred render format per visual kind? This catalog assumes the L3 decisions land first; rebuild costs change if we pick differently.
- [ ] Does the pipeline emit structured visual-block declarations, or do we author SVG / MP4 outside the pipeline and reference them by static URL?
- [ ] Manim vs Remotion for animations — port to Remotion (TS-only) is recommended once we have more than two animations to maintain.
- [ ] How does this rank against G12 Science, G11 Commerce, etc.? Cloning this analysis to other curricula is a separate exercise once G11 Science visuals ship.

## Cross-references

- Reference exemplar: [`G11-MATH-001_Sets_and_Functions/`](G11-MATH-001_Sets_and_Functions/) — Options 1, 2, and 3 already built.
- Research framing: [`docs/visual_presentation_research.md`](../../docs/visual_presentation_research.md)
- Issue [#315](https://github.com/wegofwd2020-hub/StudyBuddy_OnDemand/issues/315) — original assessment ask (this doc is its output).
- Issue [#316](https://github.com/wegofwd2020-hub/StudyBuddy_OnDemand/issues/316) — render-format decision (blocks production rebuilds).
