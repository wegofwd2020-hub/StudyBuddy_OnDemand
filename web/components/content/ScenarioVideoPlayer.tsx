"use client";

import { useState, useRef } from "react";
import { CheckCircle2, XCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import { ScenarioPlayer, type ScenarioData } from "./ScenarioPlayer";

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

type Phase = "playing" | "quiz" | "result";

const AVATAR_COLORS = ["bg-blue-500", "bg-emerald-500", "bg-violet-500", "bg-amber-500"];

function VideoDialogPlayer({
  scenario,
  clips,
}: {
  scenario: ScenarioData;
  clips: VideoClip[];
}) {
  const [clipIdx, setClipIdx] = useState(0);
  const [phase, setPhase] = useState<Phase>("playing");
  const [quizVisible, setQuizVisible] = useState(false);
  const [selectedAnswer, setSelectedAnswer] = useState<boolean | null>(null);
  const videoRef = useRef<HTMLVideoElement>(null);

  const charMap = Object.fromEntries(scenario.characters.map((c) => [c.id, c]));
  const charColorIdx = Object.fromEntries(scenario.characters.map((c, i) => [c.id, i]));

  function handleClipEnded() {
    if (clipIdx < clips.length - 1) {
      setClipIdx((i) => i + 1);
    } else {
      setTimeout(() => {
        setPhase("quiz");
        setTimeout(() => setQuizVisible(true), 30);
      }, 500);
    }
  }

  function handleAnswer(answer: boolean) {
    setSelectedAnswer(answer);
    setPhase("result");
  }

  function handleReplay() {
    setClipIdx(0);
    setPhase("playing");
    setSelectedAnswer(null);
    setQuizVisible(false);
  }

  const clip = clips[clipIdx];
  const char = charMap[clip?.speaker ?? ""];
  const colorIdx = charColorIdx[clip?.speaker ?? ""] ?? 0;
  const avatarColor = AVATAR_COLORS[colorIdx % AVATAR_COLORS.length];
  const isCorrect = selectedAnswer === scenario.quiz.correct_answer;
  const progress = ((clipIdx + 1) / clips.length) * 100;

  return (
    <div className="mx-auto max-w-2xl space-y-5">
      {/* Header */}
      <div className="flex flex-wrap items-center gap-2">
        <span className="rounded-full bg-indigo-100 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-indigo-700">
          {scenario.domain.replace(/_/g, " ")}
        </span>
        <h2 className="text-lg font-semibold text-gray-900">{scenario.title}</h2>
      </div>

      {/* Video player */}
      {phase === "playing" && clip && (
        <div className="overflow-hidden rounded-xl border shadow-lg">
          {/* Speaker label bar */}
          <div className={cn("flex items-center gap-3 px-4 py-2", avatarColor)}>
            <div className="flex h-7 w-7 items-center justify-center rounded-full bg-white/20 text-xs font-bold text-white">
              {(char?.name ?? clip.speaker)
                .split(" ")
                .map((w) => w[0])
                .join("")
                .slice(0, 2)
                .toUpperCase()}
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
              autoPlay
              playsInline
              onEnded={handleClipEnded}
              className="mx-auto max-h-80 w-full object-contain"
            />
          </div>

          {/* Progress bar */}
          <div className="h-1 bg-gray-200">
            <div
              className="h-1 bg-indigo-500 transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      )}

      {/* Quiz / result card */}
      {phase !== "playing" && (
        <div
          className={cn(
            "rounded-xl border-2 border-indigo-200 bg-indigo-50 p-6 shadow-md transition-all duration-500",
            quizVisible ? "translate-y-0 opacity-100" : "translate-y-6 opacity-0",
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
                  <span className="uppercase">{String(scenario.quiz.correct_answer)}</span>.
                </p>
              </div>

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
