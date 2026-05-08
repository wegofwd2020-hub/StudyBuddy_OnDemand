---
description: Draft a new ADR with the project template, correct numbering, and today's date.
---

You are drafting a new Architecture Decision Record titled: **$ARGUMENTS**

## Step 1 — Find the next ADR number

```bash
ls docs/ADR_*.md 2>/dev/null | sort | tail -1
```

Current ADRs use the format `docs/ADR_NNN_<slug>.md`. If the last is `ADR_001_*`, the new one is `ADR_002_<slug>.md`.

Slug: `snake_case`, derived from the title, under ~40 chars.

## Step 2 — Read ADR-001 for exact structure

```bash
head -80 docs/ADR_001_tenancy_and_subscription_model.md
```

Match its header block (Date / Status / Branch at decision) and its section ordering.

## Step 3 — Draft the ADR

Use this skeleton, adapted to match ADR-001's conventions:

```markdown
# ADR-NNN — <title from $ARGUMENTS>

**Date:** <today's date, YYYY-MM-DD>
**Status:** Proposed
**Branch at decision:** <current git branch>

---

## Context

<The forces at play. Business and technical. What existing state or constraint
is driving this decision? What did we try, or what is broken?>

## Decision

<The specific choice. Be concrete — name tables, endpoints, packages. If there
are multiple sub-decisions, number them (Decision 1 / Decision 2 / ...).>

## Consequences

### Positive
- ...

### Negative
- ...

### Neutral
- ...

## Alternatives considered

- **<Option A>** — rejected because <reason>. <Link to experiment or prior discussion if any.>
- **<Option B>** — rejected because <reason>.

## Migration / rollout

<How does this decision land in the codebase? New migrations? Deprecations?
A sequenced rollout? Reference specific PRs/commits if they exist.>
```

## Step 4 — Show me the draft

Show the complete draft. **Do not commit until I approve it.**

## Step 5 — After approval

- Write the file to `docs/ADR_NNN_<slug>.md`
<!-- doc-audit:ignore -->
- If `docs/adr/index.md` or a similar index exists, add an entry. (Currently the project has only ADR-001; there's no index yet. If this is ADR-002, ask whether to create an index now.)
- The status flips from `Proposed` → `Accepted` only after the corresponding code lands. Don't pre-flip.
