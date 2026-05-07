"use client";

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { listVisuals, type VisualAsset } from "@/lib/api/visuals";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Loader2,
  FolderOpen,
  Search,
  CheckCircle2,
  Image as ImageIcon,
  Film,
  X,
} from "lucide-react";

/**
 * AssetPicker (issue #318 phase 2c-3 polish++).
 *
 * Inline panel that shows previously-uploaded visual assets for the school
 * and lets the user click one to fill an `src` field. Designed to be the
 * default way an admin attaches visuals — no more URL typing.
 *
 * Used inside the per-unit visual editor next to each item's src input.
 *
 * Props:
 *   schoolId       — required for the listVisuals call
 *   curriculumId   — optional filter (sent to the backend list endpoint)
 *   unitId         — optional filter (sent to the backend list endpoint)
 *   currentSrc     — currently-selected URL; highlighted in the list
 *   onSelect       — invoked with the chosen asset URL
 *   onClose        — invoked to dismiss the panel
 */

interface AssetPickerProps {
  schoolId: string;
  curriculumId?: string;
  unitId?: string;
  currentSrc?: string;
  onSelect: (url: string) => void;
  onClose: () => void;
}

export function AssetPicker({
  schoolId,
  curriculumId,
  unitId,
  currentSrc,
  onSelect,
  onClose,
}: AssetPickerProps) {
  const [query, setQuery] = useState("");

  const list = useQuery({
    queryKey: ["asset-picker", schoolId, curriculumId, unitId],
    queryFn: () =>
      listVisuals(schoolId, {
        curriculumId: curriculumId || undefined,
        unitId: unitId || undefined,
      }),
    enabled: !!schoolId,
    staleTime: 30_000,
  });

  const filtered = useMemo(() => {
    const all = list.data ?? [];
    if (!query.trim()) return all;
    const q = query.toLowerCase();
    return all.filter(
      (a) =>
        a.path.toLowerCase().includes(q) || a.url.toLowerCase().includes(q),
    );
  }, [list.data, query]);

  return (
    <div className="mt-1 rounded-md border border-blue-200 bg-blue-50/40 p-3 shadow-sm">
      <div className="mb-2 flex items-center justify-between">
        <span className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-blue-800">
          <FolderOpen className="h-3.5 w-3.5" />
          Pick from uploaded assets
          {(curriculumId || unitId) && (
            <span className="rounded bg-blue-100 px-1.5 py-0.5 font-mono text-[10px] font-normal text-blue-700">
              {[curriculumId, unitId].filter(Boolean).join(" / ")}
            </span>
          )}
        </span>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={onClose}
          className="h-6 px-2 text-gray-600"
        >
          <X className="h-3 w-3" />
        </Button>
      </div>

      <div className="relative mb-2">
        <Search className="absolute left-2 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-gray-400" />
        <Input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Filter by path or URL…"
          className="pl-7 text-xs"
        />
      </div>

      {list.isLoading && (
        <div className="flex items-center gap-2 px-2 py-3 text-xs text-gray-500">
          <Loader2 className="h-3.5 w-3.5 animate-spin" /> Loading…
        </div>
      )}

      {list.isError && (
        <p className="px-2 py-2 text-xs text-red-700">
          Failed to load assets.
        </p>
      )}

      {!list.isLoading && !list.isError && filtered.length === 0 && (
        <p className="px-2 py-3 text-xs text-gray-500">
          {(list.data ?? []).length === 0
            ? "No assets uploaded yet. Use the Visual Library page to upload."
            : "No matches for that filter."}
        </p>
      )}

      {filtered.length > 0 && (
        <ul className="max-h-64 divide-y divide-blue-100 overflow-y-auto rounded border border-blue-100 bg-white">
          {filtered.map((asset) => (
            <AssetRow
              key={asset.path}
              asset={asset}
              isCurrent={asset.url === currentSrc}
              onClick={() => {
                onSelect(asset.url);
                onClose();
              }}
            />
          ))}
        </ul>
      )}
    </div>
  );
}

function AssetRow({
  asset,
  isCurrent,
  onClick,
}: {
  asset: VisualAsset;
  isCurrent: boolean;
  onClick: () => void;
}) {
  const isVideo = /\.(mp4|webm)$/i.test(asset.path);
  const isSvg = /\.svg$/i.test(asset.path);
  const Icon = isVideo ? Film : ImageIcon;

  return (
    <li>
      <button
        type="button"
        onClick={onClick}
        className={`flex w-full items-center gap-3 px-3 py-2 text-left transition-colors hover:bg-blue-50 ${
          isCurrent ? "bg-blue-50" : ""
        }`}
      >
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded border border-blue-100 bg-white">
          {isSvg ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={asset.url}
              alt=""
              aria-hidden="true"
              className="h-full w-full object-contain p-0.5"
            />
          ) : (
            <Icon className="h-4 w-4 text-gray-400" />
          )}
        </div>
        <div className="min-w-0 flex-1">
          <div className="truncate font-mono text-xs text-gray-800">
            {asset.path.split("/").pop()}
          </div>
          <div className="truncate text-[10px] text-gray-500">{asset.path}</div>
        </div>
        {isCurrent && (
          <CheckCircle2
            className="h-4 w-4 shrink-0 text-emerald-600"
            aria-label="Currently selected"
          />
        )}
      </button>
    </li>
  );
}
