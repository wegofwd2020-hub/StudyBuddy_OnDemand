# DESIGN EXPLORATION: Multi-Provider LLM Curriculum Generation

**Status:** Thought exercise — not scheduled for implementation
**Date:** 2026-04-01

---

## Overview

This document captures the design exploration around allowing schools to choose which LLM
provider(s) generate their curriculum content, and to compare outputs side-by-side before
committing to a version.

**Verdict: Pragmatic. The existing architecture is unusually well-positioned for this.**

---

## Is This Pragmatic?

Yes, with caveats. The core idea — letting schools choose their LLM provider and compare
outputs — is sound. Market reality supports it: schools increasingly have existing vendor
relationships (Microsoft, Google), data residency requirements, or policy restrictions on
specific AI providers. Offering choice removes a procurement blocker.

The existing architecture is better positioned for this than most platforms would be:

| Existing capability | Why it helps |
|---|---|
| Pipeline has a single LLM call point (`_call_claude()` in `prompts.py`) | Provider swap is a localized change — one abstraction layer, not a rewrite |
| Content Store schema is provider-agnostic | Any provider that outputs conformant JSON can write to the same store |
| `content_subject_versions` already tracks multiple versions per subject | Adding a `provider` column turns version comparison into provider comparison |
| Version diff UI already exists | The "compare two versions" mental model maps directly to "compare two providers" |
| Admin review workflow already gates publishing | Schools reviewing provider outputs fits naturally into the same review step |
| Pipeline is already async / Celery-based | Running multiple providers in parallel is an orchestration change, not an architecture change |

---

## Why an AI Agent Is NOT the Right Pattern Here

A key architectural conclusion from this exploration: **an AI agent dynamically assembling
curriculum content at runtime is incompatible with the year-long stability requirement.**

### The Core Tension

An AI agent is designed for dynamic, context-driven decisions at runtime. The curriculum
requirement is the opposite — stable, auditable, human-approved content locked in before
the academic year starts.

| | AI Agent (dynamic) | StudyBuddy Pipeline (batch) |
|---|---|---|
| When content is generated | On demand, at runtime | Once, before the academic year |
| Determinism | Non-deterministic by nature | Same input → same output, versioned |
| Human review gate | Hard to enforce | Mandatory — admin approves before publish |
| Consistency across students | Not guaranteed | Guaranteed — all students see the same version |
| Auditability (FERPA) | Complex — what did the agent decide and why? | Clean — version_id, provider, timestamp, approver |
| Teacher preparation | Impossible — content shifts under them | Teachers review curriculum before term starts |

### The Correct Model

```
Before academic year starts:
  → Trigger batch build (Provider A + Provider B)
  → Human reviews both outputs side by side
  → Human picks one (or cherry-picks per unit)
  → That version is locked and published
  → Students see it all year

Mid-year corrections:
  → Patch only (typos, factual errors, language)
  → Same subject scope — no structural changes
  → Goes through the same review gate before republishing
```

The batch pipeline — whichever provider runs it — is the only path to published content.
The agent never touches live curriculum.

### Where MCP / Agent Tooling Could Fit (Narrowly)

MCP (Model Context Protocol) would only be relevant if a future phase built an
**AI-powered admin assistant** — e.g., a Claude-powered agent embedded in the admin
console that helps school admins *manage* the pipeline (not generate content):

> *"Compare the Grade 8 Science curriculum across Anthropic and OpenAI and show me
> which one had fewer AlexJS warnings."*
> *"Trigger a comparison build for Grade 7 Math and notify me when it's done."*

In that scenario the MCP server would wrap management API calls only
(`trigger_build`, `check_status`, `approve_version`). The underlying pipeline
would still be the same batch process. This is a Phase F concern at earliest.

```
School Admin (human)
    ↓  clicks UI
Next.js → REST API → Celery pipeline

School Admin (talks to AI assistant)  [future only]
    ↓  natural language
Claude Agent → MCP Server (tool wrappers) → REST API → Celery pipeline
```

---

## Architecture Dimensions

### 1. Provider Abstraction Layer (Pipeline)

Replace `_call_claude()` with a `LLMProvider` interface:

```
pipeline/providers/
  base.py          ← abstract LLMProvider(generate(prompt, schema) → dict)
  anthropic.py     ← current Claude implementation
  openai.py        ← GPT-4o
  google.py        ← Gemini 1.5 Pro
  config.py        ← maps provider_id → class, API key env var
```

`build_unit.py` and `build_grade.py` accept `--provider anthropic|openai|google`
(or a list for multi-provider comparison builds).

**Key constraint:** Prompts tuned for Claude will not yield equivalent quality from
other providers. Each provider needs its own prompt variant. The `prompts.py` module
would need to become provider-aware (`get_prompt(content_type, provider_id)`).

---

### 2. Data Model Changes

**`content_subject_versions` — add `provider` column:**
```sql
provider  VARCHAR(50)  NOT NULL  DEFAULT 'anthropic'
          -- values: 'anthropic', 'openai', 'google', 'school_upload'
```

**New table: `school_llm_config`:**
```sql
school_id           UUID FK → schools
allowed_providers   JSONB       -- ["anthropic", "openai"]
default_provider    VARCHAR(50)
comparison_enabled  BOOLEAN     DEFAULT false
dpa_acknowledged_at TIMESTAMPTZ -- per-provider DPA acceptance timestamp
```

**New table: `provider_comparison_runs`:**
```sql
run_id          UUID PK
school_id       UUID FK
curriculum_id   UUID FK
unit_id         VARCHAR
providers       JSONB       -- ["anthropic", "openai"]
triggered_by    UUID FK → admin_users / teachers
status          VARCHAR     -- pending, running, complete, failed
created_at      TIMESTAMPTZ
```

---

### 3. School-Level Provider Selection (Admin + School Portal)

**School admin flow:**
1. School admin navigates to Settings → Curriculum AI Providers
2. Sees a list of available providers with their data processing agreements
3. Acknowledges DPA per provider (timestamp recorded — FERPA requirement)
4. Sets a default provider for new curriculum builds
5. Optionally enables "comparison mode" — builds run against 2 providers before publishing

**Comparison build trigger:**
- Admin or teacher selects a unit/subject → "Run comparison build"
- Celery dispatches parallel pipeline tasks, one per provider
- Each writes to the Content Store under its own `version_id` (tagged with `provider`)
- When both complete, the comparison view becomes available

---

### 4. Comparative Review UI

Extends the existing version diff view (`/admin/content-review/{version_id}/diff`):

**New route:** `/admin/content-review/compare?unit_id=X&providers=anthropic,openai`

| Feature | Detail |
|---|---|
| Side-by-side panel | Provider A left, Provider B right (same layout as version diff) |
| Per-section scoring | Optional: admin rates each section (1–5) per provider |
| "Use this provider for unit" | Cherry-pick per unit, not just per subject |
| "Set as school default" | Promotes one provider's output as the active version |
| Quality metadata | Show token counts, generation time, AlexJS warnings per provider |

**School teacher flow (if enabled):**
- Teacher opens a unit in the curriculum viewer
- Sees a "Provider comparison available" banner
- Can view the comparison and vote/recommend (not approve — that's admin)

---

### 5. Cost Management

Running 2–3 providers per curriculum build is a significant cost multiplier.

**Mitigation options:**

| Option | Trade-off |
|---|---|
| Comparison builds only on request (not default) | Reduces cost; schools opt in per unit |
| Comparison available only at school's own expense | Schools on a higher tier or pay-per-comparison |
| Sample comparison: 1 unit per subject, not whole grade | School gets a taste without full cost |
| Cache comparison results aggressively | Comparison outputs cached indefinitely until a new build is explicitly triggered |

The existing `MAX_PIPELINE_COST_USD` spend cap should be extended to
`MAX_PIPELINE_COST_USD_PER_SCHOOL` with per-school overrides in `school_llm_config`.

---

### 6. Data Privacy & Compliance (Critical)

This is the sharpest constraint. Sending school curriculum specifications to a
third-party LLM provider constitutes data sharing under FERPA if the curriculum
specs contain any student context (e.g., personalised difficulty scaffolding).

**Requirements before enabling a provider:**
- School must review and acknowledge the provider's data processing agreement (DPA)
- DPA acknowledgement timestamped and stored per-provider in `school_llm_config`
- Default curriculum builds (no student context) are lower risk — still require DPA
- Never send student PII to any LLM provider as part of prompt construction
- Providers must be contractually prohibited from training on school data

**Anthropic baseline:** Schools already implicitly accept Anthropic's terms when
subscribing to StudyBuddy. New providers require explicit opt-in.

---

### 7. JSON Schema Conformance Risk

Claude is unusually reliable at structured JSON output against a defined schema.
Other providers vary:

| Provider | Structured output reliability | Notes |
|---|---|---|
| Anthropic Claude 3.x+ | High | Current baseline |
| OpenAI GPT-4o | High | JSON mode + function calling |
| Google Gemini 1.5 Pro | Medium-High | Improved in 1.5; still needs retries |
| Smaller / open models | Low-Medium | Not recommended for initial release |

The existing 3× retry + validation loop in `build_unit.py` is necessary for all
providers. Per-provider failure rates should be tracked in the `pipeline_jobs` table
(add `provider` and `validation_retry_count` columns).

---

### 8. Prompt Parity Work (Most Underestimated Risk)

The current prompts are calibrated for Claude's instruction-following and output length
characteristics. Achieving equivalent curriculum quality from another provider requires:

- Separate prompt variants per provider (not just system prompt tweaks)
- Evaluation rubric: what does "equivalent quality" mean for a Grade 8 science lesson?
- Human review baseline: at least 50 units evaluated per provider before enabling for schools
- Regression detection: if a provider update degrades quality, the pipeline must alert

**Recommendation:** Treat prompt parity as a separate workstream from the pipeline
abstraction. The abstraction layer can ship first; provider enablement gates on parity
validation.

---

## Phasing Recommendation

| Phase | Scope | Unlocks |
|---|---|---|
| A | Pipeline abstraction layer + OpenAI provider | Internal comparison builds only |
| B | `provider` column in versions table + comparison run tracking | Admin can see provider metadata in review queue |
| C | Comparative review UI (admin only) | Internal evaluation of provider quality |
| D | School-level provider config + DPA acknowledgement flow | Schools can opt into a second provider |
| E | Teacher-facing comparison view + per-unit provider selection | Full school self-service |
| F | MCP server wrapping admin pipeline tools (optional, future) | AI assistant for admin pipeline management only — not content generation |

Phases A–C are internal and low-risk. Phase D is where compliance and commercial
agreements become the gating factor.

---

## Open Questions

1. **Pricing model:** Is multi-provider a premium tier feature, or included in the school plan?
2. **Provider SLA:** If a provider API is down, does the school's curriculum build fail or fall back to the default?
3. **Model pinning:** Schools must pin a specific model version, not "latest", to ensure curriculum reproducibility year-over-year — same rule as the existing `CLAUDE_MODEL` pin.
4. **Audit trail:** When a school publishes content generated by Provider X, is the provider identity surfaced to students or teachers? (Probably not, but worth deciding explicitly.)
5. **Fine-tuning path:** Some providers offer fine-tuning. Is there a future phase where schools fine-tune a model on their own uploaded curriculum? (Very high complexity — flag for later.)

---

## Related Documents

- [ARCHITECTURE.md](ARCHITECTURE.md) — Pipeline section, Content Store layout
- [BACKEND_ARCHITECTURE.md](BACKEND_ARCHITECTURE.md) — Celery dispatcher, pipeline jobs
- [REQUIREMENTS.md](REQUIREMENTS.md) — Phase 8 school/curriculum requirements
- [CHANGES.md](CHANGES.md) — Log design decisions here when this moves to implementation
