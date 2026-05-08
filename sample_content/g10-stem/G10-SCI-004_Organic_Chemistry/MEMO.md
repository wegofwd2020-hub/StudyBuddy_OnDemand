# MEMO — G10-SCI-004 Organic Chemistry

> **2-phase issue** (no Remotion clips per scope: "skeletal structures are
> static; mechanism animation deferred to G12-CHEM-006").

## Status

- **Phase 1 (Option 2 catalogue):** ✅ 16 SVGs + 16 sidecars shipped
- **Phase 2 (eval set + library promotion):** ✅ 16 sidecars promoted (all with non-NULL embeddings); 3 new known-positive eval records appended (`eval-069` / `070` / `071`)

## Phase 1 reflections

The 16 SVGs land in four sections — the heaviest chemistry catalogue yet:

| Section | Visuals |
|---|---|
| `section-1-skeletal-structures` | `skeletal-shorthand-rules`, `alkane-series-zigzag`, `branched-vs-straight-pentanes`, `cyclohexane-shapes`, `numbering-the-chain` |
| `section-2-multiple-bonds-aromatics` | `alkene-double-bond`, `alkyne-triple-bond`, `cis-trans-isomerism`, `benzene-resonance` |
| `section-3-functional-groups` | `functional-groups-reference`, `alcohol-aldehyde-ketone-card`, `carboxylic-acid-and-ester-card`, `amine-and-amide-card` |
| `section-4-iupac-naming` | `iupac-naming-flowchart`, `name-build-walkthrough`, `prefix-and-suffix-cheat-sheet` |

This unit ships the **skeletal-structure SVG generator** that the issue called the "heaviest chemistry authoring effort". The new generator carries 8 reusable bond/atom primitives that will reuse across G11-CHEM-008/009 and G12-CHEM-006/007/008/009 — six downstream organic-chem units.

### Locked-in skeletal-structure primitives (the heart of #320 reuse)

The generator defines 8 reusable functions that downstream units will lift verbatim:

| Function | Signature | Description |
|---|---|---|
| `zigzagPoints(x0, y0, n, parity)` | computes N alternating-up/down vertex positions | the canonical alkane backbone |
| `singleBond(x1, y1, x2, y2, color?, width?)` | a straight bond | basic line |
| `doubleBond(x1, y1, x2, y2, color?)` | two parallel lines with perpendicular offset | alkenes, carbonyls |
| `tripleBond(x1, y1, x2, y2, color?)` | three parallel lines | alkynes |
| `atomLabel(x, y, text, color, fontSize?)` | a labelled atom (OH, NH₂, Cl, etc.) | functional-group attachment |
| `alkaneZigzag(x0, y0, n, startsLow?)` | full N-carbon alkane backbone | composes zigzagPoints + singleBond |
| `hexagon(cx, cy, r, color?)` | a regular hexagon ring | benzene/cyclohexane |
| (functional-group constants) | locked colours per group family | OH=red, C=O=deep-red, NH₂=blue, X=green, ring=purple |

**Recommendation for #320:** ship the bond + atom primitives at `pipeline/visual_templates/organic_primitives.ts` and the functional-group palette as `pipeline/visual_templates/organic_palette.ts`. Six downstream units justify this lift.

### What was repetitive (= templatable)

1. **Zigzag-with-substituent layout** — every alkane/alkene/alkyne figure is `alkaneZigzag(...)` + a few `singleBond` branches + an `atomLabel` for each functional group. Six of the 16 figures fit this template. **Recommendation:** `<MoleculeStructure parent={n_carbons} substituents={[{position, group}]} />`.

2. **Worked-example layout** (used in `numbering-the-chain` and `name-build-walkthrough`): structure on the left, step-by-step rows on the right with the final answer highlighted at the bottom. Same shape as the chemistry Bohr-transition's energy-ladder annotations and the electronics current-flow live-readout panel. **Recommendation:** `<WorkedExample structure steps finalAnswer />`.

3. **Functional-group reference card** layout (4×2 grid of group cards) is the same shape as #329's subatomic-particles cards and #331's circuit-component-symbols reference. Three units now use it. **Recommendation:** `<ReferenceCardGrid columns={4} cards={[{title, body, color}]} />`.

4. **Numbered-flowchart pattern** (`iupac-naming-flowchart`): vertically-stacked numbered cards connected by downward arrows. Same shape as the science-experimental-method flowcharts that future biology and physics units will need. **Recommendation:** `<NumberedFlowchart steps={[{n, title, note}]} />`.

### What needed human judgment

1. **Which examples to choose for each group.** Vinegar for ethanoic acid; "fruity smell" for ester; "found in proteins" for amide. These G10-friendly anchors are curator-led — the LLM can produce technically correct examples but tends toward the abstract.

2. **Cyclohexane chair drawing.** The two parallel zigzags-connected-by-vertical-segments rendition of the chair is a hand-tuned simplification — real chair conformations have alternating axial/equatorial positions, but at G10 level we just want the *idea* of "not flat". Curator-only call on what to omit.

3. **Resonance-vs-equivalence symbols** in `benzene-resonance`. The double-headed resonance arrow (↔) between Kekulé forms vs the single equivalence arrow (≡) to the modern circle is a specific convention — students have to learn that resonance is **not** the molecule flipping back and forth. The arrow distinction makes that point visually.

4. **Skipping electron affinity** as a fourth heatmap (mentioned in issue but inconsistent at G10). Curator-only call to use four heatmaps with one summary chart instead of four direct heatmaps.

### What fell outside code-gen entirely

Mechanism animation (curved arrows showing electron movement during reactions) — explicitly deferred to G12-CHEM-006. This is the canonical "would benefit from Remotion but issue scope says no" case. The scope decision is correct: mechanism animation is a G12 concept, not G10.

### Time budget (Phase 1)

Phase 1: ~75 min (8 reusable primitives took ~30 min; 16 figures took ~45 min). The generator file is the largest in the catalogue (~700 lines) but each figure is ~30-40 lines because the primitives compose cleanly. Compare against #329 (chemistry first-of-class) at ~50 min for Phase 1 — this unit is bigger and slower because of the heavier scope (16 vs 13 figures, four sections vs four sections, more functional-group cards).

## Phase 2 reflections

Three known-positive eval records appended:

| eval id | section title | expected_entry_id |
|---|---|---|
| `eval-069` | Three Ways to Draw the Same Molecule | `chemistry-organic-skeletal-shorthand-rules` |
| `eval-070` | Carbons That Share a Double Bond | `chemistry-organic-alkene-double-bond` |
| `eval-071` | Naming Organic Molecules — Five Steps | `chemistry-organic-iupac-naming-flowchart` |

The eval-070 prose ("a soft sound rather than the hard one") is a deliberate paraphrase of "ene-suffix replaces ane-suffix" — wanted to test whether the resolver picks up phonetic descriptors. Worth watching when next eval run lands.

All 16 G10-SCI-004 sidecars seeded; 113/113 library rows, 0 NULL embeddings.

## Time budget summary

| Phase | Issue estimate | Actual |
|---|---|---|
| Phase 1 | ~1 day | ~75 min |
| Phase 2 | ~1 day (rolled in) | ~12 min |

Total: ~1 h 27 m vs. 2-day issue estimate. Wave-2 cumulative: ~2h 27m for two units shipped (#332 + #333).

---
*Author: broker. Updated 2026-05-08 (all phases complete; #333 ready to close).*
