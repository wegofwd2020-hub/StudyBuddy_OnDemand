"use client";

import { useState, useEffect, useRef } from "react";
import { Play, Pause, RotateCcw, CheckCircle2, XCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import type { QuizQuestion } from "@/components/demos/scenario/types";

// ─── Types ────────────────────────────────────────────────────────────────────

interface Character {
  id: string;
  name: string;
  org?: string;
  role_label: string;
}

interface DialogTurn {
  speaker: string;
  text: string;
}

interface LegacyQuiz {
  question: string;
  format: "true_false" | "multiple_choice" | "single_choice";
  correct_answer: boolean | string | string[];
  explanation: string;
  options?: { id: string; text: string }[];
}

export interface ScenarioData {
  scenario_id: string;
  title: string;
  domain: string;
  content_source?: string;
  characters: Character[];
  dialog: DialogTurn[];
  quiz?: LegacyQuiz;
  quiz_questions?: QuizQuestion[];
}

interface ScenarioPlayerProps {
  scenario: ScenarioData;
  autoPlayDelayMs?: number;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function initials(name: string): string {
  return name
    .split(" ")
    .map((w) => w[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
}

const AVATAR_COLORS = ["bg-blue-500", "bg-emerald-500", "bg-violet-500", "bg-amber-500"];

function isCorrectAnswer(q: QuizQuestion, answer: boolean | string | string[]): boolean {
  if (q.format === "true_false") return answer === q.correct_answer;
  if (q.format === "single_choice") return answer === q.correct_answer;
  const given = [...(answer as string[])].sort();
  const expected = [...(q.correct_answer as string[])].sort();
  return given.length === expected.length && given.every((v, i) => v === expected[i]);
}

// ─── Component ────────────────────────────────────────────────────────────────

type Phase = "dialog" | "quiz" | "result";

export function ScenarioPlayer({
  scenario,
  autoPlayDelayMs = 2500,
}: ScenarioPlayerProps) {
  const [visibleCount, setVisibleCount] = useState(0);
  const [paused, setPaused] = useState(false);
  const [phase, setPhase] = useState<Phase>("dialog");
  const [quizMounted, setQuizMounted] = useState(false);
  const [quizIdx, setQuizIdx] = useState(0);
  const [answers, setAnswers] = useState<Map<number, boolean | string | string[]>>(
    new Map(),
  );
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const charMap = Object.fromEntries(scenario.characters.map((c) => [c.id, c]));
  const charIndex = Object.fromEntries(scenario.characters.map((c, i) => [c.id, i]));
  const totalTurns = scenario.dialog.length;

  // Normalise quiz questions
  const questions: QuizQuestion[] = (() => {
    if (scenario.quiz_questions && scenario.quiz_questions.length > 0)
      return scenario.quiz_questions;
    if (scenario.quiz) {
      return [
        {
          id: "q0",
          question: scenario.quiz.question,
          format: scenario.quiz.format,
          correct_answer: scenario.quiz.correct_answer,
          explanation: scenario.quiz.explanation,
          options: scenario.quiz.options,
        },
      ];
    }
    return [];
  })();

  const currentQ = questions[quizIdx];
  const allAnswered = questions.length > 0 && answers.size === questions.length;

  // Auto-advance dialog turns
  useEffect(() => {
    if (phase !== "dialog" || paused) return;
    if (visibleCount >= totalTurns) {
      timerRef.current = setTimeout(() => {
        setPhase("quiz");
        setTimeout(() => setQuizMounted(true), 30);
      }, 900);
      return;
    }
    timerRef.current = setTimeout(
      () => setVisibleCount((v) => v + 1),
      visibleCount === 0 ? 700 : autoPlayDelayMs,
    );
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [visibleCount, phase, totalTurns, autoPlayDelayMs, paused]);

  function handleAnswer(answer: boolean | string | string[]) {
    setAnswers((prev) => new Map(prev).set(quizIdx, answer));
    setPhase("result");
  }

  function handleNextQuestion() {
    if (quizIdx < questions.length - 1) {
      setQuizIdx((i) => i + 1);
      setPhase("quiz");
    }
  }

  function handleReplay() {
    setPhase("dialog");
    setVisibleCount(0);
    setPaused(false);
    setQuizIdx(0);
    setAnswers(new Map());
    setQuizMounted(false);
  }

  return (
    <div className="mx-auto max-w-2xl space-y-5">
      {/* Header */}
      <div className="flex flex-wrap items-center gap-2">
        <span className="rounded-full bg-indigo-100 px-3 py-1 text-xs font-semibold tracking-wide text-indigo-700 uppercase">
          {scenario.domain.replace(/_/g, " ")}
        </span>
        <h2 className="text-lg font-semibold text-gray-900">{scenario.title}</h2>
      </div>

      {/* Characters legend */}
      <div className="flex flex-wrap gap-5 rounded-xl border bg-gray-50 px-4 py-3">
        {scenario.characters.map((c) => {
          const color = AVATAR_COLORS[charIndex[c.id] % AVATAR_COLORS.length];
          return (
            <div key={c.id} className="flex items-center gap-2">
              <div
                className={cn(
                  "flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-full text-xs font-bold text-white",
                  color,
                )}
              >
                {initials(c.name)}
              </div>
              <div>
                <p className="text-sm font-semibold text-gray-900">{c.name}</p>
                <p className="text-xs text-gray-500">{c.role_label}</p>
              </div>
            </div>
          );
        })}
      </div>

      {/* Dialog */}
      <div className="space-y-4">
        {scenario.dialog.slice(0, visibleCount).map((turn, i) => {
          const char = charMap[turn.speaker];
          const idx = charIndex[turn.speaker] ?? 0;
          const color = AVATAR_COLORS[idx % AVATAR_COLORS.length];
          const isLeft = idx === 0;
          return (
            <div
              key={i}
              className={cn(
                "animate-in fade-in fill-mode-both flex gap-3 duration-500",
                isLeft
                  ? "slide-in-from-left-4 justify-start"
                  : "slide-in-from-right-4 flex-row-reverse justify-start",
              )}
            >
              <div
                className={cn(
                  "flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-full text-xs font-bold text-white",
                  color,
                )}
              >
                {char ? initials(char.name) : "?"}
              </div>
              <div
                className={cn(
                  "max-w-[78%] rounded-2xl px-4 py-3 text-sm leading-relaxed shadow-sm",
                  isLeft
                    ? "rounded-tl-sm border border-gray-200 bg-white text-gray-800"
                    : "rounded-tr-sm bg-indigo-600 text-white",
                )}
              >
                <p
                  className={cn(
                    "mb-1 text-xs font-semibold",
                    isLeft ? "text-blue-600" : "text-indigo-200",
                  )}
                >
                  {char?.role_label ?? turn.speaker}
                </p>
                {turn.text}
              </div>
            </div>
          );
        })}
      </div>

      {/* Transport controls — shown while dialog is playing */}
      {phase === "dialog" && (
        <div className="flex items-center justify-center gap-4">
          <button
            onClick={handleReplay}
            title="Restart"
            className="flex items-center gap-1.5 rounded-lg border px-4 py-2 text-xs font-semibold text-gray-600 hover:bg-gray-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400"
          >
            <RotateCcw className="h-3.5 w-3.5" />
            Restart
          </button>
          <button
            onClick={() => setPaused((p) => !p)}
            className="flex items-center gap-1.5 rounded-lg bg-indigo-600 px-5 py-2 text-xs font-bold text-white hover:bg-indigo-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400"
          >
            {paused ? (
              <>
                <Play className="h-3.5 w-3.5 fill-current" /> Resume
              </>
            ) : (
              <>
                <Pause className="h-3.5 w-3.5" /> Pause
              </>
            )}
          </button>
        </div>
      )}

      {/* Quiz / result card */}
      {phase !== "dialog" && currentQ && (
        <div
          className={cn(
            "rounded-xl border-2 border-indigo-200 bg-indigo-50 p-6 shadow-md transition-all duration-500",
            quizMounted ? "translate-y-0 opacity-100" : "translate-y-6 opacity-0",
          )}
        >
          <div className="mb-1 flex items-center justify-between">
            <p className="text-xs font-semibold tracking-wide text-indigo-500 uppercase">
              Compliance Check
            </p>
            {questions.length > 1 && (
              <p className="text-xs text-indigo-400">
                {quizIdx + 1} / {questions.length}
              </p>
            )}
          </div>
          <p className="mb-5 text-base font-semibold text-gray-900">
            {currentQ.question}
          </p>

          {phase === "quiz" && <QuizInput question={currentQ} onAnswer={handleAnswer} />}

          {phase === "result" && (
            <QuizResult
              question={currentQ}
              answer={answers.get(quizIdx)!}
              hasNext={quizIdx < questions.length - 1}
              onNext={handleNextQuestion}
              onReplay={handleReplay}
            />
          )}
        </div>
      )}

      {/* Score summary */}
      {allAnswered &&
        phase === "result" &&
        quizIdx === questions.length - 1 &&
        questions.length > 1 && (
          <ScoreSummary questions={questions} answers={answers} onReplay={handleReplay} />
        )}
    </div>
  );
}

// ─── Quiz input ───────────────────────────────────────────────────────────────

function QuizInput({
  question,
  onAnswer,
}: {
  question: QuizQuestion;
  onAnswer: (a: boolean | string | string[]) => void;
}) {
  const [selected, setSelected] = useState<string[]>([]);

  if (question.format === "true_false") {
    return (
      <div className="flex gap-3">
        <button
          onClick={() => onAnswer(true)}
          className="flex-1 rounded-lg border-2 border-green-300 bg-white py-3 text-sm font-bold text-green-700 hover:bg-green-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-green-400"
        >
          TRUE
        </button>
        <button
          onClick={() => onAnswer(false)}
          className="flex-1 rounded-lg border-2 border-red-300 bg-white py-3 text-sm font-bold text-red-700 hover:bg-red-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-red-400"
        >
          FALSE
        </button>
      </div>
    );
  }

  if (question.format === "single_choice") {
    return (
      <div className="space-y-2">
        {(question.options ?? []).map((opt) => (
          <button
            key={opt.id}
            onClick={() => onAnswer(opt.id)}
            className="w-full rounded-lg border-2 border-indigo-200 bg-white px-4 py-2.5 text-left text-sm font-medium text-gray-800 hover:border-indigo-400 hover:bg-indigo-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400"
          >
            {opt.text}
          </button>
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="space-y-2">
        {(question.options ?? []).map((opt) => (
          <label
            key={opt.id}
            className={cn(
              "flex cursor-pointer items-center gap-3 rounded-lg border-2 bg-white px-4 py-2.5 text-sm font-medium transition-colors",
              selected.includes(opt.id)
                ? "border-indigo-500 bg-indigo-50 text-indigo-900"
                : "border-indigo-200 text-gray-800 hover:border-indigo-400",
            )}
          >
            <input
              type="checkbox"
              checked={selected.includes(opt.id)}
              onChange={() =>
                setSelected((p) =>
                  p.includes(opt.id) ? p.filter((x) => x !== opt.id) : [...p, opt.id],
                )
              }
              className="accent-indigo-600"
            />
            {opt.text}
          </label>
        ))}
      </div>
      <p className="text-xs text-indigo-400">Select all that apply.</p>
      <button
        onClick={() => onAnswer(selected)}
        disabled={selected.length === 0}
        className="rounded-lg bg-indigo-600 px-5 py-2 text-sm font-semibold text-white hover:bg-indigo-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400 disabled:opacity-40"
      >
        Submit
      </button>
    </div>
  );
}

// ─── Quiz result ──────────────────────────────────────────────────────────────

function QuizResult({
  question,
  answer,
  hasNext,
  onNext,
  onReplay,
}: {
  question: QuizQuestion;
  answer: boolean | string | string[];
  hasNext: boolean;
  onNext: () => void;
  onReplay: () => void;
}) {
  const correct = isCorrectAnswer(question, answer);

  function label(val: boolean | string | string[]): string {
    if (question.format === "true_false") return String(val).toUpperCase();
    if (question.format === "single_choice")
      return question.options?.find((o) => o.id === val)?.text ?? String(val);
    return (val as string[])
      .map((id) => question.options?.find((o) => o.id === id)?.text ?? id)
      .join(", ");
  }

  return (
    <div className="space-y-4">
      <div
        className={cn(
          "flex items-start gap-3 rounded-lg px-4 py-3",
          correct ? "bg-green-100 text-green-800" : "bg-red-100 text-red-800",
        )}
      >
        {correct ? (
          <CheckCircle2 className="mt-0.5 h-5 w-5 flex-shrink-0 text-green-600" />
        ) : (
          <XCircle className="mt-0.5 h-5 w-5 flex-shrink-0 text-red-500" />
        )}
        <p className="font-semibold">
          {correct
            ? "Correct!"
            : `Incorrect. Correct answer: ${label(question.correct_answer)}.`}
        </p>
      </div>
      <div className="rounded-lg border bg-white p-4 text-sm leading-relaxed text-gray-700">
        <p className="mb-1 font-semibold text-gray-900">Explanation</p>
        {question.explanation}
      </div>
      <div className="flex gap-3">
        {hasNext && (
          <button
            onClick={onNext}
            className="rounded-lg bg-indigo-600 px-5 py-2 text-sm font-semibold text-white hover:bg-indigo-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400"
          >
            Next question →
          </button>
        )}
        <button
          onClick={onReplay}
          className="text-sm text-indigo-600 underline underline-offset-2 hover:text-indigo-800"
        >
          Replay scenario
        </button>
      </div>
    </div>
  );
}

// ─── Score summary ────────────────────────────────────────────────────────────

function ScoreSummary({
  questions,
  answers,
  onReplay,
}: {
  questions: QuizQuestion[];
  answers: Map<number, boolean | string | string[]>;
  onReplay: () => void;
}) {
  const score = questions.filter((q, i) => isCorrectAnswer(q, answers.get(i)!)).length;
  const pct = Math.round((score / questions.length) * 100);
  return (
    <div className="space-y-2 rounded-xl border-2 border-indigo-200 bg-white p-6 text-center shadow-md">
      <p className="text-3xl font-bold text-indigo-700">{pct}%</p>
      <p className="text-sm text-gray-600">
        {score} of {questions.length} correct
      </p>
      {pct === 100 && (
        <p className="text-sm font-semibold text-green-700">Perfect score!</p>
      )}
      <button
        onClick={onReplay}
        className="mt-2 text-sm text-indigo-600 underline underline-offset-2 hover:text-indigo-800"
      >
        Replay scenario
      </button>
    </div>
  );
}
