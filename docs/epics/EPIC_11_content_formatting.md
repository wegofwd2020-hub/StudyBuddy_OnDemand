# Epic 11 — Content Presentation & Formatting

**Status:** ✅ Go — 9 questions resolved 2026-04-15

---

## What it is

Upgrade AI-generated content so domain-specific structures render correctly:

- **Tabular content** (Balance Sheet, P&L, Trial Balance, periodic-table
  excerpts, truth tables, reaction mechanisms, comparisons) presents as
  proper tables — not prose bullet lists.
- **Formulae** (equations of motion, accounting identities, stoichiometry,
  algebraic proofs) render as typeset math, not raw `E = mc^2` text.
- Prompts enforce this at generation time so the content JSON already
  carries the right shape; the renderer just needs to handle it.

---

## Current state

### Pipeline (generation)

`pipeline/prompts.py` instructs Claude:

> "You MUST respond with ONLY valid JSON — no markdown fences, no extra text,
> no explanation."

There are no per-subject guidelines about:
- When to use markdown tables (`| col | col |` GFM syntax)
- How to format formulae (no LaTeX / KaTeX convention, no inline vs display
  distinction)
- Tabular genres by subject (Commerce Balance Sheets, Chemistry reaction
  mechanisms, CS truth tables, etc.)

As a result, Grade 11 Commerce lessons render accounting statements as prose
bullet lists, and Physics/Maths formulae appear as raw text.

### Web renderer

- `react-markdown@10.1.0` + `remark-gfm@4.0.1` are installed.
  → **GFM tables already render correctly** if the JSON contains them.
- `remark-math` + `rehype-katex` are **not installed**.
  → LaTeX / KaTeX delimiters (`$...$`, `$$...$$`) show as raw source.
- No shared Markdown wrapper — each viewer (lesson, tutorial, quiz,
  experiment) calls `<ReactMarkdown>` with its own plugin list.

### Mobile renderer

Epic 3 not yet implemented. Whatever Markdown library Expo/RN picks up must
match the web feature set (GFM tables + math) or content will look different
across platforms.

### PDF export

Not verified in this epic scope — flagged as an open question below.

---

## Why it matters

- **Commerce credibility.** A Balance Sheet presented as bullet points makes
  the platform look unprofessional to school commerce teachers. This is a
  subject where format IS content.
- **Maths comprehension.** `E = mc^2` and `\frac{a}{b}` rendered as raw text
  are a barrier to reading — especially for the students we target at 1–2
  grade levels below their actual grade (per CLAUDE.md reading-level rule).
- **Cross-platform consistency.** When mobile ships (Epic 3), content must
  look identical to web. Fixing this at pipeline-prompt time ensures the
  canonical content carries the shape, so both renderers see the same input.
- **Generation cost amortisation.** Re-running the pipeline for
  already-built grades is cheap relative to the quality win; we only pay
  this cost once per prompt iteration.

---

## Rough scope

| Phase | What gets built | Size |
|---|---|---|
| C-1 | **Prompt guidelines — universal.** Add GFM-table + KaTeX-delimiter instructions to the base lesson / tutorial / quiz / experiment prompts in `pipeline/prompts.py`. Universal rules: comparisons with 2+ attributes, chronologies, tabular genres → markdown tables. Inline math `$...$`, display math `$$...$$`. | S |
| C-2 | **Prompt guidelines — per-subject.** Commerce (Accountancy/Business Studies/Economics): Balance Sheet, P&L, Trial Balance, Cash Flow layouts as tables. Science (Chemistry/Physics/Biology): reaction mechanisms, periodic excerpts, taxonomy as tables; formulae as KaTeX. Maths: every equation in `$...$`; numbered-step proofs. Technology/CS: pseudocode in fenced code blocks (already works), truth tables + Big-O comparisons as tables. | M |
| C-3 | **Renderer — math plugin wiring.** Install `remark-math` + `rehype-katex` + `katex` CSS in web. Create `web/components/content/Markdown.tsx` shared wrapper exporting `<SBMarkdown>{source}</SBMarkdown>` with the full plugin list (GFM + math). Replace direct `<ReactMarkdown>` calls in lesson / tutorial / quiz / experiment viewers. | S |
| C-4 | **Renderer — table + math styling.** Zebra-striped tables, numeric-column alignment (right-aligned for Balance Sheet amounts using `font-mono tabular-nums`, per CLAUDE.md §18), display math centered with subtle margin. Honour OpenDyslexic accessibility mode (per Epic 9) — KaTeX fonts swap when dyslexia mode is on. | S |
| C-5 | **Content regeneration — decision-gated.** Once C-1/C-2/C-3 land, re-run the pipeline against existing curricula to apply the new prompts. Scope depends on Q1 below: only new builds vs. targeted re-run vs. full rebuild. | S–L |
| C-6 | **Schema validation — optional hardening.** Extend `pipeline/schemas.py` to fail fast if a section that should be tabular (detected heuristically by presence of e.g. "Balance Sheet", "Trial Balance" in the heading) doesn't contain a table. Surfaces prompt drift early. | S |
| C-7 | **PDF export smoke check (Q6 resolution).** Verify only — run an export on a Commerce + Maths lesson and document whether tables + math survive. **No production PDF-generation feature** will be built. If broken, the finding is noted for a future epic. | S |
| C-8 | **Mobile renderer (Epic 3 coord).** Ensure the Expo/RN Markdown component used in Epic 3 supports GFM tables + KaTeX. Decision lives in Epic 3 M-phases; this is a cross-reference so the two epics stay aligned. | S |
| C-9 | **Attributed quotes (Q9 resolution).** Prompt rule that allows markdown blockquote attribution (`> Energy cannot be created or destroyed. — James Prescott Joule`) and explicitly forbids invented citations / paper titles / DOIs. Blockquote styling in the shared Markdown component renders the attribution line right-aligned and italicised. Curated external link catalog (option d) is deferred to a follow-up epic. | S |

---

## Open questions

Fill in the **Your answer** field under each. "My lean" is a default
recommendation — circle it, override it, or write your own reasoning.

---

### Q1. How much content do we regenerate once C-1/C-2/C-3 land?

- (a) Only new builds going forward — existing Grades 10–12 stay as they are.
- (b) Re-run only the subjects most visibly affected: Grade 11 Commerce,
  Grade 11/12 Science, any Maths-heavy Grade.
- (c) Full regeneration of everything built so far.

**My lean:** (b) — targeted re-run of the subjects where the current
formatting actively hurts comprehension. Full regen is overkill for
English / Humanities where tables + formulae aren't the norm.

**Your answer:**
Option (b) 

**Your reasoning (optional):**

---

### Q2. KaTeX delimiter convention.

- (a) Inline `$...$` + display `$$...$$` — the traditional LaTeX pair.
  Simple; widely recognised; requires escaping literal `$` in content.
- (b) Inline `\\(...\\)` + display `\\[...\\]` — the "safer" pair that avoids
  `$` escaping but is verbose.
- (c) Both supported via `remark-math` config — let Claude pick.

**My lean:** (a) — most examples Claude has seen use `$`-delimiters and
will be consistent. Literal `$` in commerce amounts can be written as `\$`
or formatted outside math mode (`USD 150.00` rather than `$150.00`).

**Your answer:**
Option (a)
---

### Q3. Table row limits.

Balance Sheets in real accountancy can run 30+ rows. A single markdown
table that wide breaks on mobile and looks cluttered.

- (a) No limit — let Claude produce whatever the content demands.
- (b) Cap at 15 rows per table; split larger statements into
  "Assets" / "Liabilities" / "Equity" sub-tables.
- (c) No limit on web; add horizontal-scroll wrapper for narrow viewports.

**My lean:** (c) — horizontal scroll with sticky first column.
Splitting accountancy statements across sub-tables loses the "total must
equal total" comprehension beat.

**Your answer:**
Option (c)
---

### Q4. Numeric alignment.

Balance Sheet amounts look wrong when left-aligned.

- (a) Right-align columns whose header contains "Amount", "Value", "Total",
  or a currency symbol. Heuristic at render time.
- (b) Pipeline emits cell alignment markers (`|---:|`) in GFM tables.
  GFM supports per-column alignment via colon position in the separator row.
- (c) Both — prompt Claude to emit GFM alignment markers; renderer falls
  back to heuristic if missing.

**My lean:** (c) — belt-and-braces. Cheap to do both.

**Your answer:**
Option (c)
---

### Q5. Scientific-notation + unit formatting.

Physics content includes quantities like `1.6 × 10⁻¹⁹ C`.

- (a) KaTeX: `$1.6 \times 10^{-19}\,\mathrm{C}$` — precise, nicely typeset.
- (b) Plain Unicode: `1.6 × 10⁻¹⁹ C` — renders fine, no plugin needed,
  but can't be copy-pasted into a calculator.
- (c) Both — KaTeX in formulae contexts, Unicode in inline body prose.

**My lean:** (c) — display equations get KaTeX (centred, typeset), and
inline "the charge is 1.6 × 10⁻¹⁹ C" in prose uses Unicode for readability.

**Your answer:**
Option (c)
---

### Q6. PDF export — in scope now?

- (a) Skip — PDF not mentioned in any current epic; no user need.
- (b) Verify only — run an export on a Commerce + Maths lesson and
  document whether tables + math survive. Fix in C-7 only if broken.
- (c) Full C-7 phase — ship PDF export at parity as part of this epic.

**My lean:** (b) — quick verification; only invest if broken.

**Your answer:**
Option (b). Keep a ticket to test this, but NO PDF file generation option to be be provided.
---

### Q7. Content moderation — does AlexJS accept KaTeX source?

AlexJS flags some words as gendered / inclusive-language concerns. Math
source has no natural language issues, but a stray `\boldsymbol{he}` or
similar LaTeX macro could trigger a false positive.

- (a) No action — if false positives emerge, handle case-by-case.
- (b) Pre-process: strip `$...$` / `$$...$$` blocks before feeding content
  to AlexJS. Re-insert for review.

**My lean:** (a) — don't pre-optimise. We'll see false positives quickly
if they exist.

**Your answer:**
Option (a)
---

### Q8. Accessibility — screen readers and KaTeX.

KaTeX emits MathML alongside the visual layout. Screen readers (VoiceOver,
TalkBack, NVDA) pick this up — most of the time. Some render "Equation
unreadable" for complex expressions.

- (a) Rely on KaTeX defaults — it's the industry standard and mostly works.
- (b) Additionally expose `aria-label` on display math with a
  human-readable transcription generated by the pipeline alongside the
  LaTeX source.

**My lean:** (a) for now. Epic 9 (Accessibility) can layer (b) in as a
later enhancement if users report issues.

**Your answer:**
Option (a)
---

### Additional notes

> Add subjects, edge cases, examples, or scope adjustments that the
> questions above don't cover. Paste screenshots or sample JSON snippets
> here so we have concrete reference material for the prompt work.


### Q9. External references / quotes.

Till now no explicit handling of external references or quotes attributed to
others. What's the best pathway?

- (a) Ban external references entirely — content stands on its own.
- (b) Attributed quotes only — markdown blockquote with author line.
  No citations, no URLs.
- (c) Structured reference metadata per unit — LLM-generated citation list.
  High hallucination risk without human curation.
- (d) Inline quotes (b) + curated external link catalog reviewed by admins.

**My lean:** (b) for this epic. (d) queued as a follow-up epic if there's
demand. (c) avoided because LLM-generated citations are frequently
fabricated; (d) mitigates this via a human-reviewed allow-list.

**Your answer:**
Option (b). (d) queued as a follow-up epic.

-
-
-
