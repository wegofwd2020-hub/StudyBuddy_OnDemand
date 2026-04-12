# Epic 2 — Production Launch & Demo Readiness

**Status:** 💭 Your call

---

## What it is

Everything needed to go from "works in Docker on localhost" to "ready for a real
school or investor demo" — infrastructure, observability, data seeding, and the
paper cuts that block a confident demo.

---

## Current state

The platform is feature-complete. Dev environment runs via `./dev_start.sh` with
Docker Compose. No production deployment exists yet. The following gaps are known:

**Infrastructure not yet built:**
- No cloud deployment (no Kubernetes manifests, no Terraform, no managed DB)
- No production Redis with AOF persistence configured
- No CDN (CloudFront) wired for audio/content delivery
- No domain, TLS, or DNS configured
- No CI/CD pipeline beyond local test runs

**Demo readiness gaps:**
- No seed data for a compelling demo school (realistic teachers, students, classrooms, curriculum)
- No "demo mode" that resets to a clean state between demos
- Admin pipeline jobs table works but no example jobs are pre-populated
- Help widget live (requires real Voyage AI + Anthropic keys connected)

**Observability:**
- `/healthz` and `/readyz` endpoints exist; Prometheus `/metrics` exposed
- No Grafana dashboards configured
- No alerting rules set up
- No log aggregation (structured JSON logged to stdout only)

---

## Why it matters

Without this epic, the platform can't be shown to a paying customer or investor
with confidence. It also blocks a production pilot with a real school.

---

## Rough scope

| Phase | What gets built |
|---|---|
| G-1 | Cloud deployment: Dockerfile hardening, K8s manifests (or Fly.io/Railway for simpler start), managed Postgres + Redis |
| G-2 | CI/CD: GitHub Actions — lint → test → build → deploy on merge to main |
| G-3 | Demo seed script: one school, 3 teachers, 30 students, 4 classrooms, pre-built curriculum, realistic progress data |
| G-4 | Observability: Grafana dashboards for API latency, error rate, pipeline job status, help widget usage |
| G-5 | Demo reset endpoint: admin-only `POST /admin/demo/reset` that wipes and re-seeds demo data |

---

## Open questions

1. **Deployment target:** K8s (full control, complex) vs Fly.io/Railway (fast, less control) vs AWS ECS (middle ground)? What's the budget and ops maturity?
2. **Managed DB:** AWS RDS, Neon, Supabase, or self-managed? pgvector availability varies by provider.
3. **Demo vs pilot:** Is the goal a polished investor demo (controlled environment), or a real school pilot (production traffic from day one)?
4. **Domain:** Is a domain already purchased? What's the branding/URL?
5. **Auth0 tenant:** Dev Auth0 tenant is used today — does a production tenant exist?
6. **Stripe:** Is the Stripe account in live mode or test mode? Any live keys provisioned?
7. **Content pipeline keys:** Are Anthropic + Voyage AI + TTS keys provisioned for production use?

---

## Your decisions / notes

> Add your thoughts here. Even rough bullet points are enough to start.

-
-
-
