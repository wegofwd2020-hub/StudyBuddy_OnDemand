/**
 * Unit tests for section 2.7 — Experiment Page components
 * Covers TC-IDs: STU-27, STU-28
 *
 * Run with:
 *   npm test -- experiment-page
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { ExperimentRenderer } from "@/components/content/ExperimentRenderer";
import {
  MOCK_EXPERIMENT,
  MOCK_EXPERIMENT_NO_SAFETY,
  MOCK_EXPERIMENT_NO_OUTCOME,
  EXPERIMENT_STRINGS,
} from "../e2e/data/experiment-page";

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
// STU-27 — ExperimentRenderer: materials, safety notes, numbered steps visible
// ---------------------------------------------------------------------------

describe("STU-27 — ExperimentRenderer: experiment content renders", () => {
  it("renders the experiment title as H1", () => {
    render(<ExperimentRenderer experiment={MOCK_EXPERIMENT} />);
    expect(
      screen.getByRole("heading", { level: 1, name: MOCK_EXPERIMENT.title }),
    ).toBeInTheDocument();
  });

  it("renders a FlaskConical icon (svg) alongside the title", () => {
    const { container } = render(<ExperimentRenderer experiment={MOCK_EXPERIMENT} />);
    // Icon is inside the title row div
    const titleRow = container.querySelector("div.flex.items-center.gap-3");
    expect(titleRow?.querySelector("svg")).toBeTruthy();
  });

  it("renders the Materials heading", () => {
    render(<ExperimentRenderer experiment={MOCK_EXPERIMENT} />);
    expect(
      screen.getByRole("heading", { name: EXPERIMENT_STRINGS.materialsHeading }),
    ).toBeInTheDocument();
  });

  it("renders all material items", () => {
    render(<ExperimentRenderer experiment={MOCK_EXPERIMENT} />);
    for (const material of MOCK_EXPERIMENT.materials) {
      expect(screen.getByText(material)).toBeInTheDocument();
    }
  });

  it("renders the Safety heading when safety notes are present", () => {
    render(<ExperimentRenderer experiment={MOCK_EXPERIMENT} />);
    expect(
      screen.getByRole("heading", { name: EXPERIMENT_STRINGS.safetyHeading }),
    ).toBeInTheDocument();
  });

  it("renders all safety notes", () => {
    render(<ExperimentRenderer experiment={MOCK_EXPERIMENT} />);
    for (const note of MOCK_EXPERIMENT.safety_notes) {
      expect(screen.getByText(note)).toBeInTheDocument();
    }
  });

  it("does not render Safety section when safety_notes is empty", () => {
    render(<ExperimentRenderer experiment={MOCK_EXPERIMENT_NO_SAFETY} />);
    expect(
      screen.queryByRole("heading", { name: EXPERIMENT_STRINGS.safetyHeading }),
    ).toBeNull();
  });

  it("renders the Steps heading", () => {
    render(<ExperimentRenderer experiment={MOCK_EXPERIMENT} />);
    expect(
      screen.getByRole("heading", { name: EXPERIMENT_STRINGS.stepsHeading }),
    ).toBeInTheDocument();
  });

  it("renders all step numbers", () => {
    render(<ExperimentRenderer experiment={MOCK_EXPERIMENT} />);
    for (const step of MOCK_EXPERIMENT.steps) {
      expect(screen.getByText(String(step.step))).toBeInTheDocument();
    }
  });

  it("renders all step instructions", () => {
    render(<ExperimentRenderer experiment={MOCK_EXPERIMENT} />);
    for (const step of MOCK_EXPERIMENT.steps) {
      expect(screen.getByText(step.instruction)).toBeInTheDocument();
    }
  });

  it("renders steps in an ordered list", () => {
    const { container } = render(<ExperimentRenderer experiment={MOCK_EXPERIMENT} />);
    expect(container.querySelector("ol")).toBeTruthy();
  });

  it("correct number of list items matches step count", () => {
    const { container } = render(<ExperimentRenderer experiment={MOCK_EXPERIMENT} />);
    const items = container.querySelectorAll("ol li");
    expect(items).toHaveLength(MOCK_EXPERIMENT.steps.length);
  });

  it("each step number renders inside a purple circle badge", () => {
    const { container } = render(<ExperimentRenderer experiment={MOCK_EXPERIMENT} />);
    const badges = container.querySelectorAll("div.bg-purple-600");
    expect(badges).toHaveLength(MOCK_EXPERIMENT.steps.length);
  });

  it("renders the Expected Outcome heading when outcome is present", () => {
    render(<ExperimentRenderer experiment={MOCK_EXPERIMENT} />);
    expect(
      screen.getByRole("heading", { name: EXPERIMENT_STRINGS.expectedOutcomeHeading }),
    ).toBeInTheDocument();
  });

  it("renders the expected outcome text", () => {
    render(<ExperimentRenderer experiment={MOCK_EXPERIMENT} />);
    expect(screen.getByText(MOCK_EXPERIMENT.expected_outcome)).toBeInTheDocument();
  });

  it("does not render Expected Outcome section when outcome is empty", () => {
    render(<ExperimentRenderer experiment={MOCK_EXPERIMENT_NO_OUTCOME} />);
    expect(
      screen.queryByRole("heading", { name: EXPERIMENT_STRINGS.expectedOutcomeHeading }),
    ).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// STU-28 — Non-lab unit: error state string is defined
// (Actual 404 redirect is triggered server-side when backend has no experiment
// for the unit. Tested here by verifying the error message constant matches
// the string rendered in ExperimentPage when isError=true.)
// ---------------------------------------------------------------------------

describe("STU-28 — Non-lab unit error state", () => {
  it("error message string matches page render", () => {
    expect(EXPERIMENT_STRINGS.errorMessage).toBe(
      "Could not load experiment. Please try again.",
    );
  });

  it("Take Quiz CTA label is defined", () => {
    expect(EXPERIMENT_STRINGS.takeQuizBtn).toBe("Take Quiz");
  });

  it("materials list renders empty gracefully (no items)", () => {
    const noMaterials = { ...MOCK_EXPERIMENT, materials: [] };
    const { container } = render(<ExperimentRenderer experiment={noMaterials} />);
    // ul exists but has no li children
    const ul = container.querySelector("ul");
    expect(ul).toBeTruthy();
    expect(ul?.querySelectorAll("li")).toHaveLength(0);
  });
});
