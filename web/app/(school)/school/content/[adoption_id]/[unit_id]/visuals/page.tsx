"use client";

import { use, useEffect, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useTeacher } from "@/lib/hooks/useTeacher";
import {
  listSectionVisuals,
  putSectionVisuals,
  type SectionSummary,
} from "@/lib/api/visuals";
import { VisualSlot } from "@/components/content/VisualSlot";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import {
  Loader2,
  Save,
  AlertCircle,
  CheckCircle2,
  Eye,
  Code,
} from "lucide-react";
import type { VisualBlock } from "@/lib/types/api";

/**
 * /school/content/{adoption_id}/{unit_id}/visuals
 *
 * Per-unit visual editor (issue #318 phase 2c-3).
 *
 * Lists each section of a unit's tutorial; per section renders a JSON
 * editor pre-populated with the current visuals[] array. Save calls
 * PUT /api/v1/schools/{school_id}/visuals/sections which appends a new
 * draft override row (Phase D append-only versioning). The school admin
 * then transitions the draft through pending_review → approved →
 * activated via the existing review queue.
 *
 * Form-based editor (kind / heading / items) is a follow-up polish pass.
 * The JSON-textarea approach is intentionally simple and evolvable.
 */

interface PageProps {
  params: Promise<{ adoption_id: string; unit_id: string }>;
}

export default function PerUnitVisualEditorPage({ params }: PageProps) {
  const { adoption_id, unit_id } = use(params);
  const teacher = useTeacher();
  const schoolId = teacher?.school_id;

  const list = useQuery({
    queryKey: ["section-visuals", schoolId, adoption_id, unit_id],
    queryFn: () => listSectionVisuals(schoolId!, adoption_id, unit_id),
    enabled: !!schoolId,
    retry: false,
  });

  if (!teacher) {
    return (
      <div className="p-6">
        <p className="text-sm text-gray-500">Loading…</p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-5xl space-y-4 p-6">
      <header>
        <p className="text-xs uppercase tracking-wide text-gray-500">
          Edit visuals · {unit_id}
        </p>
        <h1 className="text-2xl font-bold text-gray-900">
          {list.data?.title ?? unit_id}
        </h1>
        {list.data && (
          <p className="mt-1 text-xs text-gray-500">
            Latest override:{" "}
            <span className="font-mono">
              v{list.data.override_version}
            </span>{" "}
            · status:{" "}
            <span
              className={
                list.data.override_status === "approved"
                  ? "text-emerald-700"
                  : list.data.override_status === "pending_review"
                    ? "text-amber-700"
                    : "text-gray-700"
              }
            >
              {list.data.override_status}
            </span>
          </p>
        )}
      </header>

      {list.isLoading && (
        <div className="flex items-center gap-2 text-sm text-gray-500">
          <Loader2 className="h-4 w-4 animate-spin" /> Loading sections…
        </div>
      )}

      {list.isError && (
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-start gap-2 rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
              <div>
                <p className="font-semibold">No tutorial override loaded.</p>
                <p className="mt-1 text-amber-800">
                  Most likely you have not imported this unit&apos;s content
                  into your school yet. Go to{" "}
                  <code className="rounded bg-amber-100 px-1 py-0.5 text-xs">
                    /school/content/[adoption]/...
                  </code>{" "}
                  and import the unit, then return here.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {list.data?.sections.map((section) => (
        <SectionEditor
          key={section.section_id}
          schoolId={schoolId!}
          adoptionId={adoption_id}
          unitId={unit_id}
          section={section}
        />
      ))}
    </div>
  );
}

// ── Per-section editor card ──────────────────────────────────────────────

function SectionEditor({
  schoolId,
  adoptionId,
  unitId,
  section,
}: {
  schoolId: string;
  adoptionId: string;
  unitId: string;
  section: SectionSummary;
}) {
  const qc = useQueryClient();
  const [text, setText] = useState(() =>
    JSON.stringify(section.visuals ?? [], null, 2),
  );
  const [parseError, setParseError] = useState<string | null>(null);
  const [savedAt, setSavedAt] = useState<Date | null>(null);
  const [showPreview, setShowPreview] = useState(true);

  // Reset text when the source data refreshes.
  useEffect(() => {
    setText(JSON.stringify(section.visuals ?? [], null, 2));
    setParseError(null);
  }, [section]);

  const save = useMutation({
    mutationFn: async () => {
      let parsed: VisualBlock[];
      try {
        parsed = JSON.parse(text);
        if (!Array.isArray(parsed)) {
          throw new Error("Top-level value must be a JSON array");
        }
      } catch (e) {
        throw new Error(`JSON parse error: ${(e as Error).message}`);
      }
      return putSectionVisuals(schoolId, {
        adoptionId,
        unitId,
        sectionId: section.section_id,
        visuals: parsed,
      });
    },
    onSuccess: () => {
      setSavedAt(new Date());
      setParseError(null);
      qc.invalidateQueries({
        queryKey: ["section-visuals", schoolId, adoptionId, unitId],
      });
    },
    onError: (err: Error & { response?: { data?: { detail?: string } } }) => {
      setParseError(err.response?.data?.detail ?? err.message);
    },
  });

  // Live preview parse — best-effort, not a save gate
  let livePreviewBlocks: VisualBlock[] | null = null;
  let livePreviewError: string | null = null;
  try {
    const parsed = JSON.parse(text);
    if (Array.isArray(parsed)) {
      livePreviewBlocks = parsed;
    } else {
      livePreviewError = "Top-level value must be a JSON array.";
    }
  } catch (e) {
    livePreviewError = (e as Error).message;
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between text-base">
          <span>
            <span className="mr-2 rounded bg-gray-100 px-1.5 py-0.5 font-mono text-xs">
              {section.section_id}
            </span>
            {section.title}
          </span>
          <span className="text-xs font-normal text-gray-500">
            {(livePreviewBlocks ?? section.visuals ?? []).length} block(s)
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div>
          <Label htmlFor={`json-${section.section_id}`}>
            <span className="inline-flex items-center gap-1.5">
              <Code className="h-3.5 w-3.5 text-gray-500" />
              visuals[] (JSON)
            </span>
          </Label>
          <textarea
            id={`json-${section.section_id}`}
            value={text}
            onChange={(e) => setText(e.target.value)}
            className="mt-1 h-56 w-full rounded-md border border-gray-300 bg-white p-3 font-mono text-xs leading-relaxed text-gray-800 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            spellCheck={false}
          />
          <p className="mt-1 text-xs text-gray-500">
            Each block is{" "}
            <code className="rounded bg-gray-100 px-1">
              {`{ kind, heading?, items: [{src, alt, caption?, poster?, duration?}] }`}
            </code>
            . `kind` must be one of{" "}
            <code className="rounded bg-gray-100 px-1">image</code>,{" "}
            <code className="rounded bg-gray-100 px-1">image-grid</code>,{" "}
            <code className="rounded bg-gray-100 px-1">animated-svg</code>,{" "}
            <code className="rounded bg-gray-100 px-1">video</code>.
          </p>
        </div>

        {parseError && (
          <div className="flex items-start gap-2 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-800">
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
            <span>{parseError}</span>
          </div>
        )}

        <div className="flex items-center justify-between gap-2">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => setShowPreview((v) => !v)}
          >
            <Eye className="mr-1.5 h-3.5 w-3.5" />
            {showPreview ? "Hide" : "Show"} preview
          </Button>
          <div className="flex items-center gap-2">
            {savedAt && (
              <span className="flex items-center gap-1 text-xs text-emerald-700">
                <CheckCircle2 className="h-3.5 w-3.5" />
                Saved at {savedAt.toLocaleTimeString()}
              </span>
            )}
            <Button
              type="button"
              size="sm"
              onClick={() => save.mutate()}
              disabled={save.isPending || livePreviewError !== null}
            >
              {save.isPending ? (
                <>
                  <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
                  Saving…
                </>
              ) : (
                <>
                  <Save className="mr-1.5 h-3.5 w-3.5" />
                  Save section
                </>
              )}
            </Button>
          </div>
        </div>

        {showPreview && (
          <div className="rounded-md border border-gray-200 bg-gray-50 p-3">
            <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-600">
              Live preview
            </p>
            {livePreviewError ? (
              <p className="text-xs text-amber-700">
                Cannot render — fix the JSON above.
              </p>
            ) : (
              <VisualSlot visuals={livePreviewBlocks ?? []} />
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
