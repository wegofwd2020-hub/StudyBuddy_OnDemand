---
description: Draft a PR description with What/Why/Alternatives/Risk/Test plan. Stops for user input on the sections that can't be inferred.
---

You are drafting the PR description for the current branch. The template has five sections — three you can fill from the diff + git log, two that need user input (Alternatives + Risk) because they reflect decisions that don't leave traces in the code.

## Step 1 — Gather context

```bash
git log main..HEAD --oneline
git diff --stat main...HEAD
git diff main...HEAD -- '*.md' '*.py' '*.ts' '*.tsx' | head -200
```

If `git log main..HEAD` is empty, stop — there's nothing to describe.
If the diff is >1000 lines, summarize by file group rather than content (reviewers won't read it anyway; a huge diff is itself a finding worth flagging).

## Step 2 — Infer what you can

### "What changed" — from the diff

One short paragraph. Not a commit list. Describe the *shape* of the change:
- "Adds X endpoint + its migration + the persona test"
- "Refactors Y service to pull Z from Vault instead of env"
- "Removes the legacy teacher tier (3 tables, 14 endpoints, 210 LOC)"

Avoid restating the title or the issue. The reader clicked the PR already.

### "Why" — from the branch name + commit messages + referenced issue

- If the branch references an issue (e.g., `feat/foo-123`), pull the issue title/body
- If commits reference an issue (`Refs #N`), read that issue
- If neither, infer from the commit messages themselves

The "why" answers: what breaks or what's missing if this doesn't land?

### "Test plan" — from the diff scope

Bulleted checklist. Derive from what was touched:
- New endpoint → manual curl/httpie command + automated test name
- New migration → `alembic upgrade head` + `downgrade -1` + re-upgrade proof (pitfall #27)
- Web change → Playwright spec name or manual browser check path
- Config/hook change → live-trigger proof

## Step 3 — STOP for user input

Show me the draft of sections 1, 2, 5 (What / Why / Test plan). For sections 3 and 4, show placeholders and ask me directly:

**Section 3 — Alternatives considered.** Ask me:
> What options did you weigh? For each, name it + one-line rejection reason. If you considered nothing, say so honestly — an empty "Alternatives" section is more useful than a fabricated one. Reviewers trust "I didn't consider alternatives because this was the only viable path" more than fake balance.

**Section 4 — Risk.** Prompt me with specifics inferred from the diff:
- Migration touched? → "Downgrade tested? Data loss on downgrade?"
- RLS policy changed? → "Tenant isolation still holds?"
- Secret/auth surface touched? → "Attack vectors considered?"
- Hot path touched (content serving, progress writes)? → "Latency regression possible?"
- External contract (OpenAPI, Stripe, Auth0)? → "Consumer drift?"
- Nothing in the above buckets? → "Blast radius is limited to <scope>; here's what could still break:"

Risk is the section reviewers scan hardest. An honest "low risk — touches only `.claude/commands/`" beats a hedge-everything paragraph.

## Step 4 — Assemble final body

Produce a clean, copy-paste-ready markdown block using this exact structure:

```markdown
## What changed

<paragraph from Step 2>

## Why

<paragraph from Step 2 — link to issue if applicable: "Refs #NNN">

## Alternatives considered

- **<Option A>** — rejected because <reason>
- **<Option B>** — rejected because <reason>

<OR, if none:>
None considered seriously — <reason>.

## Risk

<one paragraph or bullet list covering what could go wrong, what's mitigated, what's accepted>

## Test plan

- [ ] <item 1>
- [ ] <item 2>

Refs #<issue>

🤖 Generated with [Claude Code](https://claude.com/claude-code)
```

## Step 5 — Open the PR (only if I confirm)

After I approve the final body:

```bash
gh pr create --base main --head "$(git branch --show-current)" \
  --title "<conventional-commit title derived from commits>" \
  --body "$(cat <<'EOF'
<final markdown from Step 4>
EOF
)"
```

**Do not open the PR before I approve the body.** The whole point of this command is capturing thinking that would otherwise be lost — that requires me to actually read and endorse the content, not rubber-stamp.

## What `/pr-description` does NOT do

- Doesn't run `/ship-ready` for you — run that separately first
- Doesn't run `/review-pr` for you — that's a post-push review, not a pre-push description
- Doesn't decide the merge strategy (squash vs merge commit) — that's a repo convention, set in the repo settings
- Doesn't auto-link to the umbrella issue when multiple are referenced — enumerate them explicitly
