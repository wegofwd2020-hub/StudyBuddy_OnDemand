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
3. **Three cards against Kolibri's four** — which turns out to be correct rather
   than short. See "Their fourth card is our third one's job" below.

---

## The mapping

Kolibri's four audience cards against what exists here. "Where it lives" cites
code, not intent.

| Kolibri audience | Ours | Where it lives | State |
|---|---|---|---|
| **Learners** | Student | persona §2.1 · `/tour/student` · student portal | Complete — but see the buyer problem below |
| **Educators** | Teacher | §2.2 · `/tour/teacher` · `/school/dashboard` | Complete on the marketing side. In-product, teacher and school_admin still **share one dashboard** whose numbers now mean different things (#628) |
| **Program Administrators** | **Splits into two** — School admin (one school) and district admin (many) | §2.3 · `/tour/school-admin` · Epic 5 | **Partial.** Kolibri's program admin runs a *deployment across schools*; ours runs one. Our true equivalent is Epic 5, unbuilt |
| **Content & Curriculum Specialists** | **Owned by school admin**, delegable to a teacher | `permissions.py:42-53` (`review:approve`, `pipeline:trigger`, `curriculum:delete`) · `_CAPABILITY_SUPERSET_ROLES` · `teacher_capabilities` (migration 0059) | **Not a missing role — an absorbed one.** They need a separate persona because they have no school-admin tier; we do |
| *(none)* | Platform admin | §2.4 · `/admin` | Correctly absent — internal ops, not a customer audience |
| *(none)* | **School admin as a tier at all** | ADR-005 · `/school/*` | Kolibri has no equivalent. Their deployments are run by programmes, not by the school |

### Their fourth card is our third one's job

The obvious reading of that table is "they name a role we forgot to name."
Checked against the code, it is the opposite.

`school_admin` holds the curriculum duties **directly** in its permission set:

```python
"school_admin": {
    ..., "review:approve", "content:block", "pipeline:trigger", "curriculum:delete",
}
# permissions.py:42-53
```

and it is the sole member of `_CAPABILITY_SUPERSET_ROLES`, so `has_capability()`
returns true for every curriculum grant without any row in `teacher_capabilities`.
The guards say so in their own error strings — *"Requires the
'curriculum.commission' capability (or school_admin)"*
(`school/capability_guards.py`).

So the three additive capabilities (#358) are not filling a hole in the role
model. They **delegate a duty the school admin already owns** down to a named
teacher, one gate at a time:

| Grant | What the school admin is handing over |
|---|---|
| `curriculum.commission` | Gate 1 — adopt/load a curriculum and spend build budget |
| `curriculum.review` | Gate 2 — approve and publish what came back |
| `curriculum_mgmt` | Both |

**Why Kolibri needs the separate persona and we do not.** Their content work
happens in Studio, *above* any individual school — a programme or ministry
specialist assembles channels for many deployments at once. They have no
school-admin tier for it to belong to. Ours is a within-school job, so it belongs
to the person who runs the school and is delegable when that school is large
enough to want a specialist.

**Consequence for the marketing page: do not add a fourth card.** Three is the
right number for us. The curriculum job is not a missing audience — it is
something to *say on the school admin card*, and the delegation is a selling
point rather than an org chart: one person can own curriculum, or they can hand
either gate to a teacher without making them an administrator.

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

Cheapest first. None of it needs a product decision.

1. **Link `/for-schools` → `/tour`.** One line. Closes a dead end today.
2. **Promote the audience split on the landing page** — move the three cards up,
   above or in place of the six feature cards, rather than leaving a single link
   below them. This is the actual content of item 2.
3. **Weight the cards.** School admin leads and carries the CTA; teacher and
   student read as "and here is what your staff and students get". Not four equal
   tiles.
4. **Say the curriculum job out loud on the school admin card** — and say it is
   delegable. Not a fourth card: the duty already belongs to that role, and #358
   lets it be handed to a teacher one gate at a time. That is a differentiator
   Kolibri cannot state, because they have no school-admin tier to delegate from.

Item 2 is therefore **entirely promotion and weighting of pages we already have**.
No new role, no new card, no product decision.

---

## Open question

**Is "Learners" a marketing audience for us at all?** Kolibri's learners can at
least install and use the thing. Ours cannot sign up, cannot buy, and reach the
product only through a school that already bought it. A student card may still
earn its place as reassurance *to the buyer* — but it should be written for the
buyer's eye, not addressed to a student who cannot act on it.

That is a copy decision, and it is the one place where "lead with audience" could
quietly mislead us if taken literally.
