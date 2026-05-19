# Demo Email Inventory

**Question this answers:** how many email addresses do I need to create for `demo.usestudybuddy.com`?

**Short answer:** 1 forwarding alias — `support@usestudybuddy.com` via **Cloudflare Email Routing** → `wegofwd2020@gmail.com`. Outbound send-as from `support@usestudybuddy.com` is deferred post-launch (see §"Outbound send-as deferred" below).

> **History — pivoted at launch (2026-05-17/18):**
>
> - Domain was originally `studybuddy.app`; renamed to `usestudybuddy.com` across the codebase + DNS (commit `8329913`). Every email address mentioned below uses the new domain.
> - Mail provider was originally **Zoho Mail** (per the §"Day-of Checklist" below, kept as historical context); pivoted to **Cloudflare Email Routing** (commit `761e5cb`) once Zoho's domain-verification friction outweighed the value of having a real mailbox at the address. The Day -1 instructions below are no longer the live setup; the live setup is described in §"Current setup — Cloudflare Email Routing" (below).
> - Gmail send-as for `support@usestudybuddy.com` is **deferred** (per memory `launch-gmail-sendas-deferred`): Gmail forced the SMTP form despite the alias being pre-checked, and Cloudflare Email Routing has no outbound SMTP. App-outbound email is currently composed `From: wegofwd2020@gmail.com` via the SMTP App Password.

**Setup runbook (procedure):** [`studybuddy-docs/docs/operations/dns-and-email-setup.md`](https://github.com/wegofwd2020-hub/studybuddy-docs/blob/docs/demo-walkthrough/docs/operations/dns-and-email-setup.md) Phase 3 was Zoho-based; **the live setup deviates** — see Cloudflare Email Routing section below for the actual Day 0 sequence.

---

## Current setup — Cloudflare Email Routing (live 2026-05-18 onwards)

- **CF dashboard** → `usestudybuddy.com` zone → Email → Email Routing → **Enable**
- **Catch-all rule:** `*@usestudybuddy.com` → `wegofwd2020@gmail.com` (verified destination)
- **MX records** managed by CF automatically (`route1.mx.cloudflare.net.` etc.)
- **SPF:** `v=spf1 include:_spf.mx.cloudflare.net ~all`
- **DMARC:** `v=DMARC1; p=none; rua=mailto:wegofwd2020@gmail.com` (relaxed since no real outbound from @usestudybuddy.com yet)

**App-side `.env.demo` SMTP block** (outbound — uses Gmail App Password as the relay):

```
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=wegofwd2020@gmail.com
SMTP_PASSWORD=<gmail-app-password-from-myaccount.google.com/apppasswords>
SMTP_FROM_NAME=StudyBuddy
```

Outbound mail from the demo (verification links, credentials, password resets, weekly digest) currently sends from `wegofwd2020@gmail.com` directly. Once `support@usestudybuddy.com` send-as lands (post-launch — needs a paid mail provider like Migadu/Fastmail or a custom Postfix relay), update `SMTP_USER` accordingly and the headers will switch to the branded identity.

---

---

## Mailboxes to Create on `usestudybuddy.com`

| Address | Required? | Why it exists | Where it's wired |
|---|---|---|---|
| `support@usestudybuddy.com` | **Required** | All app-outbound transactional email: password resets, demo-account verification links, test-run credentials, weekly teacher digest, alert acks. Also the DMARC `rua=` recipient (deliverability reports). | `.env.demo` → `SMTP_USER=support@usestudybuddy.com`. Code: `backend/src/email/service.py` lines 147 + 1475. Display name set by `SMTP_FROM_NAME=StudyBuddy`. |
| `sales@usestudybuddy.com` | Optional | Inbound only — sales inquiries from the "For schools" landing page, info@-style requests. Not wired into the app; you (or whoever) just read this inbox. | Not in `.env.demo` or any code path. Pure receiving inbox. |

Both are created in Zoho Mail per [`dns-and-email-setup.md` Phase 3.3](https://github.com/wegofwd2020-hub/studybuddy-docs/blob/docs/demo-walkthrough/docs/operations/dns-and-email-setup.md). Zoho free tier covers up to 5 mailboxes at 5 GB each, so there's no upgrade cost.

---

## What You Do NOT Need to Create

These already exist or are synthetic — don't waste time provisioning new mailboxes for them.

### Already-existing accounts you reuse

| Email | Purpose |
|---|---|
| `wegofwd2020@gmail.com` (your personal Gmail) | Super-admin login (`scripts/seed_super_admin.py` creates this account in the DB). Also the signup email for every SaaS account you'll create on Day -1: Cloudflare, Hetzner, Zoho, Auth0, Stripe, Sentry, Grafana Cloud, GitHub. Also the Gmail send-as host (per Phase 4) so outbound from the "From: StudyBuddy Support <support@usestudybuddy.com>" identity is composed from your normal Gmail UI. |
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

`milfordwaterford.edu` and `studybuddy.dev` are **not** real domains you control. They exist only as login-identifier strings. The Phase A `first_login=true` forced password reset and email verification flows work against these because all the email functions short-circuit on demo accounts (the app sends to `support@usestudybuddy.com`'s real mailbox if a real send is required, then logs it).

---

## Cost

| Item | Provider | Monthly |
|---|---|---|
| 1× `support@usestudybuddy.com` mailbox | Zoho Mail free tier | $0 |
| 1× `sales@usestudybuddy.com` mailbox (optional) | Zoho Mail free tier | $0 |
| Domain `usestudybuddy.com` | Cloudflare Registrar | ~$1/mo (annual ÷ 12) |
| Gmail send-as identity for `support@` | Gmail (free) | $0 |
| **Total marginal email cost for the demo** | | **$0** |

---

## Day-of Checklist

When you get to Phase 3 of the setup runbook on Day -1:

- [ ] Zoho org created (use your `wegofwd2020@gmail.com` as the org admin login)
- [ ] Domain `usestudybuddy.com` verified via TXT record in Cloudflare DNS
- [ ] `support@usestudybuddy.com` mailbox created and reachable via webmail
- [ ] (Optional) `sales@usestudybuddy.com` mailbox created
- [ ] MX records pointing to `mx.zoho.com`, `mx2.zoho.com`, `mx3.zoho.com` (priorities 10/20/50)
- [ ] SPF record `v=spf1 include:zoho.com ~all` at the apex
- [ ] DKIM record `zmail._domainkey` with the Zoho-supplied public key
- [ ] DMARC record `_dmarc` with `v=DMARC1; p=quarantine; rua=mailto:support@usestudybuddy.com`
- [ ] All three (MX/SPF/DKIM) show green checkmarks in Zoho's verification UI
- [ ] Zoho App Password generated for the Gmail send-as integration (store in password manager)
- [ ] `support@usestudybuddy.com` added as a send-as identity in Gmail (SMTP `smtp.zoho.com:465`, SSL on)
- [ ] `.env.demo` SMTP block populated with the Zoho App Password
- [ ] Forgot-password test from a demo student → reset email arrives `From: StudyBuddy <support@usestudybuddy.com>` in a real inbox

Verification commands for each step are in [`dns-and-email-setup.md`](https://github.com/wegofwd2020-hub/studybuddy-docs/blob/docs/demo-walkthrough/docs/operations/dns-and-email-setup.md) (each Phase has a "verify" sub-step).
