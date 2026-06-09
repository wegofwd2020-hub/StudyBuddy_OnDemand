# ADR-006 — Multi-Provider LLM Curriculum Generation

**Date:** 2026-06-09 (formalizes a decision shipped 2026-04-12)
**Status:** Accepted (implemented as Epic 1, migration 0043)
**Branch at decision:** `docs/adr-006-multi-provider-llm`

---

## Context

Schools and districts often have a **procurement constraint or preference** about
which AI vendor processes their data (an approved-vendor list, a region/DPA
requirement, or a stated preference for OpenAI/Google over Anthropic). Locking the
content pipeline to a single provider turns that into a deal-blocker. We also
wanted the option to **compare provider outputs** for the same unit before
publishing.

The existing architecture was unusually well-positioned for this (see the
background exploration, [`DESIGN_EXPLORATION_MULTI_PROVIDER_LLM.md`](DESIGN_EXPLORATION_MULTI_PROVIDER_LLM.md)):

- The Content Store schema is **provider-agnostic** — any provider that emits
  conformant JSON writes to the same store.
- `content_subject_versions` already tracks **multiple versions per subject**, and
  a word-level **version-diff UI** already exists → "compare two versions" maps
  directly onto "compare two providers".
- The **admin review workflow** already gates publishing.
- The pipeline is **async / Celery-based**, so running providers in parallel is an
  orchestration change, not an architecture change.

The competing framing — an **interactive "AI agent"** that generates on demand —
was considered and rejected: it breaks auditability (what did the agent decide and
why?), pre-generation/caching, cost predictability, and the FERPA-clean
`(version_id, provider, timestamp, approver)` record. The **batch pipeline remains
the only path to published content.**

## Decision

### Decision 1 — Provider abstraction layer in the pipeline
`pipeline/providers/` exposes an `LLMProvider` ABC with concrete
`AnthropicProvider`, `OpenAIProvider`, `GeminiProvider`, resolved through a
`get_provider(provider_id)` registry. `build_grade.py` / `build_unit.py` take a
`--provider` flag (or a list for comparison builds). Each provider's `generate()`
sets `max_tokens=16384` (Epic 11). The Claude model id stays pinned in
`pipeline/config.py` (`CLAUDE_MODEL`); provider model ids come from env
(`OPENAI_MODEL` default `gpt-4o`, `GEMINI_MODEL` default `gemini-1.5-pro`,
`DEFAULT_PROVIDER` default `anthropic`).

### Decision 2 — `provider` recorded on content + jobs (migration 0043)
A `provider` column is added to `content_subject_versions` **and** `pipeline_jobs`
(migration 0043; default `'anthropic'`). Pipeline idempotency keys on provider, so
the same unit can carry one version per provider, and the existing version-diff UI
becomes provider-comparison. A `ProviderBadge` chip shows the provider on the
content-review queue.

### Decision 3 — School-level provider config + DPA (FERPA), RLS-scoped
A `school_llm_config` table (RLS, tenant-scoped) holds a school's allowed
providers + default provider, exposed via `GET/PUT /api/v1/schools/{id}/llm-config`.
**DPA acknowledgements are stored as an append-only JSONB log of per-provider
timestamps** — a FERPA requirement (record of who accepted which vendor's data
processing agreement, when). Never overwrite; always append.

### Decision 4 — Comparison builds are a sequential loop, not a new orchestrator
`run_grade(providers=[...])` runs each provider in an outer sequential loop, each
writing its own `content_subject_versions` row. No `provider_comparison_runs`
table was needed (the exploration floated one); the existing version model
suffices.

### Decision 5 — NOT an AI agent
Published content is only ever produced by the batch pipeline + admin review gate.
Agent/MCP tooling, if ever added, is confined to *authoring assistance* upstream of
the pipeline — never the publish path.

## Consequences

### Positive
- Removes the single-vendor procurement blocker; schools pick an approved provider.
- Provider comparison reuses the version/diff/review machinery — near-zero new UI.
- FERPA-clean provenance: every published version carries `(version_id, provider,
  timestamp, approver)`; DPA acceptance is auditable.

### Negative
- **Prompt parity is not guaranteed across providers** — a prompt tuned for Claude
  may underperform on GPT/Gemini. `prompts.py` may need provider-aware variants;
  comparison builds are the mitigation (review before publish).
- Three SDKs + three sets of API keys/costs to manage; spend cap logic must hold
  per provider.

### Neutral
- Anthropic remains the default; multi-provider is opt-in per school via
  `school_llm_config`. No behavior change for schools that don't configure it.

## Alternatives considered
- **Interactive AI agent (generate-on-demand)** — rejected: breaks auditability,
  caching, cost predictability, and FERPA provenance (see Context).
- **Single-provider lock-in (status quo)** — rejected: procurement blocker; no
  comparison path.
- **Dedicated `provider_comparison_runs` table** — rejected as unnecessary; the
  existing `content_subject_versions` multi-version model already expresses it.

## Migration / rollout
- Shipped as **Epic 1** (F-1 … F-5, 19 tests) on 2026-04-12; **migration 0043**
  adds the `provider` columns + `school_llm_config`.
- See [`docs/epics/EPIC_01_multi_provider_llm.md`](epics/EPIC_01_multi_provider_llm.md)
  for the deliverable breakdown and [`DESIGN_EXPLORATION_MULTI_PROVIDER_LLM.md`](DESIGN_EXPLORATION_MULTI_PROVIDER_LLM.md)
  for the full exploration.
- This ADR formalizes an already-shipped decision (the work predated the ADR).

> **Naming note:** Mentible (the `StudyBuddy_SelfLearner` repo) has its own,
> separate `ADR-005-multi-provider-llm-support.md` governing *its* provider support.
> This ADR-006 is StudyBuddy OnDemand's; the two are independent.
