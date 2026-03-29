/**
 * Unit tests for section 2.10 — Curriculum Map (`/curriculum`)
 * Covers TC-IDs: STU-32, STU-33
 *
 * Run with:
 *   npm test -- curriculum-map-page
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
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

vi.mock("@/lib/hooks/useProgress", () => ({
  useProgressHistory: () => mockUseProgressHistory(),
}));

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
    for (const subject of MOCK_CURRICULUM_TREE.subjects) {
      for (const unit of subject.units) {
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
        const links = screen.getAllByRole("link", {
          name: CURRICULUM_MAP_STRINGS.quizBtn,
        });
        expect(links.some((l) => l.getAttribute("href") === quizHref(unit.unit_id))).toBe(
          true,
        );
      }
    }
  });

  it("renders Lab badge for lab units only", () => {
    mockUseCurriculumTree.mockReturnValue({
      data: MOCK_CURRICULUM_TREE,
      isLoading: false,
    });
    mockUseProgressHistory.mockReturnValue({
      data: MOCK_PROGRESS_EMPTY,
      isLoading: false,
    });
    render(<CurriculumMapPage />);
    const labBadges = screen.getAllByText(CURRICULUM_MAP_STRINGS.labBadge);
    const labUnitCount = MOCK_CURRICULUM_TREE.subjects
      .flatMap((s) => s.units)
      .filter((u) => u.has_lab).length;
    expect(labBadges).toHaveLength(labUnitCount);
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
