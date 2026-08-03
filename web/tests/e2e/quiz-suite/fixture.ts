/**
 * Shared helpers for the live quiz suite.
 *
 * Unlike every other spec in tests/e2e, these register NO route mocks — the
 * whole point is to exercise the real backend.
 *
 * NOTE ON LOGIN: the brief this file was drafted from assumed a `/login`
 * page with `getByLabel(/email/i)` / `getByLabel(/password/i)` fields and a
 * "sign in|log in" button. That page (`web/app/(public)/login/page.tsx`) is
 * actually just an interstitial that links out to Auth0 — it has no form.
 * The fixture's students are LOCAL-auth (school-provisioned; see
 * `backend/quiz_suite/seed.py` — `auth_provider: 'local'`), and the real
 * sign-in form for that track lives at `/signin`
 * (`web/app/(public)/signin/page.tsx`), which posts to
 * `POST /api/v1/auth/universal-login` and, for a `role: "student"` /
 * `auth_track: "local"` response, routes to `/dashboard`. Selectors below
 * were matched against that component, not the brief's guess.
 */
import fs from "node:fs";
import path from "node:path";
import { expect, type Page } from "@playwright/test";

export interface QuizFixture {
  student_a_email: string;
  student_b_email: string;
  password: string;
  curriculum_id: string;
  unit_quiz: string;
  unit_noquiz: string;
  answer_key: Record<string, Record<string, number>>;
}

export function loadFixture(): QuizFixture {
  const file = path.join(__dirname, ".fixture.json");
  if (!fs.existsSync(file)) {
    throw new Error(`${file} missing — run scripts/quiz_suite.sh, which seeds first.`);
  }
  return JSON.parse(fs.readFileSync(file, "utf8")) as QuizFixture;
}

export async function loginAsStudentA(page: Page): Promise<void> {
  const fixture = loadFixture();
  await page.goto("/signin");
  await page.getByRole("textbox", { name: "Email" }).fill(fixture.student_a_email);
  await page.getByRole("textbox", { name: "Password" }).fill(fixture.password);
  await page.getByRole("button", { name: /^sign in$/i }).click();
  // Local student track (first_login=false, per seed.py) routes to /dashboard.
  await expect(page).toHaveURL(/\/dashboard/, { timeout: 15000 });
}
