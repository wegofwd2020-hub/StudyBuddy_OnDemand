"use client";

import { useState } from "react";
import { Eye, PlayCircle, Film } from "lucide-react";
import type { VisualBlock, VisualItem } from "@/lib/types/api";

/**
 * Renders the `visuals` array attached to a tutorial section.
 *
 * After issue #318, this component is data-driven from `section.visuals`
 * in the tutorial JSON. The previous hard-coded `VISUAL_MAP` keyed on
 * `${unit_id}::${section_id}` has been retired — the per-unit visual
 * declarations now live alongside the rest of the section content.
 */

interface VisualSlotProps {
  visuals?: VisualBlock[];
}

export function VisualSlot({ visuals }: VisualSlotProps) {
  if (!visuals || visuals.length === 0) return null;
  return (
    <div className="mt-4 space-y-3">
      {visuals.map((block, i) => (
        <VisualBlockRender key={i} block={block} />
      ))}
    </div>
  );
}

function VisualBlockRender({ block }: { block: VisualBlock }) {
  return (
    <div className="rounded-md border border-emerald-200 bg-emerald-50 p-3">
      <div className="mb-2 flex items-center gap-2">
        <Eye className="h-3.5 w-3.5 text-emerald-700" aria-hidden="true" />
        <h4 className="text-xs font-semibold uppercase tracking-wide text-emerald-800">
          {block.heading ?? "Visual explanation"}
        </h4>
      </div>
      {block.kind === "image-grid" ? (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-2 md:grid-cols-2 lg:grid-cols-2">
          {block.items.map((item, i) => (
            <VisualImage key={i} item={item} />
          ))}
        </div>
      ) : block.kind === "video" ? (
        <div className="space-y-3">
          {block.items.map((item, i) => (
            <VisualVideo key={i} item={item} />
          ))}
        </div>
      ) : (
        <div className="space-y-3">
          {block.items.map((item, i) => (
            <VisualImage key={i} item={item} />
          ))}
        </div>
      )}
    </div>
  );
}

function VisualVideo({ item }: { item: VisualItem }) {
  const [playing, setPlaying] = useState(false);

  if (!playing) {
    return (
      <figure className="overflow-hidden rounded border border-emerald-200 bg-white">
        <button
          type="button"
          onClick={() => setPlaying(true)}
          aria-label={`Play video: ${item.alt}`}
          className="group relative flex w-full items-center justify-center gap-3 bg-gradient-to-br from-slate-900 to-slate-700 px-6 py-10 text-emerald-50 transition-colors hover:from-slate-800 hover:to-slate-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-400 focus-visible:ring-offset-2"
        >
          {item.poster && (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={item.poster}
              alt=""
              aria-hidden="true"
              className="absolute inset-0 h-full w-full object-cover opacity-50"
            />
          )}
          <span className="relative flex items-center gap-3">
            <PlayCircle
              className="h-12 w-12 text-emerald-300 transition-transform group-hover:scale-110"
              aria-hidden="true"
            />
            <span className="flex flex-col items-start">
              <span className="text-base font-semibold">Play video</span>
              <span className="flex items-center gap-2 text-xs text-emerald-200">
                <Film className="h-3 w-3" aria-hidden="true" />
                <span>{item.alt}</span>
                {item.duration && <span className="text-emerald-300">· {item.duration}</span>}
              </span>
            </span>
          </span>
        </button>
        {item.caption && (
          <figcaption className="border-t border-emerald-100 bg-emerald-50/40 px-2 py-1 text-xs text-emerald-900">
            {item.caption}
          </figcaption>
        )}
      </figure>
    );
  }

  return (
    <figure className="overflow-hidden rounded border border-emerald-200 bg-black">
      <video
        controls
        autoPlay
        preload="metadata"
        className="h-auto w-full"
        src={item.src}
        poster={item.poster}
      >
        Your browser does not support embedded video.
      </video>
      {item.caption && (
        <figcaption className="border-t border-emerald-100 bg-emerald-50/40 px-2 py-1 text-xs text-emerald-900">
          {item.caption}
        </figcaption>
      )}
    </figure>
  );
}

function VisualImage({ item }: { item: VisualItem }) {
  return (
    <figure className="overflow-hidden rounded border border-emerald-200 bg-white">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={item.src}
        alt={item.alt}
        loading="lazy"
        className="h-auto w-full"
      />
      {item.caption && (
        <figcaption className="border-t border-emerald-100 bg-emerald-50/40 px-2 py-1 text-xs text-emerald-900">
          {item.caption}
        </figcaption>
      )}
    </figure>
  );
}
