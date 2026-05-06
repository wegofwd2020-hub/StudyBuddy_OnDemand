/**
 * Unit tests for section 2.6 — Tutorial Page components
 * Covers TC-IDs: STU-26
 *
 * Run with:
 *   npm test -- tutorial-page
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, within } from "@testing-library/react";
import { TutorialRenderer } from "@/components/content/TutorialRenderer";
import {
  MOCK_TUTORIAL,
  MOCK_TUTORIAL_NO_SUMMARY,
  TUTORIAL_STRINGS,
  quizHref,
} from "../e2e/data/tutorial-page";

vi.mock("next-intl", () => ({
  useTranslations: vi.fn(() => (key: string) => key),
}));

vi.mock("next/link", () => ({
  default: ({ href, children }: { href: string; children: React.ReactNode }) => (
    <a href={href}>{children}</a>
  ),
}));

// ---------------------------------------------------------------------------
// STU-26 — TutorialRenderer: title + section disclosures
// ---------------------------------------------------------------------------

describe("STU-26 — TutorialRenderer: title + section disclosures", () => {
  it("renders the tutorial title as H1", () => {
    render(<TutorialRenderer tutorial={MOCK_TUTORIAL} />);
    expect(
      screen.getByRole("heading", { level: 1, name: MOCK_TUTORIAL.title }),
    ).toBeInTheDocument();
  });

  it("renders one disclosure button per section", () => {
    render(<TutorialRenderer tutorial={MOCK_TUTORIAL} />);
    for (const section of MOCK_TUTORIAL.sections) {
      expect(
        screen.getByRole("button", { name: new RegExp(section.title) }),
      ).toBeInTheDocument();
    }
  });

  it("first section is expanded by default; others are collapsed", () => {
    render(<TutorialRenderer tutorial={MOCK_TUTORIAL} />);
    const buttons = screen.getAllByRole("button", { expanded: true });
    expect(buttons).toHaveLength(1);
    expect(buttons[0]).toHaveAccessibleName(
      new RegExp(MOCK_TUTORIAL.sections[0].title),
    );
  });

  it("clicking a collapsed section expands it (aria-expanded toggles)", () => {
    render(<TutorialRenderer tutorial={MOCK_TUTORIAL} />);
    const second = screen.getByRole("button", {
      name: new RegExp(MOCK_TUTORIAL.sections[1].title),
    });
    expect(second).toHaveAttribute("aria-expanded", "false");
    fireEvent.click(second);
    expect(second).toHaveAttribute("aria-expanded", "true");
  });

  it("Expand all toggles every section open", () => {
    render(<TutorialRenderer tutorial={MOCK_TUTORIAL} />);
    fireEvent.click(screen.getByRole("button", { name: /expand all/i }));
    const expanded = screen.getAllByRole("button", { expanded: true });
    expect(expanded.length).toBe(MOCK_TUTORIAL.sections.length);
  });
});

// ---------------------------------------------------------------------------
// STU-26 — Common mistakes card
// ---------------------------------------------------------------------------

describe("STU-26 — Common mistakes card", () => {
  it("renders Common mistakes heading when list is non-empty", () => {
    render(<TutorialRenderer tutorial={MOCK_TUTORIAL} />);
    expect(
      screen.getByRole("heading", { name: TUTORIAL_STRINGS.commonMistakesHeading }),
    ).toBeInTheDocument();
  });

  it("renders every common-mistake bullet", () => {
    render(<TutorialRenderer tutorial={MOCK_TUTORIAL} />);
    for (const m of MOCK_TUTORIAL.common_mistakes) {
      expect(screen.getByText(m)).toBeInTheDocument();
    }
  });

  it("does not render Common mistakes card when list is empty", () => {
    render(<TutorialRenderer tutorial={MOCK_TUTORIAL_NO_SUMMARY} />);
    expect(
      screen.queryByRole("heading", { name: TUTORIAL_STRINGS.commonMistakesHeading }),
    ).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// STU-26 — Take Quiz CTA href
// ---------------------------------------------------------------------------

describe("STU-26 — Take Quiz CTA href", () => {
  it("quizHref returns /quiz/[unit_id]", () => {
    expect(quizHref("G8-SCI-001")).toBe("/quiz/G8-SCI-001");
  });

  it("MOCK_TUTORIAL unit_id is defined", () => {
    expect(MOCK_TUTORIAL.unit_id).toBeTruthy();
  });

  it("quiz href for mock tutorial unit is correct", () => {
    expect(quizHref(MOCK_TUTORIAL.unit_id)).toBe(`/quiz/${MOCK_TUTORIAL.unit_id}`);
  });
});

// ---------------------------------------------------------------------------
// STU-26 — Error and loading state strings
// ---------------------------------------------------------------------------

describe("STU-26 — Error state string", () => {
  it("error message string is defined", () => {
    expect(TUTORIAL_STRINGS.errorMessage).toBe(
      "Could not load tutorial. Please try again.",
    );
  });

  it("Take Quiz button label is defined", () => {
    expect(TUTORIAL_STRINGS.takeQuizBtn).toBe("Take Quiz");
  });
});

// Suppress unused import warning in test environments
void within;
