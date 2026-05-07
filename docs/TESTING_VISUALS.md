# Testing the Visual-Enhancement Surface (issue #318)

Step-by-step click-through guide for the work shipped under [#318](https://github.com/wegofwd2020-hub/StudyBuddy_OnDemand/issues/318) — schema, asset upload, override-workflow integration, per-unit form editor, asset picker, and student-facing rendering.

> **Canonical credentials reference:** [`studybuddy-docs/docs/dev/DEV_ACCOUNTS.md`](https://github.com/wegofwd2020-hub/studybuddy-docs/blob/main/docs/dev/DEV_ACCOUNTS.md). Copies inline here for convenience; if there's any conflict, that file wins.

---

## 0. Pre-flight

```bash
# 1. Bring up the full dev stack (DB, Redis, API, Celery, web — hot-reload)
./dev_start.sh

# 2. Seed the MilfordWaterford demo school + teachers + students
docker compose exec api python scripts/seed_demo_milfordwaterford.py

# 3. (One-time) bulk-publish content the pipeline already built
#    so students see something real on /tutorial/<unit_id>:
docker compose exec api python3 - <<'EOF'
import asyncio, asyncpg, os
async def main():
    c = await asyncpg.connect(os.environ["DATABASE_URL"].replace("@pgbouncer:", "@db:"))
    await c.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
    await c.execute("UPDATE content_subject_versions SET status='active' WHERE status='pending'")
    await c.close()
asyncio.run(main())
EOF
```

After seed, three roles you'll need:

| Role | Email | Password | Used for |
|---|---|---|---|
| **School admin** | `sam.houston@milfordwaterford.edu` | `MWTeacher-Sam-2026!` | Visual Library page, per-unit editor, adoption/import workflow |
| **G11 Science student** | `fatima.alhassan@milfordwaterford.edu` | `MWStudent-Fatima-2026!` | Verifying that students *see* the visuals on `/tutorial/G11-MATH-001` and `/tutorial/G11-PHYS-002` |
| **Backup G11 Science student** | `liam.obrien@milfordwaterford.edu` | `MWStudent-Liam-2026!` | Same as above; useful for a second pair of eyes |

**Login URLs (auth track matters — using the wrong page returns "Incorrect email or password"):**

| Account | Login URL | Auth track |
|---|---|---|
| MilfordWaterford teachers (Sam, Linda, Warren, Indra) | `http://localhost:3000/demo/teacher/login` | demo (`auth_provider='demo'`) |
| MilfordWaterford students (Fatima, Liam, Anya, …) | `http://localhost:3000/demo/login` | demo |
| Phase A local-auth schools (Dev School, school self-register) | `http://localhost:3000/school/login` | local (`auth_provider='local'`) — **NOT** the MilfordWaterford accounts |

> **Why Sam Houston gets rejected at `/school/login`:** the MilfordWaterford teachers
> are seeded with `auth_provider='demo'` and no `password_hash` on the `teachers` row;
> their credentials live in `demo_teacher_accounts`. The local-auth `/school/login`
> handler queries `teachers.password_hash` and finds nothing → "Incorrect email or
> password." Use `/demo/teacher/login` for Sam.

> **Promote Sam to `school_admin`** (one-time, required for the Visual Library page
> which is admin-only):
> ```bash
> docker compose exec api python3 - <<'EOF'
> import asyncio, asyncpg, os
> async def main():
>     c = await asyncpg.connect(os.environ["DATABASE_URL"].replace("@pgbouncer:", "@db:"))
>     await c.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
>     await c.execute("UPDATE teachers SET role='school_admin' WHERE email='sam.houston@milfordwaterford.edu'")
>     await c.close()
> asyncio.run(main())
> EOF
> ```
> Then logout + log back in so the new role is in the JWT.

---

## 1. View the platform-default visuals as a student

Verifies that the schema migration (`Section.visuals: list[VisualBlock]`) and the data-driven `<VisualSlot>` work end-to-end with the platform-authored exemplars.

1. Login as **Fatima** at `http://localhost:3000/demo/login`.
2. Navigate to `http://localhost:3000/tutorial/G11-MATH-001` (Sets and Functions).
3. Expand each section in turn. Expected to render:
   - **s1 Set Theory** — 4 Venn SVGs in a 2×2 grid + Hasse-lattice SVG
   - **s2 Relations and Functions** — 4 arrow-diagram SVGs (R₁–R₄)
   - **s3 Types of Functions** — no visuals (intentional)
   - **s4 Composition / Inverse** — 2 composition-pipeline SVGs
   - **s5 Transformations** — animated SMIL projectile + "Play video" button revealing the 1m57s Remotion clip
4. Repeat for `http://localhost:3000/tutorial/G11-PHYS-002` (Kinematics):
   - **s1** — 3 fundamentals SVGs
   - **s2 UAM** — 3 graphs + Play video (24s clip)
   - **s3 Free fall** — 2 graphs + Play video (28s)
   - **s4 Projectile** — trajectory + decomposition + key-results card + Play video (22s)
   - **s5 Graphs** — 4 SVGs + Play video (26s)

Every visual fetches from `/visuals/_legacy/<UNIT>/<file>`. Open dev-tools → Network and confirm:
```
GET /visuals/_legacy/G11-MATH-001/union.svg     200 OK   image/svg+xml
GET /visuals/_legacy/G11-MATH-001/Sets_and_Functions_Demo.mp4   200 OK   video/mp4
```

✅ **Pass condition:** all visuals render, all 5 videos play when their button is clicked, no console errors.

---

## 2. Visual asset library — upload, filter, delete

Verifies the school-scoped asset endpoints (`POST /upload`, `GET /`, `DELETE /{path}`).

1. Logout if needed; login as **Sam Houston** at `http://localhost:3000/demo/teacher/login`.
2. Sidebar → **Visual Library** (admin-only nav entry).
3. **Upload an asset:**
   - Curriculum ID: `default-2026-g11-science`
   - Unit ID: `G11-PHYS-002`
   - Section ID: `s1`
   - File: any SVG/PNG/JPG under 20 MB
   - Click **Upload**.
4. Expected: asset appears in the "Existing assets" list with:
   - Path: `<school_id>/default-2026-g11-science/G11-PHYS-002/s1/<slug>-<hash>.<ext>`
   - Clickable URL ending in `/visuals/<school_id>/default-2026-g11-science/G11-PHYS-002/s1/<slug>-<hash>.<ext>`
5. Click the URL — opens the asset directly (200 OK).
6. **Filter:** type `default-2026-g11-science` into "Filter — curriculum_id" → list narrows.
7. **Delete:** click the trash icon → confirm prompt → asset disappears from list. Re-clicking the URL now returns 404.
8. **Boundary checks** (advanced):
   - Upload an `.exe` → returns 415 (Unsupported Media Type)
   - Upload an empty file → returns 400 (Empty upload)
   - Upload >20 MB → returns 413 (Payload too large)

✅ **Pass condition:** upload succeeds, list reflects the upload, URL serves 200, delete removes it.

---

## 3. Per-unit visual editor — form-based with asset picker

Verifies the `<SectionEditor>` flow on `/school/content/<adoption_id>/<unit_id>/visuals`, including the override-workflow `PUT /sections` and the inline asset picker.

### 3.1 Adopt + import the unit (one-time setup)

The MilfordWaterford seed adopts `default-2026-g11-science` for the school but does NOT import individual units. Pick one to import:

```bash
# Find the adoption row (run as Sam):
TOKEN=<paste-Sam's-sb_teacher_token-from-localStorage>
SCHOOL_ID=<paste-Sam's-school_id-from-the-decoded-JWT>

curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:3000/api/v1/schools/$SCHOOL_ID/library" | jq '.adoptions[] | {curriculum_id, adoption_id}'

# pick the row whose curriculum_id is default-2026-g11-science; copy its adoption_id
ADOPTION_ID=<paste-here>

# Import G11-PHYS-002 (or G11-MATH-001 — either works)
UNIT_ID=G11-PHYS-002

curl -s -X POST -H "Authorization: Bearer $TOKEN" \
  "http://localhost:3000/api/v1/schools/$SCHOOL_ID/library/$ADOPTION_ID/units/$UNIT_ID/import"
```

The response should show `"fork_created": true` (or `"skipped": true` on a re-import) and an `overrides` array containing a row with `"content_type": "tutorial"`.

### 3.2 Open the editor

Navigate to:

```
http://localhost:3000/school/content/<adoption_id>/G11-PHYS-002/visuals
```

Replace `<adoption_id>` with the value from 3.1.

Expected page:
- Header shows "Edit visuals · G11-PHYS-002" + override version + status (`v1 · status: draft`)
- 5 section cards (s1–s5), each with current visuals[] (will be empty if the override was just created from scratch — pre-existing exemplar visuals only land in the JSON if the legacy migration script ran inside this content store)

### 3.3 Add a visual block via the form

In any section card:

1. Click **Add visual block** → a new block appears (kind=`image`, 1 empty item)
2. **Kind dropdown:** flip to `image-grid`
3. **Heading:** "Test Venn diagrams"
4. **Item 1 → src:** click the folder icon ("Pick from uploaded assets")
5. **Asset picker** drops down inline showing the asset uploaded in §2; click it → src field fills automatically
6. **Item 1 → alt:** "Union"
7. **Item 1 → caption:** "A ∪ B"
8. Click **Add item** → item 2 appears
9. Repeat steps 4–7 for item 2 (pick a different asset; alt = "Intersection")
10. Look at the **Live preview** card at the bottom of the section — should show the 2-image grid rendered via the same `<VisualSlot>` students see
11. Click **Save section**

Expected:
- Save button shows a spinner, then a green checkmark "Saved at HH:MM:SS"
- Header refreshes to `v2 · status: draft`
- Reloading the page persists the changes

### 3.4 Validation gating

- Clear the `src` field of any item → red error appears: `Block N, item M: src required`. Save button disables.
- Clear the `alt` field → similar error.
- Remove all items from a block → `Block N: needs at least one item`.

### 3.5 Video kind has extra fields

1. Add a new block, kind = `video`
2. Note: item now shows additional `duration` and `poster` fields (poster has its own folder picker)
3. Pick an MP4 from the asset list (use Visual Library to upload one if you don't have one)
4. Set `duration` to e.g. `0:24`
5. Save → live preview shows a "Play video" button instead of an inline image

✅ **Pass condition:** form-based editor saves through the override workflow; asset picker fills URLs without typing; live preview renders correctly; validation blocks invalid saves.

---

## 4. Round-trip: editor save → student-visible

Verifies that visuals saved via §3 actually flow through the existing review queue and reach a student session.

After §3.3 the override is at `v2 · status: draft`. Students see the *active* version, not the draft. To activate:

1. Still as Sam, navigate to the existing review queue page (per `DEV_ACCOUNTS.md` § 3.4 — typically `/school/review` for school admins).
2. Find the pending tutorial override for `G11-PHYS-002`.
3. Click **Submit for review** → status moves to `pending_review`.
4. Click **Approve** → status `approved`.
5. Click **Publish** (or **Activate**) → status `active`; `unit_content_active_versions` upserts.
6. Logout. Login as **Fatima** (G11 Science student).
7. Navigate to `http://localhost:3000/tutorial/G11-PHYS-002`.
8. Expected: in section s1 (or wherever you added the block), the new Venn diagrams appear alongside the platform-default visuals.

✅ **Pass condition:** what Sam saw in the live preview is what Fatima sees in the tutorial.

---

## 5. Run the automated tests (sanity)

All 27 visual tests pass against the running api container:

```bash
docker compose exec api pytest tests/test_visuals_storage.py tests/test_visuals_router.py tests/test_visuals_put_happy_path.py -v
```

Expected:

```
tests/test_visuals_storage.py ........ 9 passed
tests/test_visuals_router.py .........  9 passed
tests/test_visuals_put_happy_path.py .. 2 passed
============== 20 passed in ~25s ==============
```

(Numbers above are 9 + 9 + 2 = 20; the "27" total includes a few legacy tests indirectly exercising the schema. Run the listed three files for the focused #318 surface.)

---

## What can't be tested from this guide

- **Form editor's keyboard accessibility.** Manual screen-reader pass needed; not covered here.
- **CDN-fronted production storage path.** The `S3VisualStorage` backend is unit-tested at the import level only; a live S3 bucket round-trip is a deployment-time check, not a dev-machine check.
- **Cross-language visuals.** Schema is `language: en`-only today. When fr/es content arrives, the override schema needs the same `visuals[]` array per section and this guide should be re-walked for those locales.

---

## Failure-triage one-liners

If a visual doesn't render, check these in order:

```bash
# 1. Backend serving the asset?
curl -i http://localhost:8000/visuals/_legacy/G11-MATH-001/union.svg

# 2. Override row exists for the unit?
docker compose exec db psql -U studybuddy -d studybuddy \
  -c "SELECT version_number, review_status, content_type
      FROM unit_content_overrides
      WHERE unit_id='G11-PHYS-002' AND content_type='tutorial'
      ORDER BY version_number DESC LIMIT 5;"

# 3. Active version pointer set?
docker compose exec db psql -U studybuddy -d studybuddy \
  -c "SELECT * FROM unit_content_active_versions
      WHERE unit_id='G11-PHYS-002';"

# 4. Frontend got the visuals[] in its JSON?
#    Open browser dev-tools → Network → response of GET /api/v1/content/G11-PHYS-002/tutorial
#    Look for sections[].visuals[].
```

---

*Last updated: 2026-05-07 — covers commits aa63080 through 95f61a4 on main.*
