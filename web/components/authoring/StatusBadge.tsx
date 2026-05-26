"use client";

import { cn } from "@/lib/utils";
import type { AuthoringStatus } from "@/lib/api/authoring";

const STATUS_STYLES: Record<string, string> = {
  draft: "bg-gray-100 text-gray-600",
  analyzing: "bg-amber-100 text-amber-700",
  analyzed: "bg-sky-100 text-sky-700",
  structured: "bg-indigo-100 text-indigo-700",
  generating: "bg-amber-100 text-amber-700",
  generated: "bg-violet-100 text-violet-700",
  published: "bg-emerald-100 text-emerald-700",
};

export function StatusBadge({
  status,
  className,
}: {
  status: AuthoringStatus | string | null | undefined;
  className?: string;
}) {
  const s = status ?? "draft";
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium",
        STATUS_STYLES[s] ?? "bg-gray-100 text-gray-600",
        className,
      )}
    >
      {s}
    </span>
  );
}
