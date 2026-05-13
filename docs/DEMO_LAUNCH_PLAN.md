# Demo Hosting — Launch Plan (target: Day 0 / Sun 2026-05-17)

**Audience:** Sivakumar (operator) · future on-call deputy
**Document type:** End-to-end runbook from "today's main branch" → "live demo on `demo.studybuddy.app`"
**Companion docs:** [`studybuddy-docs/docs/dev/DEMO_HOSTING_GUIDE.md`](https://github.com/wegofwd2020-hub/studybuddy-docs/blob/docs/demo-walkthrough/docs/dev/DEMO_HOSTING_GUIDE.md) (Hetzner-based architecture) · [`studybuddy-docs/docs/dev/DEMO_WALKTHROUGH.md`](https://github.com/wegofwd2020-hub/studybuddy-docs/blob/docs/demo-walkthrough/docs/dev/DEMO_WALKTHROUGH.md) (click-by-click demo script) · [`studybuddy-docs/docs/operations/dns-and-email-setup.md`](https://github.com/wegofwd2020-hub/studybuddy-docs/blob/docs/demo-walkthrough/docs/operations/dns-and-email-setup.md) (domain registration + Cloudflare DNS + Zoho Mail step-by-step) · [`DEMO_EMAIL_INVENTORY.md`](DEMO_EMAIL_INVENTORY.md) (mailbox inventory at a glance — which to create, which to reuse) · [`studybuddy-docs/docs/dev/DEV_ACCOUNTS.md`](https://github.com/wegofwd2020-hub/studybuddy-docs/blob/main/docs/dev/DEV_ACCOUNTS.md) (account inventory) · [`mambakkam-net/Plans/DEMO_LAUNCH_PLAN.md`](https://github.com/wegofwd2020-hub/mambakkam-net/blob/main/Plans/DEMO_LAUNCH_PLAN.md) (the **first tenant** on the same Hetzner CX22 — its launch is hours before this one)

---

## Tenancy Position — Second Tenant on a Shared Hetzner CX22

> **Decided 2026-05-09 (inverted from 2026-05-08).** mambakkam.net is the
> first tenant on the box and cuts over at **T-0 = 09:00 EDT** on Day 0
> (Sun May 17). StudyBuddy joins as the **second tenant** at **T-0 = 13:00
> EDT** the same day, after ~4 hours of mambakkam stability.
>
> **What this means for this runbook:**
>
> - StudyBuddy's `provision.sh` is the **shorter "second-tenant" variant**.
>   It does NOT install Docker, configure UFW, set up fail2ban, create the
>   `deploy` user, or install host nginx — those were all done by
>   mambakkam.net's `provision.sh` earlier on Day 0 morning. StudyBuddy's
>   script is limited to: clone the repo to `/opt/studybuddy`, populate
>   `.env.demo`, ensure pgvector tooling, set up the StudyBuddy-specific
>   backup cron (offset to 02:00 UTC vs. mambakkam's 02:30 UTC), drop the
>   `infra/nginx/demo.studybuddy.app.conf` vhost into the existing host
>   nginx, and pull/up the compose stack.
> - The Cloudflare Origin Cert is **already in place** at
>   `/etc/ssl/cloudflare/origin-{cert,key}.pem` with `demo.studybuddy.app`
>   in the SAN list (mambakkam generated it on Day -1 evening with both
>   hostnames). Do not re-issue.
> - mambakkam.net pays the $5/mo VPS bill; StudyBuddy joins at zero
>   marginal infra cost on the box.
>
> Sections §2 (launch-day runbook), §2.5 (cold-start sequence), and §3.1
> (provision.sh inventory) below all reflect the second-tenant flow. Do
> not run StudyBuddy `provision.sh` against a fresh box — only against a
> box that mambakkam.net's `provision.sh` has already touched.

---

## Timeline at a Glance

```
May 8  (Fri) ──┐
May 9  (Sat)   │  CODE FREEZE PHASE — automation + last-mile fixes
May 10 (Sun)   │
May 11 (Mon)   │
May 12 (Tue) ──┤◀─── Day -5   code-freeze cutoff (no app changes after EOD)
May 13 (Wed)   │     Day -4   ┐
May 14 (Thu)   │     Day -3   │  TEST PHASE — staging deploy + persona walkthroughs
May 15 (Fri)   │     Day -2   │
May 16 (Sat)   │     Day -1 ──┘  Regression sweep + final go/no-go (EOD)
May 17 (Sun) ──┴───  Day  0      LAUNCH DAY · DNS cutover · announcement
May 18 (Mon)         Day  1      First day live · monitoring · smoke
```

Eight calendar days from today (2026-05-09) to Day 0 launch (2026-05-17).
Per the 2026-05-09 change-log entry, launch slipped from May 16 to May 17;
the May 12 EOD code-freeze cutoff is preserved (now labeled Day -5).
StudyBuddy's launch-day cutover (T-0 = 13:00 EST on Day 0) follows
mambakkam.net's 09:00 EST cutover by ~4 hours on the same day.

---

## §1 · What to Complete Before Day -5 (Tue May 12) Code-Freeze Cutoff

Three categories: **automation** (must), **content** (must), **polish** (nice-to-have if time permits).

### 1.A Automation — must-have for Day 0 (Sun May 17) (this commit ships them)

These ship with this PR. Use them as-is; no further code work needed.

| Deliverable | File | Purpose |
|---|---|---|
| Demo Compose override | [`docker-compose.demo.yml`](../docker-compose.demo.yml) | Production-shaped: drops PgBouncer + Beat-standby + stripe-cli, adds Nginx, persistent named volumes, `restart: always` on every service |
| First-time provisioning | [`scripts/demo/provision.sh`](../scripts/demo/provision.sh) | Idempotent Hetzner CX22 bootstrap — apt, ufw, fail2ban, Docker install, repo clone, .env.demo skeleton |
| Content sync (one command) | [`scripts/demo/sync-content.sh`](../scripts/demo/sync-content.sh) | Inject G11 visuals + rsync content_store_data/ → /data/content/ + rsync web/public/sample-visuals/ → /data/sample-visuals/. Optional --dry-run, --skip-inject, --smoke flags. Covers all three asset classes (TEXT + GRAPHICS + VIDEO) in one operator step. |
| Seeding orchestrator | [`scripts/demo/seed.sh`](../scripts/demo/seed.sh) | Runs the 5 demo seed scripts in dependency order (super_admin → milfordwaterford → demo_test_account → phase_a_dev → content_db) |
| Post-deploy smoke check | [`scripts/demo/smoke.sh`](../scripts/demo/smoke.sh) | Curl-based: `/healthz`, login as 4 persona types, fetch one lesson + one quiz, exit 1 on any 4xx/5xx |
| Daily DB + content backup | [`scripts/demo/backup.sh`](../scripts/demo/backup.sh) | restic-based, encrypted at-rest. `pg_dump` → staging file → restic snapshot of (dump + `/data/content` + `.env.demo`) → `restic forget` with 7d/4w/3m/1y policy → optional Hetzner snapshot trigger. Cron 02:00 UTC. |
| Weekly restic check + prune | [`scripts/demo/backup-check.sh`](../scripts/demo/backup-check.sh) | `restic check --read-data-subset 5%` (catches silent bit-rot) → `restic prune --max-unused 5%` (reclaims disk that daily `forget`s marked unreferenced). Cron Sun 03:00 UTC, 1h after the daily so they don't compete for the repo lock. |
| Auto-deploy on merge to main | [`.github/workflows/deploy-demo.yml`](../.github/workflows/deploy-demo.yml) | Build → GHCR push → SSH to Hetzner → `docker compose pull && up -d` → smoke test. **Web image build receives `NEXT_PUBLIC_DEMO_MODE=true` as a Docker `build-arg`** so the flag is baked into the client bundle at build time (NEXT_PUBLIC_* vars are not read at runtime). |
| Universal sign-in entry point | `web/app/(public)/signin/` + `POST /api/v1/auth/universal-login` | All three auth tracks (Auth0 students/teachers, Phase A local school users, admin bcrypt) resolve through the same `/signin` page now. Old `/school/login`, `/demo/login`, `/demo/teacher/login` redirect here. Affects every persona walkthrough in §4 — the entry URL is `/signin`, never the old per-track pages. |

**Recent CI unblocking (2026-05-13).** The web image build had been red for weeks on `npm ci ERESOLVE` after a stray `typescript@6.0.2` upgrade. Four fixes shipped in sequence: (a) `web/package.json` downgraded to `typescript@^5.9.3`; (b) `web/package-lock.json` regenerated from scratch under `node:20-alpine`; (c) Dockerfile `npm ci` switched to `--prefer-offline --legacy-peer-deps`; (d) `next.config.ts` set `output: "standalone"` so the runner stage's `COPY --from=builder /app/.next/standalone` actually has a source. Verified locally via `docker run --rm node:20-alpine npm ci && npm run build`. The deploy-demo workflow now builds + pushes both images cleanly; the SSH-deploy step fails as expected because `DEMO_VPS_HOST` is empty pre-launch (see §5 risk register).

### 1.A.bis Domain + Email — must-have

These are out-of-repo deliverables (DNS + Zoho), so they don't ship in
this commit, but they're required for the Day 0 (Sun May 17) cutover. Step-by-step
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
- [ ] Pre-launch (Day -1 / Sat May 16 EOD): TTL on the `demo` A record lowered to 300s
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
| Pipeline output uploaded to demo VPS | Operator (rsync — see §2.5 step 5) | `ssh demo 'ls /data/content/curricula/ && ls /data/sample-visuals/'` shows the 10 curricula + 44 tutorial MP4s |

**One-time cost** to build all of the above: ~$215 (per `studybuddy-docs/COST_PLAN.md`). Already partially built; finish gaps locally before Day -5 (Tue May 12).

### 1.C Polish — nice-to-have (skip if blocking)

| Item | Effort | Skip if |
|---|---|---|
| Fix 2 outstanding migration table entries (0056, 0057 in CLAUDE.md) | 5 min | Never skip — already in this PR |
| Custom branded 404 + 500 error pages | 1 hour | Default Next.js pages are acceptable for demo |
| `demo.studybuddy.app` favicon + Apple touch icon | 30 min | Browser-default favicon is acceptable |
| Demo banner ("This is a demo — content resets nightly") | 30 min | Useful but not critical |
| Status page (Cloudflare Workers) | 2 hours | Can be added post-launch |
| Sentry environment tag = `demo` | 15 min | Should ship — single env var change |

### 1.D Definition of "Done" for Day -5 (Tue May 12 EOD)

A green checkbox on each of these means we enter the test phase clean:

- [ ] All Tier-1.A automation deliverables in `main`
- [ ] All Tier-1.A.bis Domain + Email phases 1–5 ticked (every checkbox in §1.A.bis above is green)
- [ ] All Tier-1.B content built and the catalogue pushed to a staging directory
- [ ] `python3 scripts/doc_audit/run_all.py` exits clean (zero drift)
- [ ] `bun run typecheck` (web) + `pytest` (backend) green on `main`
- [ ] One **complete dry-run on a throwaway Hetzner VPS** (cheaper than figuring out failures live on Day 0 / Sun May 17): provision → seed → smoke → tear down — including the DNS + email phases against a throwaway subdomain (e.g. `dryrun.studybuddy.app`)

---

## §2 · Day 0 (Sun May 17) Launch-Day Runbook

### StudyBuddy is the second tenant on the shared CX22

mambakkam.net cuts over first on Day 0 at 09:00 EDT (per
[mambakkam-net/Plans/DEMO_LAUNCH_PLAN.md](https://github.com/wegofwd2020-hub/mambakkam-net/blob/main/Plans/DEMO_LAUNCH_PLAN.md)).
StudyBuddy joins the same box ~4 hours later, after mambakkam stability
is confirmed. The operator's actual day starts at 08:00 EDT (mambakkam
provisioning); StudyBuddy second-tenant work begins ~11:00 EDT.

### Day -1 (Sat May 16) 17:00–20:30 EDT — Account + Email Setup

**Full chronological checklist in
[`mambakkam-net/Plans/ACCOUNT_SETUP.md`](https://github.com/wegofwd2020-hub/mambakkam-net/blob/main/Plans/ACCOUNT_SETUP.md)**
— operator's source-of-truth for every account/email/credential created
that evening, with a §10 cheat-sheet showing which value lands in which
`.env.demo` line tomorrow morning.

The StudyBuddy-relevant slice (sections §7–§9 of that doc; ~90 min
within the 3.5-hour total):

- **§7 (19:00–19:25)** — Register `studybuddy.app` at Cloudflare Registrar;
  pre-stage `demo.studybuddy.app` A record at TTL=300s (proxy off); add
  `studybuddy.app` to the Zoho org with MX/SPF/DKIM/DMARC; create
  mailboxes `support@studybuddy.app` + `sales@studybuddy.app`; generate
  a second Zoho App Password for the StudyBuddy Gmail send-as identity.
- **§8 (19:25–19:50)** — Auth0 free dev tenant; create three applications
  (Student SPA, Teacher SPA, Backend M2M); save the 5 IDs + secret + JWKS
  URL.
- **§9 (19:50–20:30)** — Stripe test mode (sk_test_/pk_test_/webhook
  signing secret); Sentry project + DSN; final go/no-go.

The Cloudflare Origin Cert is generated by mambakkam in §1.3 with
`demo.studybuddy.app` already in the SAN list — StudyBuddy reuses the
same cert; nothing extra to issue.

### Day 0 (Sun May 17) — Server Cutover Runbook

mambakkam owns the morning provisioning slot from 08:00 EDT. StudyBuddy's
second-tenant work begins **at T+3h = 11:00 EDT** (after mambakkam
stability check) and cuts over at **T+4h = 13:00 EDT**.

| Time (EDT) | Δ | Action | Owner | Pass criterion |
|---|---|---|---|---|
| 08:00 | — | mambakkam.net first-tenant provisioning starts (driven by mambakkam's launch plan §2). StudyBuddy passive observer. | mambakkam | mambakkam green by 09:00 |
| 09:00 | mb T-0 | mambakkam.net live; StudyBuddy still un-launched. | mambakkam | — |
| 09:30 | mb T+30m | mambakkam first-traffic check passes | mambakkam | No 5xx |
| 11:00 | mb T+2h / sb T-2h | **Pre-flight on the shared box** — confirm mambakkam still healthy (`docker stats`, no OOM); confirm `/etc/ssl/cloudflare/` has the Origin Cert with SAN already including `demo.studybuddy.app` | Operator | mambakkam unaffected; cert SAN green |
| 11:05 | sb T-2h | Run StudyBuddy's `scripts/demo/provision.sh` (second-tenant variant — ~5 min; see §2.5 below) | Operator | All 9 steps complete; pre-flight (step 0) confirms mambakkam first-tenant artefacts |
| 11:15 | sb T-1h45m | Edit `/opt/studybuddy/.env.demo` — paste real Auth0 / Stripe-test / Gmail App Password / Sentry DSN values from your password manager; replace 5 `<REPLACE_WITH_openssl_rand_hex_32>` lines with `openssl rand -hex 32` outputs | Operator | `grep '<' /opt/studybuddy/.env.demo` returns no placeholders |
| 11:30 | sb T-1h30m | Append GH Actions deploy SSH pubkey to `/home/deploy/.ssh/authorized_keys` (mambakkam's already there — append, do not overwrite) | Operator | `wc -l /home/deploy/.ssh/authorized_keys` shows 2+ keys |
| 11:35 | sb T-1h25m | Push pre-built content (inject + both rsyncs in one command): `bash scripts/demo/sync-content.sh deploy@<vps-ip>` — handles G11 visual inject, content_store_data/ → /data/content/, and web/public/sample-visuals/ → /data/sample-visuals/ (the 44 tutorial MP4s, gitignored, never in the Docker image). See `--help` for flags. | Operator | Script exits 0; "content sync complete" banner printed |
| 11:50 | sb T-1h10m | Bring the StudyBuddy stack up: `docker compose -f docker-compose.yml -f docker-compose.demo.yml --env-file .env.demo up -d` | Operator | `docker compose ps` shows all 7 services `Up (healthy)` within 60s |
| 12:00 | sb T-1h | Reload host nginx so the StudyBuddy vhost picks up the new upstream: `sudo nginx -t && sudo systemctl reload nginx` | Operator | nginx reload OK; mambakkam still serving |
| 12:05 | sb T-55m | Run migrations + seed: `docker compose exec api alembic upgrade head` then `bash scripts/demo/seed.sh` | Operator | All seed scripts emit `done` or `skip`; no errors |
| 12:30 | sb T-30m | Local smoke against StudyBuddy compose-internal nginx: `bash scripts/demo/smoke.sh http://127.0.0.1:8443` | Operator | Exit 0 |
| 12:45 | sb T-15m | DNS cutover at Cloudflare: change the `demo.studybuddy.app` A record value from the Day -1 placeholder to the real VPS public IP, **enable proxy** (orange cloud) | Operator | `dig +short demo.studybuddy.app` returns Cloudflare-edge IP within 60s |
| 12:50 | sb T-10m | Public smoke from your laptop: `bash scripts/demo/smoke.sh https://demo.studybuddy.app` | Operator | Exit 0 |
| 12:55 | sb T-5m | Persona walkthrough (5 personas × ~1 min each) | Operator | All 5 reach their dashboard |
| **13:00** | **sb T-0** | **GO LIVE** — share `https://demo.studybuddy.app` link | Operator | Announcement sent; both sites live on shared CX22 |
| 13:30 | sb T+30m | First user telemetry — Sentry, FastAPI access log, Grafana Cloud dashboards | Operator | No 5xx; no warning-level Sentry events |
| 15:00 | sb T+2h | Co-tenant load check — `docker stats`; mambakkam unaffected | Operator | CX22 < 80% RAM combined |
| 17:00 | sb T+4h | First post-launch incident review (even if uneventful) | Operator | Notes captured for retrospective |
| Next day 02:00 UTC | — | First nightly DB + content backup runs (`0 2 * * *`); 30 min before mambakkam's 02:30 UTC backup | Auto | Backup file present in `/opt/studybuddy/backups/` |

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

- **Cold start** — done once during the Day -2 to Day -1 (May 15-16) staging dry-run and again
  on/around Day -1 (Sat May 16) when the production demo VPS is provisioned. Manual
  steps; the operator drives.
- **Ongoing deploy** — fires automatically on every merge to `main` after
  initial cold-start. CI drives; operator only intervenes on failure.

### Sequence A — Cold start (manual; ~20 minutes as second tenant)

Run this **after** mambakkam.net's `provision.sh` has bootstrapped the
shared Hetzner CX22 (Docker, UFW, fail2ban, deploy user, host nginx,
Origin Cert directory, daily-backup cron). For a fully fresh box (no
mambakkam.net yet), run mambakkam.net's `provision.sh` first — see
[`mambakkam-net/Plans/DEMO_LAUNCH_PLAN.md` §2.5](https://github.com/wegofwd2020-hub/mambakkam-net/blob/main/Plans/DEMO_LAUNCH_PLAN.md#25--deployment-sequence-consolidated).

```
┌──────────────────────────────────────────────────────────────────────┐
│  Operator action                                                      │
└──────────────────────────────────────────────────────────────────────┘

  1. Verify mambakkam.net first-tenant provisioning is complete       [~1 min]
     ssh root@<public-ip>
     docker --version          # Docker CE installed by mambakkam
     ufw status                # active; ssh / 80 / 443 allowed
     systemctl status fail2ban # active
     id deploy                 # user exists
     ls /etc/ssl/cloudflare/   # origin-cert.pem + origin-key.pem present
                               # (cert SAN must already include demo.studybuddy.app)
     systemctl status nginx    # host nginx running

  2. SSH in + run StudyBuddy second-tenant provision.sh               [~3 min]
     curl -fsSL https://raw.githubusercontent.com/wegofwd2020-hub/StudyBuddy_OnDemand/main/scripts/demo/provision.sh \
       | bash
     What it does (second-tenant variant):
       - Pre-flight: hard-fails if any first-tenant artefact is missing
       - git clone the repo to /opt/studybuddy
       - Generate .env.demo skeleton from .env.demo.example
       - Drop infra/nginx/demo.studybuddy.app.conf into
         /etc/nginx/sites-available/ and enable it (alongside mambakkam's
         vhost; the Host header dispatches)
       - Set up daily-backup cron at 02:00 UTC (offset 30 min before
         mambakkam.net's 02:30 UTC backup)
       - Verify pgvector tooling installed
     Skips (already done by mambakkam.net first-tenant provision):
       - Docker install
       - UFW firewall config
       - fail2ban setup
       - deploy user creation
       - host nginx install
       - /etc/ssl/cloudflare/ directory + Origin Cert paste

  3. Populate .env.demo                                               [~5 min]
     Replace 5 placeholder secrets via `openssl rand -hex 32`
     Paste Auth0 + Stripe-test + Gmail App Password values.

  4. Paste GH Actions deploy SSH pubkey                               [~1 min]
     /home/deploy/.ssh/authorized_keys
     (matching private key → repo secret DEMO_VPS_SSH_KEY)
     Append-only — do not overwrite mambakkam.net's deploy key.

  5. Upload pre-built content from dev machine                        [~5 min]
     bash scripts/demo/sync-content.sh deploy@<vps-ip>
     # Wraps the G11 visual inject + both rsyncs (content_store_data/ →
     # /data/content/ and web/public/sample-visuals/ → /data/sample-visuals/,
     # the latter being gitignored so it never ships in the Docker image).
     # See `--help` for --dry-run, --skip-inject, and --smoke flags.

┌──────────────────────────────────────────────────────────────────────┐
│  Container startup (docker compose handles dependencies)              │
└──────────────────────────────────────────────────────────────────────┘

  6. docker compose pull (fetch images from GHCR)                     [~3 min]
     cd /opt/studybuddy
     docker compose -f docker-compose.yml -f docker-compose.demo.yml \
       --env-file .env.demo pull

  7. docker compose up -d                                             [~2 min]
     Same flags as step 6, with `up -d`.

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
     └─ nginx                    compose-internal nginx on 127.0.0.1:8443

  8. Reload host nginx to pick up the new vhost                       [~10 sec]
     sudo nginx -t && sudo systemctl reload nginx
     (do NOT restart — reload preserves mambakkam.net traffic. Reload
      AFTER compose is up so the 127.0.0.1:8443 upstream is reachable
      the moment the vhost is enabled. Matches §2 timing.)

  9. seed.sh — populate demo accounts + content rows                  [~3 min]
     docker compose exec api bash /app/scripts/demo/seed.sh
     Idempotent. Runs:
       seed_super_admin → seed_demo_milfordwaterford →
       seed_demo_test_account → seed_phase_a_dev → seed_dev_content

 10. smoke.sh — validate end-to-end                                   [~30 sec]
     bash scripts/demo/smoke.sh http://127.0.0.1:8443
     (loopback first; switch to public domain after step 11.)

┌──────────────────────────────────────────────────────────────────────┐
│  Make it public                                                       │
└──────────────────────────────────────────────────────────────────────┘

 11. Cloudflare DNS A record → VPS public IP                          [~3 min]
     Cloudflare dashboard → demo.studybuddy.app → A record (the one
     pre-staged on Day -1 evening). Update IP value, enable proxy
     (orange cloud). SSL/TLS mode: Full (strict).

 12. smoke.sh against the public domain                               [~30 sec]
     bash scripts/demo/smoke.sh https://demo.studybuddy.app
     Cold-start complete when this exits 0.
```

**Total cold-start time:** ~20 minutes for a calm operator with all secrets
already in hand (down from ~30 min — system bootstrap was done by
mambakkam.net's first-tenant provision; this is just the application stack
on top).

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
| VPS itself unhealthy on launch day | DNS revert at Cloudflare to staging IP; investigate VPS post-mortem (TTL=300s set on Day -1 (Sat May 16) means propagation ≤5 min) | ~5 min |
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

**Run on:** the Hetzner VPS (as root), once when standing up StudyBuddy.
This is the **second-tenant variant** — it assumes mambakkam.net's
`provision.sh` has already done the system bootstrap. Do NOT run against
a fresh box without mambakkam.net being there first.

```bash
# After ssh-ing into a Hetzner CX22 that mambakkam.net has already provisioned:
curl -fsSL https://raw.githubusercontent.com/wegofwd2020-hub/StudyBuddy_OnDemand/main/scripts/demo/provision.sh | bash
```

What it does (second-tenant work only):
- Pre-flight check: confirms Docker, UFW, fail2ban, deploy user, host
  nginx, and the `/etc/ssl/cloudflare/` directory all exist (mambakkam
  first-tenant artefacts). Aborts with a clear error if any are missing.
- Verifies the `pgvector` client tooling is installed (apt — adds if
  missing; cheap)
- Creates `/opt/studybuddy/` + git clones the repo
- Generates `.env.demo` skeleton with comments explaining each variable
- Drops the StudyBuddy host-nginx vhost into `/etc/nginx/sites-available/`
  and enables it (alongside mambakkam's; Host header routes both)
- Sets up `cron` for the daily backup at 02:00 UTC (mambakkam.net runs at
  02:30, so StudyBuddy goes 30 min earlier to avoid disk I/O collision)
- Generates `/etc/restic/studybuddy.password` + initialises the local
  restic repo at `/opt/studybuddy/backups/restic/`; password printed once
- **Idempotent**: re-running is safe (skips finished steps); does not
  modify mambakkam.net artefacts

**Skips (already done by mambakkam.net first-tenant provision):**
- `apt-get update && upgrade`
- Docker CE + Compose plugin install
- UFW + fail2ban configuration
- The `deploy` system user
- Host nginx install
- The `/etc/ssl/cloudflare/` directory + Origin Cert (already SAN-listed
  for `demo.studybuddy.app`)

**Output:** the script ends with a checklist of next steps the operator must do manually (paste real Auth0 secrets, populate `.env.demo`, etc.) and prints the freshly-generated restic backup password ONCE — copy it to your password manager immediately.

### 3.2 Content sync — `scripts/demo/sync-content.sh`

**Run on:** the operator's laptop, after `provision.sh` finishes on the VPS and before `docker compose up`. Re-run any time content changes locally.

```bash
bash scripts/demo/sync-content.sh deploy@<vps-ip>
# Optional: --dry-run, --skip-inject, --smoke https://demo.studybuddy.app
bash scripts/demo/sync-content.sh --help    # full flag list
```

What it does (one command, in order):
1. **Pre-flight** — checks `content_store_data/` + `web/public/sample-visuals/` exist locally, `celery-pipeline` is up (needed for inject), and SSH to the target works.
2. **Inject G11 visuals** — runs `scripts/inject_g11_visuals.py` inside the local `celery-pipeline` container, which populates `section.visuals[]` in the G11 Science tutorial JSON from `sample_content/g11-science/` SVGs + the MP4 references in `UNIT_VIDEOS`. Idempotent. Skip with `--skip-inject`.
3. **Rsync TEXT + legacy GRAPHICS** — `content_store_data/` → `/data/content/` on the VPS. Covers lessons, quizzes, tutorials, experiments, audio MP3s, and `visuals/_legacy/` SVGs. Served by nginx at `/content/*`.
4. **Rsync VIDEO** — `web/public/sample-visuals/` → `/data/sample-visuals/` on the VPS. The 44 tutorial MP4s referenced by `tutorial_en.json` via `/sample-visuals/<unit>/<file>.mp4` URLs. **This tree is gitignored** so it never reaches the Docker image — this rsync is the only path. Served by nginx at `/sample-visuals/*`.
5. **Optional smoke** — chains into `smoke.sh <url>` if `--smoke <url>` was passed.

**Exit codes** match the failing step: 1 pre-flight, 2 inject, 3 content rsync, 4 sample-visuals rsync, 5 smoke. Each failure mode prints a hint pointing at the likely cause (e.g. "did provision.sh step 7 run?" for missing `/data/*` dirs).

### 3.3 Seed orchestrator — `scripts/demo/seed.sh`

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

### 3.4 Post-deploy smoke test — `scripts/demo/smoke.sh`

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

### 3.5 Daily DB + content backup — `scripts/demo/backup.sh` (restic)

**Run on:** the Hetzner VPS via cron. Two scripts on two schedules, both preconditioned on `provision.sh`: **step 6** installs the cron file `/etc/cron.d/studybuddy-demo-backup`; **step 8** initialises the restic repo + password file. Step 6 hard-fails on first daily run with exit 5 or 6 if step 8 was skipped.

The installed cron file (`/etc/cron.d/`-format — note the `root` user field) reads:

```cron
# Daily backup — pg_dump → restic snapshot
0 2 * * *   root cd /opt/studybuddy && bash scripts/demo/backup.sh       >> /var/log/studybuddy-backup.log 2>&1

# Weekly integrity check + prune (Sundays, 1h after the daily so they don't compete for the repo lock)
0 3 * * 0   root cd /opt/studybuddy && bash scripts/demo/backup-check.sh >> /var/log/studybuddy-backup.log 2>&1
```

**Daily — `backup.sh`** (3 numbered steps + an optional 4th):

1. `pg_dump -Fc | gzip -9` → `/opt/studybuddy/backups/staging/db-latest.dump.gz` (always overwritten; restic dedupes blocks-against-blocks across days so 30 daily dumps take ~1.2× the size of one, not 30×).
2. `restic backup` → `/opt/studybuddy/backups/restic/` covering up to three sources: the staging dump from step 1, `/data/content` (if present), and `/opt/studybuddy/.env.demo` (if present). Tags: `daily` + `host=<short hostname>`. Encrypted at-rest with AES-256; password at `/etc/restic/studybuddy.password` (generated and printed once by `provision.sh` step 8 — record it in your password manager, otherwise the repo is unrecoverable).
3. `restic forget --tag daily --keep-daily 7 --keep-weekly 4 --keep-monthly 3 --keep-yearly 1`. **`forget` only marks snapshots unreferenced** — actual disk reclamation happens in the weekly `backup-check.sh` step 2 below (`restic prune`), not here. Splitting the two keeps the daily run fast: `forget` is O(snapshots); `prune` scans every pack.
4. *(Optional)* If `HCLOUD_TOKEN` is set in `.env.demo` and not the placeholder, resolve the server ID via the Hetzner API and POST a `create_image` action. Belt-and-braces against OS-level corruption; the restic repo is the primary backup.

Exit codes: **0** success / **1** pg_dump failed / **2** restic backup failed / **3** restic forget failed / **4** Hetzner snapshot API call failed / **5** repo not initialised / **6** password file missing or unreadable. The cron line redirects all output to `/var/log/studybuddy-backup.log`, so a non-zero exit shows up there (and via Promtail → Loki) rather than via cron mail.

**Weekly — `backup-check.sh`** (2 steps):

1. `restic check --read-data-subset 5%` — reads 5% of pack files to catch silent bit-rot. Full 100% audit is too slow to run weekly; 5% cycles every pack in ~5 months on average.
2. `restic prune --max-unused 5%` — reclaims disk that the daily `forget`s marked unreferenced but didn't physically delete.

Exit codes: 0 success / 1 check failed (**possible bit-rot — investigate immediately**) / 2 prune failed / 3 repo not initialised / 4 password file unreadable.

**Log routing.** Both scripts write to `/var/log/studybuddy-backup.log` (via the cron redirect). Promtail (running in the monitoring stack — see §8) ships that log to Grafana Cloud Loki. Canonical query (matches the comment in `backup-check.sh`):

```logql
{job="backups", which="studybuddy"} |~ "(?i)check|prune|error"
```

The `BackupSilent`, `ResticCheckFailed`, `ResticPruneFailed`, and `BackupSizeRunaway` alerts (see §10) fire on this stream.

**Local-only repo.** The restic repo lives on the same disk as the originals — deliberate choice for the demo. Off-box backups (S3 / B2 / R2) are deferred until the first paying customer per the residual-risk note in [`mambakkam-net/Plans/BACKUPS.md`](https://github.com/wegofwd2020-hub/mambakkam-net/blob/main/Plans/BACKUPS.md). Until then, the optional same-account Hetzner snapshot (triggered by step 4 above if `HCLOUD_TOKEN` is set) is the only off-box copy — and only protects against OS-level corruption, not against Hetzner-account compromise.

**Companion runbook.** [`Plans/BACKUPS.md`](https://github.com/wegofwd2020-hub/mambakkam-net/blob/main/Plans/BACKUPS.md) documents 5 restore scenarios: (1) full Postgres restore, (2) single content-unit restore, (3) recover `.env.demo` after disk loss, (4) recover the Cloudflare Origin Cert + key, (5) historical access-log search (mambakkam only — StudyBuddy's logs go to Loki, not restic). **Scenario 2** is rehearsed end-to-end against the staging box on §4 Day -2; **Scenario 1** is rehearsed in dry-run mode the same day (no DB swap, to preserve staging seed data). Scenarios 3-5 stay doc-only until the demo is live.

### 3.6 Auto-deploy CI — `.github/workflows/deploy-demo.yml`

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

## §4 · Test Plan — Day -4 (Wed May 13) → Day -1 (Sat May 16)

Four-day phased validation. Each day has a **pass/fail gate** — if any gate fails, the next day's tests don't start until the issue is fixed.

### Day -4 — Wednesday May 13 — Initial Deploy + Infrastructure Smoke

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

### Day -3 — Thursday May 14 — Full Persona Walkthroughs

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

### Day -2 — Friday May 15 — Subscription, Auth, Accessibility, Customer Demo Dry-Run

**Goal:** the non-happy-path flows hold up; a customer demo can run end-to-end.

| Test area | Specific tests |
|---|---|
| **Subscription** | Stripe Checkout opens with `4242 4242 4242 4242`; subscription activates immediately; webhook fires; entitlement cache invalidates; paywall lifts. Cancel flow works. Failed-payment flow (`4000 0000 0000 0002`) shows correct error. |
| **Auth — Auth0 track** | New self-registered student via Auth0 → email verify → first lesson. Forgot password works. |
| **Auth — Local track (Phase A)** | School admin provisions a new teacher; teacher logs in; forced password reset works; teacher provisions a student; student first-login forced reset works. |
| **Auth — Admin track** | Admin login works; admin JWT does NOT grant student endpoint access; student JWT does NOT grant admin endpoint access. |
| **Accessibility** | Alt+D toggles OpenDyslexic (cookie persists). Tab through landing page — no traps. axe-core scan: no critical violations. Screen-reader test on `/student/curriculum` — heading hierarchy intact. |
| **Restore drill** | Rehearse [`Plans/BACKUPS.md`](https://github.com/wegofwd2020-hub/mambakkam-net/blob/main/Plans/BACKUPS.md) **Scenario 2 — single content-unit restore** end-to-end against the staging box. Delete one unit dir (e.g. `/data/content/curricula/default-2026-g11-science/G11-BIO-001/`); verify the unit 404s in the student portal; `restic restore latest --include …` the dir; verify the unit loads again. Time should land under 5 min. **Scenario 1 — full Postgres restore** is rehearsed in **dry-run mode only** (`restic restore --target /tmp/restore-test ... ; pg_restore --list /tmp/restore-test/db-latest.dump.gz | head` — must list ≥1 table). Do NOT swap the staging DB or you lose the seed data. Other scenarios (3 `.env.demo`, 4 Origin Cert, 5 access-log) stay doc-only. |
| **Customer demo dry-run** | Stopwatch the full 15-min cross-persona arc from DEMO_WALKTHROUGH.md §7. Practice the narration. Time should land at 14–17 min. |

**Gate to Day 4:** every flow above passes; demo dry-run completes within 17 min.

### Day -1 — Saturday May 16 — Regression Sweep + Final Go/No-Go

**Goal:** confirm nothing has regressed and produce an explicit go-decision.

| Time | Activity | Pass criterion |
|---|---|---|
| Morning | Re-run all of Day 2's persona walkthroughs against staging | Same passes as Day 2 |
| Morning | Pull the latest content from the local pipeline; rsync to staging; verify 1 newly-added unit renders | Lesson loads; no `model: dev-seed` text |
| Midday | Run Playwright persona-suite against staging | All 35 persona specs green |
| Midday | Run `python3 scripts/doc_audit/run_all.py` | Zero drift |
| Afternoon | Lower DNS TTL on `demo.studybuddy.app` to 300s (so cutover at T-1h on Day 0 propagates fast) | Cloudflare confirms TTL=300 |
| Afternoon | NOTE — production CX22 provisioning happens **on Day 0 morning**, not on Day -1. mambakkam.net's first-tenant provision runs at 08:00 EDT Day 0; StudyBuddy joins at 11:00 EDT. Staging box (provisioned earlier in the test phase) stays running through Day -1 EOD for last-mile testing. | Staging healthy; production join procedure rehearsed against staging on Day -2 |
| Evening (17:00–20:30 EDT) | Account + email setup per §2 above — mambakkam-side first (Cloudflare account, Hetzner sign-up, Zoho org, Grafana Cloud) then StudyBuddy-side (studybuddy.app domain, Auth0, Stripe-test, Sentry) | All values captured in password manager |
<!-- doc-audit:ignore -->
| 20:30 EDT | Final go/no-go meeting with self: `docs/DEMO_LAUNCH_GO_DECISION.md` checklist | All boxes ticked → GO |

**Gate to Day 0 (Sun May 17) launch:** 4 successive days of green on the test gates plus a documented go-decision.

---

## §5 · Risk Register

The known risks worth pre-mitigating, ordered by likelihood × impact:

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Real Commerce/Science lesson 500s due to content schema drift (#295/#297 not fully deployed) | Medium | High | Run smoke check after every deploy; #297 already merged in this branch — verify via `git log --grep '#297'` |
| Hetzner CX22 OOM under demo load (4 GB RAM is tight with 7 containers + Postgres) | Medium | Medium | Set `restart: always`; monitor with `docker stats`; upgrade to CX32 (8 GB, ~$10/mo) if needed |
| Cloudflare DNS cutover takes longer than 5 min | Low | Medium | Pre-stage TTL=300s on Day -1 (Sat May 16); have the staging URL bookmark as fallback during the announcement |
| Pipeline-built content doesn't match seeded curriculum metadata | Medium | High | Run `python scripts/check_content_metadata.py` (or its equivalent — verify on Day 4 before final upload) |
| Auth0 free tier rate-limit hit during demo (7,500 MAU) | Very low | Low | Demo will not approach this in a single launch day |
| `git pull` on demo VPS hits a merge conflict (someone edited files on the box) | Low | Medium | Demo box is read-only via deploy user; SSH access for the operator is for monitoring only |
| Stripe webhook fails to register against the public demo URL | Low | Medium | Use Stripe CLI or Stripe dashboard manual webhook config; test on Day 3 |
| Auto-deploy CI badge stays red until launch (every push to `main` fails at "Add SSH host to known_hosts") | Certain | None — cosmetic | `DEMO_VPS_HOST` repo secret is intentionally empty pre-launch; the build + GHCR push stages still complete green, so the images are ready for `compose pull` once the VPS is up. Failure auto-opens an `incident:demo` issue per merge — consider gating the deploy job on a non-empty `DEMO_VPS_HOST` if the issue noise gets distracting before Day 0. |

---

## §6 · Pre-Launch Decisions Open as of 2026-05-08

These need a decision before Day -5 (Tue May 12) — flagging now so they don't surface on Day -1 (Sat May 16) as blockers.

1. **Domain name.** `demo.studybuddy.app`? Or sub-path on a different parent? Confirm before Day -5 (Tue May 12).
2. **Hetzner location.** Falkenstein (DEU), Helsinki (FIN), or Ashburn (USA)? Pick the closest to your primary demo audience.
3. **Demo data reset cadence.** Nightly? Weekly? Never? — `seed.sh` is idempotent so nightly reset is feasible via cron.
4. **Stripe environment.** Test mode is the recommended default. If a paying-customer demo is planned, decide whether to swap to live mode for that specific demo (and back).
5. **Sentry project.** Reuse the existing prod project with a `demo` environment tag, or create a separate `studybuddy-demo` project? Recommend: reuse + tag.

### Decided 2026-05-08 — closed for the launch

**GitHub tier — stay on Free.** No upgrade needed before Day 0 (Sun May 17).

| Repo | Visibility | Implication for the deploy workflow |
|---|---|---|
| `StudyBuddy_OnDemand` | **public** | Unlimited Actions minutes, unlimited GHCR storage + bandwidth, full branch-protection rules |
| `studybuddy-docs` | private | 2,000 min/mo Actions cap + 500 MB Packages cap — does not affect demo deployment (no Docker images here) |
| `studybuddy_free` | public | Same unlimited capacity as the main repo |

The deploy-demo workflow (`.github/workflows/deploy-demo.yml`) builds + pushes Docker images to GHCR and runs CI on every merge to `main` — both happen against the **public** `StudyBuddy_OnDemand` repo, where Free tier covers everything the demo needs.

**Triggers that will warrant an upgrade later** (none apply on Day 0 / Sun May 17):

| Trigger | Recommended tier | Cost |
|---|---|---|
| `StudyBuddy_OnDemand` goes private (e.g. to hide competitive details when paying customers arrive) | Team | $4/user/month |
| `studybuddy-docs` private-repo Actions usage exceeds 2,000 min/month (very unlikely — markdown CI is cheap) | Team | $4/user/month |
| Second developer joins and needs branch protection + required reviewers in private repos | Team | $4/user/month |
| First school customer asks for SOC 2 evidence / SAML SSO / IP allow lists / audit-log streaming | Enterprise | $21/user/month |
| Want Dependabot security-update auto-merge in private repos | Team | $4/user/month |

**Re-evaluate after first paying customer.** Until then, Free tier saves ~$50–250/month with zero functional cost to the demo path. The only operational note: the deploy workflow uses `secrets.GITHUB_TOKEN` for GHCR pushes (right scopes on Free); if a future workflow in `studybuddy-docs` ever needs to push to GHCR, that one will need a personal access token with `write:packages` scope (still Free, just an extra step).

### Decided 2026-05-09 — closed for the launch

**Tenancy position — StudyBuddy is the second tenant on the shared CX22;
mambakkam.net is the first.** Inverts the 2026-05-08 framing. Concrete
consequences for this runbook:

- StudyBuddy launch on Day 0 (Sun May 17) cuts over at **T-0 = 13:00
  EDT**, four hours after mambakkam.net's 09:00 EDT cutover. The
  four-hour window is the mambakkam-stability gate.
- StudyBuddy `provision.sh` is the second-tenant variant — system
  bootstrap (Docker / UFW / fail2ban / deploy user / host nginx /
  Origin Cert directory) is done by mambakkam.net on Day 0 morning.
- Cron offsets: StudyBuddy backup at 02:00 UTC; mambakkam at 02:30 UTC.
- StudyBuddy joins at zero marginal infra cost on the box; mambakkam.net
  pays the $5/mo VPS bill as the first tenant.
- The Cloudflare Origin Cert (SAN list including `demo.studybuddy.app`)
  is generated up-front by mambakkam.net on Day -1 evening — StudyBuddy
  reuses it without re-issue.

---

## §7 · Observability

The shared CX22 runs a third compose stack — Prometheus +
nginx-prometheus-exporter + blackbox-exporter + node-exporter —
`remote_write`-ing to Grafana Cloud free tier. Dashboards + alerts live on
`<stack>.grafana.net`; no local Grafana. Full design + setup runbook in
[`mambakkam-net/Plans/MONITORING.md`](https://github.com/wegofwd2020-hub/mambakkam-net/blob/main/Plans/MONITORING.md).

**StudyBuddy already exposes `/metrics`** (bearer-token gated; see
[`backend/src/core/observability.py`](../backend/src/core/observability.py)
and the existing dev-time runbook in
[`studybuddy-docs/OBSERVABILITY.md`](https://github.com/wegofwd2020-hub/studybuddy-docs/blob/main/OBSERVABILITY.md)).
The production change is just where it gets scraped from:

| Dev (existing) | Production (this plan) |
|---|---|
| Thittam's local Prometheus on the operator's laptop scrapes `host.docker.internal:8000/metrics` | The CX22's local Prometheus (third tenant, alongside mambakkam + StudyBuddy) scrapes the StudyBuddy compose-internal nginx at `127.0.0.1:8443/metrics` over loopback |
| Bearer token = `dev-metrics-token` | Bearer token = real `METRICS_TOKEN` from `.env.demo` |
| Grafana on `localhost:3130` | Grafana Cloud on `<stack>.grafana.net` (free tier — 10k active series, 13-month retention) |

**Public `/metrics` surface.** The host-nginx vhost
(`infra/nginx/demo.studybuddy.app.conf`) ships a `/metrics` location gated
by:

1. Cloudflare-IP allowlist (drops direct VPS-IP curls)
2. `Cf-Access-Jwt-Assertion` header check (refuses traffic that bypassed Access)
3. The application's own `METRICS_TOKEN` bearer requirement

Cloudflare Access policies for the URL are defined in the Cloudflare
dashboard (out-of-repo). The local Prometheus does NOT use this public
surface — it scrapes loopback — so you can defer Cloudflare Access
configuration past launch without losing observability.

**Launch-timeline placement.** The monitoring stack is brought up by the
operator at **T+30m to T+2h** on Day 0 (between mambakkam-stability
check and StudyBuddy cutover). That way StudyBuddy is observable from
the moment it joins the box at T-0 = 13:00 EDT. Bringing monitoring up
after launch is fine too — scaffolding ships with mambakkam's
`provision.sh`.

Outstanding before observability is "ready":

- Grafana Cloud signup + stack creation (Day -1 evening — already in §1.A.bis-equivalent on the mambakkam plan)
- mambakkam side: `/opt/mambakkam/infra/monitoring/.env.monitoring` populated
- Cloudflare Access policy on `demo.studybuddy.app/metrics`
- Starter dashboards imported (the existing `studybuddy-health` JSON works
  unchanged — just repoint its data source at the Grafana Cloud Prometheus)

---

## §8 · Logging

Sister stack to §7. Full design + LogQL cheatsheet + local-fallback runbook
in [`mambakkam-net/Plans/LOGGING.md`](https://github.com/wegofwd2020-hub/mambakkam-net/blob/main/Plans/LOGGING.md).

**One-paragraph summary:**
Promtail (in the monitoring compose stack on the CX22) tails docker
container logs, host nginx vhost files, journald, and backup-script logs,
then ships everything to Grafana Cloud Loki (50 GB / 14 d free). Same UI
as metrics. StudyBuddy's structlog JSON gets parsed at ingest — `level`
and `logger` become Loki labels so `{project="studybuddy", level="error"}`
gets you the right slice in two keystrokes.

**Application-side change in this PR:** every service in
`docker-compose.demo.yml` now declares `logging: *logging-cap` (json-file
driver, 10 MB × 5 files) so a runaway container can't fill the CX22 disk.
The cap matches what the mambakkam compose already had.

**Local-access fallback** (when Grafana Cloud is unreachable, or you're
already on the box):

```bash
docker logs --tail 200 -f studybuddy-api-1                       # one container
docker compose -f /opt/studybuddy/docker-compose.demo.yml logs -f # whole stack
sudo tail -f /var/log/nginx/demo.studybuddy.app.error.log         # host nginx
journalctl -u sshd --since "1 hour ago"                           # systemd
```

**Launch-timeline placement.** Bring up Promtail alongside the rest of the
monitoring stack at T+30m to T+2h on Day 0. If that gets deferred, the
local fallback above still works — nothing about cutover depends on Loki.

---

## §9 · Backups & Restore

The existing `scripts/demo/backup.sh` was rewritten on 2026-05-09 to use
restic (encrypted, deduped, incremental). Full design + 5-scenario
restore runbook in
[`mambakkam-net/Plans/BACKUPS.md`](https://github.com/wegofwd2020-hub/mambakkam-net/blob/main/Plans/BACKUPS.md).

**One-paragraph summary:**
Daily 02:00 UTC cron does `pg_dump` → restic snapshot of (dump +
`/data/content` + `.env.demo`) → forget. Weekly Sunday 03:00 UTC cron
does `restic check --read-data-subset 5%` + `restic prune`. Repo lives
at `/opt/studybuddy/backups/restic/`, encrypted with password at
`/etc/restic/studybuddy.password` (auto-generated by `provision.sh` step 8
and printed once — operator must record). Forget policy: 7 daily / 4 weekly /
3 monthly / 1 yearly. Local-only repo (same disk as the originals); off-box
deferred until first paying customer per `BACKUPS.md` residual-risk note.

**Restore drill on Day -2 (Fri May 15) of test phase.** Inserted into §4
Day -2 above — Scenario 2 (single content-unit restore) is the must-pass;
Scenario 1 (full DB restore) is run in dry-run mode against the staging
box (don't swap databases on staging or you lose the seed data).

---

## §10 · Alerts

14 alert rules consolidated as YAML in
[`mambakkam-net/infra/monitoring/alerts/`](https://github.com/wegofwd2020-hub/mambakkam-net/tree/main/infra/monitoring/alerts).
Per-alert response procedures + notification routing setup in
[`mambakkam-net/Plans/RUNBOOK.md`](https://github.com/wegofwd2020-hub/mambakkam-net/blob/main/Plans/RUNBOOK.md).

**StudyBuddy-specific alerts (5 of the 14):**

| Alert | Severity | Loki/Mimir |
|---|---|---|
| `StudyBuddyDown` | page | metric (probe_success) |
| `StudyBuddyHighErrorRate` | page | metric (sb_requests_total) |
| `Demo5xxRateHigh` | page | log (host nginx access) |
| `StudyBuddyErrorBurst` | warn | log (structlog level=error) |
| `BackupSilent` | page | log (backup cron silent) |

Plus 3 backup-specific (`ResticCheckFailed`, `ResticPruneFailed`,
`BackupSizeRunaway`) — apply to both sites' restic repos including
StudyBuddy's.

**Routing:** single Gmail to `siva@mambakkam.net` with `[PAGE]` /
`[WARN]` subject prefix; Gmail filters split into separate labels.
Best-effort single-operator coverage; nothing wakes you at 3am.

**Where it fits in the launch timeline.** Same as §7+§8 — bring up
together with the rest of the monitoring stack; one end-to-end test-fire
is a Day -2 (Fri May 15) test-plan gate (see §4 above).

Outstanding:

- Cloud Access Policy token needs `RulesWriter` scope added (Day -1 evening)
- Notification policy + Gmail filters configured per RUNBOOK.md
- One synthetic alert test-fired and received (Day -2 drill)

---

## Change Log

| Date | Change |
|---|---|
| 2026-05-08 | Initial — comprehensive plan for May 16 launch (4 days code freeze + 4 days test phase) |
| 2026-05-08 | §6 — Closed the GitHub-tier decision: stay on Free; document upgrade triggers for future-self |
| 2026-05-08 | §2.5 — Added consolidated Deployment Sequence (cold-start + ongoing-deploy flows + dependency graph + rollback paths + skip-auto-deploy cases) |
| 2026-05-09 | **Tenancy-position flip** — StudyBuddy is now the **second tenant** on the shared Hetzner CX22; mambakkam.net is the first and cuts over four hours earlier the same day. Reframed the top-of-doc tenancy block, §2 launch-day timing (T-0 → 13:00), §2.5 cold-start sequence (~20 min, second-tenant flow), §3.1 provision.sh inventory, Day -1 of §4 test plan. Added §6 "Decided 2026-05-09" block. |
| 2026-05-09 | **Observability** — added §7 pointing to the new `mambakkam-net/Plans/MONITORING.md`. Prod scrape path is now CX22-local Prometheus → Grafana Cloud free tier (was operator-laptop Prometheus + Thittam's local Grafana in dev). Public `/metrics` is Cloudflare-Access-gated; loopback scrape doesn't need any of that. |
| 2026-05-09 | **Logging** — added §8 pointing to the new `mambakkam-net/Plans/LOGGING.md`. Promtail in the monitoring stack ships docker / nginx / journald / backup logs to Grafana Cloud Loki free tier. `docker-compose.demo.yml` now caps every service's json-file driver at 10 MB × 5 via a YAML anchor. |
| 2026-05-09 | **Backups rewritten** — added §9 pointing to `mambakkam-net/Plans/BACKUPS.md`. Replaced rsync+pg_dump+gzip with restic (encrypted + deduped + incremental). New `scripts/demo/backup-check.sh` for weekly integrity check + prune. `scripts/demo/provision.sh` now installs restic, generates the password (printed once), and inits the repo as new step 8. Day -2 restore drill added. Local-only posture; off-box deferred. |
| 2026-05-09 | **Alerts as code** — added §10 pointing to `mambakkam-net/Plans/RUNBOOK.md` and the new `infra/monitoring/alerts/` rule files. 14 consolidated alerts (replacing scattered tables in MONITORING / LOGGING / BACKUPS docs). Two-severity Gmail routing. Day -2 alert-test-fire row added to §4. |
| 2026-05-09 | **Day-N labels + date shift** — launch slipped from May 16 → May 17 (Day 0 = Sun May 17). Day -5 to Day -1 labels added to the 4-day test phase (May 13-16); Day 0 = launch, Day 1 = first day live (May 18). Code-freeze cutoff stays at May 12 EOD (now Day -5). Day-of-week labels in the original timeline corrected (off by one). All section headers + body text updated; companion docs in mambakkam-net/Plans/ shifted in the same pass. |
| 2026-05-09 | **Concrete Day -1 / Day 0 timing** — added Day -1 (Sat May 16) 17:00-20:30 EDT account setup checklist (StudyBuddy-side: domain, Auth0, Stripe-test, Sentry — alongside mambakkam-side shared infrastructure). Day 0 (Sun May 17) 11:00 EDT StudyBuddy second-tenant work begins (after mambakkam mb-T+2h stability), T-0 cutover at 13:00 EDT. Restored the second-tenant launch-day timing that was reverted by an earlier git checkout. |
| 2026-05-09 | **Restored §7-§10 sections lost in the date-shift git checkout** — Tenancy Position block at top of doc, §2.5 second-tenant cold-start, §3.1 second-tenant provision.sh inventory, §4 Day -1 production-join row, §6 "Decided 2026-05-09" block, and §7-§10 sister-doc pointers (Observability / Logging / Backups / Alerts). Preserved the Day-N labels and concrete timing entries that were added afterwards. |
| 2026-05-13 | **Content delivery script consolidation.** Audit found that the three demo asset classes (TEXT lesson JSON, GRAPHICS SVGs, VIDEO tutorial MP4s) weren't fully wired into the deploy path — the sample-visuals tree of 44 tutorial MP4s (219 MB) is gitignored and would have 404'd everywhere. Fixed by (a) `scripts/demo/sync-content.sh` (new) that wraps inject_g11_visuals.py + both rsyncs + optional smoke into a single operator command; (b) nginx /sample-visuals/ location + bind-mount; (c) provision.sh creates /data/sample-visuals alongside /data/content; (d) smoke.sh extended with 3 HEAD checks (lesson JSON + tutorial SVG + tutorial MP4). §3 renumbered to slot sync-content.sh in as §3.2 (operational order: provision → sync-content → seed → smoke). |
| 2026-05-13 | **Launch-blocking CI fixes + universal sign-in shipped.** §1.A: added a "Universal sign-in entry point" row covering the `/signin` page + `POST /auth/universal-login` consolidation of Auth0 / Phase A local / admin tracks; expanded the `deploy-demo.yml` row to call out the `NEXT_PUBLIC_DEMO_MODE=true` Docker `build-arg` that bakes the flag into the client bundle. Added a "Recent CI unblocking" paragraph documenting the four sequential fixes (typescript 6→^5.9.3, lockfile regen under node:20-alpine, `npm ci --legacy-peer-deps`, `next.config.ts output: "standalone"`) that unblocked the previously-red web image build. §5: added a Risk Register row for the expected-but-cosmetic SSH-deploy failure that fires on every push until `DEMO_VPS_HOST` is populated (currently auto-opens an `incident:demo` issue per merge — gate the deploy job if the noise becomes distracting before Day 0). |
