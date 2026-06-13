# Test Cycle Reports — Process

After each QA / test cycle we produce **one Markdown report** to hand back to the
tester (e.g. Venki) and keep as project history. Every report has the same three
sections:

1. **Issues reported & their fixes** — everything the tester raised, and what we did.
2. **Additional features added** — anything new shipped this cycle beyond the reported bugs.
3. **What to test next + accounts** — the regression checklist, new things to exercise,
   and the demo logins to use.

Reports live in [`docs/test-cycles/<YYYY-MM-DD>.md`](.) (one per cycle), generated from
[`TEMPLATE.md`](TEMPLATE.md). The latest is the most recent dated file.

---

## Conventions (do these during the cycle so the report assembles itself)

- **One GitHub issue per reported item**, titled `[Feedback] <summary>`. This title prefix is
  what the generator searches for.
- Optionally tag each issue with a per-cycle label `cycle:<YYYY-MM-DD>` or a **milestone** —
  this lets the generator scope a single cycle precisely instead of "all `[Feedback]` issues".
- **Fixes land via PRs to `main`** that use a closing keyword per issue
  (`Closes #437`, `Closes #438`, …). GitHub then auto-closes the issue on merge and the
  issue ↔ PR link is recorded automatically. (Note: `Closes #437, #438` only closes the
  **first** number — repeat the keyword: `Closes #437, closes #438`.)
- Items that turn out **not** to be defects are closed as *not planned* with a one-line
  rationale comment — they still appear in the report (status: "Not a bug").

## Producing a report

1. **Draft section 1** from GitHub:
   ```bash
   scripts/test_cycle_report.sh              # all [Feedback] issues + state
   scripts/test_cycle_report.sh cycle:2026-06-13   # scoped to one cycle label/milestone
   ```
   This prints a Markdown table of issues + open/closed state. Add the fixing **PR #** to
   each row (find it on the closed issue, or via
   `gh pr list --state merged --search "merged:>=<cycle-start>"`).
2. **Copy the template** to a dated file and fill all three sections:
   ```bash
   cp docs/test-cycles/TEMPLATE.md docs/test-cycles/$(date +%F).md   # run in a real shell
   ```
3. **Section 3 accounts** come from the demo environment. Keep them in sync with the
   account roster (the team's secure note / the demo-credentials reference). Treat the
   shared demo password as **demo-only** — fine to put in this report, but rotate it if the
   demo ever holds real student data.
4. **Commit** on a `docs/test-cycle-<date>` branch → PR → merge (docs-only, CI is fast).
5. **Send** the rendered Markdown to the tester.

## Definition of done for a cycle report

- Every `[Feedback]` issue from the cycle appears in section 1 with a status and (if fixed)
  a PR link.
- Section 3 lists a concrete re-verify step for each fix and the exact accounts to use.
- Still-open items are listed under "Known open / not in this build" so the tester doesn't
  re-report them.
