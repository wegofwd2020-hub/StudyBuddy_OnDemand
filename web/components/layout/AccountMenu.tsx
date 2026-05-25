"use client";

/**
 * Top-bar account dropdown for the school/teacher portal (issue #367, AP-4).
 *
 * Per-user / account config (Settings, Digest Settings, Customize, Help) and
 * Sign out used to live at the bottom of the left rail. Convention is for these
 * to sit behind the username in the top bar — moving them here frees four rail
 * slots and matches what reviewers expected. The username is the trigger.
 */

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { ChevronDown, Settings, Mail, Palette, HelpCircle, LogOut } from "lucide-react";
import { cn } from "@/lib/utils";

const ACCOUNT_LINKS: { label: string; href: string; icon: React.ReactNode }[] = [
  { label: "Settings", href: "/school/settings", icon: <Settings className="h-4 w-4" /> },
  {
    label: "Digest Settings",
    href: "/school/digest",
    icon: <Mail className="h-4 w-4" />,
  },
  {
    label: "Customize",
    href: "/school/settings/customize",
    icon: <Palette className="h-4 w-4" />,
  },
  { label: "Help", href: "/school/help", icon: <HelpCircle className="h-4 w-4" /> },
];

function handleLogout() {
  if (typeof window !== "undefined") {
    localStorage.removeItem("sb_teacher_token");
    localStorage.removeItem("sb_teacher_refresh_token");
    // /api/auth/logout clears session cookies and redirects to the correct
    // destination (local-auth → /signin, Auth0 → /).
    window.location.href = "/api/auth/logout";
  }
}

export function AccountMenu({ userName }: { userName?: string }) {
  const pathname = usePathname() ?? "";
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function onClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onClick);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onClick);
      document.removeEventListener("keydown", onKey);
    };
  }, []);

  const active = ACCOUNT_LINKS.some((l) => pathname.startsWith(l.href));
  const label = userName ?? "Account";

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label="Account menu"
        onClick={() => setOpen((v) => !v)}
        className={cn(
          "flex items-center gap-1.5 rounded-md border px-2.5 py-1.5 text-sm transition-colors",
          active || open
            ? "border-blue-500 bg-blue-50 text-blue-700"
            : "border-gray-200 text-gray-600 hover:border-gray-400 hover:text-gray-900",
        )}
      >
        <span className="max-w-[160px] truncate font-medium">{label}</span>
        <ChevronDown className="h-3.5 w-3.5" aria-hidden />
      </button>

      {open && (
        <div
          role="menu"
          className="absolute right-0 z-50 mt-1 w-52 rounded-md border border-gray-100 bg-white py-1 shadow-lg"
        >
          {ACCOUNT_LINKS.map((l) => (
            <Link
              key={l.href}
              role="menuitem"
              href={l.href}
              onClick={() => setOpen(false)}
              className={cn(
                "flex items-center gap-2.5 px-4 py-2 text-sm transition-colors",
                pathname.startsWith(l.href)
                  ? "bg-blue-50 font-medium text-blue-700"
                  : "text-gray-700 hover:bg-gray-50",
              )}
            >
              {l.icon}
              {l.label}
            </Link>
          ))}
          <div className="my-1 border-t border-gray-100" />
          <button
            type="button"
            role="menuitem"
            onClick={() => {
              setOpen(false);
              handleLogout();
            }}
            className="flex w-full items-center gap-2.5 px-4 py-2 text-sm text-gray-700 transition-colors hover:bg-gray-50"
          >
            <LogOut className="h-4 w-4" />
            Sign out
          </button>
        </div>
      )}
    </div>
  );
}
