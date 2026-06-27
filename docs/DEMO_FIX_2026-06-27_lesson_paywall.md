# StudyBuddy Demo — Fix Update & Testing Instructions

**Date:** 2026-06-27
**Re:** Venki's 06/27 feedback — *"Student sees subjects but Lesson/Quiz shows 'This isn't available yet.' School Admin can see the lessons/quizzes. Am I missing something?"*
**Environment:** `demo.usestudybuddy.com` (Hetzner demo server)
**Status:** ✅ **Fixed and verified live**

---

## 1. What was actually happening

This was **not** a missing-content or content-not-published problem. The lessons
were generated, published, and on disk the whole time — which is exactly why the
**School Admin** could see them.

The blocker was the **free-tier subscription gate**:

- Student lessons are limited to **2 free lessons** per student
  (`_FREE_TIER_LESSON_LIMIT = 2`). After that, every lesson returns **HTTP 402
  "subscription required"** until the school has an active subscription.
- The student account (`callmds@gmail.com`) had already used its 2 free lessons.
- Neither demo school had an **active subscription** on record, so every student
  stayed stuck on the free tier.
- Only the **lesson** endpoint is gated this way. **Quizzes and tutorials are not
  gated**, which is why those kept working.

**Why Admin saw everything and the student didn't:** the school-admin / teacher
content views read content directly and are not subject to the per-student
subscription limit. Only the student experience hits the paywall.

### Verification (before the fix), account `callmds@gmail.com`

| Content type | Result |
|---|---|
| Curriculum / subjects | ✅ 200 (loads — matches what you saw) |
| **Lesson** (every unit) | ❌ **402 — paywall** |
| Quiz | ✅ 200 |
| Tutorial | ✅ 200 |

---

## 2. What was fixed

Activated a subscription for **both** demo schools so their students are no longer
on the capped free tier:

| School | Plan | Status | Valid until |
|---|---|---|---|
| MilfordWaterford | professional | active | 2027-06-27 |
| ABC School | professional | active | 2027-06-27 |

After the change, lessons were re-tested for `callmds@gmail.com`:

| Unit | Lesson result |
|---|---|
| G8-MATH-001 | ✅ 200 |
| G8-SCI-001 | ✅ 200 |
| G8-ENG-001 | ✅ 200 |
| G8-TECH-001 | ✅ 200 |

> **Note:** These are demo/placeholder subscriptions (not real Stripe-billed plans).
> They exist purely to unlock the demo experience.

---

## 3. How to proceed with testing

Please re-run the original scenario to confirm on your side:

1. **Log in as a student** at `demo.usestudybuddy.com`
   - e.g. `callmds@gmail.com` (MilfordWaterford, Grade 8) or
     `kt.shanvenki@gmail.com` (ABC School)
   - Password: `StudyBuddyDemo2026!`
2. **Select a subject** → pick any unit.
3. **Open the Lesson** → it should now load (no "not available" / paywall message).
4. **Open the Quiz and Tutorial** for the same unit → confirm both load.
5. Repeat across a few subjects (Math / Science / Engineering / Technology) and a
   couple of different units to spot-check breadth.
6. Confirm the **School Admin** view still shows the same content (unchanged).

### What "working" looks like
- Lessons, quizzes, and tutorials all open for the student with no error banner.
- No "This isn't available yet" or "upgrade" message on lessons.

### If something still fails
Please capture and send:
- The exact account (email) and the **unit** + **content type** (lesson/quiz/etc.)
- A screenshot of the message
- Roughly when you tried it (so we can match server logs)

---

## 4. Separate follow-up (tracked, not blocking the demo)

There is a **secondary UI bug**, independent of the fix above, now filed as:

**GitHub issue #504** — *"Student UI shows generic error (not a paywall) on HTTP 402
for capped free-tier lessons."*

The point: when a free-tier student *does* hit the lesson cap, the app currently
shows a confusing generic error instead of a clear "you've reached your free lesson
limit — upgrade" message. The demo is unblocked by the subscription fix above; this
ticket tracks making the paywall message clear for any real free-tier student later.

---

## 5. Quick reference (for the team)

- **Free-tier lesson cap:** `backend/src/content/router.py` → `_FREE_TIER_LESSON_LIMIT = 2`
- **Gate logic:** `backend/src/content/service.py` → `get_entitlement()` / `_get_school_sub()`
  (active school subscription ⇒ student leaves free tier ⇒ cap bypassed)
- **To unlock a school's students:** ensure a `school_subscriptions` row with
  `status='active'` and a non-free `plan` exists for that `school_id`
  (invalidate `school:{school_id}:ent*` Redis keys after changing it).
