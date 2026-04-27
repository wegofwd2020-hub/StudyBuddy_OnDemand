"use client";

import { useState } from "react";
import { CheckCircle2, Download, Copy } from "lucide-react";
import type { ScenarioDraft, ScenarioFile } from "./types";

interface Props {
  draft: ScenarioDraft;
}

function slugify(s: string) {
  return s.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "");
}

function buildScenarioFile(draft: ScenarioDraft): ScenarioFile {
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
    // Legacy single-question compat for current player
    quiz: draft.quiz_questions[0]
      ? {
          question: draft.quiz_questions[0].question,
          format: draft.quiz_questions[0].format,
          correct_answer: draft.quiz_questions[0].correct_answer,
          explanation: draft.quiz_questions[0].explanation,
          options: draft.quiz_questions[0].options,
        }
      : undefined,
    video_clips: null,
    generated_at: new Date().toISOString(),
    model: "human_authored",
    content_version: 1,
  };
}

function ValidationRow({ ok, label }: { ok: boolean; label: string }) {
  return (
    <div className="flex items-center gap-2 text-sm">
      <span className={ok ? "text-green-600" : "text-red-500"}>
        {ok ? "✓" : "✗"}
      </span>
      <span className={ok ? "text-gray-700" : "text-red-600"}>{label}</span>
    </div>
  );
}

export function StepReview({ draft }: Props) {
  const [copied, setCopied] = useState(false);

  const checks = {
    hasTitle: draft.title.trim().length > 0,
    hasDomain: draft.domain.trim().length > 0,
    hasChars: draft.characters.length >= 2,
    charsNamed: draft.characters.every((c) => c.name.trim() && c.role_label.trim()),
    hasDialog: draft.dialog.length >= 2,
    dialogFilled: draft.dialog.every((t) => t.text.trim()),
    hasQuiz: draft.quiz_questions.length > 0,
    quizFilled: draft.quiz_questions.every(
      (q) => q.question.trim() && q.explanation.trim()
    ),
  };
  const allOk = Object.values(checks).every(Boolean);

  const file = buildScenarioFile(draft);
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

  return (
    <div className="space-y-6">
      {/* Validation */}
      <div className="rounded-xl border bg-white p-5 shadow-sm space-y-2">
        <p className="text-xs font-bold uppercase tracking-wide text-gray-500 mb-3">Validation</p>
        <ValidationRow ok={checks.hasTitle}    label="Scenario has a title" />
        <ValidationRow ok={checks.hasDomain}   label="Compliance domain selected" />
        <ValidationRow ok={checks.hasChars}    label="At least 2 characters defined" />
        <ValidationRow ok={checks.charsNamed}  label="All characters have a name and role" />
        <ValidationRow ok={checks.hasDialog}   label="At least 2 dialog turns" />
        <ValidationRow ok={checks.dialogFilled} label="All dialog turns have text" />
        <ValidationRow ok={checks.hasQuiz}     label="At least 1 quiz question" />
        <ValidationRow ok={checks.quizFilled}  label="All questions have text and explanation" />
      </div>

      {/* Summary */}
      <div className="rounded-xl border bg-gray-50 p-5 text-sm space-y-1">
        <p className="font-semibold text-gray-900">{draft.title || "(untitled)"}</p>
        <p className="text-gray-500">{draft.domain || "—"} · {draft.language.toUpperCase()} · {draft.difficulty}</p>
        <p className="text-gray-500">{draft.characters.length} characters · {draft.dialog.length} turns · {draft.quiz_questions.length} question{draft.quiz_questions.length !== 1 ? "s" : ""}</p>
      </div>

      {/* Avatar generation note */}
      <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
        <p className="font-semibold mb-1">Next step — Avatar Video Generation</p>
        <p>
          Download the JSON file below and run <code className="bg-amber-100 rounded px-1 py-0.5 text-xs font-mono">pipeline/avatar_worker.py</code> to
          generate D-ID talking-avatar clips. Place the resulting MP4 files in{" "}
          <code className="bg-amber-100 rounded px-1 py-0.5 text-xs font-mono">web/public/scenarios/{file.scenario_id}/</code> and
          update the <code className="bg-amber-100 rounded px-1 py-0.5 text-xs font-mono">video_clips</code> paths in the JSON before publishing.
        </p>
      </div>

      {/* Actions */}
      <div className="flex gap-3 flex-wrap">
        <button
          type="button"
          onClick={download}
          disabled={!allOk}
          className="flex items-center gap-2 rounded-lg bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-40 disabled:cursor-not-allowed focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400"
        >
          <Download className="h-4 w-4" />
          Download scenario JSON
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
        <p className="text-xs text-red-500">Fix the validation issues above before downloading.</p>
      )}
    </div>
  );
}
