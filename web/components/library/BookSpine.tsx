"use client";

import type { CSSProperties } from "react";
import { ChevronUp, FlaskConical } from "lucide-react";
import { useSubjectPalette } from "@/lib/theme/SchoolThemeContext";
import type { UnitStatus } from "@/lib/types/api";
import { STATUS_CONFIG } from "./status-config";
import { cn } from "@/lib/utils";

interface BookSpineProps {
  unitId: string;
  title: string;
  subjectKey: string;
  /** Status icon. When omitted no status icon renders (e.g. adoption spines). */
  status?: UnitStatus;
  hasLab?: boolean;
  isOpen: boolean;
  onToggle: (unitId: string) => void;
  /** Replace the subject-palette accent color. Used when status, not subject, drives color. */
  accentOverride?: string;
  /** Visually dim the spine (e.g. deactivated or platform-archived adoptions). */
  dim?: boolean;
}

export function BookSpine({
  unitId,
  title,
  subjectKey,
  status,
  hasLab,
  isOpen,
  onToggle,
  accentOverride,
  dim,
}: BookSpineProps) {
  // Hooks must be called unconditionally — always resolve the palette and only
  // swap the resulting accent value when an override is supplied.
  const palette = useSubjectPalette(subjectKey);
  const accent = accentOverride ?? palette.accent;
  const statusEntry = status ? STATUS_CONFIG[status] : null;

  const ringStyle = { ["--tw-ring-color" as string]: accent } as CSSProperties;

  return (
    <li role="listitem" className="snap-start shrink-0">
      <button
        data-spine="true"
        type="button"
        aria-expanded={isOpen}
        onClick={() => onToggle(unitId)}
        style={{ borderColor: accent, ...ringStyle }}
        className={cn(
          "group flex flex-col rounded-md p-3 text-left",
          "border-2 bg-stone-50",
          "border-l-[6px]",
          "shadow-[1px_0_0_#d4d4d8,0_1px_2px_rgba(0,0,0,0.08)]",
          "hover:bg-stone-100 hover:shadow-[1px_0_0_#a8a29e,0_4px_10px_rgba(0,0,0,0.12)]",
          "transition-[width,box-shadow,background-color] duration-150 ease-out motion-reduce:transition-none",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2",
          "max-sm:w-full max-sm:h-auto",
          "sm:w-[88px] sm:h-56 lg:w-24",
          isOpen &&
            "sm:w-40 lg:w-44 bg-white shadow-[1px_0_0_#a8a29e,3px_0_0_#fafaf9,4px_0_0_#d4d4d8,0_4px_10px_rgba(0,0,0,0.14)]",
          dim && "opacity-60 hover:opacity-100",
        )}
      >
        <span
          className="font-medium text-xs leading-tight line-clamp-4 text-gray-900"
          aria-hidden="true"
        >
          {title}
        </span>
        <span className="mt-auto flex items-center gap-1 pt-2">
          {statusEntry ? (
            <statusEntry.icon
              className={cn("h-3.5 w-3.5", statusEntry.color)}
              aria-hidden="true"
            />
          ) : null}
          {hasLab ? (
            <FlaskConical className="h-3 w-3 text-purple-600" aria-hidden="true" />
          ) : null}
          {isOpen ? (
            <ChevronUp className="ml-auto h-3.5 w-3.5 text-gray-500" aria-hidden="true" />
          ) : null}
        </span>
        <span className="sr-only">
          {title}
          {statusEntry ? `, status ${statusEntry.label}` : ""}
          {hasLab ? ", has lab" : ""}
        </span>
      </button>
    </li>
  );
}
