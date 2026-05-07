# MEMO — G6-SCI-001 Cells

> Per-unit learning memo. Captures patterns observed during hand-authoring
> for **#320 code-gen automation**'s spec input. Updated after each phase.

> **Note: this is a 2-phase issue, not 3-phase.** The issue body explicitly
> says *"No Remotion clips — anatomy is static — animation adds nothing"*.
> Phase 2 here is library promotion + eval (the equivalent of "Phase 3" in
> the prior physics/chemistry units).

## Status

- **Phase 1 (Option 2 catalogue):** ✅ 10 SVGs + 10 sidecars shipped
- **Phase 2 (eval set + library promotion):** ✅ 10 sidecars promoted (all with non-NULL embeddings); 3 new known-positive eval records appended (`eval-060` / `061` / `062`)

## Phase 1 reflections — Option 2 catalogue

The 10 SVGs land in three sections, opening the **biology primitive class**:

| Section | Visuals |
|---|---|
| `section-1-whole-cells` | `animal-cell-labeled`, `plant-cell-labeled`, `animal-vs-plant-comparison` |
| `section-2-organelles` | `nucleus-anatomy`, `mitochondrion-anatomy`, `chloroplast-anatomy`, `cell-membrane-bilayer`, `endoplasmic-reticulum-and-golgi` |
| `section-3-scale-microscopy` | `cell-size-scale`, `microscopy-comparison` |

**Locked-in biology palette** (will carry into every downstream biology unit — G7-SCI-003, G9-SCI-005, G12-BIO-*):

| Organelle | Colour | Hex |
|---|---|---|
| Cytoplasm | very pale yellow-green | `#fef9c3` |
| Cell membrane | muted slate | `#94a3b8` |
| Cell wall (plant only) | amber-brown | `#a16207` |
| Nucleus | purple | `#7c3aed` |
| Nucleolus | lighter purple | `#a855f7` |
| Mitochondrion | red (energy) | `#dc2626` |
| Chloroplast | green | `#16a34a` |
| Vacuole | pale blue | `#7dd3fc` |
| Golgi | amber | `#f59e0b` |
| Rough ER | peach | `#ea580c` |
| Lysosome | pink | `#f472b6` |
| Ribosome | dark brown dots | `#7c2d12` |
| Centrosome | slate | `#64748b` |

### What was repetitive (= templatable for #320)

1. **Leader-line label primitive.** Every figure uses the same `leaderLabel(fromX, fromY, toX, toY, text, color, anchor)` helper — a short line + a text label at the line's end. Also already a candidate primitive in the chemistry generator (subatomic-particles cards effectively reused this pattern). **Recommendation for #320:** ship `<LeaderLabel from to text color anchor />` in shared components. Single most reused primitive across physics, chemistry, biology.

2. **Ribosome-dots-along-a-path** — used in animal cell, plant cell, ER+Golgi; same `ribosomeDots(cx, cy, rx, ry, count, color)` helper everywhere. Reused in chemistry's electron-cloud rendering with minor adjustments. **Recommendation:** generalise to `<DotCluster cx cy rx ry count color size />`.

3. **Membrane-double-line pattern** — the nucleus uses two concentric ellipses to show the double envelope; the mitochondrion uses outer + inner; the chloroplast uses lens + inner. Same shape, different sizes. **Recommendation:** `<DoubleMembrane outerR innerR color />`.

4. **Stacked-folds for organelles** — Golgi (4 stacked curved lines), thylakoid grana in chloroplast (4-5 stacked ellipses), ER squiggle. Same compositional pattern: a list of N similar shapes offset along one axis. **Recommendation:** `<StackedFolds count xCenter yCenter foldShape={...} color />`.

5. **Two-cell side-by-side comparison frame.** Same layout shape as G9's uniform-vs-accelerated comparison and chemistry's subatomic-particles cards. Three units now use it. **Recommendation:** ship the side-by-side container as `<SideBySideCards leftContent rightContent comparisonPanel />`.

### What needed human judgment (= curator-only)

1. **Layout of organelles inside a cell.** No two organelles should overlap; each should be visible from outside; leader lines must not cross. This is hand-tuned positioning. **The LLM has no good prior for this.** Recommendation: keep cell-anatomy figures hand-authored; templating helps with the surrounding boilerplate (cell outline, leader lines) but the organelle *positions* are curator-led.

2. **G6-friendly nicknames.** "Powerhouse of the cell" alongside "mitochondrion"; "control center" alongside "nucleus"; "the jelly" alongside "cytoplasm". These dual-labels are pedagogical choices specific to G6. The LLM, given grade-level guidance, can produce these — but they need to be reviewed for accuracy (no kid-friendly term should mislead).

3. **The phospholipid bilayer's water-loving / water-fearing framing.** The accurate term "hydrophilic / hydrophobic" is too heavy for G6; "water-loving / water-fearing" lands. This is a curated grade-level translation; the LLM should not invent these terms — supply them.

4. **Chloroplast's solar-panel metaphor + arrows.** The "sunlight in → sugar out" arrows make the photosynthesis function visible without naming the Calvin cycle. Curator-only call: how much chemistry to suggest at G6 level vs leave for G11.

### What fell outside code-gen entirely

This catalogue is fully code-renderable, but I want to flag a *category* that future biology units will hit: **real microscopy photographs**. The `microscopy-comparison` figure here is a *stylised* representation of what you'd see down each microscope, not a real photograph. For some downstream units (G9-SCI-005 Cell Division stages, G12-BIO histology) **real microscopy images** would teach better than stylised SVGs. **Recommendation:** when those units come up, use `kind: "photo"` sidecars and source them from CC-BY-SA biology-image repositories (Biology Stock Center, Cell Image Library, MIT Biopics).

### What was new for biology vs. prior units

1. **Irregular organic shapes.** Animal cells aren't circles; chloroplasts aren't ellipses; the ER isn't a polyline. These required Bézier curve paths (`Q` and `T` SVG path commands). The kinematics + chemistry generators are entirely circles + lines + axis-aligned ellipses. **Implication for #320:** the biology primitive set must include parameterised "blob shape" generators — I left this as inline `M ... Q ... T ...` strings; future automation should expose them.

2. **Visual organicism > geometric precision.** The animal cell SVG places three mitochondria at hand-tuned angles (`-20°`, `35°`, `-50°`) so they look organically scattered, not geometrically arranged. This is *deliberate visual variation* — the LLM tends to produce evenly-spaced regular layouts, which look wrong for biology. **Recommendation for #320 templates:** when a biology figure asks for "N organelles", randomise their positions/angles within bounds rather than gridding them.

### Time budget (Phase 1)

Phase 1: ~50 minutes (helper toolkit + 10 figure functions + sidecar specs + biology-palette setup). The figures themselves were less geometric and more *artistic* than physics or chemistry — more time spent eyeballing visual feel, less on math.

## Phase 2 reflections — eval entries + library promotion

Three new known-positive eval records appended to `backend/tests/eval/visual_resolver_eval.jsonl`:

| eval id | section title | expected_entry_id |
|---|---|---|
| `eval-060` | What's Inside an Animal Cell | `biology-animal-cell-labeled` |
| `eval-061` | Inside the Cell's Power Bean | `biology-mitochondrion-anatomy` |
| `eval-062` | How Big Are All the Tiny Things | `biology-cell-size-scale-chart` |

Choices were driven by primitive-class diversity: one whole-cell anatomy chart, one organelle close-up, one scale/conceptual visual. Each section's prose deliberately avoids the words "animal cell", "mitochondrion", or "logarithmic scale" — instead the prose describes what the *student would see* (a bean-shaped structure with two skins; a horizontal line where each step is ten times the previous). The resolver should win on what-the-visual-looks-like, not name-matching.

All 10 G6-SCI-001 sidecars seeded into `visual_library_entries` via `scripts/seed_library_local.py` (run inside celery-pipeline after the docker-cp step from #339's gotcha). Verified: 10 rows present with `source_unit='G6-SCI-001'`, all with non-NULL embeddings; total rows = 75, NULL-embedding rows = 0.

### What was repetitive (= templatable)

The Phase 2 (here-Phase 3-equivalent) workflow is now **identical across four units** (#327, #328, #329, #330):

1. Append eval records → validate JSON
2. `docker cp sample_content/<unit_dir>` into `/tmp/seed/sample_content/`
3. Run `python3 /tmp/seed/scripts/seed_library_local.py`
4. SELECT verify rows + embeddings

This is the **fourth proof point** for #339's bind-mount fix. At this point the manual docker-cp dance has consumed ~5 minutes per unit × 4 units = 20 minutes of pure ceremony that a one-line YAML change would have eliminated. The fix is overdue.

### What needed human judgment

Same as in prior units — eval prose authoring stays curator-only. New pattern observed this run:

- **"Show before tell" prose alignment.** The biology eval prose deliberately runs "imagine you'd see X / a roundish dark patch off to one side" before any organelle is named. This forces the resolver-LLM to identify the visual from its *appearance* not its label. The Rutherford eval (#057) used the same pattern with "small positively-charged particles", as did the SHM eval (#051) with "traces out a perfect cosine curve in time". Across three subjects this prose-style consistently maps to known-positive resolver hits — worth promoting to the canonical eval-prose template.

- **G6-friendly framings stay inside the prose.** "The brain of the operation" (nucleus), "power bean" (mitochondrion), "stack of curved plates" (Golgi). G6-level metaphors. Resolver still hits the right entry — the embedding model is robust to friendly paraphrasing.

## Time budget summary

| Phase | Issue estimate | Actual |
|---|---|---|
| Phase 1 | ~1 day | ~50 min |
| Phase 2 | ~1 day (rolled in) | ~15 min |

Total: ~1 h 5 m vs. 2-day issue estimate. **Smallest wall-clock yet** for a first-of-class generator-building unit (#327 was 3h 15m, #329 was 1h 45m). The savings come from no Remotion phase: the issue's "no animation" call removed an entire build step that's normally 30–45 minutes for a primitive class. Future units that genuinely don't need motion (anatomy, table-driven concept maps, side-by-side comparisons) should explicitly opt out — the time saving is real.

---
*Author: broker. Updated 2026-05-07 (all phases complete; #330 ready to close).*
