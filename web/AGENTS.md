<!-- BEGIN:nextjs-agent-rules -->

# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` before writing any code. Heed deprecation notices.

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
