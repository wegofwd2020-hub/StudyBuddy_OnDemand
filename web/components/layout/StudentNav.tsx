"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  BookOpen,
  LayoutDashboard,
  Map,
  BarChart3,
  Clock,
  Settings,
  LogOut,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useDemoStudent } from "@/lib/hooks/useDemoStudent";
import { demoLogout } from "@/lib/api/demo";

const NAV_ITEMS = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/subjects", label: "Subjects", icon: BookOpen },
  { href: "/curriculum", label: "Curriculum Map", icon: Map },
  { href: "/progress", label: "Progress", icon: Clock },
  { href: "/stats", label: "My Stats", icon: BarChart3 },
] as const;

async function signOutDemo(): Promise<void> {
  const token = localStorage.getItem("sb_token");
  if (token) {
    try {
      await demoLogout(token);
    } catch {
      // best-effort — clear locally regardless
    }
  }
  localStorage.removeItem("sb_token");
  document.cookie = "sb_dev_session=; path=/; max-age=0; SameSite=Lax";
  window.location.href = "/";
}

function signOutRegular(): void {
  localStorage.removeItem("sb_token");
  window.location.href = "/api/auth/logout";
}

export function StudentNav() {
  const rawPathname = usePathname();
  const pathname = rawPathname ?? "";
  const demo = useDemoStudent();

  return (
    <aside className="hidden min-h-screen w-56 shrink-0 flex-col border-r bg-white md:flex">
      {/* Logo */}
      <div className="flex h-16 items-center gap-2 border-b px-4 text-lg font-bold">
        <BookOpen className="h-5 w-5 text-blue-600" />
        <span>StudyBuddy</span>
      </div>

      {/* Nav links */}
      <nav className="flex-1 space-y-1 px-2 py-4">
        {NAV_ITEMS.map(({ href, label, icon: Icon }) => (
          <Link
            key={href}
            href={href}
            className={cn(
              "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
              pathname === href || pathname.startsWith(href + "/")
                ? "bg-blue-50 text-blue-700"
                : "text-gray-600 hover:bg-gray-50 hover:text-gray-900",
            )}
          >
            <Icon className="h-4 w-4 shrink-0" />
            {label}
          </Link>
        ))}
      </nav>

      {/* Bottom links */}
      <div className="space-y-1 border-t px-2 py-4">
        <Link
          href="/account/settings"
          className="flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-gray-500 transition-colors hover:bg-gray-50 hover:text-gray-900"
        >
          <Settings className="h-4 w-4 shrink-0" />
          Settings
        </Link>
        <button
          onClick={() => (demo ? signOutDemo() : signOutRegular())}
          className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-gray-500 transition-colors hover:bg-gray-50 hover:text-gray-900"
        >
          <LogOut className="h-4 w-4 shrink-0" />
          Sign out
        </button>
      </div>
    </aside>
  );
}
