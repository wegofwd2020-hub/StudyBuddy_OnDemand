# Why the Kolibri page feels simple — a teardown

**29 August 2026.** Companion to [`COMPETITIVE_kolibri.md`](COMPETITIVE_kolibri.md).
Subject: [learningequality.org/kolibri/about-kolibri](https://learningequality.org/kolibri/about-kolibri/)

Written because the page reads as unusually calm and we should know *why* before
borrowing from it. Everything below is measured from the served HTML and CSS, not
from impression. Where something is inference rather than measurement, it says so.

---

## The finding: the page only has two ideas on it

This is the whole answer. It is structural, not stylistic.

```
h1        1
h2        6      <- but only TWO are real page sections
h3       21      <- 13 of them are FAQ questions; 4 are footer links
p        62
img      24
words  ~2,018
```

The two real `h2`s are:

1. **"How Kolibri works for…"** — four audience cards (Learners, Educators, Program
   Administrators, Content and Curriculum Specialists)
2. **"Frequently asked questions"** — a 13-item accordion

That is the page. Hero → who it's for → what you're about to ask → footer. Everything
else is *progressive disclosure*: 13 headings' worth of content sit collapsed until
someone wants them.

**The simplicity is a content decision wearing a design costume.** They did not
achieve calm by styling restraint — they achieved it by putting almost everything
behind an accordion and committing the open page to two questions.

### Why this matters to us

Our landing page and `/for-schools` carry a hero, six feature cards, a tour gateway,
an eight-feature grid, pricing tiers, an FAQ and a CTA — as separate, always-open
sections. Kolibri would render most of that collapsed.

Worth noticing: the four audience cards are *exactly* the persona split we did in
`DESIGN_dashboards.md` §1–2 (student / teacher / school admin / platform admin).
They put that split on the **marketing page** as the primary navigation device.
We keep it in an internal design doc.

---

## Typography

Three families are loaded from Google Fonts as full variable ranges:

| Family | Loaded weights | Role |
|---|---|---|
| **Figtree** | 300–900, incl. italic | The applied face — `font-family: 'FigTree', sans-serif` |
| **Petrona** | 100–900, incl. italic | Serif; loaded |
| **Plus Jakarta Sans** | 200–800, incl. italic | Loaded |

Figtree is a geometric-humanist sans — friendly, slightly rounded, legible at small
sizes. It is doing the work, and it is *not* Inter, which matters: the page reads as
chosen rather than defaulted.

The type scale on the page is extremely narrow. Measured declarations:

```
font-size:   1rem · 1.5rem · inherit
font-weight: normal · 600
line-height: 1.25 · 1.5 · 150%
```

**Two sizes and two weights.** That is the second half of why it feels calm — there
is almost no typographic hierarchy competing for attention, because there are almost
no levels.

> ⚠️ **The one thing not to copy.** Loading three variable families at full 300–900
> ranges is a real payload for a product whose entire premise is low-bandwidth,
> low-spec devices. I could only find **Figtree** actually applied in the served
> styles; Petrona and Plus Jakarta Sans may be used elsewhere on the site or may be
> vestigial. Either way it sits oddly against the offline-first mission.

---

## Colour

Palette measured from the page's own inline styles (not the Bootstrap layer):

| Hex | Role |
|---|---|
| `#4368f5` | Blue — primary action / link |
| `#ffc300` | Yellow — accent, used sparingly |
| `#fefff3` | Warm off-white — page ground |
| `#535352` | Warm dark grey — body text |
| `#c5c5c7` / `#c7c7c5` | Light greys — rules, dividers, muted surfaces |

Two observations worth taking:

- **The neutrals are warm, not pure.** `#535352` and `#fefff3` both carry a slight
  warmth rather than being `#333` on `#fff`. That is what stops the page reading as
  clinical, and it costs nothing.
- **Two accents, and the yellow is rationed.** Blue carries interaction; yellow
  appears rarely enough to still mean something when it does.

---

## Structure and rhythm

```
max-width:     1000px · 1150px · 1200px
border-radius: 24px (cards) · 5px (small) · 0.3em
padding:       10px 24px (buttons)
```

A **~1000–1200px measure** keeps running text near a readable line length instead of
letting it span a wide monitor. The 24px radius on cards is generous enough to read
as soft without becoming a pill.

### The stack underneath

Bootstrap 5, essentially unmodified — the CSS bundle is 231 KB and its custom
properties are stock (`--bs-primary: #0d6efd`, the standard Bootstrap blue, appears
29 times). Their own design lives in **~43 KB of inline `<style>` blocks** (24 of
them) layered on top.

That is worth naming plainly: **the page's appeal is not coming from a bespoke design
system.** It is stock Bootstrap plus a narrow type scale, a warm palette, a
constrained measure, and — most of all — a ruthless content edit.

---

## What to take, and what not to

**Take:**

1. **Collapse the secondary content.** An FAQ accordion is not a lesser section; it
   is how you keep a page to two ideas while still answering thirteen questions.
2. **Lead with audience, not features.** "How Kolibri works for Learners / Educators /
   Administrators / Content Specialists" lets a reader self-select in one glance.
   We have the persona work already; it is just not on the marketing page.
3. **Narrow the type scale.** Two sizes and two weights, deliberately. Most of the
   perceived calm is the absence of levels.
4. **Warm the neutrals.** `#535352` on `#fefff3` rather than `#333` on `#fff`.

**Don't take:**

1. **Three variable font families.** Especially not for us — see the note above.
2. **Stock Bootstrap as the base.** We are on Tailwind v4 with per-school theming
   (`school_theme`, migration 0052) and a subject palette. Their approach would
   undo that.
3. **The claim density.** The page states impact figures (*"220+ countries"*,
   *"up to 97%"*) in the same calm voice as its product facts, which is exactly what
   makes them easy to absorb uncritically — see `COMPETITIVE_kolibri.md`.

---

## Method

Measured, not eyeballed:

```bash
curl -sL https://learningequality.org/kolibri/about-kolibri/ -o kolibri.html
curl -sL https://learningequality.org/static/css/main.css -o main.css
# heading census, word count, inline-style extraction, hex frequency
```

Counts come from the served markup with `<script>` and `<style>` stripped. Colour
frequencies are from the page's inline styles, deliberately separated from the
Bootstrap bundle's defaults — mixing them would have reported Bootstrap's palette as
theirs.
