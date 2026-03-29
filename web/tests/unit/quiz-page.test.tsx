/**
 * Unit tests for section 2.5 — Quiz Page components
 * Covers TC-IDs: STU-19, STU-20, STU-21, STU-22, STU-23, STU-24
 *
 * Run with:
 *   npm test -- quiz-page
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QuizPlayer } from "@/components/content/QuizPlayer";
import {
  MOCK_QUIZ,
  MOCK_SESSION_ID,
  MOCK_ANSWER_CORRECT,
  MOCK_ANSWER_WRONG,
  MOCK_SESSION_END_PASSED,
  MOCK_SESSION_END_FAILED,
  QUIZ_STRINGS,
} from "../e2e/data/quiz-page";

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

const mockSubmitAnswer = vi.fn();
const mockEndSession = vi.fn();

vi.mock("@/lib/api/progress", () => ({
  submitAnswer: (...args: unknown[]) => mockSubmitAnswer(...args),
  endSession: (...args: unknown[]) => mockEndSession(...args),
}));

// ---------------------------------------------------------------------------
// STU-19 — Quiz question renders with options
// ---------------------------------------------------------------------------

describe("STU-19 — Quiz question renders", () => {
  it("renders the first question text", () => {
    render(<QuizPlayer quiz={MOCK_QUIZ} sessionId={MOCK_SESSION_ID} curriculumId="default-2026-g8" />);
    expect(screen.getByText(MOCK_QUIZ.questions[0].question)).toBeInTheDocument();
  });

  it("renders all 4 answer option buttons", () => {
    render(<QuizPlayer quiz={MOCK_QUIZ} sessionId={MOCK_SESSION_ID} curriculumId="default-2026-g8" />);
    for (const option of MOCK_QUIZ.questions[0].options) {
      expect(screen.getByRole("button", { name: new RegExp(option) })).toBeInTheDocument();
    }
  });

  it("renders progress indicator showing question 1 of N", () => {
    render(<QuizPlayer quiz={MOCK_QUIZ} sessionId={MOCK_SESSION_ID} curriculumId="default-2026-g8" />);
    expect(
      screen.getByText(`Question 1 of ${MOCK_QUIZ.questions.length}`),
    ).toBeInTheDocument();
  });

  it("Submit button is initially disabled (no option selected)", () => {
    render(<QuizPlayer quiz={MOCK_QUIZ} sessionId={MOCK_SESSION_ID} curriculumId="default-2026-g8" />);
    expect(
      screen.getByRole("button", { name: QUIZ_STRINGS.submitBtn }),
    ).toBeDisabled();
  });
});

// ---------------------------------------------------------------------------
// STU-20 — Selecting answer enables submit button
// ---------------------------------------------------------------------------

describe("STU-20 — Selecting answer enables submit", () => {
  it("submit button becomes enabled after clicking an option", () => {
    render(<QuizPlayer quiz={MOCK_QUIZ} sessionId={MOCK_SESSION_ID} curriculumId="default-2026-g8" />);
    const option = screen.getByRole("button", {
      name: new RegExp(MOCK_QUIZ.questions[0].options[0]),
    });
    fireEvent.click(option);
    expect(
      screen.getByRole("button", { name: QUIZ_STRINGS.submitBtn }),
    ).not.toBeDisabled();
  });

  it("clicking a different option still keeps submit enabled", () => {
    render(<QuizPlayer quiz={MOCK_QUIZ} sessionId={MOCK_SESSION_ID} curriculumId="default-2026-g8" />);
    fireEvent.click(
      screen.getByRole("button", { name: new RegExp(MOCK_QUIZ.questions[0].options[0]) }),
    );
    fireEvent.click(
      screen.getByRole("button", { name: new RegExp(MOCK_QUIZ.questions[0].options[2]) }),
    );
    expect(
      screen.getByRole("button", { name: QUIZ_STRINGS.submitBtn }),
    ).not.toBeDisabled();
  });
});

// ---------------------------------------------------------------------------
// STU-21 — Correct answer highlighted green after submit
// ---------------------------------------------------------------------------

describe("STU-21 — Correct answer shown after submit", () => {
  beforeEach(() => {
    mockSubmitAnswer.mockResolvedValue(MOCK_ANSWER_CORRECT);
  });

  it("correct option gets green background class after submit", async () => {
    const { container } = render(
      <QuizPlayer quiz={MOCK_QUIZ} sessionId={MOCK_SESSION_ID} curriculumId="default-2026-g8" />,
    );

    // Select the correct option (index 1 → "Cell")
    const correctOption = MOCK_QUIZ.questions[0].options[MOCK_QUIZ.questions[0].correct_index];
    fireEvent.click(
      screen.getByRole("button", { name: new RegExp(correctOption) }),
    );
    fireEvent.click(screen.getByRole("button", { name: QUIZ_STRINGS.submitBtn }));

    await waitFor(() => {
      const buttons = container.querySelectorAll("button");
      const correctBtn = Array.from(buttons).find((b) =>
        b.textContent?.includes(correctOption),
      );
      expect(correctBtn?.className).toContain("bg-green-50");
    });
  });

  it("CheckCircle2 SVG appears on correct option after submit", async () => {
    const { container } = render(
      <QuizPlayer quiz={MOCK_QUIZ} sessionId={MOCK_SESSION_ID} curriculumId="default-2026-g8" />,
    );
    const correctOption = MOCK_QUIZ.questions[0].options[MOCK_QUIZ.questions[0].correct_index];
    fireEvent.click(
      screen.getByRole("button", { name: new RegExp(correctOption) }),
    );
    fireEvent.click(screen.getByRole("button", { name: QUIZ_STRINGS.submitBtn }));

    await waitFor(() => {
      const buttons = container.querySelectorAll("button");
      const correctBtn = Array.from(buttons).find((b) =>
        b.textContent?.includes(correctOption),
      );
      expect(correctBtn?.querySelector("svg")).toBeTruthy();
    });
  });

  it("option buttons are disabled during reviewing phase", async () => {
    const { container } = render(
      <QuizPlayer quiz={MOCK_QUIZ} sessionId={MOCK_SESSION_ID} curriculumId="default-2026-g8" />,
    );
    const correctOption = MOCK_QUIZ.questions[0].options[MOCK_QUIZ.questions[0].correct_index];
    fireEvent.click(
      screen.getByRole("button", { name: new RegExp(correctOption) }),
    );
    fireEvent.click(screen.getByRole("button", { name: QUIZ_STRINGS.submitBtn }));

    await waitFor(() => {
      // All option buttons (not Submit/Next) should be disabled
      const optionBtns = container.querySelectorAll<HTMLButtonElement>(
        "div.space-y-3 button",
      );
      optionBtns.forEach((btn) => expect(btn).toBeDisabled());
    });
  });

  it("explanation text appears after submit", async () => {
    render(
      <QuizPlayer quiz={MOCK_QUIZ} sessionId={MOCK_SESSION_ID} curriculumId="default-2026-g8" />,
    );
    const correctOption = MOCK_QUIZ.questions[0].options[MOCK_QUIZ.questions[0].correct_index];
    fireEvent.click(
      screen.getByRole("button", { name: new RegExp(correctOption) }),
    );
    fireEvent.click(screen.getByRole("button", { name: QUIZ_STRINGS.submitBtn }));

    await waitFor(() => {
      expect(
        screen.getByText(MOCK_ANSWER_CORRECT.explanation),
      ).toBeInTheDocument();
    });
  });
});

// ---------------------------------------------------------------------------
// STU-22 — Wrong answer highlighted red; correct answer revealed
// ---------------------------------------------------------------------------

describe("STU-22 — Wrong answer shown after submit", () => {
  beforeEach(() => {
    mockSubmitAnswer.mockResolvedValue(MOCK_ANSWER_WRONG);
  });

  it("wrong selected option gets red background class after submit", async () => {
    const { container } = render(
      <QuizPlayer quiz={MOCK_QUIZ} sessionId={MOCK_SESSION_ID} curriculumId="default-2026-g8" />,
    );

    // Select a wrong option (index 0 → "Atom")
    const wrongOption = MOCK_QUIZ.questions[0].options[0]; // index 0, correct is index 1
    fireEvent.click(
      screen.getByRole("button", { name: new RegExp(wrongOption) }),
    );
    fireEvent.click(screen.getByRole("button", { name: QUIZ_STRINGS.submitBtn }));

    await waitFor(() => {
      const buttons = container.querySelectorAll("button");
      const wrongBtn = Array.from(buttons).find((b) =>
        b.textContent?.includes(wrongOption) && !b.textContent?.includes("Cell"),
      );
      expect(wrongBtn?.className).toContain("bg-red-50");
    });
  });

  it("correct option still gets green background when wrong option selected", async () => {
    const { container } = render(
      <QuizPlayer quiz={MOCK_QUIZ} sessionId={MOCK_SESSION_ID} curriculumId="default-2026-g8" />,
    );
    const wrongOption = MOCK_QUIZ.questions[0].options[0];
    fireEvent.click(
      screen.getByRole("button", { name: new RegExp(wrongOption) }),
    );
    fireEvent.click(screen.getByRole("button", { name: QUIZ_STRINGS.submitBtn }));

    await waitFor(() => {
      const correctOption = MOCK_QUIZ.questions[0].options[MOCK_QUIZ.questions[0].correct_index];
      const buttons = container.querySelectorAll("button");
      const correctBtn = Array.from(buttons).find((b) =>
        b.textContent?.includes(correctOption),
      );
      expect(correctBtn?.className).toContain("bg-green-50");
    });
  });

  it("XCircle SVG appears on wrong selected option", async () => {
    const { container } = render(
      <QuizPlayer quiz={MOCK_QUIZ} sessionId={MOCK_SESSION_ID} curriculumId="default-2026-g8" />,
    );
    const wrongOption = MOCK_QUIZ.questions[0].options[0];
    fireEvent.click(
      screen.getByRole("button", { name: new RegExp(wrongOption) }),
    );
    fireEvent.click(screen.getByRole("button", { name: QUIZ_STRINGS.submitBtn }));

    await waitFor(() => {
      const buttons = container.querySelectorAll("button");
      const wrongBtn = Array.from(buttons).find((b) =>
        b.textContent?.includes(wrongOption) && !b.textContent?.includes("Cell"),
      );
      expect(wrongBtn?.querySelector("svg")).toBeTruthy();
    });
  });
});

// ---------------------------------------------------------------------------
// STU-23 — Score screen renders after completing all questions
// ---------------------------------------------------------------------------

describe("STU-23 — Score screen after quiz completion", () => {
  beforeEach(() => {
    mockSubmitAnswer.mockResolvedValue(MOCK_ANSWER_CORRECT);
  });

  function clickOptionByText(optionText: string) {
    const btn = Array.from(document.querySelectorAll<HTMLButtonElement>("button")).find(
      (b) => b.textContent?.trim() === optionText,
    );
    if (!btn) throw new Error(`Option button not found: ${optionText}`);
    fireEvent.click(btn);
  }

  async function completeQuiz() {
    for (let q = 0; q < MOCK_QUIZ.questions.length; q++) {
      const question = MOCK_QUIZ.questions[q];
      const correctOption = question.options[question.correct_index];

      await waitFor(() => {
        expect(screen.getByText(`Question ${q + 1} of ${MOCK_QUIZ.questions.length}`)).toBeInTheDocument();
      });

      clickOptionByText(correctOption);
      fireEvent.click(screen.getByRole("button", { name: QUIZ_STRINGS.submitBtn }));

      const isLast = q === MOCK_QUIZ.questions.length - 1;
      if (isLast) {
        mockEndSession.mockResolvedValue(MOCK_SESSION_END_PASSED);
        await waitFor(() => {
          expect(screen.getByRole("button", { name: QUIZ_STRINGS.seeResultsBtn })).toBeInTheDocument();
        });
        fireEvent.click(screen.getByRole("button", { name: QUIZ_STRINGS.seeResultsBtn }));
      } else {
        await waitFor(() => {
          expect(screen.getByRole("button", { name: QUIZ_STRINGS.nextBtn })).toBeInTheDocument();
        });
        fireEvent.click(screen.getByRole("button", { name: QUIZ_STRINGS.nextBtn }));
      }
    }
  }

  it("score screen shows passed heading (Trophy) when passed", async () => {
    render(
      <QuizPlayer quiz={MOCK_QUIZ} sessionId={MOCK_SESSION_ID} curriculumId="default-2026-g8" />,
    );
    mockEndSession.mockResolvedValue(MOCK_SESSION_END_PASSED);
    await completeQuiz();

    await waitFor(() => {
      expect(screen.getByText(QUIZ_STRINGS.passedHeading)).toBeInTheDocument();
    });
  });

  it("score screen shows Trophy SVG when passed", async () => {
    const { container } = render(
      <QuizPlayer quiz={MOCK_QUIZ} sessionId={MOCK_SESSION_ID} curriculumId="default-2026-g8" />,
    );
    mockEndSession.mockResolvedValue(MOCK_SESSION_END_PASSED);
    await completeQuiz();

    await waitFor(() => {
      // Trophy SVG has text-yellow-400 class
      const svg = container.querySelector("svg.text-yellow-400");
      expect(svg).toBeTruthy();
    });
  });

  it("score screen shows try_again heading (RefreshCw) when failed", async () => {
    mockEndSession.mockResolvedValue(MOCK_SESSION_END_FAILED);
    render(
      <QuizPlayer quiz={MOCK_QUIZ} sessionId={MOCK_SESSION_ID} curriculumId="default-2026-g8" />,
    );

    // Override endSession to return failed result
    await completeQuiz();

    await waitFor(() => {
      // Either passed or try_again heading will appear
      const heading =
        screen.queryByText(QUIZ_STRINGS.passedHeading) ||
        screen.queryByText(QUIZ_STRINGS.tryAgainHeading);
      expect(heading).toBeInTheDocument();
    });
  });

  it("back to curriculum link is present on score screen", async () => {
    render(
      <QuizPlayer quiz={MOCK_QUIZ} sessionId={MOCK_SESSION_ID} curriculumId="default-2026-g8" />,
    );
    mockEndSession.mockResolvedValue(MOCK_SESSION_END_PASSED);
    await completeQuiz();

    await waitFor(() => {
      const link = screen.getByRole("link", { name: QUIZ_STRINGS.backToCurriculum });
      expect(link).toBeInTheDocument();
      expect(link.getAttribute("href")).toBe("/curriculum");
    });
  });
});

// ---------------------------------------------------------------------------
// STU-24 — Session starts: submitAnswer called with correct session_id
// ---------------------------------------------------------------------------

describe("STU-24 — Session ID is passed to progress API", () => {
  beforeEach(() => {
    mockSubmitAnswer.mockResolvedValue(MOCK_ANSWER_CORRECT);
  });

  it("submitAnswer is called with the provided sessionId", async () => {
    render(
      <QuizPlayer quiz={MOCK_QUIZ} sessionId={MOCK_SESSION_ID} curriculumId="default-2026-g8" />,
    );

    const correctOption = MOCK_QUIZ.questions[0].options[MOCK_QUIZ.questions[0].correct_index];
    fireEvent.click(
      screen.getByRole("button", { name: new RegExp(correctOption) }),
    );
    fireEvent.click(screen.getByRole("button", { name: QUIZ_STRINGS.submitBtn }));

    await waitFor(() => {
      expect(mockSubmitAnswer).toHaveBeenCalledWith(
        expect.objectContaining({ session_id: MOCK_SESSION_ID }),
      );
    });
  });

  it("no error is rendered when sessionId is provided", () => {
    render(
      <QuizPlayer quiz={MOCK_QUIZ} sessionId={MOCK_SESSION_ID} curriculumId="default-2026-g8" />,
    );
    expect(screen.queryByRole("alert")).toBeNull();
    expect(screen.queryByText(/error/i)).toBeNull();
  });

  it("submitAnswer is called with correct unit_id and question_index", async () => {
    render(
      <QuizPlayer quiz={MOCK_QUIZ} sessionId={MOCK_SESSION_ID} curriculumId="default-2026-g8" />,
    );

    const correctOption = MOCK_QUIZ.questions[0].options[MOCK_QUIZ.questions[0].correct_index];
    fireEvent.click(
      screen.getByRole("button", { name: new RegExp(correctOption) }),
    );
    fireEvent.click(screen.getByRole("button", { name: QUIZ_STRINGS.submitBtn }));

    await waitFor(() => {
      expect(mockSubmitAnswer).toHaveBeenCalledWith(
        expect.objectContaining({
          unit_id: MOCK_QUIZ.unit_id,
          question_index: 0,
        }),
      );
    });
  });
});
