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

// ── Lesson form ────────────────────────────────────────────────────────────────

interface Section {
  heading: string;
  body: string;
}

interface LessonDraft {
  synopsis: string;
  sections: Section[];
  key_points: string;
  learning_objectives: string;
}

function lessonBodyToForm(body: Record<string, unknown>): LessonDraft {
  const sections = (body.sections as Section[] | undefined) ?? [];
  const keyPoints = body.key_points as string[] | undefined;
  const objectives = body.learning_objectives as string[] | undefined;
  return {
    synopsis: (body.synopsis as string) ?? "",
    sections:
      sections.length > 0 ? sections : [{ heading: "Introduction", body: "" }],
    key_points: (keyPoints ?? []).join("\n"),
    learning_objectives: (objectives ?? []).join("\n"),
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
    key_points: form.key_points
      .split("\n")
      .map((s) => s.trim())
      .filter(Boolean),
    learning_objectives: form.learning_objectives
      .split("\n")
      .map((s) => s.trim())
      .filter(Boolean),
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
  function updateSection(i: number, field: keyof Section, value: string) {
    const next = draft.sections.map((s, idx) =>
      idx === i ? { ...s, [field]: value } : s,
    );
    onChange({ ...draft, sections: next });
  }

  function addSection() {
    onChange({
      ...draft,
      sections: [...draft.sections, { heading: "", body: "" }],
    });
  }

  function removeSection(i: number) {
    onChange({
      ...draft,
      sections: draft.sections.filter((_, idx) => idx !== i),
    });
  }

  const ta =
    "w-full rounded-md border border-gray-200 bg-white px-3 py-2 text-sm text-gray-900 shadow-sm placeholder:text-gray-400 focus:border-indigo-400 focus:outline-none focus:ring-1 focus:ring-indigo-400 disabled:bg-gray-50 disabled:text-gray-500";

  return (
    <div className="space-y-6">
      {/* Synopsis */}
      <div>
        <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-gray-500">
          Synopsis
        </label>
        <textarea
          rows={3}
          className={ta}
          value={draft.synopsis}
          disabled={readOnly}
          onChange={(e) => onChange({ ...draft, synopsis: e.target.value })}
          placeholder="A short summary of what this unit covers…"
        />
      </div>

      {/* Sections */}
      <div>
        <div className="mb-2 flex items-center justify-between">
          <label className="text-xs font-semibold uppercase tracking-wide text-gray-500">
            Sections
          </label>
          {!readOnly && (
            <button
              type="button"
              onClick={addSection}
              className="text-xs font-medium text-indigo-600 hover:underline"
            >
              + Add section
            </button>
          )}
        </div>
        <div className="space-y-4">
          {draft.sections.map((section, i) => (
            <div
              key={i}
              className="rounded-lg border border-gray-200 bg-gray-50 p-4"
            >
              <div className="mb-2 flex items-center gap-2">
                <span className="text-xs font-semibold text-gray-400">
                  §{i + 1}
                </span>
                <input
                  type="text"
                  className="flex-1 rounded border border-gray-200 bg-white px-2 py-1 text-sm font-medium text-gray-800 shadow-sm focus:border-indigo-400 focus:outline-none disabled:bg-gray-50 disabled:text-gray-500"
                  value={section.heading}
                  disabled={readOnly}
                  onChange={(e) => updateSection(i, "heading", e.target.value)}
                  placeholder="Section heading"
                />
                {!readOnly && draft.sections.length > 1 && (
                  <button
                    type="button"
                    onClick={() => removeSection(i)}
                    className="text-xs text-gray-400 hover:text-red-500"
                  >
                    Remove
                  </button>
                )}
              </div>
              <textarea
                rows={5}
                className={ta}
                value={section.body}
                disabled={readOnly}
                onChange={(e) => updateSection(i, "body", e.target.value)}
                placeholder="Section content — markdown supported"
              />
            </div>
          ))}
        </div>
      </div>

      {/* Key points */}
      <div>
        <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-gray-500">
          Key points{" "}
          <span className="normal-case font-normal text-gray-400">
            (one per line)
          </span>
        </label>
        <textarea
          rows={4}
          className={ta}
          value={draft.key_points}
          disabled={readOnly}
          onChange={(e) => onChange({ ...draft, key_points: e.target.value })}
          placeholder="Each key takeaway on its own line…"
        />
      </div>

      {/* Learning objectives */}
      <div>
        <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-gray-500">
          Learning objectives{" "}
          <span className="normal-case font-normal text-gray-400">
            (one per line)
          </span>
        </label>
        <textarea
          rows={4}
          className={ta}
          value={draft.learning_objectives}
          disabled={readOnly}
          onChange={(e) =>
            onChange({ ...draft, learning_objectives: e.target.value })
          }
          placeholder="What students will be able to do after this unit…"
        />
      </div>
    </div>
  );
}

// ── Status badge ───────────────────────────────────────────────────────────────

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
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${STATUS_STYLES[status] ?? "bg-gray-100 text-gray-500"}`}
    >
      {STATUS_LABELS[status] ?? status}
    </span>
  );
}

// ── Content type tab ───────────────────────────────────────────────────────────

const CONTENT_TYPE_LABELS: Record<string, string> = {
  lesson: "Lesson",
  tutorial: "Tutorial",
  quiz_set_1: "Quiz 1",
  quiz_set_2: "Quiz 2",
  quiz_set_3: "Quiz 3",
  experiment: "Experiment",
};

// ── Page ───────────────────────────────────────────────────────────────────────

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

  // Which content type tab is active
  const [activeType, setActiveType] = useState<string>("lesson");

  // Per-type form state for lesson editor
  const [lessonDraft, setLessonDraft] = useState<LessonDraft | null>(null);
  const [lessonOriginalBody, setLessonOriginalBody] = useState<Record<
    string,
    unknown
  > | null>(null);
  const [dirty, setDirty] = useState(false);
  const [notice, setNotice] = useState<{
    kind: "success" | "error";
    msg: string;
  } | null>(null);
  const [rejectReason, setRejectReason] = useState("");
  const [showRejectBox, setShowRejectBox] = useState(false);

  // 1. List all overrides for this unit (to know which tabs to show)
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
  const availableTypes = Object.keys(overridesByType).filter(
    (t) => t in CONTENT_TYPE_LABELS,
  );

  // Ensure active tab is valid once data loads
  useEffect(() => {
    if (availableTypes.length > 0 && !availableTypes.includes(activeType)) {
      setActiveType(availableTypes[0]);
    }
  }, [availableTypes.join(",")]);

  // 2. Fetch the body for the active content type
  const {
    data: overrideDetail,
    isLoading: detailLoading,
    refetch: refetchDetail,
  } = useQuery({
    queryKey: ["override-detail", schoolId, curriculumId, unitId, activeType],
    queryFn: () => getUnitOverride(schoolId, curriculumId, unitId, activeType),
    enabled: !!schoolId && !!curriculumId && !!unitId && availableTypes.includes(activeType),
    staleTime: 0,
  });

  // Populate form when detail loads
  useEffect(() => {
    if (!overrideDetail) return;
    if (activeType === "lesson") {
      const form = lessonBodyToForm(overrideDetail.body);
      setLessonDraft(form);
      setLessonOriginalBody(overrideDetail.body);
      setDirty(false);
    }
  }, [overrideDetail, activeType]);

  const readOnly =
    overrideDetail?.review_status === "pending_review" ||
    overrideDetail?.review_status === "approved";

  // 3. Save draft mutation
  const saveMutation = useMutation({
    mutationFn: () => {
      if (activeType === "lesson" && lessonDraft && lessonOriginalBody) {
        const body = formToLessonBody(lessonOriginalBody, lessonDraft);
        return saveDraft(schoolId, curriculumId, unitId, activeType, body);
      }
      return Promise.reject(new Error("Nothing to save"));
    },
    onSuccess: () => {
      setDirty(false);
      setNotice({ kind: "success", msg: "Draft saved." });
      queryClient.invalidateQueries({
        queryKey: ["unit-status", schoolId, curriculumId],
      });
      refetchDetail();
      setTimeout(() => setNotice(null), 3000);
    },
    onError: (err: Error) => {
      setNotice({ kind: "error", msg: err.message || "Save failed." });
    },
  });

  // 4. Submit for review mutation
  const reviewMutation = useMutation({
    mutationFn: () =>
      submitForReview(schoolId, curriculumId, unitId, null),
    onSuccess: () => {
      setNotice({ kind: "success", msg: "Submitted for review." });
      queryClient.invalidateQueries({
        queryKey: ["unit-status", schoolId, curriculumId],
      });
      refetchDetail();
    },
    onError: (err: Error) => {
      setNotice({ kind: "error", msg: err.message || "Submission failed." });
    },
  });

  // 5. Approve mutation (school_admin only)
  const approveMutation = useMutation({
    mutationFn: () => approveUnitContent(schoolId, curriculumId, unitId, true),
    onSuccess: (data) => {
      setNotice({
        kind: "success",
        msg: `Approved and published ${data.published} content item${data.published !== 1 ? "s" : ""}.`,
      });
      queryClient.invalidateQueries({
        queryKey: ["unit-status", schoolId, curriculumId],
      });
      refetchDetail();
    },
    onError: (err: Error) => {
      setNotice({ kind: "error", msg: err.message || "Approval failed." });
    },
  });

  // 6. Reject mutation (school_admin only)
  const rejectMutation = useMutation({
    mutationFn: () =>
      rejectUnitContent(schoolId, curriculumId, unitId, rejectReason),
    onSuccess: () => {
      setNotice({ kind: "success", msg: "Rejected — teacher can revise and resubmit." });
      setShowRejectBox(false);
      setRejectReason("");
      queryClient.invalidateQueries({
        queryKey: ["unit-status", schoolId, curriculumId],
      });
      refetchDetail();
    },
    onError: (err: Error) => {
      setNotice({ kind: "error", msg: err.message || "Rejection failed." });
    },
  });

  const isLoading = unitsLoading || detailLoading;
  const currentStatus = overrideDetail?.review_status;
  const canSubmit =
    currentStatus === "draft" || currentStatus === "rejected";
  const canSave = !readOnly && activeType === "lesson";
  const isAdmin = teacher?.role === "school_admin";
  const canApprove = isAdmin && currentStatus === "pending_review";

  const backHref = adoptionId
    ? `/school/content/${curriculumId}?aid=${adoptionId}`
    : `/school/content/${curriculumId}`;

  return (
    <div className="max-w-4xl space-y-6 p-6">
      {/* Header */}
      <div className="flex items-start gap-4">
        <button
          type="button"
          onClick={() => router.push(backHref)}
          className="mt-0.5 rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
          aria-label="Back"
        >
          <ArrowLeft className="h-4 w-4" />
        </button>

        <div className="flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <BookOpen className="h-5 w-5 text-indigo-600" />
            <h1 className="text-xl font-bold text-gray-900">
              {unitMeta?.title ?? unitId}
            </h1>
            {unitMeta?.subject_name && (
              <span className="rounded-full bg-indigo-50 px-2 py-0.5 text-xs font-medium text-indigo-700">
                {unitMeta.subject_name}
              </span>
            )}
            {currentStatus && <StatusBadge status={currentStatus} />}
          </div>
          <p className="mt-1 text-sm text-gray-500">
            {overrideDetail?.last_edited_by_name
              ? `Last edited by ${overrideDetail.last_edited_by_name}`
              : "Not yet edited"}
            {overrideDetail?.edited_at
              ? ` · ${new Date(overrideDetail.edited_at).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" })}`
              : ""}
            {overrideDetail?.version_number !== undefined
              ? ` · v${overrideDetail.version_number}`
              : ""}
          </p>
        </div>

        {/* Actions */}
        <div className="flex shrink-0 items-center gap-2">
          {canSave && (
            <button
              type="button"
              onClick={() => saveMutation.mutate()}
              disabled={saveMutation.isPending || !dirty}
              className="inline-flex items-center gap-1.5 rounded-md bg-white px-3 py-1.5 text-sm font-medium text-gray-700 shadow-sm ring-1 ring-gray-200 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <Save className="h-4 w-4" />
              {saveMutation.isPending ? "Saving…" : "Save draft"}
            </button>
          )}
          {canSubmit && (
            <button
              type="button"
              onClick={() => reviewMutation.mutate()}
              disabled={reviewMutation.isPending || dirty}
              className="inline-flex items-center gap-1.5 rounded-md bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white shadow-sm hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
              title={dirty ? "Save your changes before submitting" : undefined}
            >
              <Send className="h-4 w-4" />
              {reviewMutation.isPending ? "Submitting…" : "Submit for review"}
            </button>
          )}
          {canApprove && (
            <>
              <button
                type="button"
                onClick={() => setShowRejectBox((v) => !v)}
                disabled={rejectMutation.isPending}
                className="inline-flex items-center gap-1.5 rounded-md bg-white px-3 py-1.5 text-sm font-medium text-red-600 shadow-sm ring-1 ring-red-200 hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-50"
              >
                <ThumbsDown className="h-4 w-4" />
                Reject
              </button>
              <button
                type="button"
                onClick={() => approveMutation.mutate()}
                disabled={approveMutation.isPending}
                className="inline-flex items-center gap-1.5 rounded-md bg-green-600 px-3 py-1.5 text-sm font-medium text-white shadow-sm hover:bg-green-700 disabled:cursor-not-allowed disabled:opacity-50"
              >
                <ThumbsUp className="h-4 w-4" />
                {approveMutation.isPending ? "Approving…" : "Approve & publish"}
              </button>
            </>
          )}
        </div>
      </div>

      {/* Notice */}
      {notice && (
        <div
          className={`flex items-center gap-2 rounded-md border px-4 py-2.5 text-sm ${
            notice.kind === "success"
              ? "border-green-200 bg-green-50 text-green-800"
              : "border-red-200 bg-red-50 text-red-700"
          }`}
        >
          {notice.kind === "success" ? (
            <CheckCircle2 className="h-4 w-4 shrink-0" />
          ) : (
            <AlertCircle className="h-4 w-4 shrink-0" />
          )}
          {notice.msg}
        </div>
      )}

      {/* Reject reason box */}
      {showRejectBox && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4">
          <p className="mb-2 text-sm font-medium text-red-800">
            Reason for rejection
          </p>
          <textarea
            rows={3}
            className="w-full rounded-md border border-red-200 bg-white px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-red-400 focus:outline-none focus:ring-1 focus:ring-red-400"
            placeholder="Tell the teacher what needs to be revised…"
            value={rejectReason}
            onChange={(e) => setRejectReason(e.target.value)}
          />
          <div className="mt-2 flex items-center gap-2">
            <button
              type="button"
              onClick={() => rejectMutation.mutate()}
              disabled={rejectMutation.isPending || !rejectReason.trim()}
              className="inline-flex items-center gap-1.5 rounded-md bg-red-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-red-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {rejectMutation.isPending ? "Rejecting…" : "Confirm rejection"}
            </button>
            <button
              type="button"
              onClick={() => {
                setShowRejectBox(false);
                setRejectReason("");
              }}
              className="text-sm text-gray-500 hover:text-gray-700"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Pending review banner */}
      {currentStatus === "pending_review" && (
        <div className="flex items-center gap-2 rounded-md border border-blue-200 bg-blue-50 px-4 py-2.5 text-sm text-blue-800">
          <Clock className="h-4 w-4 shrink-0" />
          This unit is pending review and cannot be edited until the review is
          complete.
        </div>
      )}

      {/* Unsaved changes warning */}
      {dirty && (
        <div className="flex items-center gap-2 rounded-md border border-yellow-200 bg-yellow-50 px-4 py-2.5 text-sm text-yellow-800">
          <AlertCircle className="h-4 w-4 shrink-0" />
          You have unsaved changes — save before submitting for review.
        </div>
      )}

      {isLoading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="h-20 animate-pulse rounded-lg bg-gray-100"
            />
          ))}
        </div>
      ) : availableTypes.length === 0 ? (
        <div className="flex flex-col items-center gap-3 rounded-lg border border-dashed border-gray-200 py-12 text-center">
          <BookOpen className="h-8 w-8 text-gray-300" />
          <p className="text-sm font-medium text-gray-500">
            No content imported yet
          </p>
          <p className="max-w-xs text-xs text-gray-400">
            Go back and use the Import button to pull this unit&apos;s content
            into your workspace.
          </p>
          <button
            type="button"
            onClick={() => router.push(backHref)}
            className="mt-2 rounded-md bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700"
          >
            Back to unit list
          </button>
        </div>
      ) : (
        <div className="rounded-lg border border-gray-200 bg-white shadow-sm">
          {/* Content type tabs */}
          {availableTypes.length > 1 && (
            <div className="flex gap-0 border-b border-gray-200">
              {availableTypes.map((ct) => (
                <button
                  key={ct}
                  type="button"
                  onClick={() => {
                    if (dirty) {
                      if (
                        !confirm(
                          "You have unsaved changes. Discard and switch tab?",
                        )
                      )
                        return;
                    }
                    setActiveType(ct);
                    setDirty(false);
                  }}
                  className={`px-4 py-2.5 text-sm font-medium transition-colors ${
                    activeType === ct
                      ? "border-b-2 border-indigo-600 text-indigo-700"
                      : "text-gray-500 hover:text-gray-700"
                  }`}
                >
                  {CONTENT_TYPE_LABELS[ct] ?? ct}
                  {overridesByType[ct] && (
                    <span
                      className={`ml-1.5 inline-flex items-center rounded-full px-1.5 py-0.5 text-xs font-medium ${
                        STATUS_STYLES[overridesByType[ct].review_status] ??
                        "bg-gray-100 text-gray-500"
                      }`}
                    >
                      {STATUS_LABELS[overridesByType[ct].review_status] ??
                        overridesByType[ct].review_status}
                    </span>
                  )}
                </button>
              ))}
            </div>
          )}

          {/* Editor body */}
          <div className="p-6">
            {activeType === "lesson" && lessonDraft ? (
              <LessonEditor
                draft={lessonDraft}
                onChange={(d) => {
                  setLessonDraft(d);
                  setDirty(true);
                }}
                readOnly={readOnly}
              />
            ) : activeType !== "lesson" ? (
              <div className="flex flex-col items-center gap-3 py-12 text-center">
                <BookOpen className="h-8 w-8 text-gray-300" />
                <p className="text-sm font-medium text-gray-500">
                  {CONTENT_TYPE_LABELS[activeType] ?? activeType} editing
                  coming soon
                </p>
                <p className="max-w-xs text-xs text-gray-400">
                  Only lesson content can be edited here for now. Submit the
                  lesson for review using the button above.
                </p>
              </div>
            ) : (
              <div className="py-12 text-center text-sm text-gray-400">
                Loading content…
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
