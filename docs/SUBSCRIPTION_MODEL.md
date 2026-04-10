# StudyBuddy OnDemand — Subscription & Pricing Model

> **Single source of truth for pricing:** `backend/src/pricing.py` and `web/lib/pricing.ts`
> To change any price, edit those two files only. No other code needs to change.

---

## 1. Who Pays for What

StudyBuddy has three types of paying customers:

| Customer | What they buy | How they pay |
|---|---|---|
| **School** | A plan that covers all enrolled students and teachers | Monthly Stripe subscription |
| **School** (add-on) | Extra storage or extra curriculum builds | One-time Stripe payment |
| **Independent Teacher** | Access for their own student group | Monthly flat fee *(future — #57)* |

Students themselves never pay — access is granted by the school or teacher they belong to.

---

## 2. School Subscription Plans

One subscription per school covers every enrolled student and teacher.

| | Starter | Professional | Enterprise |
|---|---|---|---|
| **Monthly price** | $49 / month | $149 / month | Custom (sales) |
| **Students** | Up to 30 | Up to 150 | Unlimited |
| **Teachers** | Up to 3 | Up to 10 | Unlimited |
| **Curriculum builds / year** | 1 | 3 | Unlimited |
| **Storage included** | 5 GB | 5 GB | Negotiated |
| **Languages** | English | EN + FR + ES | All |
| **Custom curriculum upload** | — | ✓ | ✓ |
| **Teacher reporting dashboard** | — | ✓ | ✓ |
| **Dedicated support / SLA** | — | — | ✓ |

### What is a "curriculum build"?

A curriculum build is one full grade-level content generation run — the pipeline
calls Claude to produce lessons, quizzes, tutorials, and experiments for every unit
in a grade. It is the most compute-intensive operation on the platform.

- A **Starter** school gets 1 build per subscription year — enough to set up once.
- A **Professional** school gets 3 — allowing annual refresh or a mid-year revision.
- **Enterprise** schools have no limit.

The annual allowance resets on the subscription anniversary date. Schools that exhaust
their allowance can purchase additional builds at $15 per grade *(future — Q3-B #106)*.

---

## 3. Storage Add-On Packages

Every plan includes 5 GB of base storage for generated curriculum content.
Schools that need more can purchase additional storage as a one-time payment.
Purchased storage accumulates (never expires) and does not reset on plan renewal.

| Package | Additional storage | One-time price |
|---|---|---|
| Small | +5 GB | $19 |
| Medium | +10 GB | $35 |
| Large | +25 GB | $79 |

Storage is consumed by completed pipeline jobs (`payload_bytes` on `pipeline_jobs`).
Usage is tracked in `school_storage_quotas.used_bytes`, updated nightly by a
reconciliation task and atomically on each job completion.

---

## 4. AI Generation Cost (Platform Cost, Not Billed to Schools)

This section is **internal** — it describes what the platform pays Anthropic to
generate curriculum content. It is not charged directly to schools; it is absorbed
into subscription pricing.

### Token rates (Claude Sonnet 4.6)

| Token type | Rate |
|---|---|
| Input | $3.00 per 1 million tokens |
| Output | $15.00 per 1 million tokens |

### Per-grade cost estimate

| Scope | Estimated cost |
|---|---|
| 1 grade · English only | ~$1.60 |
| 1 grade · EN + FR + ES | ~$4.80 |
| Full K–12 (Grades 5–12, English) | ~$12.80 |
| Full K–12 (Grades 5–12, 3 languages) | ~$38.40 |

*Based on 30 units/grade, ~1,800 input and ~3,200 output tokens/unit.*
*Actual costs vary by grade level and subject density.*

### Margin analysis

| Plan | Annual revenue | Max build cost (1 EN grade) | AI cost as % of revenue |
|---|---|---|---|
| Starter (1 build/yr) | $588 | ~$1.60 | < 0.3 % |
| Professional (3 builds/yr) | $1,788 | ~$4.80 | < 0.3 % |
| Enterprise | Negotiated | Unlimited | Managed per contract |

AI generation cost is not the margin risk — storage, infrastructure, and Stripe fees are larger line items.

### Safety cap

The pipeline aborts if cumulative token cost for a single run exceeds **$50**.
This prevents runaway jobs from a malformed curriculum JSON. Configured in
`pipeline/config.py` via `MAX_PIPELINE_COST_USD`.

---

## 5. Independent Teacher Plans *(future — #57)*

When the teacher tier is rebuilt, independent teachers (not affiliated with a school)
will pay a flat monthly fee and keep 100 % of their student revenue (Option A).

| Tier | Students | Monthly fee |
|---|---|---|
| Solo | Up to 25 | $29 / month |
| Growth | Up to 75 | $59 / month |
| Pro | Up to 200 | $99 / month |

Alternative billing models are tracked as future issues:
- **Q2-B #104** — Revenue share (Stripe Connect, platform takes ~20 %)
- **Q2-C #105** — Seat-tiered flat fee (same tiers, different enforcement)

---

## 6. Billing Flow (Stripe)

```
School admin clicks "Upgrade" on the subscription page
  → POST /schools/{id}/subscription/checkout
  → Backend creates a Stripe Checkout Session (mode=subscription)
  → Admin is redirected to Stripe-hosted payment page

Payment succeeds
  → Stripe fires checkout.session.completed webhook
  → Backend verifies signature (stripe.Webhook.construct_event)
  → activate_school_subscription() is called:
      · Upserts school_subscriptions (plan, status=active, seat caps)
      · Stamps build allowance on school_storage_quotas
      · Bulk-upserts student_entitlements for all enrolled students
      · Invalidates school entitlement cache in Redis
  → All enrolled students gain plan access immediately

School admin cancels
  → DELETE /schools/{id}/subscription
  → Backend calls Stripe cancel_at_period_end=True
  → Status becomes cancelled_at_period_end
  → Students retain access until the period end date

Stripe fires customer.subscription.deleted
  → Backend sets status=cancelled
  → All enrolled students reverted to free tier

Payment fails
  → Backend sets status=past_due, sets grace_period_end = NOW() + 3 days
  → Students retain access during the grace period
  → If payment is not recovered, subscription is cancelled
```

---

## 7. Entitlement Model

The entitlement system answers: *"is this student allowed to access this content?"*

```
Student JWT arrives at a content endpoint
  │
  ├─ Student enrolled in a school?
  │     Yes → check school_subscriptions (cached at school:{id}:ent, TTL=300s)
  │           → plan determines which grades and languages are available
  │
  └─ No school → check student_entitlements (individual subscription)
                  → legacy path; individual subscriptions were removed in migration 0027
```

School entitlement cache is explicitly invalidated (not TTL-expired) on:
- Subscription activation / renewal
- Cancellation
- Payment failure / recovery
- Student enrolment or removal

---

## 8. Seat Limit Enforcement

Seat limits are enforced at the write path (enrolment upload and teacher invite),
not at content access time.

| Action | Limit checked | HTTP response on breach |
|---|---|---|
| Enrol students (bulk upload) | `max_students` vs current active count | 402 `seat_limit_reached` |
| Invite teacher | `max_teachers` vs current active count | 402 `seat_limit_reached` |

Seat counts come from live DB queries:
- Students: `COUNT(*) FROM school_enrolments WHERE status = 'active'`
- Teachers: `COUNT(*) FROM teachers WHERE account_status = 'active'`

---

## 9. Key Tables

| Table | Purpose |
|---|---|
| `school_subscriptions` | One row per school. Plan, status, Stripe IDs, seat caps, period dates. |
| `school_storage_quotas` | Storage usage + build allowance per school. |
| `student_entitlements` | Per-student plan snapshot. Bulk-updated on school subscription events. |
| `stripe_events` | Deduplication log. Every processed `stripe_event_id` is recorded here. |

---

## 10. Where to Change Prices

All pricing constants live in two files. Edit both together.

| File | Language | Edit when |
|---|---|---|
| `backend/src/pricing.py` | Python | Changing plan prices, seat limits, build allowances, storage package prices, AI cost rates, teacher plan prices |
| `web/lib/pricing.ts` | TypeScript | Same changes — mirrors the Python file for the frontend |

Stripe price IDs (`STRIPE_SCHOOL_PRICE_*_ID`) are **not** in these files — they are
environment-specific Stripe configuration set in `.env`. Changing business pricing
requires creating a new Stripe price in the dashboard and updating the `.env` value.
