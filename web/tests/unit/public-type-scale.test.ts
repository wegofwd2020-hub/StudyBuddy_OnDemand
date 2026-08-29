/**
 * Marketing pages use one heading scale.
 *
 * Item 3 of docs/DESIGN_kolibri_site_teardown.md "What to take" — *"use few
 * levels, not few sizes"*. Kolibri runs about four heading levels and adds none
 * of its own; the calm comes from restraint in USE, not from a shrunken scale.
 *
 * A raw census of the public tree counts ten type sizes, which sounds like drift
 * but mostly is not: the tree holds three page families with genuinely different
 * needs, and the count was measuring across all three.
 *
 *   marketing   landing · for-schools · pricing · quality · tour gateway
 *               hero h1 at text-4xl sm:text-5xl, section h2 at text-3xl
 *   long-form   privacy · terms · accessibility
 *               h2 at text-xl, because a legal document is not a landing page
 *   utility     login · verify · reset-password · dev-login · demo request
 *               h1 at text-xl, because it titles a card, not a page
 *
 * The real drift was WITHIN the marketing family: pricing's hero was the only
 * one with no responsive step, the tour gateway sat a full level below its
 * siblings, and two section h2s were text-2xl while their neighbours were
 * text-3xl. Those are fixed; this pins them so they cannot drift back.
 *
 * Scope is deliberately the marketing family only. Flattening the other two
 * families into it would be worse, not better -- a login card whose title is
 * rendered at hero size is not restraint.
 */
import { readFileSync } from "node:fs";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

const PAGES = join(process.cwd(), "app/(public)");

/** Pages whose h1 is a marketing hero. Excludes the step-walkthrough tour
 *  sub-pages, whose h1 is the current step's title (app-like, not a hero). */
const MARKETING = [
  "page.tsx",
  "for-schools/page.tsx",
  "pricing/page.tsx",
  "quality/page.tsx",
  "tour/page.tsx",
];

const SIZE = /\b((?:sm:|md:|lg:|xl:)?text-(?:xs|sm|base|lg|xl|2xl|3xl|4xl|5xl|6xl))\b/g;

function headings(rel: string, tag: "h1" | "h2"): string[][] {
  const src = readFileSync(join(PAGES, rel), "utf8");
  const out: string[][] = [];
  for (const m of src.matchAll(new RegExp(`<${tag}\\b([^>]*)>`, "g"))) {
    out.push([...m[1].matchAll(SIZE)].map((x) => x[1]));
  }
  return out;
}

describe("marketing heroes share one heading level", () => {
  it.each(MARKETING)("%s h1 is text-4xl sm:text-5xl", (rel) => {
    const h1s = headings(rel, "h1");
    expect(h1s.length, `${rel} should have exactly one h1`).toBe(1);
    const sizes = h1s[0];
    expect(sizes, `${rel} hero h1`).toContain("text-4xl");
    expect(sizes, `${rel} hero h1`).toContain("sm:text-5xl");
  });

  it("only the landing page adds a step above the shared hero level", () => {
    // The site's front door may be the largest thing on it -- Kolibri does the
    // same, giving h1 its one custom rule (.kolibri-page-header). What matters
    // is that this stays a deliberate exception rather than spreading.
    const withLg = MARKETING.filter((rel) =>
      headings(rel, "h1")[0]?.some((s) => s.endsWith("text-6xl")),
    );
    expect(withLg).toEqual(["page.tsx"]);
  });
});

describe("marketing section headings share one level", () => {
  it.each(MARKETING)("%s section h2s are text-3xl", (rel) => {
    for (const sizes of headings(rel, "h2")) {
      // Card titles inside a section legitimately sit lower (text-lg and below);
      // this guards the SECTION heads, which are the ones that set the page's
      // rhythm. Anything in between -- text-2xl, text-xl -- is the drift.
      const isSectionHead = sizes.some((s) =>
        ["text-2xl", "text-3xl", "text-4xl", "sm:text-3xl"].includes(s),
      );
      if (!isSectionHead) continue;
      expect(
        sizes,
        `${rel} section h2 should be text-3xl, got ${sizes.join(" ")}`,
      ).toContain("text-3xl");
      expect(sizes, `${rel} section h2 should not also carry text-2xl`).not.toContain(
        "text-2xl",
      );
    }
  });
});

describe("the other two families are left alone on purpose", () => {
  it("long-form legal pages keep their smaller section heads", () => {
    // If someone "fixes" these to text-3xl the documents become unreadable
    // walls of shouting. The count of sizes is not the goal.
    for (const rel of ["privacy/page.tsx", "terms/page.tsx", "accessibility/page.tsx"]) {
      const h2s = headings(rel, "h2");
      expect(h2s.length, `${rel} should have section h2s`).toBeGreaterThan(0);
      expect(
        h2s.some((sizes) => sizes.includes("text-xl")),
        `${rel} long-form h2s should stay at text-xl`,
      ).toBe(true);
    }
  });
});
