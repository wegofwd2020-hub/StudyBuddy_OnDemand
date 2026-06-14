# SPEC — Per-Content "Reviewed & Verified" Badge

**Status:** Draft / proposed
**Author:** (fill in)
**Date:** 2026-06-14
**Related:** Epic 11 (content formatting), Epic 7 (content review), `web/lib/compliance.ts`,
`/quality` public page, [`docs/COMPLIANCE_ONE_PAGER.md`](COMPLIANCE_ONE_PAGER.md)

---

## 1. Problem

StudyBuddy enforces a strong content-quality and compliance stack — strict schema
validation, an inclusive-language (AlexJS) scan, a human approve/publish gate, and
serve-time privacy scoping. **None of this is visible to the people consuming the
content.** A student opens a lesson and sees prose; a teacher assigns a unit with no
on-screen signal that it was reviewed and approved, by whom, or when.

This spec turns an invisible backend fact ("this version was approved and published")
into a small, trustworthy, daily-visible UI signal: a **Reviewed & Verified badge**.

It is the per-unit complement to the public `/quality` page: that page explains the
gates in general; this badge proves a *specific* unit cleared them.

## 2. Goals / Non-goals

**Goals**
- Surface, on each rendered unit, that the content is **AI-generated and human-reviewed**.
- For teachers/admins, additionally surface **provenance**: review status, published date,
  version number, and the AI provider.
- Reuse existing review metadata (`content_subject_versions`) — do not invent a new
  source of truth.
- Satisfy the EU AI Act Art. 50 transparency obligation already claimed in
  `web/lib/compliance.ts` ("AI content disclosure on every lesson/quiz/tutorial/experiment").

**Non-goals**
- No new review *workflow* — this is display-only over existing statuses.
- No claim the badge can't back. We do **not** show "reading-level verified" (reading level
  is prompt-targeted, not measured — see §8 Honesty constraints).
- No per-section badges in v1 (unit-level only).

## 3. Audiences & what each sees

| Audience | Sees | Rationale |
|---|---|---|
| **Student** | A compact "AI-generated · Reviewed" pill + plain-language disclosure line. No internal IDs, no status words like "published", no reviewer identity. | Content Rule #5: nothing technical/internal student-facing. Students only ever receive published content, so status is implicit. |
| **Teacher / school_admin** | Full badge: status (Published/Approved), published date, version number, AI provider, language built. | They make assignment decisions and answer parent questions. |
| **Admin reviewer** | Already served by the existing review queue + version detail pages — **out of scope** here (no change). | |

## 4. Data — what exists vs. what's missing

### Already available at serve time
The content serve responses (`backend/src/content/schemas.py`) already carry, from the
unit's `meta.json`:
- `generated_at: str | None`
- `model: str | None`
- `content_version: int | None`

This is enough for the **student** badge today (AI-generated + disclosure), with no
backend change.

### Missing at serve time (needed for the teacher/admin badge)
Review/approval state lives only in `content_subject_versions` and is **not** joined into
the content serve path:
- `status` (`pending` → `approved` → `published` / `rejected` / `blocked`)
- `published_at`
- `version_number`
- `provider` (`anthropic` | `openai` | `google` | `school_upload`)
- `alex_warnings_count`

Columns confirmed in: migration `0002_phase2_content_schema.py` (base), `0015_subject_name.py`,
`0043_provider_column.py`.

## 5. Backend design

Two options; **Option A recommended.**

### Option A — dedicated lightweight metadata endpoint (recommended)

Add a read-only endpoint that resolves the published `content_subject_versions` row for a
unit's subject and returns just the verification fields. Keep it **separate** from the hot
content-serve path so we don't add a DB join to the cache-warm read (Performance Rule #1).

```
GET /api/v1/content/{unit_id}/verification
→ 200 ContentVerificationResponse
```

```python
# backend/src/content/schemas.py
class ContentVerificationResponse(BaseModel):
    unit_id: str
    is_reviewed: bool            # status in ('approved','published')
    is_published: bool           # status == 'published'
    status: Literal["pending","approved","published","rejected","blocked"] | None
    version_number: int | None
    published_at: datetime | None
    provider: Literal["anthropic","openai","google","school_upload"] | None
    model: str | None            # from meta.json
    generated_at: datetime | None
    # NB: alex_warnings_count is intentionally NOT exposed to non-admin clients —
    # a raw warning count is misleading out of context (warnings can be reviewed
    # false-positives). Reviewer-facing surfaces keep using the admin queue.
```

Resolution (service layer, mirrors `content/service.py::resolve_curriculum_id`):
1. Resolve `curriculum_id` for the requesting student/teacher (existing 3-step resolver).
2. Resolve the unit's `subject` from `curriculum_units`.
3. `SELECT … FROM content_subject_versions WHERE curriculum_id=$1 AND subject=$2
   AND status='published' ORDER BY version_number DESC LIMIT 1`.
4. Layer `model`/`generated_at` from the unit `meta.json` already loaded by the serve path.

Caching: L2 Redis key `verif:{curriculum_id}:{subject}` with the **same invalidation hook
already used on publish/rollback** (publish already bumps content caches — extend it to drop
this key). TTL 1h as a backstop.

RLS: the endpoint runs under the caller's JWT, so `app.current_school_id` is already stamped
by `get_db(request)` — school scoping is automatic. A student JWT and a teacher JWT both hit
the same endpoint; the **response is shaped client-side per role** (§6), but the server may
also omit `status`/`version_number` for student tokens if we want defense-in-depth.

**Why separate, not inlined into `/content/{unit_id}/lesson`:** the lesson endpoint is the
hot read path and must stay zero-DB on cache-warm requests. The badge is non-blocking chrome;
fetching it in a second, low-priority request keeps the lesson render fast and lets the badge
degrade gracefully (see §6).

### Option B — inline fields on each content response (rejected)

Add the same fields to `LessonResponse`/`QuizResponse`/etc. Rejected because it forces a
`content_subject_versions` join (or a second lookup) into the hot path for a piece of UI that
is non-critical and identical across all content types of the same subject.

## 6. Frontend design

### 6.1 Component — `ContentVerifiedBadge`

New file: `web/components/content/ContentVerifiedBadge.tsx`. Mirrors the visual language of the
existing `ProviderBadge` (`admin/content-review/page.tsx`) and `StatusBadge`
(`web/components/authoring/StatusBadge.tsx`).

```tsx
"use client";

import { ShieldCheck, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";

const PROVIDER_LABELS: Record<string, string> = {
  anthropic: "Claude",
  openai: "GPT",
  google: "Gemini",
  school_upload: "School upload",
};

export interface ContentVerification {
  is_reviewed: boolean;
  is_published: boolean;
  status?: string | null;
  version_number?: number | null;
  published_at?: string | null;
  provider?: string | null;
  model?: string | null;
  generated_at?: string | null;
}

/**
 * Per-unit trust signal. `audience` controls disclosure depth:
 *  - "student": AI-generated + reviewed pill only, no internal fields.
 *  - "staff":   adds status, version, published date, provider.
 */
export function ContentVerifiedBadge({
  data,
  audience,
  className,
}: {
  data: ContentVerification | null | undefined;
  audience: "student" | "staff";
  className?: string;
}) {
  if (!data) return null; // graceful: badge simply absent if metadata unavailable

  return (
    <div
      className={cn(
        "flex flex-wrap items-center gap-2 rounded-lg border border-blue-100 bg-blue-50 px-3 py-2 text-xs text-gray-600",
        className,
      )}
      // not a status alert; informational. Avoid role="status" (no live updates).
    >
      <Sparkles className="h-4 w-4 shrink-0 text-blue-600" aria-hidden="true" />
      <span>AI-generated</span>
      {data.is_reviewed && (
        <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-2 py-0.5 font-medium text-emerald-700">
          <ShieldCheck className="h-3.5 w-3.5" aria-hidden="true" />
          Reviewed
        </span>
      )}
      {audience === "staff" && (
        <span className="text-gray-400">
          {data.version_number != null && `v${data.version_number} · `}
          {data.provider && `${PROVIDER_LABELS[data.provider] ?? data.provider} · `}
          {data.published_at &&
            `Published ${new Date(data.published_at).toLocaleDateString()}`}
        </span>
      )}
    </div>
  );
}
```

### 6.2 Student-facing disclosure line

Below the badge, render the plain-language AI disclosure that `web/lib/compliance.ts` already
claims exists ("AIContentDisclosure notice … on every lesson, quiz, tutorial, and experiment").
If a shared `AIContentDisclosure` component already exists, reuse it; otherwise this badge's
student variant satisfies the requirement. Copy:

> *This lesson was created by StudyBuddy's AI and reviewed by an educator before it was
> published.*

(Reading-level wording deliberately omitted — see §8.)

### 6.3 Where it attaches

Top of each unit render, after the title, before the body:
- Student: `web/app/(student)/lesson/[unit_id]/page.tsx` (and `tutorial`, `quiz`, `experiment`
  equivalents) — or once inside `LessonRenderer`/`TutorialRenderer`
  (`web/components/content/`) so all four content types inherit it.
- Teacher: the school-portal content viewer that renders units.

### 6.4 Data fetching

New client + hook in `web/lib/api/content.ts`:

```ts
export async function getContentVerification(unitId: string): Promise<ContentVerification> {
  const res = await api.get<ContentVerification>(`/content/${unitId}/verification`);
  return res.data;
}
```

Fetch with a **separate, non-blocking `useQuery`** (don't gate the lesson render on it).
`audience` is derived from the current portal/role (student pages pass `"student"`, school
pages pass `"staff"`). On error/empty → badge renders nothing (§6.1 guard).

## 7. Rollout plan

1. **Phase 1 (no backend change):** ship the student badge using the `generated_at`/`model`
   fields already on the lesson response → "AI-generated" + disclosure line. Immediate AI Act
   transparency coverage on student content.
2. **Phase 2:** add `GET /content/{unit_id}/verification` + Redis caching + publish/rollback
   invalidation; add the staff badge to the teacher content viewer.
3. **Phase 3 (optional):** expose `is_reviewed` on the student badge once Phase 2 lands, so
   students see the green "Reviewed" pill, not just "AI-generated".

## 8. Honesty constraints (do not violate)

These mirror the caveats already encoded as `status: "targeted"` in `web/lib/compliance.ts`:

- **No "reading-level verified" claim.** Reading level is *prompt-targeted* (generated 1–2
  grades below), not measured by a Flesch-Kincaid gate. Until a real validator exists, the
  badge/disclosure says "created for your grade level" at most — never "verified".
- **"Reviewed" must mean it.** Only show the green Reviewed pill when
  `status in ('approved','published')`. Auto-approve pipelines
  (`REVIEW_AUTO_APPROVE=true`) set `published` without a human — if that env is ever on in
  production, the pill would overclaim. Gate the pill on a real human-approval signal
  (e.g. `approved_by IS NOT NULL`) before enabling it in any auto-approve environment.
- **Don't surface raw `alex_warnings_count`** to non-admins; a bare count is misleading once
  warnings are reviewed/false-positived.
- **No reviewer identity** to students (FERPA/privacy hygiene; not student-relevant).

## 9. Testing

- **Backend:** verification endpoint returns published row; returns nulls/`is_reviewed=false`
  when only a pending version exists; RLS scopes cross-school (a teacher from School B gets no
  row for School A's curriculum); cache invalidated on publish + rollback.
- **Web typecheck/lint/prettier** (`web/AGENTS.md` gate).
- **E2E (Playwright):** student lesson shows AI-generated + disclosure; teacher content view
  shows version + provider + published date; badge absent (not broken) when metadata 404s.
- **a11y:** icons `aria-hidden`, text conveys all meaning (no colour-only), badge passes axe on
  the lesson/tutorial personas.

## 10. Open questions

1. Should the staff badge link through to the admin version-detail page for admins who are also
   viewing as staff? (Probably yes for `super_admin`.)
2. Do we want a single shared `AIContentDisclosure` component extracted now, or fold it into the
   badge's student variant? (Lean: extract if one is already referenced in compliance copy.)
3. Phase 1 vs. Phase 2 priority — is AI Act transparency (student disclosure) the urgent driver,
   or teacher provenance? That decides which phase ships first.
