<!-- BEGIN:nextjs-agent-rules -->

# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` (resolved from this file's directory; in monorepos the `next` package may not be visible from the repo root) before writing any code. Heed deprecation notices.

This block is written and re-added by `next dev` — verify at `node_modules/next/dist/server/lib/generate-agent-files.js`. Removing it from a diff only re-creates the uncommitted change; committing it with your work keeps the tree clean.

<!-- END:nextjs-agent-rules -->

# Before opening a frontend PR

CI runs **`npm run format:check` (Prettier) as a separate step from ESLint** in
the "Frontend — Lint & Typecheck" job. `npm run lint` passing does **not** mean
formatting is clean — a Prettier miss reds the whole job. Always run, from `web/`:

```bash
npm run format:check   # prettier --check .  (fix with: npm run format)
npm run lint
npm run typecheck
```

`/done` and `/ship-ready` include this; run them before `gh pr create`.
