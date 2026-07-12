"use client";

import { useReducer } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import type { QuizContent, AnswerResponse, SessionEndResponse } from "@/lib/types/api";
import { Button } from "@/components/ui/button";
import { LinkButton } from "@/components/ui/link-button";
import { CheckCircle2, XCircle, Trophy, RefreshCw } from "lucide-react";
import { cn } from "@/lib/utils";
import { submitAnswer, endSession } from "@/lib/api/progress";

// ─── State machine ────────────────────────────────────────────────────────────

type Phase = "answering" | "reviewing" | "scoring";

interface State {
  phase: Phase;
  questionIndex: number;
  selectedIndex: number | null;
  answerResult: AnswerResponse | null;
  correctCount: number;
  result: SessionEndResponse | null;
}

type Action =
  | { type: "SELECT"; index: number }
  | { type: "REVIEWED"; result: AnswerResponse }
  | { type: "NEXT" }
  | { type: "SCORE"; result: SessionEndResponse };

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case "SELECT":
      return { ...state, selectedIndex: action.index };
    case "REVIEWED":
      return {
        ...state,
        phase: "reviewing",
        answerResult: action.result,
        // Local tally is for display only. The score on the result screen is the
        // server's — it grades each answer and keeps its own count.
        correctCount: action.result.correct ? state.correctCount + 1 : state.correctCount,
      };
    case "NEXT":
      return {
        ...state,
        phase: "answering",
        questionIndex: state.questionIndex + 1,
        selectedIndex: null,
        answerResult: null,
      };
    case "SCORE":
      return { ...state, phase: "scoring", result: action.result };
    default:
      return state;
  }
}

// ─── Component ───────────────────────────────────────────────────────────────

interface QuizPlayerProps {
  quiz: QuizContent;
  sessionId: string;
  curriculumId: string;
  /** Restart the quiz with a fresh session. The score screen "Try Again" button
   *  calls this instead of navigating to the same URL (which did nothing — #459). */
  onRetry?: () => void;
}

export function QuizPlayer({ quiz, sessionId, onRetry }: QuizPlayerProps) {
  const t = useTranslations("result_screen");
  const queryClient = useQueryClient();
  const [state, dispatch] = useReducer(reducer, {
    phase: "answering",
    questionIndex: 0,
    selectedIndex: null,
    answerResult: null,
    correctCount: 0,
    result: null,
  });

  const question = quiz.questions[state.questionIndex];
  const isLast = state.questionIndex === quiz.questions.length - 1;

  async function handleSubmit() {
    if (state.selectedIndex === null) return;
    // The server grades this. We send the choice; it returns the verdict, the
    // correct option and the explanation — none of which we had beforehand.
    const res = await submitAnswer({
      session_id: sessionId,
      question_id: question.question_id,
      answer_index: state.selectedIndex,
    });
    dispatch({ type: "REVIEWED", result: res });
  }

  async function handleNext() {
    if (isLast) {
      // No score is sent: the backend reports what it graded during the session.
      const res = await endSession(sessionId);
      // Session completion is written synchronously by endSession, so the
      // stats/history reads are fresh — refresh them now instead of waiting for
      // a manual browser reload (#466).
      queryClient.invalidateQueries({ queryKey: ["stats"] });
      queryClient.invalidateQueries({ queryKey: ["progress"] });
      dispatch({ type: "SCORE", result: res });
    } else {
      dispatch({ type: "NEXT" });
    }
  }

  // Score screen
  if (state.phase === "scoring" && state.result) {
    const { score: rawScore, total: rawTotal, passed, attempt_number } = state.result;
    // Defensive clamp: never render an impossible result (e.g. 8/5 = 160%).
    // The backend also clamps on write — this guards any legacy/stale data too.
    const total = rawTotal > 0 ? rawTotal : 1;
    const score = Math.max(0, Math.min(rawScore, total));
    const pct = Math.round((score / total) * 100);
    return (
      <div className="space-y-6 py-8 text-center">
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
        <p className="text-gray-500">{t("score_label", { score, total, pct })}</p>
        <p className="text-sm text-gray-400">
          {t("attempt_label", { attempt: attempt_number })}
        </p>
        <div className="flex justify-center gap-3">
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

  // Question screen
  return (
    <div className="space-y-6">
      {/* Progress */}
      <div className="flex items-center justify-between text-sm text-gray-500">
        <span>
          Question {state.questionIndex + 1} of {quiz.questions.length}
        </span>
        <div className="flex gap-1">
          {quiz.questions.map((_, i) => (
            <div
              key={i}
              className={cn(
                "h-1.5 w-6 rounded-full",
                i < state.questionIndex
                  ? "bg-blue-500"
                  : i === state.questionIndex
                    ? "bg-blue-300"
                    : "bg-gray-100",
              )}
            />
          ))}
        </div>
      </div>

      {/* Question */}
      <div className="rounded-lg border bg-white p-6 shadow-sm">
        <p className="mb-6 text-lg font-medium text-gray-900">{question.question}</p>

        <div className="space-y-3">
          {question.options.map((option, i) => {
            const isSelected = state.selectedIndex === i;
            const reviewed = state.phase === "reviewing";
            // Which option is right is only known once the server has told us —
            // it isn't in the quiz payload.
            const isCorrect = reviewed && i === state.answerResult?.correct_index;

            const variant = "outline";
            let extra = "";
            if (reviewed && isCorrect)
              extra = "border-green-500 bg-green-50 text-green-800";
            else if (reviewed && isSelected && !isCorrect)
              extra = "border-red-500 bg-red-50 text-red-800";
            else if (isSelected) extra = "border-blue-500 bg-blue-50 text-blue-800";

            return (
              <button
                key={i}
                disabled={reviewed}
                onClick={() => dispatch({ type: "SELECT", index: i })}
                className={cn(
                  "w-full rounded-lg border px-4 py-3 text-left text-sm font-medium transition-colors",
                  "focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500",
                  extra || (isSelected ? "" : "hover:bg-gray-50"),
                  variant,
                )}
              >
                <span className="flex items-center gap-2">
                  {reviewed && isCorrect && (
                    <CheckCircle2 className="h-4 w-4 text-green-600" />
                  )}
                  {reviewed && isSelected && !isCorrect && (
                    <XCircle className="h-4 w-4 text-red-500" />
                  )}
                  {option}
                </span>
              </button>
            );
          })}
        </div>

        {/* Explanation — supplied by the server with the verdict */}
        {state.phase === "reviewing" && state.answerResult?.explanation && (
          <div className="mt-4 rounded-lg border bg-gray-50 p-3 text-sm text-gray-600">
            {state.answerResult.explanation}
          </div>
        )}
      </div>

      {/* Action button */}
      <div className="flex justify-end">
        {state.phase === "answering" ? (
          <Button onClick={handleSubmit} disabled={state.selectedIndex === null}>
            Submit answer
          </Button>
        ) : (
          <Button onClick={handleNext}>{isLast ? "See results" : "Next question"}</Button>
        )}
      </div>
    </div>
  );
}
