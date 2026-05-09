"use client";

import { useEffect, type ReactNode } from "react";
import { X } from "lucide-react";

interface BookOpenProps {
  title: string;
  onClose: () => void;
  children: ReactNode;
  /** Small uppercase label next to the title. Defaults to "Topics". */
  subheading?: string;
  /** Override the region's aria-label. Defaults to `Details for ${title}`. */
  ariaLabel?: string;
}

export function BookOpen({
  title,
  onClose,
  children,
  subheading = "Topics",
  ariaLabel,
}: BookOpenProps) {
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div
      role="region"
      aria-label={ariaLabel ?? `${subheading} for ${title}`}
      className="mt-2 rounded-lg border border-gray-200 bg-white p-4 transition-all duration-150 motion-reduce:transition-none"
    >
      <div className="mb-3 flex items-center gap-2">
        <span className="text-sm font-semibold text-gray-900">{title}</span>
        {subheading ? (
          <span className="text-xs tracking-wide text-gray-400 uppercase">
            {subheading}
          </span>
        ) : null}
        <button
          type="button"
          aria-label="Close"
          onClick={onClose}
          className="ml-auto rounded p-1 text-gray-500 hover:bg-gray-100 focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:outline-none"
        >
          <X className="h-4 w-4" aria-hidden="true" />
        </button>
      </div>
      {children}
    </div>
  );
}
