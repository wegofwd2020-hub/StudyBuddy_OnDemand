# Local Setup Guide for Demo (Laptop)

Complete guide to check out and run StudyBuddy on a new machine for demo purposes.

## Prerequisites

Install before starting:
- **Git** — version control
- **Docker** + **Docker Compose** — containerization (required for full stack)
- **Python 3.9+** — for seed scripts
- **Node.js 18+** — for web frontend dev server (optional if not modifying web)
- **4GB+ RAM**, **10GB+ disk** — minimum for containers
- **Internet** — initial docker pull (images ~2GB)

### macOS
```bash
# Install Homebrew if not present
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Docker Desktop
brew install --cask docker

# Verify installation
docker --version
docker compose --version
```

### Linux (Ubuntu/Debian)
```bash
sudo apt update
sudo apt install -y git docker.io docker-compose python3 python3-pip nodejs npm

# Add user to docker group (avoid sudo for docker commands)
sudo usermod -aG docker $USER
# Restart shell or: newgrp docker
```

### Windows
- Download **Docker Desktop for Windows** from docker.com
- Install **Git for Windows** from git-scm.com
- Install **Python 3.9+** from python.org (check "Add to PATH")
- Install **Node.js** from nodejs.org (optional)

---

## Step 1: Clone Repository

```bash
git clone https://github.com/wegofwd2020-hub/StudyBuddy_OnDemand.git
cd StudyBuddy_OnDemand
```

---

## Step 2: Create Environment File

```bash
# Copy template
cp .env.example .env  # If it exists, otherwise create from scratch

# Edit .env with required variables
cat > .env << 'EOF'
# Database
POSTGRES_PASSWORD=demo_password_secure_123

# Redis
REDIS_PASSWORD=redis_secure_password_123

# App
APP_ENV=development
DEBUG=false

# Optional: Anthropic API (for content generation, leave empty for demo)
ANTHROPIC_API_KEY=

# Optional: Voyage API (for help widget, leave empty for demo)
VOYAGE_API_KEY=
EOF
```

---

## Step 3: Start Local Stack

```bash
# Start all services (db, redis, api, web, etc.)
./dev_start.sh

# Watch logs (in another terminal)
docker compose logs -f api

# Stack should be ready when you see:
# - api: "Application startup complete"
# - migrate: "All migrations applied"
```

**Expected startup time: 60-90 seconds**

Check services are healthy:
```bash
docker compose ps
# All should show "healthy" or "Up"
```

---

## Step 4: Create Super Admin Account

```bash
# Set admin password
docker compose exec api python /app/scripts/reset_admin_password.py \
  --email admin@lincoln.demo \
  --password AdminPassword123!

# Output should confirm: "Password updated for admin@lincoln.demo"
```

Test admin login at: **http://localhost:80/admin/login**
- Email: `admin@lincoln.demo`
- Password: `AdminPassword123!`

---

## Step 5: Seed Demo School, Teachers, Students

### Option A: Automated Seed Script (Recommended)

```bash
# Run seed script from repository
cd StudyBuddy_OnDemand
docker compose exec -T db psql -U studybuddy -d studybuddy < \
  /tmp/claude-1000/-home-sivam-Documents-code-projects-AIStuff-STEM-studybuddy-StudyBuddy-OnDemand/13f29509-750d-49af-ac02-67a51faedbdf/scratchpad/seed_grades_8_12_fixed.sql
```

Or use the SQL file directly:

```bash
# Create seed file in your repo
cat > scripts/seed_demo_lincoln_high.sql << 'EOFQUERY'
-- Creates Lincoln High School with 5 teachers and 50 students (10 per grade 8-12)
-- All accounts use password: "password" (bcrypt hash included)

SET session_replication_role = REPLICA;

-- School
INSERT INTO schools (school_id, name, contact_email, country, status, created_at)
VALUES (
  'f0000000-0000-0000-0000-000000000001'::uuid,
  'Lincoln High School',
  'admin@lincoln.demo',
  'CA',
  'active',
  NOW()
) ON CONFLICT DO NOTHING;

-- Subscription (required for students to access lessons)
INSERT INTO school_subscriptions (
  school_id, plan, status, stripe_customer_id, stripe_subscription_id, 
  max_students, max_teachers, current_period_end, created_at, updated_at
)
VALUES (
  'f0000000-0000-0000-0000-000000000001'::uuid,
  'enterprise',
  'active',
  'cus_demo_enterprise',
  'sub_demo_enterprise',
  100,
  10,
  NOW() + INTERVAL '1 year',
  NOW(),
  NOW()
) ON CONFLICT DO NOTHING;

-- 50 Students (10 per grade 8-12), grades distributed
-- Bcrypt hash for password "password"
INSERT INTO students (student_id, email, name, grade, password_hash, auth_provider, 
  school_id, account_status, enrolled_at, created_at, locale, external_auth_id)
VALUES
  ('d0000000-0000-0000-0008-000000000001'::uuid, 'g8.01@lincoln.demo', 'Alex M.', 8, 
    '$2b$12$7yxLwDJmovKZR6wNSEqxT.3ToW6.BNCukV/xuPe0goXh9.JikGZxa', 'local', 
    'f0000000-0000-0000-0000-000000000001'::uuid, 'active', NOW(), NOW(), 'en', 'local_g8_01'),
  ('d0000000-0000-0000-0008-000000000002'::uuid, 'g8.02@lincoln.demo', 'Bailey T.', 8,
    '$2b$12$7yxLwDJmovKZR6wNSEqxT.3ToW6.BNCukV/xuPe0goXh9.JikGZxa', 'local',
    'f0000000-0000-0000-0000-000000000001'::uuid, 'active', NOW(), NOW(), 'en', 'local_g8_02'),
  -- ... (insert 48 more students for grades 9-12, 10 per grade)
ON CONFLICT DO NOTHING;

SET session_replication_role = DEFAULT;
EOFQUERY

# Run it
docker compose exec -T db psql -U studybuddy -d studybuddy < scripts/seed_demo_lincoln_high.sql
```

### Option B: Manual Creation (via Admin Console)

1. Go to **http://localhost:80/admin** (logged in as super admin)
2. Navigate to **Schools** → **Create School**
3. Create "Lincoln High School" with contact email
4. Create 5 teachers via UI
5. Invite/create 50 students

---

## Step 6: Verify Setup

### Test Admin Login
```
URL: http://localhost:80/admin/login
Email: admin@lincoln.demo
Password: AdminPassword123!
Expected: Admin dashboard loads with metrics
```

### Test Student Login
```
URL: http://localhost/signin
Email: g8.01@lincoln.demo (or any seeded student)
Password: password
Expected: Student dashboard with curriculum access
```

### Check Services
```bash
# All should show "healthy" or "Up"
docker compose ps

# Logs should show no errors
docker compose logs --tail 20 api
```

---

## Step 7: Prepare for Demo (Laptop)

### Offline Content
Pre-generate lesson content before traveling:

```bash
# Build Grade 8-9 content (fast, ~5 min per grade)
docker compose run --rm pipeline python build_grade.py --grade 8 --lang en
docker compose run --rm pipeline python build_grade.py --grade 9 --lang en
```

This stores content in `content_store_data/` (included in repo).

### Disk Space Check
```bash
# Stack size (should be < 5GB for demo)
du -sh .
du -sh content_store_data/
docker system df  # See image sizes
```

### Network Requirements
- **On LAN/WiFi**: Full app works, no internet needed after docker images pulled
- **Offline**: Backend needs no internet; web browser still needs localhost connectivity

---

## Step 8: Running Demo

### Start Demo
```bash
# In demo location, start stack
./dev_start.sh

# Wait 60-90 seconds for services to boot
docker compose ps  # Verify all healthy
```

### Demo Flow
1. **Show Admin Console** → `/admin/login` (super admin)
   - Dashboard: subscription status, pipeline jobs
   - Content Review: view AI-generated lessons
   
2. **Show Student Portal** → `/signin` (student account)
   - Curriculum: browse by grade/subject
   - Lessons: view formatted content
   - Quizzes: take sample assessments

3. **Credentials for Demo**
   - **Admin**: `admin@lincoln.demo` / `AdminPassword123!`
   - **Student**: `g8.01@lincoln.demo` / `password` (or any seeded student)

### Stop Demo
```bash
docker compose down

# Keep data (volumes persist)
# To wipe data: docker compose down -v
```

---

## Troubleshooting

### Stack won't start
```bash
# Check Docker is running
docker ps

# See startup errors
docker compose logs migrate
docker compose logs api

# Rebuild images (in case of corruption)
docker compose build --no-cache
```

### Can't reach localhost
- Ensure Docker Desktop is running (macOS/Windows)
- Try `localhost:8000` (API) or `localhost:3000` (web) directly
- On Linux: `sudo usermod -aG docker $USER` and log back in

### Database locked
```bash
# Kill any stuck connections
docker compose exec db psql -U studybuddy -d studybuddy -c \
  "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='studybuddy' AND pid != pg_backend_pid();"
```

### Password hashes don't work
```bash
# Regenerate hashes for all students
python3 << 'EOF'
import bcrypt
password = "password"
hash_str = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(rounds=12)).decode('utf-8')
print(f"Hash: {hash_str}")
EOF

# Update DB
docker compose exec -T db psql -U studybuddy -d studybuddy << SQL
UPDATE students SET password_hash = '<HASH_FROM_ABOVE>';
SQL
```

---

## Portable Checklist

Before leaving with laptop:

- [ ] `docker images` shows all images (no need to re-pull on demo machine)
- [ ] `content_store_data/` has pre-built lessons for G8-12
- [ ] `.env` file is present and configured
- [ ] `docker compose ps` shows all services healthy
- [ ] Admin login works (`admin@lincoln.demo`)
- [ ] At least one student can log in
- [ ] Backup `.env` file (don't lose it!)

---

## Quick Reference

| What | URL | Credentials |
|---|---|---|
| Admin Console | http://localhost/admin | admin@lincoln.demo / AdminPassword123! |
| Student Portal | http://localhost | g8.01@lincoln.demo / password |
| API | http://localhost:8000 | (Bearer JWT from login) |
| Web Dev | http://localhost:3000 | (if running separately) |

---

## Tips for Demo Success

1. **Test login flow before demo** — Run through the full signin → dashboard path
2. **Pre-load content** — Build grades 8-9 before traveling (no need to wait during demo)
3. **Disable notifications** — Silent Docker logs during presentation
4. **Have backup credentials** — Write down admin + 3 student logins on a card
5. **Network:** Demo works on any WiFi; doesn't need internet after startup
6. **Laptop power:** Keep plugged in during demo (Docker can be resource-heavy)

---

## Next Steps

- **Modify content**: Edit `pipeline/prompts.py` to change lesson tone/depth
- **Add more students**: Use seed scripts to add grades or additional schools
- **Customize branding**: Edit `web/app/(public)/page.tsx` for landing page
- **Test production paths**: Create a Dockerfile-based deployment

See `OPERATIONS.md` for production deployment.
