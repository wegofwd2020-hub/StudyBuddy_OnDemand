# School User Account Management — Functional Spec

**Status:** Draft · **Scope:** School-tenant user lifecycle · **Audience:** Engineering + Product

> **Decision record:** the role model and uniqueness rules below are locked in
> [ADR-005](ADR_005_school_roles_and_uniqueness.md). This document is the
> functional companion to that ADR.

---

## 1. Overview

Defines how user accounts are created, modified, and authenticated within a
**school tenant**. A school is onboarded by a StudyBuddy **super-admin**, after
which the school manages its own users under a configurable authentication mode.

---

## 2. Authentication Mode (per-school toggle)

Each school has an authentication-system setting:

| Type | Name | Status | Description |
|---|---|---|---|
| **Type 1** | Self-Managed | ✅ Active | The school manages its own user accounts and passwords inside StudyBuddy. |
| **Type 2** | External System Integration | ⏸️ Deferred | Auth delegated to the school's external identity provider. *Not in scope yet.* |

> The remainder of this document specifies **Type 1 (Self-Managed)**.

---

## 3. Super-Admin Responsibilities (StudyBuddy internal)

The super-admin performs the **initial onboarding only**:

1. **Onboards a new school** — supplies the school **name** and a **valid,
   pre-existing email-id** already registered with the service provider.
2. **Onboards the school-admin account(s)** — supplies a valid, pre-existing
   email-id. A school may have **more than one** school-admin account.
3. Sets the school's authentication mode (Type 1 by default).

The super-admin does **not** manage teachers, students, or curriculum content.

---

## 4. System-Automated Actions (account provisioning)

On creation of any school-admin (and any provisioned user):

1. **System auto-generates** the initial password.
2. **System emails** the credentials to the account's email-id for first login.
3. **System sets password expiry on first login** and **forces a password reset**
   before any portal access is granted.

---

## 5. Roles

Three roles exist within a school tenant:

| Role | Account type | Notes |
|---|---|---|
| **School Admin** | Elevated **teacher** | A teacher account that additionally holds the school-admin capability. |
| **Teacher** | Teacher | Can be assigned to multiple grades/classes. |
| **Student** | Student | Can be assigned to multiple grades/classes. |

**Constraints on roles:**
- An account is **either a teacher or a student — never both** (Rule 6).
- School-admin is **not a separate account type**; it is a superset role layered
  on a teacher account, added/removed by an existing school-admin (Rule 10c).
  A school-admin can also teach (be assigned to grades/classes). See
  [ADR-005, Decision 1](ADR_005_school_roles_and_uniqueness.md).

---

## 6. School-Level Account Management (Type 1)

The **school** (via its school-admins) is responsible for:

1. Managing user accounts — **Add / Modify / Delete** (Rule 1).
2. Managing user-account **password resets** (Rule 2).
3. **Onboarding student accounts** (Rule 4).
4. Maintaining the required school-admin account(s) (Rule 3).

---

## 7. Grade / Class Assignment

| Subject | Rule | Effect |
|---|---|---|
| Teacher | Assigned to **multiple** grades/classes (Rule 7) | Can access materials for those grades/classes (Rule 9). |
| Student | Assigned to **multiple** grades/classes (Rule 8) | Can access materials for those grades/classes (Rule 9). |

Assignment is the access-control mechanism: **assignment to a grade/class ⇒
access to that grade/class's materials.**

---

## 8. Permissions Matrix

| Capability | Student | Teacher | School Admin |
|---|:--:|:--:|:--:|
| Access materials for **assigned** grades/classes | ✅ | ✅ | ✅ |
| **View all** grade curriculum | ❌ | ❌ | ✅ (Rule 10a) |
| Onboard a new **teacher** or **student** | ❌ | ❌ | ✅ (Rule 10b) |
| Change a teacher's role — **add/remove school-admin** | ❌ | ❌ | ✅ (Rule 10c) |
| Change a student's grade/class — **add/remove** | ❌ | ❌ | ✅ (Rule 10d) |
| **Create / modify curriculum** and curriculum/course content | ❌ | ❌ | ✅ (Rule 11) |
| Manage own account password | ✅ | ✅ | ✅ |

> **Curriculum authority (Rule 11):** Only school-admins may create or modify
> curriculum and course content. Plain teachers and students cannot. Narrower
> curriculum capabilities (`curriculum.commission` / `curriculum.review`) may be
> granted to *non-admin* teachers via `teacher_capabilities` (migration 0059) —
> see [ADR-005](ADR_005_school_roles_and_uniqueness.md).

**Authority precedence:** `school_admin` ⊃ any `teacher_capabilities` grant ⊃
plain `teacher`.

---

## 9. Uniqueness & Association Constraints

| # | Constraint | Enforcement |
|---|---|---|
| a | School **email-id** is unique | `schools.contact_email` UNIQUE (migration 0025). |
| a | School **name** is **NOT** required to be unique | No constraint — duplicate names permitted. See [ADR-005, Decision 2](ADR_005_school_roles_and_uniqueness.md). |
| b | A school-admin account is associated with **exactly one** school | One-school binding via `teachers.school_id`. |
| — | Teacher / student email-ids are globally unique | `teachers.email` / `students.email` UNIQUE (ADR-001). |
| — | Email-ids supplied at onboarding must be **valid and pre-existing** | Validated before account creation. |

---

## 10. Lifecycle Flows

### 10.1 School Onboarding (super-admin)
```
super-admin
  → enter school name + valid email-id
  → system checks: contact_email unique  ──(conflict)──▶ reject
    (school name may duplicate — not checked)
  → create school (auth mode = Type 1)
  → create school-admin account(s)  [≥1; may be more than 1]
  → system auto-generates password → emails credentials
```

### 10.2 First Login (any provisioned account)
```
user receives emailed credentials
  → logs in with temporary password
  → system: password expired on first login → force reset
  → user sets new password
  → access granted
```

### 10.3 User Provisioning (school-admin)
```
school-admin
  → Add teacher OR student   (account type fixed: one or the other)
  → assign to grade(s)/class(es)
  → system auto-generates password → emails credentials → first-login reset
```

### 10.4 Role / Assignment Changes (school-admin)
```
school-admin
  → promote/demote teacher  (add/remove school-admin capability)
  → add/remove student from grade(s)/class(es)
  → modify / delete accounts
  → reset any user's password
```

---

## 11. Implementation Notes (current Phase-A local auth)

Much of Type 1 is already implemented by the Phase-A local-auth track:

- `POST /schools/register` — school founder registration (`auth_provider='local'`).
- Auto-generated password + emailed credentials + `first_login=TRUE` on
  provisioned teachers/students.
- `first_login=true` forces a redirect to `/school/change-password?required=1`
  before any portal page renders (enforced at the portal layout).
- Role stored as `teachers.role ∈ {teacher, school_admin}`; `teacher_capabilities`
  (migration 0059) provides additive partial grants for non-admin teachers.

See the **Authentication** section of `CLAUDE.md` for the three-track auth model
and JWT payload shapes.

---

## 12. Open Questions / To Confirm

1. **Rule 3 — "2 user accounts that are part of the school admin":** Is this a
   **minimum of 2 school-admin accounts per school** (for redundancy), or a
   default of 2 created at onboarding that can later grow? Stated here as
   "≥1, may be more"; please confirm the minimum.
2. **Delete semantics:** Is account "Delete" a hard delete or a deactivate
   (soft delete)? Relevant for FERPA record-retention on student accounts.
