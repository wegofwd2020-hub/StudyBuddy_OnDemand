"use client";

/**
 * Top-bar "Administration" dropdown (issue #415) — supersedes the #358
 * "Curriculum Management" menu.
 *
 * Groups the two school_admin task clusters off the left rail into one menu:
 *   • Curriculum       — shown to canManageCurriculum: a school_admin OR a
 *                        teacher granted a `curriculum*` capability. Preserves the
 *                        #358 / ADR-005 Decision 1 delegation model.
 *   • User Management  — shown to school_admin only.
 *
 * The button renders when either section is visible (plain teacher → no button;
 * delegated curriculum teacher → Curriculum section only; school_admin → both).
 * This is a convenience surface; the backend enforces each action's gate
 * independently — hiding a link is never the control.
 */

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { ShieldCheck, ChevronDown } from "lucide-react";
import { canManageCurriculum, isSchoolAdmin, useTeacher } from "@/lib/hooks/useTeacher";
import { cn } from "@/lib/utils";

interface MenuLink {
  label: string;
  href: string;
}

interface MenuSection {
  heading: string;
  links: MenuLink[];
}

// Curriculum labels name the verb/noun each surface represents (issue #367 AP-3):
// browse platform packages → adopt into your owned set → open the lessons inside.
const CURRICULUM_LINKS: MenuLink[] = [
  { label: "Browse Catalog", href: "/school/catalog" },
  { label: "My Curricula", href: "/school/library" },
  { label: "Lessons & Content", href: "/school/curriculum/content" },
  { label: "Curriculum Builder", href: "/school/curriculum" },
  { label: "Review Queue", href: "/school/review" },
];

// User Management = account provisioning, roles, and grade/class assignment.
const USER_MGMT_LINKS: MenuLink[] = [
  { label: "Students", href: "/school/students" },
  { label: "Teachers", href: "/school/teachers" },
];

export function AdministrationMenu() {
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

  const sections: MenuSection[] = [];
  if (canManageCurriculum(teacher)) {
    sections.push({ heading: "Curriculum", links: CURRICULUM_LINKS });
  }
  if (isSchoolAdmin(teacher)) {
    sections.push({ heading: "User Management", links: USER_MGMT_LINKS });
  }

  // Hidden entirely for users with neither cluster (plain teachers / students).
  if (sections.length === 0) return null;

  const active = sections.some((s) => s.links.some((l) => pathname.startsWith(l.href)));

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
        <ShieldCheck className="h-4 w-4" aria-hidden />
        Administration
        <ChevronDown className="h-3.5 w-3.5" aria-hidden />
      </button>

      {open && (
        <div
          role="menu"
          className="absolute right-0 z-50 mt-1 w-56 rounded-md border border-gray-100 bg-white py-1 shadow-lg"
        >
          {sections.map((section, si) => (
            <div key={section.heading}>
              {si > 0 && <div className="my-1 border-t border-gray-100" aria-hidden />}
              <p className="px-4 pt-2 pb-1 text-xs font-semibold tracking-wide text-gray-400 uppercase">
                {section.heading}
              </p>
              {section.links.map((l) => (
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
          ))}
        </div>
      )}
    </div>
  );
}
