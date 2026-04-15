/**
 * tests/e2e/helpers/axe.ts
 *
 * Thin wrapper around @axe-core/playwright.
 *
 * Usage:
 *   import { checkA11y } from "../helpers/axe";
 *   await checkA11y(page, "Student dashboard");
 *
 * Fails the calling test if any critical or serious WCAG violations are found,
 * with a readable summary of each violation.
 */

import AxeBuilder from "@axe-core/playwright";
import type { Page } from "@playwright/test";
import { expect } from "@playwright/test";

export interface A11yViolation {
  id: string;
  impact: string;
  description: string;
  helpUrl: string;
  nodes: number;
}

export interface A11yReport {
  page: string;
  url: string;
  violations: A11yViolation[];
  passes: number;
  incomplete: number;
}

/**
 * Run axe-core on the current page state and assert zero critical/serious violations.
 *
 * Checks WCAG 2.1 A + AA rules plus best-practice rules.
 * Violations at "moderate" or "minor" impact are recorded in the report
 * but do not fail the test — raise the bar incrementally over time.
 *
 * @param page          Playwright page object
 * @param label         Human-readable name used in failure messages and reports
 * @param excludeRules  Axe rule IDs to disable for this check. Use sparingly,
 *                      and only when a regression is already tracked — the
 *                      default posture is zero exclusions.
 */
export async function checkA11y(
  page: Page,
  label: string,
  excludeRules: readonly string[] = [],
): Promise<A11yReport> {
  let builder = new AxeBuilder({ page }).withTags([
    "wcag2a",
    "wcag2aa",
    "best-practice",
  ]);
  if (excludeRules.length > 0) {
    builder = builder.disableRules([...excludeRules]);
  }
  const results = await builder.analyze();

  const critical = results.violations.filter(
    (v) => v.impact === "critical" || v.impact === "serious",
  );

  const report: A11yReport = {
    page: label,
    url: page.url(),
    violations: results.violations.map((v) => ({
      id: v.id,
      impact: v.impact ?? "unknown",
      description: v.description,
      helpUrl: v.helpUrl,
      nodes: v.nodes.length,
    })),
    passes: results.passes.length,
    incomplete: results.incomplete.length,
  };

  if (critical.length > 0) {
    const summary = critical
      .map(
        (v) =>
          `  [${v.impact}] ${v.id}: ${v.description}` +
          ` (${v.nodes.length} node(s))\n    ${v.helpUrl}`,
      )
      .join("\n");

    expect(
      critical.length,
      `${label}: ${critical.length} critical/serious WCAG violation(s) found:\n${summary}`,
    ).toBe(0);
  }

  return report;
}
