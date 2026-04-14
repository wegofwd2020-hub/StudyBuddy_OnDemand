# Epic 8 — Onboarding Completeness (Address & Measurement Units)

**Status:** 💭 Your call

---

## What it is

Capture the full postal address during school onboarding and in school settings,
and use the country code to drive the measurement-units system used when content
(especially experiments) is rendered. Makes the platform usable for a school in
any country without the UI feeling US-centric.

Full specification lives in
[studybuddy-docs/UX_REQUIREMENTS.md §2.1](https://github.com/wegofwd2020-hub/studybuddy-docs/blob/main/UX_REQUIREMENTS.md#21-school-address--country-driven-measurement-units).

---

## Current state

- `schools.country` exists (ISO-3166-α2, default `'CA'`) and is already displayed
  on `/school/settings`.
- No other address fields exist — `address_line1/2`, `city`, `state_region`,
  `postal_code` are all missing.
- Content JSON stores measurements as inline strings (e.g. `"250 ml"`) rather
  than `{value, unit}` pairs, so there is nothing for a renderer to convert.
- No `units.ts` helper, no `<Measurement>` component.

---

## Why it matters

- **SaaS readiness.** A platform that asks only for country can't produce a
  proper invoice, can't localise legal disclosures, and feels half-finished at
  signup.
- **Content quality.** A US student shouldn't see "250 ml of vinegar" in a
  lab, and a UK student shouldn't see "1 cup". Fixing this at render time
  (not at pipeline time) avoids doubling content cost per market.
- **Future-proofs regional expansion.** Once the unit-system hook exists,
  adding locale-specific formatting (dates, currency) reuses the same
  context.

---

## Rough scope

| Phase | What gets built | Size |
|---|---|---|
| H-1 | Migration `0044_school_address` — add `address_line1/2`, `city`, `state_region`, `postal_code`; normalise `country` to ISO-3166-α2 with whitelist validation | S |
| H-2 | API — extend `POST /schools/register`, `PUT /schools/{id}`, `GET /schools/{id}` with address payload + validation | S |
| H-3 | UI — school self-registration Address step (country dropdown first, adapts label "State"/"Province"); new **Address** card on `/school/settings` with inline edit | M |
| H-4 | `web/lib/units.ts` helper — `getUnitSystem(country)` returning `"imperial"` / `"metric"`; React context `SchoolPreferencesProvider` exposes school country + unit system | S |
| H-5 | `<Measurement value={250} unit="ml" />` component — consumes unit-system context; fallback to raw string if JSON still holds inline value | S |
| H-6 | Experiment JSON schema update — canonical metric storage format; migrate existing content lazily (component handles both shapes) | M |
| H-7 | Tests — API validation, country whitelist, unit conversion (metric↔imperial for common units: ml, L, g, kg, cm, m, °C) | S |
| H-8 | **Streams — backend** ✅ (shipped 2026-04-14) — migration `0044_stream_column` adds `curricula.stream_code`, `students.stream`, `teachers.stream`; admin upload + trigger endpoints accept `stream` query/body param; curriculum_id gains `-{stream}` suffix; `pipeline/build_grade.py` honours the stream arg. Canonical codes: `science | commerce | humanities | english | stem`. Backward-compatible — legacy stream-unaware uploads still work. | S |
| H-9 | **Streams — student/teacher UI** — stream picker on onboarding; students.stream filter on curriculum map, content library, reports; school portal "Upload curriculum" form exposes a stream dropdown; teacher assignment UI accepts stream | M |
| H-10 | **Streams — mandatory picker + registry + housekeeping** — admin Upload page makes Stream required with an "Other…" custom-code path; soft `streams` registry with upsert-on-use; admin CRUD + merge + archive pages at `/admin/streams`. Tickets: **S-1** #175 (migration 0045), **S-2** #176 (backend endpoints), **S-3** #177 (frontend + housekeeping UI). | M |

---

## Open questions

1. **Country whitelist.** Full ISO-3166-α2 (250+ countries) or a curated list of
   markets we actually serve? Curated is safer for validation errors and copy
   translations.
2. **State/region.** Free-text for all countries, or structured dropdown for
   US/CA/AU/IN and free-text elsewhere? Structured is better data; free-text
   is faster to ship.
3. **Postal code validation.** Regex per country, or just length ≤ 12 and
   accept anything? Lenient is safer for edge cases (new countries, missing
   codes in some regions).
4. **Unit conversion precision.** Round to sensible precision per unit
   (e.g. 1 mL → 0.034 fl oz → display as "0.03 fl oz"), or show fractional
   imperial (⅛ tsp)?
5. **Backfill.** Existing schools (Dev, MilfordWaterford, Riverside) default
   to empty strings. Do we prompt the school admin on next login to complete
   the address, or leave it silent?

---

## Dependencies

- None blocking. Does not depend on hosting, Epic 1, or other epics.

---

## Your decisions / notes

> Add your thoughts here. Even rough bullet points are enough to start.

-
-
-
