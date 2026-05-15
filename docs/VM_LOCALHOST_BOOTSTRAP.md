# VM Localhost Bootstrap — StudyBuddy

**Purpose:** Stand up the full StudyBuddy stack on a fresh Linux VM as a
**localhost mirror** of the Saturday demo configuration. Same container
shape as the production demo (base `docker-compose.yml` + `docker-compose.demo.yml`),
but no domain, no TLS, no Cloudflare, and no third-party accounts
(Auth0/Stripe/SMTP/Sentry) required. All externals are stubbed.

**Companion to:**
- `scripts/demo/provision.sh` — production Hetzner second-tenant deploy (NOT this doc)
- `docs/DEMO_LAUNCH_PLAN.md` — production launch runbook (NOT this doc)

**Use this doc when:** you want a private, working copy of the demo stack
on your laptop / a private VM for testing, content authoring, or rehearsing
the Saturday demo without going public.

---

## TL;DR

```bash
# On the destination VM, as a sudo-capable NON-root user:
scp <THIS_REPO>/scripts/demo/vm-localhost-bootstrap.sh user@vm-ip:/tmp/

# On the VM:
GHCR_PAT=ghp_xxxxx bash /tmp/vm-localhost-bootstrap.sh
```

When it finishes, open `http://localhost:8443` on the VM (or SSH-tunnel
from your laptop). The install log captures every step start/success/failure
at `/tmp/studybuddy-bootstrap-<UTC-timestamp>.log` — quote it when reporting
issues.

---

## Prerequisites

- A fresh Linux VM running **Ubuntu**, **Debian**, or a derivative (Linux Mint,
  Pop!_OS, KDE Neon, MX Linux). The script auto-detects derivatives via
  `ID_LIKE` in `/etc/os-release` and uses the upstream Ubuntu/Debian repo.
- A sudo-capable **non-root** user. The script will refuse to run as root.
- ~6 GB RAM and ~20 GB free disk.
- **GitHub Personal Access Token** with `read:packages` scope.
  The StudyBuddy GHCR images (`ghcr.io/wegofwd2020-hub/studybuddy-{api,web}`)
  are private — you need a PAT to `docker login ghcr.io` before
  `docker compose pull` works.
  Generate at: <https://github.com/settings/tokens>
- (Optional) SSH access from the VM to your existing StudyBuddy dev machine,
  if you want to rsync real content (lessons, audio, visuals) over in the
  same bootstrap run.

---

## What the script does (8 steps)

| Step | What it does |
|---|---|
| **preflight** | Validates `IMAGE_STRATEGY`, `GHCR_PAT`, not running as root, sudo present |
| **1/8** | Installs Docker Engine + Compose v2 + git + rsync. Detects Mint/Pop/Neon and uses the upstream Ubuntu/Debian apt repo. |
| **2/8** | Clones the repo into `/opt/studybuddy`. If already cloned, attempts `git fetch + reset --hard`; continues with the existing checkout if offline. |
| **3/8** | **GHCR login** (Path A — pull strategy) or **Docker daemon DNS sanity check** (Path B — local build strategy) |
| **4/8** | Generates `.env.demo` with random secrets + stubbed Auth0/Stripe/SMTP values. Creates `.env` symlink, `web/.env.local` stub, patches `docker-compose.yml` to drop `pgbouncer` from depends-on anchors, writes `docker-compose.localhost.yml` with the three localhost-specific overrides (depends_on, python healthcheck, web volumes reset). |
| **5/8** | Creates the content-store directories at `/opt/studybuddy/content_store_data` and `/opt/studybuddy/data` with mode 777 (so the container's non-root user can write). |
| **6/8** | (Pull strategy only) `docker cp` extracts the prebuilt Next.js standalone `/app/server.js` from the GHCR web image into `/opt/studybuddy/web/`. This sidesteps a Compose volume-merge issue. |
| **7/8** | `docker compose pull && up -d`, waits 45s, verifies `/healthz`, runs `alembic upgrade head`, copies `seed.sh` into the api container, runs all 5 seed scripts. |
| **8/8** | (Optional, if `OLD_HOST` is set) rsyncs `content_store_data/` and `web/public/sample-visuals/` from the old machine to the correct bind targets on the VM. |

Every step prints `STEP_START`, `STEP_OK`, or `STEP_FAIL` to the install
log with a wall-clock timestamp, so you can grep through it after the
run to confirm what happened.

---

## Quick reference — environment variables

| Var | Purpose | Default |
|---|---|---|
| `LOG_FILE` | Where to write the install log (text) | `/tmp/studybuddy-bootstrap-<UTC-ts>.log` |
| `LOG_DIR` | Where to write the JSON deployment log | `/opt/studybuddy/logs` |
| `IMAGE_STRATEGY` | `pull` (GHCR) or `build` (local) | `pull` |
| `GHCR_PAT` | GitHub PAT with `read:packages` | **required if pull** |
| `GHCR_USER` | GitHub owner for images | `wegofwd2020-hub` |
| `OLD_HOST` | `user@host` for content rsync | empty (skips Step 8) |
| `OLD_REPO_DIR` | Absolute path to repo on old machine | **required if `OLD_HOST` set** |
| `REPO_URL` | Where to clone from | upstream `StudyBuddy_OnDemand` |
| `REPO_BRANCH` | Branch to clone | `main` |
| `INSTALL_DIR` | Where to put the repo | `/opt/studybuddy` |

---

## Two image strategies

### Path A — pull from GHCR (matches Saturday verbatim)

This is the default. Pulls pre-built `studybuddy-api:latest` and
`studybuddy-web:latest` from `ghcr.io/wegofwd2020-hub`. Requires a GitHub
PAT with `read:packages` scope. Fastest — no compilation needed on the VM.

```bash
GHCR_PAT=ghp_xxxxx bash /tmp/vm-localhost-bootstrap.sh
```

### Path B — build images locally

No GHCR auth needed, but you need a Docker daemon with working DNS
(otherwise `apt-get update` inside the build will fail with
`Temporary failure resolving 'deb.debian.org'`). The script runs a DNS
sanity check before committing to this path.

```bash
IMAGE_STRATEGY=build bash /tmp/vm-localhost-bootstrap.sh
```

Build takes ~5 minutes. Useful if you've made local changes to backend
or web code that you want to test in the demo configuration.

---

## Running with content rsync in one shot

If your old machine is reachable from the VM via SSH:

```bash
# On the VM:
GHCR_PAT=ghp_xxxxx \
OLD_HOST=siva@old-box-ip \
OLD_REPO_DIR=/home/siva/Documents/projects/AIStuff/STEM_studybuddy/StudyBuddy_OnDemand \
bash /tmp/vm-localhost-bootstrap.sh
```

This makes Step 8 rsync `content_store_data/` and `web/public/sample-visuals/`
from the old box into the VM's bind targets at `/opt/studybuddy/content_store_data/`
and `/opt/studybuddy/web/public/sample-visuals/`.

---

## After it finishes — smoke test + browser

```bash
# Stack state
COMPOSE="docker compose -f docker-compose.yml -f docker-compose.demo.yml -f docker-compose.localhost.yml --env-file .env.demo"
cd /opt/studybuddy
sudo $COMPOSE ps

# HTTP smoke
curl -sfI http://127.0.0.1:8443/healthz | head -3
curl -sfI http://127.0.0.1:8443/         | head -3
```

Browser:

- **From the VM directly:** open `http://localhost:8443`
- **From your laptop via SSH tunnel:**
  ```bash
  ssh -L 8443:127.0.0.1:8443 user@vm-ip
  # then on your laptop:
  open http://localhost:8443
  ```

---

## Demo personas

The seed scripts produce an `access_info.txt`-style summary on stdout
listing every account they create. Capture that output! The default seeded
identities:

### Super admin

| Login URL | Email | Password |
|---|---|---|
| `/admin/login` | `wegofwd2020@gmail.com` | (printed by `seed_super_admin.py`) |

### MilfordWaterford School (4 teachers, 16 students, 7 classrooms)

**Teachers (Grade 11 focus):**

| Email | Password | Classrooms |
|---|---|---|
| `sam.houston@milfordwaterford.edu` | `MWTeacher-Sam-2026!` | G8 STEM, G11 STEM |
| `warren.buffett@milfordwaterford.edu` | `MWTeacher-Warren-2026!` | G11 Commerce, G12 Commerce |
| `linda.ronstad@milfordwaterford.edu` | `MWTeacher-Linda-2026!` | G11 Science, G12 Science |
| `indra.nooyi@milfordwaterford.edu` | `MWTeacher-Indra-2026!` | G10 STEM |

**Grade 11 students** (a representative sample — the seed creates 7 G11 students total):

| Email | Password | Stream |
|---|---|---|
| `emma.thompson@milfordwaterford.edu` | `MWStudent-Emma-2026!` | G11 STEM |
| `david.chen@milfordwaterford.edu` | `MWStudent-David-2026!` | G11 STEM |
| `anya.iyer@milfordwaterford.edu` | `MWStudent-Anya-2026!` | G11 Commerce |
| `raj.kapoor@milfordwaterford.edu` | `MWStudent-Raj-2026!` | G11 Commerce |
| `mei.chen@milfordwaterford.edu` | `MWStudent-Mei-2026!` | G11 Commerce |
| `fatima.alhassan@milfordwaterford.edu` | `MWStudent-Fatima-2026!` | G11 Science |
| `liam.obrien@milfordwaterford.edu` | `MWStudent-Liam-2026!` | G11 Science |

All use `/signin` as the login URL.

### Phase A Dev School (local-auth testing)

| Login URL | Email | Password | Role |
|---|---|---|---|
| `/signin` | `admin@devschool.dev` | `DevAdmin1234!` | school admin |
| `/signin` | `teacher@devschool.dev` | `DevTeacher1234!` | teacher |
| `/signin` | `student@devschool.dev` | `DevStudent1234!` | student G8 |

A second school (`devschoolb.dev` with `…B1234!` passwords) is also seeded
for multi-tenant testing.

### Public "request demo via email" flow (the test-run router)

Located at `backend/src/demo/test_run_router.py`. The marketing site's
"Try a test run" widget submits an email → emails a verification link →
on click, auto-provisions BOTH a teacher and a student account at
**Grade 11 Science, MilfordWaterford** with random passwords (emailed
back to the visitor).

This is the path subscribers see when they request a demo via email.

### Persistent test account (no email needed)

| Login URL | Email | Password |
|---|---|---|
| `/signin` | `demo-test@studybuddy.dev` | `DemoTest-2026!` |

Grade 8 student. TTL 30 days from last seed run.

---

## The install log

Default path: `/tmp/studybuddy-bootstrap-<UTC-timestamp>.log`. Override
with `LOG_FILE=/path/to/file.log`.

Everything (info/warn/step output PLUS every command's stdout+stderr)
goes to both terminal and log. ANSI color codes are stripped from the
log copy. Structured markers make it greppable:

```bash
grep -E "STEP_(START|OK|FAIL)" /tmp/studybuddy-bootstrap-*.log
# STEP_START [17:23:01Z] preflight  Validate config
# STEP_OK    [17:23:01Z] preflight  Validate config
# STEP_START [17:23:01Z] 1/8  Install Docker, git, rsync
# STEP_OK    [17:23:18Z] 1/8  Install Docker, git, rsync
# ...
```

On any command failure under `set -e`, the ERR trap fires and prints
the failing step name, exit code, and the last 25 log lines, then exits
non-zero. The full log path is printed too — quote it when reporting
issues.

---

## The JSON deployment log

Alongside the text log, every run writes a structured JSON file with one
entry per step. Same shape as mambakkam-net's `scripts/launch/_log.sh`
output — so any downstream tooling (Promtail/Loki, dashboards, grep+jq)
treats both deployments uniformly.

Default path: `/opt/studybuddy/logs/vm-localhost-bootstrap-<UTC-timestamp>.json`,
plus a `vm-localhost-bootstrap-latest.json` symlink that always points at
the most recent run. Override the directory with `LOG_DIR=/path/to/dir`.

Shape:

```json
{
  "script": "vm-localhost-bootstrap",
  "host": "studybuddy",
  "image_strategy": "pull",
  "started_at": "2026-05-15T18:13:01Z",
  "finished_at": "2026-05-15T18:18:42Z",
  "duration_ms": 341000,
  "exit_code": 0,
  "steps": [
    {"name": "preflight  Validate config",
     "status": "Success",
     "started_at": "...", "finished_at": "...", "duration_ms": 12},
    {"name": "7/8  Bring stack up + migrations + seed",
     "status": "Error",
     "error": "exit 1; tail of /tmp/studybuddy-bootstrap-...log: ...",
     "started_at": "...", "finished_at": "...", "duration_ms": 287530}
  ]
}
```

The file is written atomically (tmp + mv) on the EXIT trap, so it always
lands intact even if the script aborts mid-step. An unfinished step at
script exit is auto-finalised as `Error` with the message
`"script exited (code=N) before step finished"`.

Quick queries:

```bash
# What step failed, on the latest run?
jq '.steps[] | select(.status == "Error")' \
  /opt/studybuddy/logs/vm-localhost-bootstrap-latest.json

# Total wall-clock time per step, sorted descending (find the slow ones)
jq -r '.steps[] | [.duration_ms, .name] | @tsv' \
  /opt/studybuddy/logs/vm-localhost-bootstrap-latest.json | sort -rn

# Compare run-time of the last 5 deployments
ls -t /opt/studybuddy/logs/vm-localhost-bootstrap-2*.json | head -5 \
  | xargs -I{} jq -r '[.started_at, .duration_ms, .exit_code] | @tsv' {}
```

---

## Six gotchas the script handles for you

These are the issues that turn into a multi-hour debugging session if
you bring up the stack manually. Listed here so you understand what the
script is doing.

1. **GHCR images are private.** The `studybuddy-api` and `studybuddy-web`
   packages on `ghcr.io/wegofwd2020-hub` return HTTP 401 to unauthenticated
   pulls. Need `docker login ghcr.io` with a `read:packages` PAT.

2. **Base compose's YAML anchors reference `pgbouncer`.** `x-depends-infra`
   and `x-depends-all` both include a `pgbouncer:` entry. The demo override
   puts `pgbouncer` behind `profiles: ["never"]`, but Compose validation
   on versions <2.21 still rejects `service "api" depends on undefined
   service "pgbouncer"`. The script surgically removes those two entries
   from the anchors (Python in-place edit; backup at `docker-compose.yml.bak`).

3. **Compose `depends_on` deep-merges.** A sidecar override file CAN'T
   remove `pgbouncer` from the merged result — it can only add keys.
   That's why we have to edit the source anchors (#2).

4. **Bind targets for `/data/content` are `/opt/studybuddy/content_store_data`
   on the host, not `/data/content`.** The base compose's `./content_store_data:/data/content`
   volume wins; the demo override doesn't reset it on migrate/api/celery.
   The container's non-root UID rarely matches the host user, so the
   directory needs `chmod 777` for `seed_dev_content.py` to write into it.

5. **The api image has no `curl`.** The base/demo healthcheck
   `["CMD", "curl", "-f", "..."]` always fails — web/nginx wait forever
   on `condition: service_healthy`. The localhost override replaces it
   with a `python urllib.request` probe.

6. **The web service bind-mounts `./web:/app` over the prebuilt Next.js
   standalone image,** hiding `/app/server.js`. Web crash-loops with
   `MODULE_NOT_FOUND`. The fix: `docker cp` the image's `/app` contents
   onto the host `web/` directory in Step 6, so the bind mount serves
   the prebuilt code. (We also set `volumes: []` on web in the localhost
   override, but Compose's volume-merge semantics are inconsistent across
   versions, so the `docker cp` is the load-bearing fix.)

---

## Troubleshooting

### "Could not resolve host: github.com" / DNS broken on the VM

```bash
# Disable systemd-resolved permanently
sudo systemctl disable --now systemd-resolved
sudo systemctl mask systemd-resolved

# Replace /etc/resolv.conf with a static immutable file
sudo rm -f /etc/resolv.conf
sudo tee /etc/resolv.conf >/dev/null <<'EOF'
nameserver 1.1.1.1
nameserver 8.8.8.8
EOF
sudo chattr +i /etc/resolv.conf

# Tell Docker daemon to use public DNS for container traffic too
sudo mkdir -p /etc/docker
sudo tee /etc/docker/daemon.json >/dev/null <<'EOF'
{ "dns": ["1.1.1.1", "8.8.8.8"] }
EOF
sudo systemctl restart docker

# Verify
getent hosts github.com
sudo docker run --rm alpine:latest nslookup ghcr.io
```

### "service \"X\" depends on undefined service \"pgbouncer\""

The base compose anchor patch didn't apply. Check whether the patch
ran correctly:

```bash
grep -A8 "^x-depends-all:" /opt/studybuddy/docker-compose.yml
# Should show db, redis, migrate — NO pgbouncer
```

If pgbouncer is still there, re-run the patch manually:

```bash
sudo sed -i '/^  pgbouncer:$/{N;/condition: service_\(healthy\|started\)/d}' \
  /opt/studybuddy/docker-compose.yml
```

### Migrate exits 1 with `PermissionError: '/data/content/curricula'`

The chmod went to the wrong path. The container's `/data/content` is
actually `/opt/studybuddy/content_store_data` on the host:

```bash
sudo chmod -R 777 /opt/studybuddy/content_store_data /opt/studybuddy/data
cd /opt/studybuddy
COMPOSE="docker compose -f docker-compose.yml -f docker-compose.demo.yml -f docker-compose.localhost.yml --env-file .env.demo"
sudo $COMPOSE up -d
```

### api is unhealthy / web returns 502

```bash
# Was the image's prebuilt /app extracted onto the host?
ls -la /opt/studybuddy/web/server.js
```

If `server.js` is missing, extract it:

```bash
sudo docker create --name temp-web ghcr.io/wegofwd2020-hub/studybuddy-web:latest
sudo docker cp temp-web:/app/. /opt/studybuddy/web/
sudo docker rm temp-web

cd /opt/studybuddy
sudo docker compose -f docker-compose.yml -f docker-compose.demo.yml -f docker-compose.localhost.yml --env-file .env.demo up -d --force-recreate web
```

### Other failures

Run the script with logging enabled (it always is) and quote the log
path printed in the FATAL banner. Useful greps:

```bash
# What step failed?
grep "STEP_FAIL" /tmp/studybuddy-bootstrap-*.log

# Last 50 lines before failure
tail -n 50 /tmp/studybuddy-bootstrap-*.log

# Search for a specific error
grep -i "error\|fail\|denied" /tmp/studybuddy-bootstrap-*.log | head
```

---

## Resetting / teardown

### Stop the stack, keep data

```bash
cd /opt/studybuddy
sudo docker compose -f docker-compose.yml -f docker-compose.demo.yml -f docker-compose.localhost.yml --env-file .env.demo stop
```

### Stop the stack, wipe the DB

```bash
cd /opt/studybuddy
sudo docker compose -f docker-compose.yml -f docker-compose.demo.yml -f docker-compose.localhost.yml --env-file .env.demo down -v
```

### Full nuke (start over from the bootstrap)

```bash
cd /opt/studybuddy
sudo docker compose -f docker-compose.yml -f docker-compose.demo.yml -f docker-compose.localhost.yml --env-file .env.demo down -v
sudo rm -rf /opt/studybuddy
sudo rm -rf /data/content /data/sample-visuals
# Then re-run the bootstrap from /tmp/
GHCR_PAT=ghp_xxxxx bash /tmp/vm-localhost-bootstrap.sh
```

---

## Companion: `scripts/sync_repos.py`

Mirrors every repo under `github.com/wegofwd2020-hub` (or whatever
`SYNC_REPOS_OWNER` is set to) into a local directory. Useful for keeping
sibling projects (`mambakkam-net`, `studybuddy-docs`, etc.) in sync next
to `StudyBuddy_OnDemand`.

```bash
# Default — clones/pulls all org repos as siblings of THIS repo
python3 scripts/sync_repos.py

# Custom destination
SYNC_REPOS_ROOT=/srv/repos python3 scripts/sync_repos.py

# Different org
SYNC_REPOS_OWNER=anthropics python3 scripts/sync_repos.py

# Higher rate limit / private repos
GITHUB_TOKEN=ghp_xxxxx python3 scripts/sync_repos.py
```

The script skips local directories with uncommitted changes (warns,
doesn't touch them). Uses SSH by default (`CLONE_PROTO=https` to switch).

---

## Related artifacts

| File | Purpose |
|---|---|
| `scripts/demo/vm-localhost-bootstrap.sh` | The bootstrap script this doc describes |
| `scripts/demo/provision.sh` | Production Hetzner second-tenant deploy (different target) |
| `scripts/demo/seed.sh` | Demo data seed orchestrator (run by Step 7 inside the api container) |
| `scripts/demo/smoke.sh` | Post-deploy smoke checks (run manually after bootstrap finishes) |
| `scripts/sync_repos.py` | GitHub-org repo sync helper |
| `docker-compose.yml` | Base compose (modified by bootstrap: pgbouncer removed from anchors) |
| `docker-compose.demo.yml` | Saturday demo override (image: pulls + drop services) |
| `docker-compose.localhost.yml` | Generated by bootstrap: localhost-specific overrides |
| `docs/DEMO_LAUNCH_PLAN.md` | Production Saturday launch runbook (NOT this doc) |
| `docs/DEMO_HOSTING_READINESS.md` | One-page status snapshot of production demo readiness |
| `backend/src/demo/test_run_router.py` | Public "request demo via email" flow — defaults to Grade 11 Science at MilfordWaterford |
