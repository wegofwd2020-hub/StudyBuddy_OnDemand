# Visual-Library Automation Readiness — Synthesis

> **Purpose.** Aggregates findings from the 10 MEMO.md files written during
> Epic #326 (Visual Library Expansion, Wave 1+2). This doc is the canonical
> input spec for **#320 — AI-generated visuals (LLM-authors-source, not pixels)**.
> Every claim is cited back to a source MEMO so a downstream reviewer can
> verify against the original observation.
>
> **Wave 1+2 corpus.** 10 issues closed (#327–#336). 144 visual_library_entries
> seeded with non-NULL embeddings. 80 known-positive resolver eval records.
> 9 Remotion clips. ~14h 56m total wall time vs. ~19 FTE-days estimated.
>
> **Status:** post-#326. Predecessor to #340 (close-out generator lift to
> `pipeline/visual_templates/`) and #320 (LLM code-gen consumer).

---

## How to read this doc

Three buckets, three sections:

1. **Automatable** — patterns that recurred across multiple units, recognisable as templates the LLM can fill in given a small spec. The bulk of #320's work.
2. **Curator-only** — judgement calls (pedagogical sequencing, layout choices, perceptual hand-tuning) that remain human work even after #320 ships. Document but do not automate.
3. **Outside code-gen entirely** — content that should fall back to `kind: "photo"` sidecars rather than LLM-generated SVG.

A fourth section captures the **#320 input spec** explicitly — which templates to ship in `pipeline/visual_templates/` first, in priority order.

---

## 1. Automatable — what the LLM can fill in

### 1.1 Universal helpers (every generator)

Every one of the 10 generator scripts imported, byte-identical, the same micro-toolkit. Lift these into `pipeline/visual_templates/shared.ts` first — every downstream template depends on them.

| Helper | Signature | Source |
|---|---|---|
| `svgWrap(viewBox, title, desc, body)` | wraps SVG body with role/aria/title/desc | every MEMO |
| `write(section, name, svg)` | writes to `Option2_Catalogue/<section>/<name>.svg` | every MEMO |
| `makePlot(config: PlotConfig)` | axis frame + grid + ticks + labels | G9 §1.1, G11-PHYS-010 |
| `polyline(points, xToPx, yToPx, stroke, width, dash?)` | polyline data → SVG | G9 §1.1 |
| `mkdirSync(dir, { recursive: true })` | dest-dir creation per `write()` | every generator |

**Locked-in universal style tokens:**

| Token | Hex | Use |
|---|---|---|
| `INK` | `#1a202c` | text + structural lines |
| `MUTED` | `#4a5568` | secondary text |
| `ACCENT` | `#2b6cb0` | primary accent (blue) |
| `ACCENT_2` | `#dd6b20` | secondary accent (orange) |
| `ACCENT_3` | `#319795` | tertiary accent (teal) |
| `POSITIVE` | `#15803d` | success / current arrow |
| `NEGATIVE` | `#dc2626` | warning / opposing direction |
| `GRID` | `#e2e8f0` | grid lines |
| `AXIS` | `#94a3b8` | axis lines |
| `BG` | `#f7fafc` | plot background |

### 1.2 Cross-class primitives (mentioned in 3+ MEMOs)

These primitives recurred across multiple subject classes. Highest #320 leverage — ship in `pipeline/visual_templates/components/` ahead of any class-specific templates.

| Primitive | Mentioned in | Recommended signature |
|---|---|---|
| **`<LeaderLabel />`** | G6-SCI-001, G6-ENG-002, chemistry generators | `from to text color anchor` — short line + label at line-end |
| **`<DotCluster />`** | G6-SCI-001 (ribosomes), G11-CHEM-002 (electron clouds) | `cx cy rx ry count color size` |
| **`<MotionStrip />`** | G9-SCI-001, future G6 forces, G7 energy, G9 Newton's | `y color ballPositionPx visibleStrobeCount strobePositions label showSpacingMarkers` |
| **`<Spring />`** | G11-PHYS-010 (SHM), Hooke's law, mech-energy clips | `fromX endX y coils amp` |
| **`<RotatingPoint />`** | G11-PHYS-010 (SHM, Doppler), G11-CHEM-002 (Bohr orbits) | `cx cy r theta` |
| **`<EmittedParticle />`** | G11-CHEM-002 (photon emission), biology signal-transduction, physics solar | `from to startFrame endFrame color` |
| **`<SpinArrow />`** | G11-CHEM-002 (orbital boxes) | `x yTop yBot spin` |
| **`<SecantLine />`** | G11-MATH-002 (used in both SVG and Remotion verbatim) | `fn x1 x2 plot` |
| **`<SideBySideCards />`** | G9-SCI-001, G6-SCI-001, G6-ENG-002, G11-CHEM-002, G10-SCI-004 — **5 units** | `leftContent rightContent comparisonPanel` |
| **`<ReferenceCardGrid />`** | G11-CHEM-002, G6-ENG-002, G10-SCI-004 | `columns cards={[{title, body, color}]}` |
| **`<NumberedFlowchart />`** | G10-SCI-004 (IUPAC naming), future biology + physics method flowcharts | `steps={[{n, title, note}]}` |
| **`<StackedPlots />`** | G9-SCI-001, G11-PHYS-010, G11-MATH-002, G11-CHEM-002 — **4 units** | `plots={[{cfg, fn, color}]}` |
| **`<FormulaCard />`** | G11-MATH-002, G11-CHEM-002, G6-ENG-002 (Ohm's-law triangle) | `formula examples` |
| **`<LiveValuesPanel />`** | G6-ENG-002, G11-CHEM-002 (Bohr energy ladder), future Ohm's law / Newton's law | `rows={[{label, value, unit, color}]} equation` |
| **`<SceneTitle />`** | G11-PHYS-010, G9-SCI-001, G11-CHEM-002, G11-MATH-002, G6-ENG-002, G12-PHYS-005 — **every Remotion clip** | `title subtitle subSub` — spring + interpolate fade-in pattern |

The `<SceneTitle />` recurrence is universal: every Remotion scene authored across the wave starts with `titleScale = spring(...)`, `titleOp = interpolate([0,30], [0,1])`, `subOp = interpolate([20,60], [0,1])` — byte-identical across 9 clips. This is the most under-factored primitive in the corpus.

### 1.3 Class-specific primitives

These are class-specific but reused inside their class. Lift into `pipeline/visual_templates/<class>/`.

#### Physics — kinematics / oscillations / waves / optics

| Primitive | Recommended signature | Source |
|---|---|---|
| `time-series-plot` | `xRange yRange fn slopeAnnotation axisLabels` | G9 §1.1 — covers ~40% of physics-time-series catalogue |
| `slope-triangle` | `plot x1 x2 color dxLabel dyLabel` | G9 §1.1 |
| `single-plot`, `stacked-plots`, `multi-curve-plot`, `side-by-side-concept` | Sine/superposition/comparison templates | G11-PHYS-010 §1 — covers ~70–80% of oscillations catalogue |
| `free-body-diagram` | `bob_position vectors=[{name, direction, length, color}] pivot` | G11-PHYS-010 §1 — pendulum + reused in G9-SCI-002, G10-ENG-001 |
| `standing-wave-modes` | `harmonics=[1,2,3] color_palette` (closed-form solver embedded) | G11-PHYS-010 §1 |
| `doppler-wavefronts` | `vs cs Ttick xStart yBaseline` (parameterised primitive; LLM tunes constants only) | G11-PHYS-010 §1, §2 |
| `motion-strip` | `N spacing: 'equal' \| (i: number) => number color label` | G9 §1.1 |
| `colored-band-strip` | `bands={[{name, color, lambda}]} insetMagnify={...}` | G8-SCI-002 §1 — EM spectrum + visible light + future spectrum-comparison |
| `compression-rarefaction-cluster` | `count modulationAmp` — vertical lines with sinusoidally-modulated horizontal density | G8-SCI-002 §1 |
| `rayArrow`, `normalLine`, `angleArc` | `x1 y1 x2 y2 color` / `cx cy r ang1 ang2 color` | G12-PHYS-005 §1 |
| `<RayDiagramVertex />` | `incidentAngle refractedAngle showNormal showAngles` | G12-PHYS-005 §1 — Snell's, reflection, TIR |
| `<LensMirrorRayDiagram />` | `type='convex-lens' \| 'concave-lens' \| 'concave-mirror' \| 'convex-mirror' object={...}` | G12-PHYS-005 §1 |
| `cumulativePhase(frame)` integral pattern | piecewise integral of speed-by-regime | G6-ENG-002 §2, G11-PHYS-010 §2, G9-SCI-001 §2 — **3 units** |

#### Chemistry — atoms / orbitals / periodic table

| Primitive | Recommended signature | Source |
|---|---|---|
| `<ConcentricShells />` | `nucleus electronCounts={[2,8,5]} radii={[50,95,145]}` — Bohr / Rutherford skeleton | G11-CHEM-002 §1 |
| `<Orbital kind="s\|p\|d" />` | shape primitives (s = filled circle, p = three perpendicular dumbbells, d = four cloverleaves + dumbbell-with-doughnut) | G11-CHEM-002 §1 |
| **Particle constants** | proton red `p⁺`, neutron slate `n⁰`, electron blue `e⁻`, photon yellow `ν` — **must be identical across every chemistry visual** (students bind colour to identity) | G11-CHEM-002 §1 |
| `<EnergyLadder />` | `levels={[{n:1,y:20},{n:2,y:80},...]}` | G11-CHEM-002 §1 |
| `<OrbitalBoxRow />` | `boxes={[{label:"1s",spins:[+1,-1]},{label:"2pₓ",spins:[+1]},...]}` | G11-CHEM-002 §1 |
| `<MiniBohrAtom />` | `Z size` — composable into "many atoms in a grid" diagrams | G7-SCI-001 §1 |
| `<HeatmapTile />` | `element value range palette` | G7-SCI-001 §1 |
| `<PeriodicTrendHeatmap />` | `data trendKey palette legend` | G7-SCI-001 §1 |
| `<PeriodicTableGrid />` | `cellRenderer={(el) => ReactNode}` | G7-SCI-001 §1 |
| `tileXY(group, period)` | maps to (x, y) on fixed-spacing periodic grid | G7-SCI-001 §1 |
| `buildConfig(electrons)` + `superscript(n)` | electron-configuration string utilities | G11-CHEM-002 §2 |
| **`elements_data.ts`** | canonical Z=1..118 element table — currently Z=1..36 in G7-SCI-001 generator, grow mechanically | G7-SCI-001 §1 |

#### Organic chemistry (skeletal structures)

The `generate_organic_chemistry_visuals.ts` generator is the highest-density primitive class — 8 reusable functions cover the entire catalogue.

| Primitive | Signature | Source |
|---|---|---|
| `zigzagPoints(x0, y0, n, parity)` | N alternating-up/down vertex positions | G10-SCI-004 §1 |
| `singleBond(x1, y1, x2, y2, color?, width?)` | straight bond | G10-SCI-004 §1 |
| `doubleBond(x1, y1, x2, y2, color?)` | two parallel lines with perpendicular offset | G10-SCI-004 §1 |
| `tripleBond(x1, y1, x2, y2, color?)` | three parallel lines | G10-SCI-004 §1 |
| `atomLabel(x, y, text, color, fontSize?)` | functional-group attachment label | G10-SCI-004 §1 |
| `alkaneZigzag(x0, y0, n, startsLow?)` | full N-carbon backbone — composes zigzagPoints + singleBond | G10-SCI-004 §1 |
| `hexagon(cx, cy, r, color?)` | benzene/cyclohexane ring | G10-SCI-004 §1 |
| **Functional-group palette** | OH=red, C=O=deep-red, NH₂=blue, X=green, ring=purple — **lock as constants** | G10-SCI-004 §1 |
| `<MoleculeStructure />` | `parent={n_carbons} substituents={[{position, group}]}` (composable) | G10-SCI-004 §1 |
| `<WorkedExample />` | `structure steps finalAnswer` — same shape as Bohr-transition energy-ladder | G10-SCI-004 §1 |

#### Biology — cells, anatomy

| Primitive | Recommended signature | Source |
|---|---|---|
| **Organelle palette (locked)** | nucleus `#7c3aed`, mitochondrion `#dc2626`, chloroplast `#16a34a`, vacuole `#7dd3fc`, cytoplasm `#fef9c3`, cell membrane `#94a3b8`, plant cell wall `#a16207`, golgi `#f59e0b`, rough ER `#ea580c`, lysosome `#f472b6`, ribosomes `#7c2d12`, centrosome `#64748b` — **carry into every downstream biology unit** | G6-SCI-001 §1 |
| `<DoubleMembrane />` | `outerR innerR color` — nucleus envelope, mitochondrion, chloroplast | G6-SCI-001 §1 |
| `<StackedFolds />` | `count xCenter yCenter foldShape color` — Golgi, thylakoid grana, ER | G6-SCI-001 §1 |
| Bézier blob shapes | parameterised "N-vertex organic outline" via `M ... Q ... T ...` SVG path commands | G6-SCI-001 §1 |

**Biology layout note (curator-led):** when an LLM template asks for "N organelles", **randomise positions/angles within bounds** rather than gridding them. Visual organicism > geometric precision. Cited: G6-SCI-001 §1 — animal cell mitochondria placed at hand-tuned `-20°`, `35°`, `-50°` for organic feel.

#### Engineering — circuits

The `generate_electronics_circuit_visuals.ts` generator ships **9 reusable circuit primitives** that 6 downstream units (G8-SCI-003, G10-ENG-002, G11-ENG-003, G12-PHYS-002, G12-PHYS-008) will lift.

| Primitive | Signature | Source |
|---|---|---|
| `wire(x1,y1,x2,y2,color?)` | basic line, locked stroke width | G6-ENG-002 §1 |
| `node(x,y,color?)` | junction dot | G6-ENG-002 §1 |
| `resistor(cx,cy,orient,label?)` | brown zigzag (US style); h/v orientation | G6-ENG-002 §1 |
| `batteryCell(cx,cy,orient,label?)` | single cell, long+short lines | G6-ENG-002 §1 |
| `battery(cx,cy,orient,label?)` | two cells stacked | G6-ENG-002 §1 |
| `lamp(cx,cy,r,lit?,label?)` | circle-with-X; lit toggles colour fill + glow | G6-ENG-002 §1 |
| `switchSymbol(cx,cy,open,label?)` | hinged lever; open vs closed pose | G6-ENG-002 §1 |
| `capacitor(cx,cy,orient,label?)` | two parallel lines, h/v orientation | G6-ENG-002 §1 |
| `led(cx,cy,lit?,label?)` | triangle+bar+arrows; lit toggles glow + arrow opacity | G6-ENG-002 §1 |
| `currentArrow(x,y,dir,label?)` | green triangle on a wire; up/down/left/right | G6-ENG-002 §1 |
| `<RectangularLoop />` | `topComponents bottomComponents leftComponents rightComponents` — half the layout work in any unit | G6-ENG-002 §1 |
| `<CurrentTrace />` | `edges=[(start,end),...] label` — distributes arrows along path | G6-ENG-002 §2 |
| `loopXY(phase, vertices)` | maps phase ∈ [0,1) to (x,y) on a closed polygon perimeter | G6-ENG-002 §2 |

**Locked-in circuit palette** (G6-ENG-002 §1): wires `#1a202c`, resistor `#92400e`, battery+ `#dc2626`, battery− `#1a202c`, capacitor `#2b6cb0`, LED body `#dc2626` / glow `#fbbf24`, lamp `#fbbf24`, switch `#4a5568`, current arrow `#15803d`, junction node `#1a202c` (r=4).

#### Math — calculus

| Primitive | Signature | Source |
|---|---|---|
| `<CurveWithTangent />` | `fn x` | G11-MATH-002 §1 |
| `<CurveWithSecant />` | `fn x1 x2` | G11-MATH-002 §1 |
| `secantLine(fn, x1, x2, ...)` | line through two points on a function, extended across visible plot — **lifts verbatim into Remotion** | G11-MATH-002 §1, §2 |

### 1.4 Remotion infra (all 9 clips, byte-identical)

The wave's most-replicated boilerplate. Lift into a single generator: `pipeline/visual_templates/remotion_project.ts` taking `{slug, scenes: [{id, durationSec, component}]}` and stamping the entire infra layer.

| File | Variability |
|---|---|
| `package.json` | name + render script names; deps + version pins are fixed |
| `tsconfig.json` | byte-identical |
| `remotion.config.ts` | byte-identical |
| `src/index.ts` | byte-identical |
| `src/theme.ts` | byte-identical universal palette + per-class additions |
| `src/Root.tsx` | per-unit composition list + durations |
| `package.json zod pin` | **must match Remotion's expected version** (currently `4.3.6` for `@remotion/cli@4.0.458`) — see G11-PHYS-010 §2 papercut note |

After lift, per-unit human work shrinks to writing the scene file (`src/scenes/<Name>Scene.tsx`).

### 1.5 Eval-record + library-promotion automation

Every Phase 3 across 8 of 10 units (and Phase 2 in the two no-Remotion units) followed an identical 4-step ritual:

1. Append eval records → validate JSON
2. `docker cp sample_content/<unit_dir>` into `/tmp/seed/sample_content/` *(retired by #339 — bind mounts now permanent)*
3. Run `python3 /app/scripts-repo/seed_library_local.py` *(post-#339 invocation)*
4. SELECT verify rows + embeddings

**Recommendation for #320:** ship a per-unit eval-record generator that takes `[(visual_id, section_title, prose), ...]` and stamps the JSONL. Then the per-unit pipeline is `generator → seeder → eval-runner` end-to-end.

---

## 2. Curator-only — judgement that does not automate

These items recurred across MEMOs and remain human work after #320 ships. They should appear in #320's prompts as **constraints supplied to the LLM**, not patterns the LLM is asked to invent.

### 2.1 Pedagogical sequencing

- **Show before tell.** Eval prose, animation captions, and worked-example layouts all share this convention: describe what the student sees first, name it second. Cited in 5 MEMOs (G11-PHYS-010 §3, G9-SCI-001 §3, G6-SCI-001 §2, G11-CHEM-002 §3, G6-ENG-002 §3). The resolver-LLM behaviour validates this — appearance-first prose hits known-positives more reliably.
- **Order matters in animations.** G6-ENG-002's "voltage doubles → resistance doubles" sequence (V first, R second) follows the intuition order. G11-CHEM-002's "secant → tangent → limit-of-secants → derivative-as-function" follows the conceptual ladder. Reverse orders are technically correct but pedagogically wrong.
- **End-frame design.** G11-CHEM-002 ElectronFill ends at Argon (full 3p shell, visually satisfying), not Potassium (half-filled 4s, looks unfinished). #320 prompts should cap animation-end-points at "completion" landmarks.

### 2.2 Layout + composition decisions

- **Organelle positions in cells.** G6-SCI-001 §1: leader lines must not cross; organelles must not overlap; each must be visible from outside. Hand-tuned positioning. **The LLM has no good prior here** — supply explicit positioning constraints in the prompt.
- **Component placement on circuit loops.** G6-ENG-002 §1: switches conventionally on the wire entering the load; battery at the bottom; load on top. LLM tends to randomise — supply explicit placement rules.
- **Mirror arc curvature** + **biconcave lens shape.** G12-PHYS-005 §1: hand-tuned SVG `<path d="...">` data; the visual sweetspot for "this reads as mirror/lens" is fragile. **Ship as exemplar SVGs in `pipeline/visual_templates/exemplars/`**, not as parametric generators.
- **d-orbital cloverleaf arrangement.** G11-CHEM-002 §1: notoriously hard to draw recognisably in 2D. Hand-authored exemplar; LLM-template attempts have poor cost-benefit.
- **Cyclohexane chair drawing.** G10-SCI-004 §1: hand-tuned simplification omitting axial/equatorial detail. Ship as exemplar at G10 level.

### 2.3 Perceptual hand-tuning

- **Animation pacing.** Electron-orbital speed (~1.2 rad/s in G11-CHEM-002), strobe-dot 1-second-per-electron pacing, cumulativePhase secant-shrink schedule (Δx = 2.5 → 0.05 over 10 s in G11-MATH-002), wavefront emission cadence in Doppler. **The LLM has no good prior for "what speed makes this readable"** — supply timing constants per template.
- **Dot density** (G6-ENG-002 §2): 12 dots around a 2400-px perimeter — sparse enough to track individual dots, dense enough to feel populated. Hand-tuned.
- **Compression-rarefaction line count** (G8-SCI-002 §1): 30 lines was the readable sweetspot. Fewer = sparse; more = unreadable.
- **Wavefront accumulation count** (G12-PHYS-005 §2): the optics-interference clip's 66.6 MB output was driven by ~30 concurrent wavefronts/source compressing poorly into h264. **Recommended cap: 8–10 visible wavefronts** at any given frame.

### 2.4 Pedagogical lies (deliberate, named)

These are *intentionally* unphysical choices the curator made for clarity. The LLM must not "fix" them:

- **Hydrogen emission spectrum colours** (G11-CHEM-002 §1): hand-picked perceptual colours that approximate spectral reality without being unreadably dim. Keep curator-supplied.
- **Photon trajectory toward spectrum strip** (G11-CHEM-002 §2): real photons go in random directions; the deliberate trajectory makes cause-and-effect visible. Curator-only.
- **Rutherford gold-foil scattering ratio** (G11-CHEM-002 §1): real ~1 in 10⁴ for back-scatter; the diagram shows ~1 in 6 for visibility.
- **EM spectrum linear placement** (G8-SCI-002 §1): real charts use logarithmic wavelength axes; G8-friendly version uses linear.
- **Both-bulb-broken side-by-side comparison** (G6-ENG-002 §1): pedagogically richer than two intact circuits side-by-side. LLM defaults to intact.

### 2.5 Grade-level translations

- **G6-friendly nicknames** (G6-SCI-001 §1): "powerhouse" alongside "mitochondrion"; "control center" alongside "nucleus"; "the jelly" alongside "cytoplasm". Curator-supplied per grade.
- **"Water-loving / water-fearing"** instead of "hydrophilic / hydrophobic" at G6 level.
- **"Push-flow-friction"** instead of "voltage-current-resistance" at G6 (G6-ENG-002 §3 eval prose).

### 2.6 Eval prose authoring (the only Phase-3 curator-only step)

- **Always describe what's about to be shown, not the visual itself.** G9-SCI-001 §3: *"Plot speed against time and the points fall on a straight line that climbs through the origin"* > *"a straight line on a speed-time plot"*.
- **Don't keyword-stuff.** Across 80 eval records, the section_title and prose deliberately avoid the entry's name verbatim (no "Rutherford", "p-orbital", "Aufbau", "tangent", "diffraction" in the prose). The resolver wins on semantics.
- **Period-detail anchors recognition** (G11-CHEM-002 §3): "early 1900s tabletop experiment fired a stream of small positively-charged particles" uniquely identifies Rutherford without naming him. Compound anchors > single keywords.
- **Procedural prose for rule visuals** (G11-CHEM-002 §3): the Aufbau prose mirrors the diagonal sweep step-by-step. Prose-mirrors-diagram alignment maximises resolver hit-rate.

---

## 3. Outside code-gen entirely — `kind: "photo"` exceptions

### 3.1 Confirmed needs (flag for sourcing)

- **Real microscopy photographs** (G6-SCI-001 §1.4): for downstream G9-SCI-005 Cell Division stages and G12-BIO histology, real images would teach better than stylised SVGs. Source from CC-BY-SA repositories (Biology Stock Center, Cell Image Library, MIT Biopics).
- **Real-component photos** (G6-ENG-002 §1.4): if pilots show students benefit, add `kind: "photo"` exceptions for `resistor-anatomy`, `capacitor-anatomy`, `battery-and-cell-anatomy` — the three figures already split into "real component | schematic" panels.
- **Vintage-lab photographs** (G11-CHEM-002 §1.4): museum cathode-ray tubes, gold-foil apparatus replicas — flag for future units; not blocking #326.

### 3.2 Out-of-scope this wave

- **Mechanism animation** (G10-SCI-004 §1.4): curved arrows showing electron movement during reactions. Explicitly deferred to G12-CHEM-006. Don't auto-generate at G10 level.

---

## 4. The #320 input spec — priority order

Recommended template-ship order for `pipeline/visual_templates/`. Numbered by lift × audience × reuse-evidence.

### Tier 1 — ship first (universal infrastructure)

1. **`shared.ts`** — `svgWrap`, `write`, `makePlot`, `polyline`, style tokens (10 generators × ~120 LOC duplicated each = ~1,200 LOC saved).
2. **`remotion_project.ts`** generator — stamps the entire Remotion infra layer (9 clips × ~6 boilerplate files = 54 files of byte-duplication retired).
3. **`<SceneTitle />`** — universal Remotion title-fade pattern (9 clips).
4. **`<LeaderLabel />`**, **`<DotCluster />`**, **`<SideBySideCards />`**, **`<StackedPlots />`**, **`<ReferenceCardGrid />`** — the cross-class primitives (3+ MEMOs each).

### Tier 2 — ship per-class first-of-class generators

These open the class, then same-class downstream units (which the audit identifies — see §5) lift them.

5. **Physics — kinematics + oscillations**: `time-series-plot`, `slope-triangle`, `motion-strip`, `<Spring />`, `<RotatingPoint />`, `cumulativePhase` integral. Covers all G9 / G11 / G12 motion + waves units.
6. **Engineering — circuits**: 9 component primitives + `<RectangularLoop />` + `<CurrentTrace />` + `loopXY`. Covers G6, G8, G10, G11, G12 circuit/electricity units.
7. **Chemistry — atoms / orbitals**: particle constants + `<ConcentricShells />` + `<Orbital />` + `<EnergyLadder />` + `<OrbitalBoxRow />` + `<MiniBohrAtom />` + element data table. Covers G7, G11, G12 chemistry-atomic units.

### Tier 3 — ship per-class second-of-class extensions

8. **Chemistry — periodic-trend**: `<HeatmapTile />`, `<PeriodicTrendHeatmap />`, `<PeriodicTableGrid />`. Covers G7 + G11/G12 trend-heatmap units.
9. **Organic chemistry**: 8-primitive skeletal-structure set (`zigzagPoints`, bonds, `atomLabel`, `alkaneZigzag`, `hexagon`) + functional-group palette + `<MoleculeStructure />`. Covers G10 + 6 downstream units.
10. **Biology — anatomy**: organelle palette (13 colours), `<DoubleMembrane />`, `<StackedFolds />`, Bézier-blob helpers. Covers G6, G7, G9, G12 biology-anatomy units.
11. **Optics — ray diagrams**: `rayArrow`, `normalLine`, `angleArc`, `<RayDiagramVertex />`, `<LensMirrorRayDiagram />`. Covers G8, G10, G12 optics units.
12. **Math — calculus**: `<CurveWithTangent />`, `<CurveWithSecant />`, `<FormulaCard />`. Covers G11/G12 math units.

### Tier 4 — exemplar SVGs (not parametric)

13. **Hand-authored exemplars** at `pipeline/visual_templates/exemplars/`: cathode-ray apparatus, d-orbital cloverleaves, biconcave lens, cyclohexane chair, gold-foil scattering layout. The LLM can reference but should not regenerate.

---

## 5. Time + cost evidence

### 5.1 Wave 1+2 wall-time vs estimate

| Unit | Issue estimate | Actual | Compression |
|---|---|---|---|
| #327 G11-PHYS-010 (1st-of-class oscillations) | 2 days | 3h 15m | 5× |
| #328 G9-SCI-001 (kinematics, downstream-of-G11-PHYS-002) | 1.5 days | 1h 5m | 16× |
| #329 G11-CHEM-002 (1st-of-class chemistry) | 2 days | 1h 45m | 9× |
| #330 G6-SCI-001 (1st-of-class biology, no Remotion) | 2 days | 1h 5m | 14× |
| #331 G6-ENG-002 (1st-of-class engineering) | 2 days | 1h 55m | 8× |
| #332 G7-SCI-001 (downstream chemistry) | 1.5 days | 1h | 12× |
| #333 G10-SCI-004 (downstream chemistry, heaviest catalogue) | 2 days | 1h 27m | 11× |
| #334 G11-MATH-002 (downstream math) | 1.5 days | 1h 27m | 8× |
| #335 G8-SCI-002 (downstream physics) | 1.5 days | 55m | 16× |
| #336 G12-PHYS-005 (downstream physics, last unit) | 2 days | 2h 2m | 8× |
| **Total** | **18 FTE-days** | **14h 56m** | **~10×** |

### 5.2 Compression source

The compression is **process maturity, not primitive reuse**. Most SVGs and Remotion scenes are class-specific. What scaled was the Phase 1/2/3 ritual — the helpers-toolkit, the SidecarSpec format, the eval JSONL append, the MEMO.md template. First-of-class shipping (#327) ≈3h; same-class downstream (#328) ≈45 min.

This implies #320's compression target is **same-class downstream** rather than first-of-class — the LLM should be evaluated against the kinematics/oscillations corpus, not against a fresh class.

### 5.3 LLM token-cost estimate (from G11-PHYS-010 §1.5)

- **Without prior templates:** ~2k input + ~1.5k output per visual. 12 visuals/unit × 10 units = ~$0.07/unit ≈ ~$15 for the entire 218-unit corpus at Sonnet 4.6 prices.
- **With prior templates (kinematics + oscillations as priors):** ~1k input + ~0.8k output. 12 visuals/unit ≈ ~$0.04/unit ≈ ~$9 for the corpus.

Code-gen is **economically obvious** for this content type. The constraint is template quality, not unit cost.

---

## 6. Coverage measurement

Per the audit doc's "Cross-curriculum reusable generators" section, the 9 generators built in Wave 1+2 are *projected* to cover ~70% of all 218 audit units. The measured coverage is **45.0% (98/218 audit-corpus units)** — see [`automation_readiness_coverage.md`](automation_readiness_coverage.md) for the per-class breakdown and uncovered-unit list.

The gap between the audit's projection and the measurement reflects three real things:

1. **The audit's "~70%" was forward-looking.** It assumed 3–4 generators "well-shipped" plus several others. Some of the projected high-leverage classes (geography/map, cycle-diagram, Punnett/phylogenetic) were not built in Wave 1+2 — and these are the largest source of uncovered units (~30+ humanities, history, geography, biology-genetics units).
2. **Inherently non-visual units exist in the corpus.** ~20 English literature, philosophy, and language units are text-driven; SVG generators add no value. Their visual content is photo / illustration / map exceptions.
3. **Adjacent STEM classes still need new generators.** ~15 units (Thermodynamics, Probability, Statistics, Computer Architecture, Data Science, Genetics) need their own primitive sets.

The 45.0% figure is the honest *current* coverage with the 9 generators built. Adding the four classes the audit projected (map, cycle, Punnett, statistics-plot) is what closes the gap to the projected ~70% — and is the natural follow-up to #340.

Closing the gap to ~70% is roughly four more generator classes' work — a Wave-3 sized effort estimated at ~5 FTE-days given the wave-process maturity demonstrated in Wave 1+2.

---

## 7. Source MEMOs (citation index)

| MEMO | Issue | Path |
|---|---|---|
| G11-PHYS-010 Oscillations | #327 | `g11-science/G11-PHYS-010_Oscillations_and_Waves/MEMO.md` |
| G9-SCI-001 Kinematics 1D | #328 | `g9-stem/G9-SCI-001_Kinematics_1D/MEMO.md` |
| G11-CHEM-002 Atom Structure | #329 | `g11-science/G11-CHEM-002_Structure_of_Atom/MEMO.md` |
| G6-SCI-001 Cells | #330 | `g6-stem/G6-SCI-001_Cells/MEMO.md` |
| G6-ENG-002 Electronics | #331 | `g6-stem/G6-ENG-002_Electronics_Basics/MEMO.md` |
| G7-SCI-001 Periodic Table | #332 | `g7-stem/G7-SCI-001_Atoms_and_Periodic_Table/MEMO.md` |
| G10-SCI-004 Organic Chem | #333 | `g10-stem/G10-SCI-004_Organic_Chemistry/MEMO.md` |
| G11-MATH-002 Derivatives | #334 | `g11-stem/G11-MATH-002_Derivatives_Rules_and_Applications/MEMO.md` |
| G8-SCI-002 Waves L&S | #335 | `g8-stem/G8-SCI-002_Waves_Light_and_Sound/MEMO.md` |
| G12-PHYS-005 Optics | #336 | `g12-science/G12-PHYS-005_Optics/MEMO.md` |

---

*Author: broker. Synthesised 2026-05-08 from MEMO files written 2026-04-26 → 2026-05-08. Closes acceptance-criterion #2 of #340.*
