/**
 * Unit tests for QuizPlayer scoring (#504, #506) under the #532 defer-results flow.
 *
 * The contract these pin: scoring is the SERVER's job. The quiz payload never
 * ships the answer key; the player sends only the picked option and renders the
 * score the server reports at the end — it never counts locally (which is also
 * why the old local double-count that caused #460 can't recur: there is no local
 * tally to inflate). The per-answer reveal is withheld until the summary.
 *
 * Run with:
 *   npm test -- quiz-player-scoring
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor, within } from "@testing-library/react";
import { QuizPlayer } from "@/components/content/QuizPlayer";
import type { QuizContent } from "@/lib/types/api";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

const mockSubmitAnswer = vi.fn();
const mockEndSession = vi.fn();
// #667: the player asks the server which options were already picked, so a
// refresh restores them. Defaults to "nothing answered yet".
const mockGetSessionAnswers = vi.fn(
  async () => [] as { question_id: string; answer_index: number }[],
);

vi.mock("@/lib/api/progress", () => ({
  submitAnswer: (...args: unknown[]) => mockSubmitAnswer(...args),
  endSession: (...args: unknown[]) => mockEndSession(...args),
  getSessionAnswers: (...args: unknown[]) => mockGetSessionAnswers(...args),
}));

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string, vals?: Record<string, unknown>) =>
    vals ? `${key}:${JSON.stringify(vals)}` : key,
}));

vi.mock("@tanstack/react-query", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@tanstack/react-query")>();
  return { ...actual, useQueryClient: () => ({ invalidateQueries: vi.fn() }) };
});

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

/**
 * 5 questions. Note there is NO correct_index here — the browser is not given the
 * answer key. The server decides; option 0 is "Right" only by the mock's grading.
 */
const QUIZ: QuizContent = {
  unit_id: "G8-SCI-001",
  title: "Quiz — Set 1",
  pass_threshold: 3,
  subject: "Science",
  questions: Array.from({ length: 5 }, (_, i) => ({
    index: i,
    question_id: `q${i + 1}`,
    question: `Question ${i + 1}?`,
    options: ["Right", "Wrong A", "Wrong B", "Wrong C"],
  })),
};

const CORRECT = 0;
const WRONG = 1;

/** Server-side grading, simulated: option 0 is the correct one. */
const SERVER_CORRECT_INDEX = 0;

// #532 flow: pick an option (it submits in the background, no Submit button),
// move with "Next", and "Finish" at the end. Labels are the i18n keys under the
// mock above.
async function playQuiz(answers: number[]) {
  for (let i = 0; i < answers.length; i++) {
    const isLast = i === answers.length - 1;
    fireEvent.click(await screen.findByText(QUIZ.questions[i].options[answers[i]]));
    if (!isLast) fireEvent.click(screen.getByRole("button", { name: "next" }));
  }
  fireEvent.click(screen.getByRole("button", { name: "finish" }));
}

// ---------------------------------------------------------------------------

describe("QuizPlayer", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // The server grades and returns the verdict + the reveal.
    mockSubmitAnswer.mockImplementation(async ({ answer_index }) => ({
      correct: answer_index === SERVER_CORRECT_INDEX,
      correct_index: SERVER_CORRECT_INDEX,
      explanation: "Because that is the right one.",
    }));
    mockEndSession.mockResolvedValue({
      score: 3,
      total: 5,
      passed: true,
      attempt_number: 1,
      // The key travels with the SUMMARY since #684 — the answer response is a
      // bare acknowledgement, so this is where the reveal has to come from.
      reveal: QUIZ.questions.map((q) => ({
        question_id: q.question_id,
        correct_index: SERVER_CORRECT_INDEX,
        explanation: "Because that is the right one.",
        your_answer: null,
        correct: false,
      })),
    });
  });

  describe("server-side grading contract", () => {
    it("submits only the picked option — never a correctness claim", async () => {
      render(<QuizPlayer quiz={QUIZ} sessionId="s1" />);
      await playQuiz([CORRECT, WRONG, WRONG, CORRECT, CORRECT]);

      const firstCall = mockSubmitAnswer.mock.calls[0][0];
      expect(firstCall).toEqual({
        session_id: "s1",
        question_id: "q1", // the content's own id, not a synthesised one
        answer_index: 0,
      });
      // The client must not be asserting correctness or shipping the key back.
      expect(firstCall).not.toHaveProperty("correct");
      expect(firstCall).not.toHaveProperty("correct_index");
    });

    it("ends the session without sending a score", async () => {
      render(<QuizPlayer quiz={QUIZ} sessionId="s1" />);
      await playQuiz([CORRECT, WRONG, WRONG, CORRECT, CORRECT]);

      await waitFor(() => expect(mockEndSession).toHaveBeenCalledTimes(1));
      expect(mockEndSession).toHaveBeenCalledWith("s1");
    });

    it("renders the score the SERVER reports, not a locally counted one", async () => {
      // Server says 2/5 even though the player locally saw 3 correct. The server wins.
      mockEndSession.mockResolvedValue({
        score: 2,
        total: 5,
        passed: false,
        attempt_number: 1,
      });

      render(<QuizPlayer quiz={QUIZ} sessionId="s1" />);
      await playQuiz([CORRECT, WRONG, WRONG, CORRECT, CORRECT]);

      expect(await screen.findByText(/"score":2/)).toBeTruthy();
    });
  });

  describe("reveal comes from the server response", () => {
    it("shows the explanation (from the server) on the end-of-quiz summary, not mid-quiz", async () => {
      render(<QuizPlayer quiz={QUIZ} sessionId="s1" />);

      // Answer one question; the verdict/explanation must NOT appear yet.
      fireEvent.click(await screen.findByText("Wrong A"));
      await waitFor(() => expect(mockSubmitAnswer).toHaveBeenCalled());
      expect(screen.queryByText("Because that is the right one.")).toBeNull();

      // Finish (with the rest blank → confirm), then the summary reveals it.
      fireEvent.click(screen.getByRole("button", { name: "finish" }));
      const dialog = await screen.findByRole("alertdialog");
      fireEvent.click(
        within(dialog).getByRole("button", { name: "blank_warning_confirm" }),
      );

      expect(
        (await screen.findAllByText("Because that is the right one.")).length,
      ).toBeGreaterThan(0);
    });
  });
});

// ---------------------------------------------------------------------------
// #666 — the finish confirmation must not outlive the question it was raised on
// ---------------------------------------------------------------------------

describe("QuizPlayer — finish confirmation dismissal (#666)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockSubmitAnswer.mockResolvedValue({
      correct: true,
      correct_index: SERVER_CORRECT_INDEX,
      explanation: "",
    });
  });

  /** Jump to the last question and raise the blank-answers confirmation. */
  function openConfirmOnLastQuestion() {
    render(<QuizPlayer quiz={QUIZ} sessionId="s1" />);
    for (let i = 0; i < QUIZ.questions.length - 1; i++) {
      fireEvent.click(screen.getByRole("button", { name: "next" }));
    }
    fireEvent.click(screen.getByRole("button", { name: "finish" }));
    return screen.getByRole("alertdialog");
  }

  it("raises the confirmation when questions are unanswered", () => {
    expect(openConfirmOnLastQuestion()).toBeInTheDocument();
  });

  it("dismisses it when the student goes Back", () => {
    // Venki, 2026-08-28: the panel stayed, so the screen showed both its
    // "Finish anyway" and the footer's "Finish quiz" — two competing controls
    // at the moment a student decides whether to submit.
    openConfirmOnLastQuestion();
    fireEvent.click(screen.getByRole("button", { name: "back" }));

    expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument();
  });

  it("leaves exactly one finish control after going Back", () => {
    // The defect as seen, rather than via the dialog role.
    openConfirmOnLastQuestion();
    fireEvent.click(screen.getByRole("button", { name: "back" }));

    expect(
      screen.queryAllByRole("button", { name: "blank_warning_confirm" }),
    ).toHaveLength(0);
    expect(screen.getAllByRole("button", { name: "finish" })).toHaveLength(1);
  });

  it("dismisses it when the student answers instead", () => {
    // The panel states a count of unanswered questions, and that count is wrong
    // the instant one is answered.
    openConfirmOnLastQuestion();
    fireEvent.click(screen.getByText(QUIZ.questions[4].options[CORRECT]));

    expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// #667 — a refresh restores the options already picked
// ---------------------------------------------------------------------------

describe("QuizPlayer — resuming after a refresh (#667)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockSubmitAnswer.mockResolvedValue({
      correct: true,
      correct_index: SERVER_CORRECT_INDEX,
      explanation: "",
    });
  });

  it("re-seats the option the student had already picked", async () => {
    // Venki, 2026-08-28: after a refresh the page came back blank, so a student
    // re-answered questions they had already done, unable to tell which.
    mockGetSessionAnswers.mockResolvedValue([{ question_id: "q1", answer_index: WRONG }]);

    render(<QuizPlayer quiz={QUIZ} sessionId="s1" />);

    const picked = await screen.findByRole("button", {
      name: new RegExp(QUIZ.questions[0].options[WRONG]),
      pressed: true,
    });
    expect(picked).toBeInTheDocument();
  });

  it("does not reveal whether the restored answer was right", async () => {
    // The reveal belongs to the summary (#532). A resume must not become a way
    // around it — the payload carries no verdict, and none is rendered.
    mockGetSessionAnswers.mockResolvedValue([{ question_id: "q1", answer_index: WRONG }]);

    render(<QuizPlayer quiz={QUIZ} sessionId="s1" />);
    await screen.findByRole("button", {
      name: new RegExp(QUIZ.questions[0].options[WRONG]),
      pressed: true,
    });

    expect(screen.queryByText(/Because that is the right one/)).not.toBeInTheDocument();
  });

  it("leaves the quiz untouched when nothing was answered yet", async () => {
    mockGetSessionAnswers.mockResolvedValue([]);

    render(<QuizPlayer quiz={QUIZ} sessionId="s1" />);
    await waitFor(() => expect(mockGetSessionAnswers).toHaveBeenCalled());

    expect(screen.queryByRole("button", { pressed: true })).not.toBeInTheDocument();
  });

  it("still lets the student take the quiz if the restore call fails", async () => {
    // Losing the highlights costs nothing that matters — the answers are
    // server-side — so a failure must not block the quiz or surface an error.
    mockGetSessionAnswers.mockRejectedValue(new Error("network"));

    render(<QuizPlayer quiz={QUIZ} sessionId="s1" />);

    fireEvent.click(await screen.findByText(QUIZ.questions[0].options[CORRECT]));
    await waitFor(() => expect(mockSubmitAnswer).toHaveBeenCalled());
  });
});
