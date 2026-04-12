# Epic 5 — District Admin

**Status:** 💭 Your call

---

## What it is

A super-tier above School Admin: a District Administrator who manages multiple
schools from a single dashboard — cross-school analytics, bulk school provisioning,
district-wide curriculum assignment, and consolidated billing.

---

## Current state

The platform is currently school-centric. Each school is an independent entity:
- `schools` table has no parent/district relationship
- Billing is per-school (Stripe subscription per school)
- Analytics are scoped per school
- Admin accounts are per-school (School Admin can only see their own school)

A district buying 20 school licenses today would need 20 separate School Admin
accounts and no cross-school visibility — a serious friction point for district-level sales.

---

## Why it matters

- **Sales tier:** Districts are larger contracts than individual schools. A single district sale can replace 10–50 individual school sales.
- **Procurement simplicity:** Districts want one contract, one invoice, one support relationship.
- **Curriculum consistency:** Districts often mandate specific curriculum across all schools. A district-level assignment saves each school from setting it up separately.
- **Reporting:** District administrators, board members, and grant funders want aggregate data across schools — not 20 separate CSV exports.

---

## Data model changes

```
districts
  district_id   UUID PK
  name          TEXT NOT NULL
  contact_email TEXT UNIQUE NOT NULL
  created_at    TIMESTAMPTZ

schools
  district_id   UUID FK → districts (nullable — schools can exist without a district)

district_admins
  district_admin_id  UUID PK
  district_id        UUID FK → districts
  email              TEXT UNIQUE NOT NULL
  password_hash      TEXT
  created_at         TIMESTAMPTZ
```

A `district_admin` JWT would carry `district_id` and `role: "district_admin"`.
District admin endpoints would JOIN across all schools where `schools.district_id = $district_id`.

---

## Rough scope

| Phase | What gets built |
|---|---|
| J-1 | Schema: `districts` table, `district_id` FK on `schools`, `district_admins` table + auth |
| J-2 | District admin portal: school list, add/remove schools, invite School Admins |
| J-3 | Cross-school analytics: aggregate completion rates, at-risk counts, active student counts |
| J-4 | District curriculum: assign a curriculum package to all schools in the district at once |
| J-5 | District billing: single Stripe subscription covers all schools; per-school seat counts rolled up |

---

## Open questions

1. **Is this a near-term priority?** District admin is a significant schema change. Is there an active district prospect that makes this urgent, or is it a future-state investment?
2. **Billing model:** Does a district pay per school? Per student across all schools? A flat district license fee? This changes the Stripe integration significantly.
3. **Data isolation:** Should a district admin see individual student records, or only school-level aggregates? FERPA implications differ.
4. **School onboarding:** Does a district admin self-provision schools, or does the StudyBuddy super admin provision them?
5. **Existing schools:** Can standalone schools (no district) be retroactively added to a district? Migration path for existing customers.
6. **District curriculum:** If a district assigns a package to all schools, can individual schools override or add to it?

---

## Your decisions / notes

> Add your thoughts here. Even rough bullet points are enough to start.

-
-
-
