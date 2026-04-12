# StudyBuddy OnDemand — Local Testing Guide

How to seed test accounts and walk through every persona on your local dev stack.

---

## 1. Start the stack

```bash
./dev_start.sh
```

Services come up at:

| Service | URL |
|---|---|
| Web (Next.js) | http://localhost:3000 |
| API (FastAPI) | http://localhost:8000 |
| API docs | http://localhost:8000/api/docs |
| Health | http://localhost:8000/health |
| Readiness | http://localhost:8000/readyz |
| Liveness | http://localhost:8000/healthz |

---

## 2. Seed all demo accounts

Run these once (they are idempotent — safe to re-run at any time):

```bash
# Super admin
docker compose exec api python scripts/seed_super_admin.py

# Generic demo student (for the public "Try it" flow)
docker compose exec api python scripts/seed_demo_test_account.py

# Full school demo — MilfordWaterford Local School (teachers + students, Auth0 demo track)
docker compose exec api python scripts/seed_demo_milfordwaterford.py

# Dev School — local auth track (Phase A: email+password login, no Auth0)
docker compose exec api python scripts/seed_phase_a_dev.py
```

---

## 3. Personas and credentials

### 3.1 Super Admin

| Field | Value |
|---|---|
| URL | http://localhost:3000/admin/login |
| Email | wegofwd2020@gmail.com |
| Password | Admin1234! |
| Role | super_admin |

**What to test:**
- Dashboard — subscription KPIs, MRR card (now shows as string e.g. `$0.00`)
- Content Review queue — approve / reject / publish / rollback versions
- Pipeline job list — sortable, filterable; trigger a new job
- Demo accounts — manage demo student requests
- Demo teacher accounts — manage demo teacher requests
- Feedback — student feedback submissions
- Audit log

---

### 3.2 Demo Student (public "Try it" flow)

| Field | Value |
|---|---|
| Landing page | http://localhost:3000 |
| Demo login URL | http://localhost:3000/demo |
| Email | demo-test@studybuddy.dev |
| Password | DemoTest-2026! |
| Grade | 8 |

**What to test:**
1. Go to http://localhost:3000 → click **Try it free**
2. Log in with the credentials above
3. Pick any STEM subject from the curriculum map
4. Work through a lesson → quiz → experiment
5. Check progress screen (streak, history)
6. Test dyslexia toggle: click the Eye icon in the header or press **Alt+D**

---

### 3.3 School Teachers — MilfordWaterford Local School

Both teachers log in at: http://localhost:3000/school/login

#### Sam Houston (Grade 8 teacher)

| Field | Value |
|---|---|
| Email | sam.houston@milfordwaterford.edu |
| Password | MWTeacher-Sam-2026! |
| Role | teacher |
| Assigned grades | 8 |

#### Linda Ronstad (Grade 12 teacher)

| Field | Value |
|---|---|
| Email | linda.ronstad@milfordwaterford.edu |
| Password | MWTeacher-Linda-2026! |
| Role | teacher |
| Assigned grades | 12 |

**What to test (teacher persona):**
1. Log in → school portal dashboard → **My Classes** panel (shows assigned grade)
2. **Curriculum** tab — grade-filtered view of uploaded curriculum structure
3. **Content Library** — browse AI-generated lessons, quizzes, tutorials by grade; click into a unit
4. **Reports** → Overview, Trends, At-Risk, Unit Performance, Engagement, Feedback
5. **Students** tab — roster filtered to the teacher's enrolled grade
6. Check **Alerts** badge for unacknowledged alerts
7. Test dyslexia toggle via Eye button in portal header or **Alt+D**

> **Note:** Teachers see only their assigned grades in Content Library and Student Roster.
> To widen the view, the school admin must re-assign grades from the Teachers page.

---

### 3.4 School Students — MilfordWaterford

Students log in via Auth0 (not the demo path). In local dev Auth0 is mocked —
use the dev login shortcut at http://localhost:8000/api/docs (`POST /auth/dev-login`).

Or seed the students as demo accounts using the MilfordWaterford seed script and
log them in at http://localhost:3000/demo.

| Name | Email | Password | Grade |
|---|---|---|---|
| Sam Jr | samjr@milfordwaterford.edu | MWStudent-SamJr-2026! | 8 |
| Jose Herbert | jose.herbert@milfordwaterford.edu | MWStudent-Jose-2026! | 8 |
| Sam Sr | samsr@milfordwaterford.edu | MWStudent-SamSr-2026! | 12 |
| Linda Herbert | linda.herbert@milfordwaterford.edu | MWStudent-Linda-2026! | 12 |

**What to test (student persona):**
- Curriculum map — units visible match the school's curriculum + default content
- Lesson → Tutorial → Quiz → Experiment flow
- Audio playback (requires content pipeline to have run)
- Progress history and streak counter
- Settings page — language, notifications, dyslexia font toggle

---

### 3.5 School Admin (MilfordWaterford)

The seed script creates the school but not a dedicated `school_admin` teacher.
To promote Sam Houston to school_admin:

```bash
docker compose exec api python3 - <<'EOF'
import asyncio, asyncpg, os

async def main():
    conn = await asyncpg.connect(os.environ["DATABASE_URL"])
    await conn.execute(
        "UPDATE teachers SET role = 'school_admin' WHERE email = $1",
        "sam.houston@milfordwaterford.edu"
    )
    await conn.close()
    print("Done — Sam Houston is now school_admin")

asyncio.run(main())
EOF
```

Then log in at http://localhost:3000/school/login as Sam Houston.

**Additional school_admin pages:**
- **Teachers** tab — full teacher roster, grade assignments
- **Subscription** tab — plan status, checkout flow (Stripe test mode)
- **Settings** — school profile

---

## 4. Quick API smoke-test (curl)

```bash
# Liveness
curl http://localhost:8000/healthz

# Readiness (checks DB + Redis)
curl http://localhost:8000/readyz

# Admin login
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/admin/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"wegofwd2020@gmail.com","password":"Admin1234!"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])")

# Subscription analytics (mrr_usd is now a string)
curl -s http://localhost:8000/api/v1/admin/analytics/subscriptions \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

# Demo teacher login
curl -s -X POST http://localhost:8000/api/v1/demo/teacher/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"sam.houston@milfordwaterford.edu","password":"MWTeacher-Sam-2026!"}' \
  | python3 -m json.tool

# Demo student login
curl -s -X POST http://localhost:8000/api/v1/demo/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"demo-test@studybuddy.dev","password":"DemoTest-2026!"}' \
  | python3 -m json.tool
```

---

## 5. Accessibility features to verify

| Feature | How to trigger |
|---|---|
| Dyslexia font toggle | Click Eye icon in portal header OR press **Alt+D** |
| Dyslexia font (settings page) | Student → Account → Settings → Accessibility card |
| Font persists across reload | Cookie `sb_dyslexic=1` is set — toggle survives refresh |
| Skip to content link | Tab on any page — first focus target is "Skip to main content" |
| High-contrast mode | Enable OS forced-colors / high-contrast mode |

---

## 6. Re-seed / reset

```bash
# Wipe DB and start fresh (destroys all data)
./dev_start.sh reset

# After reset, re-seed everything:
docker compose exec api python scripts/seed_super_admin.py
docker compose exec api python scripts/seed_demo_test_account.py
docker compose exec api python scripts/seed_demo_milfordwaterford.py
docker compose exec api python scripts/seed_phase_a_dev.py
```

---

## 7. ADR-001 changes that affect testing (shipped 2026-04-05)

The `adr-001-complete` tag (commit `4ab32c8`) introduced structural changes that
affect how you seed and test the school model. Key things to know:

### Subscription model — school-only billing

Individual student subscriptions (`subscriptions` table) and private teacher
subscriptions have been removed. All billing flows through `school_subscriptions`.

- The **Subscription** tab in the school portal creates a Stripe checkout session for the school.
- Stripe metadata: `{"school_id": "...", "plan": "starter|professional|enterprise"}`.
- In local dev (no live Stripe), you can simulate an active subscription by inserting directly:

```bash
docker compose exec api python3 - <<'EOF'
import asyncio, asyncpg, os, uuid
from datetime import datetime, UTC, timedelta

async def main():
    conn = await asyncpg.connect(os.environ["DATABASE_URL"])
    # Get the MilfordWaterford school_id
    school = await conn.fetchrow(
        "SELECT id FROM schools WHERE contact_email = 'admin@milfordwaterford.edu'"
    )
    if not school:
        print("School not found — run seed_demo_milfordwaterford.py first")
        return
    school_id = school["id"]
    await conn.execute(
        """
        INSERT INTO school_subscriptions
            (school_id, plan, status, max_students, max_teachers,
             stripe_customer_id, stripe_subscription_id, current_period_end)
        VALUES ($1, 'professional', 'active', 200, 20, 'cus_test', 'sub_test', $2)
        ON CONFLICT (school_id) DO UPDATE
            SET plan='professional', status='active',
                current_period_end=EXCLUDED.current_period_end
        """,
        school_id,
        datetime.now(UTC) + timedelta(days=30),
    )
    print(f"School {school_id} — professional subscription activated")
    await conn.close()

asyncio.run(main())
EOF
```

### Row-Level Security (RLS)

All seven tenant-scoped tables now have PostgreSQL RLS policies. This is invisible
during normal use (the API stamps `app.current_school_id` automatically), but affects
direct DB access:

- **psql / pgAdmin queries** — if you connect as the app user, you must set the variable
  before querying or you'll see zero rows:
  ```sql
  SELECT set_config('app.current_school_id', 'bypass', false);
  SELECT * FROM teachers;   -- now shows all rows
  ```
- **Direct seed scripts** — the seed scripts run as the `postgres` superuser
  (via the `DATABASE_URL` env var), which is exempt from RLS. They work as-is.
- **Test fixtures** — the `db_conn` pytest fixture sets bypass mode automatically.

### Private teacher tier removed

The `src/private_teacher/` module and its endpoints are gone. There are no
`/auth/private-teacher/*` routes. Home schoolers and private tutors register
as a school (`POST /api/v1/schools/register`) with their personal email as both
the school contact email and teacher email.

### Redis key namespace

School-scoped Redis keys now use the `school:{school_id}:` prefix. If you're
inspecting Redis manually (e.g. with RedisInsight), use `SCAN school:*` to browse
tenant-scoped cache entries.

---

## 8. Phase A — Local Auth (school-provisioned users)

Phase A adds a third auth track: email + password login for school-provisioned
teachers and students (no Auth0 required). New schools register via
`POST /schools/register` instead of Auth0.

### Seed the Dev School (local auth)

```bash
docker compose exec api python scripts/seed_phase_a_dev.py
```

This is idempotent. To wipe and recreate:

```bash
docker compose exec api python scripts/seed_phase_a_dev.py --reset
```

### Accounts

All accounts log in at: **http://localhost:3000/school/login**

| Role | Email | Password | Notes |
|---|---|---|---|
| School Admin | `admin@devschool.local` | `DevAdmin1234!` | `first_login=FALSE` — no forced reset |
| Teacher | `teacher@devschool.local` | `DevTeacher1234!` | `first_login=FALSE` |
| Student | `student@devschool.local` | `DevStudent1234!` | Grade 8 |

### First-login forced-reset flow

When a school admin provisions a new teacher or student via the portal, the system
sets `first_login=TRUE` and emails a generated password. To test this flow manually:

```bash
# Force first_login=TRUE on the Dev Teacher
docker compose exec api python3 - <<'EOF'
import asyncio, asyncpg, os

async def main():
    conn = await asyncpg.connect(os.environ["DATABASE_URL"])
    await conn.execute(
        "UPDATE teachers SET first_login = TRUE WHERE email = $1",
        "teacher@devschool.local"
    )
    print("Done — teacher@devschool.local will be forced to reset on next login")
    await conn.close()

asyncio.run(main())
EOF
```

Then log in as `teacher@devschool.local` — the portal must redirect to
`/school/change-password?required=1` before any other page renders.

After changing the password, `first_login` is set back to `FALSE` and normal
navigation resumes.

### What to test (Phase A)

1. **School self-registration** — `POST /api/v1/schools/register` (requires `password` ≥12 chars)
2. **Local login** — `POST /api/v1/auth/login` → JWT with `first_login` bool in payload
3. **Forced password reset** — set `first_login=TRUE`, log in, confirm redirect to change-password page
4. **`PATCH /auth/change-password`** — verifies current password, clears `first_login`
5. **Teacher provisioning** — as school admin: `POST /schools/{id}/teachers`
6. **Student provisioning** — as school admin: `POST /schools/{id}/students`

---

## 9. Phase B — Classrooms

Classrooms let school admins group curriculum packages and assign students to them.

### Routes

| URL | What it shows |
|---|---|
| http://localhost:3000/school/classrooms | List of classrooms for the school |
| http://localhost:3000/school/classrooms/[id] | Classroom detail — packages + students |

### What to test

1. Log in as Sam Houston (or Dev Admin from Phase A) at `/school/login`
2. Navigate to **Classrooms** in the sidebar
3. Create a new classroom (name + grade level)
4. Add a curriculum package to the classroom
5. Assign enrolled students to the classroom
6. Verify the classroom detail page shows both the package list and student roster

### API endpoints

```bash
# List classrooms (requires teacher JWT)
curl http://localhost:8000/api/v1/schools/{school_id}/classrooms \
  -H "Authorization: Bearer $TEACHER_TOKEN"

# Create classroom
curl -X POST http://localhost:8000/api/v1/schools/{school_id}/classrooms \
  -H "Authorization: Bearer $TEACHER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Grade 8 Science","grade":8}'
```

---

## 10. Phase C — Curriculum Catalog

The catalog browser lets school staff see all platform-provided curriculum packages
and their content readiness per subject.

### Route

| URL | What it shows |
|---|---|
| http://localhost:3000/school/catalog | Platform curriculum catalog |
| http://localhost:3000/school/catalog?grade=8 | Filtered to Grade 8 |

### What to test

1. Log in as any teacher at `/school/login`
2. Navigate to **Catalog** in the sidebar
3. Expand a subject row — see content readiness bar (% of units with generated content)
4. Filter by grade using the dropdown

### API

```bash
# All grades
curl http://localhost:8000/api/v1/curricula/catalog \
  -H "Authorization: Bearer $TEACHER_TOKEN"

# Grade 8 only
curl "http://localhost:8000/api/v1/curricula/catalog?grade=8" \
  -H "Authorization: Bearer $TEACHER_TOKEN"
```

---

## 11. Phase D — Curriculum Builder

School admins can submit custom curriculum definitions for platform review and
AI content generation.

### Routes

| URL | What it shows |
|---|---|
| http://localhost:3000/school/curriculum/definitions | Approval queue — submitted definitions |
| http://localhost:3000/school/curriculum/definitions/new | 4-step definition submission form |
| http://localhost:3000/school/curriculum/definitions/[id] | Definition detail + review actions |

### What to test

1. Log in as Sam Houston (promoted to school_admin) at `/school/login`
2. Go to **Curriculum → Definitions** → click **New Definition**
3. Complete the 4-step form (grade, subject, unit list, confirmation)
4. Submit — definition appears in the queue with status `pending`
5. As super admin in the admin console, approve or reject the definition
6. Verify the status updates on the school portal

### API

```bash
# Submit a definition
curl -X POST http://localhost:8000/api/v1/schools/{school_id}/curriculum/definitions \
  -H "Authorization: Bearer $TEACHER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"grade":8,"subject":"MATH","units":[{"title":"Algebra Intro","sort_order":1}]}'

# List definitions
curl http://localhost:8000/api/v1/schools/{school_id}/curriculum/definitions \
  -H "Authorization: Bearer $TEACHER_TOKEN"
```

---

## 12. Phase E — Pipeline Billing

Before triggering a custom curriculum build, school admins see a cost estimate
and must confirm. Builds beyond the plan allowance require a Stripe payment.

### What to test

1. Log in as school admin, go to a definition in `approved` status
2. Click **Estimate Cost** — see unit count, token forecast, `within_allowance`, card on file
3. Click **Trigger Build** — if within allowance, Celery dispatches immediately; if not, Stripe PaymentIntent is required
4. Confirm the pipeline job appears in the admin console at http://localhost:3000/admin/pipeline

### Simulate within-allowance scenario

The MilfordWaterford school starts with 0 builds used. The starter plan includes 1 free
build per year. After seeding, the first trigger will be within allowance:

```bash
# Get cost estimate for a definition
curl http://localhost:8000/api/v1/schools/{school_id}/curriculum/definitions/{def_id}/estimate \
  -H "Authorization: Bearer $TEACHER_TOKEN"
```

### Simulate over-allowance (Stripe required)

```bash
# Exhaust the build allowance
docker compose exec api python3 - <<'EOF'
import asyncio, asyncpg, os

async def main():
    conn = await asyncpg.connect(os.environ["DATABASE_URL"])
    school = await conn.fetchrow(
        "SELECT id FROM schools WHERE contact_email = 'admin@milfordwaterford.edu'"
    )
    await conn.execute(
        "UPDATE school_subscriptions SET builds_used = max_builds WHERE school_id = $1",
        school["id"]
    )
    print("Build allowance exhausted — next trigger will require Stripe payment")
    await conn.close()

asyncio.run(main())
EOF
```

---

## 13. Epic 1 — Multi-Provider LLM

Schools can configure which LLM provider (Anthropic Claude, OpenAI GPT-4o, Google
Gemini) generates their curriculum content. Admins can see which provider generated
each version in the content review queue.

### Provider badge in admin content review

1. Log in as super admin → http://localhost:3000/admin/content-review
2. The **Provider** column shows a colour-coded chip per version:
   - Violet = Anthropic Claude
   - Emerald = OpenAI GPT-4o
   - Blue = Google Gemini
   - Amber = School Upload

### School LLM config API

```bash
# Get current LLM config for a school
curl http://localhost:8000/api/v1/schools/{school_id}/llm-config \
  -H "Authorization: Bearer $TEACHER_TOKEN"

# Response:
# {
#   "school_id": "...",
#   "allowed_providers": ["anthropic"],
#   "default_provider": "anthropic",
#   "comparison_enabled": false,
#   "dpa_acknowledged_at": {}
# }

# Enable OpenAI + acknowledge DPA
curl -X PUT http://localhost:8000/api/v1/schools/{school_id}/llm-config \
  -H "Authorization: Bearer $TEACHER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "allowed_providers": ["anthropic", "openai"],
    "default_provider": "openai",
    "comparison_enabled": false,
    "acknowledge_dpa_for": ["openai"]
  }'
```

### Trigger a comparison build (CLI)

```bash
# Run both Anthropic and OpenAI on Grade 8 (dry run first)
docker compose exec celery-pipeline python pipeline/build_grade.py \
  --grade 8 --lang en --provider anthropic,openai --dry-run

# Live run (requires ANTHROPIC_API_KEY + OPENAI_API_KEY in environment)
docker compose exec celery-pipeline python pipeline/build_grade.py \
  --grade 8 --lang en --provider anthropic,openai
```

Both versions appear in the content review queue side-by-side. Use the existing
**Compare with previous version** diff view to compare outputs.
