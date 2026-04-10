# StudyBuddy OnDemand — Subscription & Pricing Model

> **Single source of truth for pricing:** `backend/src/pricing.py` and `web/lib/pricing.ts`
> To change any price, edit those two files only. No other code needs to change.

---

## 1. Who Pays for What

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Money flows                                   │
│                                                                      │
│  ┌──────────┐  monthly sub   ┌─────────────┐                        │
│  │  School  │ ─────────────► │  StudyBuddy │                        │
│  │  Admin   │  one-time      │  Platform   │                        │
│  │          │ ─────────────► │             │                        │
│  └──────────┘ (storage/      └─────────────┘                        │
│               extra builds)        │                                 │
│                                    │ covers access for               │
│                                    ▼                                 │
│               ┌────────────────────────────────┐                    │
│               │   All enrolled students         │  ← never pay      │
│               │   All school teachers           │  ← never pay      │
│               └────────────────────────────────┘                    │
│                                                                      │
│  ┌─────────────────┐  monthly flat fee  ┌─────────────┐            │
│  │ Indep. Teacher  │ ──────────────────► │  Platform   │  (future)  │
│  │                 │  keeps all student  │             │            │
│  └─────────────────┘  revenue           └─────────────┘            │
└─────────────────────────────────────────────────────────────────────┘
```

Students themselves never pay — access is granted by the school or teacher they belong to.

---

## 2. School Subscription Plans

One subscription per school covers every enrolled student and teacher.

```
                    ┌────────────┬────────────────┬─────────────────┐
                    │  STARTER   │  PROFESSIONAL  │   ENTERPRISE    │
                    ├────────────┼────────────────┼─────────────────┤
  Monthly price     │  $49/mo    │   $149/mo      │   Custom        │
  ─────────────────────────────────────────────────────────────────
  Students          │  up to 30  │   up to 150    │   Unlimited     │
  Teachers          │  up to 3   │   up to 10     │   Unlimited     │
  ─────────────────────────────────────────────────────────────────
  Builds / year     │     1      │       3        │   Unlimited     │
  Storage           │    5 GB    │      5 GB      │   Negotiated    │
  ─────────────────────────────────────────────────────────────────
  Languages         │     EN     │  EN, FR, ES    │   All           │
  Custom curriculum │     —      │       ✓        │   ✓             │
  Teacher reports   │     —      │       ✓        │   ✓             │
  Dedicated support │     —      │       —        │   ✓             │
                    └────────────┴────────────────┴─────────────────┘
```

### What is a "curriculum build"?

```
  One curriculum build = one full grade-level AI content generation run

  ┌─────────────────────────────────────────────────────────────────┐
  │  Grade 8  (30 units)                                            │
  │                                                                 │
  │  Unit 1 → Lesson + Quiz + Tutorial + Experiment  (EN)          │
  │  Unit 2 → Lesson + Quiz + Tutorial + Experiment  (EN)          │
  │  ...                                                            │
  │  Unit 30 → Lesson + Quiz + Tutorial + Experiment (EN)          │
  │                                                                 │
  │  = 1 build consumed from annual allowance                       │
  └─────────────────────────────────────────────────────────────────┘

  Allowance resets every subscription anniversary.

  Starter  ──── [■□□] 1 build / year  (set up once)
  Pro      ──── [■■■] 3 builds / year (annual refresh + 2 revisions)
  Enterprise ── [∞]   Unlimited
```

Schools that exhaust their allowance can purchase extra builds at $15/grade *(future — Q3-B #106)*.

---

## 3. Storage Add-On Packages

```
  Every plan:  5 GB base (included, resets on plan change? No — stays)
               │
               ▼
  ┌────────────────────────────────────────────────────────────────┐
  │  school_storage_quotas                                         │
  │                                                                │
  │  base_gb = 5        ← always included                         │
  │  purchased_gb = 0   ← accumulates with add-on purchases       │
  │  used_bytes = …     ← updated after each pipeline build       │
  │                                                                │
  │  total = base_gb + purchased_gb                               │
  └────────────────────────────────────────────────────────────────┘

  Add-on packages (one-time, never expire):

  ┌──────────────┬────────────┬────────────┐
  │   +5 GB      │   +10 GB   │   +25 GB   │
  │   $19        │    $35     │    $79     │
  │  ($3.80/GB)  │  ($3.50/GB)│  ($3.16/GB)│
  └──────────────┴────────────┴────────────┘
                  ↑ bulk discount
```

---

## 4. AI Generation Cost (Platform Cost — Not Billed to Schools)

This is **internal margin data** — what the platform pays Anthropic per build.

```
  Claude Sonnet 4.6 token rates
  ┌──────────────────────────────────────────────────────────────┐
  │  Input tokens  →  $3.00 per 1 million tokens                 │
  │  Output tokens →  $15.00 per 1 million tokens                │
  └──────────────────────────────────────────────────────────────┘

  Per curriculum unit (avg):
  ┌──────────────────────────────────────────────────────────────┐
  │  ~1,800 input tokens   →  $0.0054                           │
  │  ~3,200 output tokens  →  $0.0480                           │
  │  ─────────────────────────────────────                       │
  │  cost per unit         →  ~$0.053                           │
  │  × 30 units / grade    →  ~$1.60 per grade (English)        │
  │  × 3 languages         →  ~$4.80 per grade (EN+FR+ES)       │
  └──────────────────────────────────────────────────────────────┘

  Full K–12 build cost estimate (Grades 5–12 = 8 grades):
  ┌──────────────────────────────────────────────────────────────┐
  │  English only   8 × $1.60 = ~$12.80                         │
  │  3 languages    8 × $4.80 = ~$38.40                         │
  └──────────────────────────────────────────────────────────────┘
```

### Margin at a glance

```
  ┌─────────────────┬─────────────┬──────────────┬────────────────┐
  │  Plan           │ Annual rev  │ Max AI cost  │ AI as % of rev │
  ├─────────────────┼─────────────┼──────────────┼────────────────┤
  │ Starter  (1/yr) │    $588     │    ~$1.60    │    < 0.3 %     │
  │ Pro      (3/yr) │  $1,788     │    ~$4.80    │    < 0.3 %     │
  │ Enterprise      │  Negotiated │  Unlimited   │  Per contract  │
  └─────────────────┴─────────────┴──────────────┴────────────────┘
  ↑ AI generation cost is not the margin risk.
    Infrastructure, storage egress, and Stripe fees are larger.

  Safety cap: pipeline aborts if a single run exceeds $50
  (prevents runaway jobs from malformed curriculum JSON)
```

---

## 5. Independent Teacher Plans *(future — #57)*

```
  ┌───────────────────────────────────────────────────────────┐
  │  Option A  (shipped as config — awaiting teacher tier)    │
  │                                                           │
  │  Teacher pays flat monthly fee → keeps 100% of student    │
  │  revenue                                                  │
  │                                                           │
  │  ┌─────────┬────────────┬─────────┐                      │
  │  │  Solo   │  Growth    │   Pro   │                      │
  │  │ ≤25 stu │  ≤75 stu   │ ≤200 stu│                      │
  │  │ $29/mo  │  $59/mo    │ $99/mo  │                      │
  │  └─────────┴────────────┴─────────┘                      │
  │                                                           │
  │  Future alternatives:                                     │
  │  • Q2-B #104 — Revenue share via Stripe Connect (~20%)   │
  │  • Q2-C #105 — Same tiers, seat-based enforcement        │
  └───────────────────────────────────────────────────────────┘
```

---

## 6. Billing Flow (Stripe)

```
  UPGRADE FLOW
  ────────────
  School admin                  Backend                     Stripe
       │                           │                           │
       │  POST /subscription/      │                           │
       │  checkout                 │                           │
       │──────────────────────────►│                           │
       │                           │  Create Checkout Session  │
       │                           │──────────────────────────►│
       │                           │  ◄── checkout_url         │
       │  ◄── redirect to Stripe   │                           │
       │                           │                           │
       │     [pays on Stripe]      │                           │
       │                           │                           │
       │                           │  ◄─ checkout.session.     │
       │                           │     completed (webhook)   │
       │                           │                           │
       │                           │  verify signature         │
       │                           │  activate_school_sub()    │
       │                           │   ├─ upsert subscription  │
       │                           │   ├─ stamp build quota    │
       │                           │   ├─ update entitlements  │
       │                           │   └─ invalidate Redis     │
       │                           │                           │
       │  [students gain access]   │                           │


  CANCELLATION FLOW
  ─────────────────
  Admin clicks Cancel
       │
       │  DELETE /subscription → cancel_at_period_end = true (Stripe)
       │  status → "cancelled_at_period_end"
       │  Students retain access until period end
       │
  Period ends
       │
       ▼  customer.subscription.deleted webhook
       │  status → "cancelled"
       └► All enrolled students reverted to free tier


  PAYMENT FAILURE FLOW
  ────────────────────
  Invoice fails
       │
       ▼  invoice.payment_failed webhook
       │  status → "past_due"
       │  grace_period_end = NOW() + 3 days
       │  Students retain access during grace period
       │
  Grace period expires without payment
       ▼
       └► Subscription cancelled → students lose access
```

---

## 7. Entitlement Model

*"Is this student allowed to access this content?"*

```
  Student JWT hits a content endpoint
          │
          ▼
  ┌───────────────────────────────────────────────────────────┐
  │  Is student enrolled in a school?                         │
  └──────────────────────────┬───────────────────────────────┘
                             │
          ┌──── YES ─────────┴──────── NO ────┐
          │                                    │
          ▼                                    ▼
  Check school plan                   Check student_entitlements
  (cached in Redis,                   (legacy individual sub path —
   TTL = 300s)                         removed in migration 0027)
          │
          ▼
  ┌───────────────────────────────────────┐
  │  school_subscriptions                 │
  │  plan = "professional"                │
  │  status = "active"                    │──► grant access
  │  max_students = 150                   │
  │  current_period_end = 2027-03-01      │
  └───────────────────────────────────────┘

  Cache invalidated (not TTL-expired) on:
  ┌────────────────────────────────────┐
  │  • Subscription activation         │
  │  • Cancellation                    │
  │  • Payment failure / recovery      │
  │  • Student enrolment / removal     │
  └────────────────────────────────────┘
```

---

## 8. Seat Limit Enforcement

```
  Limits are checked at write time — not at content access time.

  ┌──────────────────────────────────────────────────────────────┐
  │  POST /schools/{id}/enrolment  (bulk student upload)         │
  │                                                              │
  │  incoming students + current active count > max_students?    │
  │                                                              │
  │  YES ──► 402  { "error": "seat_limit_reached",              │
  │                 "limit": 30,                                 │
  │                 "used": 28,                                  │
  │                 "requested": 5 }                             │
  │                                                              │
  │  NO  ──► 201  enrolment proceeds                            │
  └──────────────────────────────────────────────────────────────┘

  ┌──────────────────────────────────────────────────────────────┐
  │  POST /schools/{id}/teachers/invite                          │
  │                                                              │
  │  current active teachers ≥ max_teachers?                     │
  │                                                              │
  │  YES ──► 402  { "error": "seat_limit_reached" }             │
  │  NO  ──► 201  invite sent                                   │
  └──────────────────────────────────────────────────────────────┘

  UI warning thresholds (LimitWarningBanner):
  ────────────────────────────────────────────
  ≥ 80% used  →  amber banner  "approaching limit"
  = 100% used →  red banner    "limit reached — action blocked"
```

---

## 9. Key Database Tables

```
  ┌──────────────────────────────────────────────────────────────────┐
  │                    school_subscriptions                           │
  │  school_id │ plan │ status │ stripe_sub_id │ max_students │ ...  │
  │  (one row per school — the billing source of truth)              │
  └──────────────────────────────────────┬───────────────────────────┘
                                         │ on change →
                                         ▼ bulk upsert
  ┌──────────────────────────────────────────────────────────────────┐
  │                    student_entitlements                           │
  │  student_id │ plan │ valid_until                                  │
  │  (per-student snapshot — drives content access checks)           │
  └──────────────────────────────────────────────────────────────────┘

  ┌──────────────────────────────────────────────────────────────────┐
  │                    school_storage_quotas                          │
  │  school_id │ base_gb │ purchased_gb │ used_bytes                  │
  │            │ builds_included │ builds_used │ builds_period_end    │
  │  (storage metering + annual build allowance — one row per school)│
  └──────────────────────────────────────────────────────────────────┘

  ┌──────────────────────────────────────────────────────────────────┐
  │                       stripe_events                               │
  │  stripe_event_id │ event_type │ outcome                          │
  │  (deduplication log — prevents double-processing webhooks)       │
  └──────────────────────────────────────────────────────────────────┘
```

---

## 10. Where to Change Prices

```
  ┌─────────────────────────────────────────────────────────────────┐
  │                                                                   │
  │   To change ANY price or limit:                                   │
  │                                                                   │
  │   1. Edit  backend/src/pricing.py   (Python — backend + pipeline) │
  │   2. Edit  web/lib/pricing.ts       (TypeScript — frontend UI)    │
  │                                                                   │
  │   Nothing else needs to change.                                   │
  │                                                                   │
  │   ┌──────────────────┐        ┌──────────────────────────────┐   │
  │   │  pricing.py      │        │  pricing.ts                  │   │
  │   │                  │        │                              │   │
  │   │  SCHOOL_PLANS    │  ────► │  SCHOOL_PLANS_LIST           │   │
  │   │  STORAGE_PACKAGES│  ────► │  STORAGE_PACKAGES            │   │
  │   │  AI_COST         │        │  AI_COST_MODEL               │   │
  │   │  TEACHER_PLANS   │  ────► │  TEACHER_PLANS               │   │
  │   └──────────────────┘        └──────────────────────────────┘   │
  │           │                              │                        │
  │           ▼                              ▼                        │
  │   subscription_service.py       subscription/page.tsx            │
  │   storage_router.py             storage/page.tsx                 │
  │   pipeline/config.py            LimitWarningBanner               │
  │                                                                   │
  └─────────────────────────────────────────────────────────────────┘

  Stripe price IDs (STRIPE_SCHOOL_PRICE_*_ID) live in .env only —
  they are environment-specific and are NOT in the pricing files.
```
