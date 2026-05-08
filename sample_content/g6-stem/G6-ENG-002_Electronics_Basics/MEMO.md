# MEMO — G6-ENG-002 Electronics Basics

> Per-unit learning memo. Captures patterns observed during hand-authoring
> for **#320 code-gen automation**'s spec input. Updated after each phase.

## Status

- **Phase 1 (Option 2 catalogue):** ✅ 13 SVGs + 13 sidecars shipped
- **Phase 2 (Option 3 Remotion clip):** ✅ `Electronics_CurrentFlow.mp4` (3.1 MB / 24 s)
- **Phase 3 (eval set + library promotion):** pending

## Phase 1 reflections — Option 2 catalogue

The 13 SVGs land in three sections, opening the **engineering / circuit-schematic primitive class**:

| Section | Visuals |
|---|---|
| `section-1-components` | `circuit-component-symbols`, `resistor-anatomy`, `capacitor-anatomy`, `battery-and-cell-anatomy` |
| `section-2-circuits` | `simple-circuit-with-lamp`, `series-circuit`, `parallel-circuit`, `series-vs-parallel-comparison`, `led-with-current-limit-resistor` |
| `section-3-flow-and-laws` | `current-flow-direction`, `open-vs-closed-circuit`, `ohms-law-relationship`, `short-circuit-warning` |

### Subject-enum gotcha

The closed `SUBJECTS` enum (validator + `library.py::SUBJECTS`) does **not** include `engineering`. Allowed values: `physics, chemistry, math, biology, geography, history, languages`. Circuits/electricity were tagged as `subject: "physics"` here — defensible (they *are* physics topics) but the unit's audit-row in `visual_audit_all_grades.md` puts them under "Engineering". **Recommendation:** either add `engineering` to `SUBJECTS` (single line in `validate_library_metadata.ts` + `backend/src/visuals/library.py` + the `SidecarSpec` type union in `seed_library_sidecars.ts`), or document that engineering content lives under `physics` with an `electronics` keyword tag.

### Locked-in circuit-schematic palette (carries into G8-SCI-003, G10-ENG-002, G11-ENG-003, G12-PHYS-002 + 008)

| Element | Convention | Hex |
|---|---|---|
| Wires | black, 2.5 px stroke | `#1a202c` |
| Resistor | brown zigzag (US style) | `#92400e` |
| Battery + terminal (long line) | red | `#dc2626` |
| Battery − terminal (short line) | black | `#1a202c` |
| Capacitor | blue parallel lines | `#2b6cb0` |
| LED | red triangle + bar + amber light arrows | `#dc2626` body, `#fbbf24` glow |
| Lamp | amber circle with X (lit fills colour, unlit white) | `#fbbf24` |
| Switch | slate hinged lever | `#4a5568` |
| Current arrow | green triangle | `#15803d` |
| Junction node | small black dot, r=4 | `#1a202c` |

### Reusable circuit primitives shipped (the heart of #320 reuse)

The generator defines **9 reusable functions** that downstream units will lift verbatim:

| Function | Signature | Description |
|---|---|---|
| `wire(x1,y1,x2,y2,color?)` | straight wire | basic line, locked stroke width |
| `node(x,y,color?)` | junction dot | for branches |
| `resistor(cx,cy,orient,label?)` | zigzag resistor | h/v orientation |
| `batteryCell(cx,cy,orient,label?)` | single cell | long+short lines |
| `battery(cx,cy,orient,label?)` | multi-cell battery | two cells stacked |
| `lamp(cx,cy,r,lit?,label?)` | circle-with-X | lit toggles colour fill + glow |
| `switchSymbol(cx,cy,open,label?)` | hinged lever | open vs closed pose |
| `capacitor(cx,cy,orient,label?)` | two parallel lines | h/v orientation |
| `led(cx,cy,lit?,label?)` | triangle+bar+arrows | lit toggles glow + arrow opacity |
| `currentArrow(x,y,dir,label?)` | green triangle on a wire | up/down/left/right |

### What was repetitive (= templatable for #320)

1. **Rectangular-loop circuit layout**. Six of the 13 figures use the same `wire(x1,y1,...)` skeleton — a rectangle with components on its edges. Coordinates are hand-tuned per figure but the *shape* is identical. **Recommendation for #320:** template `<RectangularLoop topComponents={...} bottomComponents={...} leftComponents={...} rightComponents={...} />`. Half the work in this catalogue is laying out which-component-goes-on-which-edge.

2. **Side-by-side comparison frame** (used in `series-vs-parallel-comparison` and `open-vs-closed-circuit`). Same shape as G9's uniform-vs-accelerated, biology's animal-vs-plant, chemistry's subatomic-particles. Five units now use this layout. **Recommendation:** seriously consider promoting `<SideBySideCircuits leftCircuit rightCircuit captionLeft captionRight />` to shared components — it's the most-reused layout primitive across the entire visual library so far.

3. **Current arrows on multi-edge wires.** Every circuit with more than one labelled flow direction uses `currentArrow()` at multiple points along the wire. **Recommendation:** template `<CurrentTrace edges=[(start,end),...] label />` that distributes arrows along a path automatically.

4. **Component-with-label pattern.** Every component primitive accepts a `label?` parameter and renders the label at a conventional offset (above for horizontal, right-of for vertical). This avoids one-off label positioning bugs. **Recommendation:** keep this convention everywhere — saves 30s per component instance × ~50 component instances per unit.

### What needed human judgment (= curator-only)

1. **Component placement on the loop.** Where does the switch go vs the lamp vs the battery? It's not arbitrary — pedagogically, the switch is usually on the wire entering the load (so opening it visibly cuts the lamp), the battery is conventionally at the bottom, the load (lamp/resistor/LED) is typically on top or in line. The LLM has a vague prior on this from training data but tends to place components randomly. **Recommendation for #320 spec:** when a circuit figure is requested, supply explicit placement constraints: `top: <component>`, `bottom: battery, left: switch, right: load`.

2. **Resistor colour-band decoding.** The 4-band code (brown-black-red-gold = 1 kΩ ±5%) is real-world correct and pedagogically rich. The LLM can recall the colour code, but choosing *which value* to demonstrate needs a curator (1 kΩ is the canonical first example because its bands are visually distinct).

3. **Series-vs-parallel "broken bulb" choice.** The pedagogical move of showing one bulb broken in BOTH circuits — to make the structural difference visceral — is curator-only. The LLM would default to drawing intact circuits side-by-side, which is technically correct but pedagogically weaker.

4. **Short-circuit warning aesthetics.** The bright red bypass wire + the "I = HUGE" label + the X on the lamp + the "⚠" in the title are all stacked redundancy. This is deliberate: short-circuit kills batteries and starts fires; the warning needs to be *over*-emphasised relative to the geometry. Curator-only — the LLM would draw the technically-correct bypass wire without any of the warning emphasis.

### What fell outside code-gen entirely

This catalogue is fully code-renderable. Real-world photos of circuits-on-breadboards or component-close-ups would teach better than schematics for some students, but the issue scope explicitly calls for schematics. If pilots show students benefit from a real-component photo alongside the schematic, add as `kind: "photo"` exceptions for `resistor-anatomy`, `capacitor-anatomy`, `battery-and-cell-anatomy` (the three figures that already split into "real component | schematic" panels).

### Time budget (Phase 1)

Phase 1: ~70 minutes (helpers — 9 reusable circuit primitives — took ~35 min; figures took ~35 min). The reusable primitives are doing all the work — `simple-circuit-with-lamp` is ~25 lines of declarative function calls, not raw SVG. **The investment in helpers will pay back across 6+ downstream units.** This is the highest leverage Phase 1 yet.

## Phase 2 reflections — Option 3 Remotion clip

One composition (`electronics-current-flow`, 24 s, 3.1 MB):

A simple battery + switch + resistor + LED loop with **green charge dots flowing around the rectangular wire**. Three regimes play out in sequence:
- **A** (frames 60–150): switch open, no current, LED dark, dots not visible
- **B** (frames 150–300): switch closes; V = 5 V, R = 330 Ω → I = 15 mA. Dots flow at baseline rate (one full loop every 4 s).
- **C** (frames 300–450): voltage doubles to 10 V → current doubles to 30 mA. **Dots flow visibly twice as fast** (one loop every 2 s). LED brightens with the brighter glow.
- **D** (frames 450–600): resistance doubles to 660 Ω → current halves back to 15 mA. Dots return to baseline rate. LED dims back.
- **E** (frames 600–720): hold final tableau.

A live V/I/R readout panel on the right updates with each regime. A caption fades in/out under the circuit telling the student which regime is active. Ohm's law `I = V / R` is rendered statically in the readout panel.

### What was repetitive (= templatable for #320)

1. **Cumulative-phase integral** (`cumulativePhase(frame)`) — a piecewise integral of speed over time that gives smooth motion across regime transitions. Same exact pattern as the wave-superposition phase sweep in #327's `WaveSuperpositionScene` and the strobe-dot accumulation in #328's `MotionAlongStripScene`. **Recommendation:** ship a `useCumulativeIntegral(speedByRegime)` hook in shared components — three units now use this pattern.

2. **`loopXY(phase)`** — maps a phase ∈ [0, 1) to (x, y) on a rectangular loop's perimeter. Reusable for any "object travels around a closed wire/path" animation: cyclic chemistry (Krebs cycle, in future biology units), water-cycle physics, any process diagram. **Recommendation:** generalise to `loopXY(phase, vertices)` taking an arbitrary closed polygon, ship as `<DotsAroundPath path dots speed />`.

3. **Live-value readout panel.** Right-side rectangle with three label-value rows + an equation at the bottom. Same shape as the Bohr-transition energy ladder (#329). Same shape as future Ohm's-law / Newton's-law / chemistry-equation-with-live-values clips. **Recommendation:** `<LiveValuesPanel rows={[{label,value,unit,color}]} equation />`.

4. **Component-with-state primitives.** The LED has `lit?: boolean`; the switch has `closed: boolean`; the lamp had `lit?: boolean` in the SVG generator. Each component should ship as `<Component state />` where state captures every visual variation. **Recommendation:** lift `<Resistor />`, `<Battery />`, `<LED state />`, `<Switch state />` from the generator into Remotion-shared components — they're already factored out in the SVG generator, just need a Remotion-flavoured wrapper.

### What needed human judgment (= curator-only)

1. **Choosing the regimes.** The sequence "baseline → V doubles → R doubles" is a deliberate pedagogical arc that lets the student watch each variable's effect *separately*. A "V and R both change" regime would obscure the relationship. The order matters too — voltage first, because students intuit "more push = more flow" before they intuit "more friction = less flow". Curator-only.

2. **Dot density (12 dots).** Fewer dots make the flow look sparse and trackable; more dots make it look like a continuous river. 12 around a 2400-px perimeter (one every 200 px) is the sweet spot for "I can see individual dots move but the flow feels populated". Hand-tuned. The LLM has no good prior here.

3. **Speed multiplier choices (0.25 / 0.50 / 0.25 loops/sec).** Four-second loop time at baseline is slow enough to follow but fast enough that you don't get bored. Doubling to two-second loops is *visibly* faster but not so fast it blurs. Pure perceptual hand-tuning.

4. **No physics during regime A.** The clip explicitly shows the circuit *with no flow* for 3 seconds before the switch closes. This is curatorial — the student needs to see "no current" as a state to contrast against, not just an absence. A naïve LLM-driven version would skip this and start at I > 0.

### What fell outside code-gen entirely

Nothing. Pure 2D animation + math.

### Time budget reconciliation (Phase 2)

Estimated ~0.5 day (rolled into 2-day issue total); **actual: ~30 minutes authoring + 1 minute render**. The Phase-1 circuit-schematic palette + the loopXY/cumulativePhase math both lifted cleanly into the Remotion theme. Per-scene LoC: ~280 (one scene file) — comparable to the G9 motion-along-strip scene (~260) but with more pedagogical state to track.

## Time budget summary

| Phase | Issue estimate | Actual |
|---|---|---|
| Phase 1 | ~1 day | ~70 min |
| Phase 2 | ~0.5 day | ~30 min |
| Phase 3 | (rolled into 2 d) | pending |

Tracking on pace with #329 (chemistry first-of-class). The investment in helpers in Phase 1 paid off cleanly in Phase 2 — every component primitive translated to a corresponding Remotion drawing call, and the cumulative-phase pattern was already proven from physics units.

---
*Author: broker. Updated 2026-05-08 (Phase 2 complete).*
