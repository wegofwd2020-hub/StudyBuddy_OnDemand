"use client";

import { useState, useRef, useEffect } from "react";
import { Play, Pause, RotateCcw, SkipForward, CheckCircle2, XCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import { ScenarioPlayer, type ScenarioData } from "./ScenarioPlayer";
import type { QuizQuestion } from "@/components/demos/scenario/types";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface VideoClip {
  turn_index: number;
  speaker: string;
  video_url: string;
  duration_seconds: number;
  status: string;
}

export interface ScenarioWithClips extends ScenarioData {
  video_clips?: VideoClip[] | null;
}

// ─── Entry point — picks video or text player ─────────────────────────────────

export function ScenarioVideoPlayer({ scenario }: { scenario: ScenarioWithClips }) {
  if (!scenario.video_clips || scenario.video_clips.length === 0) {
    return <ScenarioPlayer scenario={scenario} />;
  }
  return <VideoDialogPlayer scenario={scenario} clips={scenario.video_clips} />;
}

// ─── Video player ─────────────────────────────────────────────────────────────

type Phase = "idle" | "playing" | "paused" | "quiz" | "result" | "done";

const AVATAR_COLORS = ["bg-blue-500", "bg-emerald-500", "bg-violet-500", "bg-amber-500"];

function VideoDialogPlayer({
  scenario,
  clips,
}: {
  scenario: ScenarioData;
  clips: VideoClip[];
}) {
  const [clipIdx, setClipIdx] = useState(0);
  const [phase, setPhase] = useState<Phase>("idle");
  const [quizVisible, setQuizVisible] = useState(false);
  const [quizIdx, setQuizIdx] = useState(0);
  const [answers, setAnswers] = useState<Map<number, boolean | string | string[]>>(new Map());
  const videoRef = useRef<HTMLVideoElement>(null);

  const charMap = Object.fromEntries(scenario.characters.map((c) => [c.id, c]));
  const charColorIdx = Object.fromEntries(scenario.characters.map((c, i) => [c.id, i]));

  // Normalise quiz_questions: prefer the new array, fall back to the legacy single question
  const questions: QuizQuestion[] = (() => {
    const qs = (scenario as unknown as { quiz_questions?: QuizQuestion[] }).quiz_questions;
    if (qs && qs.length > 0) return qs;
    if (scenario.quiz) {
      return [{
        id: "q0",
        question: scenario.quiz.question,
        format: scenario.quiz.format,
        correct_answer: scenario.quiz.correct_answer,
        explanation: scenario.quiz.explanation,
        options: (scenario.quiz as unknown as { options?: string[] }).options,
      } as unknown as QuizQuestion];
    }
    return [];
  })();

  // Play each clip as it becomes active
  useEffect(() => {
    if (phase !== "playing") return;
    const timer = setTimeout(() => videoRef.current?.play(), 50);
    return () => clearTimeout(timer);
  }, [clipIdx, phase]);

  function handleStart() {
    setPhase("playing");
  }

  function handlePlayPause() {
    if (phase === "playing") {
      videoRef.current?.pause();
      setPhase("paused");
    } else if (phase === "paused") {
      videoRef.current?.play();
      setPhase("playing");
    }
  }

  function handleSkip() {
    if (clipIdx < clips.length - 1) {
      setClipIdx((i) => i + 1);
      setPhase("playing");
    } else {
      transitionToQuiz();
    }
  }

  function handleReplayVideo() {
    setClipIdx(0);
    setPhase("playing");
  }

  function handleClipEnded() {
    if (clipIdx < clips.length - 1) {
      setClipIdx((i) => i + 1);
    } else {
      transitionToQuiz();
    }
  }

  function transitionToQuiz() {
    if (questions.length === 0) {
      setTimeout(() => setPhase("done"), 500);
      return;
    }
    setTimeout(() => {
      setPhase("quiz");
      setTimeout(() => setQuizVisible(true), 30);
    }, 500);
  }

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
    setClipIdx(0);
    setPhase("idle");
    setQuizIdx(0);
    setAnswers(new Map());
    setQuizVisible(false);
  }

  const clip = clips[clipIdx];
  const char = charMap[clip?.speaker ?? ""];
  const colorIdx = charColorIdx[clip?.speaker ?? ""] ?? 0;
  const avatarColor = AVATAR_COLORS[colorIdx % AVATAR_COLORS.length];
  const progress = ((clipIdx + 1) / clips.length) * 100;

  const allAnswered = questions.length > 0 && answers.size === questions.length;
  const currentQ = questions[quizIdx];

  return (
    <div className="mx-auto max-w-2xl space-y-5">
      {/* Header */}
      <div className="flex flex-wrap items-center gap-2">
        <span className="rounded-full bg-indigo-100 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-indigo-700">
          {scenario.domain.replace(/_/g, " ")}
        </span>
        <h2 className="text-lg font-semibold text-gray-900">{scenario.title}</h2>
      </div>

      {/* Idle state */}
      {phase === "idle" && (
        <div className="flex flex-col items-center justify-center gap-4 rounded-xl border bg-gray-900 py-16 shadow-lg">
          <p className="text-sm text-gray-400">Watch the scenario unfold, then answer the compliance question{questions.length !== 1 ? "s" : ""}</p>
          <button
            onClick={handleStart}
            className="flex items-center gap-3 rounded-full bg-indigo-600 px-8 py-4 text-base font-bold text-white shadow-lg transition-colors hover:bg-indigo-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400"
          >
            <Play className="h-6 w-6 fill-current" />
            Play Scenario
          </button>
        </div>
      )}

      {/* Video player */}
      {(phase === "playing" || phase === "paused") && clip && (
        <div className="overflow-hidden rounded-xl border shadow-lg">
          {/* Speaker label */}
          <div className={cn("flex items-center gap-3 px-4 py-2", avatarColor)}>
            <div className="flex h-7 w-7 items-center justify-center rounded-full bg-white/20 text-xs font-bold text-white">
              {(char?.name ?? clip.speaker).split(" ").map((w) => w[0]).join("").slice(0, 2).toUpperCase()}
            </div>
            <span className="text-xs font-bold uppercase tracking-wide text-white">
              {char?.role_label ?? clip.speaker}
            </span>
            <span className="ml-auto text-xs text-white/70">
              {clipIdx + 1} / {clips.length}
            </span>
          </div>

          {/* Video */}
          <div className="bg-black">
            <video
              key={clip.video_url}
              ref={videoRef}
              src={clip.video_url}
              playsInline
              onEnded={handleClipEnded}
              className="mx-auto max-h-80 w-full object-contain"
            />
          </div>

          {/* Progress bar */}
          <div className="h-1 bg-gray-200">
            <div className="h-1 bg-indigo-500 transition-all duration-300" style={{ width: `${progress}%` }} />
          </div>
        </div>
      )}

      {/* Transport controls */}
      {(phase === "playing" || phase === "paused") && (
        <div className="flex items-center justify-center gap-4">
          <button
            onClick={handleReplayVideo}
            title="Replay from beginning"
            className="flex items-center gap-1.5 rounded-lg border px-4 py-2 text-xs font-semibold text-gray-600 hover:bg-gray-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400"
          >
            <RotateCcw className="h-3.5 w-3.5" />
            Replay
          </button>

          <button
            onClick={handlePlayPause}
            className="flex items-center gap-1.5 rounded-lg bg-indigo-600 px-5 py-2 text-xs font-bold text-white hover:bg-indigo-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400"
          >
            {phase === "playing"
              ? <><Pause className="h-3.5 w-3.5" /> Pause</>
              : <><Play className="h-3.5 w-3.5 fill-current" /> Play</>
            }
          </button>

          <button
            onClick={handleSkip}
            title="Skip to next clip"
            className="flex items-center gap-1.5 rounded-lg border px-4 py-2 text-xs font-semibold text-gray-600 hover:bg-gray-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400"
          >
            <SkipForward className="h-3.5 w-3.5" />
            Skip
          </button>
        </div>
      )}

      {/* Quiz / result card */}
      {(phase === "quiz" || phase === "result") && currentQ && (
        <div
          className={cn(
            "rounded-xl border-2 border-indigo-200 bg-indigo-50 p-6 shadow-md transition-all duration-500",
            quizVisible ? "translate-y-0 opacity-100" : "translate-y-6 opacity-0",
          )}
        >
          <div className="flex items-center justify-between mb-1">
            <p className="text-xs font-semibold uppercase tracking-wide text-indigo-500">Compliance Check</p>
            {questions.length > 1 && (
              <p className="text-xs text-indigo-400">{quizIdx + 1} / {questions.length}</p>
            )}
          </div>
          <p className="mb-5 text-base font-semibold text-gray-900">{currentQ.question}</p>

          {phase === "quiz" && (
            <QuizInput question={currentQ} onAnswer={handleAnswer} />
          )}

          {phase === "result" && (
            <QuizResult
              question={currentQ}
              answer={answers.get(quizIdx)!}
              hasNext={quizIdx < questions.length - 1}
              allAnswered={allAnswered}
              onNext={handleNextQuestion}
              onReplay={handleReplay}
            />
          )}
        </div>
      )}

      {/* Summary after all questions answered */}
      {allAnswered && phase === "result" && quizIdx === questions.length - 1 && questions.length > 1 && (
        <ScoreSummary questions={questions} answers={answers} onReplay={handleReplay} />
      )}

      {/* Done state — no-quiz scenarios (e.g. social stories) */}
      {phase === "done" && (
        <div className="rounded-xl border-2 border-indigo-200 bg-indigo-50 p-6 shadow-md text-center space-y-3">
          <p className="text-base font-semibold text-gray-900">End of story</p>
          <p className="text-sm text-gray-600">You can replay it any time.</p>
          <button
            onClick={handleReplay}
            className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-5 py-2 text-sm font-semibold text-white hover:bg-indigo-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400"
          >
            <RotateCcw className="h-4 w-4" /> Replay
          </button>
        </div>
      )}
    </div>
  );
}

// ─── Quiz input component ─────────────────────────────────────────────────────

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
        <button onClick={() => onAnswer(true)}
          className="flex-1 rounded-lg border-2 border-green-300 bg-white py-3 text-sm font-bold text-green-700 transition-colors hover:bg-green-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-green-400">
          TRUE
        </button>
        <button onClick={() => onAnswer(false)}
          className="flex-1 rounded-lg border-2 border-red-300 bg-white py-3 text-sm font-bold text-red-700 transition-colors hover:bg-red-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-red-400">
          FALSE
        </button>
      </div>
    );
  }

  if (question.format === "single_choice") {
    return (
      <div className="space-y-2">
        {(question.options ?? []).map((opt) => (
          <button key={opt.id} onClick={() => onAnswer(opt.id)}
            className="w-full rounded-lg border-2 border-indigo-200 bg-white px-4 py-2.5 text-left text-sm font-medium text-gray-800 hover:border-indigo-400 hover:bg-indigo-50 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400">
            {opt.text}
          </button>
        ))}
      </div>
    );
  }

  // Multiple choice
  const opts = question.options ?? [];
  function toggle(id: string) {
    setSelected((prev) => prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]);
  }

  return (
    <div className="space-y-3">
      <div className="space-y-2">
        {opts.map((opt) => (
          <label key={opt.id}
            className={cn(
              "flex items-center gap-3 rounded-lg border-2 bg-white px-4 py-2.5 text-sm font-medium cursor-pointer transition-colors",
              selected.includes(opt.id) ? "border-indigo-500 bg-indigo-50 text-indigo-900" : "border-indigo-200 text-gray-800 hover:border-indigo-400",
            )}>
            <input type="checkbox" checked={selected.includes(opt.id)} onChange={() => toggle(opt.id)}
              className="accent-indigo-600" />
            {opt.text}
          </label>
        ))}
      </div>
      <p className="text-xs text-indigo-400">Select all that apply.</p>
      <button onClick={() => onAnswer(selected)} disabled={selected.length === 0}
        className="rounded-lg bg-indigo-600 px-5 py-2 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-40 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400">
        Submit
      </button>
    </div>
  );
}

// ─── Quiz result component ────────────────────────────────────────────────────

function isCorrectAnswer(question: QuizQuestion, answer: boolean | string | string[]): boolean {
  if (question.format === "true_false") return answer === question.correct_answer;
  if (question.format === "single_choice") return answer === question.correct_answer;
  // Multiple choice: same set (order-insensitive)
  const given = [...(answer as string[])].sort();
  const expected = [...(question.correct_answer as string[])].sort();
  return given.length === expected.length && given.every((v, i) => v === expected[i]);
}

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
  allAnswered: boolean;
  onNext: () => void;
  onReplay: () => void;
}) {
  const correct = isCorrectAnswer(question, answer);

  function answerLabel(): string {
    if (question.format === "true_false") return String(answer).toUpperCase();
    if (question.format === "single_choice") {
      return question.options?.find((o) => o.id === answer)?.text ?? String(answer);
    }
    const ids = answer as string[];
    return ids.map((id) => question.options?.find((o) => o.id === id)?.text ?? id).join(", ");
  }

  function correctLabel(): string {
    if (question.format === "true_false") return String(question.correct_answer).toUpperCase();
    if (question.format === "single_choice") {
      return question.options?.find((o) => o.id === question.correct_answer)?.text ?? String(question.correct_answer);
    }
    const ids = question.correct_answer as string[];
    return ids.map((id) => question.options?.find((o) => o.id === id)?.text ?? id).join(", ");
  }

  return (
    <div className="space-y-4">
      <div className={cn("flex items-start gap-3 rounded-lg px-4 py-3",
        correct ? "bg-green-100 text-green-800" : "bg-red-100 text-red-800")}>
        {correct
          ? <CheckCircle2 className="mt-0.5 h-5 w-5 flex-shrink-0 text-green-600" />
          : <XCircle className="mt-0.5 h-5 w-5 flex-shrink-0 text-red-500" />}
        <p className="font-semibold">
          {correct ? "Correct!" : "Incorrect."}{!correct && <> You answered: <em>{answerLabel()}</em>. Correct: <em>{correctLabel()}</em>.</>}
        </p>
      </div>
      <div className="rounded-lg border bg-white p-4 text-sm leading-relaxed text-gray-700">
        <p className="mb-1 font-semibold text-gray-900">Explanation</p>
        {question.explanation}
      </div>
      <div className="flex gap-3">
        {hasNext && (
          <button onClick={onNext}
            className="rounded-lg bg-indigo-600 px-5 py-2 text-sm font-semibold text-white hover:bg-indigo-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400">
            Next question →
          </button>
        )}
        <button onClick={onReplay}
          className="text-sm text-indigo-600 underline underline-offset-2 hover:text-indigo-800">
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
    <div className="rounded-xl border-2 border-indigo-200 bg-white p-6 shadow-md text-center space-y-2">
      <p className="text-3xl font-bold text-indigo-700">{pct}%</p>
      <p className="text-sm text-gray-600">{score} of {questions.length} correct</p>
      {pct === 100 && <p className="text-sm font-semibold text-green-700">Perfect score!</p>}
      <button onClick={onReplay}
        className="mt-2 text-sm text-indigo-600 underline underline-offset-2 hover:text-indigo-800">
        Replay scenario
      </button>
    </div>
  );
}
