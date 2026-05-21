"use client";

/**
 * Top-bar "Curriculum Management" dropdown (issue #358).
 *
 * Renders only when the logged-in teacher holds a curriculum capability (or is a
 * school_admin superset) — see canManageCurriculum. Groups the curriculum nav
 * that used to live in the left rail. This is a convenience surface; the backend
 * enforces each action's gate independently (hiding a link is never the control).
 */

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { BookMarked, ChevronDown } from "lucide-react";
import { canManageCurriculum, useTeacher } from "@/lib/hooks/useTeacher";
import { cn } from "@/lib/utils";

const CURRICULUM_LINKS: { label: string; href: string }[] = [
  { label: "Browse Catalog", href: "/school/catalog" },
  { label: "Our Library", href: "/school/library" },
  { label: "Content Library", href: "/school/curriculum/content" },
  { label: "Curriculum Builder", href: "/school/curriculum" },
  { label: "Review Queue", href: "/school/review" },
];

export function CurriculumMenu() {
  const teacher = useTeacher();
  const pathname = usePathname() ?? "";
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function onClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  // Hidden entirely unless the teacher may manage curriculum.
  if (!canManageCurriculum(teacher)) return null;

  const active = CURRICULUM_LINKS.some((l) => pathname.startsWith(l.href));

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
        className={cn(
          "flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-sm transition-colors",
          active
            ? "border-blue-500 bg-blue-50 font-medium text-blue-700"
            : "border-gray-200 text-gray-600 hover:border-gray-400 hover:text-gray-900",
        )}
      >
        <BookMarked className="h-4 w-4" aria-hidden />
        Curriculum Management
        <ChevronDown className="h-3.5 w-3.5" aria-hidden />
      </button>

      {open && (
        <div
          role="menu"
          className="absolute right-0 z-50 mt-1 w-52 rounded-md border border-gray-100 bg-white py-1 shadow-lg"
        >
          {CURRICULUM_LINKS.map((l) => (
            <Link
              key={l.href}
              role="menuitem"
              href={l.href}
              onClick={() => setOpen(false)}
              className={cn(
                "block px-4 py-2 text-sm transition-colors",
                pathname.startsWith(l.href)
                  ? "bg-blue-50 font-medium text-blue-700"
                  : "text-gray-700 hover:bg-gray-50",
              )}
            >
              {l.label}
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
