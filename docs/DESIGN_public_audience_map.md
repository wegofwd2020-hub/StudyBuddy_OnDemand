# Audience on the marketing pages — what we already have

**29 August 2026.** Working note for item 2 of "What to take" in
[`DESIGN_kolibri_site_teardown.md`](DESIGN_kolibri_site_teardown.md) — *"lead with
audience, not features."* Companion: [`COMPETITIVE_kolibri.md`](COMPETITIVE_kolibri.md).

Everything below is checked against the repo, not against the design docs.

---

## First, a correction to the teardown

The teardown says:

> *"We have the persona work already; it is just not on the marketing page."*

**That is wrong, and it changes the task.** We have an audience-split page in
public, live, with real depth behind it:

| Page | What it is |
|---|---|
| `web/app/(public)/tour/page.tsx` | Three role cards — School Admin · Teacher · Student — each with an icon, a one-line job description and its own CTA |
| `/tour/school-admin` · `/tour/teacher` · `/tour/student` | A full page each |

So item 2 is not *"build an audience split."* It is **"we built one and buried
it."** Three concrete gaps, in descending order of cheapness:

1. **It is one level down.** The landing page links to `/tour` once
   (`web/app/(public)/page.tsx:226`), below six feature cards. Kolibri puts the
   audience split *on* the page as one of only two real sections.
2. **`/for-schools` does not link to `/tour` at all.** Our most audience-specific
   page has no route to our audience-specific content. That is a dead end, not a
   design decision.
3. **The split has three cards; the personas doc has four roles** — and the
   missing one is the interesting one. See below.

---

## The mapping

Kolibri's four audience cards against what exists here. "Where it lives" cites
code, not intent.

| Kolibri audience | Ours | Where it lives | State |
|---|---|---|---|
| **Learners** | Student | persona §2.1 · `/tour/student` · student portal | Complete — but see the buyer problem below |
| **Educators** | Teacher | §2.2 · `/tour/teacher` · `/school/dashboard` | Complete on the marketing side. In-product, teacher and school_admin still **share one dashboard** whose numbers now mean different things (#628) |
| **Program Administrators** | **Splits into two** — School admin (one school) and district admin (many) | §2.3 · `/tour/school-admin` · Epic 5 | **Partial.** Kolibri's program admin runs a *deployment across schools*; ours runs one. Our true equivalent is Epic 5, unbuilt |
| **Content & Curriculum Specialists** | `curriculum_mgmt` capability · Authoring Studio | `permissions.py:98-110` · `teacher_capabilities` (migration 0059) · `/admin/authoring` | **The capability exists; the role does not.** No card, no tour page, no name in the product |
| *(none)* | Platform admin | §2.4 · `/admin` | Correctly absent — internal ops, not a customer audience |

### The fourth card is a naming gap, not a build gap

`COMPETITIVE_kolibri.md` already flagged this ("*'Content specialist' is a named
role… we have the capability but have not named the job*"). The mapping makes it
concrete. We ship all three grants:

```python
ALLOWED_CAPABILITIES = {
    "curriculum.commission",  # approve/adopt/load + trigger generation
    "curriculum.review",      # approve/publish generated content
    "curriculum_mgmt",        # umbrella — covers both gates
}
# permissions.py — additive, granted per teacher, minted into the JWT at login
```

A teacher holding `curriculum_mgmt` is doing exactly the job Kolibri puts on its
marketing page. In our product that person has no title, no tour page, and no
card — they are "a teacher with a checkbox ticked". This is the one place where
copying Kolibri would add something we do not have, and it costs a name and a
page rather than a feature.

---

## The asymmetry that stops this being a straight copy

**Kolibri's four audiences are all users of a deployment somebody else paid for.**
They are a grant-funded non-profit; their marketing page never has to sell. Every
card can be a pure "here's your job" card.

**Our audience list contains the buyer.** Checked against the nav
(`components/layout/PublicNav.tsx`), the only purchasing CTA on the public site is
**"Register your school"**, and the school admin is simultaneously the operator and
the person with the card. Meanwhile:

- **Students cannot sign up.** Accounts are school-provisioned (#609). `/signup`
  exists but is not linked from the nav.
- **Teachers cannot buy.** They are provisioned by their school.

So a straight four-card grid would place our **only** purchasing persona as one of
four equal tiles, three of which lead to people who cannot act. Kolibri can afford
that. We cannot.

**Consequence for the design:** take the *device* (let a reader self-select in one
glance) without taking the *flatness*. The school admin card is the conversion
path; the others are reassurance that the product serves the people they are
buying for.

---

## What I would actually do

Cheapest first. None of this needs a product decision except where marked.

1. **Link `/for-schools` → `/tour`.** One line. Closes a dead end today.
2. **Promote the audience split on the landing page** — move the three cards up,
   above or in place of the six feature cards, rather than leaving a single link
   below them. This is the actual content of item 2.
3. **Weight the cards.** School admin leads and carries the CTA; teacher and
   student read as "and here is what your staff and students get". Not four equal
   tiles.
4. **Name the curriculum specialist** — 💭 *your call*, because it is a product
   decision, not a copy one. Adding a fourth card means committing to the role in
   the product too (a title, and probably a tour page). The capability already
   ships; naming it is what is missing.

Item 2 is therefore mostly **promotion and weighting of existing pages**, plus one
genuine open question.

---

## Open question

**Is "Learners" a marketing audience for us at all?** Kolibri's learners can at
least install and use the thing. Ours cannot sign up, cannot buy, and reach the
product only through a school that already bought it. A student card may still
earn its place as reassurance *to the buyer* — but it should be written for the
buyer's eye, not addressed to a student who cannot act on it.

That is a copy decision, and it is the one place where "lead with audience" could
quietly mislead us if taken literally.
