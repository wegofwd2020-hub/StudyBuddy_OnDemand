# MEMO — G11-PHYS-010 Oscillations and Waves

> Per-unit learning memo. Captures patterns observed during hand-authoring
> for **#320 code-gen automation**'s spec input. Updated after each phase.

## Status

- **Phase 1 (Option 2 catalogue):** ✅ 12 SVGs + 12 sidecars shipped
- **Phase 2 (Option 3 Remotion clips):** pending — SHM, wave superposition, Doppler
- **Phase 3 (eval set + library promotion):** pending

## What was repetitive (= automatable)

These patterns appeared across many of the 12 SVGs and are perfect templates for #320 to fill in:

1. **Single-axis sine plot** with amplitude / period markers — appeared in `shm-displacement-time`, `wave-anatomy`. Template: `makePlot(...)` + `polyline(samples([...sin...]), ...)` + a few label overlays. **Variability:** ω, A, x-range. **Constants:** colour palette, padding, axis labels.

2. **Stacked-plots-for-comparison** — appeared in `shm-y-v-a-comparison` (3 stacks), `superposition-constructive/destructive` (3 stacks each). Template: a `stacks` array of `{data, color, label, yRange}`, render each into a transform-translated `<g>`. **Variability:** number of stacks (always 2-3), colour rotation. **Constants:** layout math, gap, font sizes.

3. **Comparison-on-same-axes** — appeared in `damped-oscillation-comparison` (3 curves, one plot), `resonance-amplitude-curve` (3 curves, one plot). Template: same `makePlot` + N `polyline` calls with different colours + a small legend block in the corner. **Variability:** N curves, the math function, palette choice. **Constants:** legend layout, axis labels.

4. **Side-by-side concept comparison** — appeared in `transverse-vs-longitudinal`. Template: split the canvas in half with a vertical divider, render each concept into its half, label and arrow each. **Variability:** which two concepts. **Constants:** divider placement, label positions, arrow style.

These four templates would cover ~70–80% of the unit's catalogue. **Strong candidates for #320 templates** named `single-plot`, `stacked-plots`, `multi-curve-plot`, `side-by-side-concept`.

## What needed human judgment (= curator-only territory)

These visuals required hand-authored geometric layout that wouldn't have come out of an LLM template fill cleanly:

1. **Pendulum free-body diagram** — required computing the position of the bob from a given angle, the perpendicular direction for the restoring component, marker positions for the angle arc, and the relative lengths of the three force vectors so the geometry is readable. The LLM would need to write coordinate geometry against the pendulum's hinge frame; doable but the prompt would need the formula for the restoring component as a constraint. **Recommendation for #320:** template `free-body-diagram` with parameters `{bob_position, vectors:[{name, direction, length, color}], pivot}`.

2. **Standing-wave modes** — the envelope curve for each harmonic depends on `n`; nodes appear at `kL/n` for `k=0..n`. Generated with `for k in 1..n` placement. The pattern is clean enough to template, but the LLM would need to know the closed-form for the standing-wave envelope. **Recommendation:** template `standing-wave-modes` with parameters `{harmonics:[1, 2, 3], color_palette}` — solver embedded in template.

3. **Doppler wavefront geometry** — successive wavefronts are circles of increasing radius emitted from successively-translated source positions. The LLM has to compute the right radii sequence such that the wavefronts visually crowd ahead of the source and spread behind. Hand-authored values (`r=130, 95, 60, 25`; positions `srcX=cx-120, -80, -40, 0`) chosen for visual clarity, not derived from physics. **Recommendation:** template `doppler-wavefronts` with hand-chosen example parameters — the LLM tunes only the labels and observer placement.

## What fell outside code-gen entirely (= deferred to `kind: "photo"` exception)

Nothing in this unit. Every visual was code-renderable. Pure mechanics + waves; no real-world photographs or watercolour-style illustrations earned their cost over the precise SVG primitives.

## Token cost estimate (if LLM-authored from scratch)

Each visual is ~50–250 lines of TS spec data + the shared `makePlot` boilerplate. Hand-authored, this took roughly 90 minutes of focused work for all 12 visuals (because the templates from kinematics carried over).

If LLM-authored from scratch (no prior templates):
- Per visual: ~2k input tokens (concept + template prompt) + ~1.5k output tokens (TS spec)
- 12 visuals: ~24k input + ~18k output ≈ ~$0.07 (Sonnet 4.6 at $3/M in, $15/M out)

If LLM-authored *with* the Kinematics templates as priors:
- Per visual: ~1k input + ~0.8k output
- 12 visuals: ~12k input + ~10k output ≈ ~$0.04

This is well below the per-unit cost ceiling. **Code-gen is economically obvious for this unit class.**

## What this means for #320

1. The **four templates** identified above (single-plot, stacked-plots, multi-curve-plot, side-by-side-concept) cover the bulk of physics-time-series content. Worth shipping in `pipeline/visual_templates/` first.
2. **Free-body-diagram template** is the next most-leveraged primitive — used here for the pendulum, will be reused in G6-ENG-001 (#331), G9-SCI-002 Newton's Laws, G10-ENG-001 Statics, every kinematics unit.
3. **Doppler-wavefront / wave-source template** is more niche; ship after the bulk-template work.
4. The Kinematics templates carry over directly. **Conjecture: most G11/G12 physics units will fit on top of the Kinematics+Oscillations template set.** Verifiable when we ship #335 (G8-SCI-002 Waves) and #336 (G12-PHYS-005 Optics).

## Time budget reconciliation (issue's 2-day estimate)

- Phase 1 (this commit): ~2 hours hand-authoring + iteration
- Phase 2 (Remotion clips): ~6 hours expected — three clips with `useCurrentFrame()` driving SHM, superposition, and Doppler
- Phase 3 (eval set + library promotion + final review): ~2 hours

Total realistic: ~10 hours = ~1.5 working days, beating the 2-day estimate. Wave 1 cost padding looks correct.

---
*Author: broker. Updated 2026-05-07 (Phase 1 complete).*
