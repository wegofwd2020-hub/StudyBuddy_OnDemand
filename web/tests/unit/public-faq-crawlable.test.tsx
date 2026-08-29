/**
 * Public-page FAQs are collapsed, and their answers stay in the DOM.
 *
 * Collapsing the FAQ is a deliberate design choice (docs/DESIGN_kolibri_site_teardown.md
 * "What to take" #1). The trap is that Base UI's Accordion.Panel defaults to
 * keepMounted={false}, so a closed panel renders NOTHING — collapsing a marketing
 * FAQ the obvious way silently deletes every answer from the server-rendered HTML.
 * Search engines then index a page of questions with no answers, and a visitor's
 * Ctrl+F finds nothing.
 *
 * `hiddenUntilFound` is what makes the collapse safe: hidden="until-found" leaves
 * the text in the DOM and lets browser find-in-page expand the panel. These tests
 * assert the OUTCOME (answer text present while collapsed), not the prop, so they
 * still hold if the component is swapped out.
 *
 * Verified to fail in both directions: dropping `hiddenUntilFound` from either page
 * makes that page's test fail on the answer-text assertion.
 */
import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import ForSchoolsPage from "@/app/(public)/for-schools/page";
import PricingPage from "@/app/(public)/pricing/page";

const PAGES = [
  {
    name: "/for-schools",
    Page: ForSchoolsPage,
    // Distinctive fragments of FAQ ANSWER copy — never of a question.
    answers: ["Most schools are live in under 20 minutes"],
  },
  {
    name: "/pricing",
    Page: PricingPage,
    answers: ["the school acts as the consent authority"],
  },
];

describe.each(PAGES)("$name FAQ", ({ Page, answers }) => {
  it("renders answers into the DOM even though the accordion starts closed", () => {
    const { container } = render(<Page />);

    // The section is genuinely collapsed: every trigger reports aria-expanded="false".
    const triggers = container.querySelectorAll('[data-slot="accordion-trigger"]');
    expect(triggers.length).toBeGreaterThan(0);
    for (const t of triggers) {
      expect(t.getAttribute("aria-expanded")).toBe("false");
    }

    // ...and yet the answer copy is present. This is the assertion that fails
    // without hiddenUntilFound, because the closed panel would not render at all.
    for (const answer of answers) {
      expect(container.textContent).toContain(answer);
    }
  });

  it("keeps each question reachable as an accordion trigger", () => {
    const { container } = render(<Page />);
    const triggers = container.querySelectorAll('[data-slot="accordion-trigger"]');
    const panels = container.querySelectorAll('[data-slot="accordion-content"]');
    // One panel per question — a panel count of 0 is the failure mode this guards.
    expect(panels.length).toBe(triggers.length);
  });
});

describe("no public FAQ renders fully expanded", () => {
  it("does not fall back to an always-open definition list", () => {
    for (const { Page } of PAGES) {
      const { container, unmount } = render(<Page />);
      // The pre-collapse treatment was a <dl> of open <dt>/<dd> cards. If one
      // reappears alongside no accordion, the page has regressed to that.
      const hasAccordion =
        container.querySelectorAll('[data-slot="accordion-trigger"]').length > 0;
      expect(hasAccordion).toBe(true);
      unmount();
    }
  });
});
