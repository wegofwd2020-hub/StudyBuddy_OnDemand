"use client";

import { useState, useEffect, useRef } from "react";
import { CheckCircle2, XCircle } from "lucide-react";
import { cn } from "@/lib/utils";

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

interface ScenarioQuiz {
  question: string;
  format: "true_false" | "multiple_choice";
  correct_answer: boolean | string;
  explanation: string;
  options?: string[];
}

export interface ScenarioData {
  scenario_id: string;
  title: string;
  domain: string;
  content_source?: string;
  characters: Character[];
  dialog: DialogTurn[];
  quiz: ScenarioQuiz;
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

// ─── Component ────────────────────────────────────────────────────────────────

type Phase = "dialog" | "quiz" | "result";

export function ScenarioPlayer({
  scenario,
  autoPlayDelayMs = 2500,
}: ScenarioPlayerProps) {
  const [visibleCount, setVisibleCount] = useState(0);
  const [phase, setPhase] = useState<Phase>("dialog");
  const [quizMounted, setQuizMounted] = useState(false);
  const [selectedAnswer, setSelectedAnswer] = useState<boolean | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const charMap = Object.fromEntries(scenario.characters.map((c) => [c.id, c]));
  const charIndex = Object.fromEntries(scenario.characters.map((c, i) => [c.id, i]));
  const totalTurns = scenario.dialog.length;

  // Auto-advance dialog turns, then reveal quiz
  useEffect(() => {
    if (phase !== "dialog") return;
    if (visibleCount >= totalTurns) {
      timerRef.current = setTimeout(() => {
        setPhase("quiz");
        // tiny delay so quiz mounts first, then CSS transition fires
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
  }, [visibleCount, phase, totalTurns, autoPlayDelayMs]);

  function handleAnswer(answer: boolean) {
    setSelectedAnswer(answer);
    setPhase("result");
  }

  function handleReplay() {
    setPhase("dialog");
    setVisibleCount(0);
    setSelectedAnswer(null);
    setQuizMounted(false);
  }

  const isCorrect = selectedAnswer === scenario.quiz.correct_answer;

  return (
    <div className="mx-auto max-w-2xl space-y-5">
      {/* Header */}
      <div className="flex flex-wrap items-center gap-2">
        <span className="rounded-full bg-indigo-100 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-indigo-700">
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
                "flex gap-3 animate-in fade-in duration-500 fill-mode-both",
                isLeft
                  ? "justify-start slide-in-from-left-4"
                  : "flex-row-reverse justify-start slide-in-from-right-4",
              )}
            >
              {/* Avatar */}
              <div
                className={cn(
                  "flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-full text-xs font-bold text-white",
                  color,
                )}
              >
                {char ? initials(char.name) : "?"}
              </div>

              {/* Bubble */}
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

      {/* Quiz / Result card */}
      {phase !== "dialog" && (
        <div
          className={cn(
            "rounded-xl border-2 border-indigo-200 bg-indigo-50 p-6 shadow-md transition-all duration-500",
            quizMounted ? "translate-y-0 opacity-100" : "translate-y-6 opacity-0",
          )}
        >
          <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-indigo-500">
            Compliance Check
          </p>
          <p className="mb-5 text-base font-semibold text-gray-900">
            {scenario.quiz.question}
          </p>

          {phase === "quiz" && (
            <div className="flex gap-3">
              <button
                onClick={() => handleAnswer(true)}
                className="flex-1 rounded-lg border-2 border-green-300 bg-white py-3 text-sm font-bold text-green-700 transition-colors hover:bg-green-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-green-400"
              >
                TRUE
              </button>
              <button
                onClick={() => handleAnswer(false)}
                className="flex-1 rounded-lg border-2 border-red-300 bg-white py-3 text-sm font-bold text-red-700 transition-colors hover:bg-red-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-red-400"
              >
                FALSE
              </button>
            </div>
          )}

          {phase === "result" && (
            <div className="space-y-4">
              {/* Verdict */}
              <div
                className={cn(
                  "flex items-start gap-3 rounded-lg px-4 py-3",
                  isCorrect ? "bg-green-100 text-green-800" : "bg-red-100 text-red-800",
                )}
              >
                {isCorrect ? (
                  <CheckCircle2 className="mt-0.5 h-5 w-5 flex-shrink-0 text-green-600" />
                ) : (
                  <XCircle className="mt-0.5 h-5 w-5 flex-shrink-0 text-red-500" />
                )}
                <p className="font-semibold">
                  {isCorrect ? "Correct!" : "Incorrect."} The answer is{" "}
                  <span className="uppercase">
                    {String(scenario.quiz.correct_answer)}
                  </span>
                  .
                </p>
              </div>

              {/* Explanation */}
              <div className="rounded-lg border bg-white p-4 text-sm leading-relaxed text-gray-700">
                <p className="mb-1 font-semibold text-gray-900">Explanation</p>
                {scenario.quiz.explanation}
              </div>

              <button
                onClick={handleReplay}
                className="text-sm text-indigo-600 underline underline-offset-2 hover:text-indigo-800"
              >
                Replay scenario
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
