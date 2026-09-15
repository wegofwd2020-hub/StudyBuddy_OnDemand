/**
 * Unit tests for section 2.10 — Curriculum Map (`/curriculum`)
 * Covers TC-IDs: STU-32, STU-33
 *
 * Run with:
 *   npm test -- curriculum-map-page
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import CurriculumMapPage from "@/app/(student)/curriculum/page";
import {
  MOCK_CURRICULUM_TREE,
  MOCK_PROGRESS_WITH_STATUS,
  MOCK_PROGRESS_EMPTY,
  CURRICULUM_MAP_STRINGS,
  lessonHref,
  quizHref,
} from "../e2e/data/curriculum-map-page";

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

vi.mock("@/components/student/OfflineBanner", () => ({
  OfflineBanner: () => null,
}));

const mockUseCurriculumTree = vi.fn();
const mockUseProgressHistory = vi.fn();

vi.mock("@/lib/hooks/useCurriculumTree", () => ({
  useCurriculumTree: () => mockUseCurriculumTree(),
}));

// The page reads per-unit status from the SERVER since #677 — it no longer
// derives it in the browser from quiz sessions. The fixtures are unchanged;
// only the seam moved, so `unit_progress` is adapted into the map the hook
// hands back.
vi.mock("@/lib/hooks/useProgressMap", () => ({
  useUnitStatuses: () => {
    const result = mockUseProgressHistory();
    const statusByUnit = new Map<string, string>();
    result?.data?.unit_progress?.forEach((up: { unit_id: string; status: string }) =>
      statusByUnit.set(up.unit_id, up.status),
    );
    return { statusByUnit, isLoading: result?.isLoading ?? false };
  },
}));

// A BookSpine's accessible name is its sr-only label: `${title}, status …`
// (and `, has lab` for lab units). Match on the title prefix.
const spineName = (title: string) => (name: string) => name.startsWith(title);

// ---------------------------------------------------------------------------
// STU-32 — Curriculum tree renders: Grade → Subject → Unit hierarchy
// ---------------------------------------------------------------------------

describe("STU-32 — Curriculum tree renders", () => {
  it("renders the page title", () => {
    mockUseCurriculumTree.mockReturnValue({
      data: MOCK_CURRICULUM_TREE,
      isLoading: false,
    });
    mockUseProgressHistory.mockReturnValue({
      data: MOCK_PROGRESS_EMPTY,
      isLoading: false,
    });
    render(<CurriculumMapPage />);
    expect(
      screen.getByRole("heading", { name: CURRICULUM_MAP_STRINGS.title }),
    ).toBeInTheDocument();
  });

  it("renders a section heading for each subject", () => {
    mockUseCurriculumTree.mockReturnValue({
      data: MOCK_CURRICULUM_TREE,
      isLoading: false,
    });
    mockUseProgressHistory.mockReturnValue({
      data: MOCK_PROGRESS_EMPTY,
      isLoading: false,
    });
    render(<CurriculumMapPage />);
    for (const subject of MOCK_CURRICULUM_TREE.subjects) {
      expect(screen.getByRole("heading", { name: subject.subject })).toBeInTheDocument();
    }
  });

  it("renders all unit titles", () => {
    mockUseCurriculumTree.mockReturnValue({
      data: MOCK_CURRICULUM_TREE,
      isLoading: false,
    });
    mockUseProgressHistory.mockReturnValue({
      data: MOCK_PROGRESS_EMPTY,
      isLoading: false,
    });
    render(<CurriculumMapPage />);
    for (const subject of MOCK_CURRICULUM_TREE.subjects) {
      for (const unit of subject.units) {
        expect(screen.getByText(unit.title)).toBeInTheDocument();
      }
    }
  });

  it("renders a Lesson link for each unit with correct href", () => {
    mockUseCurriculumTree.mockReturnValue({
      data: MOCK_CURRICULUM_TREE,
      isLoading: false,
    });
    mockUseProgressHistory.mockReturnValue({
      data: MOCK_PROGRESS_EMPTY,
      isLoading: false,
    });
    render(<CurriculumMapPage />);
    // Each unit is a BookSpine; its Lesson/Quiz links live in the Toc shown
    // after the spine is opened (only one unit open at a time).
    for (const subject of MOCK_CURRICULUM_TREE.subjects) {
      for (const unit of subject.units) {
        fireEvent.click(screen.getByRole("button", { name: spineName(unit.title) }));
        const links = screen.getAllByRole("link", {
          name: CURRICULUM_MAP_STRINGS.lessonBtn,
        });
        expect(
          links.some((l) => l.getAttribute("href") === lessonHref(unit.unit_id)),
        ).toBe(true);
      }
    }
  });

  it("renders a Quiz link for each unit with correct href", () => {
    mockUseCurriculumTree.mockReturnValue({
      data: MOCK_CURRICULUM_TREE,
      isLoading: false,
    });
    mockUseProgressHistory.mockReturnValue({
      data: MOCK_PROGRESS_EMPTY,
      isLoading: false,
    });
    render(<CurriculumMapPage />);
    for (const subject of MOCK_CURRICULUM_TREE.subjects) {
      for (const unit of subject.units) {
        fireEvent.click(screen.getByRole("button", { name: spineName(unit.title) }));
        const links = screen.getAllByRole("link", {
          name: CURRICULUM_MAP_STRINGS.quizBtn,
        });
        expect(links.some((l) => l.getAttribute("href") === quizHref(unit.unit_id))).toBe(
          true,
        );
      }
    }
  });

  it("shows an Experiment link for lab units only", () => {
    mockUseCurriculumTree.mockReturnValue({
      data: MOCK_CURRICULUM_TREE,
      isLoading: false,
    });
    mockUseProgressHistory.mockReturnValue({
      data: MOCK_PROGRESS_EMPTY,
      isLoading: false,
    });
    render(<CurriculumMapPage />);
    // The redesigned Toc replaces the old "Lab" badge with an Experiment link
    // rendered only when the opened unit has a lab.
    for (const subject of MOCK_CURRICULUM_TREE.subjects) {
      for (const unit of subject.units) {
        fireEvent.click(screen.getByRole("button", { name: spineName(unit.title) }));
        const experimentLink = screen
          .queryAllByRole("link", { name: "Experiment" })
          .find((l) => l.getAttribute("href") === `/experiment/${unit.unit_id}`);
        if (unit.has_lab) {
          expect(experimentLink).toBeTruthy();
        } else {
          expect(experimentLink).toBeFalsy();
        }
      }
    }
  });

  it("renders status legend with all four status labels", () => {
    mockUseCurriculumTree.mockReturnValue({
      data: MOCK_CURRICULUM_TREE,
      isLoading: false,
    });
    mockUseProgressHistory.mockReturnValue({
      data: MOCK_PROGRESS_EMPTY,
      isLoading: false,
    });
    render(<CurriculumMapPage />);
    expect(screen.getByText(CURRICULUM_MAP_STRINGS.completed)).toBeInTheDocument();
    expect(screen.getByText(CURRICULUM_MAP_STRINGS.needsRetry)).toBeInTheDocument();
    expect(screen.getByText(CURRICULUM_MAP_STRINGS.inProgress)).toBeInTheDocument();
    expect(screen.getByText(CURRICULUM_MAP_STRINGS.notStarted)).toBeInTheDocument();
  });

  it("shows loading skeletons while fetching", () => {
    mockUseCurriculumTree.mockReturnValue({ data: undefined, isLoading: true });
    mockUseProgressHistory.mockReturnValue({ data: undefined, isLoading: false });
    const { container } = render(<CurriculumMapPage />);
    expect(container.querySelector("[data-slot='skeleton']")).toBeTruthy();
  });
});

// ---------------------------------------------------------------------------
// STU-33 — Completed units are marked with green CheckCircle2
// ---------------------------------------------------------------------------

describe("STU-33 — Completed units marked differently", () => {
  it("completed unit shows green CheckCircle2 icon", () => {
    mockUseCurriculumTree.mockReturnValue({
      data: MOCK_CURRICULUM_TREE,
      isLoading: false,
    });
    mockUseProgressHistory.mockReturnValue({
      data: MOCK_PROGRESS_WITH_STATUS,
      isLoading: false,
    });
    const { container } = render(<CurriculumMapPage />);
    // CheckCircle2 renders with text-green-500 class
    expect(container.querySelector("svg.text-green-500")).toBeTruthy();
  });

  it("needs_retry unit shows amber AlertCircle icon", () => {
    mockUseCurriculumTree.mockReturnValue({
      data: MOCK_CURRICULUM_TREE,
      isLoading: false,
    });
    mockUseProgressHistory.mockReturnValue({
      data: MOCK_PROGRESS_WITH_STATUS,
      isLoading: false,
    });
    const { container } = render(<CurriculumMapPage />);
    expect(container.querySelector("svg.text-amber-500")).toBeTruthy();
  });

  it("in_progress unit shows blue Clock icon", () => {
    mockUseCurriculumTree.mockReturnValue({
      data: MOCK_CURRICULUM_TREE,
      isLoading: false,
    });
    mockUseProgressHistory.mockReturnValue({
      data: MOCK_PROGRESS_WITH_STATUS,
      isLoading: false,
    });
    const { container } = render(<CurriculumMapPage />);
    expect(container.querySelector("svg.text-blue-500")).toBeTruthy();
  });

  it("not_started units show gray Circle icon", () => {
    mockUseCurriculumTree.mockReturnValue({
      data: MOCK_CURRICULUM_TREE,
      isLoading: false,
    });
    mockUseProgressHistory.mockReturnValue({
      data: MOCK_PROGRESS_WITH_STATUS,
      isLoading: false,
    });
    const { container } = render(<CurriculumMapPage />);
    // 3 units are not_started + 4 legend items = at least 4 gray-300 svgs
    expect(container.querySelectorAll("svg.text-gray-300").length).toBeGreaterThan(0);
  });

  it("all units without progress default to not_started (gray)", () => {
    mockUseCurriculumTree.mockReturnValue({
      data: MOCK_CURRICULUM_TREE,
      isLoading: false,
    });
    mockUseProgressHistory.mockReturnValue({
      data: MOCK_PROGRESS_EMPTY,
      isLoading: false,
    });
    const { container } = render(<CurriculumMapPage />);
    const allUnits = MOCK_CURRICULUM_TREE.subjects.flatMap((s) => s.units);
    // Each unit + each legend entry renders a gray Circle — at least allUnits.length
    const grayIcons = container.querySelectorAll("svg.text-gray-300");
    expect(grayIcons.length).toBeGreaterThanOrEqual(allUnits.length);
  });
});

// ---------------------------------------------------------------------------
// Href helpers
// ---------------------------------------------------------------------------

describe("Curriculum map href helpers", () => {
  it("lessonHref returns /lesson/[unit_id]", () => {
    expect(lessonHref("G8-SCI-001")).toBe("/lesson/G8-SCI-001");
  });

  it("quizHref returns /quiz/[unit_id]", () => {
    expect(quizHref("G8-SCI-001")).toBe("/quiz/G8-SCI-001");
  });
});
