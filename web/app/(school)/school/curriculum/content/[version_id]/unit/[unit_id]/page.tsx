"use client";

import { useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { SBMarkdown } from "@/components/content/Markdown";
import { useTeacher } from "@/lib/hooks/useTeacher";
import { getSchoolUnitMeta, getSchoolUnitContent } from "@/lib/api/school-admin";
import { Skeleton } from "@/components/ui/skeleton";
import {
  ArrowLeft,
  BookOpen,
  GraduationCap,
  ClipboardList,
  FlaskConical,
  MessageSquare,
} from "lucide-react";
import { cn } from "@/lib/utils";

// ── Type metadata ─────────────────────────────────────────────────────────────

const TYPE_META: Record<string, { label: string; icon: React.ReactNode }> = {
  lesson: { label: "Lesson", icon: <BookOpen className="h-4 w-4" /> },
  tutorial: { label: "Tutorial", icon: <GraduationCap className="h-4 w-4" /> },
  quiz_set_1: { label: "Quiz Set 1", icon: <ClipboardList className="h-4 w-4" /> },
  quiz_set_2: { label: "Quiz Set 2", icon: <ClipboardList className="h-4 w-4" /> },
  quiz_set_3: { label: "Quiz Set 3", icon: <ClipboardList className="h-4 w-4" /> },
  experiment: { label: "Experiment", icon: <FlaskConical className="h-4 w-4" /> },
};

// ── Shared prose renderer ─────────────────────────────────────────────────────
// Thin alias kept for callsite compatibility; real rendering lives in
// components/content/Markdown.tsx (Epic 11 C-3).

function Prose({ text, className }: { text: string; className?: string }) {
  return <SBMarkdown className={className}>{text}</SBMarkdown>;
}

// ── Annotations panel ─────────────────────────────────────────────────────────

interface AnnotationItem {
  annotation_id: string;
  content_type: string;
  annotation_text: string;
  created_at: string;
  reviewer_email: string | null;
}

function AnnotationsPanel({ annotations, activeType }: { annotations: AnnotationItem[]; activeType: string }) {
  const relevant = annotations.filter(a => a.content_type.includes(activeType));
  if (relevant.length === 0) return null;

  return (
    <div className="mt-6 rounded-lg border border-amber-200 bg-amber-50 p-4">
      <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-amber-800">
        <MessageSquare className="h-4 w-4" />
        Review Notes ({relevant.length})
      </h3>
      <div className="space-y-2">
        {relevant.map(a => (
          <div key={a.annotation_id} className="rounded-md border border-amber-100 bg-white px-3 py-2">
            <p className="text-sm text-gray-800 whitespace-pre-wrap">{a.annotation_text}</p>
            <p className="mt-1 text-xs text-gray-400">
              {a.reviewer_email ?? "Reviewer"} · {new Date(a.created_at).toLocaleDateString()}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Content renderers (read-only — no annotation controls) ────────────────────

function LessonRenderer({ data }: { data: Record<string, unknown> }) {
  const sections = (data.sections ?? []) as Array<{ heading: string; body: string }>;
  const keyPoints = (data.key_points ?? []) as string[];

  return (
    <div className="space-y-6">
      {sections.map((s, i) => (
        <div key={i} className="border-b border-gray-50 pb-5 last:border-0 last:pb-0">
          <h3 className="mb-1.5 text-sm font-semibold text-gray-800">{s.heading}</h3>
          <Prose text={s.body} />
        </div>
      ))}
      {keyPoints.length > 0 && (
        <div className="rounded-lg border border-indigo-100 bg-indigo-50 p-4">
          <h3 className="mb-2 text-sm font-semibold text-indigo-800">Key Points</h3>
          <ul className="space-y-1.5">
            {keyPoints.map((kp, i) => (
              <li key={i} className="flex gap-2.5 text-sm text-indigo-700">
                <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-indigo-400" />
                {kp}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function TutorialRenderer({ data }: { data: Record<string, unknown> }) {
  const sections = (data.sections ?? []) as Array<{
    section_id?: string;
    title: string;
    content: string;
    examples?: string[];
    practice_question?: string;
  }>;
  const mistakes = (data.common_mistakes ?? []) as string[];

  const tabs = [
    ...sections.map((s, i) => ({ key: s.section_id ?? String(i), label: s.title })),
    ...(mistakes.length > 0 ? [{ key: "__mistakes__", label: "Common Mistakes" }] : []),
  ];

  const [activeTab, setActiveTab] = useState<string>(tabs[0]?.key ?? "");
  const activeSection = sections.find((s, i) => (s.section_id ?? String(i)) === activeTab);

  return (
    <div>
      <div className="mb-4 flex flex-wrap gap-1 border-b border-gray-200">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={cn(
              "-mb-px rounded-t-md border-b-2 px-3 py-2 text-xs font-medium transition-colors",
              activeTab === tab.key
                ? tab.key === "__mistakes__"
                  ? "border-red-500 bg-red-50 text-red-600"
                  : "border-indigo-500 bg-indigo-50 text-indigo-700"
                : "border-transparent text-gray-500 hover:bg-gray-50 hover:text-gray-800",
            )}
          >
            {tab.key === "__mistakes__" ? "⚠ Common Mistakes" : tab.label}
          </button>
        ))}
      </div>

      {activeTab === "__mistakes__" ? (
        <ul className="space-y-2">
          {mistakes.map((m, i) => (
            <li key={i} className="flex gap-2 rounded-md bg-red-50 px-3 py-2 text-sm text-red-600">
              <span className="shrink-0">⚠</span>
              <span>{m}</span>
            </li>
          ))}
        </ul>
      ) : activeSection ? (
        <div className="space-y-4">
          <Prose text={activeSection.content} />
          {activeSection.examples && activeSection.examples.length > 0 && (
            <div className="space-y-2">
              <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">
                Examples
              </p>
              {activeSection.examples.map((ex, j) => (
                <div
                  key={j}
                  className="rounded-md border border-gray-100 bg-gray-50 p-3"
                >
                  <SBMarkdown className="text-xs text-gray-800">{ex}</SBMarkdown>
                </div>
              ))}
            </div>
          )}
          {activeSection.practice_question && (
            <div className="rounded-md border border-indigo-100 bg-indigo-50 px-3 py-2">
              <p className="mb-1 text-xs font-semibold text-indigo-500">Practice</p>
              <p className="text-xs text-indigo-700">{activeSection.practice_question}</p>
            </div>
          )}
        </div>
      ) : null}
    </div>
  );
}

function QuizRenderer({ data }: { data: Record<string, unknown> }) {
  const setNumber = data.set_number as number | undefined;
  const questions = (data.questions ?? []) as Array<{
    question_id: string;
    question_text: string;
    options: Array<{ option_id: string; text: string }>;
    correct_option: string;
    explanation?: string;
    difficulty?: string;
  }>;

  return (
    <div className="space-y-5">
      {setNumber && (
        <p className="text-xs font-medium uppercase tracking-wide text-gray-400">
          Quiz Set {setNumber} · {questions.length} questions
        </p>
      )}
      {questions.map((q, i) => (
        <div
          key={q.question_id ?? i}
          className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm"
        >
          <div className="mb-3 flex gap-2">
            <span className="mt-0.5 shrink-0 font-mono text-xs text-gray-400">Q{i + 1}.</span>
            <Prose text={q.question_text} className="flex-1" />
          </div>
          <ul className="space-y-1.5">
            {q.options.map((opt) => (
              <li
                key={opt.option_id}
                className={cn(
                  "flex items-start gap-2 rounded-md px-3 py-2 text-sm",
                  opt.option_id === q.correct_option
                    ? "bg-green-50 font-medium text-green-800"
                    : "bg-gray-50 text-gray-700",
                )}
              >
                <span className="mt-0.5 shrink-0 font-mono text-xs text-gray-400">
                  {opt.option_id}.
                </span>
                <span className="flex-1">{opt.text}</span>
                {opt.option_id === q.correct_option && (
                  <span className="ml-auto shrink-0 text-xs text-green-600">✓ correct</span>
                )}
              </li>
            ))}
          </ul>
          {q.explanation && (
            <div className="mt-3 rounded bg-amber-50 px-3 py-2">
              <p className="mb-1 text-xs font-semibold text-amber-600">Explanation</p>
              <Prose text={q.explanation} className="text-xs text-amber-700" />
            </div>
          )}
          {q.difficulty && (
            <p className="mt-2 text-xs text-gray-400">Difficulty: {q.difficulty}</p>
          )}
        </div>
      ))}
    </div>
  );
}

function ExperimentRenderer({ data }: { data: Record<string, unknown> }) {
  const materials = (data.materials ?? []) as string[];
  const steps = (data.steps ?? []) as Array<{ step?: number; instruction: string }>;
  const safety = (data.safety_notes ?? []) as string[];
  const outcome = data.expected_outcome as string | undefined;

  return (
    <div className="space-y-6">
      {materials.length > 0 && (
        <div>
          <h3 className="mb-2 text-sm font-semibold text-gray-800">Materials</h3>
          <ul className="grid grid-cols-2 gap-1">
            {materials.map((m, i) => (
              <li key={i} className="text-sm text-gray-700">• {m}</li>
            ))}
          </ul>
        </div>
      )}
      {steps.length > 0 && (
        <div>
          <h3 className="mb-2 text-sm font-semibold text-gray-800">Steps</h3>
          <ol className="space-y-3">
            {steps.map((s, i) => (
              <li key={i} className="rounded-lg border border-gray-100 bg-gray-50 p-3">
                <div className="flex gap-3">
                  <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-indigo-100 text-xs font-semibold text-indigo-700">
                    {s.step ?? i + 1}
                  </span>
                  <Prose text={s.instruction} className="flex-1" />
                </div>
              </li>
            ))}
          </ol>
        </div>
      )}
      {safety.length > 0 && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4">
          <h3 className="mb-2 text-sm font-semibold text-red-700">Safety Notes</h3>
          <ul className="space-y-1">
            {safety.map((n, i) => (
              <li key={i} className="flex gap-2 text-sm text-red-600">
                <span className="shrink-0">⚠</span>
                <span>{n}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
      {outcome && (
        <div>
          <h3 className="mb-1 text-sm font-semibold text-gray-800">Expected Outcome</h3>
          <Prose text={outcome} />
        </div>
      )}
    </div>
  );
}

function ContentRenderer({
  contentType,
  data,
}: {
  contentType: string;
  data: Record<string, unknown>;
}) {
  if (contentType === "lesson") return <LessonRenderer data={data} />;
  if (contentType === "tutorial") return <TutorialRenderer data={data} />;
  if (contentType.startsWith("quiz_set")) return <QuizRenderer data={data} />;
  if (contentType === "experiment") return <ExperimentRenderer data={data} />;
  return (
    <pre className="overflow-x-auto rounded-lg bg-gray-50 p-4 text-xs text-gray-700">
      {JSON.stringify(data, null, 2)}
    </pre>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function SchoolUnitContentPage() {
  const { version_id, unit_id } = useParams<{ version_id: string; unit_id: string }>();
  const teacher = useTeacher();
  const schoolId = teacher?.school_id ?? "";

  const [activeType, setActiveType] = useState<string | null>(null);

  const { data: meta, isLoading: metaLoading } = useQuery({
    queryKey: ["school-unit-meta", schoolId, version_id, unit_id],
    queryFn: () => getSchoolUnitMeta(schoolId, version_id, unit_id),
    enabled: !!schoolId && !!version_id && !!unit_id,
    staleTime: 60_000,
  });

  const resolvedType = activeType ?? meta?.available_types[0] ?? null;

  const { data: contentFile, isLoading: fileLoading } = useQuery({
    queryKey: ["school-unit-content", schoolId, version_id, unit_id, resolvedType],
    queryFn: () => getSchoolUnitContent(schoolId, version_id, unit_id, resolvedType!),
    enabled: !!schoolId && resolvedType !== null,
    staleTime: 120_000,
  });

  const content = contentFile?.content as Record<string, unknown> | null | undefined;

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      {/* Top bar */}
      <div className="flex items-center gap-3 border-b border-gray-100 bg-white px-6 py-3">
        <Link
          href={`/school/curriculum/content/${version_id}`}
          className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-800"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to units
        </Link>
        {meta && (
          <span className="text-sm font-medium text-gray-700">— {meta.title}</span>
        )}
      </div>

      <div className="flex flex-1 overflow-auto">
        {/* Left nav: content type selector */}
        <aside className="w-44 shrink-0 border-r border-gray-100 bg-white px-2 py-4">
          {metaLoading ? (
            <div className="space-y-2 px-1">
              {[1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-8 rounded" />
              ))}
            </div>
          ) : meta?.available_types.length === 0 ? (
            <p className="px-3 text-xs text-gray-400 italic">No content yet.</p>
          ) : (
            <nav className="space-y-0.5">
              {(meta?.available_types ?? []).map((ct) => {
                const m = TYPE_META[ct] ?? { label: ct, icon: null };
                return (
                  <button
                    key={ct}
                    onClick={() => setActiveType(ct)}
                    className={cn(
                      "flex w-full items-center gap-2 rounded-md px-3 py-2 text-xs transition-colors",
                      resolvedType === ct
                        ? "bg-indigo-50 font-medium text-indigo-700"
                        : "text-gray-600 hover:bg-gray-50 hover:text-gray-900",
                    )}
                  >
                    {m.icon}
                    {m.label}
                  </button>
                );
              })}
            </nav>
          )}
        </aside>

        {/* Main content area */}
        <main className="flex-1 overflow-auto p-6">
          {fileLoading ? (
            <div className="space-y-4">
              {[1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-24 rounded-lg" />
              ))}
            </div>
          ) : !resolvedType ? (
            <p className="text-sm text-gray-400 italic">Select a content type on the left.</p>
          ) : !content ? (
            <p className="text-sm text-gray-400 italic">No content available for this type.</p>
          ) : (
            <>
              <ContentRenderer contentType={resolvedType} data={content} />
              {meta?.annotations && resolvedType && (
                <AnnotationsPanel annotations={meta.annotations} activeType={resolvedType} />
              )}
            </>
          )}
        </main>
      </div>
    </div>
  );
}
