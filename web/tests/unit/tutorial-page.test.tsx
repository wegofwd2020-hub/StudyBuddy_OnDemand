/**
 * Unit tests for section 2.6 — Tutorial Page components
 * Covers TC-IDs: STU-26
 *
 * Run with:
 *   npm test -- tutorial-page
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { TutorialRenderer } from "@/components/content/TutorialRenderer";
import {
  MOCK_TUTORIAL,
  MOCK_TUTORIAL_NO_SUMMARY,
  TUTORIAL_STRINGS,
  quizHref,
} from "../e2e/data/tutorial-page";

// ---------------------------------------------------------------------------
// Shared mocks
// ---------------------------------------------------------------------------

vi.mock("next-intl", () => ({
  useTranslations: vi.fn(() => (key: string) => key),
}));

vi.mock("next/link", () => ({
  default: ({ href, children }: { href: string; children: React.ReactNode }) => (
    <a href={href}>{children}</a>
  ),
}));

// ---------------------------------------------------------------------------
// STU-26 — TutorialRenderer: tutorial content loads
// ---------------------------------------------------------------------------

describe("STU-26 — TutorialRenderer: tutorial content loads", () => {
  it("renders the tutorial title as H1", () => {
    render(<TutorialRenderer tutorial={MOCK_TUTORIAL} />);
    expect(
      screen.getByRole("heading", { level: 1, name: MOCK_TUTORIAL.title }),
    ).toBeInTheDocument();
  });

  it("renders the tutorial objective", () => {
    render(<TutorialRenderer tutorial={MOCK_TUTORIAL} />);
    expect(screen.getByText(MOCK_TUTORIAL.objective)).toBeInTheDocument();
  });

  it("renders all step numbers in the ordered list", () => {
    render(<TutorialRenderer tutorial={MOCK_TUTORIAL} />);
    for (const step of MOCK_TUTORIAL.steps) {
      expect(screen.getByText(String(step.step))).toBeInTheDocument();
    }
  });

  it("renders all step titles as headings", () => {
    render(<TutorialRenderer tutorial={MOCK_TUTORIAL} />);
    for (const step of MOCK_TUTORIAL.steps) {
      expect(
        screen.getByRole("heading", { name: step.title }),
      ).toBeInTheDocument();
    }
  });

  it("renders all step body text", () => {
    render(<TutorialRenderer tutorial={MOCK_TUTORIAL} />);
    for (const step of MOCK_TUTORIAL.steps) {
      expect(screen.getByText(step.body)).toBeInTheDocument();
    }
  });

  it("renders Summary heading when summary is present", () => {
    render(<TutorialRenderer tutorial={MOCK_TUTORIAL} />);
    expect(
      screen.getByRole("heading", { name: TUTORIAL_STRINGS.summaryHeading }),
    ).toBeInTheDocument();
  });

  it("renders summary body text", () => {
    render(<TutorialRenderer tutorial={MOCK_TUTORIAL} />);
    expect(screen.getByText(MOCK_TUTORIAL.summary)).toBeInTheDocument();
  });

  it("does not render Summary section when summary is empty", () => {
    render(<TutorialRenderer tutorial={MOCK_TUTORIAL_NO_SUMMARY} />);
    expect(
      screen.queryByRole("heading", { name: TUTORIAL_STRINGS.summaryHeading }),
    ).toBeNull();
  });

  it("renders steps in an ordered list", () => {
    const { container } = render(<TutorialRenderer tutorial={MOCK_TUTORIAL} />);
    expect(container.querySelector("ol")).toBeTruthy();
  });

  it("correct number of list items matches step count", () => {
    const { container } = render(<TutorialRenderer tutorial={MOCK_TUTORIAL} />);
    const items = container.querySelectorAll("li");
    expect(items).toHaveLength(MOCK_TUTORIAL.steps.length);
  });

  it("each step number renders inside a blue circle badge", () => {
    const { container } = render(<TutorialRenderer tutorial={MOCK_TUTORIAL} />);
    const badges = container.querySelectorAll("div.bg-blue-600");
    expect(badges).toHaveLength(MOCK_TUTORIAL.steps.length);
  });
});

// ---------------------------------------------------------------------------
// STU-26 — CTA: Take Quiz href construction
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
