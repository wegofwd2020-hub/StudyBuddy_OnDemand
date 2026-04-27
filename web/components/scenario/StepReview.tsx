"use client";

import { useState, useEffect, useRef } from "react";
import { CheckCircle2, XCircle, Download, Copy, Loader2, Video, AlertCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import type { ScenarioDraft, ScenarioFile } from "./types";
import {
  generateClips,
  pollClipsStatus,
  clipVideoUrl,
  type ClipsStatusResponse,
} from "@/lib/api/scenarios";

interface Props {
  draft: ScenarioDraft;
}

function slugify(s: string) {
  return s.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "");
}

function buildScenarioFile(draft: ScenarioDraft, clipOverrides?: { turn_index: number; video_url: string }[]): ScenarioFile {
  const id = slugify(draft.title) || "scenario-001";
  return {
    scenario_id: id,
    title: draft.title,
    domain: draft.domain,
    language: draft.language,
    difficulty: draft.difficulty,
    target_seniority: draft.target_seniority,
    description: draft.description,
    content_source: "human_authored",
    characters: draft.characters.map(({ id, name, role_label, org, gender, ethnicity, approx_age, animation_style, voice_id, background }) => ({
      id, name, role_label, org, gender, ethnicity, approx_age, animation_style, voice_id, background,
    })),
    dialog: draft.dialog.map(({ speaker, text }) => ({ speaker, text })),
    quiz_questions: draft.quiz_questions,
    quiz: draft.quiz_questions[0]
      ? {
          question: draft.quiz_questions[0].question,
          format: draft.quiz_questions[0].format,
          correct_answer: draft.quiz_questions[0].correct_answer,
          explanation: draft.quiz_questions[0].explanation,
          options: draft.quiz_questions[0].options,
        }
      : undefined,
    video_clips: clipOverrides
      ? clipOverrides.map((c) => ({ ...c, speaker: draft.dialog[c.turn_index]?.speaker ?? "", duration_seconds: 0, status: "ready" }))
      : null,
    generated_at: new Date().toISOString(),
    model: "human_authored",
    content_version: 1,
  };
}

function ValidationRow({ ok, label }: { ok: boolean; label: string }) {
  return (
    <div className="flex items-center gap-2 text-sm">
      <span className={ok ? "text-green-600" : "text-red-500"}>{ok ? "✓" : "✗"}</span>
      <span className={ok ? "text-gray-700" : "text-red-600"}>{label}</span>
    </div>
  );
}

const STATUS_ICON: Record<string, React.ReactNode> = {
  pending:    <div className="h-4 w-4 rounded-full bg-gray-200" />,
  generating: <Loader2 className="h-4 w-4 animate-spin text-indigo-500" />,
  ready:      <CheckCircle2 className="h-4 w-4 text-green-600" />,
  error:      <XCircle className="h-4 w-4 text-red-500" />,
};

export function StepReview({ draft }: Props) {
  const [copied, setCopied] = useState(false);
  const [genState, setGenState] = useState<"idle" | "submitting" | "polling" | "done" | "failed">("idle");
  const [jobResult, setJobResult] = useState<ClipsStatusResponse | null>(null);
  const [genError, setGenError] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => () => { if (pollRef.current) clearInterval(pollRef.current); }, []);

  const checks = {
    hasTitle:     draft.title.trim().length > 0,
    hasDomain:    draft.domain.trim().length > 0,
    hasChars:     draft.characters.length >= 2,
    charsNamed:   draft.characters.every((c) => c.name.trim() && c.role_label.trim()),
    hasDialog:    draft.dialog.length >= 2,
    dialogFilled: draft.dialog.every((t) => t.text.trim()),
    hasQuiz:      draft.quiz_questions.length > 0,
    quizFilled:   draft.quiz_questions.every((q) => q.question.trim() && q.explanation.trim()),
  };
  const allOk = Object.values(checks).every(Boolean);

  // Build clip overrides once generation is done so download JSON has backend URLs
  const clipOverrides = jobResult?.status === "done"
    ? jobResult.clips
        .filter((c) => c.status === "ready")
        .map((c) => ({ turn_index: c.turn_index, video_url: clipVideoUrl(jobResult.scenario_id, c.turn_index) }))
    : undefined;

  const file = buildScenarioFile(draft, clipOverrides);
  const json = JSON.stringify(file, null, 2);
  const filename = `${file.scenario_id}_${draft.language}.json`;

  function download() {
    const blob = new Blob([json], { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = filename;
    a.click();
  }

  function copyJson() {
    navigator.clipboard.writeText(json).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }

  async function handleGenerate() {
    setGenState("submitting");
    setGenError(null);
    try {
      const { job_id, scenario_id } = await generateClips(file);

      setGenState("polling");

      // Mark all clips "generating" immediately for visual feedback
      setJobResult({
        job_id,
        scenario_id,
        status: "running",
        total_clips: draft.dialog.length,
        completed_clips: 0,
        clips: draft.dialog.map((_, i) => ({ turn_index: i, status: "generating" })),
      });

      pollRef.current = setInterval(async () => {
        try {
          const status = await pollClipsStatus(scenario_id, job_id);
          setJobResult(status);
          if (status.status === "done" || status.status === "failed") {
            clearInterval(pollRef.current!);
            setGenState(status.status === "done" ? "done" : "failed");
            if (status.error) setGenError(status.error);
          }
        } catch (err: unknown) {
          clearInterval(pollRef.current!);
          setGenState("failed");
          setGenError(err instanceof Error ? err.message : "Polling failed");
        }
      }, 3000);
    } catch (err: unknown) {
      setGenState("failed");
      setGenError(err instanceof Error ? err.message : "Request failed");
    }
  }

  return (
    <div className="space-y-6">
      {/* Validation */}
      <div className="rounded-xl border bg-white p-5 shadow-sm space-y-2">
        <p className="text-xs font-bold uppercase tracking-wide text-gray-500 mb-3">Validation</p>
        <ValidationRow ok={checks.hasTitle}     label="Scenario has a title" />
        <ValidationRow ok={checks.hasDomain}    label="Compliance domain selected" />
        <ValidationRow ok={checks.hasChars}     label="At least 2 characters defined" />
        <ValidationRow ok={checks.charsNamed}   label="All characters have a name and role" />
        <ValidationRow ok={checks.hasDialog}    label="At least 2 dialog turns" />
        <ValidationRow ok={checks.dialogFilled} label="All dialog turns have text" />
        <ValidationRow ok={checks.hasQuiz}      label="At least 1 quiz question" />
        <ValidationRow ok={checks.quizFilled}   label="All questions have text and explanation" />
      </div>

      {/* Summary */}
      <div className="rounded-xl border bg-gray-50 p-5 text-sm space-y-1">
        <p className="font-semibold text-gray-900">{draft.title || "(untitled)"}</p>
        <p className="text-gray-500">{draft.domain || "—"} · {draft.language.toUpperCase()} · {draft.difficulty}</p>
        <p className="text-gray-500">
          {draft.characters.length} characters · {draft.dialog.length} turns · {draft.quiz_questions.length} question{draft.quiz_questions.length !== 1 ? "s" : ""}
        </p>
      </div>

      {/* Avatar generation panel */}
      <div className="rounded-xl border bg-white p-5 shadow-sm space-y-4">
        <div className="flex items-center gap-2">
          <Video className="h-4 w-4 text-indigo-500" />
          <p className="text-sm font-bold text-gray-900">Avatar Video Generation</p>
        </div>

        {genState === "idle" && (
          <p className="text-sm text-gray-500">
            Click <strong>Generate Avatars</strong> to send each dialog turn to D-ID and produce
            talking-avatar MP4 clips. This takes ~30–60 s per turn.
          </p>
        )}

        {/* Per-clip status */}
        {jobResult && (
          <div className="space-y-2">
            {jobResult.clips.map((clip) => {
              const char = draft.characters.find((c) => c.id === draft.dialog[clip.turn_index]?.speaker);
              return (
                <div key={clip.turn_index} className="flex items-center gap-3 text-sm">
                  {STATUS_ICON[clip.status] ?? STATUS_ICON.pending}
                  <span className="text-gray-700">
                    Turn {clip.turn_index + 1}
                    {char ? ` — ${char.name}` : ""}
                  </span>
                  <span className={cn(
                    "ml-auto text-xs font-semibold capitalize",
                    clip.status === "ready"  ? "text-green-600" :
                    clip.status === "error"  ? "text-red-500"   :
                    clip.status === "generating" ? "text-indigo-500" : "text-gray-400",
                  )}>
                    {clip.status}
                  </span>
                  {clip.error && <span className="text-xs text-red-400 truncate max-w-xs">{clip.error}</span>}
                </div>
              );
            })}
          </div>
        )}

        {/* Progress bar */}
        {genState === "polling" && jobResult && (
          <div className="space-y-1">
            <div className="h-1.5 w-full rounded-full bg-gray-100">
              <div
                className="h-1.5 rounded-full bg-indigo-500 transition-all duration-500"
                style={{ width: `${Math.round((jobResult.completed_clips / Math.max(jobResult.total_clips, 1)) * 100)}%` }}
              />
            </div>
            <p className="text-xs text-gray-400 text-right">
              {jobResult.completed_clips} / {jobResult.total_clips} clips complete
            </p>
          </div>
        )}

        {genState === "done" && (
          <div className="flex items-center gap-2 rounded-lg bg-green-50 px-4 py-3 text-sm text-green-800">
            <CheckCircle2 className="h-4 w-4 flex-shrink-0 text-green-600" />
            All clips ready. Download the JSON below — video URLs now point to the backend.
          </div>
        )}

        {genState === "failed" && (
          <div className="flex items-start gap-2 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-800">
            <AlertCircle className="h-4 w-4 flex-shrink-0 text-red-500 mt-0.5" />
            <div>
              <p className="font-semibold">Generation failed</p>
              {genError && <p className="text-xs mt-0.5">{genError}</p>}
            </div>
          </div>
        )}

        {(genState === "idle" || genState === "failed") && (
          <button
            type="button"
            onClick={handleGenerate}
            disabled={!allOk}
            className="flex items-center gap-2 rounded-lg bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-40 disabled:cursor-not-allowed focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400"
          >
            <Video className="h-4 w-4" />
            {genState === "failed" ? "Retry Generation" : "Generate Avatars"}
          </button>
        )}

        {genState === "submitting" && (
          <div className="flex items-center gap-2 text-sm text-indigo-600">
            <Loader2 className="h-4 w-4 animate-spin" />
            Submitting to pipeline…
          </div>
        )}

        {genState === "polling" && (
          <div className="flex items-center gap-2 text-sm text-indigo-600">
            <Loader2 className="h-4 w-4 animate-spin" />
            Generating avatars via D-ID…
          </div>
        )}
      </div>

      {/* JSON export */}
      <div className="flex gap-3 flex-wrap">
        <button
          type="button"
          onClick={download}
          disabled={!allOk}
          className="flex items-center gap-2 rounded-lg bg-gray-800 px-5 py-2.5 text-sm font-semibold text-white hover:bg-gray-900 disabled:opacity-40 disabled:cursor-not-allowed focus:outline-none focus-visible:ring-2 focus-visible:ring-gray-400"
        >
          <Download className="h-4 w-4" />
          Download JSON
        </button>
        <button
          type="button"
          onClick={copyJson}
          className="flex items-center gap-2 rounded-lg border px-5 py-2.5 text-sm font-semibold text-gray-700 hover:bg-gray-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400"
        >
          {copied ? <CheckCircle2 className="h-4 w-4 text-green-600" /> : <Copy className="h-4 w-4" />}
          {copied ? "Copied!" : "Copy JSON"}
        </button>
      </div>

      {!allOk && (
        <p className="text-xs text-red-500">Fix the validation issues above before generating or downloading.</p>
      )}
    </div>
  );
}
