"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { diffWords } from "diff";
import {
  getReviewItem,
  getReviewQueue,
  getUnitContentFile,
  type ReviewQueueItem,
} from "@/lib/api/admin";
import { ArrowLeft, GitCompare } from "lucide-react";
import { cn } from "@/lib/utils";

// ── Word-level diff renderer ──────────────────────────────────────────────────

function DiffText({ oldText, newText }: { oldText: string; newText: string }) {
  if (oldText === newText) {
    return <span className="text-gray-700">{oldText}</span>;
  }
  const parts = diffWords(oldText, newText);
  return (
    <>
      {parts.map((part, i) => {
        if (part.added) {
          return (
            <mark key={i} className="rounded bg-green-100 text-green-800 px-0.5">
              {part.value}
            </mark>
          );
        }
        if (part.removed) {
          return (
            <del key={i} className="rounded bg-red-100 text-red-700 px-0.5 line-through">
              {part.value}
            </del>
          );
        }
        return <span key={i} className="text-gray-700">{part.value}</span>;
      })}
    </>
  );
}

// ── Section-level diff for a content type ────────────────────────────────────

function extractTextFields(contentType: string, data: Record<string, unknown>): Array<{ label: string; text: string }> {
  const fields: Array<{ label: string; text: string }> = [];

  if (contentType === "lesson") {
    const sections = (data.sections ?? []) as Array<{ heading: string; body: string }>;
    sections.forEach((s) => fields.push({ label: s.heading, text: s.body }));
    const kp = (data.key_points ?? []) as string[];
    if (kp.length) fields.push({ label: "Key Points", text: kp.join("\n") });
  } else if (contentType === "tutorial") {
    const sections = (data.sections ?? []) as Array<{ title: string; content: string; examples?: string[] }>;
    sections.forEach((s) => {
      fields.push({ label: s.title, text: s.content });
      if (s.examples?.length) {
        fields.push({ label: `${s.title} — Examples`, text: s.examples.join("\n\n") });
      }
    });
    const mistakes = (data.common_mistakes ?? []) as string[];
    if (mistakes.length) fields.push({ label: "Common Mistakes", text: mistakes.join("\n") });
  } else if (contentType.startsWith("quiz_set")) {
    const questions = (data.questions ?? []) as Array<{
      question_text: string;
      options: Array<{ option_id: string; text: string }>;
      explanation?: string;
    }>;
    questions.forEach((q, i) => {
      fields.push({ label: `Q${i + 1}`, text: q.question_text });
      fields.push({
        label: `Q${i + 1} Options`,
        text: q.options.map((o) => `${o.option_id}. ${o.text}`).join("\n"),
      });
      if (q.explanation) fields.push({ label: `Q${i + 1} Explanation`, text: q.explanation });
    });
  } else if (contentType === "experiment") {
    const steps = (data.steps ?? []) as Array<{ instruction: string }>;
    steps.forEach((s, i) => fields.push({ label: `Step ${i + 1}`, text: s.instruction }));
    const safety = (data.safety_notes ?? []) as string[];
    if (safety.length) fields.push({ label: "Safety Notes", text: safety.join("\n") });
    if (data.expected_outcome) fields.push({ label: "Expected Outcome", text: data.expected_outcome as string });
  }

  return fields;
}

const CONTENT_TYPES = ["lesson", "tutorial", "quiz_set_1", "quiz_set_2", "quiz_set_3", "experiment"];
const CONTENT_TYPE_LABELS: Record<string, string> = {
  lesson: "Lesson",
  tutorial: "Tutorial",
  quiz_set_1: "Quiz Set 1",
  quiz_set_2: "Quiz Set 2",
  quiz_set_3: "Quiz Set 3",
  experiment: "Experiment",
};

// ── Unit diff view ────────────────────────────────────────────────────────────

function UnitDiff({
  unitId,
  currentVersionId,
  prevVersionId,
}: {
  unitId: string;
  currentVersionId: string;
  prevVersionId: string;
}) {
  const [activeType, setActiveType] = useState("lesson");

  const { data: currentFile, isLoading: loadingCurrent } = useQuery({
    queryKey: ["diff", "current", currentVersionId, unitId, activeType],
    queryFn: () => getUnitContentFile(currentVersionId, unitId, activeType),
    staleTime: 120_000,
    retry: false,
  });

  const { data: prevFile, isLoading: loadingPrev } = useQuery({
    queryKey: ["diff", "prev", prevVersionId, unitId, activeType],
    queryFn: () => getUnitContentFile(prevVersionId, unitId, activeType),
    staleTime: 120_000,
    retry: false,
  });

  const isLoading = loadingCurrent || loadingPrev;

  const currentFields = currentFile ? extractTextFields(activeType, currentFile.data) : [];
  const prevFields = prevFile ? extractTextFields(activeType, prevFile.data) : [];

  const hasChanges =
    currentFields.length > 0 &&
    prevFields.length > 0 &&
    currentFields.some((f, i) => f.text !== (prevFields[i]?.text ?? ""));

  return (
    <div>
      {/* Content type tabs */}
      <div className="mb-4 flex flex-wrap gap-1 border-b border-gray-200">
        {CONTENT_TYPES.map((ct) => (
          <button
            key={ct}
            onClick={() => setActiveType(ct)}
            className={cn(
              "px-3 py-2 text-xs font-medium rounded-t-md border-b-2 -mb-px transition-colors",
              activeType === ct
                ? "border-indigo-500 text-indigo-700 bg-indigo-50"
                : "border-transparent text-gray-500 hover:text-gray-800 hover:bg-gray-50",
            )}
          >
            {CONTENT_TYPE_LABELS[ct]}
          </button>
        ))}
      </div>

      {isLoading ? (
        <div className="space-y-2">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-16 animate-pulse rounded-lg bg-gray-100" />
          ))}
        </div>
      ) : !currentFile && !prevFile ? (
        <p className="text-sm text-gray-400 italic">No content for this type in either version.</p>
      ) : (
        <>
          {/* Legend */}
          <div className="mb-3 flex items-center gap-4 text-xs text-gray-500">
            {hasChanges ? (
              <>
                <span className="flex items-center gap-1">
                  <span className="inline-block rounded bg-green-100 px-1.5 py-0.5 text-green-800">added</span>
                </span>
                <span className="flex items-center gap-1">
                  <span className="inline-block rounded bg-red-100 px-1.5 py-0.5 text-red-700 line-through">removed</span>
                </span>
              </>
            ) : (
              <span className="text-green-600 font-medium">No changes in this content type</span>
            )}
          </div>

          {/* Field-by-field diff */}
          <div className="space-y-4">
            {currentFields.map((field, i) => {
              const prevField = prevFields.find((p) => p.label === field.label) ?? prevFields[i];
              const oldText = prevField?.text ?? "";
              const changed = oldText !== field.text;
              return (
                <div
                  key={field.label}
                  className={cn(
                    "rounded-lg border p-4",
                    changed ? "border-amber-200 bg-amber-50/40" : "border-gray-100 bg-gray-50",
                  )}
                >
                  <div className="mb-2 flex items-center gap-2">
                    <p className="text-xs font-semibold text-gray-600">{field.label}</p>
                    {changed && (
                      <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-700">
                        changed
                      </span>
                    )}
                  </div>
                  <p className="text-sm leading-relaxed whitespace-pre-wrap">
                    <DiffText oldText={oldText} newText={field.text} />
                  </p>
                </div>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function ContentDiffPage() {
  const { version_id } = useParams<{ version_id: string }>();
  const [selectedUnit, setSelectedUnit] = useState<string | null>(null);
  const [compareVersionId, setCompareVersionId] = useState<string | null>(null);

  // Load current version details
  const { data: current, isLoading: loadingCurrent } = useQuery({
    queryKey: ["admin", "content-review", version_id],
    queryFn: () => getReviewItem(version_id),
    staleTime: 60_000,
  });

  // Load all versions of the same subject to populate the compare dropdown
  const { data: allVersions } = useQuery({
    queryKey: ["admin", "content-review-versions", current?.curriculum_id, current?.subject],
    queryFn: () => getReviewQueue(undefined, current!.curriculum_id, current!.subject),
    enabled: !!current,
    staleTime: 60_000,
  });

  const otherVersions: ReviewQueueItem[] = (allVersions?.items ?? []).filter(
    (v) => v.version_id !== version_id,
  );

  // Default compare target: highest version_number that is less than current
  const defaultCompare =
    otherVersions
      .filter((v) => v.version_number < (current?.version_number ?? 0))
      .sort((a, b) => b.version_number - a.version_number)[0] ?? otherVersions[0];

  const resolvedCompareId = compareVersionId ?? defaultCompare?.version_id ?? null;

  const activeUnit = selectedUnit ?? (current?.units[0]?.unit_id ?? null);

  if (loadingCurrent) {
    return (
      <div className="mx-auto max-w-6xl p-8 space-y-4">
        <div className="h-8 w-64 animate-pulse rounded-lg bg-gray-100" />
        <div className="h-96 animate-pulse rounded-xl bg-gray-100" />
      </div>
    );
  }

  if (!current) {
    return <p className="p-8 text-sm text-gray-400">Version not found.</p>;
  }

  if (otherVersions.length === 0) {
    return (
      <div className="mx-auto max-w-4xl p-8">
        <Link
          href={`/admin/content-review/${version_id}`}
          className="mb-6 inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-900"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to version
        </Link>
        <div className="rounded-xl border border-gray-200 bg-white p-12 text-center">
          <GitCompare className="mx-auto mb-3 h-10 w-10 text-gray-300" />
          <p className="text-sm text-gray-500">
            No other versions exist for <strong>{current.subject_name ?? current.subject}</strong> yet.
            <br />
            Diff will be available once a second version is generated.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-6xl p-8">
      <Link
        href={`/admin/content-review/${version_id}`}
        className="mb-6 inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-900"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to version
      </Link>

      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
          <GitCompare className="h-6 w-6 text-indigo-500" />
          Version Diff — {current.subject_name ?? current.subject}
        </h1>

        {/* Compare selector */}
        <div className="mt-3 flex flex-wrap items-center gap-3 text-sm">
          <div className="flex items-center gap-2 rounded-lg border border-green-200 bg-green-50 px-3 py-1.5">
            <span className="text-xs font-medium text-green-700">Current</span>
            <span className="font-semibold text-green-800">v{current.version_number}</span>
            <span className="rounded px-1.5 py-0.5 text-xs bg-green-100 text-green-600">{current.status}</span>
          </div>

          <span className="text-gray-400">vs</span>

          <div className="flex items-center gap-2">
            <label className="text-xs text-gray-500">Compare against:</label>
            <select
              value={resolvedCompareId ?? ""}
              onChange={(e) => setCompareVersionId(e.target.value)}
              className="rounded-md border border-gray-200 px-2 py-1.5 text-sm text-gray-700 focus:border-indigo-400 focus:outline-none"
            >
              {otherVersions.map((v) => (
                <option key={v.version_id} value={v.version_id}>
                  v{v.version_number} — {v.status} — {new Date(v.generated_at).toLocaleDateString()}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {resolvedCompareId && (
        <div className="flex gap-6">
          {/* Left: unit list */}
          <div className="w-52 flex-shrink-0">
            <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-gray-400">Units</p>
            <nav className="space-y-1">
              {current.units.map((u) => (
                <button
                  key={u.unit_id}
                  onClick={() => setSelectedUnit(u.unit_id)}
                  className={cn(
                    "w-full rounded-lg px-3 py-2 text-left transition-colors",
                    activeUnit === u.unit_id
                      ? "bg-indigo-50 text-indigo-700"
                      : "text-gray-600 hover:bg-gray-50 hover:text-gray-900",
                  )}
                >
                  <p className="text-sm font-medium truncate">{u.title}</p>
                  <p className="font-mono text-xs text-gray-400">{u.unit_id}</p>
                </button>
              ))}
            </nav>
          </div>

          {/* Right: diff view */}
          <div className="min-w-0 flex-1 rounded-xl border border-gray-200 bg-white p-6">
            {activeUnit ? (
              <UnitDiff
                key={`${activeUnit}-${resolvedCompareId}`}
                unitId={activeUnit}
                currentVersionId={version_id}
                prevVersionId={resolvedCompareId}
              />
            ) : (
              <p className="text-sm text-gray-400">Select a unit to compare.</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
