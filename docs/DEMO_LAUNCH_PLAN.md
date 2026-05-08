# Demo Hosting — Launch Plan (target: 2026-05-16)

**Audience:** Sivakumar (operator) · future on-call deputy
**Document type:** End-to-end runbook from "today's main branch" → "live demo on `demo.studybuddy.app`"
**Companion docs:** [`studybuddy-docs/docs/dev/DEMO_HOSTING_GUIDE.md`](https://github.com/wegofwd2020-hub/studybuddy-docs/blob/docs/demo-walkthrough/docs/dev/DEMO_HOSTING_GUIDE.md) (Hetzner-based architecture) · [`studybuddy-docs/docs/dev/DEMO_WALKTHROUGH.md`](https://github.com/wegofwd2020-hub/studybuddy-docs/blob/docs/demo-walkthrough/docs/dev/DEMO_WALKTHROUGH.md) (click-by-click demo script) · [`studybuddy-docs/docs/operations/dns-and-email-setup.md`](https://github.com/wegofwd2020-hub/studybuddy-docs/blob/docs/demo-walkthrough/docs/operations/dns-and-email-setup.md) (domain registration + Cloudflare DNS + Zoho Mail step-by-step) · [`studybuddy-docs/docs/dev/DEV_ACCOUNTS.md`](https://github.com/wegofwd2020-hub/studybuddy-docs/blob/main/docs/dev/DEV_ACCOUNTS.md) (account inventory)

---

## Timeline at a Glance

```
May 8  (Thu) ──┐
May 9  (Fri)   │  CODE FREEZE PHASE — automation + last-mile fixes
May 10 (Sat)   │
May 11 (Sun)   │
May 12 (Mon) ──┤◀─── code-freeze cutoff (no app changes after EOD)
May 13 (Tue)   │
May 14 (Wed)   │  TEST PHASE — staging deploy + persona walkthroughs
May 15 (Thu)   │
May 16 (Fri) ──┴◀─── LAUNCH DAY · DNS cutover · announcement
```

Eight calendar days from today (2026-05-08) to launch.

---

## §1 · What to Complete Before May 12 (4 days, code-freeze cutoff)

Three categories: **automation** (must), **content** (must), **polish** (nice-to-have if time permits).

### 1.A Automation — must-have for May 16 (this commit ships them)

These ship with this PR. Use them as-is; no further code work needed.

| Deliverable | File | Purpose |
|---|---|---|
| Demo Compose override | [`docker-compose.demo.yml`](../docker-compose.demo.yml) | Production-shaped: drops PgBouncer + Beat-standby + stripe-cli, adds Nginx, persistent named volumes, `restart: always` on every service |
| First-time provisioning | [`scripts/demo/provision.sh`](../scripts/demo/provision.sh) | Idempotent Hetzner CX22 bootstrap — apt, ufw, fail2ban, Docker install, repo clone, .env.demo skeleton |
| Seeding orchestrator | [`scripts/demo/seed.sh`](../scripts/demo/seed.sh) | Runs the 5 demo seed scripts in dependency order (super_admin → milfordwaterford → demo_test_account → phase_a_dev → content_db) |
| Post-deploy smoke check | [`scripts/demo/smoke.sh`](../scripts/demo/smoke.sh) | Curl-based: `/healthz`, login as 4 persona types, fetch one lesson + one quiz, exit 1 on any 4xx/5xx |
| Daily DB + content backup | [`scripts/demo/backup.sh`](../scripts/demo/backup.sh) | `pg_dump` compressed + `rsync` content_store to local backup dir; retains last 7 days; cron-friendly |
| Auto-deploy on merge to main | [`.github/workflows/deploy-demo.yml`](../.github/workflows/deploy-demo.yml) | Build → GHCR push → SSH to Hetzner → `docker compose pull && up -d` → smoke test |

### 1.A.bis Domain + Email — must-have

These are out-of-repo deliverables (DNS + Zoho), so they don't ship in
this commit, but they're required for the May 16 cutover. Step-by-step
in [`studybuddy-docs/docs/operations/dns-and-email-setup.md`](https://github.com/wegofwd2020-hub/studybuddy-docs/blob/docs/demo-walkthrough/docs/operations/dns-and-email-setup.md).

Track each by ticking the checkbox; the "Verify by" column is the
green-light command/check.

#### Phase 1 — Domain registration (~15 min)

- [ ] Domain registered (Cloudflare Registrar — `studybuddy.app` recommended)
  · *verify:* `dig NS studybuddy.app` returns Cloudflare nameservers (`*.ns.cloudflare.com`)

#### Phase 2 — Cloudflare DNS for `demo.studybuddy.app` (~10 min)

- [ ] A record `demo` → VPS public IP, **Proxied** (orange cloud)
  · *verify:* `dig demo.studybuddy.app +short` returns a Cloudflare-edge IP (104.21.x.x or 172.67.x.x), **NOT** the raw VPS IP
- [ ] SSL/TLS mode set to **Full (strict)**; **Always Use HTTPS** toggled on
  · *verify:* `curl -vI https://demo.studybuddy.app` shows a valid Cloudflare-edge TLS cert + 200/301 response
- [ ] Cloudflare Origin Certificate generated; cert + key installed at `/etc/ssl/cloudflare/origin-{cert,key}.pem` on the VPS
  · *verify:* nginx container starts cleanly; `curl https://demo.studybuddy.app/healthz` returns 200 with `db:ok`
- [ ] Pre-launch (May 15 EOD): TTL on the `demo` A record lowered to 300s
  · *verify:* Cloudflare DNS UI shows "TTL: 5 min" instead of "Auto"

#### Phase 3 — Zoho Mail free-tier (~30 min)

- [ ] Zoho Mail account created; domain verification TXT record added to Cloudflare DNS
  · *verify:* `dig TXT studybuddy.app +short` shows `zoho-verification=zb...`
- [ ] Two mailboxes live: `support@studybuddy.app`, `sales@studybuddy.app`
  · *verify:* Send a test from each via Zoho webmail to your personal Gmail; reply arrives back in Zoho
- [ ] MX records (mx.zoho.com priorities 10/20/50) added to Cloudflare DNS
  · *verify:* `dig MX studybuddy.app +short` lists `mx.zoho.com`, `mx2.zoho.com`, `mx3.zoho.com`
- [ ] SPF record `v=spf1 include:zoho.com ~all` added (single TXT at apex)
  · *verify:* `dig TXT studybuddy.app +short | grep spf1` returns the record
- [ ] DKIM record `zmail._domainkey` added with the Zoho-supplied public key
  · *verify:* All three (MX, SPF, DKIM) show green checkmarks in Zoho's verification UI
- [ ] DMARC record `_dmarc` added with `v=DMARC1; p=quarantine; rua=mailto:support@...`
  · *verify:* `dig TXT _dmarc.studybuddy.app +short` returns the policy

#### Phase 4 — Gmail send-as (~15 min)

- [ ] Zoho App Password generated for the Gmail integration (NOT the regular Zoho login password)
  · *verify:* App Password copied to a password manager (one-time display from Zoho)
- [ ] `support@studybuddy.app` added as a send-as identity in Gmail (SMTP `smtp.zoho.com:465`, SSL on)
  · *verify:* Compose new mail in Gmail, From dropdown shows `StudyBuddy Support <support@studybuddy.app>`
- [ ] (Optional) `sales@studybuddy.app` added as a second send-as identity
  · *verify:* same check for the sales address

#### Phase 5 — Wire SMTP into the app (~5 min)

- [ ] `.env.demo` SMTP block updated to Zoho values (`SMTP_HOST=smtp.zoho.com`, `SMTP_PORT=465`, `SMTP_USER=support@studybuddy.app`, `SMTP_PASSWORD=<app-password>`, `SMTP_USE_SSL=true`)
  · *verify:* `docker compose exec api env | grep SMTP` shows the new values
- [ ] api + celery-worker restarted to pick up the new env
  · *verify:* `docker compose ps` shows recent restart timestamps
- [ ] App-originated email arrives from the custom domain
  · *verify:* Trigger a forgot-password from a demo student; the reset email arrives From `StudyBuddy <support@studybuddy.app>`

### 1.B Content — must-have

The pipeline runs offline and outputs are pushed to the demo VPS. No `ANTHROPIC_API_KEY` lives on the demo box.

| Item | Owner | Verify by |
|---|---|---|
| **Grade 8 STEM** content built (en) — Sam Jr, Jose Herbert | Operator | `ls sample_content/g8-stem/G8-MATH-001/` non-empty; `meta.json` shows `model: claude-sonnet-4-6` |
| **Grade 10 STEM** content built (en) — Priya, Carlos | Operator | same check on `g10-stem/` |
| **Grade 11 STEM** content built (en) — Emma, David | Operator | same on `g11-stem/` |
| **Grade 11 Commerce** content built (en) — Anya, Raj, Mei | Operator | same on `g11-science/G11-ACC-001` (real Commerce content for Anya) |
| **Grade 11 Science** content built (en) — Fatima, Liam | Operator | same on `g11-science/G11-PHYS-002` etc. |
| **Grade 12 Commerce** content built (en) — Isabella, James | Operator | same on `g12-commerce/` |
| **Grade 12 Science** content built (en) — Sam Sr, Linda | Operator | same on `g12-science/` |
| Pipeline output uploaded to demo VPS | CI (deploy workflow) | `ssh demo 'ls /opt/studybuddy/content_store/'` shows current set |

**One-time cost** to build all of the above: ~$215 (per `studybuddy-docs/COST_PLAN.md`). Already partially built; finish gaps locally before May 12.

### 1.C Polish — nice-to-have (skip if blocking)

| Item | Effort | Skip if |
|---|---|---|
| Fix 2 outstanding migration table entries (0056, 0057 in CLAUDE.md) | 5 min | Never skip — already in this PR |
| Custom branded 404 + 500 error pages | 1 hour | Default Next.js pages are acceptable for demo |
| `demo.studybuddy.app` favicon + Apple touch icon | 30 min | Browser-default favicon is acceptable |
| Demo banner ("This is a demo — content resets nightly") | 30 min | Useful but not critical |
| Status page (Cloudflare Workers) | 2 hours | Can be added post-launch |
| Sentry environment tag = `demo` | 15 min | Should ship — single env var change |

### 1.D Definition of "Done" for May 12 EOD

A green checkbox on each of these means we enter the test phase clean:

- [ ] All Tier-1.A automation deliverables in `main`
- [ ] All Tier-1.A.bis Domain + Email phases 1–5 ticked (every checkbox in §1.A.bis above is green)
- [ ] All Tier-1.B content built and the catalogue pushed to a staging directory
- [ ] `python3 scripts/doc_audit/run_all.py` exits clean (zero drift)
- [ ] `bun run typecheck` (web) + `pytest` (backend) green on `main`
- [ ] One **complete dry-run on a throwaway Hetzner VPS** (cheaper than figuring out failures live on May 16): provision → seed → smoke → tear down — including the DNS + email phases against a throwaway subdomain (e.g. `dryrun.studybuddy.app`)

---

## §2 · May 16 Launch-Day Runbook

**Prerequisite checks the day before (May 15 EOD):**
- DNS pre-staged at Cloudflare (lower TTL to 300s a day in advance)
- Hetzner production VPS provisioned (run `scripts/demo/provision.sh` on a fresh box ≥ 24h before launch)
- All Tier-1.B content uploaded
- `.env.demo` populated with real Auth0 / Stripe-test / Gmail / JWT secrets
- SSH key for `deploy@demo` registered as a GitHub repo secret

**Launch day timing (EST; adjust as needed):**

| Time | Action | Owner | Pass criterion |
|---|---|---|---|
| **T-2h** (07:00) | Pre-flight: `ssh demo 'docker compose ps'` shows all 7 services healthy | Operator | All `Up (healthy)` |
| T-2h (07:05) | Run `scripts/demo/smoke.sh` against staging URL | Operator | Exit 0; all checks pass |
| T-1h (08:00) | Final content sync from local pipeline output | Operator | `rsync` reports zero deltas |
| T-1h (08:05) | DNS cutover: `demo.studybuddy.app` A-record → demo VPS public IP | Operator | `dig +short demo.studybuddy.app` returns the new IP |
| T-30m (08:30) | Re-run `smoke.sh` against the **public domain** | Operator | Exit 0 |
| T-15m (08:45) | Post-cutover persona walkthrough — 5 minutes per persona | Operator | All 5 personas can log in and reach their dashboard |
| T-0 (09:00) | **GO LIVE** — share `https://demo.studybuddy.app` link to the announcement channel | Operator | Announcement sent |
| T+30m (09:30) | First user telemetry check — Sentry, FastAPI request log | Operator | No 5xx in logs; no Sentry errors above warning level |
| T+2h (11:00) | First DB backup runs (cron `0 11 * * *`) | Auto | Backup file present in `/opt/studybuddy/backups/` |
| T+4h (13:00) | First post-launch incident review (even if uneventful) | Operator | Notes captured for retrospective |

**Rollback plan (if smoke fails after cutover):**

1. Revert DNS at Cloudflare to the old IP / staging domain (fastest; <60s TTL kicks in within 5 min)
2. `ssh demo 'cd /opt/studybuddy && git checkout <previous-tag> && docker compose --env-file .env.demo up -d'`
3. Re-run smoke; if green, post a status update and investigate the breaking change post-mortem
4. If DB migration is the blocker: `alembic downgrade -1` rolls back the last migration

**On-call duties (T+0 → T+24h):**
- Watch Sentry every 30 min for the first 4 hours
- Check `docker compose logs` for any non-INFO log line
- Respond to first user feedback within 1 hour during business hours

---

## §2.5 · Deployment Sequence (consolidated)

The deployment story has **two distinct sequences** the operator must keep
separate in their head:

- **Cold start** — done once during the May 14–15 staging dry-run and again
  on/around May 15 when the production demo VPS is provisioned. Manual
  steps; the operator drives.
- **Ongoing deploy** — fires automatically on every merge to `main` after
  initial cold-start. CI drives; operator only intervenes on failure.

### Sequence A — Cold start (manual; ~30 minutes the first time)

Run this when standing up either the staging or production demo VPS from
nothing.

```
┌──────────────────────────────────────────────────────────────────────┐
│  Operator action                                                      │
└──────────────────────────────────────────────────────────────────────┘

  1. Provision Hetzner CX22                                           [~3 min]
     Hetzner console → + Add Server → CX22 + Ubuntu 22.04 + SSH key.
     Note the public IP.

  2. SSH in + run provision.sh                                        [~5 min]
     ssh root@<public-ip>
     curl -fsSL https://raw.githubusercontent.com/wegofwd2020-hub/StudyBuddy_OnDemand/main/scripts/demo/provision.sh \
       | bash
     Installs Docker, UFW, fail2ban, clones repo, creates `deploy` user,
     drops .env.demo skeleton, sets up daily-backup cron.

  3. Populate .env.demo                                               [~5 min]
     Replace 5 placeholder secrets via `openssl rand -hex 32`
     Paste Auth0 + Stripe-test + Gmail App Password values.

  4. Paste Cloudflare Origin Cert                                     [~2 min]
     /etc/ssl/cloudflare/origin-cert.pem
     /etc/ssl/cloudflare/origin-key.pem

  5. Paste GH Actions deploy SSH pubkey                               [~1 min]
     /home/deploy/.ssh/authorized_keys
     (matching private key → repo secret DEMO_VPS_SSH_KEY)

  6. Upload pre-built content from dev machine                        [~5 min]
     rsync -avz ./content_store/ deploy@<vps-ip>:/data/content/

┌──────────────────────────────────────────────────────────────────────┐
│  Container startup (docker compose handles dependencies)              │
└──────────────────────────────────────────────────────────────────────┘

  7. docker compose pull (fetch images from GHCR)                     [~3 min]
     cd /opt/studybuddy
     docker compose -f docker-compose.yml -f docker-compose.demo.yml \
       --env-file .env.demo pull

  8. docker compose up -d                                             [~2 min]
     Same flags as step 7, with `up -d`.

     Healthcheck-gated startup order:
     ┌─ db (postgres)            healthcheck: pg_isready
     ├─ redis                    healthcheck: redis-cli ping
     │     ↓ (db + redis healthy)
     ├─ migrate (one-shot)       runs alembic upgrade head, exits cleanly
     │     ↓ (migrate exits with code 0)
     ├─ api                      healthcheck: GET /healthz returns 200
     ├─ celery-worker            depends on migrate completion
     ├─ celery-beat-primary      depends on migrate completion
     │     ↓ (api healthy)
     ├─ web                      depends on api healthcheck
     │     ↓ (api + web ready)
     └─ nginx                    fronts api + web on :80 + :443

  9. seed.sh — populate demo accounts + content rows                  [~3 min]
     docker compose exec api bash /app/scripts/demo/seed.sh
     Idempotent. Runs:
       seed_super_admin → seed_demo_milfordwaterford →
       seed_demo_test_account → seed_phase_a_dev → seed_dev_content

 10. smoke.sh — validate end-to-end                                   [~30 sec]
     bash scripts/demo/smoke.sh https://<vps-ip>
     (use IP first; switch to domain after step 11.)

┌──────────────────────────────────────────────────────────────────────┐
│  Make it public                                                       │
└──────────────────────────────────────────────────────────────────────┘

 11. Cloudflare DNS A record → VPS public IP                          [~3 min]
     Cloudflare dashboard → demo.studybuddy.app → A record.
     SSL/TLS mode: Full (strict).
     Set TTL to 300s in advance of any future cutover.

 12. smoke.sh against the public domain                               [~30 sec]
     bash scripts/demo/smoke.sh https://demo.studybuddy.app
     Cold-start complete when this exits 0.
```

**Total cold-start time:** ~30 minutes for a calm operator with all secrets
already in hand.

### Sequence B — Ongoing deploy (automatic; ~5 minutes per merge)

Fires on every push to `main` via `.github/workflows/deploy-demo.yml`.
No operator action unless the smoke check fails.

```
┌──────────────────────────────────────────────────────────────────────┐
│  GitHub Actions                                                       │
└──────────────────────────────────────────────────────────────────────┘

  1. Push lands on main                                               [event]

  2. test.yml runs first (separate workflow)                          [~3 min]
     Backend lint + pytest + web typecheck + Playwright smoke.
     deploy-demo.yml does NOT wait on test.yml today — the operator
     should ensure tests pass before merging. (Optional future
     enhancement: gate deploy on test.yml success via workflow_run.)

  3. deploy-demo.yml triggered                                        [event]

  4. Build api + web images (parallel)                                [~3 min]
     docker buildx build with GHA cache.

  5. Push images to GHCR                                              [~30 sec]
     Tagged :latest and :<short-sha> for every build.

┌──────────────────────────────────────────────────────────────────────┐
│  Demo VPS                                                             │
└──────────────────────────────────────────────────────────────────────┘

  6. SSH to VPS as deploy@DEMO_VPS_HOST                              [~1 sec]
     Uses DEMO_VPS_SSH_KEY repo secret.

  7. sudo git -C /opt/studybuddy pull origin main                     [~2 sec]
     Picks up any new docker-compose.demo.yml / scripts/demo/* changes.

  8. docker compose pull                                              [~30 sec]
     Pulls the new :latest images for api, web (other services
     unchanged — same compose pull is idempotent).

  9. docker compose up -d --remove-orphans                            [~30 sec]
     Rolling restart. Containers that match old image:
     ├─ db, redis            no restart (image unchanged)
     ├─ migrate              re-runs alembic upgrade head — idempotent;
     │                        exits 0 quickly if at head
     ├─ api (NEW IMAGE)      old api drains, new api starts;
     │                        nginx routes to new once healthcheck OK
     ├─ celery-worker        rolling restart
     ├─ celery-beat-primary  rolling restart
     ├─ web (NEW IMAGE)      old web drains, new web starts
     └─ nginx                no restart needed (proxies to internal DNS)

 10. Wait 30 seconds                                                  [~30 sec]
     Healthchecks settle. nginx upstream resolution catches up.

 11. scripts/demo/smoke.sh https://<DEMO_VPS_HOST>                    [~30 sec]
     9 checks (healthz, readyz, 3 logins, lesson, quiz, /, /demo).
     Run from the GH Actions runner, not the VPS.

 12a. (Smoke green)
      Step summary posted to the GH Actions UI. Done.

 12b. (Smoke fails)
      Auto-creates GitHub issue tagged `incident:demo` + `priority:high`
      with the workflow-run URL and a triage checklist.
      **Auto-rollback is intentionally NOT wired** — operator must
      review logs and decide.
```

**Total auto-deploy time:** ~5 minutes from `git push` to live on demo URL.

### Healthcheck dependency graph (runtime, both sequences)

```
                         ┌────────┐
                         │   db   │  pg_isready
                         └────┬───┘
                              │ healthy
                  ┌───────────┴───────────┐
                  ▼                       ▼
            ┌──────────┐            ┌────────────┐
            │  redis   │            │  migrate   │
            │ (ping)   │            │ (one-shot) │
            └────┬─────┘            └──────┬─────┘
                 │ healthy                 │ exit 0
                 └────────────┬────────────┘
                              ▼
                   ┌──────────┴──────────────┬──────────────────┐
                   ▼                         ▼                  ▼
            ┌──────────┐              ┌─────────────┐    ┌─────────────┐
            │   api    │              │  celery-    │    │  celery-    │
            │ /healthz │              │   worker    │    │ beat-primary│
            └────┬─────┘              └─────────────┘    └─────────────┘
                 │ healthy
                 ▼
            ┌──────────┐
            │   web    │
            │  Next.js │
            └────┬─────┘
                 │ ready
                 ▼
            ┌──────────┐
            │  nginx   │  exposes :80 + :443
            └──────────┘
```

`docker-compose.demo.yml` keeps the same dependency graph as the local-dev
compose; only the **services on the graph** change (PgBouncer + celery-pipeline +
celery-beat-standby are dropped, nginx is added).

### Rollback paths

| When | Mechanism | Time to recover |
|---|---|---|
| Smoke fails after auto-deploy | Operator manually rolls back per issue triage: `ssh demo 'cd /opt/studybuddy && sudo git -C /opt/studybuddy reset --hard <previous-sha> && sudo docker compose --env-file .env.demo up -d'` | ~5 min |
| Bad migration on auto-deploy | `docker compose exec api alembic downgrade -1` then redeploy with the migration reverted in code | ~10 min |
| VPS itself unhealthy on launch day | DNS revert at Cloudflare to staging IP; investigate VPS post-mortem (TTL=300s set on May 15 means propagation ≤5 min) | ~5 min |
| Breaking customer issue mid-demo (catastrophic) | Cloudflare → DNS → set demo.studybuddy.app to "under maintenance" page hosted on Cloudflare Pages | ~2 min |

### When NOT to follow Sequence B

There are three cases where the auto-deploy should be skipped or the operator
should take over:

1. **Schema-breaking migration.** Auto-deploy runs `alembic upgrade head` on
   every push. If a new migration is destructive (data loss, table rename
   without compatibility shim), pause auto-deploy via repo settings before
   merging, run the migration manually with backups, then re-enable.

2. **Image pull is mid-rollout.** GHCR push completes after the workflow's
   `docker push` step succeeds. If the operator is also `docker compose pull`
   on the VPS at that exact moment, two pulls race. Don't manually pull on
   the VPS during a workflow run — let the workflow's SSH step do it.

3. **`.env.demo` change.** Compose doesn't restart containers when only env
   values change. After editing `.env.demo`, run `docker compose --env-file
   .env.demo up -d --force-recreate` to pick up the new values. The deploy
   workflow does NOT do this — it's deliberately a manual step.

---

## §3 · Automation Scripts — Inventory + Usage

All scripts live under `scripts/demo/` and are invoked from the **operator's laptop** or **Hetzner VPS** depending on the script. The deploy workflow is in `.github/workflows/`.

### 3.1 First-time provisioning — `scripts/demo/provision.sh`

**Run on:** the Hetzner VPS (as root), once when the box is provisioned.

```bash
# After ssh-ing into a fresh Hetzner CX22 Ubuntu 22.04 box:
curl -fsSL https://raw.githubusercontent.com/wegofwd2020-hub/StudyBuddy_OnDemand/main/scripts/demo/provision.sh | bash
```

What it does:
- `apt-get update && upgrade`
- Installs `ufw`, `fail2ban`, `docker-ce`, `docker-compose-plugin`, `nginx`, `rsync`, `cron`, `pgvector` client tools
- Configures UFW (allow ssh / 80 / 443; deny everything else) + fail2ban (default ssh jail)
- Creates `/opt/studybuddy/` + git clones the repo
- Generates `.env.demo` skeleton with comments explaining each variable
- Adds the `deploy` user with passwordless sudo for docker compose only
- Sets up `cron` for the daily backup at 02:00 UTC
- **Idempotent**: re-running is safe (skips finished steps)

**Output:** the script ends with a checklist of next steps the operator must do manually (paste real Auth0 secrets, configure Cloudflare, etc.).

### 3.2 Seed orchestrator — `scripts/demo/seed.sh`

**Run on:** the Hetzner VPS, after `docker compose up` is healthy.

```bash
docker compose --env-file .env.demo exec api bash /app/scripts/demo/seed.sh
```

What it does:
1. `alembic upgrade head` (idempotent; skips if at head)
2. `python scripts/seed_super_admin.py` — creates `wegofwd2020@gmail.com` / Admin1234! (writes credentials to a one-shot file with `chmod 600`)
3. `python scripts/seed_demo_milfordwaterford.py` — MilfordWaterford school + 4 teachers + 15 students (matches DEMO_WALKTHROUGH.md §0 exactly)
4. `python scripts/seed_demo_test_account.py` — public "Try it" student (`demo-test@studybuddy.dev`)
5. `python scripts/seed_phase_a_dev.py` — Dev School + Phase A local-auth admin
6. `python scripts/seed_dev_content.py` — content-DB shell rows pointing at the uploaded content store

**Idempotent.** If a record already exists the script skips it and emits `[skip]` instead of failing.

### 3.3 Post-deploy smoke test — `scripts/demo/smoke.sh`

**Run on:** the operator's laptop (against the public domain) or in CI (against the deployed staging URL).

```bash
./scripts/demo/smoke.sh https://demo.studybuddy.app
```

What it checks:

| Check | Expected | Fails on |
|---|---|---|
| `GET /healthz` | 200 + `db: ok, redis: ok` | Any non-200 |
| `GET /readyz` | 200 | Any non-200 |
| `POST /api/v1/admin/auth/login` (super admin) | 200 + token | Wrong response shape |
| `POST /api/v1/auth/teacher/login` (Sam Houston) | 200 + token | Wrong response shape |
| `POST /api/v1/auth/login` (Anya Iyer student) | 200 + token | Wrong response shape |
| `GET /api/v1/content/G8-MATH-001/lesson` (with a student token) | 200 + has `sections` array | Empty or 404 |
| `GET /api/v1/content/G8-MATH-001/quiz/1` | 200 + has `questions` array | Empty or 404 |
| **Web frontend** `GET /` | 200 + has `<title>StudyBuddy` | Down |
| **Web frontend** `GET /demo` | 200 | Down |

Exits 0 if all green; exits 1 with a structured failure summary if any check fails.

### 3.4 Daily DB + content backup — `scripts/demo/backup.sh`

**Run on:** the Hetzner VPS, scheduled via cron at 02:00 UTC.

```cron
0 2 * * * /opt/studybuddy/scripts/demo/backup.sh >> /var/log/studybuddy-backup.log 2>&1
```

What it does:
1. `docker compose exec -T db pg_dump -U studybuddy -Fc studybuddy > /opt/studybuddy/backups/db-$(date +%Y%m%d).dump.gz`
2. `rsync -a /opt/studybuddy/content_store/ /opt/studybuddy/backups/content-$(date +%Y%m%d)/`
3. Prune backups older than 7 days
4. Trigger a Hetzner snapshot via API (if `HCLOUD_TOKEN` is set in `.env.demo`)
5. Email a one-line success/failure summary via the existing Gmail SMTP config

### 3.5 Auto-deploy CI — `.github/workflows/deploy-demo.yml`

**Triggers:** push to `main`, manual `workflow_dispatch`.

Steps:
1. Run the full test suite (`pytest`, `npm run typecheck`, `npm run lint`)
2. Build Docker images for `api`, `celery-worker`, `web`
3. Push to GitHub Container Registry tagged `:latest` and `:<short-sha>`
4. SSH to demo VPS using `DEMO_VPS_SSH_KEY` repo secret
5. On the VPS: `cd /opt/studybuddy && git pull && docker compose --env-file .env.demo pull && docker compose --env-file .env.demo up -d --remove-orphans`
6. Wait 30 seconds for health checks to settle
7. Run `scripts/demo/smoke.sh https://demo.studybuddy.app`
8. On smoke failure: open a GitHub issue tagged `incident:demo`; do NOT roll back automatically (operator must triage)

**Required GitHub secrets:**

| Secret | Purpose |
|---|---|
| `DEMO_VPS_SSH_KEY` | Private SSH key for the `deploy` user on demo VPS |
| `DEMO_VPS_HOST` | e.g. `demo.studybuddy.app` or the VPS IP |
| `DEMO_VPS_USER` | `deploy` |
| `GHCR_TOKEN` | Personal access token with `write:packages` |

---

## §4 · Test Plan — May 12 → May 15

Four-day phased validation. Each day has a **pass/fail gate** — if any gate fails, the next day's tests don't start until the issue is fixed.

### Day 1 — Monday May 12 — Initial Deploy + Infrastructure Smoke

**Goal:** prove the automation works end-to-end on a real Hetzner box.

| Time | Activity | Pass criterion |
|---|---|---|
| Morning | Provision a fresh CX22 (`scripts/demo/provision.sh`) — call this the **staging** box, separate from production | `docker compose ps` shows 7 healthy services |
| | Configure Cloudflare DNS for `staging.studybuddy.app` | `dig` resolves the new A-record |
| | `scripts/demo/seed.sh` | All seed scripts emit `done` or `skip`; no errors |
| | `scripts/demo/smoke.sh https://staging.studybuddy.app` | Exit 0 |
| Afternoon | Trigger a fake `main` push — verify auto-deploy works end-to-end | `deploy-demo.yml` finishes green; smoke check passes inside the workflow |
| | Trigger a deliberate smoke failure (e.g. break a healthcheck) — verify rollback / issue creation | Issue auto-opened with `incident:demo` label |
| End of day | Backup script runs (manually trigger once at 17:00 to verify cron works) | Backup file present in `/opt/studybuddy/backups/` |

**Gate to Day 2:** all infra works on staging; rollback path proven.

### Day 2 — Tuesday May 13 — Full Persona Walkthroughs

**Goal:** every persona can log in and reach their happy-path screen with real content.

Walk through `studybuddy-docs/docs/dev/DEMO_WALKTHROUGH.md` end-to-end against `https://staging.studybuddy.app`, checking off each section's URL list.

| § | Persona | Critical check |
|---|---|---|
| 1 | Super Admin | All 9 admin URLs load; Content Review queue shows real pending versions |
| 2 | Sam Houston (school admin) | All 9 school URLs load; classroom + roster + subscription tabs populated |
| 3 | Warren Buffett (G11/12 Commerce teacher) | Teacher dashboard + 7 reports tabs all load; at-risk list is non-empty |
| 4 | Anya Iyer (G11 Commerce student) | Lesson + quiz + tutorial all render; **no STEM-Curriculum drift** (resolver fix #297 must be deployed) |
| 5 | Demo "Try it" G8 student | Public landing → demo login → first lesson; paywall after 2 lessons |
| 6 | Phase A local-auth admin | `first_login=true` forced reset works |

**Gate to Day 3:** all 6 personas pass; any 5xx errors documented + fixed.

### Day 3 — Wednesday May 14 — Subscription, Auth, Accessibility, Customer Demo Dry-Run

**Goal:** the non-happy-path flows hold up; a customer demo can run end-to-end.

| Test area | Specific tests |
|---|---|
| **Subscription** | Stripe Checkout opens with `4242 4242 4242 4242`; subscription activates immediately; webhook fires; entitlement cache invalidates; paywall lifts. Cancel flow works. Failed-payment flow (`4000 0000 0000 0002`) shows correct error. |
| **Auth — Auth0 track** | New self-registered student via Auth0 → email verify → first lesson. Forgot password works. |
| **Auth — Local track (Phase A)** | School admin provisions a new teacher; teacher logs in; forced password reset works; teacher provisions a student; student first-login forced reset works. |
| **Auth — Admin track** | Admin login works; admin JWT does NOT grant student endpoint access; student JWT does NOT grant admin endpoint access. |
| **Accessibility** | Alt+D toggles OpenDyslexic (cookie persists). Tab through landing page — no traps. axe-core scan: no critical violations. Screen-reader test on `/student/curriculum` — heading hierarchy intact. |
| **Customer demo dry-run** | Stopwatch the full 15-min cross-persona arc from DEMO_WALKTHROUGH.md §7. Practice the narration. Time should land at 14–17 min. |

**Gate to Day 4:** every flow above passes; demo dry-run completes within 17 min.

### Day 4 — Thursday May 15 — Regression Sweep + Final Go/No-Go

**Goal:** confirm nothing has regressed and produce an explicit go-decision.

| Time | Activity | Pass criterion |
|---|---|---|
| Morning | Re-run all of Day 2's persona walkthroughs against staging | Same passes as Day 2 |
| Morning | Pull the latest content from the local pipeline; rsync to staging; verify 1 newly-added unit renders | Lesson loads; no `model: dev-seed` text |
| Midday | Run Playwright persona-suite against staging | All 35 persona specs green |
| Midday | Run `python3 scripts/doc_audit/run_all.py` | Zero drift |
| Afternoon | Lower DNS TTL on `demo.studybuddy.app` to 300s (so cutover at T-1h on May 16 propagates fast) | Cloudflare confirms TTL=300 |
| Afternoon | Provision the **production** demo VPS (separate from staging — same `provision.sh` on a fresh CX22) | Staging stays running for last-mile testing; prod VPS is ready and seeded |
<!-- doc-audit:ignore -->
| Afternoon | Final go/no-go meeting with self: `docs/DEMO_LAUNCH_GO_DECISION.md` checklist | All boxes ticked → GO |

**Gate to May 16 launch:** 4 successive days of green on the test gates plus a documented go-decision.

---

## §5 · Risk Register

The known risks worth pre-mitigating, ordered by likelihood × impact:

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Real Commerce/Science lesson 500s due to content schema drift (#295/#297 not fully deployed) | Medium | High | Run smoke check after every deploy; #297 already merged in this branch — verify via `git log --grep '#297'` |
| Hetzner CX22 OOM under demo load (4 GB RAM is tight with 7 containers + Postgres) | Medium | Medium | Set `restart: always`; monitor with `docker stats`; upgrade to CX32 (8 GB, ~$10/mo) if needed |
| Cloudflare DNS cutover takes longer than 5 min | Low | Medium | Pre-stage TTL=300s on May 15; have the staging URL bookmark as fallback during the announcement |
| Pipeline-built content doesn't match seeded curriculum metadata | Medium | High | Run `python scripts/check_content_metadata.py` (or its equivalent — verify on Day 4 before final upload) |
| Auth0 free tier rate-limit hit during demo (7,500 MAU) | Very low | Low | Demo will not approach this in a single launch day |
| `git pull` on demo VPS hits a merge conflict (someone edited files on the box) | Low | Medium | Demo box is read-only via deploy user; SSH access for the operator is for monitoring only |
| Stripe webhook fails to register against the public demo URL | Low | Medium | Use Stripe CLI or Stripe dashboard manual webhook config; test on Day 3 |

---

## §6 · Pre-Launch Decisions Open as of May 8

These need a decision before May 12 — flagging now so they don't surface on May 15 as blockers.

1. **Domain name.** `demo.studybuddy.app`? Or sub-path on a different parent? Confirm before May 12.
2. **Hetzner location.** Falkenstein (DEU), Helsinki (FIN), or Ashburn (USA)? Pick the closest to your primary demo audience.
3. **Demo data reset cadence.** Nightly? Weekly? Never? — `seed.sh` is idempotent so nightly reset is feasible via cron.
4. **Stripe environment.** Test mode is the recommended default. If a paying-customer demo is planned, decide whether to swap to live mode for that specific demo (and back).
5. **Sentry project.** Reuse the existing prod project with a `demo` environment tag, or create a separate `studybuddy-demo` project? Recommend: reuse + tag.

### Decided 2026-05-08 — closed for the launch

**GitHub tier — stay on Free.** No upgrade needed before May 16.

| Repo | Visibility | Implication for the deploy workflow |
|---|---|---|
| `StudyBuddy_OnDemand` | **public** | Unlimited Actions minutes, unlimited GHCR storage + bandwidth, full branch-protection rules |
| `studybuddy-docs` | private | 2,000 min/mo Actions cap + 500 MB Packages cap — does not affect demo deployment (no Docker images here) |
| `studybuddy_free` | public | Same unlimited capacity as the main repo |

The deploy-demo workflow (`.github/workflows/deploy-demo.yml`) builds + pushes Docker images to GHCR and runs CI on every merge to `main` — both happen against the **public** `StudyBuddy_OnDemand` repo, where Free tier covers everything the demo needs.

**Triggers that will warrant an upgrade later** (none apply on May 16):

| Trigger | Recommended tier | Cost |
|---|---|---|
| `StudyBuddy_OnDemand` goes private (e.g. to hide competitive details when paying customers arrive) | Team | $4/user/month |
| `studybuddy-docs` private-repo Actions usage exceeds 2,000 min/month (very unlikely — markdown CI is cheap) | Team | $4/user/month |
| Second developer joins and needs branch protection + required reviewers in private repos | Team | $4/user/month |
| First school customer asks for SOC 2 evidence / SAML SSO / IP allow lists / audit-log streaming | Enterprise | $21/user/month |
| Want Dependabot security-update auto-merge in private repos | Team | $4/user/month |

**Re-evaluate after first paying customer.** Until then, Free tier saves ~$50–250/month with zero functional cost to the demo path. The only operational note: the deploy workflow uses `secrets.GITHUB_TOKEN` for GHCR pushes (right scopes on Free); if a future workflow in `studybuddy-docs` ever needs to push to GHCR, that one will need a personal access token with `write:packages` scope (still Free, just an extra step).

---

## Change Log

| Date | Change |
|---|---|
| 2026-05-08 | Initial — comprehensive plan for May 16 launch (4 days code freeze + 4 days test phase) |
| 2026-05-08 | §6 — Closed the GitHub-tier decision: stay on Free; document upgrade triggers for future-self |
| 2026-05-08 | §2.5 — Added consolidated Deployment Sequence (cold-start + ongoing-deploy flows + dependency graph + rollback paths + skip-auto-deploy cases) |
