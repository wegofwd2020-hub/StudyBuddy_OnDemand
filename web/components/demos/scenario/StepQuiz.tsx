"use client";

import { Plus, Trash2 } from "lucide-react";
import type { ScenarioDraft, QuizQuestion } from "./types";
import { emptyQuestion } from "./types";

interface Props {
  draft: ScenarioDraft;
  onChange: (patch: Partial<ScenarioDraft>) => void;
}

export function StepQuiz({ draft, onChange }: Props) {
  const questions = draft.quiz_questions;

  function addQuestion() {
    onChange({ quiz_questions: [...questions, emptyQuestion()] });
  }

  function updateQuestion(idx: number, patch: Partial<QuizQuestion>) {
    onChange({
      quiz_questions: questions.map((q, i) => (i === idx ? { ...q, ...patch } : q)),
    });
  }

  function removeQuestion(idx: number) {
    onChange({ quiz_questions: questions.filter((_, i) => i !== idx) });
  }

  function addOption(qIdx: number) {
    const q = questions[qIdx];
    const opts = [...(q.options ?? []), { id: crypto.randomUUID(), text: "" }];
    updateQuestion(qIdx, { options: opts });
  }

  function updateOption(qIdx: number, oIdx: number, text: string) {
    const q = questions[qIdx];
    const opts = (q.options ?? []).map((o, i) => (i === oIdx ? { ...o, text } : o));
    updateQuestion(qIdx, { options: opts });
  }

  function removeOption(qIdx: number, oIdx: number) {
    const q = questions[qIdx];
    const opts = (q.options ?? []).filter((_, i) => i !== oIdx);
    updateQuestion(qIdx, { options: opts });
  }

  return (
    <div className="space-y-6">
      {questions.length === 0 && (
        <p className="rounded-xl border border-dashed bg-gray-50 py-6 text-center text-sm text-gray-500">
          No questions yet. Add at least one compliance check question.
        </p>
      )}

      {questions.map((q, qIdx) => (
        <div key={q.id} className="space-y-4 rounded-xl border bg-white p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold tracking-wide text-indigo-600 uppercase">
              Question {qIdx + 1}
            </span>
            <button
              type="button"
              onClick={() => removeQuestion(qIdx)}
              className="text-gray-400 hover:text-red-500"
            >
              <Trash2 className="h-4 w-4" />
            </button>
          </div>

          {/* Question text */}
          <div>
            <label className="mb-1 block text-xs font-semibold text-gray-600">
              Question *
            </label>
            <textarea
              value={q.question}
              onChange={(e) => updateQuestion(qIdx, { question: e.target.value })}
              placeholder="What compliance question should the learner answer after watching?"
              rows={2}
              className="w-full resize-none rounded-lg border px-3 py-2 text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200"
            />
          </div>

          {/* Format */}
          <div>
            <label className="mb-1 block text-xs font-semibold text-gray-600">
              Answer Format
            </label>
            <div className="flex flex-wrap gap-3">
              {(["true_false", "single_choice", "multiple_choice"] as const).map(
                (fmt) => (
                  <label key={fmt} className="flex cursor-pointer items-center gap-2">
                    <input
                      type="radio"
                      name={`format-${q.id}`}
                      value={fmt}
                      checked={q.format === fmt}
                      onChange={() =>
                        updateQuestion(qIdx, {
                          format: fmt,
                          correct_answer:
                            fmt === "true_false"
                              ? true
                              : fmt === "multiple_choice"
                                ? []
                                : "",
                          options:
                            fmt === "true_false"
                              ? undefined
                              : (q.options ?? [
                                  { id: crypto.randomUUID(), text: "" },
                                  { id: crypto.randomUUID(), text: "" },
                                ]),
                        })
                      }
                      className="accent-indigo-600"
                    />
                    <span className="text-sm">
                      {fmt === "true_false"
                        ? "True / False"
                        : fmt === "single_choice"
                          ? "Single choice"
                          : "Multiple choice"}
                    </span>
                  </label>
                ),
              )}
            </div>
          </div>

          {/* True/False correct answer */}
          {q.format === "true_false" && (
            <div>
              <label className="mb-1 block text-xs font-semibold text-gray-600">
                Correct Answer
              </label>
              <div className="flex gap-4">
                {([true, false] as const).map((v) => (
                  <label
                    key={String(v)}
                    className="flex cursor-pointer items-center gap-2"
                  >
                    <input
                      type="radio"
                      name={`tf-${q.id}`}
                      checked={q.correct_answer === v}
                      onChange={() => updateQuestion(qIdx, { correct_answer: v })}
                      className="accent-indigo-600"
                    />
                    <span className="text-sm font-semibold uppercase">{String(v)}</span>
                  </label>
                ))}
              </div>
            </div>
          )}

          {/* Single / Multiple choice options */}
          {(q.format === "single_choice" || q.format === "multiple_choice") && (
            <div className="space-y-3">
              <label className="block text-xs font-semibold text-gray-600">Options</label>
              {(q.options ?? []).map((opt, oIdx) => {
                const isCorrect =
                  q.format === "multiple_choice"
                    ? (q.correct_answer as string[]).includes(opt.id)
                    : q.correct_answer === opt.id;

                function toggleCorrect() {
                  if (q.format === "single_choice") {
                    updateQuestion(qIdx, { correct_answer: opt.id });
                  } else {
                    const cur = q.correct_answer as string[];
                    updateQuestion(qIdx, {
                      correct_answer: cur.includes(opt.id)
                        ? cur.filter((id) => id !== opt.id)
                        : [...cur, opt.id],
                    });
                  }
                }

                return (
                  <div key={opt.id} className="flex items-center gap-2">
                    <input
                      type={q.format === "single_choice" ? "radio" : "checkbox"}
                      name={`correct-${q.id}`}
                      checked={isCorrect}
                      onChange={toggleCorrect}
                      title="Mark as correct answer"
                      className="flex-shrink-0 accent-indigo-600"
                    />
                    <input
                      value={opt.text}
                      onChange={(e) => updateOption(qIdx, oIdx, e.target.value)}
                      placeholder={`Option ${oIdx + 1}`}
                      className="flex-1 rounded-lg border px-3 py-1.5 text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200"
                    />
                    <button
                      type="button"
                      onClick={() => removeOption(qIdx, oIdx)}
                      className="flex-shrink-0 text-gray-400 hover:text-red-500"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                );
              })}
              <button
                type="button"
                onClick={() => addOption(qIdx)}
                className="flex items-center gap-1 text-xs font-semibold text-indigo-600 hover:text-indigo-800"
              >
                <Plus className="h-3 w-3" /> Add option
              </button>
              <p className="text-xs text-gray-400">
                {q.format === "single_choice"
                  ? "Select the radio button next to the correct option."
                  : "Check all options that are correct."}
              </p>
            </div>
          )}

          {/* Explanation */}
          <div>
            <label className="mb-1 block text-xs font-semibold text-gray-600">
              Explanation (shown after answering)
            </label>
            <textarea
              value={q.explanation}
              onChange={(e) => updateQuestion(qIdx, { explanation: e.target.value })}
              placeholder="Explain why the correct answer is correct — cite the relevant regulation or policy."
              rows={3}
              className="w-full resize-none rounded-lg border px-3 py-2 text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200"
            />
          </div>
        </div>
      ))}

      <button
        type="button"
        onClick={addQuestion}
        className="flex items-center gap-2 rounded-lg border-2 border-dashed border-indigo-300 px-5 py-3 text-sm font-semibold text-indigo-600 transition-colors hover:border-indigo-500 hover:bg-indigo-50"
      >
        <Plus className="h-4 w-4" />
        Add Question
      </button>
    </div>
  );
}
