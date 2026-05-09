"use client";

import { useRef, type KeyboardEvent, type ReactNode } from "react";
import { cn } from "@/lib/utils";

interface ShelfProps {
  children: ReactNode;
  ariaLabel?: string;
}

// Roving tabindex: spines opt in by setting data-spine="true" so the
// keyboard handler can locate them without a Context handshake.
export function Shelf({ children, ariaLabel }: ShelfProps) {
  const ref = useRef<HTMLOListElement | null>(null);

  function focusSpineAt(index: number) {
    const spines = ref.current?.querySelectorAll<HTMLElement>('[data-spine="true"]');
    if (!spines || spines.length === 0) return;
    const clamped = Math.max(0, Math.min(spines.length - 1, index));
    spines[clamped]?.focus();
  }

  function indexOfTarget(target: EventTarget | null): number {
    const spines = ref.current?.querySelectorAll<HTMLElement>('[data-spine="true"]');
    if (!spines) return -1;
    const list = Array.from(spines);
    if (!(target instanceof HTMLElement)) return -1;
    const owner = target.closest<HTMLElement>('[data-spine="true"]');
    return owner ? list.indexOf(owner) : -1;
  }

  function onKeyDown(e: KeyboardEvent<HTMLOListElement>) {
    const current = indexOfTarget(e.target);
    if (current < 0) return;
    switch (e.key) {
      case "ArrowRight":
      case "ArrowDown":
        e.preventDefault();
        focusSpineAt(current + 1);
        break;
      case "ArrowLeft":
      case "ArrowUp":
        e.preventDefault();
        focusSpineAt(current - 1);
        break;
      case "Home":
        e.preventDefault();
        focusSpineAt(0);
        break;
      case "End": {
        e.preventDefault();
        const spines = ref.current?.querySelectorAll<HTMLElement>('[data-spine="true"]');
        if (spines) focusSpineAt(spines.length - 1);
        break;
      }
      default:
        break;
    }
  }

  return (
    <ol
      ref={ref}
      role="list"
      aria-label={ariaLabel}
      onKeyDown={onKeyDown}
      className={cn(
        "relative flex flex-col gap-3 pb-2",
        "sm:snap-x sm:snap-mandatory sm:flex-row sm:overflow-x-auto",
        "sm:border-b-2 sm:border-stone-400/70 sm:pb-3",
        "sm:shadow-[0_5px_6px_-5px_rgba(0,0,0,0.18)]",
      )}
    >
      {children}
    </ol>
  );
}
