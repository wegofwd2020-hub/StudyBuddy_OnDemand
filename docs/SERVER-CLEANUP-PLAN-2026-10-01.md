# StudyBuddy Server Cleanup & Redeployment Plan
**Date:** 2026-10-01  
**Server:** 178.105.160.62 (Hetzner)  
**Status:** Ready to execute  

---

## Table of Contents
1. [Server Inventory](#server-inventory)
2. [What to Keep vs. Delete](#what-to-keep-vs-delete)
3. [9-Phase Cleanup & Redeployment](#9-phase-cleanup--redeployment)
4. [Rollback Strategy](#rollback-strategy)
5. [Gotchas & Notes](#gotchas--notes)

---

## Server Inventory

### Active Projects (5 total)
Five independent projects run on this server. Only StudyBuddy will be cleaned.

| Project | Containers | Network | Status | Safe to Touch? |
|---------|-----------|---------|--------|---|
| **StudyBuddy** | api, web, nginx, celery-worker, celery-beat, redis, db, autoheal, migrate | studybuddy_default | ✅ UP | **YES** |
| Mentible | api, celery-beat, celery-worker, redis | mentible_default | ✅ UP | ❌ NO |
| Mambakkam | astrowind website | mambakkam_default | ✅ UP | ❌ NO |
| Kaundinyalabs | website | kaundinyalabs_default | 🔴 UNHEALTHY | ❌ NO |
| Agastya | API server | agastya_default | ✅ UP | ❌ NO |
| Pramana | DB only | pramana_default | ✅ UP | ❌ NO |

**Key:** Each has isolated docker network + volumes. No cross-project dependencies.

### StudyBuddy Artifact Map

| Path | Contents | Size | Usage | Keep? |
|------|----------|------|-------|-------|
| `/opt/studybuddy/` | Main repo (git) + docker-compose + code + scripts | — | Active | ✅ YES |
| `/opt/studybuddy/.git` | Git history + branches | — | Development | ✅ YES |
| `/opt/studybuddy/backups/` | Database + content snapshots | — | Recovery | ✅ YES |
| `/opt/studybuddy/pgbouncer/` | PgBouncer config + pool settings | — | Production | ✅ YES |
| `/opt/studybuddy/.env` + `.env.demo` | Secrets + config | — | Build artifact | 🗑️ REGEN |
| `/opt/studybuddy/docker-compose.yml` | Service definitions | — | Source | ✅ YES |
| `/opt/studybuddy/docker-compose.override.yml` | Dev/prod config overrides | — | Build artifact | 🗑️ REGEN |
| `/opt/studybuddy/infra/nginx/nginx.dev.conf` | Reverse proxy (/ → web:3000, /api/ → api:8000) | — | Source | ✅ YES |
| `/opt/studybuddy/web/.next` | Next.js build cache | — | Build artifact | 🗑️ DELETE |
| `/opt/studybuddy/backend/__pycache__` | Python cache | — | Build artifact | 🗑️ DELETE |
| `/opt/sb202609/` | OLD StudyBuddy version (Jun 2026) | — | Obsolete | 🗑️ DELETE |
| `/data/content/` | Pre-generated lessons (JSON) | 8 KB | Content | ✅ YES |
| `/data/sample-visuals/` | Visual assets | 219 MB | Content | ✅ YES |
| `/data/videos/` | Video content | 36 MB | Content | ✅ YES |

### Docker Volumes (Managed)
```
studybuddy_postgres_data          ← Live PostgreSQL (users, progress, content metadata)
studybuddy_redis_data             ← Live Redis (cache, sessions)
studybuddy_demo_pgdata            ← Old demo DB (delete if unused)
studybuddy_demo_redis             ← Old demo cache (delete if unused)
sb_20609_postgres_data            ← Old version data (delete with /opt/sb202609/)
sb_20609_redis_data               ← Old version cache (delete with /opt/sb202609/)
```

### Networking
- **Port 80:** nginx (reverse proxy, routes to api:8000 + web:3000)
- **Port 8081:** Mambakkam (internal, do not touch)
- **Port 8082:** Kaundinyalabs (internal)
- **Port 8083:** Agastya (internal)
- **Port 8092:** Mentible (internal)
- **Port 6379:** StudyBuddy Redis (internal)
- **Port 5432:** StudyBuddy PostgreSQL (internal)

**No external DNS.** Access via IP directly: `http://178.105.160.62/`

---

## What to Keep vs. Delete

### ✅ KEEP (Critical)
- `.git/` — all commit history
- `backups/` — snapshots for recovery
- `/data/` — all content (8 KB + 255 MB)
- `docker-compose.yml` — service definitions
- `infra/nginx/` — routing config
- `pgbouncer/` — connection pool config
- `backend/`, `web/`, `pipeline/`, `mobile/` — source code
- `docs/`, `CLAUDE.md`, `README.md` — documentation

### 🗑️ DELETE (Safe)
- `.env`, `.env.demo` — regenerate (contains stale secrets)
- `docker-compose.override.yml` — regenerate for fresh env
- `.next/` in `web/` — Next.js cache (rebuild on start)
- `__pycache__/`, `.pytest_cache/` — Python build artifacts
- `/opt/sb202609/` — old version (entire directory)
- `sb_20609_postgres_data`, `sb_20609_redis_data` volumes — old data
- `studybuddy_demo_pgdata`, `studybuddy_demo_redis` volumes — old demo (if unused)
- `/opt/mentible-old-*` — old Mentible backups (unrelated project)
- Stale branches in `.git/` (optional, safe to keep)

### ⚠️ REGENERATE (Required)
- `.env` — new secrets + database URLs
- `docker-compose.override.yml` — new DB/Redis URLs
- `.next/` — will auto-rebuild on first start

---

## 9-Phase Cleanup & Redeployment

**Total time:** 50–60 min | **Downtime:** ~15 min (Phase 2–7)

### Phase 1: Pre-cleanup Backup (5 min)
**Goal:** Snapshot current state in case rollback needed.

```bash
cd /opt/studybuddy

# Backup PostgreSQL
docker compose exec -T db pg_dump \
  -U studybuddy studybuddy | gzip > backups/db-before-cleanup-$(date +%s).sql.gz

# Backup all content
tar -czf backups/content-before-cleanup-$(date +%s).tar.gz /data/

# Snapshot docker state
docker compose ps > backups/docker-state-before-cleanup.txt
docker volume ls > backups/volumes-before-cleanup.txt

# Tag current commit
git tag -a "before-cleanup-oct-2026" HEAD -m "Pre-cleanup snapshot"

# Verify
ls -lh backups/db-before-cleanup-*.sql.gz
ls -lh backups/content-before-cleanup-*.tar.gz
```

**Expected output:**
```
db-before-cleanup-1727799600.sql.gz  (~50-100 MB)
content-before-cleanup-1727799600.tar.gz (~255 MB)
docker-state-before-cleanup.txt
volumes-before-cleanup.txt
```

### Phase 2: Stop StudyBuddy (3 min)
**Goal:** Cleanly shut down all containers. Volumes + data persist.

```bash
cd /opt/studybuddy
docker compose down

# Verify containers stopped
docker ps | grep studybuddy  # Should return nothing

# Verify volumes still exist
docker volume ls | grep studybuddy  # Should show all volumes
```

### Phase 3: Clean Build Artifacts (2 min)
**Goal:** Remove stale build artifacts. Keep source + data.

```bash
cd /opt/studybuddy

# Python cache
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null

# Next.js build cache
rm -rf web/.next

# pytest cache
rm -rf backend/.pytest_cache

# Misc caches
find . -type d -name ".cache" -exec rm -rf {} + 2>/dev/null
find . -type d -name "dist" -exec rm -rf {} + 2>/dev/null
find . -type d -name "build" -exec rm -rf {} + 2>/dev/null

# Old compose overrides (will regenerate)
rm -f docker-compose.override.yml

# Old env files (will regenerate)
rm -f .env .env.demo

# Verify data still exists
ls -la /data/  # Should show content/ sample-visuals/ videos/
ls -la backups/  # Should show db + content snapshots
```

### Phase 4: Sync Fresh Code from Localhost (10–15 min)
**Goal:** Update server code to match your local version.

#### Option A: Git Pull (Fastest)
If server's git remote points to GitHub:

```bash
cd /opt/studybuddy
git fetch origin
git checkout main
git pull origin main

# Verify
git log --oneline -5
```

#### Option B: Rsync from Localhost (Safest)
Run from your local machine:

```bash
cd ~/Documents/code/projects/AIStuff/STEM_studybuddy/StudyBuddy_OnDemand

# Push to server (excludes build artifacts, .env, node_modules, data)
rsync -av --delete \
  --exclude='.next' \
  --exclude='.env*' \
  --exclude='*.pyc' \
  --exclude='__pycache__' \
  --exclude='node_modules' \
  --exclude='backups' \
  --exclude='data' \
  --exclude='.pytest_cache' \
  ./ deploy@178.105.160.62:/opt/studybuddy/

# (Or use root if no deploy user:)
rsync -av --delete \
  --exclude='.next' \
  --exclude='.env*' \
  --exclude='*.pyc' \
  --exclude='__pycache__' \
  --exclude='node_modules' \
  --exclude='backups' \
  --exclude='data' \
  --exclude='.pytest_cache' \
  ./ root@178.105.160.62:/opt/studybuddy/
```

**Verify on server:**
```bash
cd /opt/studybuddy
git status  # Should be clean
ls -la | grep "docker-compose" | grep -v override  # Should see .yml files
```

### Phase 5: Configure Environment (5 min)
**Goal:** Generate production `.env` + `docker-compose.override.yml` with new secrets.

On server:

```bash
cd /opt/studybuddy

# === Create .env ===
cat > .env << 'ENVEOF'
# Database
POSTGRES_USER=studybuddy
POSTGRES_PASSWORD=CHANGE_ME_TO_STRONG_PASSWORD_12345
POSTGRES_DB=studybuddy
PGBOUNCER_USER=pgbouncer
PGBOUNCER_PASSWORD=CHANGE_ME_TO_STRONG_PGBOUNCER_PASSWORD

# Redis
REDIS_PASSWORD=CHANGE_ME_TO_STRONG_REDIS_PASSWORD

# Auth secrets (generate with: `openssl rand -hex 32`)
JWT_SECRET=CHANGE_ME_GENERATE_WITH_OPENSSL_RAND_HEX_32
ADMIN_JWT_SECRET=CHANGE_ME_GENERATE_WITH_OPENSSL_RAND_HEX_32

# Anthropic (if pipeline runs)
ANTHROPIC_API_KEY=

# Stripe (if payments enabled)
STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=

# Auth0 (if enabled)
AUTH0_DOMAIN=
AUTH0_CLIENT_ID=
AUTH0_CLIENT_SECRET=

# App config
NEXT_PUBLIC_API_URL=http://178.105.160.62/api
DEMO_CONTENT=true
ENVIRONMENT=production
ENVEOF

echo "✅ .env created. Edit secrets now:"
nano .env  # or vim .env

# === Create docker-compose.override.yml ===
cat > docker-compose.override.yml << 'OVERRIDEEOF'
services:
  api:
    environment:
      DATABASE_URL: postgresql://studybuddy:${POSTGRES_PASSWORD}@pgbouncer:5432/studybuddy
      REDIS_URL: redis://:${REDIS_PASSWORD}@redis:6379/0
  web:
    environment:
      NEXT_PUBLIC_API_URL: ${NEXT_PUBLIC_API_URL}
OVERRIDEEOF

# === Verify config ===
docker compose config --quiet && echo "✅ Config OK"
```

**Generate strong secrets:**
```bash
# On your local machine or server:
openssl rand -hex 32  # Run 2× for JWT_SECRET + ADMIN_JWT_SECRET
openssl rand -hex 16  # Run 2× for POSTGRES_PASSWORD + REDIS_PASSWORD
```

### Phase 6: Restore/Initialize Database (5–10 min)

#### Option A: Restore from Pre-cleanup Backup (Recommended)
Preserves all existing user data.

```bash
cd /opt/studybuddy

# Ensure DB is running
docker compose up -d db
sleep 3
docker compose exec -T db pg_isready -U studybuddy

# Restore snapshot
docker compose exec -T db psql -U studybuddy -d studybuddy < \
  backups/db-before-cleanup-LATEST.sql.gz

# Or if gzipped:
zcat backups/db-before-cleanup-LATEST.sql.gz | \
  docker compose exec -T db psql -U studybuddy -d studybuddy

# Verify
docker compose exec -T db psql -U studybuddy -d studybuddy -c "SELECT COUNT(*) as student_count FROM students;"
```

#### Option B: Fresh Start (Nuke Old Data)
Starts with empty database.

```bash
cd /opt/studybuddy

# Delete volumes (data lost)
docker volume rm studybuddy_postgres_data studybuddy_redis_data

# Start fresh
docker compose up -d db redis

# Wait for DB to initialize
sleep 5

# Run migrations
docker compose exec -e TEST_DB_URL= api alembic upgrade head

# (Optional) Seed demo admin
docker compose exec api python scripts/seed_super_admin.py
```

### Phase 7: Start Services (5 min)
**Goal:** Boot the full stack.

```bash
cd /opt/studybuddy

# Pull latest images (if using container registry)
docker compose pull

# Start all services
docker compose up -d

# Monitor startup
docker compose logs -f api web nginx

# Wait for healthchecks
sleep 10

# Verify health
curl -s http://localhost/health | jq .
docker compose ps  # All should show "Up"
```

**Expected logs:**
```
api-1 | INFO:     Application startup complete
web-1 | ready - started server on 0.0.0.0:3000, url: http://localhost:3000
nginx-1 | [notice] signal process started
```

### Phase 8: Verify E2E (5 min)
**Goal:** Confirm system works end-to-end.

```bash
# === Health probe ===
curl http://localhost/health

# === Database connectivity ===
docker compose exec -T db psql -U studybuddy -d studybuddy -c "SELECT version();"

# === Redis ===
docker compose exec redis redis-cli PING

# === Admin console (via SSH tunnel if needed) ===
# curl http://178.105.160.62/admin/login
# Login test (JWT validation)

# === Student portal ===
# curl http://178.105.160.62/
# Verify homepage loads

# === API routes ===
curl http://localhost/api/v1/health
curl http://localhost/api/v1/curriculum/grades

# === Check logs for errors ===
docker compose logs --since 2m | grep -i error
```

**Success criteria:**
- All containers show `Up`
- `/health` returns `200 OK`
- Database queries succeed
- No error logs in last 2 min

### Phase 9: Cleanup Old Artifacts (10 min)
**Goal:** Remove StudyBuddy v1 + stale backups.

Only after Phase 8 verification succeeds:

```bash
cd /opt/studybuddy

# === Remove old StudyBuddy version ===
rm -rf /opt/sb202609/

# === Remove old volume data (if safe) ===
docker volume rm sb_20609_postgres_data sb_20609_redis_data 2>/dev/null

# === Remove old demo volumes (if safe) ===
# docker volume rm studybuddy_demo_pgdata studybuddy_demo_redis

# === Remove old Mentible backups (unrelated project) ===
rm -rf /opt/mentible-old-20260918* /opt/mentible-old-20260919*

# === Clean dangling Docker images (CAREFUL: affects all projects) ===
# SAFER: Skip this step or do manually
# docker system prune -a --volumes --force

# === Archive old compose files (optional) ===
mkdir -p /opt/studybuddy/archive
mv /opt/studybuddy/docker-compose.demo.yml /opt/studybuddy/archive/ 2>/dev/null
mv /opt/studybuddy/docker-compose.host-db.yml /opt/studybuddy/archive/ 2>/dev/null
mv /opt/studybuddy/docker-compose.local.yml /opt/studybuddy/archive/ 2>/dev/null

# === Final verification ===
df -h  # Check disk space recovered
docker ps | grep -c studybuddy  # Should show 9 StudyBuddy containers

# === Tag cleanup completion ===
git tag -a "cleanup-complete-oct-2026" HEAD -m "Cleanup + redeployment complete"
git push --tags origin
```

---

## Rollback Strategy

If anything breaks post-cleanup:

### Level 1: Container Restart (Safe)
```bash
cd /opt/studybuddy
docker compose restart api web nginx
```

### Level 2: Full Stack Restart (Safe)
```bash
cd /opt/studybuddy
docker compose down
docker compose up -d
```

### Level 3: Restore Database Only (Safe)
Database + volumes preserved; code reverted.

```bash
cd /opt/studybuddy

# Stop services
docker compose down

# Restore DB from backup
docker compose up -d db
sleep 3
zcat backups/db-before-cleanup-LATEST.sql.gz | \
  docker compose exec -T db psql -U studybuddy -d studybuddy

# Restart
docker compose up -d
```

### Level 4: Full Rollback (Nuclear)
Revert code + restore database + volumes.

```bash
cd /opt/studybuddy

# Stop everything
docker compose down

# Revert code to pre-cleanup tag
git checkout before-cleanup-oct-2026

# Restore DB
docker compose up -d db
sleep 3
zcat backups/db-before-cleanup-LATEST.sql.gz | \
  docker compose exec -T db psql -U studybuddy -d studybuddy

# Restart with old code
docker compose up -d
```

**All pre-cleanup data is preserved.** Recovery is reversible up to Phase 9.

---

## Gotchas & Notes

### PgBouncer
- Already configured (commit da48cc3)
- `/opt/studybuddy/pgbouncer/` handles connection pooling
- Don't overwrite unless tuning pool size
- Credentials must match `postgres` service in compose

### Secrets
- Generate new JWT secrets for production (don't copy from localhost)
- Database password must be URL-safe (no special chars that break URIs)
- Store secrets in `.env`, never commit to git

### Redis Persistence
- Default: `appendonly no` (volatile, data lost on restart)
- Production: Set `appendonly yes` in compose for durability

### Anthropic API Key
- Pipeline fails silently if key missing
- Only required if running `build_grade.py` / `build_unit.py`
- Leave blank if pipeline disabled

### DNS & Routing
- No external domain needed
- Access via IP: `http://178.105.160.62`
- nginx reverse proxy (inside docker) routes port 80 → api:8000 + web:3000

### Other Projects
- **DO NOT** delete Mentible, Pramana, Agastya, Mambakkam, or Kaundinyalabs containers/volumes
- Each has isolated docker network
- No shared databases or caches

### Nginx Config
- Routes / → web:3000
- Routes /api/ → api:8000
- Config: `/opt/studybuddy/infra/nginx/nginx.dev.conf`
- No need to modify unless adding new routes

### Test DB URL
- Migrations: Must pass `-e TEST_DB_URL=` (targets test DB, not dev)
- Pytest: Must NOT pass `-e TEST_DB_URL=` (conftest downgrades production DB on exit)
- See CLAUDE.md pitfall #37 for why

---

## Time Estimate Summary

| Phase | Time | Activity |
|-------|------|----------|
| 1. Backup | 5 min | pg_dump + tar backup |
| 2. Stop | 3 min | docker compose down |
| 3. Clean | 2 min | rm artifacts |
| 4. Sync code | 10 min | rsync / git pull |
| 5. Config | 5 min | Generate .env + override |
| 6. DB restore | 5–10 min | pg_restore or fresh migrations |
| 7. Start | 5 min | docker compose up -d |
| 8. Verify | 5 min | curl + database checks |
| 9. Cleanup | 10 min | rm old artifacts |
| **TOTAL** | **50–60 min** | |
| **Downtime** | ~15 min | (Phases 2–7) |

---

## Execution Checklist

- [ ] Read this plan end-to-end
- [ ] Review Gotchas section
- [ ] SSH access confirmed
- [ ] Backup system available (restore scripts tested)
- [ ] Phase 1: Backup created + verified
- [ ] Phase 2: Services stopped cleanly
- [ ] Phase 3: Build artifacts removed
- [ ] Phase 4: Code synced (git or rsync)
- [ ] Phase 5: .env + override regenerated + secrets filled
- [ ] Phase 6: Database restored or initialized
- [ ] Phase 7: Full stack started
- [ ] Phase 8: E2E verification passed
- [ ] Phase 9: Old artifacts cleaned
- [ ] Git tags created (`before-cleanup` + `cleanup-complete`)

---

**Ready?** Execute phases sequentially, pausing between phases if needed. Downtime window is phases 2–7 (~15 min).
