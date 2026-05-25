# Responsive / Device Target

Where each StudyBuddy surface is meant to run, so reviewers and demo audiences
don't test on the wrong device and read expected behavior as a bug.

Raised by demo feedback 2026-05-24 (Sundararajan Ramanathan, SR-1 — issue #371):
*"The lesson menu and layout look fine in landscape — is your intent any device,
or iPad/Surface/Mac/laptop/desktop and then mobile phones?"*

## Device matrix

| Surface | Audience | Primary device | Notes |
|---|---|---|---|
| **Web portal** (`web/` — school/teacher + admin) | School admins, teachers, internal team | **Desktop / laptop / tablet (landscape)** | Admin & teacher work is desk-oriented: rosters, reports, content review, dashboards. Built desktop/tablet-first. |
| **Student mobile app** (Expo / React Native — Epic 3) | Students | **Phones & tablets** | The phone experience for students is the native app, **not** the responsive web portal. Parked behind testing + hosting (see project backlog). |
| **Public site** (`web/app/(public)`) | Prospects, parents | All sizes | Marketing pages are fully responsive down to phone widths. |

## Supported widths — school/teacher/admin portal

| Width | Support level |
|---|---|
| **≥ 1024px** (desktop, laptop, tablet landscape) | **Primary.** Fully designed and tested. |
| **768–1023px** (tablet portrait) | **Supported / graceful.** Content reflows; the fixed 224px rail coexists with content; no horizontal scroll. Tighter, but functional. |
| **< 768px** (phones) | **Out of primary scope.** The portal renders but the fixed sidebar consumes significant width — it is not optimised for phones. Students should use the mobile app (Epic 3); admins/teachers should use a tablet or larger. |

## Rationale

The portal's left rail is a fixed-width (`w-56` = 224px) sidebar without a mobile
drawer. That is a deliberate desktop/tablet-first choice: the people who use the
portal (admins, teachers) are doing desk work, while the phone-shaped audience
(students) is served by the dedicated native app rather than a squeezed web view.

## Verification (graceful degradation)

Checked with Playwright on the school dashboard:

| Viewport | `scrollWidth` vs `innerWidth` | Result |
|---|---|---|
| 1024 × 768 (tablet landscape) | 1024 = 1024 | ✅ no horizontal overflow |
| 768 × 1024 (tablet portrait) | 768 = 768 | ✅ no horizontal overflow |

The layout degrades gracefully to tablet portrait (no broken/clipped layout,
no horizontal scrollbar). Phones below 768px are explicitly out of primary
scope per the table above.

## Guidance

- **Demos / reviews:** present the portal on a laptop, desktop, or tablet in
  landscape. Don't evaluate the school portal on a phone — that's the student
  app's job (Epic 3).
- **Future work:** a responsive sidebar drawer for < 768px would extend portal
  support to phones if a real need emerges; not currently prioritised.
