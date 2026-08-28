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

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, within } from "@testing-library/react";
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
const mockUseUnitStatuses = vi.fn(() => ({
  statusByUnit: new Map<string, string>(),
  isLoading: false,
}));

// Per-unit status comes from the server (#677). Mocked at the hook so these
// tests stay about rendering rather than needing a QueryClientProvider.
vi.mock("@/lib/hooks/useProgressMap", () => ({
  useUnitStatuses: () => mockUseUnitStatuses(),
}));

const mockSearchParams = vi.fn(() => new URLSearchParams());
vi.mock("next/navigation", () => ({
  useSearchParams: () => mockSearchParams(),
}));

vi.mock("@/lib/hooks/useCurriculumTree", () => ({
  useCurriculumTree: () => mockUseCurriculumTree(),
}));

// ---------------------------------------------------------------------------
// STU-12 — Subject list renders for grade
// ---------------------------------------------------------------------------

describe("STU-12 — Subject list renders", () => {
  it("shows page heading", () => {
    mockUseCurriculumTree.mockReturnValue({
      data: MOCK_CURRICULUM_TREE,
      isLoading: false,
      isError: false,
    });
    render(<SubjectsPage />);
    expect(
      screen.getByRole("heading", { name: SUBJECTS_STRINGS.pageHeading }),
    ).toBeInTheDocument();
  });

  it("renders a spine for each subject", () => {
    mockUseCurriculumTree.mockReturnValue({
      data: MOCK_CURRICULUM_TREE,
      isLoading: false,
      isError: false,
    });
    render(<SubjectsPage />);

    // Each subject renders a clickable BookSpine whose accessible name is the
    // subject (from its sr-only label).
    for (const subject of MOCK_CURRICULUM_TREE.subjects) {
      expect(screen.getByRole("button", { name: subject.subject })).toBeInTheDocument();
    }
  });

  it("shows unit count in the opened subject panel", () => {
    mockUseCurriculumTree.mockReturnValue({
      data: MOCK_CURRICULUM_TREE,
      isLoading: false,
      isError: false,
    });
    render(<SubjectsPage />);

    // Units (and the count) live in the BookOpen panel shown after a spine is
    // opened — only one subject is open at a time.
    for (const subject of MOCK_CURRICULUM_TREE.subjects) {
      fireEvent.click(screen.getByRole("button", { name: subject.subject }));
      const n = subject.units.length;
      expect(screen.getByText(`${n} unit${n !== 1 ? "s" : ""}`)).toBeInTheDocument();
    }
  });

  it("renders all unit titles in the opened subject panel", () => {
    mockUseCurriculumTree.mockReturnValue({
      data: MOCK_CURRICULUM_TREE,
      isLoading: false,
      isError: false,
    });
    render(<SubjectsPage />);

    for (const subject of MOCK_CURRICULUM_TREE.subjects) {
      fireEvent.click(screen.getByRole("button", { name: subject.subject }));
      const panel = screen.getByRole("region", {
        name: `${subject.units.length} unit${subject.units.length !== 1 ? "s" : ""} for ${subject.subject}`,
      });
      for (const unit of subject.units) {
        expect(within(panel).getByText(unit.title)).toBeInTheDocument();
      }
    }
  });

  it("shows loading skeletons while fetching", () => {
    mockUseCurriculumTree.mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
    });
    const { container } = render(<SubjectsPage />);
    // Skeleton divs render during loading
    expect(container.querySelector("[data-slot='skeleton']")).toBeTruthy();
  });

  it("shows error message on fetch failure", () => {
    mockUseCurriculumTree.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
    });
    render(<SubjectsPage />);
    expect(screen.getByText(SUBJECTS_STRINGS.errorMessage)).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// STU-13 — Units and Lesson/Quiz buttons after opening a subject
// (Units live in the BookOpen panel — open the spine to reveal them.)
// ---------------------------------------------------------------------------

describe("STU-13 — Unit buttons and hrefs", () => {
  it("each unit has a Lesson link with correct href", () => {
    mockUseCurriculumTree.mockReturnValue({
      data: MOCK_CURRICULUM_TREE,
      isLoading: false,
      isError: false,
    });
    render(<SubjectsPage />);

    for (const subject of MOCK_CURRICULUM_TREE.subjects) {
      fireEvent.click(screen.getByRole("button", { name: subject.subject }));
      for (const unit of subject.units) {
        const lessonLinks = screen.getAllByRole("link", {
          name: SUBJECTS_STRINGS.lessonBtn,
        });
        const match = lessonLinks.find(
          (el) => el.getAttribute("href") === lessonHref(unit.unit_id),
        );
        expect(match).toBeTruthy();
      }
    }
  });

  it("each unit has a Quiz link with correct href", () => {
    mockUseCurriculumTree.mockReturnValue({
      data: MOCK_CURRICULUM_TREE,
      isLoading: false,
      isError: false,
    });
    render(<SubjectsPage />);

    for (const subject of MOCK_CURRICULUM_TREE.subjects) {
      fireEvent.click(screen.getByRole("button", { name: subject.subject }));
      for (const unit of subject.units) {
        const quizLinks = screen.getAllByRole("link", { name: SUBJECTS_STRINGS.quizBtn });
        const match = quizLinks.find(
          (el) => el.getAttribute("href") === quizHref(unit.unit_id),
        );
        expect(match).toBeTruthy();
      }
    }
  });

  it("lab units show a flask icon (svg)", () => {
    mockUseCurriculumTree.mockReturnValue({
      data: MOCK_CURRICULUM_TREE,
      isLoading: false,
      isError: false,
    });
    const { container } = render(<SubjectsPage />);

    // Open the subject that contains lab units (Science).
    const labSubject = MOCK_CURRICULUM_TREE.subjects.find((s) =>
      s.units.some((u) => u.has_lab),
    )!;
    const labUnits = labSubject.units.filter((u) => u.has_lab);
    expect(labUnits.length).toBeGreaterThan(0);

    fireEvent.click(screen.getByRole("button", { name: labSubject.subject }));

    // Each lab unit row renders a FlaskConical svg in the opened panel.
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
    mockUseCurriculumTree.mockReturnValue({
      data: nonLabOnly,
      isLoading: false,
      isError: false,
    });
    const { container } = render(<SubjectsPage />);

    // Was `querySelectorAll("svg")).toHaveLength(0)`, which stood in for "no
    // flask" only while the flask was the ONLY icon on the row. Since #677 every
    // unit also carries a status mark, so the assertion now targets the flask
    // itself rather than counting icons.
    const flasks = container.querySelectorAll(".text-purple-500");
    expect(flasks).toHaveLength(0);
  });
});

// ---------------------------------------------------------------------------
// #677 — which units are done, and getting to them
// ---------------------------------------------------------------------------

describe("#677 — per-unit status and subject deep link", () => {
  beforeEach(() => {
    mockSearchParams.mockReturnValue(new URLSearchParams());
    mockUseUnitStatuses.mockReturnValue({
      statusByUnit: new Map<string, string>(),
      isLoading: false,
    });
  });

  it("marks each unit with the status the server reports", () => {
    const units = MOCK_CURRICULUM_TREE.subjects[0].units;
    mockUseCurriculumTree.mockReturnValue({
      data: MOCK_CURRICULUM_TREE,
      isLoading: false,
      isError: false,
    });
    mockUseUnitStatuses.mockReturnValue({
      statusByUnit: new Map([[units[0].unit_id, "completed"]]),
      isLoading: false,
    });

    render(<SubjectsPage />);
    fireEvent.click(screen.getByRole("button", { name: "Mathematics" }));

    // The mark is icon-only, so its accessible name is what a screen reader
    // and this test both read.
    expect(screen.getAllByText("Completed").length).toBeGreaterThan(0);
  });

  it("a unit the server knows nothing about reads as not started", () => {
    mockUseCurriculumTree.mockReturnValue({
      data: MOCK_CURRICULUM_TREE,
      isLoading: false,
      isError: false,
    });

    render(<SubjectsPage />);
    fireEvent.click(screen.getByRole("button", { name: "Mathematics" }));

    expect(screen.getAllByText("Not started").length).toBeGreaterThan(0);
  });

  it("opens the subject named in the query string", () => {
    // The dashboard's subject card links here; landing on a closed shelf and
    // making the student find the subject again defeats the point (#677).
    mockUseCurriculumTree.mockReturnValue({
      data: MOCK_CURRICULUM_TREE,
      isLoading: false,
      isError: false,
    });
    mockSearchParams.mockReturnValue(new URLSearchParams("subject=Mathematics"));

    render(<SubjectsPage />);

    const units = MOCK_CURRICULUM_TREE.subjects[0].units;
    expect(screen.getByText(units[0].title)).toBeInTheDocument();
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
