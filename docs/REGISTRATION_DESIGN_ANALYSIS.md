# Registration & Onboarding — Design Analysis

> Produced from `REGISTRATION_DESIGN_QA.md` answers (2026-04-11).
> Updated to incorporate inline decisions and lock in terminology (2026-04-11).
> This document maps the design decisions to architectural changes,
> identifies what is new, what changes, what stays the same,
> and flags the open questions that must be resolved before build begins.

---

## 0. Terminology (locked — use these terms throughout)

| Term | Definition |
|---|---|
| **Curriculum Definition** | The structured spec a teacher builds via the form UI: grade, subject names, unit titles, languages. This is the INPUT to the pipeline. No content exists yet at this stage. |
| **Curriculum Package** | The OUTPUT of a pipeline run against an approved Definition. Contains lessons, quizzes, tutorials, and audio stored in the content store. This is what gets assigned to a Classroom. |
| **Platform Catalog** | A set of pre-built Curriculum Packages provided by the platform operator (e.g. Grade 5–12 STEM defaults). Selecting from the catalog skips the Definition + pipeline stage entirely. |
| **Classroom** | The binding between a group of students and one or more Curriculum Packages. Created by a school admin or teacher. |

---

## 1. Summary of Decisions

| # | Decision |
|---|---|
| Q1 | First person to register a school is automatically `school_admin` |
| Q2 | Teacher email must be unique; two roles = two email addresses |
| Q3 | No account absorption; once registered, accounts are independent |
| Q4 | School adds students by email → system sends default password → student forced to reset on first login. School admin can reset passwords |
| Q5 | Same provisioning model for teachers as students (default password, forced reset) |
| Q6 | **No self-registration for teachers or students.** School is the sole provisioner. School assigns each student to exactly one grade program |
| Q7 | Curriculum builder = **form-based UI** (subject / unit / title fields; app constructs the JSON) |
| Q8 | Curriculum selection = **pick from platform catalog** (Grade 5–12 STEM defaults; more combinations later) |
| Q9 | Custom Curriculum Definitions require **school admin approval** before pipeline runs. Teacher submits → school admin approves. Platform admin is escalation-only. Multiple people can hold `school_admin` per school |
| Q10 | **Two-tier billing**: SaaS subscription (access) + pay-per-pipeline-run (separate charge) |
| Q11 | Billing card captured at subscription time and **reused for pipeline runs** |
| Q12 | **Cost estimate shown** before pipeline confirmed. Uses **live Anthropic token pricing** |
| Q13 | Content accessed via **existing web portal + mobile app** |
| Q14 | School/teacher pulls a Curriculum Package into a **Classroom** and assigns students to it |
| Q15 | School self-registration is **public and self-service** on both web and mobile. Platform admin is escalation path only |
| Q16 | Classroom scope is **school's choice** — they name it and pick which Curriculum Packages go in it |
| Q17 | A student is assigned to **one classroom at a time**. Temporal reassignment (moving later) is valid |
| Q18 | Curriculum Definition approval is **school admin only**. Platform admin is escalation-only. Multiple people can be `school_admin` per school |
| Q19 | **Auth0 is kept as a parallel login path** for existing self-registered students. New school-provisioned users use email/password (local bcrypt) |
| Q20 | **Independent teachers and students register as a school/institution** (same public form). The registrant becomes `school_admin` of their own micro-school and follows the same path |
| Q21 | Pipeline cost estimate uses **live Anthropic token pricing** (API call before showing the confirmation modal) |
| Q22 | Classroom shows a **merged view** of all Curriculum Packages assigned to it. If the same unit appears in two packages, **both versions are kept and shown** — no deduplication. School/teacher can add, remove, and reorder packages via CRUD |

---

## 2. The Classroom Concept (New Entity)

```
┌──────────────────────────────────────────────────────────────────┐
│                       CLASSROOM                                  │
│                                                                  │
│  A Classroom is the binding between:                             │
│    • One or more Curriculum Packages                             │
│    • A set of students                                           │
│    • (Optionally) a teacher responsible for it                   │
│                                                                  │
│  Created by: school_admin or teacher                             │
│  Packages assigned: from catalog or custom-built (many-to-many)  │
│  Students: one classroom at a time; temporal reassignment OK     │
│  Student view: merged across all assigned packages               │
│  Duplicate unit_id across packages: both versions shown          │
└──────────────────────────────────────────────────────────────────┘
```

### Classroom data model

```
classrooms
  classroom_id   UUID         PK
  school_id      UUID         FK → schools
  teacher_id     UUID         FK → teachers (nullable)
  name           TEXT         e.g. "Grade 8 — Section A"
  grade          INT
  status         TEXT         'active' | 'archived'
  created_at     TIMESTAMPTZ

classroom_packages                              ← binds packages to classrooms
  classroom_id   UUID         FK → classrooms
  curriculum_id  UUID         FK → curricula    (a Curriculum Package)
  assigned_at    TIMESTAMPTZ
  assigned_by    UUID         FK → teachers or admin_users
  sort_order     INT          teacher controls display order
  PRIMARY KEY (classroom_id, curriculum_id)

classroom_students
  classroom_id   UUID         FK → classrooms
  student_id     UUID         FK → students
  joined_at      TIMESTAMPTZ
  PRIMARY KEY (classroom_id, student_id)
```

**Why many-to-many packages?** A teacher generates content for "Quadratic Equations" one
week and "Polynomial Functions" the next — each as a separate pipeline run (Curriculum Package).
Both should appear in the same classroom without creating a new classroom each time.

**Duplicate unit handling:** If Package A and Package B both contain `G8-MATH-001`, the
student sees two entries for that unit — one from each package. The display distinguishes
them by package name and assignment date. No merging or replacement logic is required.

---

## 3. Two-Stage Curriculum Lifecycle

```
  Stage 1 — DEFINITION  (no content yet)
  ───────────────────────────────────────
  Teacher fills form:
    ┌────────────────────────────────────┐
    │  Curriculum name + grade           │
    │  Subjects (open naming — any label)│
    │    └─ Units per subject            │
    │  Languages                         │
    └────────────────────────────────────┘
    → JSON Definition produced
    → Submitted for school admin approval
    → Status: pending_approval

  School admin approves
    → Status: approved
    → Teacher notified: "Ready to generate"

  Stage 2 — PACKAGE  (content exists)
  ────────────────────────────────────
  School admin confirms cost estimate (live Anthropic pricing)
  → Stripe charge created (pay-per-run)
  → Pipeline triggered → returns job_id
  → Status: generating → completed

  Completed Package assigned to Classroom
  → Student sees merged content view
```

**Platform catalog packages** enter at Stage 2 directly — the platform operator
has already run the pipeline. Schools select and assign without any Definition or
approval step.

---

## 4. Authentication Model Change

### Current model

```
Students  → Auth0 PKCE browser flow → backend token exchange
Teachers  → Auth0 PKCE browser flow → backend token exchange
Admins    → local bcrypt (email + password)
```

### New model

```
Schools       → self-register (web or mobile) → school_admin account (local bcrypt)
Teachers      → added by school_admin → local bcrypt (default pw → forced reset)
Students      → added by school_admin → local bcrypt (default pw → forced reset)
Platform admins → unchanged (local bcrypt)
Auth0         → KEPT as parallel login path for legacy self-registered students
```

### Provisioning sequence (school-managed users)

```
School admin adds teacher/student by email
        │
        ▼
System generates a random default password
        │
        ▼
Email sent: "Welcome to StudyBuddy — your login is ready"
  Body: email + default password + login URL
        │
        ▼
User logs in with default password
        │
        ▼
System detects first_login = true → redirect to password reset page
        │
        ▼
User sets their own password → first_login = false → normal login
```

### School admin: password reset

```
School admin portal → Manage Users → select user → "Reset Password"
→ System generates new default password → email sent
→ User forced to reset on next login
```

### Multiple school admins

Each school can have more than one `school_admin`. The role is assignable to N people;
the original registrant is assigned it automatically. An existing `school_admin` can
promote other teachers to the role.

---

## 5. Registration Flows

### 5a. School self-registration (web or mobile)

```
Step 1 — School details
  School name · Country
  Contact email (becomes school_admin email)
  Password (set directly — no default password for the founder)

Step 2 — Billing information
  Card details via Stripe Elements · Plan selection

Step 3 — Confirmation
  School created → school_admin account created
  Welcome email sent → redirect to school admin portal
```

### 5b. School adds a teacher

```
School admin portal → Teachers → "Add Teacher"
  Name · Email · Subject specialisation (optional)
→ Local bcrypt account created with default password → welcome email
→ Teacher logs in → forced password reset
```

### 5c. School adds a student

```
School admin portal → Students → "Add Student"
  Name · Email · Grade (1–12)
→ Local bcrypt account created with default password → welcome email
→ Student logs in → forced password reset
→ School admin assigns student to a Classroom
```

### 5d. Independent teacher or student (Q20)

```
An "independent" individual registers as a school using the same public form.

  Independent teacher → registers school → becomes school_admin
                      → adds themselves as a teacher within that school
                      → adds their students · builds their own curriculum

  Independent student → registers school → becomes school_admin
                      → adds themselves as a student

No separate "independent" account type. The school model handles all cases.
```

### 5e. No self-registration for teachers/students (confirmed)

```
/register is for schools only (including individuals using the school path).
There is no public signup for teachers or students.
Teachers and students exist only if a school_admin creates them.
```

---

## 6. Curriculum Flows

### 6a. Use platform catalog

```
School admin / Teacher → Classrooms → "Set Curriculum"
  → Browse platform catalog:

  ┌─────────────────────────────────────────────────┐
  │  Platform Curriculum Catalog                    │
  │  (pre-built Packages — no pipeline run needed)  │
  │                                                 │
  │  Grade 5 — STEM  (Math · Science · Tech · Eng) │
  │  Grade 6 — STEM  …  Grade 12 — STEM            │
  │  [More subject combinations coming]             │
  └─────────────────────────────────────────────────┘

  Note: "STEM" is the US default label. Subject naming and
  grouping are open — not constrained to any regional naming.

  → Select Package → Assign to Classroom → content immediately available
```

### 6b. Build custom Curriculum Definition (form-based UI)

```
School admin / Teacher → Classrooms → "Build Custom Curriculum"

  Step 1 — Name + grade
  Step 2 — Add subjects (open naming) + units per subject
  Step 3 — Select languages
  Step 4 — Submit for school admin approval

→ Status: pending_approval
→ School admin reviews and approves or rejects
→ On approval: school admin triggers pipeline (with cost estimate)
→ On completion: Package available → assign to Classroom
```

### 6c. Cost estimate (live token pricing)

```
School admin → Curriculum → "Generate Content"

  ┌─────────────────────────────────────────────────────┐
  │  Content Generation Estimate                        │
  │                                                     │
  │  Subjects: 2  Units: 8  Languages: 2 (en, fr)       │
  │  Estimated cost: $12.00  (live Anthropic pricing)   │
  │  Charged to card ending ••••4242                    │
  │                                                     │
  │  [Cancel]           [Confirm & Generate]            │
  └─────────────────────────────────────────────────────┘

→ On Confirm: Stripe charge → pipeline job → progress dashboard
→ On completion: Package added to curricula table → assign to Classroom
```

### 6d. Adding more content to an existing Classroom (Q22)

```
Teacher decides students need more lessons mid-course:

  Option A — Add from catalog:
    Classroom → "Add Curriculum" → pick another catalog Package
    → immediately visible in merged view

  Option B — Build new Definition:
    Teacher builds new Definition (e.g. "Advanced Polynomial Functions")
    → approval → pipeline → new Package
    → assign to same Classroom
    → merged with existing content
    → if unit_id overlaps: both versions shown, distinguished by package + date

  CRUD on classroom packages:
    Teacher / school admin can remove a Package from a Classroom
    Teacher / school admin can reorder Packages (sort_order)
```

---

## 7. What Changes vs. What Stays the Same

### Changes

| Area | Current | New |
|---|---|---|
| Student auth | Auth0 PKCE only | Local bcrypt (school-provisioned) + Auth0 as parallel path |
| Teacher auth | Auth0 PKCE only | Local bcrypt (school-provisioned) + Auth0 as parallel path |
| Student registration | Self-register via Auth0 | School admin creates account; Auth0 path kept for legacy |
| Teacher registration | Self-register via Auth0 | School admin creates account; independent users use school path |
| Curriculum assignment | Curriculum linked to school directly | Curriculum Packages assigned to Classrooms (many-to-many) |
| Student-curriculum routing | Via `school_enrolments` → `school_subscriptions` | Via `classroom_students` → `classroom_packages` → `curricula` |
| Pipeline trigger | Admin-only | School admin (post-approval, post-billing-confirmation) |
| Pipeline billing | Included in subscription | Separate pay-per-run charge (live token pricing estimate) |
| Curriculum approval | Platform admin | School admin (platform admin is escalation only) |
| Independent teacher | Separate account type | Registers as a school; becomes school_admin of micro-school |

### Stays the same

| Area | Status |
|---|---|
| School self-registration (`/register`) | Same endpoint; extend to mobile |
| Platform admin panel | Same; gains support/escalation queue for curriculum |
| Content delivery (lesson / quiz / tutorial / audio) | Unchanged |
| Web portal + mobile app for content access | Unchanged |
| Stripe subscription (SaaS access fee) | Unchanged |
| Progress tracking · Analytics · RLS | Unchanged |

---

## 8. Email Uniqueness Model

Every person — school admin, teacher, student, platform admin — must have a globally
unique email address. Email is the primary identifier.

```
Two roles at the same institution require two separate email addresses.
An independent individual who is also school_admin uses one email for both
(they are the same person acting in both capacities).
```

---

## 9. Impact on Mobile App

### Dual auth path (Q19)

```
Legacy:   mobile login → Auth0 PKCE → /auth/exchange → JWT
New:      mobile login → email + password → /auth/login → JWT

LoginScreen must support both paths.
Mobile also needs a public school registration screen (Q15).
```

Password reset (new path):
```
"Forgot password?" → enter email → POST /auth/forgot-password
→ reset link emailed → user clicks link → web page → resets
→ returns to mobile login
```

---

## 10. Open Questions

All questions Q1–Q22 are now answered. No blockers remain before Phase A begins.

---

## 11. Proposed Build Order

```
Phase A — Auth & Provisioning
  1.  first_login flag + forced password reset flow (backend)
  2.  School admin: add teacher endpoint (default pw + email)
  3.  School admin: add student endpoint (default pw + email)
  4.  School admin: reset password endpoint
  5.  POST /auth/login (email+pw); keep POST /auth/exchange (Auth0) as parallel path
  6.  Multiple school_admin support per school
  7.  Mobile: email/password login form alongside Auth0 path
  8.  Mobile: public school registration screen

Phase B — Classroom
  9.  DB migration: classrooms + classroom_packages + classroom_students
  10. Classroom CRUD endpoints (school admin portal)
  11. Assign/remove student to classroom
  12. Assign/remove/reorder Curriculum Package in classroom (classroom_packages)
  13. Curriculum resolver: routes via classroom_students → classroom_packages → curricula
  14. Student app: merged content view across all packages in classroom
      (duplicate unit_id → show both, label by package + date)

Phase C — Curriculum Catalog
  15. GET /curricula/catalog — list pre-built platform Packages
  16. POST /classrooms/{id}/packages — assign catalog Package to Classroom
  17. School admin portal: catalog browser UI

Phase D — Curriculum Builder
  18. Form-based Curriculum Definition builder (open subject/unit naming)
  19. POST /curricula/definitions — submit Definition for school admin approval
  20. School admin approval queue + approve/reject endpoints + notifications

Phase E — Pipeline Billing
  21. POST /pipeline/estimate — live Anthropic token pricing calculation
  22. Cost estimate modal (school admin portal)
  23. Stripe pay-per-run charge (separate from subscription)
  24. Pipeline trigger gated on: school admin approval + billing confirmation
  25. On completion: Package assigned to Classroom; merged view updated
```

---

*Analysis produced: 2026-04-11*
*Updated: 2026-04-11 — all Q1–Q22 answered; terminology locked; no blockers*
*Status: Ready for Phase A build*
