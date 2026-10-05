"use client";

import { useEffect, useState } from "react";
import api from "@/lib/api/client";
import type { VisualHint, WikimediaImage } from "@/lib/types/api";

interface Props {
  hint: VisualHint;
}

export function WikimediaVisual({ hint }: Props) {
  const [image, setImage] = useState<WikimediaImage | null>(null);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");

  useEffect(() => {
    let cancelled = false;
    api
      .get<WikimediaImage>("/content/visuals/wikimedia", {
        params: { query: hint.query },
      })
      .then((res) => {
        if (!cancelled) {
          setImage(res.data);
          setStatus("ready");
        }
      })
      .catch(() => {
        if (!cancelled) setStatus("error");
      });
    return () => {
      cancelled = true;
    };
  }, [hint.query]);

  if (status === "error") return null;

  if (status === "loading") {
    return (
      <div
        className="my-4 h-48 w-full animate-pulse rounded-lg bg-gray-200"
        aria-hidden="true"
      />
    );
  }

  if (!image) return null;

  return (
    <figure className="my-4 overflow-hidden rounded-lg border border-gray-200 bg-white shadow-sm">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={image.thumbnail_url}
        alt={hint.caption}
        loading="lazy"
        className="h-auto w-full object-cover"
      />
      <figcaption className="flex items-start justify-between gap-2 border-t border-gray-100 bg-gray-50 px-3 py-2 text-xs text-gray-600">
        <span>{hint.caption}</span>
        <a
          href={`https://commons.wikimedia.org/wiki/File:${encodeURIComponent(image.title)}`}
          target="_blank"
          rel="noopener noreferrer"
          className="shrink-0 text-gray-400 hover:text-gray-600"
          aria-label={`View ${image.title} on Wikimedia Commons`}
        >
          {image.license} · Wikimedia
        </a>
      </figcaption>
    </figure>
  );
}
