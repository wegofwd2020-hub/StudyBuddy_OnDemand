/**
 * Unit tests for section 2.8 — Progress Page (`/progress`)
 * Covers TC-IDs: STU-29, STU-30
 *
 * Run with:
 *   npm test -- progress-page
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import ProgressPage from "@/app/(student)/progress/page";
import {
  MOCK_PROGRESS_HISTORY,
  MOCK_PROGRESS_EMPTY,
  PROGRESS_STRINGS,
  lessonHref,
  quizHref,
} from "../e2e/data/progress-page";

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

const mockUseProgressHistory = vi.fn();
const mockUseCurriculumTree = vi.fn(() => ({ data: undefined }));

// The page joins unit titles from the curriculum tree (#670) — the history
// endpoint returns IDs only. Mocked at the hook so these tests do not need a
// QueryClientProvider; the default (no tree) exercises the unit_id fallback.
vi.mock("@/lib/hooks/useCurriculumTree", () => ({
  useCurriculumTree: () => mockUseCurriculumTree(),
}));

vi.mock("@/lib/hooks/useProgress", () => ({
  useProgressHistory: () => mockUseProgressHistory(),
}));

// ---------------------------------------------------------------------------
// STU-29 — Progress history renders: sessions with scores
// ---------------------------------------------------------------------------

describe("STU-29 — Progress history renders", () => {
  it("renders the page heading", () => {
    mockUseProgressHistory.mockReturnValue({
      data: MOCK_PROGRESS_HISTORY,
      isLoading: false,
    });
    render(<ProgressPage />);
    expect(
      screen.getByRole("heading", { name: PROGRESS_STRINGS.pageHeading }),
    ).toBeInTheDocument();
  });

  it("renders a card for each session", () => {
    mockUseProgressHistory.mockReturnValue({
      data: MOCK_PROGRESS_HISTORY,
      isLoading: false,
    });
    render(<ProgressPage />);
    for (const session of MOCK_PROGRESS_HISTORY.sessions) {
      expect(screen.getByText(session.unit_title)).toBeInTheDocument();
    }
  });

  it("renders the subject for each session", () => {
    mockUseProgressHistory.mockReturnValue({
      data: MOCK_PROGRESS_HISTORY,
      isLoading: false,
    });
    render(<ProgressPage />);
    // Science appears twice — just check both subjects are rendered
    expect(screen.getAllByText(/Science/)).toHaveLength(
      MOCK_PROGRESS_HISTORY.sessions.filter((s) => s.subject === "Science").length,
    );
    expect(screen.getByText(/Mathematics/)).toBeInTheDocument();
  });

  it("renders score as X/Y for sessions with a score", () => {
    mockUseProgressHistory.mockReturnValue({
      data: MOCK_PROGRESS_HISTORY,
      isLoading: false,
    });
    render(<ProgressPage />);
    const withScore = MOCK_PROGRESS_HISTORY.sessions.filter(
      (s) => s.score !== null && s.total !== null,
    );
    for (const session of withScore) {
      // Reads "Score 5/8" inline on the meta line since #670, so the matcher
      // normalises across the label and the number rather than expecting a
      // bare "5/8" node.
      expect(
        screen.getByText(
          (_, el) => el?.textContent === `Score ${session.score}/${session.total}`,
        ),
      ).toBeInTheDocument();
    }
  });

  it("shows the unit title when the curriculum tree has one (#670)", () => {
    const first = MOCK_PROGRESS_HISTORY.sessions[0];
    mockUseProgressHistory.mockReturnValue({
      data: MOCK_PROGRESS_HISTORY,
      isLoading: false,
    });
    // The history endpoint returns unit IDs only; the readable title comes from
    // the tree, so a student sees the unit name rather than "G10-MATH-002".
    mockUseCurriculumTree.mockReturnValue({
      data: {
        curriculum_id: "c1",
        grade: 8,
        subjects: [
          {
            subject: first.subject,
            units: [{ unit_id: first.unit_id, title: "Readable Unit Title" }],
          },
        ],
      },
    });

    render(<ProgressPage />);
    expect(screen.getByText("Readable Unit Title")).toBeInTheDocument();
  });

  it("falls back to the unit id when no title is available (#670)", () => {
    const first = MOCK_PROGRESS_HISTORY.sessions[0];
    mockUseProgressHistory.mockReturnValue({
      data: MOCK_PROGRESS_HISTORY,
      isLoading: false,
    });
    mockUseCurriculumTree.mockReturnValue({ data: undefined });

    render(<ProgressPage />);
    expect(screen.getByText(first.unit_title)).toBeInTheDocument();
  });

  it("renders attempt number for each session", () => {
    mockUseProgressHistory.mockReturnValue({
      data: MOCK_PROGRESS_HISTORY,
      isLoading: false,
    });
    render(<ProgressPage />);
    // Collect all unique attempt numbers and verify each appears at least once
    const attemptNumbers = [
      ...new Set(MOCK_PROGRESS_HISTORY.sessions.map((s) => s.attempt_number)),
    ];
    for (const n of attemptNumbers) {
      expect(screen.getAllByText(new RegExp(`Attempt #${n}`)).length).toBeGreaterThan(0);
    }
  });

  it("passed session renders CheckCircle2 (green svg)", () => {
    mockUseProgressHistory.mockReturnValue({
      data: MOCK_PROGRESS_HISTORY,
      isLoading: false,
    });
    const { container } = render(<ProgressPage />);
    expect(container.querySelector("svg.text-green-500")).toBeTruthy();
  });

  it("failed session renders XCircle (red svg)", () => {
    mockUseProgressHistory.mockReturnValue({
      data: MOCK_PROGRESS_HISTORY,
      isLoading: false,
    });
    const { container } = render(<ProgressPage />);
    expect(container.querySelector("svg.text-red-400")).toBeTruthy();
  });

  it("each session card has a Lesson link with correct href", () => {
    mockUseProgressHistory.mockReturnValue({
      data: MOCK_PROGRESS_HISTORY,
      isLoading: false,
    });
    render(<ProgressPage />);
    for (const session of MOCK_PROGRESS_HISTORY.sessions) {
      const links = screen.getAllByRole("link", { name: PROGRESS_STRINGS.lessonBtn });
      const match = links.find(
        (el) => el.getAttribute("href") === lessonHref(session.unit_id),
      );
      expect(match).toBeTruthy();
    }
  });

  it("each session card has a Retry quiz link with correct href", () => {
    mockUseProgressHistory.mockReturnValue({
      data: MOCK_PROGRESS_HISTORY,
      isLoading: false,
    });
    render(<ProgressPage />);
    for (const session of MOCK_PROGRESS_HISTORY.sessions) {
      const links = screen.getAllByRole("link", { name: PROGRESS_STRINGS.retryQuizBtn });
      const match = links.find(
        (el) => el.getAttribute("href") === quizHref(session.unit_id),
      );
      expect(match).toBeTruthy();
    }
  });

  it("shows loading skeletons while fetching", () => {
    mockUseProgressHistory.mockReturnValue({ data: undefined, isLoading: true });
    const { container } = render(<ProgressPage />);
    expect(container.querySelector("[data-slot='skeleton']")).toBeTruthy();
  });
});

// ---------------------------------------------------------------------------
// STU-30 — Empty state: no sessions
// ---------------------------------------------------------------------------

describe("STU-30 — Empty state when no history", () => {
  it("renders empty state message when sessions list is empty", () => {
    mockUseProgressHistory.mockReturnValue({
      data: MOCK_PROGRESS_EMPTY,
      isLoading: false,
    });
    render(<ProgressPage />);
    expect(screen.getByText(PROGRESS_STRINGS.emptyMessage)).toBeInTheDocument();
  });

  it("renders Browse Subjects link in empty state", () => {
    mockUseProgressHistory.mockReturnValue({
      data: MOCK_PROGRESS_EMPTY,
      isLoading: false,
    });
    render(<ProgressPage />);
    const link = screen.getByRole("link", { name: PROGRESS_STRINGS.browseSubjects });
    expect(link).toBeInTheDocument();
    expect(link.getAttribute("href")).toBe("/subjects");
  });

  it("renders Clock icon (svg) in empty state", () => {
    mockUseProgressHistory.mockReturnValue({
      data: MOCK_PROGRESS_EMPTY,
      isLoading: false,
    });
    const { container } = render(<ProgressPage />);
    expect(container.querySelector("svg")).toBeTruthy();
  });

  it("does not render any session cards in empty state", () => {
    mockUseProgressHistory.mockReturnValue({
      data: MOCK_PROGRESS_EMPTY,
      isLoading: false,
    });
    render(<ProgressPage />);
    expect(screen.queryByText(/Attempt #/)).toBeNull();
  });

  it("empty state string is correct", () => {
    expect(PROGRESS_STRINGS.emptyMessage).toBe(
      "No sessions yet. Start learning to track progress.",
    );
  });
});

// ---------------------------------------------------------------------------
// Href helpers
// ---------------------------------------------------------------------------

describe("Progress page href helpers", () => {
  it("lessonHref returns /lesson/[unit_id]", () => {
    expect(lessonHref("G8-SCI-001")).toBe("/lesson/G8-SCI-001");
  });

  it("quizHref returns /quiz/[unit_id]", () => {
    expect(quizHref("G8-SCI-001")).toBe("/quiz/G8-SCI-001");
  });
});
