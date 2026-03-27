"use client";

import { useReducer } from "react";
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
  | { type: "REVIEWED"; result: AnswerResponse; correct: boolean }
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
        correctCount: action.correct ? state.correctCount + 1 : state.correctCount,
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
}

export function QuizPlayer({ quiz, sessionId }: QuizPlayerProps) {
  const t = useTranslations("result_screen");
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
    const res = await submitAnswer({
      session_id: sessionId,
      unit_id: quiz.unit_id,
      question_index: state.questionIndex,
      answer_index: state.selectedIndex,
    });
    const correct = state.selectedIndex === question.correct_index;
    dispatch({ type: "REVIEWED", result: res, correct });
  }

  async function handleNext() {
    if (isLast) {
      const total = quiz.questions.length;
      const score = state.correctCount + (state.answerResult?.correct ? 1 : 0);
      const res = await endSession(sessionId, score, total);
      dispatch({ type: "SCORE", result: res });
    } else {
      dispatch({ type: "NEXT" });
    }
  }

  // Score screen
  if (state.phase === "scoring" && state.result) {
    const { score, total, passed, attempt_number } = state.result;
    const pct = Math.round((score / total) * 100);
    return (
      <div className="text-center space-y-6 py-8">
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
        <p className="text-gray-500">{t("score_label", { score, total, pct })}</p>
        <p className="text-sm text-gray-400">{t("attempt_label", { attempt: attempt_number })}</p>
        <div className="flex justify-center gap-3">
          {!passed && (
            <LinkButton variant="outline" href={`/quiz/${quiz.unit_id}`}>
              {t("try_again_btn")}
            </LinkButton>
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
        <p className="text-lg font-medium text-gray-900 mb-6">{question.question}</p>

        <div className="space-y-3">
          {question.options.map((option, i) => {
            const isSelected = state.selectedIndex === i;
            const isCorrect = i === question.correct_index;
            const reviewed = state.phase === "reviewing";

            let variant = "outline";
            let extra = "";
            if (reviewed && isCorrect) extra = "border-green-500 bg-green-50 text-green-800";
            else if (reviewed && isSelected && !isCorrect)
              extra = "border-red-500 bg-red-50 text-red-800";
            else if (isSelected) extra = "border-blue-500 bg-blue-50 text-blue-800";

            return (
              <button
                key={i}
                disabled={reviewed}
                onClick={() => dispatch({ type: "SELECT", index: i })}
                className={cn(
                  "w-full text-left rounded-lg border px-4 py-3 text-sm font-medium transition-colors",
                  "focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500",
                  extra || (isSelected ? "" : "hover:bg-gray-50"),
                  variant,
                )}
              >
                <span className="flex items-center gap-2">
                  {reviewed && isCorrect && <CheckCircle2 className="h-4 w-4 text-green-600" />}
                  {reviewed && isSelected && !isCorrect && (
                    <XCircle className="h-4 w-4 text-red-500" />
                  )}
                  {option}
                </span>
              </button>
            );
          })}
        </div>

        {/* Explanation */}
        {state.phase === "reviewing" && state.answerResult && (
          <div className="mt-4 rounded-lg bg-gray-50 border p-3 text-sm text-gray-600">
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
