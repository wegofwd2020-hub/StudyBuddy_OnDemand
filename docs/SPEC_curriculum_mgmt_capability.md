# Spec — `curriculum_mgmt` capability

**Status:** Implemented (migration **0059**; issue #358) · **Date:** 2026-05-21
**Design:** [DESIGN_curriculum_mgmt_capability.md](DESIGN_curriculum_mgmt_capability.md)

Grounded patterns: guard helper `_require_school_admin(teacher, school_id, request)`
at `backend/src/school/router.py`; capability guards in `backend/src/school/capability_guards.py`;
test tokens via `make_teacher_token(..., capabilities=[...])` in
`backend/tests/helpers/token_factory.py`. Migration landed as **0059** (0058 was
taken by `demo_request_name`).

---

## 1. Failing test(s)

### Backend — `backend/tests/test_curriculum_mgmt_capability.py` (new)

```python
import pytest
from httpx import AsyncClient
from tests.helpers.token_factory import make_teacher_token

# ── require_curriculum_mgmt: the guard that gates the 9 endpoints ─────────────

async def test_granted_teacher_can_adopt(client: AsyncClient, db_conn) -> None:
    """A teacher holding curriculum_mgmt may hit a school_admin-only curriculum endpoint."""
    school = await _register_school(client)              # helper in conftest
    school_id, admin_token = school["school_id"], school["access_token"]
    tid, _ = await _provision_teacher(client, school_id, admin_token, "cm@example.com")

    # admin grants the capability
    r = await client.put(
        f"/api/v1/schools/{school_id}/teachers/{tid}/capabilities",
        json={"capabilities": ["curriculum_mgmt"]},
        headers=_auth(admin_token),
    )
    assert r.status_code == 200
    assert r.json()["capabilities"] == ["curriculum_mgmt"]

    # token now carries the grant (simulates next-login mint)
    cm_token = make_teacher_token(
        teacher_id=tid, school_id=school_id, role="teacher",
        capabilities=["curriculum_mgmt"],
    )
    r = await client.post(
        f"/api/v1/schools/{school_id}/library",
        json={"curriculum_id": _PLATFORM_CURRICULUM_ID},
        headers=_auth(cm_token),
    )
    assert r.status_code in (200, 201)   # adoption allowed


async def test_ungranted_teacher_forbidden(client: AsyncClient, db_conn) -> None:
    """A plain teacher (no grant) gets 403 on the same endpoint."""
    school = await _register_school(client)
    school_id = school["school_id"]
    token = make_teacher_token(teacher_id="t-1", school_id=school_id, role="teacher")
    r = await client.post(
        f"/api/v1/schools/{school_id}/library",
        json={"curriculum_id": _PLATFORM_CURRICULUM_ID},
        headers=_auth(token),
    )
    assert r.status_code == 403
    assert r.json()["detail"]["error"] == "forbidden"


async def test_school_admin_implicit(client: AsyncClient, db_conn) -> None:
    """school_admin needs NO explicit grant — superset (locked decision)."""
    school = await _register_school(client)
    school_id, admin_token = school["school_id"], school["access_token"]
    r = await client.post(
        f"/api/v1/schools/{school_id}/library",
        json={"curriculum_id": _PLATFORM_CURRICULUM_ID},
        headers=_auth(admin_token),
    )
    assert r.status_code in (200, 201)


async def test_revocation_via_grant_removal(client: AsyncClient, db_conn) -> None:
    """After the grant row is removed, a freshly-minted token no longer authorizes."""
    school = await _register_school(client)
    school_id, admin_token = school["school_id"], school["access_token"]
    tid, _ = await _provision_teacher(client, school_id, admin_token, "rev@example.com")

    await client.put(
        f"/api/v1/schools/{school_id}/teachers/{tid}/capabilities",
        json={"capabilities": ["curriculum_mgmt"]}, headers=_auth(admin_token))
    await client.put(   # revoke
        f"/api/v1/schools/{school_id}/teachers/{tid}/capabilities",
        json={"capabilities": []}, headers=_auth(admin_token))

    r = await client.get(f"/api/v1/schools/{school_id}/teachers/{tid}", headers=_auth(admin_token))
    assert r.json()["capabilities"] == []   # grant gone → next login mints empty


async def test_assign_requires_admin(client: AsyncClient, db_conn) -> None:
    """A non-admin (even one holding curriculum_mgmt) cannot grant capabilities to others."""
    school = await _register_school(client)
    school_id = school["school_id"]
    cm_token = make_teacher_token(
        teacher_id="t-cm", school_id=school_id, role="teacher",
        capabilities=["curriculum_mgmt"])
    r = await client.put(
        f"/api/v1/schools/{school_id}/teachers/t-2/capabilities",
        json={"capabilities": ["curriculum_mgmt"]}, headers=_auth(cm_token))
    assert r.status_code == 403


async def test_cross_school_grant_forbidden(client: AsyncClient, db_conn) -> None:
    school = await _register_school(client)
    other_admin = make_teacher_token(teacher_id="a-x", school_id="other-school", role="school_admin")
    r = await client.put(
        f"/api/v1/schools/{school['school_id']}/teachers/t-1/capabilities",
        json={"capabilities": ["curriculum_mgmt"]}, headers=_auth(other_admin))
    assert r.status_code == 403


@pytest.mark.parametrize("caps", [["bogus_cap"], ["curriculum_mgmt", "bogus"]])
async def test_unknown_capability_rejected(client, db_conn, caps) -> None:
    school = await _register_school(client)
    r = await client.put(
        f"/api/v1/schools/{school['school_id']}/teachers/t-1/capabilities",
        json={"capabilities": caps}, headers=_auth(school["access_token"]))
    assert r.status_code == 422   # only whitelisted capabilities accepted


async def test_login_mints_capabilities(client: AsyncClient, db_conn) -> None:
    """Local-auth login includes capabilities[] in the issued teacher JWT."""
    # provision + grant + login → decode token → assert 'curriculum_mgmt' in payload['capabilities']
    ...


# ── Two-gate isolation: commission grant ≠ review grant ──────────────────────

async def test_commission_grant_does_not_clear_review_gate(client, db_conn) -> None:
    """A teacher with curriculum.commission can trigger generation but CANNOT approve content."""
    school = await _register_school(client)
    school_id = school["school_id"]
    tok = make_teacher_token(teacher_id="t-c", school_id=school_id, role="teacher",
                             capabilities=["curriculum.commission"])
    # Gate 1 (commission) — allowed
    r = await client.post(f"/api/v1/schools/{school_id}/library",
                          json={"curriculum_id": _PLATFORM_CURRICULUM_ID}, headers=_auth(tok))
    assert r.status_code in (200, 201)
    # Gate 2 (review) — forbidden
    r = await client.post(
        f"/api/v1/schools/{school_id}/content/{_FORK_ID}/units/{_UNIT}/approve",
        json={}, headers=_auth(tok))
    assert r.status_code == 403


async def test_review_grant_does_not_clear_commission_gate(client, db_conn) -> None:
    """A teacher with curriculum.review can approve content but CANNOT trigger generation."""
    school = await _register_school(client)
    school_id = school["school_id"]
    tok = make_teacher_token(teacher_id="t-r", school_id=school_id, role="teacher",
                             capabilities=["curriculum.review"])
    # Gate 1 (commission) — forbidden
    r = await client.post(f"/api/v1/schools/{school_id}/library",
                          json={"curriculum_id": _PLATFORM_CURRICULUM_ID}, headers=_auth(tok))
    assert r.status_code == 403


async def test_umbrella_clears_both_gates(client, db_conn) -> None:
    """curriculum_mgmt umbrella satisfies both commission and review guards."""
    school = await _register_school(client)
    school_id = school["school_id"]
    tok = make_teacher_token(teacher_id="t-u", school_id=school_id, role="teacher",
                             capabilities=["curriculum_mgmt"])
    r = await client.post(f"/api/v1/schools/{school_id}/library",
                          json={"curriculum_id": _PLATFORM_CURRICULUM_ID}, headers=_auth(tok))
    assert r.status_code in (200, 201)   # Gate 1 ok; Gate 2 covered by has_capability unit test


# ── Tier 0: view is broad, act is gated ──────────────────────────────────────

@pytest.mark.parametrize("cap", ["curriculum.commission", "curriculum.review", "curriculum_mgmt"])
async def test_any_curriculum_capability_can_view_queue(client, db_conn, cap) -> None:
    """A reviewer can SEE the pending-approval list even though they can't commission."""
    school = await _register_school(client)
    school_id = school["school_id"]
    tok = make_teacher_token(teacher_id=f"t-{cap}", school_id=school_id, role="teacher",
                             capabilities=[cap])
    r = await client.get(f"/api/v1/schools/{school_id}/curriculum/definitions", headers=_auth(tok))
    assert r.status_code == 200            # view allowed for any curriculum capability
    r = await client.get(f"/api/v1/schools/{school_id}/content/review-queue", headers=_auth(tok))
    assert r.status_code == 200            # symmetric: Gate 2 queue also viewable


async def test_reviewer_can_view_but_not_approve_definition(client, db_conn) -> None:
    """The read/act split: review-holder views the commission queue but 403s on approve."""
    school = await _register_school(client)
    school_id, admin_token = school["school_id"], school["access_token"]
    defn_id = await _submit_definition(client, school_id, admin_token)   # a pending definition
    tok = make_teacher_token(teacher_id="t-rev", school_id=school_id, role="teacher",
                             capabilities=["curriculum.review"])
    assert (await client.get(
        f"/api/v1/schools/{school_id}/curriculum/definitions", headers=_auth(tok))).status_code == 200
    r = await client.post(
        f"/api/v1/schools/{school_id}/curriculum/definitions/{defn_id}/approve",
        json={}, headers=_auth(tok))
    assert r.status_code == 403            # approve is commission-only


async def test_plain_teacher_without_capability_cannot_view_queue(client, db_conn) -> None:
    """No curriculum capability → no view (proposing teachers see only their own, not the queue)."""
    school = await _register_school(client)
    school_id = school["school_id"]
    tok = make_teacher_token(teacher_id="t-plain", school_id=school_id, role="teacher")
    r = await client.get(f"/api/v1/schools/{school_id}/content/review-queue", headers=_auth(tok))
    assert r.status_code == 403
```

### `has_capability` unit test — `backend/tests/test_permissions.py` (extend)

```python
from src.core.permissions import has_capability

def test_admin_has_all_capabilities():
    assert has_capability({"role": "school_admin"}, "curriculum.commission") is True
    assert has_capability({"role": "school_admin"}, "curriculum.review") is True

def test_exact_grant():
    p = {"role": "teacher", "capabilities": ["curriculum.commission"]}
    assert has_capability(p, "curriculum.commission") is True
    assert has_capability(p, "curriculum.review") is False   # gate isolation

def test_umbrella_covers_both_gates():
    p = {"role": "teacher", "capabilities": ["curriculum_mgmt"]}
    assert has_capability(p, "curriculum.commission") is True
    assert has_capability(p, "curriculum.review") is True

def test_missing_capabilities_key_defaults_false():
    assert has_capability({"role": "teacher"}, "curriculum.review") is False
```

### Web — `web/lib/hooks/useTeacher.test.ts` (new, vitest)

```ts
import { describe, it, expect } from "vitest";
import { readTeacherClaimsForTest as read } from "@/lib/hooks/useTeacher"; // export added for test

it("exposes capabilities array from JWT", () => {
  const t = read(fakeJwt({ teacher_id: "t1", school_id: "s1", role: "teacher",
                           capabilities: ["curriculum_mgmt"] }));
  expect(t?.capabilities).toContain("curriculum_mgmt");
});

it("defaults capabilities to [] when absent (no coercion drop)", () => {
  const t = read(fakeJwt({ teacher_id: "t1", school_id: "s1", role: "teacher" }));
  expect(t?.capabilities).toEqual([]);
  expect(t?.role).toBe("teacher");   // unknown-field coercion must not break role
});
```

### Cross-persona — `web/tests/e2e/curriculum-mgmt-nav.spec.ts` (new, Playwright, run from host — pitfall #26)

```ts
test("plain teacher does NOT see Curriculum Management", async ({ page }) => {
  await loginAsTeacher(page, { capabilities: [] });
  await expect(page.getByRole("button", { name: /curriculum management/i })).toHaveCount(0);
});

test("granted teacher sees the top-bar menu with curriculum items", async ({ page }) => {
  await loginAsTeacher(page, { capabilities: ["curriculum_mgmt"] });
  await page.getByRole("button", { name: /curriculum management/i }).click();
  await expect(page.getByRole("menuitem", { name: /my curricula/i })).toBeVisible();
});

test("school_admin sees it implicitly (no grant)", async ({ page }) => {
  await loginAsSchoolAdmin(page);
  await expect(page.getByRole("button", { name: /curriculum management/i })).toBeVisible();
});
```

---

## 2. API contract

### New endpoint — assign capabilities

| Field | Value |
|---|---|
| Method + path | `PUT /api/v1/schools/{school_id}/teachers/{teacher_id}/capabilities` |
| Auth track | **local (school-provisioned)** teacher JWT — `sb_teacher_token` |
| Authorization | `school_admin` for `{school_id}` only (reuses `_require_school_admin`). **Not** grantable by a curriculum_mgmt holder. |
| Request | `CapabilityGrantRequest{ capabilities: list[str] }` — validator: each in `ALLOWED_CAPABILITIES = {"curriculum.commission", "curriculum.review", "curriculum_mgmt"}`; set semantics (full replace, not append); deduped |
| Response | `200` `TeacherCapabilitiesResponse{ teacher_id: str, capabilities: list[str] }` |
| Errors | `403` caller not school_admin / different school · `404` teacher not in this school · `422` unknown capability or malformed body · `401` no/invalid token |
| Idempotency | Natural — PUT is a full replace; re-sending same set is a no-op. No `Idempotency-Key`. |
| Rate limit | Standard authenticated teacher bucket (100/min per JWT); no special bucket |
| RLS scope | `async with get_db(request)` — tenant-stamped `app.current_school_id`; write to `teacher_capabilities` is school-scoped by RLS |
| Observability | `emit_event("capability.grant"/"capability.revoke", …)`; `write_audit_log` row `teacher.capabilities_changed` (who/whom/before→after); counter `sb_capability_grants_total{capability}` |

### Changed endpoints — three-tier guard (no shape change)

Each guard in `school/router.py` swaps `_require_school_admin` → a tiered guard.
Request/response unchanged; only the 403 condition changes.

**Tier 0 — `_require_curriculum_view`** (any curriculum capability | `curriculum_mgmt` | school_admin):
`GET …/curriculum/definitions` · `GET …/definitions/{id}` · `GET …/content/review-queue` · `GET …/library`

**Tier 1 — `_require_commission`** (`curriculum.commission` | `curriculum_mgmt` | school_admin):
`POST …/library` · `PATCH …/library/{adoption_id}` · `POST …/definitions/{id}/approve|reject|estimate|trigger` · school "load new curriculum" (definition create + trigger)

**Tier 2 — `_require_review`** (`curriculum.review` | `curriculum_mgmt` | school_admin):
`POST …/content/{cur}/units/{unit}/approve|reject`

Out of scope: `POST /admin/pipeline/upload-grade` stays admin-track (seeds platform content).
Teacher-open and unchanged: submit definition, import unit, save draft, submit-for-review.

### JWT mint change

Local login + Auth0/teacher exchange add `capabilities: list[str]` (looked up from
`teacher_capabilities`) to the teacher payload. Empty list when none. `school_admin`
tokens may omit it (helper treats admin as superset regardless).

---

## 3. Data / migration impact

**Migration `0058_teacher_capabilities.py`:**

```sql
CREATE TABLE teacher_capabilities (
  teacher_id  UUID NOT NULL REFERENCES teachers(id) ON DELETE CASCADE,
  school_id   UUID NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
  capability  TEXT NOT NULL CHECK (capability IN
                ('curriculum.commission', 'curriculum.review', 'curriculum_mgmt')),
  granted_by  UUID,
  granted_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (teacher_id, capability)
);
CREATE INDEX ix_teacher_capabilities_school ON teacher_capabilities(school_id);
```

- **RLS:** `ENABLE` + `FORCE ROW LEVEL SECURITY`; PERMISSIVE `tenant_isolation` policy keyed on `app.current_school_id` (mirrors migration 0028).
- **Downgrade:** `DROP TABLE teacher_capabilities` — safe; additive, no dependents. No data-only pre-drop.
- **Backfill:** none — absence of a row = no capability (correct default). No `NOT NULL` added to existing tables.
- **`school_id` denormalized** onto the row so the RLS policy scopes without a subquery (consistent with `classroom_students`).
- Rule #16 doc-drift: add row to CLAUDE.md migrations table (0058); no renamed identifiers.

---

## 4. Acceptance criteria checklist

- [ ] §1 tests pass (backend guard matrix + two-gate isolation + `has_capability` unit + `useTeacher` vitest + 3 persona e2e)
- [ ] **Gate isolation proven** — `curriculum.commission` clears Gate 1 but 403s on Gate 2, and vice versa; umbrella clears both
- [ ] **Read/act split proven** — any curriculum capability can `GET` both queues; a review-holder 403s on definition `approve`; a plain teacher 403s on the queue view
<!-- doc-audit:ignore -->
- [ ] §2 contract matches impl — `scripts/export_openapi.py` + `npm run gen:types` show only the new endpoint as drift
- [ ] Migration 0058 applies on fresh DB **and** full downgrade→upgrade cycle clean (pitfall #27)
- [ ] RLS verified with `studybuddy_rls_tester` non-superuser — a teacher in school A cannot read/write school B's `teacher_capabilities` rows
- [ ] Observability — `sb_capability_grants_total` on `/metrics`; `teacher.capabilities_changed` audit row present; correlation ID in logs
- [ ] **Backend is the real gate** — ungranted teacher gets 403 even calling the API directly (pitfall #10); a hidden button is not the control
- [ ] Pitfalls reviewed: **#23** (login mint must `SET app.current_school_id='bypass'` before reading grants) · **#18** (migration after pull) · **#24** (`first_login` redirect still wins) · **#2** (grant lookup async, no event-loop block) · **#1** (frontend never calls Anthropic/Stripe)
- [ ] CLAUDE.md migrations table + design doc status flipped Proposed → Implemented

### Deliberate N/A

- **Idempotency-Key:** N/A — PUT full-replace is naturally idempotent.
- **Pipeline section:** N/A — no pipeline/Anthropic/TTS code touched.
- **Revocation latency** (design open-Q #1): spec trusts the JWT claim; a removed grant is honored until token expiry. The revocation test asserts the *grant store* is cleared, not that live tokens are killed. Flag if instant revoke required → adds a per-request grant check.

---

## Implementation notes (2026-05-21)

- Migration landed as **0059** (0058 was `demo_request_name`, undocumented drift — now added to the CLAUDE.md table).
- Guards live in `backend/src/school/capability_guards.py` (`require_curriculum_view` / `require_commission` / `require_review`), wired into `school/router.py` and `pipeline_router.py`. The school "load new curriculum" surface = `POST …/curriculum/upload` + the pipeline triggers, all now commission-gated.
- JWT mint adds `capabilities[]` on **all four** teacher token paths: `/auth/login`, `/auth/universal-login`, `/auth/refresh` (so it survives the ~15-min cycle), and the Auth0 teacher exchange.
- **Harness fix:** the conftest test pool was missing the production jsonb codec (`init=_init_db_conn`), which had silently broken every jsonb-write endpoint in tests since the May-19 codec commit. Added it — un-breaks `test_phase_d_definitions` (19) + `test_epic12_content_authoring` (27).
- **e2e deferred:** the 3 persona Playwright specs are not yet committed (require host browser per pitfall #26 + persona-capability fixtures); the vitest + backend guard matrix cover the gating logic. Tracked as follow-up on #358.
- **Pre-existing failures unrelated to this work:** 19 full-suite failures remain on `main` (pipeline `ModuleNotFoundError`; `curricula` platform-write RLS, pitfall #28) — verified independent of these changes.

## Resolved decisions (2026-05-21)

- **Capability granularity:** two gates + umbrella — `curriculum.commission` (Gate 1),
  `curriculum.review` (Gate 2), `curriculum_mgmt` (both).
- **Separation of duties:** **optional**, school-controlled. No hard self-approval block;
  a school enforces maker-checker by granting the two capabilities to different people.
  The umbrella exists for schools that want one person to do both.
- **Read/act split:** *viewing* the pending-approval and content-review queues is open to
  **any** curriculum capability (Tier 0 `require_curriculum_view`); *acting* needs the
  matching gate. Symmetric across both gates. "View" is not its own grant — it's derived
  from holding any curriculum capability.
- **Upload surface:** the school "load new curriculum" act (definition + trigger) is
  commission-gated. `/admin/pipeline/upload-grade` stays admin-track (platform content).
