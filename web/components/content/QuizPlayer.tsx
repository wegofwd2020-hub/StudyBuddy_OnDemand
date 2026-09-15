"use client";

import { useEffect, useReducer, useRef } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import type { QuizContent, SessionEndResponse } from "@/lib/types/api";
import { Button } from "@/components/ui/button";
import { LinkButton } from "@/components/ui/link-button";
import {
  CheckCircle2,
  XCircle,
  Trophy,
  RefreshCw,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { submitAnswer, endSession, getSessionAnswers } from "@/lib/api/progress";

// ─── State machine ────────────────────────────────────────────────────────────
//
// The quiz no longer grades in front of the student. Every answer is still
// submitted as it is picked (the server keeps its own tally, #532 blocker), but
// the verdict is withheld: the student answers everything at their own pace,
// moving freely between questions, then sees one summary at the end. The cached
// AnswerResponse per question feeds that summary — it is never rendered mid-quiz.

type SaveStatus = "idle" | "saving" | "saved" | "error";

interface QuestionState {
  selectedIndex: number | null;
  /** Server verdict — held back until the summary; also drives the retry-on-error hint. */
  save: SaveStatus;
}

interface State {
  phase: "answering" | "summary";
  current: number;
  questions: QuestionState[];
  /** Blank-warning confirmation is open. */
  confirming: boolean;
  finishing: boolean;
  finishError: boolean;
  result: SessionEndResponse | null;
}

type Action =
  | { type: "GOTO"; index: number }
  | { type: "SELECT"; index: number; choice: number }
  | { type: "SAVED"; index: number }
  | { type: "SAVE_ERROR"; index: number }
  | { type: "OPEN_CONFIRM" }
  | { type: "CLOSE_CONFIRM" }
  | { type: "RESTORE"; byPosition: Map<number, number> }
  | { type: "FINISHING" }
  | { type: "FINISH_ERROR" }
  | { type: "FINISHED"; result: SessionEndResponse };

function patchQuestion(
  state: State,
  index: number,
  patch: Partial<QuestionState>,
): QuestionState[] {
  return state.questions.map((q, i) => (i === index ? { ...q, ...patch } : q));
}

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case "GOTO":
      // Leaving the question dismisses the finish confirmation (#666). It used
      // to stay open, so the screen showed BOTH its "Finish anyway" and the
      // footer's "Finish quiz" — two competing controls at the moment a student
      // is deciding whether to submit. Covers Back, Next and the question
      // number chips, all of which come through here.
      return { ...state, current: action.index, confirming: false };
    case "SELECT":
      return {
        ...state,
        // Answering also dismisses it: the panel states a count of unanswered
        // questions, and that count is wrong the instant one is answered.
        confirming: false,
        // Optimistic: highlight immediately, clear any prior verdict (it is being
        // re-graded), and drop a stale error so the option looks live again.
        questions: patchQuestion(state, action.index, {
          selectedIndex: action.choice,
          save: "saving",
        }),
      };
    case "SAVED":
      return {
        ...state,
        questions: patchQuestion(state, action.index, { save: "saved" }),
      };
    case "SAVE_ERROR":
      return {
        ...state,
        questions: patchQuestion(state, action.index, { save: "error" }),
      };
    case "RESTORE": {
      // Re-seat the options the student had already picked (#667). Selections
      // only — `result` stays null, because the reveal belongs to the summary
      // (#532) and the resume payload carries no verdicts to leak.
      let changed = false;
      const questions = state.questions.map((q, i) => {
        const restored = action.byPosition.get(i);
        if (restored === undefined || q.selectedIndex !== null) return q;
        changed = true;
        return { ...q, selectedIndex: restored, save: "saved" as SaveStatus };
      });
      return changed ? { ...state, questions } : state;
    }
    case "OPEN_CONFIRM":
      return { ...state, confirming: true };
    case "CLOSE_CONFIRM":
      return { ...state, confirming: false };
    case "FINISHING":
      return { ...state, finishing: true, finishError: false, confirming: false };
    case "FINISH_ERROR":
      return { ...state, finishing: false, finishError: true };
    case "FINISHED":
      return { ...state, phase: "summary", finishing: false, result: action.result };
    default:
      return state;
  }
}

// ─── Component ───────────────────────────────────────────────────────────────

interface QuizPlayerProps {
  quiz: QuizContent;
  sessionId: string;
  /** Restart the quiz with a fresh session. The summary "Try Again" button calls
   *  this instead of navigating to the same URL (which did nothing — #459). */
  onRetry?: () => void;
}

export function QuizPlayer({ quiz, sessionId, onRetry }: QuizPlayerProps) {
  const t = useTranslations("result_screen");
  const tq = useTranslations("quiz_screen");
  const queryClient = useQueryClient();

  const [state, dispatch] = useReducer(reducer, {
    phase: "answering",
    current: 0,
    questions: quiz.questions.map(() => ({
      selectedIndex: null,
      save: "idle" as SaveStatus,
    })),
    confirming: false,
    finishing: false,
    finishError: false,
    result: null,
  });

  // Answers are submitted as they are picked; end_session reads the server tally
  // those requests build. Await any still in flight before finishing so the tally
  // reflects the final selections (submitAnswer updates it synchronously).
  const pendingSaves = useRef<Promise<unknown>[]>([]);

  const total = quiz.questions.length;
  const blanks = state.questions.filter((q) => q.selectedIndex === null).length;

  function handleSelect(choice: number) {
    const index = state.current;
    const question = quiz.questions[index];
    // Re-picking the same option is a no-op; the server would just overwrite it.
    if (state.questions[index].selectedIndex === choice) return;

    dispatch({ type: "SELECT", index, choice });
    const p = submitAnswer({
      session_id: sessionId,
      question_id: question.question_id,
      answer_index: choice,
    })
      .then(() => dispatch({ type: "SAVED", index }))
      .catch(() => dispatch({ type: "SAVE_ERROR", index }));
    pendingSaves.current.push(p);
  }

  // Restore prior selections after a refresh (#667). Runs once per session:
  // the server is the record of what was answered, and until this the page came
  // back blank while those answers were safely graded and stored.
  useEffect(() => {
    let cancelled = false;
    getSessionAnswers(sessionId)
      .then((answers) => {
        if (cancelled || answers.length === 0) return;
        const positionOf = new Map(quiz.questions.map((q, i) => [q.question_id, i]));
        const byPosition = new Map<number, number>();
        for (const a of answers) {
          const i = positionOf.get(a.question_id);
          if (i !== undefined) byPosition.set(i, a.answer_index);
        }
        if (byPosition.size > 0) dispatch({ type: "RESTORE", byPosition });
      })
      // A failure here costs the student their highlighted options, not their
      // answers — the score is server-side either way, so it must not block the
      // quiz or raise an error at them.
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [sessionId, quiz.questions]);

  async function doFinish() {
    dispatch({ type: "FINISHING" });
    try {
      // Let every in-flight answer land so the tally is complete before we read it.
      await Promise.allSettled(pendingSaves.current);
      const result = await endSession(sessionId);
      // Completion is written synchronously, so stats/history reads are fresh —
      // refresh them now rather than waiting for a manual reload (#466).
      queryClient.invalidateQueries({ queryKey: ["stats"] });
      queryClient.invalidateQueries({ queryKey: ["progress"] });
      dispatch({ type: "FINISHED", result });
    } catch {
      dispatch({ type: "FINISH_ERROR" });
    }
  }

  function handleFinish() {
    if (state.finishing) return;
    if (blanks > 0) {
      dispatch({ type: "OPEN_CONFIRM" });
      return;
    }
    void doFinish();
  }

  // ── Summary screen ──────────────────────────────────────────────────────────
  if (state.phase === "summary" && state.result) {
    const { score: rawScore, total: rawTotal, passed, attempt_number } = state.result;
    const revealByQuestion = new Map(
      (state.result.reveal ?? []).map((r) => [r.question_id, r]),
    );
    // Defensive clamp: never render an impossible result (e.g. 8/5 = 160%).
    const totalQ = rawTotal > 0 ? rawTotal : 1;
    const score = Math.max(0, Math.min(rawScore, totalQ));
    const pct = Math.round((score / totalQ) * 100);

    return (
      <div className="space-y-6 py-2">
        {/* Score header */}
        <div className="space-y-3 py-4 text-center">
          <div className="flex justify-center">
            {passed ? (
              <Trophy className="h-16 w-16 text-yellow-400" />
            ) : (
              <RefreshCw className="h-16 w-16 text-gray-400" />
            )}
          </div>
          <h2 className="text-2xl font-bold text-gray-900">
            {passed ? t("passed_heading") : t("try_again_heading")}
          </h2>
          {quiz.subject && (
            <p className="text-xs font-medium tracking-wide text-gray-400 uppercase">
              {quiz.subject}
            </p>
          )}
          <p className="text-gray-500">
            {t("score_label", { score, total: totalQ, pct })}
          </p>
          <p className="text-sm text-gray-400">
            {t("attempt_label", { attempt: attempt_number })}
          </p>
        </div>

        {/* Per-question review */}
        <h3 className="text-sm font-semibold tracking-wide text-gray-500 uppercase">
          {tq("summary_heading")}
        </h3>
        <ol className="space-y-4">
          {quiz.questions.map((question, qi) => {
            const { selectedIndex } = state.questions[qi];
            const answered = selectedIndex !== null;
            // The key comes with the SUMMARY now, not with each answer (#684).
            // Returning it per answer let a student read the right option and
            // re-answer for a perfect score, since re-answering overwrites the
            // verdict.
            const revealed = revealByQuestion.get(question.question_id);
            const correctIndex = revealed?.correct_index ?? null;

            return (
              <li
                key={question.question_id}
                className="rounded-lg border bg-white p-4 shadow-sm"
              >
                <p className="mb-3 font-medium text-gray-900">
                  <span className="text-gray-400">{qi + 1}. </span>
                  {question.question}
                </p>
                <ul className="space-y-2">
                  {question.options.map((option, oi) => {
                    const isChosen = selectedIndex === oi;
                    const isCorrect = correctIndex === oi;
                    return (
                      <li
                        key={oi}
                        className={cn(
                          "flex items-center gap-2 rounded-md border px-3 py-2 text-sm",
                          isCorrect
                            ? "border-green-500 bg-green-50 text-green-800"
                            : isChosen
                              ? "border-red-500 bg-red-50 text-red-800"
                              : "border-gray-100 text-gray-600",
                        )}
                      >
                        {isCorrect ? (
                          <CheckCircle2 className="h-4 w-4 shrink-0 text-green-600" />
                        ) : isChosen ? (
                          <XCircle className="h-4 w-4 shrink-0 text-red-500" />
                        ) : (
                          <span className="h-4 w-4 shrink-0" />
                        )}
                        <span>{option}</span>
                        {isChosen && (
                          <span className="ml-auto text-xs font-medium text-gray-400">
                            {tq("your_answer")}
                          </span>
                        )}
                      </li>
                    );
                  })}
                </ul>
                {!answered && (
                  <p className="mt-2 text-xs font-medium text-amber-600">
                    {tq("not_answered")}
                  </p>
                )}
                {revealed?.explanation && (
                  <div className="mt-3 rounded-md border bg-gray-50 p-3 text-sm text-gray-600">
                    {revealed.explanation}
                  </div>
                )}
              </li>
            );
          })}
        </ol>

        <div className="flex justify-center gap-3 pt-2">
          {!passed && onRetry && (
            <Button variant="outline" onClick={onRetry}>
              {t("try_again_btn")}
            </Button>
          )}
          <LinkButton href="/curriculum">{t("back_to_curriculum_btn")}</LinkButton>
        </div>
      </div>
    );
  }

  // ── Answering screen ────────────────────────────────────────────────────────
  const question = quiz.questions[state.current];
  const currentState = state.questions[state.current];
  const isFirst = state.current === 0;
  const isLast = state.current === total - 1;

  return (
    <div className="space-y-6">
      {/* Question-number row: answered / current / blank, tappable to jump */}
      <div className="flex flex-wrap items-center gap-1.5">
        {quiz.questions.map((_, i) => {
          const answered = state.questions[i].selectedIndex !== null;
          const isCurrent = i === state.current;
          return (
            <button
              key={i}
              type="button"
              onClick={() => dispatch({ type: "GOTO", index: i })}
              aria-label={tq("jump_to_question", { n: i + 1 })}
              aria-current={isCurrent ? "step" : undefined}
              className={cn(
                "h-8 w-8 rounded-full border text-xs font-semibold transition-colors",
                "focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500",
                isCurrent
                  ? "border-blue-500 bg-blue-500 text-white"
                  : answered
                    ? "border-blue-300 bg-blue-50 text-blue-700"
                    : "border-gray-200 bg-white text-gray-400 hover:bg-gray-50",
              )}
            >
              {i + 1}
            </button>
          );
        })}
      </div>

      <p className="text-sm text-gray-500">
        {tq("question_progress", { current: state.current + 1, total })}
      </p>

      {/* Question */}
      <div className="rounded-lg border bg-white p-6 shadow-sm">
        <p className="mb-6 text-lg font-medium text-gray-900">{question.question}</p>

        <div className="space-y-3">
          {question.options.map((option, i) => {
            const isSelected = currentState.selectedIndex === i;
            // No verdict mid-quiz: the only state shown is which option is picked.
            return (
              <button
                key={i}
                type="button"
                onClick={() => handleSelect(i)}
                aria-pressed={isSelected}
                className={cn(
                  "w-full rounded-lg border px-4 py-3 text-left text-sm font-medium transition-colors",
                  "focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500",
                  isSelected
                    ? "border-blue-500 bg-blue-50 text-blue-800"
                    : "border-border bg-background hover:bg-gray-50",
                )}
              >
                {option}
              </button>
            );
          })}
        </div>

        {/* Answer failed to save. Plain language, no status codes or ids — this is
            student-facing (Content Rule #5). Re-tapping the option retries. */}
        {currentState.save === "error" && (
          <p role="alert" className="mt-4 text-sm text-red-600">
            {tq("save_error")}
          </p>
        )}
      </div>

      {/* Blank-warning confirmation */}
      {state.confirming && (
        <div
          role="alertdialog"
          aria-labelledby="quiz-confirm-title"
          aria-describedby="quiz-confirm-body"
          className="rounded-lg border border-amber-300 bg-amber-50 p-4"
        >
          <p id="quiz-confirm-title" className="font-medium text-amber-900">
            {tq("blank_warning_title")}
          </p>
          <p id="quiz-confirm-body" className="mt-1 text-sm text-amber-800">
            {tq("blank_warning_body", { count: blanks })}
          </p>
          <div className="mt-3 flex justify-end gap-2">
            <Button variant="outline" onClick={() => dispatch({ type: "CLOSE_CONFIRM" })}>
              {tq("blank_warning_cancel")}
            </Button>
            <Button onClick={() => void doFinish()} disabled={state.finishing}>
              {tq("blank_warning_confirm")}
            </Button>
          </div>
        </div>
      )}

      {state.finishError && (
        <p role="alert" className="text-sm text-red-600">
          {tq("finish_error")}
        </p>
      )}

      {/* Navigation + finish */}
      <div className="flex items-center justify-between">
        <Button
          variant="outline"
          onClick={() => dispatch({ type: "GOTO", index: state.current - 1 })}
          disabled={isFirst}
        >
          <ChevronLeft className="h-4 w-4" />
          {tq("back")}
        </Button>

        <div className="flex gap-2">
          {!isLast && (
            <Button
              variant="outline"
              onClick={() => dispatch({ type: "GOTO", index: state.current + 1 })}
            >
              {tq("next")}
              <ChevronRight className="h-4 w-4" />
            </Button>
          )}
          <Button onClick={handleFinish} disabled={state.finishing}>
            {state.finishing ? tq("finishing") : tq("finish")}
          </Button>
        </div>
      </div>
    </div>
  );
}
