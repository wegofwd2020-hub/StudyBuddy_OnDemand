/**
 * Unit tests for section 2.3 — Subjects Page (`/subjects`)
 * Covers TC-IDs: STU-12, STU-13, STU-14
 *
 * Run with:
 *   npm test -- subjects-page
 *
 * STU-14 (paywall) is server-side (HTTP 402 from backend) — not testable at
 * the component level. Tests here verify href construction and data shape.
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import SubjectsPage from "@/app/(student)/subjects/page";
import {
  MOCK_CURRICULUM_TREE,
  SUBJECTS_STRINGS,
  lessonHref,
  quizHref,
} from "../e2e/data/subjects-page";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

vi.mock("next-intl", () => ({
  useTranslations: vi.fn(() => (key: string) => key),
}));

vi.mock("@/components/student/OfflineBanner", () => ({
  OfflineBanner: () => null,
}));

vi.mock("next/link", () => ({
  default: ({ href, children }: { href: string; children: React.ReactNode }) => (
    <a href={href}>{children}</a>
  ),
}));

const mockUseCurriculumTree = vi.fn();
vi.mock("@/lib/hooks/useCurriculumTree", () => ({
  useCurriculumTree: () => mockUseCurriculumTree(),
}));

// ---------------------------------------------------------------------------
// STU-12 — Subject list renders for grade
// ---------------------------------------------------------------------------

describe("STU-12 — Subject list renders", () => {
  it("shows page heading", () => {
    mockUseCurriculumTree.mockReturnValue({ data: MOCK_CURRICULUM_TREE, isLoading: false, isError: false });
    render(<SubjectsPage />);
    expect(screen.getByRole("heading", { name: SUBJECTS_STRINGS.pageHeading })).toBeInTheDocument();
  });

  it("renders a card for each subject", () => {
    mockUseCurriculumTree.mockReturnValue({ data: MOCK_CURRICULUM_TREE, isLoading: false, isError: false });
    render(<SubjectsPage />);

    for (const subject of MOCK_CURRICULUM_TREE.subjects) {
      expect(screen.getByText(subject.subject)).toBeInTheDocument();
    }
  });

  it("shows unit count for each subject card", () => {
    mockUseCurriculumTree.mockReturnValue({ data: MOCK_CURRICULUM_TREE, isLoading: false, isError: false });
    render(<SubjectsPage />);

    for (const subject of MOCK_CURRICULUM_TREE.subjects) {
      expect(
        screen.getByText(`${subject.units.length} units`),
      ).toBeInTheDocument();
    }
  });

  it("renders all unit titles", () => {
    mockUseCurriculumTree.mockReturnValue({ data: MOCK_CURRICULUM_TREE, isLoading: false, isError: false });
    render(<SubjectsPage />);

    for (const subject of MOCK_CURRICULUM_TREE.subjects) {
      for (const unit of subject.units) {
        expect(screen.getByText(unit.title)).toBeInTheDocument();
      }
    }
  });

  it("shows loading skeletons while fetching", () => {
    mockUseCurriculumTree.mockReturnValue({ data: undefined, isLoading: true, isError: false });
    const { container } = render(<SubjectsPage />);
    // Skeleton divs render during loading
    expect(container.querySelector("[data-slot='skeleton']")).toBeTruthy();
  });

  it("shows error message on fetch failure", () => {
    mockUseCurriculumTree.mockReturnValue({ data: undefined, isLoading: false, isError: true });
    render(<SubjectsPage />);
    expect(screen.getByText(SUBJECTS_STRINGS.errorMessage)).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// STU-13 — Units are visible; Lesson and Quiz buttons have correct hrefs
// (Page always renders units inline — no expand/collapse interaction needed)
// ---------------------------------------------------------------------------

describe("STU-13 — Unit buttons and hrefs", () => {
  it("each unit has a Lesson link with correct href", () => {
    mockUseCurriculumTree.mockReturnValue({ data: MOCK_CURRICULUM_TREE, isLoading: false, isError: false });
    render(<SubjectsPage />);

    for (const subject of MOCK_CURRICULUM_TREE.subjects) {
      for (const unit of subject.units) {
        const lessonLinks = screen
          .getAllByRole("link", { name: SUBJECTS_STRINGS.lessonBtn });
        const match = lessonLinks.find(
          (el) => el.getAttribute("href") === lessonHref(unit.unit_id),
        );
        expect(match).toBeTruthy();
      }
    }
  });

  it("each unit has a Quiz link with correct href", () => {
    mockUseCurriculumTree.mockReturnValue({ data: MOCK_CURRICULUM_TREE, isLoading: false, isError: false });
    render(<SubjectsPage />);

    for (const subject of MOCK_CURRICULUM_TREE.subjects) {
      for (const unit of subject.units) {
        const quizLinks = screen
          .getAllByRole("link", { name: SUBJECTS_STRINGS.quizBtn });
        const match = quizLinks.find(
          (el) => el.getAttribute("href") === quizHref(unit.unit_id),
        );
        expect(match).toBeTruthy();
      }
    }
  });

  it("lab units show a flask icon (svg)", () => {
    mockUseCurriculumTree.mockReturnValue({ data: MOCK_CURRICULUM_TREE, isLoading: false, isError: false });
    const { container } = render(<SubjectsPage />);

    const labUnits = MOCK_CURRICULUM_TREE.subjects
      .flatMap((s) => s.units)
      .filter((u) => u.has_lab);

    // Each lab unit row contains an svg (FlaskConical icon)
    expect(labUnits.length).toBeGreaterThan(0);
    const svgs = container.querySelectorAll("svg");
    expect(svgs.length).toBeGreaterThanOrEqual(labUnits.length);
  });

  it("non-lab units do not add extra flask icons", () => {
    const nonLabOnly: typeof MOCK_CURRICULUM_TREE = {
      ...MOCK_CURRICULUM_TREE,
      subjects: [
        {
          subject: "Mathematics",
          units: MOCK_CURRICULUM_TREE.subjects[0].units, // all has_lab: false
        },
      ],
    };
    mockUseCurriculumTree.mockReturnValue({ data: nonLabOnly, isLoading: false, isError: false });
    const { container } = render(<SubjectsPage />);

    const svgs = container.querySelectorAll("svg");
    expect(svgs).toHaveLength(0);
  });
});

// ---------------------------------------------------------------------------
// STU-14 — Paywall — data-level verification
// (Actual paywall redirect is triggered server-side on /lesson/[unit_id] — HTTP 402)
// ---------------------------------------------------------------------------

describe("STU-14 — Paywall href construction", () => {
  it("lesson href follows /lesson/[unit_id] pattern", () => {
    expect(lessonHref("G8-SCI-001")).toBe("/lesson/G8-SCI-001");
  });

  it("quiz href follows /quiz/[unit_id] pattern", () => {
    expect(quizHref("G8-SCI-001")).toBe("/quiz/G8-SCI-001");
  });

  it("all unit hrefs are unique", () => {
    const allUnits = MOCK_CURRICULUM_TREE.subjects.flatMap((s) => s.units);
    const lessonHrefs = allUnits.map((u) => lessonHref(u.unit_id));
    const unique = new Set(lessonHrefs);
    expect(unique.size).toBe(allUnits.length);
  });
});
