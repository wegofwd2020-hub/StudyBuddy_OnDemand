# ADR-002 — EPUB Export & the Auth-Free Reading Paradigm

**Date:** 2026-05-26
**Status:** Proposed
**Branch at decision:** `docs/adr-002-epub-export`

---

## Context

The Curriculum Authoring Studio (super-admin; PRs #383, #385, #388, #390, #392, #393)
produces self-contained **authored packages** — e.g. *Context Engineering in the
Enterprise*, the Copilot topics — that are far more **book-like** than school
curriculum. They are linear, narrative, professional/self-directed reading material.

The school platform's apparatus (Auth0/local auth, enrolment, classrooms, entitlement
gating, progress tracking) is the wrong vessel for "I just want to read this like a
book." We want a **reading-first, low-friction, portable** consumption mode that does
**not** require authentication and is **separate** from the authenticated platform.

This fits the documented product thesis: the scoped-retrieval/generation engine is
shared; different **wrappers** serve different audiences. The school LMS is one wrapper;
an auth-free reader for professional / home-school / self-directed readers is another.

This ADR is the **assembly/export** half of the work tracked in **issue #391**
(final-package organization: quiz consolidation + PDF export). It decides the
reading-distribution format. A per-unit `study_pack_{lang}.pdf` already exists
(`pipeline/build_unit.py::generate_pdf`); EPUB is its reflowable, e-reader-native sibling.

---

## Decision

### D1 — Ship EPUB export as a package-assembly output (Phase 1)

Add an **EPUB exporter** that turns a published authored curriculum into a single
`.epub` file. It is an **opt-in, per-package, super-admin-triggered** action (an export
button at/after the Authoring Studio `publish` step, and/or a CLI for operators). EPUB is
chosen over building a reader first because it is a bounded, additive pipeline feature
that rides the entire e-reader ecosystem and validates the reading-paradigm hypothesis
cheaply.

### D2 — Render server-side; pre-render the dynamic parts

EPUB readers do not reliably run JavaScript, so the exporter renders everything to static
XHTML at build time, reusing the content-store JSON (`curricula/{curriculum_id}/{unit_id}/
{lesson,tutorial,quiz_set_*}_{lang}.json`):

| Source element | EPUB rendering |
|---|---|
| Markdown prose / GFM tables | Markdown → XHTML (+ CSS) |
| KaTeX `$…$` / `$$…$$` | KaTeX → **MathML** (EPUB3 native; image fallback if needed) |
| ```` ```mermaid ```` fenced blocks | **Pre-rendered to SVG** (mermaid-cli / headless) and inlined as `<img>`/inline-SVG |
| Fenced code blocks | `<pre><code>` with CSS |

### D3 — Quizzes are static (interactivity stays on the web)

Quizzes export as printed **"Practice Questions"** per topic plus a consolidated
**"Answer Key"** appendix (this is exactly the quiz-consolidation ask in #391 — gather all
quizzes into one section, still grouped by topic). Interactive answering/scoring remains
a web-platform concern, not an EPUB concern.

### D4 — Reading order from the package manifest

The EPUB spine follows the authored package structure: front matter → per-topic chapters
(lesson → tutorial) → consolidated Quiz section (by topic) → Answer Key. Derived from the
Authoring Studio's structured TOC / materialised `curriculum_units` order.

### D5 — Access model: uncontrolled file by design

An EPUB is freely copyable; there is **no DRM in Phase 1**. Therefore export is **opt-in
per package** and intended for content the operator is willing to distribute openly
(free / sample / open courseware). **Monetized or access-controlled content stays behind
the authenticated platform** (or the Phase-2 reader). This makes "no authentication" a
deliberate property of *which* packages get exported, not a removal of platform gating.

### D6 — No auth, no reading backend in Phase 1

The `.epub` is a downloadable artifact produced by an admin/pipeline action. Phase 1 adds
**no public reading endpoint and no reader app** — avoiding a new unauthenticated surface
on an entitlement-gated backend and not compounding the Epic-2 hosting blocker.

### D7 — Accept the analytics trade-off

EPUB yields **no read telemetry** (who read what, completion). This is an accepted Phase-1
limitation. If engagement/completion reporting becomes required (e.g. corporate L&D), that
is a driver for Phase 2, not a reason to instrument EPUB.

---

## Phase 2 (documented, NOT decided here) — auth-free PWA reader

If/when we need **interactive quizzes, read analytics, central content updates, or
soft access control**, build a **read-only PWA** that fetches published-package JSON from a
public read endpoint and renders it with the *existing* components (`SBMarkdown` +
`MermaidDiagram` + KaTeX) — i.e. ship the renderer we already have as an installable,
offline-capable, unauthenticated app, not a from-scratch e-reader. This keeps full
fidelity (live Mermaid/math, interactive quizzes) at the cost of hosting + a public
endpoint. EPUB (Phase 1) and the PWA (Phase 2) can coexist: EPUB for true offline/
e-reader portability of the linear reading; PWA for the interactive experience.

---

## Architecture

<!-- doc-audit:ignore -->
- **New module** `pipeline/epub_export.py` (sibling of the PDF pack), or a small
  `pipeline/package/` assembler. Pure/offline like the rest of the pipeline.
- **Inputs:** the published curriculum's content-store JSON + the structured TOC for
  chapter ordering. No DB writes required to read; optional `package_exports` audit row.
- **Render dependencies (new):** a Markdown→XHTML renderer, `katex` (MathML output), and a
  headless Mermaid→SVG step (mermaid-cli/puppeteer, or a Node sidecar). EPUB packaging via
  a library (e.g. `ebooklib`) or a templated OPF/spine + zip.
- **Trigger:** super-admin action in the Authoring Studio (extends the `publish` flow) and
  an operator CLI. Output written to the content store as
  `curricula/{curriculum_id}/package_{lang}.epub` (mirrors the `study_pack` path shape).
- **Accessibility:** emit EPUB3 with proper semantics, `lang`, alt text on diagram images,
  and MathML — directly serving the WCAG 2.1 AA goal (reflow + screen-reader support come
  free from the reader).

---

## Consequences

**Positive**
- Reading rides the e-reader ecosystem (Apple Books, Kobo, Calibre, Kindle via convert);
  genuinely offline; accessibility largely for free; **no reader app to build or host**.
- "No auth, separate" satisfied by the artifact's nature.
- Bounded, additive; reuses content-store JSON and the existing PDF-pack pattern; resolves
  the quiz-consolidation half of #391.

**Negative / explicitly out of scope in Phase 1**
- Interactive quizzes flatten to printed Q + Answer Key.
- New server-side render step for Mermaid (SVG) and math (MathML) — the one real build cost.
- No central updates (re-distribute the file on change), no telemetry, no access control/DRM.

---

## Open questions (Phase-1 defaults adopted above; confirm or override)

1. **Open vs monetized** — D5 assumes exported packages are OK to distribute freely. If any
   are monetized, those must NOT be EPUB-exported (use Phase 2 / platform). _Confirm._
2. **Static vs interactive quizzes** — D3 assumes static (Q + Answer Key) is acceptable for
   reading. _Confirm._
3. **Analytics** — D7 assumes no read telemetry is acceptable in Phase 1. _Confirm._
4. **Scope** — which packages get the EPUB path (all authored, or only "book-like"
   corporate/home-school ones)?
5. **Diagram/math fidelity** — D2 assumes pre-rendered SVG + MathML is acceptable. _Confirm._

---

## Alternatives considered

- **PDF only (status quo).** A per-unit `study_pack` PDF already exists, but PDF is fixed-
  layout — not reflowable, weaker on small screens and screen readers, not e-reader-native.
  Keep PDF for print; EPUB for reading.
- **Custom reader first.** Rejected for Phase 1: it needs hosting + a public endpoint and is
  a second maintained surface on top of the Epic-2 hosting blocker. Deferred to Phase 2 and
  scoped down to "ship the existing renderer as a PWA."
- **Plain HTML bundle / zip of pages.** Simpler than EPUB but loses the e-reader ecosystem,
  reflow semantics, and offline packaging that EPUB gives for the same rendering work.

---

## References

- Issue #391 — Authoring Studio final-package organization (quiz consolidation + PDF export);
  this ADR is its EPUB/reading-format decision.
- Authoring Studio PRs: #383, #385 (backend), #388 (smoke), #390 (web UI), #392/#393 (fixes).
- `pipeline/build_unit.py::generate_pdf` / `study_pack_{lang}.pdf` — existing per-unit pack.
- `web/components/content/Markdown.tsx` (`SBMarkdown`) + `MermaidDiagram.tsx` — the renderer
  the Phase-2 PWA would reuse.
