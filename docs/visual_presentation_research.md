# Visual presentation research — Sets and Functions

> Research artifact, not production code. Three explorations of how to graphically present generated content, evaluated against the Grade 11 Science *Sets and Functions* unit (`G11-MATH-001`).

## Why this research exists

The pipeline emits richly-formatted Markdown for every lesson, tutorial, quiz, and experiment. Markdown alone is sufficient for the web reader, but most chapters contain visual primitives — Venn diagrams, function plots, arrow mappings, animated walk-throughs — that can be rendered far more effectively than as static images embedded in `<SBMarkdown>`.

Before committing to one rendering strategy across the platform, we built three deliberately different demonstrations from the **same** chapter and put them side-by-side. The artifact set under `sample_content/g11-science/G11-MATH-001_Sets_and_Functions/` is the output.

## Mapping to the project plan

This work is **research input** to several active and parked epics — it does not itself ship to students. The mapping:

| Epic / Phase | Relevance | What this research informs |
|---|---|---|
| **Epic 3 — Student mobile app** *(parked, behind testing + hosting)* | **Strong** | The mobile renderer needs to display the same chapter content as the web. Pre-rendered MP4 (Option 3) and inline SVG (Option 2) both ship cleanly to React Native; heavy interactive JS (Option 1's Plotly + Mermaid) does not. This research tells us which idioms survive the platform jump. |
| **Epic 11 — Content Formatting** *(C-7 / C-8 pending)* | Direct | C-8 is "mobile renderer parity" for the Markdown content. The catalogue (Option 2) gives us a reference set of "what good looks like" per visual category that the web `<SBMarkdown>` and the mobile renderer must each match. |
| **Epic 7 — Admin Dashboard / Content Review** *(complete; reviewer extensions possible)* | Indirect | The interactive demo page (Option 1) is a candidate format for admin reviewers comparing visual presentation alternatives during content QA. |
| **Phase 2 — Content Pipeline** *(complete)* | Reference only | Confirms the pipeline already emits everything Options 1–3 need (KaTeX-flavoured Markdown, GFM tables, structured JSON for quizzes). No pipeline change required by any of the three options. |
| **Phase 3 — Progress Tracking** *(complete)* | None | Progress tracking is data plumbing; this is content rendering. No relationship. |

So the answer to "how much of this is part of phase 3?": **none of it** if "phase 3" means backend Phase 3 (Progress Tracking). **Most of it is upstream of Epic 3 (mobile)** and **Epic 11 C-8 (mobile renderer parity)**.

## The three options

### Option 1 — Single interactive HTML page (`Demos.html`)

One self-contained file using KaTeX, Plotly, Mermaid, inline SVG, and vanilla JS animation across 12 worked examples on one scrollable page. Optimised for *evaluating* presentation idioms side-by-side.

| Tradeoff | Fit |
|---|---|
| Interactive | strong |
| Mobile-friendly | weak (Plotly bundle ≈ 3.5 MB) |
| Production-ready | research-grade |
| Reusable parts | requires extraction |

### Option 2 — Per-example artifact catalogue (`Option2_Catalogue/`)

The right tool per visual: hand-authored SVG for set diagrams and arrow diagrams (driven by a TS spec generator), Desmos / GeoGebra recipes for function graphs with sliders, Manim Python scenes for animations (with an SMIL no-install fallback for the projectile), and a KaTeX HTML cheatsheet for typography.

| Tradeoff | Fit |
|---|---|
| Per-file polish | high |
| Mobile-friendly | strong (SVG + MP4) |
| Install footprint | varies (Manim heaviest) |
| Reusable parts | each file is independently embeddable |

### Option 3 — Remotion explainer video (`Option3_Video/`)

A 9-scene React-driven composition rendered to `~/Downloads/Sets_and_Functions_Demo.mp4` (1920×1080, 30 fps, ~1 min 57 s). All animation is `useCurrentFrame()`-driven per Remotion rules; PAI charcoal + purple theme via `theme.ts`.

| Tradeoff | Fit |
|---|---|
| External-share polish | high |
| Mobile-friendly | strong (8.6 MB MP4) |
| Render cost | one-shot ~5 min on dev laptop |
| Reusable parts | the project source — re-render for any chapter using the same scaffold |

## Which to use when

```
                  research / pick winners       student-facing delivery
  ┌──────────────────────────────────┬─────────────────────────────────────┐
  │ Option 1                         │ Option 3 (mobile / external share)  │
  │ — compare idioms side-by-side    │ — one MP4 ships everywhere         │
  │                                  │                                     │
  │                                  │ Option 2 (web embed / docs)         │
  │                                  │ — SVG + Desmos for interactive      │
  │                                  │   web rendering                     │
  └──────────────────────────────────┴─────────────────────────────────────┘
```

For a typical chapter:

1. Build the catalogue (Option 2) — the visual primitives and the Desmos recipes carry the technical content.
2. Use Option 1 only when there's a real comparison to be made between idioms.
3. Render Option 3 when you need a polished single artifact (deck, marketing, mobile pre-roll, externally shared link).

## Scripts produced as a byproduct

Two reusable TypeScript generators live under `scripts/` and apply to any unit, not just `G11-MATH-001`:

| Script | Purpose |
|---|---|
| `scripts/extract_unit_to_markdown.ts` | Reads a `content_store_data/.../UNIT_ID/` directory and emits a single Markdown document (lesson + tutorial + quizzes) suitable for archiving, pandoc-rendering to PDF/HTML, or feeding into any of the three options. |
| `scripts/generate_arrow_diagrams.ts` | Emits hand-authored arrow-diagram SVGs from a declarative spec — adding a new diagram is six lines. Used to build Option 2's `arrow-diagrams/` set. |

## File inventory

```
sample_content/
└── g11-science/
    └── G11-MATH-001_Sets_and_Functions/
        ├── Sets_and_Functions.md                (extracted source)
        ├── Sets_and_Functions.html              (pandoc + KaTeX render)
        ├── Demonstration_Options.md             (the three-option design memo)
        ├── Demos.html                           (Option 1 — single page, 12 examples)
        ├── Option2_Catalogue/                   (Option 2 — 22 files, see its README)
        └── Option3_Video/                       (Option 3 — Remotion source; render to ~/Downloads)
```

The rendered MP4 lives at `~/Downloads/Sets_and_Functions_Demo.mp4`, **not** in the repo (gitignored — keeps the repo lean).

## Next decisions

1. Pick winning idiom per visual category from the Option 1 page → drives the production renderer choice.
2. Decide whether Manim stays as a separate render path or gets ported to Remotion / TS-only. (Lean: port to Remotion if we end up using more than one or two animations across chapters.)
3. Decide whether `sample_content/` is a research-only area or becomes the ingestion source for an "exemplar gallery" surfaced inside the admin / school portal.

Decisions 1 and 2 are blocked on Epic 3 / Epic 11 C-8 unparking.
