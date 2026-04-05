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

# Full school demo — MilfordWaterford Local School (teachers + students)
docker compose exec api python scripts/seed_demo_milfordwaterford.py
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

# After reset, re-seed:
docker compose exec api python scripts/seed_super_admin.py
docker compose exec api python scripts/seed_demo_test_account.py
docker compose exec api python scripts/seed_demo_milfordwaterford.py
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
