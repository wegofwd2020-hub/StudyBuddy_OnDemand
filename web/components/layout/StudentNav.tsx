"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { BookOpen, LayoutDashboard, Map, BarChart3, Clock, Settings, LogOut } from "lucide-react";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/subjects", label: "Subjects", icon: BookOpen },
  { href: "/curriculum", label: "Curriculum Map", icon: Map },
  { href: "/progress", label: "Progress", icon: Clock },
  { href: "/stats", label: "My Stats", icon: BarChart3 },
] as const;

export function StudentNav() {
  const rawPathname = usePathname();
  const pathname = rawPathname ?? "";

  return (
    <aside className="hidden md:flex flex-col w-56 shrink-0 border-r bg-white min-h-screen">
      {/* Logo */}
      <div className="flex items-center gap-2 h-16 px-4 border-b font-bold text-lg">
        <BookOpen className="h-5 w-5 text-blue-600" />
        <span>StudyBuddy</span>
      </div>

      {/* Nav links */}
      <nav className="flex-1 px-2 py-4 space-y-1">
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
      <div className="px-2 py-4 border-t space-y-1">
        <Link
          href="/account/settings"
          className="flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-gray-500 hover:bg-gray-50 hover:text-gray-900 transition-colors"
        >
          <Settings className="h-4 w-4 shrink-0" />
          Settings
        </Link>
        <button
          onClick={() => {
            localStorage.removeItem("sb_token");
            window.location.href = "/api/auth/logout";
          }}
          className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-gray-500 hover:bg-gray-50 hover:text-gray-900 transition-colors"
        >
          <LogOut className="h-4 w-4 shrink-0" />
          Sign out
        </button>
      </div>
    </aside>
  );
}
