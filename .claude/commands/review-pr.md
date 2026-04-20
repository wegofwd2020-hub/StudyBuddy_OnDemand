---
description: Run /review + /security-review on the current branch diff and compile findings.
---

Run the built-in review and security-review skills on the current branch's diff against `main`, then compile a single prioritised report.

## Step 1 — Confirm scope

```bash
git log main..HEAD --oneline
git diff --stat main...HEAD
```

If the diff is empty, stop — there's nothing to review. If it's enormous (>1000 lines), ask whether to narrow scope before proceeding (large reviews produce shallow findings).

## Step 2 — Run both reviews

Invoke, in order:

1. **`/security-review`** — the built-in security-review skill. Focus on OWASP top 10, secret handling, RLS bypass, auth track confusion (pitfall #13), Stripe signature verification (pitfall #8), entitlement gating location (pitfall #10).

2. **`/review`** — the built-in code review skill. General code quality, adherence to CODING_RULES (money-as-Decimal Rule #1, idempotency Rule #5, fire-and-forget Rule #6, audit Rule #7, structured logging Rule #12).

Run them sequentially (each returns a summary) — combined they usually surface non-overlapping findings.

## Step 3 — Deduplicate and prioritise

Merge findings from both into one table:

| Severity | Area | Finding | Source | File:line |
|---|---|---|---|---|
| 🔴 block | security | ... | security-review | ... |
| 🟠 fix-before-merge | correctness | ... | review | ... |
| 🟡 follow-up | style | ... | review | ... |

Severity rubric:
- **🔴 block** — the PR should not merge as-is (security hole, data loss risk, contract break)
- **🟠 fix-before-merge** — merge would work but a real bug is present
- **🟡 follow-up** — nit / future cleanup / optional improvement

## Step 4 — Cross-check the StudyBuddy-specific pitfalls

Regardless of what the skills say, confirm:

- [ ] Mobile/web does NOT call Anthropic or Stripe directly (pitfall #1, #10)
- [ ] No blocking calls on the async event loop (pitfall #2)
- [ ] Audio served via pre-signed URL, not streamed through FastAPI (pitfall #3)
- [ ] Progress/analytics writes are fire-and-forget (pitfall #4)
- [ ] Stripe webhook verifies signature + dedupes by `stripe_event_id` (pitfall #8, #9)
- [ ] Idempotency key support on POST endpoints (Rule #5)
- [ ] `attempt_number` computed server-side (pitfall #12)
- [ ] RLS bypass pattern used where required (pitfall #23); RLS tests use `studybuddy_rls_tester`
- [ ] Migration: full downgrade→upgrade cycle proven (pitfall #27)
- [ ] CLAUDE.md + top pitfalls grid updated if new migration / new pitfall

Add any of these that fail as findings in the table.

## Step 5 — Do NOT auto-fix

Surface the findings; let me decide which to act on. If the user asks you to fix afterwards, handle them one at a time with small commits — not one sweeping commit.

## Note on sub-agents

If the built-in skills are unavailable in the current session, fall back to spawning `Agent(subagent_type: "general-purpose")` with the security-review prompt and a second `Agent` with a code-review prompt, running them in parallel.
