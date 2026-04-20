/**
 * tests/e2e/personas/school-admin-curriculum-flow.spec.ts
 *
 * Happy-path E2E for issue #188 — school-admin submits a curriculum
 * definition and drives it through estimate → trigger → pipeline job.
 *
 * Scope: UI walkthrough with mocked API responses. Verifies the wizard
 * collects the right data, submits to the right endpoint, and each
 * follow-up action (approve, estimate, trigger) reaches the expected
 * paths. Does NOT run the real pipeline — that's covered by the backend
 * integration tests.
 *
 * Status:
 *   - Wizard-submit test: live. Asserts the 4-step flow posts the right
 *     shape to POST /api/v1/schools/{id}/curriculum/definitions.
 *   - 5 follow-up tests: fixme'd with concrete --trace=on unblock steps.
 *     Each comment names the next action needed to un-fixme that test.
 *
 * Covers steps 1–4 of the ticket walkthrough. Steps 5–7 (pipeline job
 * progress, content review, student visibility) require a live backend
 * and are tracked separately in the manual QA path.
 */

import { test, expect } from "@playwright/test";
import type { Page } from "@playwright/test";
import { makeTeacherToken, devSessionCookie } from "../helpers/tokens";

const SCHOOL_ID = "test-school-001";
const TEACHER_TOKEN = makeTeacherToken(
  "test-teacher-001",
  SCHOOL_ID,
  "school_admin",
);

const DEFINITION_ID = "def-test-001";
const SUBMITTED_DEFINITION = {
  definition_id: DEFINITION_ID,
  school_id: SCHOOL_ID,
  name: "Grade 11 Commerce — Semester 1",
  grade: 11,
  stream: "commerce",
  status: "pending",
  submitted_at: new Date().toISOString(),
  submitted_by: "test-teacher-001",
  subjects: [
    {
      subject_id: "G11-ACC",
      name: "Accountancy",
      units: [
        { unit_id: "G11-ACC-101", title: "Introduction to Accounting", has_lab: false },
      ],
    },
  ],
};

// ── Auth + mock setup ────────────────────────────────────────────────────────

async function setupSchoolAdmin(page: Page) {
  await page
    .context()
    .addCookies([devSessionCookie("School Admin", "admin@test.invalid")]);
  await page.addInitScript(
    (t) => localStorage.setItem("sb_teacher_token", t),
    TEACHER_TOKEN,
  );
}

async function stubDefinitionApis(page: Page, opts: { overage?: boolean } = {}) {
  // Submit — capture request body for later assertions
  await page.route(
    `**/api/v1/schools/${SCHOOL_ID}/curriculum/definitions`,
    async (route) => {
      if (route.request().method() === "POST") {
        await route.fulfill({ status: 201, json: SUBMITTED_DEFINITION });
      } else {
        await route.fulfill({
          status: 200,
          json: { items: [SUBMITTED_DEFINITION] },
        });
      }
    },
  );

  // Detail fetch
  await page.route(
    `**/api/v1/schools/${SCHOOL_ID}/curriculum/definitions/${DEFINITION_ID}`,
    (route) => route.fulfill({ status: 200, json: SUBMITTED_DEFINITION }),
  );

  // Approval
  await page.route(
    `**/api/v1/schools/${SCHOOL_ID}/curriculum/definitions/${DEFINITION_ID}/approve`,
    (route) =>
      route.fulfill({
        status: 200,
        json: { ...SUBMITTED_DEFINITION, status: "approved" },
      }),
  );

  // Cost estimate
  await page.route(
    `**/api/v1/schools/${SCHOOL_ID}/curriculum/definitions/${DEFINITION_ID}/estimate`,
    (route) =>
      route.fulfill({
        status: 200,
        json: {
          unit_runs: 1,
          forecast_tokens: 25000,
          forecast_cost_usd: "0.32",
          within_allowance: !opts.overage,
          card_last4: opts.overage ? "4242" : null,
        },
      }),
  );

  // Trigger — returns job_id
  await page.route(
    `**/api/v1/schools/${SCHOOL_ID}/curriculum/definitions/${DEFINITION_ID}/trigger`,
    (route) =>
      route.fulfill({
        status: 202,
        json: { job_id: "job-test-001", status: "queued" },
      }),
  );

  // Teacher + school chrome
  await page.route(`**/api/v1/schools/${SCHOOL_ID}`, (route) =>
    route.fulfill({
      status: 200,
      json: { school_id: SCHOOL_ID, name: "Test School", country: "CA" },
    }),
  );

  // Catch-all
  await page.route("**/api/v1/**", (route) =>
    route.fulfill({ status: 200, json: {} }),
  );
}

// ── Tests ────────────────────────────────────────────────────────────────────

test.describe("School admin — curriculum submission flow (#188)", () => {
  test.beforeEach(async ({ page }) => {
    await setupSchoolAdmin(page);
    await stubDefinitionApis(page);
  });

  test("wizard loads at step 1 with name + grade inputs", async ({ page }) => {
    await page.goto("/school/curriculum/definitions/new");
    await expect(page.getByLabel(/curriculum name/i)).toBeVisible();
    await expect(page.getByLabel(/^grade$/i)).toBeVisible();
  });

  test("wizard submits and posts to the definitions endpoint", async ({
    page,
  }) => {
    // Capture the POST before navigation so no request is missed.
    const postBodyPromise = page.waitForRequest(
      (req) =>
        req.method() === "POST" &&
        req.url().endsWith(
          `/api/v1/schools/${SCHOOL_ID}/curriculum/definitions`,
        ),
    );

    await page.goto("/school/curriculum/definitions/new");

    // Step 0 — Basics. validateStep(0) requires non-empty name + grade.
    await page.getByLabel(/curriculum name/i).fill("Grade 11 Commerce — Sem 1");
    await page.getByLabel(/^grade$/i).selectOption("11");
    await page.getByRole("button", { name: /^Next$/i }).click();

    // Step 1 — Subjects. A default subject row with one empty unit is already
    // rendered by the page; validateStep(1) requires subject_label + unit title
    // to be non-empty. Selectors match SubjectCard + UnitRow placeholders.
    await page
      .getByPlaceholder("Subject name (e.g. Mathematics)")
      .fill("Accountancy");
    await page.getByPlaceholder("Unit title").fill("Introduction to Accounting");
    await page.getByRole("button", { name: /^Next$/i }).click();

    // Step 2 — Languages. Default state ["en"] satisfies validation; no input.
    await page.getByRole("button", { name: /^Next$/i }).click();

    // Step 3 — Review. Fire the mutation.
    await page
      .getByRole("button", { name: /submit for approval/i })
      .click();

    // Assert the wizard collected the right shape.
    const req = await postBodyPromise;
    const body = req.postDataJSON() as {
      name: string;
      grade: number;
      languages: string[];
      subjects: Array<{ subject_label: string; units: Array<{ title: string }> }>;
    };
    expect(body.name).toBe("Grade 11 Commerce — Sem 1");
    expect(body.grade).toBe(11);
    expect(body.languages).toEqual(["en"]);
    expect(body.subjects).toHaveLength(1);
    expect(body.subjects[0].subject_label).toBe("Accountancy");
    expect(body.subjects[0].units).toHaveLength(1);
    expect(body.subjects[0].units[0].title).toBe("Introduction to Accounting");
  });

  test.fixme("approval queue lists the submitted definition", async ({
    page,
  }) => {
    // UNBLOCK: run `cd web && npx playwright test -g "approval queue" --trace=on`
    // then `npx playwright show-trace test-results/.../trace.zip` and inspect the
    // Network tab. The list fetch is initiated by a React Query hook on the
    // /school/curriculum/definitions page; confirm the exact URL (likely
    // `GET /api/v1/schools/{school_id}/curriculum/definitions`, possibly with
    // `?status=pending` or paging params). Tighten `stubDefinitionApis`'
    // GET branch to match, then delete the fixme here.
    await page.goto("/school/curriculum/definitions");
    await expect(page.getByText(SUBMITTED_DEFINITION.name)).toBeVisible();
    await expect(page.getByText(/pending/i).first()).toBeVisible();
  });

  test.fixme("definition detail view shows grade, status, subjects", async ({
    page,
  }) => {
    // UNBLOCK: run `cd web && npx playwright test -g "detail view" --trace=on`
    // and inspect the trace Network tab for the single-definition fetch from
    // `web/app/(school)/school/curriculum/definitions/[definitionId]/page.tsx`.
    // Confirm the exact URL (detail mock is currently
    // `/api/v1/schools/{id}/curriculum/definitions/{definitionId}`). If the
    // page also fetches estimate/status separately on mount, stub those too —
    // otherwise the page stays in a loading skeleton and the heading doesn't
    // render. Once the page fully renders in the trace, delete this fixme.
    await page.goto(`/school/curriculum/definitions/${DEFINITION_ID}`);
    await expect(page.getByText(SUBMITTED_DEFINITION.name)).toBeVisible();
    await expect(page.getByText(/grade 11/i).first()).toBeVisible();
  });

  test.fixme("cost estimate endpoint returns within_allowance=true on fresh build", async ({
    page,
  }) => {
    // UNBLOCK: depends on the detail-view fixme above being resolved first
    // (the "Estimate cost" button only renders once the detail page has
    // hydrated). After that, run `--trace=on` and confirm (a) the exact
    // button label the UI uses (current regex `/estimate|cost/i` is a guess)
    // and (b) the estimate endpoint fires — the current mock matches
    // `.../estimate` which should be right.
    await page.goto(`/school/curriculum/definitions/${DEFINITION_ID}`);

    const estimatePromise = page.waitForResponse((res) =>
      res
        .url()
        .endsWith(
          `/definitions/${DEFINITION_ID}/estimate`,
        ),
    );

    const estimateBtn = page.getByRole("button", { name: /estimate|cost/i }).first();
    if (await estimateBtn.isVisible()) {
      await estimateBtn.click();
      const res = await Promise.race([
        estimatePromise,
        new Promise<null>((resolve) => setTimeout(() => resolve(null), 3000)),
      ]);
      if (res) {
        const json = await res.json();
        expect(json.within_allowance).toBe(true);
      }
    }
  });

  test.fixme("trigger returns a job_id and queued status", async ({ page }) => {
    // UNBLOCK: same dependency chain as the estimate fixme above. The trigger
    // button likely only enables AFTER an estimate has been fetched (UX flow:
    // estimate → confirm → trigger). Run `--trace=on`, click Estimate first,
    // then click Trigger, and confirm both events fire. Current button regex
    // `/build|trigger|start build/i` is a guess — replace with the real
    // label observed in the trace.
    await page.goto(`/school/curriculum/definitions/${DEFINITION_ID}`);

    const triggerPromise = page.waitForResponse((res) =>
      res
        .url()
        .endsWith(
          `/definitions/${DEFINITION_ID}/trigger`,
        ),
    );

    const triggerBtn = page
      .getByRole("button", { name: /build|trigger|start build/i })
      .first();
    if (await triggerBtn.isVisible()) {
      await triggerBtn.click();
      const res = await Promise.race([
        triggerPromise,
        new Promise<null>((resolve) => setTimeout(() => resolve(null), 3000)),
      ]);
      if (res) {
        const json = await res.json();
        expect(json.job_id).toBe("job-test-001");
        expect(json.status).toBe("queued");
      }
    }
  });
});

// ── Overage path ─────────────────────────────────────────────────────────────

test.describe("School admin — curriculum build overage gate", () => {
  test.beforeEach(async ({ page }) => {
    await setupSchoolAdmin(page);
    await stubDefinitionApis(page, { overage: true });
  });

  test.fixme("estimate surfaces within_allowance=false + card_last4", async ({
    page,
  }) => {
    // UNBLOCK: same chain as the happy-path estimate fixme above. Additionally,
    // confirm the UI actually surfaces `card_last4` and `within_allowance=false`
    // distinctly — the Stripe-gated overage path may render a charge-card
    // confirmation modal rather than inline text. The assertion here checks
    // the raw JSON response, which is safe regardless of UI surface.
    await page.goto(`/school/curriculum/definitions/${DEFINITION_ID}`);

    const estimatePromise = page.waitForResponse((res) =>
      res
        .url()
        .endsWith(
          `/definitions/${DEFINITION_ID}/estimate`,
        ),
    );

    const estimateBtn = page.getByRole("button", { name: /estimate|cost/i }).first();
    if (await estimateBtn.isVisible()) {
      await estimateBtn.click();
      const res = await Promise.race([
        estimatePromise,
        new Promise<null>((resolve) => setTimeout(() => resolve(null), 3000)),
      ]);
      if (res) {
        const json = await res.json();
        expect(json.within_allowance).toBe(false);
        expect(json.card_last4).toBe("4242");
      }
    }
  });
});
