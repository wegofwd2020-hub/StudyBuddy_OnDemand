/**
 * Unit tests for section 2.5 — Quiz Page (the #532 defer-results flow)
 * Covers TC-IDs: STU-19, STU-20, STU-21, STU-22, STU-23, STU-24
 *
 * The quiz now submits each answer as it is picked but WITHHOLDS the verdict
 * until an end-of-quiz summary. There is no per-question Submit button and no
 * mid-quiz green/red reveal. These tests pin that behaviour.
 *
 * Run with:
 *   npm test -- quiz-page
 *
 * next-intl is mocked to the identity function, so rendered button labels are
 * the i18n KEYS (e.g. "next", "finish"), not the English strings. The
 * quiz_screen keys are referenced directly below; the result_screen constants in
 * QUIZ_STRINGS already hold their keys.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor, within } from "@testing-library/react";
import { QuizPlayer } from "@/components/content/QuizPlayer";
import {
  MOCK_QUIZ,
  MOCK_CORRECT_INDEXES,
  correctOptionText,
  MOCK_SESSION_ID,
  MOCK_ANSWER_CORRECT,
  MOCK_ANSWER_WRONG,
  MOCK_SESSION_END_PASSED,
  MOCK_SESSION_END_FAILED,
  QUIZ_STRINGS,
} from "../e2e/data/quiz-page";

// quiz_screen i18n keys, as rendered under the identity mock below.
const KEY = {
  next: "next",
  finish: "finish",
  summaryHeading: "summary_heading",
  saveError: "save_error",
  confirm: "blank_warning_confirm",
} as const;

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

// QuizPlayer calls useQueryClient().invalidateQueries() after the session ends;
// stub it so the component renders without a QueryClientProvider.
vi.mock("@tanstack/react-query", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@tanstack/react-query")>();
  return {
    ...actual,
    useQueryClient: vi.fn(() => ({ invalidateQueries: vi.fn() })),
  };
});

beforeEach(() => {
  mockSubmitAnswer.mockReset().mockResolvedValue(MOCK_ANSWER_CORRECT);
  mockEndSession.mockReset().mockResolvedValue(MOCK_SESSION_END_PASSED);
});

function renderQuiz() {
  return render(<QuizPlayer quiz={MOCK_QUIZ} sessionId={MOCK_SESSION_ID} />);
}

function optionButton(text: string) {
  return screen.getByRole("button", { name: text });
}

// ---------------------------------------------------------------------------
// STU-19 — Quiz question renders with options
// ---------------------------------------------------------------------------

describe("STU-19 — Quiz question renders", () => {
  it("renders the first question text", () => {
    renderQuiz();
    expect(screen.getByText(MOCK_QUIZ.questions[0].question)).toBeInTheDocument();
  });

  it("renders all answer option buttons", () => {
    renderQuiz();
    for (const option of MOCK_QUIZ.questions[0].options) {
      expect(optionButton(option)).toBeInTheDocument();
    }
  });

  it("renders a question-number row with one entry per question", () => {
    renderQuiz();
    // The jump buttons share the (identity-mocked) aria-label "jump_to_question";
    // there is exactly one per question.
    const jumpButtons = screen.getAllByRole("button", { name: "jump_to_question" });
    expect(jumpButtons).toHaveLength(MOCK_QUIZ.questions.length);
    jumpButtons.forEach((btn, i) => expect(btn).toHaveTextContent(String(i + 1)));
  });

  it("has a Finish button and NO per-question Submit button", () => {
    renderQuiz();
    expect(screen.getByRole("button", { name: KEY.finish })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /submit/i })).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// STU-20 — Selecting an answer highlights it and submits it
// ---------------------------------------------------------------------------

describe("STU-20 — Selecting an answer", () => {
  it("highlights the picked option and submits it (no Submit button needed)", async () => {
    renderQuiz();
    const option = optionButton(MOCK_QUIZ.questions[0].options[0]);
    fireEvent.click(option);

    expect(option.getAttribute("aria-pressed")).toBe("true");
    await waitFor(() =>
      expect(mockSubmitAnswer).toHaveBeenCalledWith(
        expect.objectContaining({ answer_index: 0 }),
      ),
    );
  });

  it("changing the choice moves the highlight and submits again", async () => {
    renderQuiz();
    fireEvent.click(optionButton(MOCK_QUIZ.questions[0].options[0]));
    await waitFor(() => expect(mockSubmitAnswer).toHaveBeenCalledTimes(1));

    fireEvent.click(optionButton(MOCK_QUIZ.questions[0].options[2]));
    expect(
      optionButton(MOCK_QUIZ.questions[0].options[2]).getAttribute("aria-pressed"),
    ).toBe("true");
    expect(
      optionButton(MOCK_QUIZ.questions[0].options[0]).getAttribute("aria-pressed"),
    ).toBe("false");
    await waitFor(() => expect(mockSubmitAnswer).toHaveBeenCalledTimes(2));
  });
});

// ---------------------------------------------------------------------------
// STU-21 / STU-22 — The verdict is WITHHELD until the summary
// ---------------------------------------------------------------------------

describe("STU-21/22 — no mid-quiz verdict", () => {
  it("picking the correct option shows no green highlight and no explanation", async () => {
    const { container } = renderQuiz();
    const correct = correctOptionText(0);
    fireEvent.click(optionButton(correct));

    // Give the (resolved) submit a chance to land — the verdict is cached, not shown.
    await waitFor(() => expect(mockSubmitAnswer).toHaveBeenCalled());
    expect(container.querySelector(".bg-green-50")).toBeNull();
    expect(screen.queryByText(MOCK_ANSWER_CORRECT.explanation)).toBeNull();
  });

  it("picking a wrong option shows no red highlight mid-quiz", async () => {
    mockSubmitAnswer.mockResolvedValue(MOCK_ANSWER_WRONG);
    const { container } = renderQuiz();
    fireEvent.click(optionButton(MOCK_QUIZ.questions[0].options[0]));

    await waitFor(() => expect(mockSubmitAnswer).toHaveBeenCalled());
    expect(container.querySelector(".bg-red-50")).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// STU-23 — End-of-quiz summary
// ---------------------------------------------------------------------------

describe("STU-23 — summary after completion", () => {
  async function answerAllAndFinish() {
    for (let q = 0; q < MOCK_QUIZ.questions.length; q++) {
      await screen.findByText(MOCK_QUIZ.questions[q].question);
      fireEvent.click(optionButton(correctOptionText(q)));
      if (q < MOCK_QUIZ.questions.length - 1) {
        fireEvent.click(screen.getByRole("button", { name: KEY.next }));
      }
    }
    fireEvent.click(screen.getByRole("button", { name: KEY.finish }));
  }

  it("shows the passed heading and Trophy, and reveals the withheld explanation", async () => {
    const { container } = renderQuiz();
    await answerAllAndFinish();

    await waitFor(() =>
      expect(screen.getByText(QUIZ_STRINGS.passedHeading)).toBeInTheDocument(),
    );
    expect(container.querySelector("svg.text-yellow-400")).toBeTruthy();
    // The summary heading and the previously-withheld explanation are now shown.
    expect(screen.getByRole("heading", { name: KEY.summaryHeading })).toBeInTheDocument();
    expect(screen.getAllByText(MOCK_ANSWER_CORRECT.explanation).length).toBeGreaterThan(
      0,
    );
  });

  it("shows the try-again heading when the score does not pass", async () => {
    mockEndSession.mockResolvedValue(MOCK_SESSION_END_FAILED);
    renderQuiz();
    await answerAllAndFinish();

    await waitFor(() =>
      expect(screen.getByText(QUIZ_STRINGS.tryAgainHeading)).toBeInTheDocument(),
    );
  });

  it("offers a back-to-curriculum link on the summary", async () => {
    renderQuiz();
    await answerAllAndFinish();

    await waitFor(() => {
      const link = screen.getByRole("link", { name: QUIZ_STRINGS.backToCurriculum });
      expect(link).toBeInTheDocument();
      expect(link.getAttribute("href")).toBe("/curriculum");
    });
  });
});

// ---------------------------------------------------------------------------
// STU-23b — Finishing with blanks warns before scoring
// ---------------------------------------------------------------------------

describe("STU-23b — blank-answer warning", () => {
  it("finishing with an unanswered question opens a confirmation before ending", async () => {
    renderQuiz();
    // Answer only the first question, leave the rest blank, then Finish.
    fireEvent.click(optionButton(correctOptionText(0)));
    fireEvent.click(screen.getByRole("button", { name: KEY.finish }));

    // A confirmation appears and the session has NOT ended yet.
    const dialog = await screen.findByRole("alertdialog");
    expect(dialog).toBeInTheDocument();
    expect(mockEndSession).not.toHaveBeenCalled();

    // Confirming finishes anyway.
    fireEvent.click(within(dialog).getByRole("button", { name: KEY.confirm }));
    await waitFor(() => expect(mockEndSession).toHaveBeenCalledWith(MOCK_SESSION_ID));
  });
});

// ---------------------------------------------------------------------------
// STU-24 — API wiring
// ---------------------------------------------------------------------------

describe("STU-24 — progress API wiring", () => {
  it("submitAnswer is called with the session id and the content's own question_id", async () => {
    renderQuiz();
    fireEvent.click(optionButton(correctOptionText(0)));

    await waitFor(() =>
      expect(mockSubmitAnswer).toHaveBeenCalledWith(
        expect.objectContaining({
          session_id: MOCK_SESSION_ID,
          question_id: MOCK_QUIZ.questions[0].question_id,
          answer_index: MOCK_CORRECT_INDEXES[0],
        }),
      ),
    );
  });

  it("renders no error initially", () => {
    renderQuiz();
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("surfaces a save error when the answer submission fails", async () => {
    mockSubmitAnswer.mockRejectedValue(new Error("network"));
    renderQuiz();
    fireEvent.click(optionButton(MOCK_QUIZ.questions[0].options[0]));

    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent(KEY.saveError),
    );
  });
});
