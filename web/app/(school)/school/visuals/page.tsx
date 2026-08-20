"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { describeMissingUploadFields } from "@/lib/school/visual-upload";
import { useTeacher } from "@/lib/hooks/useTeacher";
import {
  uploadVisual,
  listVisuals,
  deleteVisual,
  type VisualAsset,
} from "@/lib/api/visuals";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Loader2,
  Upload as UploadIcon,
  Trash2,
  ImageIcon,
  Film,
  AlertCircle,
} from "lucide-react";

/**
 * /school/visuals — visual asset library (issue #318 phase 2c).
 *
 * Lists, uploads, and deletes visual assets keyed by curriculum / unit /
 * section. Per-section override integration with the tutorial JSON
 * `visuals[]` array is a follow-up slice; for now this page lets a school
 * admin manage the asset pool that the tutorial JSON will reference.
 */
// IDs must start alphanumeric, then alnum / '.' '_' '-' — mirrors the backend
// guard so junk like "===============" is caught before upload (feedback #445).
const ID_RE = /^[A-Za-z0-9][A-Za-z0-9._-]*$/;

export default function VisualLibraryPage() {
  const teacher = useTeacher();
  const qc = useQueryClient();

  // Filter state for listing
  const [filterCurriculum, setFilterCurriculum] = useState("");
  const [filterUnit, setFilterUnit] = useState("");

  // Upload form state
  const [upCurriculum, setUpCurriculum] = useState("");
  const [upUnit, setUpUnit] = useState("");
  const [upSection, setUpSection] = useState("s1");
  const [upFile, setUpFile] = useState<File | null>(null);
  const [upError, setUpError] = useState<string | null>(null);

  const schoolId = teacher?.school_id;

  const list = useQuery({
    queryKey: ["visuals", schoolId, filterCurriculum, filterUnit],
    queryFn: () =>
      listVisuals(schoolId!, {
        curriculumId: filterCurriculum || undefined,
        unitId: filterUnit || undefined,
      }),
    enabled: !!schoolId,
  });

  const upload = useMutation({
    mutationFn: () =>
      uploadVisual({
        schoolId: schoolId!,
        curriculumId: upCurriculum,
        unitId: upUnit,
        sectionId: upSection,
        file: upFile!,
      }),
    onSuccess: () => {
      setUpFile(null);
      setUpError(null);
      qc.invalidateQueries({ queryKey: ["visuals", schoolId] });
    },
    onError: (err: Error & { response?: { data?: { detail?: string } } }) => {
      setUpError(err.response?.data?.detail ?? err.message ?? "Upload failed");
    },
  });

  const remove = useMutation({
    mutationFn: (path: string) => deleteVisual(schoolId!, path),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["visuals", schoolId] }),
  });

  // True when the user has typed something that isn't a valid ID — drives the hint.
  const showIdHint =
    (upCurriculum.trim().length > 0 && !ID_RE.test(upCurriculum.trim())) ||
    (upUnit.trim().length > 0 && !ID_RE.test(upUnit.trim())) ||
    (upSection.trim().length > 0 && !ID_RE.test(upSection.trim()));

  if (!teacher) {
    return (
      <div className="p-6">
        <p className="text-sm text-gray-500">Loading…</p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-5xl space-y-6 p-6">
      <header>
        <h1 className="text-2xl font-bold text-gray-900">Visual asset library</h1>
        <p className="mt-1 text-sm text-gray-600">
          Upload SVG, PNG, JPG, WebP, MP4, or WebM assets for your curricula. Once
          uploaded, the URL can be added to a tutorial section&apos;s{" "}
          <code className="rounded bg-gray-100 px-1 py-0.5 text-xs">visuals</code> array.
        </p>
      </header>

      {/* Upload card ─────────────────────────────────────────────── */}

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <UploadIcon className="h-4 w-4 text-blue-600" />
            Upload new asset
          </CardTitle>
        </CardHeader>
        <CardContent>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              // Say what is missing rather than leaving an inert button — a
              // disabled control with no message reads as broken (#618).
              const missing = describeMissingUploadFields({
                file: upFile,
                curriculum: upCurriculum,
                unit: upUnit,
                section: upSection,
              });
              if (missing) {
                setUpError(missing);
                return;
              }
              upload.mutate();
            }}
            className="space-y-4"
          >
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
              <div>
                <Label htmlFor="up-curriculum">
                  Curriculum ID{" "}
                  <span className="text-red-500" aria-hidden="true">
                    *
                  </span>
                </Label>
                <Input
                  id="up-curriculum"
                  value={upCurriculum}
                  onChange={(e) => setUpCurriculum(e.target.value)}
                  placeholder="e.g. default-2026-g11-science"
                />
              </div>
              <div>
                <Label htmlFor="up-unit">
                  Unit ID{" "}
                  <span className="text-red-500" aria-hidden="true">
                    *
                  </span>
                </Label>
                <Input
                  id="up-unit"
                  value={upUnit}
                  onChange={(e) => setUpUnit(e.target.value)}
                  placeholder="e.g. G11-PHYS-002"
                />
              </div>
              <div>
                <Label htmlFor="up-section">
                  Section ID{" "}
                  <span className="text-red-500" aria-hidden="true">
                    *
                  </span>
                </Label>
                <Input
                  id="up-section"
                  value={upSection}
                  onChange={(e) => setUpSection(e.target.value)}
                  placeholder="e.g. s1"
                />
              </div>
            </div>
            {showIdHint && (
              <p className="text-xs text-amber-600">
                IDs must start with a letter or number and use only letters, numbers,
                &quot;.&quot;, &quot;_&quot;, or &quot;-&quot;.
              </p>
            )}
            <div>
              <Label htmlFor="up-file">
                File (≤20 MB){" "}
                <span className="text-red-500" aria-hidden="true">
                  *
                </span>
              </Label>
              <Input
                id="up-file"
                type="file"
                accept="image/svg+xml,image/png,image/jpeg,image/webp,video/mp4,video/webm"
                onChange={(e) => setUpFile(e.target.files?.[0] ?? null)}
              />
              {upFile && (
                <p className="mt-1 text-xs text-gray-500">
                  {upFile.name} · {(upFile.size / 1024).toFixed(1)} KB ·{" "}
                  {upFile.type || "unknown type"}
                </p>
              )}
            </div>
            {upError && (
              <div className="flex items-start gap-2 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-800">
                <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
                <span>{upError}</span>
              </div>
            )}
            <Button type="submit" disabled={upload.isPending}>
              {upload.isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Uploading…
                </>
              ) : (
                <>
                  <UploadIcon className="mr-2 h-4 w-4" />
                  Upload
                </>
              )}
            </Button>
          </form>
        </CardContent>
      </Card>

      {/* Filter + list ────────────────────────────────────────────── */}

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Existing assets</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="mb-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div>
              <Label htmlFor="filter-curriculum">Filter — curriculum_id</Label>
              <Input
                id="filter-curriculum"
                value={filterCurriculum}
                onChange={(e) => setFilterCurriculum(e.target.value)}
                placeholder="(any)"
              />
            </div>
            <div>
              <Label htmlFor="filter-unit">Filter — unit_id</Label>
              <Input
                id="filter-unit"
                value={filterUnit}
                onChange={(e) => setFilterUnit(e.target.value)}
                placeholder="(any)"
              />
            </div>
          </div>

          {list.isLoading ? (
            <div className="flex items-center gap-2 text-sm text-gray-500">
              <Loader2 className="h-4 w-4 animate-spin" />
              Loading…
            </div>
          ) : list.isError ? (
            <p className="text-sm text-red-600">Failed to load assets.</p>
          ) : (list.data ?? []).length === 0 ? (
            <p className="text-sm text-gray-500">No assets yet. Upload one above.</p>
          ) : (
            <ul className="divide-y divide-gray-100 rounded-md border border-gray-200 bg-white">
              {(list.data ?? []).map((a) => (
                <AssetRow
                  key={a.path}
                  asset={a}
                  onDelete={() => remove.mutate(a.path)}
                  deleting={remove.isPending && remove.variables === a.path}
                />
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

// ── Asset row ───────────────────────────────────────────────────────────

function AssetRow({
  asset,
  onDelete,
  deleting,
}: {
  asset: VisualAsset;
  onDelete: () => void;
  deleting: boolean;
}) {
  const isVideo = /\.(mp4|webm)$/i.test(asset.path);
  const Icon = isVideo ? Film : ImageIcon;
  return (
    <li className="flex items-center gap-3 px-3 py-2">
      <Icon className="h-4 w-4 shrink-0 text-gray-400" aria-hidden="true" />
      <div className="min-w-0 flex-1">
        <div className="truncate font-mono text-sm text-gray-800">{asset.path}</div>
        <a
          href={asset.url}
          target="_blank"
          rel="noopener noreferrer"
          className="truncate text-xs text-blue-600 hover:underline"
        >
          {asset.url}
        </a>
      </div>
      <Button
        type="button"
        variant="outline"
        size="sm"
        onClick={() => {
          if (
            window.confirm(
              `Delete this asset?\n\n${asset.path}\n\nThis cannot be undone.`,
            )
          ) {
            onDelete();
          }
        }}
        disabled={deleting}
        className="text-red-600 hover:bg-red-50 hover:text-red-700"
      >
        {deleting ? (
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
        ) : (
          <Trash2 className="h-3.5 w-3.5" />
        )}
      </Button>
    </li>
  );
}
