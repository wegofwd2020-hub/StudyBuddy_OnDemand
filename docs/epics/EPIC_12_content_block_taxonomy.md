# Epic 12 — Structured Content Block Taxonomy

**Status:** 🚧 Filed as GitHub #193; scope pending confirmation

---

## What it is

Replace the current markdown-per-subject pipeline output with a **typed block
schema**. The pipeline emits a `ContentDocument` of the shape:

```json
{
  "schema_version": "1.0",
  "blocks": [ { "type": "Heading", "id": "intro", "data": { ... } }, ... ]
}
```

A web `<BlockRenderer>` dispatches by `block.type` to a dedicated React
component per type. Presentation lives in the renderer; prompts own semantic
structure only.

v0 covers 16 universal block types in three layers:

- **Flow (7):** `Heading`, `Paragraph`, `List`, `Callout`, `Figure`, `Quote`, `Code`
- **Pedagogical (6):** `Definition`, `KeyConcept`, `WorkedExample`, `TryThis`, `Summary`, `CrossReference`
- **Structural (3):** `Formula`, `DataTable`, `Diagram`

Subject-specific (`acc.*`, `chem.*`, `math.*`), assessment (`MCQ`,
`ProblemSet`), and experiment blocks are **explicitly out of scope for v0** —
they land as Layers 4–6 in follow-up sub-epics.

---

## Current state

### Pipeline

`pipeline/prompts.py` instructs Claude to emit freeform JSON where the content
body is markdown strings. Epic 11 (C-1/C-2) layered subject-specific formatting
rules into those prompts — GFM tables for Commerce, KaTeX for Maths/Science,
etc. Improvements work, but:

- Every formatting improvement requires re-reviewing every subject's output
- Subject-specific layout patterns (Balance Sheet totals, reaction arrows,
  two-column proofs) are prompt conventions, not first-class types
- No stable IDs inside a unit — inline reviewer annotations are keyed on
  heading index / paragraph position and break across regens

### Web renderer

`web/components/content/Markdown.tsx` (shipped in Epic 11 C-3) wraps
`react-markdown` + `remark-gfm` + `remark-math` + `rehype-katex`. Works for
flat markdown. There is no concept of a "block" with an ID, a type, or a
schema-validated shape; all structure is implicit in the markdown string.

### Admin review UI

`/admin/content-review/[version_id]/unit/[unit_id]` renders lesson / tutorial
/ quiz / experiment content. Inline `content_annotations` are keyed on a
string like `{unit_id}::{content_type}::{section_id}` where `section_id` is a
positional index. Regens break annotation targets when paragraph order shifts.

### Format validation

`pipeline/content_format_validator.py` (Epic 11 C-6) emits soft `format_drift`
warnings when a heading suggests tabular/formula content but the output
lacks it. This is a heuristic post-pass; the schema-enforced model proposed
here would make many of these warnings redundant.

---

## Why it matters

- **Formatting improvements ship once.** A change to `<WorkedExample>` styling
  instantly applies to every worked example across every subject and grade —
  no prompt iteration, no regen to pick up CSS changes.
- **Subject-specific layouts become first-class.** Once Layer 4 lands,
  `acc.BalanceSheet` is a real type with assets / liabilities / equity arrays
  — the totals-match invariant is schema-enforceable, and the renderer
  handles currency alignment, totals rows, and print CSS without prompt rules.
- **Stable annotation targets.** Block IDs survive regens (positional
  `b-NNNN` + slug anchors for `Heading` / `Definition` / `KeyConcept`), so
  reviewer notes don't break when Claude reorders a paragraph.
- **Version diff gets meaningful.** Block-level diff tells us "WorkedExample
  was replaced" vs "paragraph 4 changed 17 words" — the former is the
  editorially interesting signal.
- **Mobile renderer parity is cheaper.** When Epic 3 ships, the RN renderer
  implements 16 typed components, not a full markdown-compatibility layer.
- **Token economics.** Blocks are smaller JSON than markdown + subject-rules
  prompt prose. Prompt token budget falls slightly; output token ceiling stays
  at 16384 per Epic 11's finding.

---

## Why now

Epic 11 C-1/C-2 shipped the formatting wins we can get from prompt rules
alone. The remaining scope in C-5 (Grade 12 Commerce, Maths-heavy units) is
where the block model pays for itself — rebuilding those with the block
schema avoids another round of prompt-then-review cycles.

---

## Rough scope

| Phase | What gets built | Size |
|---|---|---|
| T-1 | **Schema + types + renderer scaffold.** JSON Schema (Draft 2020-12) at `pipeline/schemas/content_block.v0.schema.json`. Python Pydantic mirror at `pipeline/content_blocks.py` with `validate_document()`. TypeScript types at `web/lib/content/blocks.ts` with `isBlock<T>()` guard. `<BlockRenderer>` + 16 per-type components under `web/components/content/blocks/*.tsx`. Backward-compat: legacy markdown string wrapped as a single `Paragraph` block. Unit tests on both sides. **Fully additive — no runtime change, no prompt change, no DB migration.** | M |
| T-2 | **Pipeline emits blocks — Accounts first.** Prompt builder for Accounts (Grade 11 & 12) emits `ContentDocument`. Validate at pipeline boundary (reuse existing retry-on-validation-error loop). Pipeline post-processes stable IDs: `b-0001`, `b-0002` positional + `def-balance-sheet` slugs for anchorable blocks. Regen Grade 11 + 12 Accounts; side-by-side review vs prior markdown output. | M |
| T-3 | **Admin content review UI.** Unit viewer reads `schema_version` field — dispatches to `<BlockRenderer>` when present, falls back to `<SBMarkdown>` for legacy content. Inline annotations re-keyed on `block.id`. Version diff renders block-level add / remove / modify instead of word-diff-over-markdown. | M |
| T-4 | **Roll out remaining subjects.** Chemistry → Mathematics → Physics → Biology → CS → English → Humanities. Per-subject regen; per-subject side-by-side review gate. No subject-specific blocks yet — still on Layers 1–3. | L |
| T-5 | **Deprecate markdown emission.** Remove the markdown path from prompt builders once ≥80% of active content is on blocks. `<SBMarkdown>` retained for admin-authored strings only (warnings, feedback, etc.). Update CLAUDE.md, ARCHITECTURE.md, `docs/epics/INDEX.md` status. | S |
| T-6 | **Media pipeline — images only.** Image storage under `curricula/{curriculum_id}/{unit_id}/media/` + CDN integration (CloudFront invalidation on content-version bump, same pattern as existing lesson MP3s). `Figure` block wired end-to-end: `src`, `alt` (required), `caption`, `attribution`, `license`. Sourcing workflow per Q10 outcome. Alt-text validator in `content_format_validator.py`. Per-subject image categories map to concrete catalogues (Biology: cell structures, organ systems; Geography: physical/political/climate maps; Physics: circuit/force diagrams; Chemistry: molecular structures; History: primary-source imagery). **Inline video and audio (beyond the existing lesson-narration TTS MP3s) are not ingested** — emitted as a new `MediaPlaceholder` block with `media_type: "video" \| "audio"`, external `url`, and `caption` only. No download, no transcoding, no CDN hosting. | L |

---

## Non-goals (v0)

- **Subject-specific blocks** (`acc.BalanceSheet`, `chem.Reaction`,
  `math.Proof`, etc.) — Layer 4, separate sub-epic after T-5 lands
- **Assessment blocks** (`MCQ`, `NumericAnswer`, `ProblemSet`) — Layer 5.
  Quizzes stay on their current `quiz_set_N_en.json` shape through T-5
- **Experiment / lab blocks** (`Materials`, `SafetyNote`, `Procedure`) —
  Layer 6, probably bundled with an "enhanced visual experiments" epic
- **Mobile renderer parity** — blocked on Epic 3
- **DB schema changes** — content lives on the filesystem; blocks are a
  content-store shape, not a DB shape
- **Video / audio ingest pipelines.** Inline video and audio inside lesson
  blocks are emitted as `MediaPlaceholder` references (external URL +
  caption) only. No download, transcoding, CDN hosting, offline caching,
  or playback UI beyond an "open external link" affordance. Deferred as a
  future enhancement. **Does not affect the existing lesson-narration TTS
  MP3 delivery**, which lives outside the block pipeline and continues to
  serve via pre-signed CDN URL.

---

## Open questions

Fill in the **Your answer** field under each. "My lean" is a default
recommendation — circle it, override it, or write your own reasoning.

---

### Q1. Block ID generation strategy.

Block IDs are the stable identity used for `CrossReference` anchors and for
`content_annotations` targeting. If they drift between regens, every inline
reviewer note breaks.

- (a) **Claude generates IDs.** Cleanest prompt; but Claude picks new slugs
  on every regen → annotation breakage is near-certain.
- (b) **Pipeline stamps positional `b-NNNN`.** Deterministic, trivial.
  Breakage only when block count changes (add/remove); reorder-within-count
  still breaks.
- (c) **Hybrid: positional `b-NNNN` for prose blocks + slugified `def-xxx`,
  `heading-xxx`, `concept-xxx` for anchorable blocks.** Anchorable blocks
  (Heading, Definition, KeyConcept) get human-readable IDs tied to their
  content (`def-balance-sheet`, `heading-the-accounting-equation`). Prose
  blocks get positional IDs. Annotations on anchorable blocks survive regens
  as long as the term/heading text doesn't change; prose annotations are
  best-effort.

**My lean:** (c) — the value of annotation stability scales with how
discussion-worthy a block is, and that correlates with "it's an anchorable
block." Prose-paragraph annotations are already fragile under word edits;
positional is as good as we can do there without a semantic diff tool.

**Your answer:**
Option (c)
---

### Q2. `InlineMarkdown` vs structured inline AST.

Body fields (`Paragraph.markdown`, `Definition.body`, `List.items[]`, etc.)
accept a markdown string restricted to inline constructs (**bold**, *italic*,
`code`, [links](url), `$...$` math). A secondary validator enforces "no
block-level markdown constructs" after JSON Schema passes.

- (a) **Keep markdown strings.** Reuses the existing `remark` / `rehype-katex`
  pipeline. Prompt token budget stays manageable. "No block-level markdown"
  is enforced in a second-pass validator, not the JSON schema itself.
- (b) **Full inline AST.**
  `{ runs: [{bold: "..."}, {text: "..."}, {math: "..."}] }`.
  Zero renderer ambiguity; every inline construct is explicit. Costs ~30-40%
  more output tokens and a much more rigid prompt. Can always tighten to this
  later if (a) causes problems.

**My lean:** (a) — simpler, cheaper, reuses proven Epic 11 tooling.
Revisit if the second-pass validator catches frequent violations.

**Your answer:**
Option (a). I presume with this approach if at a future data we want users to have the ability to export or pdf/ps then it would be a separate functionality. Am I correct?
---

### Q3. First subject for T-2 rollout.

Which subject do we port first?

- (a) **Accounts** (Grade 11 & 12 Commerce). Highest formatting pain today.
  Balance Sheets, journal entries, and P&Ls are where prompt-driven
  markdown is least reliable.
- (b) **Mathematics** (any grade). Most dense KaTeX usage; `WorkedExample`
  and `Formula` block types are directly exercised.
- (c) **Chemistry** (Grade 11/12). Mix of tables (periodic excerpts) +
  formulae (KaTeX) + potential reactions (future `chem.Reaction` block).

**My lean:** (a) — Accounts is where schools will see the credibility
delta first, and the pure-tabular nature exercises `DataTable` + alignment +
tabular-nums end-to-end. Maths is a close second.

**Your answer:**
Option (a)
---

### Q4. Legacy content migration policy.

Existing units (rendered from markdown, no `schema_version` field) stay in the
content store indefinitely through T-3/T-4/T-5. At what point do we regen
them into blocks?

- (a) **Never regen legacy.** The `<BlockRenderer>` backward-compat
  wrapper renders them forever. Subjects only move to blocks on their next
  scheduled rebuild.
- (b) **Regen on demand.** Admin UI gets a "rebuild as blocks" button per
  unit/subject/grade; operator triggers when ready.
- (c) **Full regen post-T-5.** Once all prompt builders emit blocks, kick off
  a background rebuild of everything. Cost: one more full pipeline run across
  all active curricula (~token budget of the last regen).

**My lean:** (b) — regen on demand is the lowest-risk path. Nothing
forces a legacy unit to migrate; admins decide per curriculum. The backward-
compat wrapper keeps the door open indefinitely.

**Your answer:**
Option (b)
---

### Q5. Backward-compat wrapper — prose fidelity.

Wrapping a legacy markdown string as a single `Paragraph` block loses
heading / list / table / code-block structure (the `InlineMarkdown` contract
forbids those). Two options:

- (a) **Render legacy content via the existing `<SBMarkdown>` component
  entirely**, bypassing `<BlockRenderer>` when `schema_version` is absent.
  Legacy content looks exactly as it does today.
- (b) **Pre-parse legacy markdown into blocks at render time**
  (heading → `Heading` block, `|table|` → `DataTable`, etc.). Lets legacy
  content benefit from block-level styling immediately but adds a client-
  side parser and risks subtle layout regressions.

**My lean:** (a) — wall off legacy rendering behind the old component.
Cleanest separation; zero risk of regressing content that's already been
reviewed and approved. The cost is that legacy content doesn't pick up
block-level styling improvements, but that's the price of not regen-ing.

**Your answer:**
Option (a)
---

### Q6. Schema version bumping policy.

`schema_version: "1.0"` is on every document. When we add Layer 4
(`acc.*` etc.) or adjust an existing block's shape, how do we version?

- (a) **SemVer.** Additive changes bump minor (`1.1`); breaking changes bump
  major (`2.0`). Renderer supports multiple majors via a dispatch table.
- (b) **Date-based.** `schema_version: "2026-05"`. Renderer picks the right
  codepath by date; migrations are explicit per bump.
- (c) **Flat integer.** `schema_version: 1`, then `2`, etc. Each is a hard
  cut; content is regen'd when the number changes.

**My lean:** (a) — SemVer is the web standard. Additive Layer-4 blocks are
minor bumps (existing content still validates); breaking changes (field
renames, required → optional) warrant a major bump and per-version dispatch.

**Your answer:**
Option (a)
---

### Q7. Pydantic mirror — Python ↔ JSON Schema drift.

Pipeline validates documents against both the JSON Schema and the Pydantic
model. Over time the two can drift. Options:

- (a) **Hand-author both, CI test for drift.** A parametrised test emits
  valid/invalid samples through both validators and compares verdicts.
  Fails on mismatch.
- (b) **Generate Pydantic from JSON Schema.** `datamodel-code-generator`
  keeps them in sync automatically. Less flexible; generated code is harder
  to extend with domain methods.
- (c) **Drop Pydantic, use `jsonschema` library only.** Single source of
  truth; no mirror to drift. Loses type hints and IDE autocomplete on the
  pipeline side.

**My lean:** (a) — hand-author with a drift test. Mirrors are small
(16 blocks × ~5 fields) and rarely change; the flexibility to add domain
methods (e.g. `WorkedExample.total_steps()`) on Pydantic models is worth it.

**Your answer:**
Option (a)
---

### Q8. First-slice PR — single PR or split?

T-1 is the additive scaffold. It's ~8 new files across pipeline and web.

- (a) **One PR.** Entirely additive; low review risk; lets us ship the
  renderer and schema together so reviewers can eyeball a sample doc.
- (b) **Three PRs.** (1) JSON Schema + Pydantic + tests, (2) TS types +
  tests, (3) `<BlockRenderer>` + 16 components + snapshots. Smaller review
  units; easier bisect if something regresses later.
- (c) **Two PRs.** (1) schemas + types (data-only), (2) renderer
  components (presentation-only).

**My lean:** (c) — schemas + types first lets us freeze the contract
before writing rendering code. One data PR and one presentation PR maps
cleanly to the "separate content from presentation" thesis of this epic.

**Your answer:**
Option (c)
---

### Q9. Subject scope and per-subject presentation needs.

v0's 16 blocks cover universal text presentation. Epic 12 targets **every
subject currently in the Grade 5–12 catalogue**, not just the three
mentioned in Q3. Each subject has presentation affordances the universal
set doesn't fully exercise, and some need subject-specific Layer-4 blocks.

| Subject | Universal blocks exercised (v0) | Layer-4 / media gaps |
|---|---|---|
| Mathematics | Formula, WorkedExample, Definition, DataTable | `math.Proof` (two-column), GeoGebra embed, step-annotated solution |
| Natural Science / Physics | Formula, DataTable, Figure, Diagram | Labelled diagrams (force, circuit, ray), unit-aware numeric fields |
| Chemistry | Formula, DataTable, Figure | `chem.Reaction` (reactants → products with conditions), molecular structure images, periodic-table excerpts |
| Biology | Figure, DataTable, Definition | Labelled anatomical images, micrograph captions, taxonomy trees, punnett squares |
| Accounts / Commerce | DataTable, Formula | `acc.BalanceSheet`, `acc.JournalEntry`, `acc.LedgerAccount`, `acc.TrialBalance` |
| Geography | Figure, DataTable, Diagram | Maps (physical / political / climate), choropleth overlays, `geo.Timeline` |
| History | Quote, Figure, CrossReference | `hist.Timeline`, primary-source callouts, dated-event list, archival imagery |
| English / Literature | Quote, Paragraph | Annotated passage (inline margin notes), vocabulary sidebar |
| Computer Science | Code, DataTable | Truth tables (DataTable covers), pseudocode block, complexity-analysis sidebar |
| Humanities | Quote, Paragraph, Figure | Annotated source, comparison table, case-study callout |

- (a) **Commit to per-subject blocks as Layer 4 follow-ups.** Epic 12
  ships Layers 1–3 universally; each subject gets a dedicated sub-epic
  for Layer 4 after T-5. Cleanest separation of concerns.
- (b) **Pull the highest-pain Layer-4 blocks into T-4.** Accounts gets
  `acc.BalanceSheet` + `acc.JournalEntry` inside Epic 12 since they're
  where the win is biggest; other subjects wait for follow-ups. Blurs
  scope but ships the credibility-moving blocks sooner.
- (c) **Defer all Layer 4 to separate epics.** Keep Epic 12 strictly
  universal (Layers 1–3) so it lands faster. File per-subject Layer-4
  epics from the needs table above once T-5 ships.

**My lean:** (c) — Epic 12 is already 6 phases. Keeping it universal-only
makes the review surface predictable. Each Layer-4 sub-epic after T-5 can
be reasoned about in isolation (per-subject regen, per-subject review gate).

**Your answer:**
Option (c)
---

### Q10. Image sourcing strategy.

`Figure` ships in v0 schema but nothing populates `src` today — the
pipeline only emits text. T-6 wires storage + CDN + renderer, but images
have to come from somewhere. Three candidate sources (not mutually
exclusive):

- (a) **Curated CC / public-domain library.** LLM-driven search tool
  proposes candidates from OpenStax, Wikimedia Commons, NASA, NOAA,
  Smithsonian Open Access, etc.; operator approves in the review UI;
  image + attribution + licence stored alongside the unit. Safe for
  COPPA, free, attribution tracked. Cost: operator time per unit; some
  subjects (Geography maps, Biology micrographs) have excellent
  coverage, others (Accounts diagrams) thin.
- (b) **AI image generation.** Imagen / DALL-E / Gemini on demand.
  Scales. Three unresolved risks before this is viable:
  - **COPPA + child safety:** AI images of people need prompt-guard +
    moderation; generated children/classroom scenes are a minefield
  - **Factual accuracy:** generated science/geography diagrams routinely
    invent features (wrong organelles, fake coastlines, misspelled
    labels); still needs human review per image
  - **Licensing:** educational redistribution terms vary per provider;
    legal review before commit
- (c) **Admin / teacher uploads via review UI.** Works for school-
  authored curricula (Phase D); schools supply their own images with
  their own licensing. Doesn't help default platform content.
- (d) **Hybrid: (a) for platform defaults + (c) for school-authored,
  (b) deferred** until a dedicated child-safety + licensing review
  signs off.

**My lean:** (d) — ship curated CC for platform defaults with an LLM-
assisted search tool (operator picks from a shortlist), wire the Phase D
builder to accept admin uploads, and park AI generation behind a
separate safety/licensing review epic. Avoids blocking T-6 on
legal/safety work while still giving every subject an image pathway.

**Your answer:**
Option (d)
---

## Your decisions / notes

> Add anything the questions above don't cover — subjects to prioritise,
> subject-specific block types to reserve namespace for, accessibility
> concerns, or scope adjustments.

-

---

## Tracking

- **GitHub:** [#193](https://github.com/wegofwd2020-hub/StudyBuddy_OnDemand/issues/193)
- **Related epics:** Epic 11 Content Formatting (C-1/C-2/C-6 — this builds on them)
- **Related issues:** #188 e2e school-admin curriculum submission (re-test after T-2)
