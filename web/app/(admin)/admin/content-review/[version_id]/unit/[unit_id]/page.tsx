"use client";

import { createContext, useContext, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  getUnitContentMeta,
  getUnitContentFile,
  getReviewItem,
  addAnnotation,
  deleteAnnotation,
  type ReviewAnnotationItem,
} from "@/lib/api/admin";
import {
  ArrowLeft,
  BookOpen,
  ClipboardList,
  FlaskConical,
  GraduationCap,
  MessageSquarePlus,
  Trash2,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { cn } from "@/lib/utils";

// ── Type labels + icons ───────────────────────────────────────────────────────

const TYPE_META: Record<string, { label: string; icon: React.ReactNode }> = {
  lesson: { label: "Lesson", icon: <BookOpen className="h-4 w-4" /> },
  tutorial: { label: "Tutorial", icon: <GraduationCap className="h-4 w-4" /> },
  quiz_set_1: { label: "Quiz Set 1", icon: <ClipboardList className="h-4 w-4" /> },
  quiz_set_2: { label: "Quiz Set 2", icon: <ClipboardList className="h-4 w-4" /> },
  quiz_set_3: { label: "Quiz Set 3", icon: <ClipboardList className="h-4 w-4" /> },
  experiment: { label: "Experiment", icon: <FlaskConical className="h-4 w-4" /> },
};

// ── Annotation context ────────────────────────────────────────────────────────
// Passed down to renderers so each section can show/add its own notes without prop drilling.

interface AnnotationCtx {
  versionId: string;
  unitId: string;
  annotations: ReviewAnnotationItem[];
  onAdd: (effectiveKey: string, text: string) => Promise<void>;
  onDelete: (annotationId: string) => Promise<void>;
}

const AnnotationContext = createContext<AnnotationCtx | null>(null);

function useAnnotations(effectiveKey: string) {
  const ctx = useContext(AnnotationContext);
  if (!ctx) return { annotations: [], onAdd: async () => {}, onDelete: async () => {} };
  return {
    annotations: ctx.annotations.filter((a) => a.content_type === effectiveKey),
    onAdd: (text: string) => ctx.onAdd(effectiveKey, text),
    onDelete: ctx.onDelete,
  };
}

// ── Inline section notes ──────────────────────────────────────────────────────
// Used inside Lesson sections, Quiz questions, Experiment steps.

function SectionNotes({ effectiveKey }: { effectiveKey: string }) {
  const { annotations, onAdd, onDelete } = useAnnotations(effectiveKey);
  const [open, setOpen] = useState(false);
  const [note, setNote] = useState("");
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    if (!note.trim()) return;
    setSaving(true);
    await onAdd(note.trim());
    setNote("");
    setOpen(false);
    setSaving(false);
  };

  return (
    <div className="mt-3">
      {/* Toggle button with count badge */}
      <button
        onClick={() => setOpen((o) => !o)}
        className="inline-flex items-center gap-1.5 text-xs text-amber-600 hover:text-amber-800 transition-colors"
      >
        <MessageSquarePlus className="h-3.5 w-3.5" />
        {annotations.length > 0 ? (
          <span>
            {annotations.length} note{annotations.length !== 1 ? "s" : ""}
          </span>
        ) : (
          <span>Add note</span>
        )}
        {open ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
      </button>

      {open && (
        <div className="mt-2 rounded-lg border border-amber-100 bg-amber-50 p-3 space-y-2">
          {/* Existing notes */}
          {annotations.map((a) => (
            <div
              key={a.annotation_id}
              className="flex gap-2 rounded-md border border-amber-100 bg-white px-3 py-2"
            >
              <div className="flex-1 min-w-0">
                <p className="text-xs text-gray-800 whitespace-pre-wrap">{a.annotation_text}</p>
                <p className="mt-0.5 text-xs text-gray-400">
                  {a.reviewer_email ?? "Admin"} · {new Date(a.created_at).toLocaleString()}
                </p>
              </div>
              <button
                onClick={() => onDelete(a.annotation_id)}
                className="flex-shrink-0 text-gray-300 hover:text-red-500 transition-colors"
                title="Delete note"
              >
                <Trash2 className="h-3 w-3" />
              </button>
            </div>
          ))}

          {/* Add note textarea */}
          <textarea
            autoFocus
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="Write a note about this section…"
            rows={2}
            className="w-full rounded-md border border-gray-200 px-3 py-2 text-xs text-gray-800 placeholder-gray-400 focus:border-amber-400 focus:outline-none resize-none"
          />
          <div className="flex justify-end gap-2">
            <button
              onClick={() => { setOpen(false); setNote(""); }}
              className="rounded px-2 py-1 text-xs text-gray-500 hover:text-gray-800"
            >
              Cancel
            </button>
            <button
              disabled={!note.trim() || saving}
              onClick={handleSave}
              className="rounded bg-amber-600 px-3 py-1 text-xs font-medium text-white hover:bg-amber-700 disabled:opacity-50 transition-colors"
            >
              {saving ? "Saving…" : "Save"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Shared prose renderer ─────────────────────────────────────────────────────

function Prose({ text, className }: { text: string; className?: string }) {
  return (
    <div className={cn("text-sm text-gray-700", className)}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          table: ({ children }) => (
            <div className="overflow-x-auto my-3">
              <table className="w-full text-xs border-collapse">{children}</table>
            </div>
          ),
          thead: ({ children }) => (
            <thead className="bg-gray-100 text-gray-600 font-semibold">{children}</thead>
          ),
          tbody: ({ children }) => (
            <tbody className="divide-y divide-gray-100">{children}</tbody>
          ),
          tr: ({ children }) => <tr className="even:bg-gray-50">{children}</tr>,
          th: ({ children }) => <th className="px-3 py-2 text-left">{children}</th>,
          td: ({ children }) => <td className="px-3 py-2">{children}</td>,
          code: ({ children, className }) => {
            const isBlock = className?.includes("language-");
            if (isBlock) {
              return (
                <pre className="bg-gray-50 rounded-md p-3 overflow-x-auto text-xs font-mono text-gray-800 my-2">
                  <code>{children}</code>
                </pre>
              );
            }
            return (
              <code className="rounded bg-gray-100 px-1 py-0.5 font-mono text-xs text-indigo-700">
                {children}
              </code>
            );
          },
          p: ({ children }) => <p className="mb-2 last:mb-0 leading-relaxed">{children}</p>,
          ul: ({ children }) => <ul className="list-disc pl-4 space-y-1 mb-2">{children}</ul>,
          ol: ({ children }) => <ol className="list-decimal pl-4 space-y-1 mb-2">{children}</ol>,
          li: ({ children }) => <li className="leading-relaxed">{children}</li>,
        }}
      >
        {text}
      </ReactMarkdown>
    </div>
  );
}

function ExampleBlock({ text }: { text: string }) {
  const hasSteps = text.includes("\n");
  if (!hasSteps) {
    return <p className="text-xs text-gray-600 leading-relaxed">{text}</p>;
  }
  return (
    <pre className="whitespace-pre-wrap rounded-md bg-gray-50 border border-gray-100 p-3 font-mono text-xs text-gray-800 leading-relaxed overflow-x-auto">
      {text}
    </pre>
  );
}

// ── Content renderers ─────────────────────────────────────────────────────────

function LessonRenderer({ data, baseKey }: { data: Record<string, unknown>; baseKey: string }) {
  const sections = (data.sections ?? []) as Array<{ heading: string; body: string }>;
  const keyPoints = (data.key_points ?? []) as string[];

  return (
    <div className="space-y-6">
      {sections.map((s, i) => {
        const key = `${baseKey}::${s.heading || i}`;
        return (
          <div key={i} className="border-b border-gray-50 pb-5 last:border-0 last:pb-0">
            <h3 className="mb-1.5 text-sm font-semibold text-gray-800">{s.heading}</h3>
            <Prose text={s.body} />
            <SectionNotes effectiveKey={key} />
          </div>
        );
      })}
      {keyPoints.length > 0 && (
        <div className="rounded-lg border border-indigo-100 bg-indigo-50 p-4">
          <h3 className="mb-2 text-sm font-semibold text-indigo-800">Key Points</h3>
          <ul className="space-y-1.5">
            {keyPoints.map((kp, i) => (
              <li key={i} className="flex gap-2.5 text-sm text-indigo-700">
                <span className="mt-1.5 h-1.5 w-1.5 flex-shrink-0 rounded-full bg-indigo-400" />
                {kp}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function TutorialRenderer({ data, baseKey }: { data: Record<string, unknown>; baseKey: string }) {
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

  const activeSectionKey = activeTab === "__mistakes__"
    ? `${baseKey}::mistakes`
    : `${baseKey}::${activeTab}`;

  return (
    <div>
      {/* Tab bar */}
      <div className="flex flex-wrap gap-1 border-b border-gray-200 mb-4">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={cn(
              "px-3 py-2 text-xs font-medium rounded-t-md border-b-2 -mb-px transition-colors",
              activeTab === tab.key
                ? tab.key === "__mistakes__"
                  ? "border-red-500 text-red-600 bg-red-50"
                  : "border-indigo-500 text-indigo-700 bg-indigo-50"
                : "border-transparent text-gray-500 hover:text-gray-800 hover:bg-gray-50",
            )}
          >
            {tab.key === "__mistakes__" ? "⚠ Common Mistakes" : tab.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {activeTab === "__mistakes__" ? (
        <>
          <ul className="space-y-2">
            {mistakes.map((m, i) => (
              <li key={i} className="flex gap-2 text-sm text-red-600 rounded-md bg-red-50 px-3 py-2">
                <span className="flex-shrink-0">⚠</span>
                <span>{m}</span>
              </li>
            ))}
          </ul>
          <SectionNotes effectiveKey={activeSectionKey} />
        </>
      ) : activeSection ? (
        <div className="space-y-4">
          <Prose text={activeSection.content} />
          {activeSection.examples && activeSection.examples.length > 0 && (
            <div className="space-y-2">
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Examples</p>
              {activeSection.examples.map((ex, j) => (
                <ExampleBlock key={j} text={ex} />
              ))}
            </div>
          )}
          {activeSection.practice_question && (
            <div className="rounded-md border border-indigo-100 bg-indigo-50 px-3 py-2">
              <p className="text-xs font-semibold text-indigo-500 mb-1">Practice</p>
              <p className="text-xs text-indigo-700">{activeSection.practice_question}</p>
            </div>
          )}
          {/* Note scoped to this tab/section */}
          <SectionNotes effectiveKey={activeSectionKey} />
        </div>
      ) : null}
    </div>
  );
}

function QuizRenderer({ data, baseKey }: { data: Record<string, unknown>; baseKey: string }) {
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
        <p className="text-xs font-medium text-gray-400 uppercase tracking-wide">
          Quiz Set {setNumber} · {questions.length} questions
        </p>
      )}
      {questions.map((q, i) => {
        const qKey = `${baseKey}::Q${i + 1}`;
        return (
          <div key={q.question_id ?? i} className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
            <div className="mb-3 flex gap-2">
              <span className="flex-shrink-0 font-mono text-xs text-gray-400 mt-0.5">Q{i + 1}.</span>
              <Prose text={q.question_text} className="flex-1" />
            </div>
            <ul className="space-y-1.5">
              {q.options.map((opt) => (
                <li
                  key={opt.option_id}
                  className={cn(
                    "flex items-start gap-2 rounded-md px-3 py-2 text-sm",
                    opt.option_id === q.correct_option
                      ? "bg-green-50 text-green-800 font-medium"
                      : "bg-gray-50 text-gray-700",
                  )}
                >
                  <span className="flex-shrink-0 font-mono text-xs mt-0.5 text-gray-400">
                    {opt.option_id}.
                  </span>
                  <span className="flex-1">{opt.text}</span>
                  {opt.option_id === q.correct_option && (
                    <span className="ml-auto flex-shrink-0 text-xs text-green-600">✓ correct</span>
                  )}
                </li>
              ))}
            </ul>
            {q.explanation && (
              <div className="mt-3 rounded bg-amber-50 px-3 py-2">
                <p className="text-xs font-semibold text-amber-600 mb-1">Explanation</p>
                <Prose text={q.explanation} className="text-xs text-amber-700" />
              </div>
            )}
            {q.difficulty && (
              <p className="mt-2 text-xs text-gray-400">Difficulty: {q.difficulty}</p>
            )}
            {/* Note scoped to this question */}
            <SectionNotes effectiveKey={qKey} />
          </div>
        );
      })}
    </div>
  );
}

function ExperimentRenderer({ data, baseKey }: { data: Record<string, unknown>; baseKey: string }) {
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
                  <span className="flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full bg-indigo-100 text-xs font-semibold text-indigo-700">
                    {s.step ?? i + 1}
                  </span>
                  <Prose text={s.instruction} className="flex-1" />
                </div>
                <SectionNotes effectiveKey={`${baseKey}::step${i + 1}`} />
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
                <span className="flex-shrink-0">⚠</span>
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
  baseKey,
}: {
  contentType: string;
  data: Record<string, unknown>;
  baseKey: string;
}) {
  if (contentType === "lesson") return <LessonRenderer data={data} baseKey={baseKey} />;
  if (contentType === "tutorial") return <TutorialRenderer data={data} baseKey={baseKey} />;
  if (contentType.startsWith("quiz_set")) return <QuizRenderer data={data} baseKey={baseKey} />;
  if (contentType === "experiment") return <ExperimentRenderer data={data} baseKey={baseKey} />;
  return (
    <pre className="overflow-x-auto rounded-lg bg-gray-50 p-4 text-xs text-gray-700">
      {JSON.stringify(data, null, 2)}
    </pre>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function AdminUnitContentPage() {
  const { version_id, unit_id } = useParams<{ version_id: string; unit_id: string }>();
  const [activeType, setActiveType] = useState<string | null>(null);
  const queryClient = useQueryClient();

  const { data: meta, isLoading: metaLoading } = useQuery({
    queryKey: ["admin", "unit-meta", version_id, unit_id],
    queryFn: () => getUnitContentMeta(version_id, unit_id),
    staleTime: 60_000,
  });

  const { data: detail } = useQuery({
    queryKey: ["admin", "review-detail", version_id],
    queryFn: () => getReviewItem(version_id),
    staleTime: 30_000,
  });

  const resolvedType = activeType ?? (meta?.available_types[0] ?? null);

  const { data: contentFile, isLoading: fileLoading } = useQuery({
    queryKey: ["admin", "unit-content", version_id, unit_id, resolvedType],
    queryFn: () => getUnitContentFile(version_id, unit_id, resolvedType!),
    enabled: resolvedType !== null,
    staleTime: 120_000,
  });

  const addMutation = useMutation({
    mutationFn: ({ effectiveKey, text }: { effectiveKey: string; text: string }) =>
      addAnnotation(version_id, unit_id, effectiveKey, text),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin", "review-detail", version_id] }),
  });

  const deleteMutation = useMutation({
    mutationFn: (annotationId: string) => deleteAnnotation(annotationId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin", "review-detail", version_id] }),
  });

  const annotationCtx: AnnotationCtx = {
    versionId: version_id,
    unitId: unit_id,
    annotations: detail?.annotations ?? [],
    onAdd: async (effectiveKey, text) => { await addMutation.mutateAsync({ effectiveKey, text }); },
    onDelete: async (id) => { await deleteMutation.mutateAsync(id); },
  };

  // base key = "{unit_id}::{contentType}" — section keys append "::{sectionId}"
  const baseKey = resolvedType ? `${unit_id}::${resolvedType}` : "";

  return (
    <AnnotationContext.Provider value={annotationCtx}>
      <div className="mx-auto max-w-6xl p-8">
        <Link
          href={`/admin/content-review/${version_id}`}
          className="mb-6 inline-flex items-center gap-1.5 text-sm text-gray-500 transition-colors hover:text-gray-900"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to version
        </Link>

        {metaLoading ? (
          <div className="space-y-4">
            <div className="h-8 w-64 animate-pulse rounded-lg bg-gray-100" />
            <div className="h-96 animate-pulse rounded-xl bg-gray-100" />
          </div>
        ) : meta ? (
          <>
            <div className="mb-6">
              <h1 className="text-2xl font-bold text-gray-900">{meta.title}</h1>
              <p className="mt-1 font-mono text-xs text-gray-400">
                {unit_id} · {meta.curriculum_id} · {meta.lang.toUpperCase()}
              </p>
            </div>

            <div className="flex gap-6">
              {/* Left: content type nav */}
              <div className="w-48 flex-shrink-0">
                <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-gray-400">
                  Content Types
                </p>
                {meta.available_types.length === 0 ? (
                  <p className="text-xs text-gray-400">No content files on disk.</p>
                ) : (
                  <nav className="space-y-1">
                    {meta.available_types.map((ct) => {
                      const m = TYPE_META[ct] ?? { label: ct, icon: null };
                      return (
                        <button
                          key={ct}
                          onClick={() => setActiveType(ct)}
                          className={cn(
                            "flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-left text-sm font-medium transition-colors",
                            resolvedType === ct
                              ? "bg-indigo-50 text-indigo-700"
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
              </div>

              {/* Right: content viewer */}
              <div className="min-w-0 flex-1 rounded-xl border border-gray-200 bg-white p-6">
                {fileLoading ? (
                  <div className="space-y-3">
                    <div className="h-5 w-48 animate-pulse rounded bg-gray-100" />
                    <div className="h-4 w-full animate-pulse rounded bg-gray-100" />
                    <div className="h-4 w-4/5 animate-pulse rounded bg-gray-100" />
                    <div className="h-4 w-3/5 animate-pulse rounded bg-gray-100" />
                    <div className="h-4 w-full animate-pulse rounded bg-gray-100" />
                  </div>
                ) : contentFile ? (
                  <>
                    <div className="mb-5 flex items-center gap-2 border-b border-gray-100 pb-4">
                      {TYPE_META[contentFile.content_type]?.icon}
                      <p className="text-sm font-semibold text-gray-800">
                        {TYPE_META[contentFile.content_type]?.label ?? contentFile.content_type}
                      </p>
                    </div>
                    <ContentRenderer
                      contentType={contentFile.content_type}
                      data={contentFile.data}
                      baseKey={baseKey}
                    />
                  </>
                ) : (
                  <p className="text-sm text-gray-400">
                    {meta.available_types.length === 0
                      ? "No content files are available for this unit."
                      : "Select a content type from the left to preview."}
                  </p>
                )}
              </div>
            </div>
          </>
        ) : (
          <p className="text-sm text-gray-400">Unit not found.</p>
        )}
      </div>
    </AnnotationContext.Provider>
  );
}
