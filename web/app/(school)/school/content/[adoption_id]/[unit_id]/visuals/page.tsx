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
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Loader2,
  Save,
  AlertCircle,
  CheckCircle2,
  Eye,
  Plus,
  Trash2,
  Image as ImageIcon,
  Film,
} from "lucide-react";
import type { VisualBlock, VisualItem } from "@/lib/types/api";

/**
 * /school/content/{adoption_id}/{unit_id}/visuals
 *
 * Per-unit visual editor (issue #318 phase 2c-3 + form-based polish).
 *
 * Form-based editor with per-section block + per-block item controls.
 * Live preview renders through the same <VisualSlot> the student
 * tutorial uses, so what the school admin sees is what students see.
 *
 * Save → PUT /api/v1/schools/{school_id}/visuals/sections appends a
 * new draft override row through the existing Phase D review flow.
 */

const VISUAL_KINDS = ["image", "image-grid", "animated-svg", "video"] as const;
type VisualKind = (typeof VISUAL_KINDS)[number];

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
            <span className="font-mono">v{list.data.override_version}</span>
            {" · status: "}
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
                  into your school yet. Import the unit first, then return here.
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
  const [blocks, setBlocks] = useState<VisualBlock[]>(() => section.visuals ?? []);
  const [savedAt, setSavedAt] = useState<Date | null>(null);
  const [showPreview, setShowPreview] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Reset local state when the source data refreshes.
  useEffect(() => {
    setBlocks(section.visuals ?? []);
    setError(null);
  }, [section]);

  const save = useMutation({
    mutationFn: () =>
      putSectionVisuals(schoolId, {
        adoptionId,
        unitId,
        sectionId: section.section_id,
        visuals: blocks,
      }),
    onSuccess: () => {
      setSavedAt(new Date());
      setError(null);
      qc.invalidateQueries({
        queryKey: ["section-visuals", schoolId, adoptionId, unitId],
      });
    },
    onError: (err: Error & { response?: { data?: { detail?: string } } }) => {
      setError(err.response?.data?.detail ?? err.message ?? "Save failed");
    },
  });

  function addBlock() {
    setBlocks([
      ...blocks,
      { kind: "image", heading: "", items: [{ src: "", alt: "" }] },
    ]);
  }

  function updateBlock(idx: number, patch: Partial<VisualBlock>) {
    setBlocks(blocks.map((b, i) => (i === idx ? { ...b, ...patch } : b)));
  }

  function removeBlock(idx: number) {
    setBlocks(blocks.filter((_, i) => i !== idx));
  }

  // Validate before save: every block must have ≥1 item; every item must have src + alt.
  const validation = (() => {
    for (const [bi, b] of blocks.entries()) {
      if (!b.items || b.items.length === 0)
        return `Block ${bi + 1}: needs at least one item`;
      for (const [ii, it] of b.items.entries()) {
        if (!it.src.trim()) return `Block ${bi + 1}, item ${ii + 1}: src required`;
        if (!it.alt.trim()) return `Block ${bi + 1}, item ${ii + 1}: alt required`;
      }
    }
    return null;
  })();

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
            {blocks.length} block(s)
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {blocks.map((block, bi) => (
          <BlockEditor
            key={bi}
            index={bi}
            block={block}
            onChange={(patch) => updateBlock(bi, patch)}
            onRemove={() => removeBlock(bi)}
          />
        ))}

        <Button type="button" variant="outline" size="sm" onClick={addBlock}>
          <Plus className="mr-1.5 h-3.5 w-3.5" /> Add visual block
        </Button>

        {(error || validation) && (
          <div className="flex items-start gap-2 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-800">
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
            <span>{error ?? validation}</span>
          </div>
        )}

        <div className="flex items-center justify-between gap-2 border-t border-gray-100 pt-3">
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
              disabled={save.isPending || validation !== null}
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
            {validation ? (
              <p className="text-xs text-amber-700">
                Cannot render — fix validation issues above.
              </p>
            ) : (
              <VisualSlot visuals={blocks} />
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// ── Per-block editor ─────────────────────────────────────────────────────

function BlockEditor({
  index,
  block,
  onChange,
  onRemove,
}: {
  index: number;
  block: VisualBlock;
  onChange: (patch: Partial<VisualBlock>) => void;
  onRemove: () => void;
}) {
  const isVideo = block.kind === "video";

  function updateItem(idx: number, patch: Partial<VisualItem>) {
    const items = (block.items ?? []).map((it, i) =>
      i === idx ? { ...it, ...patch } : it,
    );
    onChange({ items });
  }
  function addItem() {
    onChange({
      items: [...(block.items ?? []), { src: "", alt: "" }],
    });
  }
  function removeItem(idx: number) {
    onChange({
      items: (block.items ?? []).filter((_, i) => i !== idx),
    });
  }

  return (
    <div className="rounded-md border border-gray-200 bg-white p-3">
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          {isVideo ? (
            <Film className="h-4 w-4 text-gray-500" />
          ) : (
            <ImageIcon className="h-4 w-4 text-gray-500" />
          )}
          <span className="text-xs font-semibold uppercase tracking-wide text-gray-600">
            Block {index + 1}
          </span>
        </div>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={onRemove}
          className="text-red-600 hover:bg-red-50"
        >
          <Trash2 className="h-3.5 w-3.5" />
        </Button>
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <div>
          <Label htmlFor={`kind-${index}`}>Kind</Label>
          <select
            id={`kind-${index}`}
            value={block.kind}
            onChange={(e) =>
              onChange({ kind: e.target.value as VisualKind })
            }
            className="mt-1 block h-9 w-full rounded-md border border-gray-300 bg-white px-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            {VISUAL_KINDS.map((k) => (
              <option key={k} value={k}>
                {k}
              </option>
            ))}
          </select>
        </div>
        <div className="sm:col-span-2">
          <Label htmlFor={`heading-${index}`}>Heading (optional)</Label>
          <Input
            id={`heading-${index}`}
            value={block.heading ?? ""}
            onChange={(e) => onChange({ heading: e.target.value })}
            placeholder="e.g. Set operations — Venn diagrams"
          />
        </div>
      </div>

      <div className="mt-3 space-y-2">
        <p className="text-xs font-medium text-gray-700">
          Items ({(block.items ?? []).length})
        </p>
        {(block.items ?? []).map((item, ii) => (
          <ItemEditor
            key={ii}
            index={ii}
            item={item}
            isVideo={isVideo}
            onChange={(patch) => updateItem(ii, patch)}
            onRemove={() => removeItem(ii)}
          />
        ))}
        <Button type="button" variant="outline" size="sm" onClick={addItem}>
          <Plus className="mr-1.5 h-3.5 w-3.5" /> Add item
        </Button>
      </div>
    </div>
  );
}

// ── Per-item editor ──────────────────────────────────────────────────────

function ItemEditor({
  index,
  item,
  isVideo,
  onChange,
  onRemove,
}: {
  index: number;
  item: VisualItem;
  isVideo: boolean;
  onChange: (patch: Partial<VisualItem>) => void;
  onRemove: () => void;
}) {
  return (
    <div className="rounded border border-gray-100 bg-gray-50/40 p-2">
      <div className="mb-1.5 flex items-center justify-between">
        <span className="text-xs font-semibold text-gray-600">
          Item {index + 1}
        </span>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={onRemove}
          className="h-6 px-2 text-red-600 hover:bg-red-50"
        >
          <Trash2 className="h-3 w-3" />
        </Button>
      </div>

      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
        <div>
          <Label htmlFor={`src-${index}`} className="text-xs">
            src <span className="text-red-500">*</span>
          </Label>
          <Input
            id={`src-${index}`}
            value={item.src}
            onChange={(e) => onChange({ src: e.target.value })}
            placeholder="/visuals/_legacy/G11-PHYS-002/xt-uam.svg"
            className="font-mono text-xs"
          />
        </div>
        <div>
          <Label htmlFor={`alt-${index}`} className="text-xs">
            alt <span className="text-red-500">*</span>
          </Label>
          <Input
            id={`alt-${index}`}
            value={item.alt}
            onChange={(e) => onChange({ alt: e.target.value })}
            placeholder="x-t parabola for UAM"
          />
        </div>
        <div className="sm:col-span-2">
          <Label htmlFor={`caption-${index}`} className="text-xs">
            caption (optional)
          </Label>
          <Textarea
            id={`caption-${index}`}
            value={item.caption ?? ""}
            onChange={(e) => onChange({ caption: e.target.value })}
            placeholder="x = vᵢt + ½at² → parabolic"
            rows={2}
            className="text-xs"
          />
        </div>

        {isVideo && (
          <>
            <div>
              <Label htmlFor={`duration-${index}`} className="text-xs">
                duration (e.g. 0:24)
              </Label>
              <Input
                id={`duration-${index}`}
                value={item.duration ?? ""}
                onChange={(e) => onChange({ duration: e.target.value })}
                placeholder="0:24"
              />
            </div>
            <div>
              <Label htmlFor={`poster-${index}`} className="text-xs">
                poster (optional)
              </Label>
              <Input
                id={`poster-${index}`}
                value={item.poster ?? ""}
                onChange={(e) => onChange({ poster: e.target.value })}
                placeholder="/visuals/_legacy/.../poster.jpg"
                className="font-mono text-xs"
              />
            </div>
          </>
        )}
      </div>
    </div>
  );
}
