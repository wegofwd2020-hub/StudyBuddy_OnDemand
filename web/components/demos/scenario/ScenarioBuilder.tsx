"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";
import { StepMetadata } from "./StepMetadata";
import { StepCharacters } from "./StepCharacters";
import { StepDialog } from "./StepDialog";
import { StepQuiz } from "./StepQuiz";
import { StepReview } from "./StepReview";
import { emptyDraft, type ScenarioDraft } from "./types";

const STEPS = [
  { id: 1, label: "Details" },
  { id: 2, label: "Characters" },
  { id: 3, label: "Dialog" },
  { id: 4, label: "Quiz" },
  { id: 5, label: "Review" },
];

export function ScenarioBuilder() {
  const [step, setStep] = useState(1);
  const [draft, setDraft] = useState<ScenarioDraft>(emptyDraft);

  function patch(p: Partial<ScenarioDraft>) {
    setDraft((prev) => ({ ...prev, ...p }));
  }

  function canAdvance(): boolean {
    if (step === 1)
      return draft.title.trim().length > 0 && draft.domain.trim().length > 0;
    if (step === 2)
      return (
        draft.characters.length >= 2 &&
        draft.characters.every((c) => c.name.trim() && c.role_label.trim())
      );
    if (step === 3)
      return draft.dialog.length >= 2 && draft.dialog.every((t) => t.text.trim());
    if (step === 4)
      return (
        draft.quiz_questions.length >= 1 &&
        draft.quiz_questions.every((q) => q.question.trim() && q.explanation.trim())
      );
    return true;
  }

  return (
    <div className="mx-auto max-w-3xl space-y-8">
      {/* Step indicator */}
      <nav className="flex items-center gap-0">
        {STEPS.map((s, idx) => (
          <div key={s.id} className="flex flex-1 items-center last:flex-none">
            <button
              type="button"
              onClick={() => {
                if (s.id < step) setStep(s.id);
              }}
              className={cn(
                "group flex flex-col items-center gap-1",
                s.id === step
                  ? "pointer-events-none"
                  : s.id < step
                    ? "cursor-pointer"
                    : "pointer-events-none opacity-40",
              )}
            >
              <span
                className={cn(
                  "flex h-8 w-8 items-center justify-center rounded-full text-sm font-bold transition-colors",
                  s.id === step
                    ? "bg-indigo-600 text-white"
                    : s.id < step
                      ? "bg-indigo-100 text-indigo-700 group-hover:bg-indigo-200"
                      : "bg-gray-100 text-gray-400",
                )}
              >
                {s.id}
              </span>
              <span
                className={cn(
                  "hidden text-xs font-medium sm:block",
                  s.id === step
                    ? "text-indigo-700"
                    : s.id < step
                      ? "text-indigo-500"
                      : "text-gray-400",
                )}
              >
                {s.label}
              </span>
            </button>
            {idx < STEPS.length - 1 && (
              <div
                className={cn(
                  "mx-2 mt-[-12px] h-0.5 flex-1",
                  step > s.id ? "bg-indigo-300" : "bg-gray-200",
                )}
              />
            )}
          </div>
        ))}
      </nav>

      {/* Step content */}
      <div className="rounded-2xl border bg-gray-50 p-6 shadow-sm">
        <h2 className="mb-1 text-lg font-bold text-gray-900">
          {step === 1 && "Scenario Details"}
          {step === 2 && "Define Characters"}
          {step === 3 && "Write the Dialog"}
          {step === 4 && "Compliance Quiz"}
          {step === 5 && "Review & Export"}
        </h2>
        <p className="mb-6 text-sm text-gray-500">
          {step === 1 && "Name the scenario, pick the compliance domain and audience."}
          {step === 2 && "Add 2–4 characters. Each will become a talking avatar."}
          {step === 3 &&
            "Enter the dialog turns in the order they should play. Use the arrows to reorder."}
          {step === 4 &&
            "Add the quiz questions that follow the scenario. Mix question types as needed."}
          {step === 5 &&
            "Check for errors, then download the scenario JSON to trigger avatar generation."}
        </p>

        {step === 1 && <StepMetadata draft={draft} onChange={patch} />}
        {step === 2 && <StepCharacters draft={draft} onChange={patch} />}
        {step === 3 && <StepDialog draft={draft} onChange={patch} />}
        {step === 4 && <StepQuiz draft={draft} onChange={patch} />}
        {step === 5 && <StepReview draft={draft} />}
      </div>

      {/* Navigation */}
      <div className="flex justify-between">
        <button
          type="button"
          onClick={() => setStep((s) => s - 1)}
          disabled={step === 1}
          className="rounded-lg border px-5 py-2.5 text-sm font-semibold text-gray-700 hover:bg-gray-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400 disabled:cursor-not-allowed disabled:opacity-30"
        >
          ← Back
        </button>

        {step < 5 && (
          <button
            type="button"
            onClick={() => setStep((s) => s + 1)}
            disabled={!canAdvance()}
            className="rounded-lg bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-indigo-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400 disabled:cursor-not-allowed disabled:opacity-40"
          >
            Next →
          </button>
        )}
      </div>
    </div>
  );
}
