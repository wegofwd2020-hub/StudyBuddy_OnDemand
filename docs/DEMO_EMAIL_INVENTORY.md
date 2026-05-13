# Demo Email Inventory

**Question this answers:** how many email addresses do I need to create for `demo.studybuddy.app`?

**Short answer:** 1 required, 1 optional — both on the `studybuddy.app` domain via Zoho Mail.

**Setup runbook (procedure):** [`studybuddy-docs/docs/operations/dns-and-email-setup.md`](https://github.com/wegofwd2020-hub/studybuddy-docs/blob/docs/demo-walkthrough/docs/operations/dns-and-email-setup.md) Phases 3 (Zoho), 4 (Gmail send-as), 5 (wire into app).

---

## Mailboxes to Create on `studybuddy.app`

| Address | Required? | Why it exists | Where it's wired |
|---|---|---|---|
| `support@studybuddy.app` | **Required** | All app-outbound transactional email: password resets, demo-account verification links, test-run credentials, weekly teacher digest, alert acks. Also the DMARC `rua=` recipient (deliverability reports). | `.env.demo` → `SMTP_USER=support@studybuddy.app`. Code: `backend/src/email/service.py` lines 147 + 1475. Display name set by `SMTP_FROM_NAME=StudyBuddy`. |
| `sales@studybuddy.app` | Optional | Inbound only — sales inquiries from the "For schools" landing page, info@-style requests. Not wired into the app; you (or whoever) just read this inbox. | Not in `.env.demo` or any code path. Pure receiving inbox. |

Both are created in Zoho Mail per [`dns-and-email-setup.md` Phase 3.3](https://github.com/wegofwd2020-hub/studybuddy-docs/blob/docs/demo-walkthrough/docs/operations/dns-and-email-setup.md). Zoho free tier covers up to 5 mailboxes at 5 GB each, so there's no upgrade cost.

---

## What You Do NOT Need to Create

These already exist or are synthetic — don't waste time provisioning new mailboxes for them.

### Already-existing accounts you reuse

| Email | Purpose |
|---|---|
| `wegofwd2020@gmail.com` (your personal Gmail) | Super-admin login (`scripts/seed_super_admin.py` creates this account in the DB). Also the signup email for every SaaS account you'll create on Day -1: Cloudflare, Hetzner, Zoho, Auth0, Stripe, Sentry, Grafana Cloud, GitHub. Also the Gmail send-as host (per Phase 4) so outbound from the "From: StudyBuddy Support <support@studybuddy.app>" identity is composed from your normal Gmail UI. |
| `siva@mambakkam.net` | Receives Grafana Cloud alerts (`[PAGE]` / `[WARN]` subject-prefix routing). Already needs to exist for the mambakkam.net first-tenant launch; the StudyBuddy alerts (5 of 14) route to the same address. No new studybuddy mailbox needed for alerts. |

### Synthetic database accounts (NOT real mailboxes)

The seed orchestrator (`scripts/demo/seed.sh`) creates persona accounts that exist only as DB rows for login purposes. **Do not** create real mailboxes for these — they'll never receive email in the demo.

| Persona | DB email (synthetic) | Created by |
|---|---|---|
| MilfordWaterford school admin | `sam.houston@milfordwaterford.edu` | `seed_demo_milfordwaterford.py` |
| G11 Commerce teacher (Warren Buffett) | `warren.buffett@milfordwaterford.edu` | `seed_demo_milfordwaterford.py` |
| G11 Commerce student (Anya Iyer) | `anya.iyer@milfordwaterford.edu` | `seed_demo_milfordwaterford.py` |
| 14 other MilfordWaterford students | `<name>@milfordwaterford.edu` | `seed_demo_milfordwaterford.py` |
| Public "Try it" G8 student | `demo-test@studybuddy.dev` | `seed_demo_test_account.py` |
| Phase A dev school admin | configurable | `seed_phase_a_dev.py` |

`milfordwaterford.edu` and `studybuddy.dev` are **not** real domains you control. They exist only as login-identifier strings. The Phase A `first_login=true` forced password reset and email verification flows work against these because all the email functions short-circuit on demo accounts (the app sends to `support@studybuddy.app`'s real mailbox if a real send is required, then logs it).

---

## Cost

| Item | Provider | Monthly |
|---|---|---|
| 1× `support@studybuddy.app` mailbox | Zoho Mail free tier | $0 |
| 1× `sales@studybuddy.app` mailbox (optional) | Zoho Mail free tier | $0 |
| Domain `studybuddy.app` | Cloudflare Registrar | ~$1/mo (annual ÷ 12) |
| Gmail send-as identity for `support@` | Gmail (free) | $0 |
| **Total marginal email cost for the demo** | | **$0** |

---

## Day-of Checklist

When you get to Phase 3 of the setup runbook on Day -1:

- [ ] Zoho org created (use your `wegofwd2020@gmail.com` as the org admin login)
- [ ] Domain `studybuddy.app` verified via TXT record in Cloudflare DNS
- [ ] `support@studybuddy.app` mailbox created and reachable via webmail
- [ ] (Optional) `sales@studybuddy.app` mailbox created
- [ ] MX records pointing to `mx.zoho.com`, `mx2.zoho.com`, `mx3.zoho.com` (priorities 10/20/50)
- [ ] SPF record `v=spf1 include:zoho.com ~all` at the apex
- [ ] DKIM record `zmail._domainkey` with the Zoho-supplied public key
- [ ] DMARC record `_dmarc` with `v=DMARC1; p=quarantine; rua=mailto:support@studybuddy.app`
- [ ] All three (MX/SPF/DKIM) show green checkmarks in Zoho's verification UI
- [ ] Zoho App Password generated for the Gmail send-as integration (store in password manager)
- [ ] `support@studybuddy.app` added as a send-as identity in Gmail (SMTP `smtp.zoho.com:465`, SSL on)
- [ ] `.env.demo` SMTP block populated with the Zoho App Password
- [ ] Forgot-password test from a demo student → reset email arrives `From: StudyBuddy <support@studybuddy.app>` in a real inbox

Verification commands for each step are in [`dns-and-email-setup.md`](https://github.com/wegofwd2020-hub/studybuddy-docs/blob/docs/demo-walkthrough/docs/operations/dns-and-email-setup.md) (each Phase has a "verify" sub-step).
