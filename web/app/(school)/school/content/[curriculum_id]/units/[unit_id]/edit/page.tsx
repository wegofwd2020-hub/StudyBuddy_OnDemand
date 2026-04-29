"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useTeacher } from "@/lib/hooks/useTeacher";
import {
  listUnitOverrideStatus,
  getUnitOverride,
  saveDraft,
  submitForReview,
  approveUnitContent,
  rejectUnitContent,
  type UnitOverrideStatus,
} from "@/lib/api/school-admin";
import {
  ArrowLeft,
  BookOpen,
  Save,
  Send,
  CheckCircle2,
  AlertCircle,
  Clock,
  ThumbsUp,
  ThumbsDown,
} from "lucide-react";

// Shared textarea class
const TA =
  "w-full rounded-md border border-gray-200 bg-white px-3 py-2 text-sm text-gray-900 shadow-sm placeholder:text-gray-400 focus:border-indigo-400 focus:outline-none focus:ring-1 focus:ring-indigo-400 disabled:bg-gray-50 disabled:text-gray-500";

// ── Lesson ────────────────────────────────────────────────────────────────────

interface LessonSection {
  heading: string;
  body: string;
}

interface LessonDraft {
  synopsis: string;
  sections: LessonSection[];
  key_points: string;
  learning_objectives: string;
}

function lessonBodyToForm(body: Record<string, unknown>): LessonDraft {
  const sections = (body.sections as LessonSection[] | undefined) ?? [];
  return {
    synopsis: (body.synopsis as string) ?? "",
    sections: sections.length > 0 ? sections : [{ heading: "Introduction", body: "" }],
    key_points: ((body.key_points as string[]) ?? []).join("\n"),
    learning_objectives: ((body.learning_objectives as string[]) ?? []).join("\n"),
  };
}

function formToLessonBody(
  original: Record<string, unknown>,
  form: LessonDraft,
): Record<string, unknown> {
  return {
    ...original,
    synopsis: form.synopsis,
    sections: form.sections,
    key_points: form.key_points.split("\n").map((s) => s.trim()).filter(Boolean),
    learning_objectives: form.learning_objectives.split("\n").map((s) => s.trim()).filter(Boolean),
  };
}

function LessonEditor({
  draft,
  onChange,
  readOnly,
}: {
  draft: LessonDraft;
  onChange: (d: LessonDraft) => void;
  readOnly: boolean;
}) {
  function updateSection(i: number, field: keyof LessonSection, value: string) {
    onChange({ ...draft, sections: draft.sections.map((s, idx) => idx === i ? { ...s, [field]: value } : s) });
  }

  return (
    <div className="space-y-6">
      <div>
        <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-gray-500">Synopsis</label>
        <textarea rows={3} className={TA} value={draft.synopsis} disabled={readOnly}
          onChange={(e) => onChange({ ...draft, synopsis: e.target.value })}
          placeholder="A short summary of what this unit covers…" />
      </div>

      <div>
        <div className="mb-2 flex items-center justify-between">
          <label className="text-xs font-semibold uppercase tracking-wide text-gray-500">Sections</label>
          {!readOnly && (
            <button type="button" onClick={() => onChange({ ...draft, sections: [...draft.sections, { heading: "", body: "" }] })}
              className="text-xs font-medium text-indigo-600 hover:underline">+ Add section</button>
          )}
        </div>
        <div className="space-y-4">
          {draft.sections.map((section, i) => (
            <div key={i} className="rounded-lg border border-gray-200 bg-gray-50 p-4">
              <div className="mb-2 flex items-center gap-2">
                <span className="text-xs font-semibold text-gray-400">§{i + 1}</span>
                <input type="text"
                  className="flex-1 rounded border border-gray-200 bg-white px-2 py-1 text-sm font-medium text-gray-800 shadow-sm focus:border-indigo-400 focus:outline-none disabled:bg-gray-50 disabled:text-gray-500"
                  value={section.heading} disabled={readOnly}
                  onChange={(e) => updateSection(i, "heading", e.target.value)}
                  placeholder="Section heading" />
                {!readOnly && draft.sections.length > 1 && (
                  <button type="button" onClick={() => onChange({ ...draft, sections: draft.sections.filter((_, idx) => idx !== i) })}
                    className="text-xs text-gray-400 hover:text-red-500">Remove</button>
                )}
              </div>
              <textarea rows={5} className={TA} value={section.body} disabled={readOnly}
                onChange={(e) => updateSection(i, "body", e.target.value)}
                placeholder="Section content — markdown supported" />
            </div>
          ))}
        </div>
      </div>

      <div>
        <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-gray-500">
          Key points <span className="font-normal normal-case text-gray-400">(one per line)</span>
        </label>
        <textarea rows={4} className={TA} value={draft.key_points} disabled={readOnly}
          onChange={(e) => onChange({ ...draft, key_points: e.target.value })}
          placeholder="Each key takeaway on its own line…" />
      </div>

      <div>
        <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-gray-500">
          Learning objectives <span className="font-normal normal-case text-gray-400">(one per line)</span>
        </label>
        <textarea rows={4} className={TA} value={draft.learning_objectives} disabled={readOnly}
          onChange={(e) => onChange({ ...draft, learning_objectives: e.target.value })}
          placeholder="What students will be able to do after this unit…" />
      </div>
    </div>
  );
}

// ── Tutorial ──────────────────────────────────────────────────────────────────

interface TutorialSection {
  section_id: string;
  title: string;
  content: string;
  examples: string;        // joined with \n for editing
  practice_question: string;
}

interface TutorialDraft {
  title: string;
  sections: TutorialSection[];
  common_mistakes: string; // joined with \n
}

function tutorialBodyToForm(body: Record<string, unknown>): TutorialDraft {
  const rawSections = (body.sections as Record<string, unknown>[] | undefined) ?? [];
  return {
    title: (body.title as string) ?? "",
    sections:
      rawSections.length > 0
        ? rawSections.map((s) => ({
            section_id: (s.section_id as string) ?? "",
            title: (s.title as string) ?? "",
            content: (s.content as string) ?? "",
            examples: ((s.examples as string[]) ?? []).join("\n"),
            practice_question: (s.practice_question as string) ?? "",
          }))
        : [{ section_id: "s1", title: "", content: "", examples: "", practice_question: "" }],
    common_mistakes: ((body.common_mistakes as string[]) ?? []).join("\n"),
  };
}

function formToTutorialBody(
  original: Record<string, unknown>,
  form: TutorialDraft,
): Record<string, unknown> {
  return {
    ...original,
    title: form.title,
    sections: form.sections.map((s) => ({
      section_id: s.section_id,
      title: s.title,
      content: s.content,
      examples: s.examples.split("\n").map((e) => e.trim()).filter(Boolean),
      practice_question: s.practice_question,
    })),
    common_mistakes: form.common_mistakes.split("\n").map((s) => s.trim()).filter(Boolean),
  };
}

function TutorialEditor({
  draft,
  onChange,
  readOnly,
}: {
  draft: TutorialDraft;
  onChange: (d: TutorialDraft) => void;
  readOnly: boolean;
}) {
  function updateSection(i: number, field: keyof TutorialSection, value: string) {
    onChange({ ...draft, sections: draft.sections.map((s, idx) => idx === i ? { ...s, [field]: value } : s) });
  }

  function addSection() {
    const newId = `s${draft.sections.length + 1}`;
    onChange({ ...draft, sections: [...draft.sections, { section_id: newId, title: "", content: "", examples: "", practice_question: "" }] });
  }

  return (
    <div className="space-y-6">
      <div>
        <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-gray-500">Tutorial title</label>
        <input type="text"
          className="w-full rounded-md border border-gray-200 bg-white px-3 py-2 text-sm font-medium text-gray-900 shadow-sm placeholder:text-gray-400 focus:border-indigo-400 focus:outline-none focus:ring-1 focus:ring-indigo-400 disabled:bg-gray-50 disabled:text-gray-500"
          value={draft.title} disabled={readOnly}
          onChange={(e) => onChange({ ...draft, title: e.target.value })}
          placeholder="Tutorial title…" />
      </div>

      <div>
        <div className="mb-2 flex items-center justify-between">
          <label className="text-xs font-semibold uppercase tracking-wide text-gray-500">Sections</label>
          {!readOnly && (
            <button type="button" onClick={addSection} className="text-xs font-medium text-indigo-600 hover:underline">+ Add section</button>
          )}
        </div>
        <div className="space-y-5">
          {draft.sections.map((section, i) => (
            <div key={section.section_id || i} className="space-y-3 rounded-lg border border-gray-200 bg-gray-50 p-4">
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold text-gray-400">§{i + 1}</span>
                <input type="text"
                  className="flex-1 rounded border border-gray-200 bg-white px-2 py-1 text-sm font-medium text-gray-800 shadow-sm focus:border-indigo-400 focus:outline-none disabled:bg-gray-50 disabled:text-gray-500"
                  value={section.title} disabled={readOnly}
                  onChange={(e) => updateSection(i, "title", e.target.value)}
                  placeholder="Section title" />
                {!readOnly && draft.sections.length > 1 && (
                  <button type="button"
                    onClick={() => onChange({ ...draft, sections: draft.sections.filter((_, idx) => idx !== i) })}
                    className="text-xs text-gray-400 hover:text-red-500">Remove</button>
                )}
              </div>
              <div>
                <label className="mb-1 block text-xs text-gray-500">Content</label>
                <textarea rows={4} className={TA} value={section.content} disabled={readOnly}
                  onChange={(e) => updateSection(i, "content", e.target.value)}
                  placeholder="Section content — markdown supported" />
              </div>
              <div>
                <label className="mb-1 block text-xs text-gray-500">
                  Examples <span className="text-gray-400">(one per line)</span>
                </label>
                <textarea rows={3} className={TA} value={section.examples} disabled={readOnly}
                  onChange={(e) => updateSection(i, "examples", e.target.value)}
                  placeholder="Each worked example on its own line…" />
              </div>
              <div>
                <label className="mb-1 block text-xs text-gray-500">Practice question</label>
                <input type="text"
                  className="w-full rounded-md border border-gray-200 bg-white px-3 py-2 text-sm text-gray-900 shadow-sm placeholder:text-gray-400 focus:border-indigo-400 focus:outline-none focus:ring-1 focus:ring-indigo-400 disabled:bg-gray-50 disabled:text-gray-500"
                  value={section.practice_question} disabled={readOnly}
                  onChange={(e) => updateSection(i, "practice_question", e.target.value)}
                  placeholder="A question to check understanding…" />
              </div>
            </div>
          ))}
        </div>
      </div>

      <div>
        <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-gray-500">
          Common mistakes <span className="font-normal normal-case text-gray-400">(one per line)</span>
        </label>
        <textarea rows={4} className={TA} value={draft.common_mistakes} disabled={readOnly}
          onChange={(e) => onChange({ ...draft, common_mistakes: e.target.value })}
          placeholder="Each common mistake students make, one per line…" />
      </div>
    </div>
  );
}

// ── Quiz ──────────────────────────────────────────────────────────────────────

interface QuizOption {
  option_id: string;
  text: string;
}

interface QuizQuestion {
  question_id: string;
  question_text: string;
  question_type: string;
  options: QuizOption[];
  correct_option: string;
  explanation: string;
  difficulty: string;
}

interface QuizDraft {
  questions: QuizQuestion[];
}

function blankQuestion(i: number): QuizQuestion {
  return {
    question_id: `Q${i + 1}`,
    question_text: "",
    question_type: "multiple_choice",
    options: [
      { option_id: "A", text: "" },
      { option_id: "B", text: "" },
      { option_id: "C", text: "" },
      { option_id: "D", text: "" },
    ],
    correct_option: "A",
    explanation: "",
    difficulty: "medium",
  };
}

function quizBodyToForm(body: Record<string, unknown>): QuizDraft {
  const rawQs = (body.questions as Record<string, unknown>[] | undefined) ?? [];
  const questions = Array.from({ length: 8 }, (_, i) => {
    const q = rawQs[i];
    if (!q) return blankQuestion(i);
    const rawOptions = (q.options as Record<string, unknown>[] | undefined) ?? [];
    const options: QuizOption[] = ["A", "B", "C", "D"].map((id) => {
      const found = rawOptions.find((o) => (o.option_id as string) === id);
      return { option_id: id, text: found ? ((found.text as string) ?? "") : "" };
    });
    return {
      question_id: (q.question_id as string) ?? `Q${i + 1}`,
      question_text: (q.question_text as string) ?? "",
      question_type: (q.question_type as string) ?? "multiple_choice",
      options,
      correct_option: (q.correct_option as string) ?? "A",
      explanation: (q.explanation as string) ?? "",
      difficulty: (q.difficulty as string) ?? "medium",
    };
  });
  return { questions };
}

function formToQuizBody(
  original: Record<string, unknown>,
  form: QuizDraft,
): Record<string, unknown> {
  return {
    ...original,
    questions: form.questions.map((q) => ({
      question_id: q.question_id,
      question_text: q.question_text,
      question_type: q.question_type,
      options: q.options,
      correct_option: q.correct_option,
      explanation: q.explanation,
      difficulty: q.difficulty,
    })),
  };
}

function QuizEditor({
  draft,
  onChange,
  readOnly,
}: {
  draft: QuizDraft;
  onChange: (d: QuizDraft) => void;
  readOnly: boolean;
}) {
  function updateQuestion(qi: number, field: keyof Omit<QuizQuestion, "options">, value: string) {
    onChange({ questions: draft.questions.map((q, i) => i === qi ? { ...q, [field]: value } : q) });
  }

  function updateOption(qi: number, optionId: string, value: string) {
    onChange({
      questions: draft.questions.map((q, i) => {
        if (i !== qi) return q;
        return { ...q, options: q.options.map((o) => o.option_id === optionId ? { ...o, text: value } : o) };
      }),
    });
  }

  return (
    <div className="space-y-6">
      {draft.questions.map((q, qi) => (
        <div key={q.question_id} className="space-y-4 rounded-lg border border-gray-200 bg-gray-50 p-4">
          <div className="flex items-center gap-2">
            <span className="flex h-6 w-6 items-center justify-center rounded-full bg-indigo-100 text-xs font-bold text-indigo-700">
              {qi + 1}
            </span>
            <select value={q.difficulty} disabled={readOnly}
              onChange={(e) => updateQuestion(qi, "difficulty", e.target.value)}
              className="ml-auto rounded border border-gray-200 bg-white px-2 py-1 text-xs text-gray-600 focus:border-indigo-400 focus:outline-none disabled:bg-gray-50">
              <option value="easy">Easy</option>
              <option value="medium">Medium</option>
              <option value="hard">Hard</option>
            </select>
          </div>

          <div>
            <label className="mb-1 block text-xs text-gray-500">Question</label>
            <textarea rows={2} className={TA} value={q.question_text} disabled={readOnly}
              onChange={(e) => updateQuestion(qi, "question_text", e.target.value)}
              placeholder="Enter the question…" />
          </div>

          <div className="space-y-2">
            <label className="block text-xs text-gray-500">Options — select the correct answer</label>
            {q.options.map((opt) => (
              <div key={opt.option_id} className="flex items-center gap-2">
                <input type="radio"
                  name={`correct-${qi}-${q.question_id}`}
                  value={opt.option_id}
                  checked={q.correct_option === opt.option_id}
                  disabled={readOnly}
                  onChange={() => updateQuestion(qi, "correct_option", opt.option_id)}
                  className="h-4 w-4 text-indigo-600 focus:ring-indigo-500" />
                <span className="w-5 text-xs font-bold text-gray-500">{opt.option_id}</span>
                <input type="text"
                  className="flex-1 rounded border border-gray-200 bg-white px-2 py-1.5 text-sm text-gray-900 shadow-sm placeholder:text-gray-400 focus:border-indigo-400 focus:outline-none disabled:bg-gray-50 disabled:text-gray-500"
                  value={opt.text} disabled={readOnly}
                  onChange={(e) => updateOption(qi, opt.option_id, e.target.value)}
                  placeholder={`Option ${opt.option_id}…`} />
              </div>
            ))}
          </div>

          <div>
            <label className="mb-1 block text-xs text-gray-500">Explanation (shown after answering)</label>
            <textarea rows={2} className={TA} value={q.explanation} disabled={readOnly}
              onChange={(e) => updateQuestion(qi, "explanation", e.target.value)}
              placeholder="Explain why the correct answer is correct…" />
          </div>
        </div>
      ))}
    </div>
  );
}

// ── Experiment ────────────────────────────────────────────────────────────────

interface ExperimentStep {
  step_number: number;
  instruction: string;
  expected_observation: string;
}

interface ExperimentQA {
  question: string;
  answer: string;
}

interface ExperimentDraft {
  experiment_title: string;
  materials: string;    // joined with \n
  safety_notes: string; // joined with \n
  steps: ExperimentStep[];
  questions: ExperimentQA[];
  conclusion_prompt: string;
}

function experimentBodyToForm(body: Record<string, unknown>): ExperimentDraft {
  const rawSteps = (body.steps as Record<string, unknown>[] | undefined) ?? [];
  const rawQs = (body.questions as Record<string, unknown>[] | undefined) ?? [];
  return {
    experiment_title: (body.experiment_title as string) ?? "",
    materials: ((body.materials as string[]) ?? []).join("\n"),
    safety_notes: ((body.safety_notes as string[]) ?? []).join("\n"),
    steps:
      rawSteps.length > 0
        ? rawSteps.map((s) => ({
            step_number: (s.step_number as number) ?? 0,
            instruction: (s.instruction as string) ?? "",
            expected_observation: (s.expected_observation as string) ?? "",
          }))
        : [{ step_number: 1, instruction: "", expected_observation: "" }],
    questions:
      rawQs.length > 0
        ? rawQs.map((q) => ({
            question: (q.question as string) ?? "",
            answer: (q.answer as string) ?? "",
          }))
        : [{ question: "", answer: "" }],
    conclusion_prompt: (body.conclusion_prompt as string) ?? "",
  };
}

function formToExperimentBody(
  original: Record<string, unknown>,
  form: ExperimentDraft,
): Record<string, unknown> {
  return {
    ...original,
    experiment_title: form.experiment_title,
    materials: form.materials.split("\n").map((s) => s.trim()).filter(Boolean),
    safety_notes: form.safety_notes.split("\n").map((s) => s.trim()).filter(Boolean),
    steps: form.steps,
    questions: form.questions,
    conclusion_prompt: form.conclusion_prompt,
  };
}

function ExperimentEditor({
  draft,
  onChange,
  readOnly,
}: {
  draft: ExperimentDraft;
  onChange: (d: ExperimentDraft) => void;
  readOnly: boolean;
}) {
  function updateStep(i: number, field: keyof Omit<ExperimentStep, "step_number">, value: string) {
    onChange({ ...draft, steps: draft.steps.map((s, idx) => idx === i ? { ...s, [field]: value } : s) });
  }

  function addStep() {
    onChange({ ...draft, steps: [...draft.steps, { step_number: draft.steps.length + 1, instruction: "", expected_observation: "" }] });
  }

  function removeStep(i: number) {
    onChange({ ...draft, steps: draft.steps.filter((_, idx) => idx !== i).map((s, idx) => ({ ...s, step_number: idx + 1 })) });
  }

  function updateQuestion(i: number, field: keyof ExperimentQA, value: string) {
    onChange({ ...draft, questions: draft.questions.map((q, idx) => idx === i ? { ...q, [field]: value } : q) });
  }

  return (
    <div className="space-y-6">
      <div>
        <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-gray-500">Experiment title</label>
        <input type="text"
          className="w-full rounded-md border border-gray-200 bg-white px-3 py-2 text-sm font-medium text-gray-900 shadow-sm placeholder:text-gray-400 focus:border-indigo-400 focus:outline-none focus:ring-1 focus:ring-indigo-400 disabled:bg-gray-50 disabled:text-gray-500"
          value={draft.experiment_title} disabled={readOnly}
          onChange={(e) => onChange({ ...draft, experiment_title: e.target.value })}
          placeholder="Experiment title…" />
      </div>

      <div>
        <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-gray-500">
          Materials <span className="font-normal normal-case text-gray-400">(one per line)</span>
        </label>
        <textarea rows={4} className={TA} value={draft.materials} disabled={readOnly}
          onChange={(e) => onChange({ ...draft, materials: e.target.value })}
          placeholder="Each material item on its own line…" />
      </div>

      <div>
        <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-gray-500">
          Safety notes <span className="font-normal normal-case text-gray-400">(one per line)</span>
        </label>
        <textarea rows={3} className={TA} value={draft.safety_notes} disabled={readOnly}
          onChange={(e) => onChange({ ...draft, safety_notes: e.target.value })}
          placeholder="Each safety precaution on its own line…" />
      </div>

      <div>
        <div className="mb-2 flex items-center justify-between">
          <label className="text-xs font-semibold uppercase tracking-wide text-gray-500">Procedure steps</label>
          {!readOnly && (
            <button type="button" onClick={addStep} className="text-xs font-medium text-indigo-600 hover:underline">+ Add step</button>
          )}
        </div>
        <div className="space-y-4">
          {draft.steps.map((step, i) => (
            <div key={i} className="space-y-3 rounded-lg border border-gray-200 bg-gray-50 p-4">
              <div className="flex items-center gap-2">
                <span className="flex h-6 w-6 items-center justify-center rounded-full bg-blue-100 text-xs font-bold text-blue-700">
                  {step.step_number}
                </span>
                {!readOnly && draft.steps.length > 1 && (
                  <button type="button" onClick={() => removeStep(i)}
                    className="ml-auto text-xs text-gray-400 hover:text-red-500">Remove</button>
                )}
              </div>
              <div>
                <label className="mb-1 block text-xs text-gray-500">Instruction</label>
                <textarea rows={2} className={TA} value={step.instruction} disabled={readOnly}
                  onChange={(e) => updateStep(i, "instruction", e.target.value)}
                  placeholder="What should the student do…" />
              </div>
              <div>
                <label className="mb-1 block text-xs text-gray-500">Expected observation</label>
                <textarea rows={2} className={TA} value={step.expected_observation} disabled={readOnly}
                  onChange={(e) => updateStep(i, "expected_observation", e.target.value)}
                  placeholder="What should the student observe…" />
              </div>
            </div>
          ))}
        </div>
      </div>

      <div>
        <div className="mb-2 flex items-center justify-between">
          <label className="text-xs font-semibold uppercase tracking-wide text-gray-500">Reflection questions</label>
          {!readOnly && (
            <button type="button"
              onClick={() => onChange({ ...draft, questions: [...draft.questions, { question: "", answer: "" }] })}
              className="text-xs font-medium text-indigo-600 hover:underline">+ Add question</button>
          )}
        </div>
        <div className="space-y-4">
          {draft.questions.map((q, i) => (
            <div key={i} className="space-y-3 rounded-lg border border-gray-200 bg-gray-50 p-4">
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold text-gray-400">Q{i + 1}</span>
                {!readOnly && draft.questions.length > 1 && (
                  <button type="button"
                    onClick={() => onChange({ ...draft, questions: draft.questions.filter((_, idx) => idx !== i) })}
                    className="ml-auto text-xs text-gray-400 hover:text-red-500">Remove</button>
                )}
              </div>
              <div>
                <label className="mb-1 block text-xs text-gray-500">Question</label>
                <textarea rows={2} className={TA} value={q.question} disabled={readOnly}
                  onChange={(e) => updateQuestion(i, "question", e.target.value)}
                  placeholder="Reflection question…" />
              </div>
              <div>
                <label className="mb-1 block text-xs text-gray-500">Expected answer</label>
                <textarea rows={2} className={TA} value={q.answer} disabled={readOnly}
                  onChange={(e) => updateQuestion(i, "answer", e.target.value)}
                  placeholder="The ideal answer or key points…" />
              </div>
            </div>
          ))}
        </div>
      </div>

      <div>
        <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-gray-500">Conclusion prompt</label>
        <textarea rows={3} className={TA} value={draft.conclusion_prompt} disabled={readOnly}
          onChange={(e) => onChange({ ...draft, conclusion_prompt: e.target.value })}
          placeholder="Prompt students to write their conclusion…" />
      </div>
    </div>
  );
}

// ── Shared UI ─────────────────────────────────────────────────────────────────

const STATUS_STYLES: Record<string, string> = {
  draft: "bg-orange-50 text-orange-700 border border-orange-200",
  pending_review: "bg-blue-50 text-blue-700 border border-blue-200",
  approved: "bg-green-50 text-green-700 border border-green-200",
  rejected: "bg-red-50 text-red-700 border border-red-200",
};

const STATUS_LABELS: Record<string, string> = {
  draft: "Draft",
  pending_review: "Pending review",
  approved: "Approved",
  rejected: "Rejected",
};

function StatusBadge({ status }: { status: string }) {
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${STATUS_STYLES[status] ?? "bg-gray-100 text-gray-500"}`}>
      {STATUS_LABELS[status] ?? status}
    </span>
  );
}

const CONTENT_TYPE_LABELS: Record<string, string> = {
  lesson: "Lesson",
  tutorial: "Tutorial",
  quiz_set_1: "Quiz 1",
  quiz_set_2: "Quiz 2",
  quiz_set_3: "Quiz 3",
  experiment: "Experiment",
};

// ── Page ──────────────────────────────────────────────────────────────────────

export default function UnitEditPage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const router = useRouter();
  const curriculumId = params.curriculum_id as string;
  const unitId = params.unit_id as string;
  const adoptionId = searchParams.get("aid") ?? "";

  const teacher = useTeacher();
  const schoolId = teacher?.school_id ?? "";
  const queryClient = useQueryClient();

  const [activeType, setActiveType] = useState<string>("lesson");

  // Per-type draft state
  const [lessonDraft, setLessonDraft] = useState<LessonDraft | null>(null);
  const [lessonOriginalBody, setLessonOriginalBody] = useState<Record<string, unknown> | null>(null);
  const [tutorialDraft, setTutorialDraft] = useState<TutorialDraft | null>(null);
  const [tutorialOriginalBody, setTutorialOriginalBody] = useState<Record<string, unknown> | null>(null);
  const [quizDraft, setQuizDraft] = useState<QuizDraft | null>(null);
  const [quizOriginalBody, setQuizOriginalBody] = useState<Record<string, unknown> | null>(null);
  const [experimentDraft, setExperimentDraft] = useState<ExperimentDraft | null>(null);
  const [experimentOriginalBody, setExperimentOriginalBody] = useState<Record<string, unknown> | null>(null);

  const [dirty, setDirty] = useState(false);
  const [notice, setNotice] = useState<{ kind: "success" | "error"; msg: string } | null>(null);
  const [rejectReason, setRejectReason] = useState("");
  const [showRejectBox, setShowRejectBox] = useState(false);

  // 1. List all overrides for this unit (tab availability)
  const { data: unitData, isLoading: unitsLoading } = useQuery({
    queryKey: ["unit-status", schoolId, curriculumId],
    queryFn: () => listUnitOverrideStatus(schoolId, curriculumId),
    enabled: !!schoolId && !!curriculumId,
    staleTime: 30_000,
  });

  const unitMeta = unitData?.units.find((u) => u.unit_id === unitId);
  const overridesByType = Object.fromEntries(
    (unitMeta?.overrides ?? []).map((o) => [o.content_type, o]),
  ) as Record<string, UnitOverrideStatus>;
  const availableTypes = Object.keys(overridesByType).filter((t) => t in CONTENT_TYPE_LABELS);

  useEffect(() => {
    if (availableTypes.length > 0 && !availableTypes.includes(activeType)) {
      setActiveType(availableTypes[0]);
    }
  }, [availableTypes.join(",")]);

  // 2. Fetch body for active content type
  const { data: overrideDetail, isLoading: detailLoading, refetch: refetchDetail } = useQuery({
    queryKey: ["override-detail", schoolId, curriculumId, unitId, activeType],
    queryFn: () => getUnitOverride(schoolId, curriculumId, unitId, activeType),
    enabled: !!schoolId && !!curriculumId && !!unitId && availableTypes.includes(activeType),
    staleTime: 0,
  });

  // Populate form when detail loads
  useEffect(() => {
    if (!overrideDetail) return;
    const body = overrideDetail.body;
    if (activeType === "lesson") {
      setLessonDraft(lessonBodyToForm(body));
      setLessonOriginalBody(body);
    } else if (activeType === "tutorial") {
      setTutorialDraft(tutorialBodyToForm(body));
      setTutorialOriginalBody(body);
    } else if (activeType.startsWith("quiz_set_")) {
      setQuizDraft(quizBodyToForm(body));
      setQuizOriginalBody(body);
    } else if (activeType === "experiment") {
      setExperimentDraft(experimentBodyToForm(body));
      setExperimentOriginalBody(body);
    }
    setDirty(false);
  }, [overrideDetail, activeType]);

  const readOnly =
    overrideDetail?.review_status === "pending_review" ||
    overrideDetail?.review_status === "approved";

  // 3. Save draft
  const saveMutation = useMutation({
    mutationFn: () => {
      if (activeType === "lesson" && lessonDraft && lessonOriginalBody)
        return saveDraft(schoolId, curriculumId, unitId, activeType, formToLessonBody(lessonOriginalBody, lessonDraft));
      if (activeType === "tutorial" && tutorialDraft && tutorialOriginalBody)
        return saveDraft(schoolId, curriculumId, unitId, activeType, formToTutorialBody(tutorialOriginalBody, tutorialDraft));
      if (activeType.startsWith("quiz_set_") && quizDraft && quizOriginalBody)
        return saveDraft(schoolId, curriculumId, unitId, activeType, formToQuizBody(quizOriginalBody, quizDraft));
      if (activeType === "experiment" && experimentDraft && experimentOriginalBody)
        return saveDraft(schoolId, curriculumId, unitId, activeType, formToExperimentBody(experimentOriginalBody, experimentDraft));
      return Promise.reject(new Error("Nothing to save"));
    },
    onSuccess: () => {
      setDirty(false);
      setNotice({ kind: "success", msg: "Draft saved." });
      queryClient.invalidateQueries({ queryKey: ["unit-status", schoolId, curriculumId] });
      refetchDetail();
      setTimeout(() => setNotice(null), 3000);
    },
    onError: (err: Error) => setNotice({ kind: "error", msg: err.message || "Save failed." }),
  });

  // 4. Submit for review (scoped to active type)
  const reviewMutation = useMutation({
    mutationFn: () => submitForReview(schoolId, curriculumId, unitId, activeType),
    onSuccess: () => {
      const label = CONTENT_TYPE_LABELS[activeType] ?? activeType;
      setNotice({ kind: "success", msg: `${label} submitted for review.` });
      queryClient.invalidateQueries({ queryKey: ["unit-status", schoolId, curriculumId] });
      refetchDetail();
    },
    onError: (err: Error) => setNotice({ kind: "error", msg: err.message || "Submission failed." }),
  });

  // 5. Approve (school_admin only)
  const approveMutation = useMutation({
    mutationFn: () => {
      const ok = window.confirm("Approve and publish this content? It will be immediately visible to students.");
      if (!ok) return Promise.reject(new Error("cancelled"));
      return approveUnitContent(schoolId, curriculumId, unitId, true);
    },
    onSuccess: (data) => {
      setNotice({ kind: "success", msg: `Approved and published ${data.published} content item${data.published !== 1 ? "s" : ""}.` });
      queryClient.invalidateQueries({ queryKey: ["unit-status", schoolId, curriculumId] });
      refetchDetail();
    },
    onError: (err: Error) => {
      if (err.message !== "cancelled")
        setNotice({ kind: "error", msg: err.message || "Approval failed." });
    },
  });

  // 6. Reject (school_admin only)
  const rejectMutation = useMutation({
    mutationFn: () => rejectUnitContent(schoolId, curriculumId, unitId, rejectReason),
    onSuccess: () => {
      setNotice({ kind: "success", msg: "Rejected — teacher can revise and resubmit." });
      setShowRejectBox(false);
      setRejectReason("");
      queryClient.invalidateQueries({ queryKey: ["unit-status", schoolId, curriculumId] });
      refetchDetail();
    },
    onError: (err: Error) => setNotice({ kind: "error", msg: err.message || "Rejection failed." }),
  });

  const currentStatus = overrideDetail?.review_status;
  const canSubmit = currentStatus === "draft" || currentStatus === "rejected";
  const canSave =
    !readOnly &&
    ((activeType === "lesson" && !!lessonDraft) ||
      (activeType === "tutorial" && !!tutorialDraft) ||
      (activeType.startsWith("quiz_set_") && !!quizDraft) ||
      (activeType === "experiment" && !!experimentDraft));
  const isAdmin = teacher?.role === "school_admin";
  const canApprove = isAdmin && currentStatus === "pending_review";

  const backHref = adoptionId
    ? `/school/content/${curriculumId}?aid=${adoptionId}`
    : `/school/content/${curriculumId}`;

  function switchTab(ct: string) {
    if (dirty && !confirm("You have unsaved changes. Discard and switch tab?")) return;
    setActiveType(ct);
    setDirty(false);
    setLessonDraft(null);
    setTutorialDraft(null);
    setQuizDraft(null);
    setExperimentDraft(null);
  }

  return (
    <div className="max-w-4xl space-y-6 p-6">
      {/* Header */}
      <div className="flex items-start gap-4">
        <button type="button" onClick={() => router.push(backHref)}
          className="mt-0.5 rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600" aria-label="Back">
          <ArrowLeft className="h-4 w-4" />
        </button>

        <div className="flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <BookOpen className="h-5 w-5 text-indigo-600" />
            <h1 className="text-xl font-bold text-gray-900">{unitMeta?.title ?? unitId}</h1>
            {unitMeta?.subject_name && (
              <span className="rounded-full bg-indigo-50 px-2 py-0.5 text-xs font-medium text-indigo-700">
                {unitMeta.subject_name}
              </span>
            )}
            {currentStatus && <StatusBadge status={currentStatus} />}
          </div>
          <p className="mt-1 text-sm text-gray-500">
            {overrideDetail?.last_edited_by_name ? `Last edited by ${overrideDetail.last_edited_by_name}` : "Not yet edited"}
            {overrideDetail?.edited_at ? ` · ${new Date(overrideDetail.edited_at).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" })}` : ""}
            {overrideDetail?.version_number !== undefined ? ` · v${overrideDetail.version_number}` : ""}
          </p>
        </div>

        {/* Actions */}
        <div className="flex shrink-0 items-center gap-2">
          {canSave && (
            <button type="button" onClick={() => saveMutation.mutate()}
              disabled={saveMutation.isPending || !dirty}
              className="inline-flex items-center gap-1.5 rounded-md bg-white px-3 py-1.5 text-sm font-medium text-gray-700 shadow-sm ring-1 ring-gray-200 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50">
              <Save className="h-4 w-4" />
              {saveMutation.isPending ? "Saving…" : "Save draft"}
            </button>
          )}
          {canSubmit && (
            <button type="button" onClick={() => reviewMutation.mutate()}
              disabled={reviewMutation.isPending || dirty}
              title={dirty ? "Save your changes before submitting" : undefined}
              className="inline-flex items-center gap-1.5 rounded-md bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white shadow-sm hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50">
              <Send className="h-4 w-4" />
              {reviewMutation.isPending ? "Submitting…" : `Submit ${CONTENT_TYPE_LABELS[activeType] ?? activeType} for review`}
            </button>
          )}
          {canApprove && (
            <>
              <button type="button" onClick={() => setShowRejectBox((v) => !v)}
                disabled={rejectMutation.isPending}
                className="inline-flex items-center gap-1.5 rounded-md bg-white px-3 py-1.5 text-sm font-medium text-red-600 shadow-sm ring-1 ring-red-200 hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-50">
                <ThumbsDown className="h-4 w-4" />
                Reject
              </button>
              <button type="button" onClick={() => approveMutation.mutate()}
                disabled={approveMutation.isPending}
                className="inline-flex items-center gap-1.5 rounded-md bg-green-600 px-3 py-1.5 text-sm font-medium text-white shadow-sm hover:bg-green-700 disabled:cursor-not-allowed disabled:opacity-50">
                <ThumbsUp className="h-4 w-4" />
                {approveMutation.isPending ? "Approving…" : "Approve & publish"}
              </button>
            </>
          )}
        </div>
      </div>

      {/* Notice */}
      {notice && (
        <div className={`flex items-center gap-2 rounded-md border px-4 py-2.5 text-sm ${notice.kind === "success" ? "border-green-200 bg-green-50 text-green-800" : "border-red-200 bg-red-50 text-red-700"}`}>
          {notice.kind === "success" ? <CheckCircle2 className="h-4 w-4 shrink-0" /> : <AlertCircle className="h-4 w-4 shrink-0" />}
          {notice.msg}
        </div>
      )}

      {/* Rejection reason — shown to teacher */}
      {currentStatus === "rejected" && overrideDetail?.rejection_reason && (
        <div className="flex gap-3 rounded-lg border border-red-200 bg-red-50 px-4 py-3">
          <ThumbsDown className="mt-0.5 h-4 w-4 shrink-0 text-red-500" />
          <div>
            <p className="text-sm font-semibold text-red-800">Returned for revision</p>
            <p className="mt-0.5 text-sm text-red-700">{overrideDetail.rejection_reason}</p>
          </div>
        </div>
      )}

      {/* Reject reason box (admin) */}
      {showRejectBox && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4">
          <p className="mb-2 text-sm font-medium text-red-800">Reason for rejection</p>
          <textarea rows={3}
            className="w-full rounded-md border border-red-200 bg-white px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-red-400 focus:outline-none focus:ring-1 focus:ring-red-400"
            placeholder="Tell the teacher what needs to be revised…"
            value={rejectReason} onChange={(e) => setRejectReason(e.target.value)} />
          <div className="mt-2 flex items-center gap-2">
            <button type="button" onClick={() => rejectMutation.mutate()}
              disabled={rejectMutation.isPending || !rejectReason.trim()}
              className="inline-flex items-center gap-1.5 rounded-md bg-red-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-red-700 disabled:cursor-not-allowed disabled:opacity-50">
              {rejectMutation.isPending ? "Rejecting…" : "Confirm rejection"}
            </button>
            <button type="button" onClick={() => { setShowRejectBox(false); setRejectReason(""); }}
              className="text-sm text-gray-500 hover:text-gray-700">Cancel</button>
          </div>
        </div>
      )}

      {/* Pending review banner */}
      {currentStatus === "pending_review" && (
        <div className="flex items-center gap-2 rounded-md border border-blue-200 bg-blue-50 px-4 py-2.5 text-sm text-blue-800">
          <Clock className="h-4 w-4 shrink-0" />
          This unit is pending review and cannot be edited until the review is complete.
        </div>
      )}

      {/* Unsaved changes warning */}
      {dirty && (
        <div className="flex items-center gap-2 rounded-md border border-yellow-200 bg-yellow-50 px-4 py-2.5 text-sm text-yellow-800">
          <AlertCircle className="h-4 w-4 shrink-0" />
          You have unsaved changes — save before submitting for review.
        </div>
      )}

      {/* Main content */}
      {unitsLoading && availableTypes.length === 0 ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-20 animate-pulse rounded-lg bg-gray-100" />
          ))}
        </div>
      ) : availableTypes.length === 0 ? (
        <div className="flex flex-col items-center gap-3 rounded-lg border border-dashed border-gray-200 py-12 text-center">
          <BookOpen className="h-8 w-8 text-gray-300" />
          <p className="text-sm font-medium text-gray-500">No content imported yet</p>
          <p className="max-w-xs text-xs text-gray-400">
            Go back and use the Import button to pull this unit&apos;s content into your workspace.
          </p>
          <button type="button" onClick={() => router.push(backHref)}
            className="mt-2 rounded-md bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700">
            Back to unit list
          </button>
        </div>
      ) : (
        <div className="rounded-lg border border-gray-200 bg-white shadow-sm">
          {/* Content type tabs */}
          {availableTypes.length > 1 && (
            <div className="flex gap-0 border-b border-gray-200">
              {availableTypes.map((ct) => (
                <button key={ct} type="button" onClick={() => switchTab(ct)}
                  className={`px-4 py-2.5 text-sm font-medium transition-colors ${activeType === ct ? "border-b-2 border-indigo-600 text-indigo-700" : "text-gray-500 hover:text-gray-700"}`}>
                  {CONTENT_TYPE_LABELS[ct] ?? ct}
                  {overridesByType[ct] && (
                    <span className={`ml-1.5 inline-flex items-center rounded-full px-1.5 py-0.5 text-xs font-medium ${STATUS_STYLES[overridesByType[ct].review_status] ?? "bg-gray-100 text-gray-500"}`}>
                      {STATUS_LABELS[overridesByType[ct].review_status] ?? overridesByType[ct].review_status}
                    </span>
                  )}
                </button>
              ))}
            </div>
          )}

          {/* Editor body */}
          <div className="p-6">
            {detailLoading ? (
              <div className="space-y-3 py-4">
                {[1, 2, 3].map((i) => <div key={i} className="h-16 animate-pulse rounded-lg bg-gray-100" />)}
              </div>
            ) : activeType === "lesson" && lessonDraft ? (
              <LessonEditor draft={lessonDraft}
                onChange={(d) => { setLessonDraft(d); setDirty(true); }}
                readOnly={readOnly} />
            ) : activeType === "tutorial" && tutorialDraft ? (
              <TutorialEditor draft={tutorialDraft}
                onChange={(d) => { setTutorialDraft(d); setDirty(true); }}
                readOnly={readOnly} />
            ) : activeType.startsWith("quiz_set_") && quizDraft ? (
              <QuizEditor draft={quizDraft}
                onChange={(d) => { setQuizDraft(d); setDirty(true); }}
                readOnly={readOnly} />
            ) : activeType === "experiment" && experimentDraft ? (
              <ExperimentEditor draft={experimentDraft}
                onChange={(d) => { setExperimentDraft(d); setDirty(true); }}
                readOnly={readOnly} />
            ) : (
              <div className="py-12 text-center text-sm text-gray-400">Loading content…</div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
