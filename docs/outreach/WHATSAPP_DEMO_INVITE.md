# WhatsApp Demo Invite — Template

Reusable message for inviting people to try the live StudyBuddy demo over
WhatsApp. WhatsApp renders `*asterisks*` as **bold** and `_underscores_` as
_italic_ — the formatting below is intentional, paste it as-is.

> Before posting: the demo logins are seeded data. If accounts were wiped (see
> `memory: project-demo-accounts-wiped`), re-seed first so portal logins work —
> `ssh demo` → `docker exec studybuddy-api-1 bash /app/scripts/demo/seed.sh`.
> Otherwise visitors land on the public site / "Request a demo" flow.

---

## Default — consumer framing (parents / teachers / friends)

```
🎓 *StudyBuddy is live — come take it for a spin!*

*Lessons, always current.* AI-powered lessons, quizzes & tutorials that bridge what kids learn in class to the world that won't sit still — for Grades 5–12, in English, French & Spanish.

✨ What you can try:
• Instant lessons & step-by-step tutorials
• Auto-generated quizzes with feedback
• Hands-on experiments & visualizations
• Teacher & school tools for custom curricula

👉 *Try the live demo:* https://demo.usestudybuddy.com

Takes 2 minutes — no app to install, works right in your browser. I'd love your honest feedback: what feels useful, what's confusing, what you'd want for your own kids/classroom.

Happy to walk anyone through it 1:1 — just reply here. 🙏
```

---

## Variant — schools / B2B (point at /for-schools)

```
🏫 *StudyBuddy for Schools — live demo*

A curriculum-aligned AI lesson platform for Grades 5–12. Teachers and schools upload their own curricula; students get instant, current lessons, quizzes & tutorials in English, French & Spanish. FERPA/COPPA-aligned, WCAG AA.

👉 *See it for schools:* https://demo.usestudybuddy.com/for-schools

Happy to give your team a guided walkthrough — reply and we'll set a time.
```

---

## Variant — one-liner (status / broadcast)

```
🎓 StudyBuddy is live — AI lessons, quizzes & tutorials for Grades 5–12. Try the demo: https://demo.usestudybuddy.com
```

---

_Branding note: the tagline word is **"current"**, never "today's"/"latest" — it's
load-bearing (evergreen claim). See `CLAUDE.md` → Positioning._
