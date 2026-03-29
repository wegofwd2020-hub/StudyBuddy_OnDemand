"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTeacher } from "@/lib/hooks/useTeacher";
import { useQuery } from "@tanstack/react-query";
import { getAlerts } from "@/lib/api/reports";
import { cn } from "@/lib/utils";
import {
  LayoutDashboard,
  Users,
  BarChart2,
  Bell,
  BookOpen,
  Mail,
  LogOut,
  BookMarked,
  GraduationCap,
  Settings,
} from "lucide-react";

interface NavItem {
  label: string;
  href: string;
  icon: React.ReactNode;
  adminOnly?: boolean;
}

const NAV_ITEMS: NavItem[] = [
  {
    label: "Dashboard",
    href: "/school/dashboard",
    icon: <LayoutDashboard className="h-4 w-4" />,
  },
  {
    label: "Class Overview",
    href: "/school/class/all",
    icon: <Users className="h-4 w-4" />,
  },
  {
    label: "Reports",
    href: "/school/reports/overview",
    icon: <BarChart2 className="h-4 w-4" />,
  },
  {
    label: "Curriculum",
    href: "/school/curriculum",
    icon: <BookMarked className="h-4 w-4" />,
  },
  { label: "Students", href: "/school/students", icon: <Users className="h-4 w-4" /> },
  {
    label: "Teachers",
    href: "/school/teachers",
    icon: <GraduationCap className="h-4 w-4" />,
    adminOnly: true,
  },
  { label: "Alerts", href: "/school/alerts", icon: <Bell className="h-4 w-4" /> },
  {
    label: "Digest Settings",
    href: "/school/digest",
    icon: <Mail className="h-4 w-4" />,
  },
  { label: "Settings", href: "/school/settings", icon: <Settings className="h-4 w-4" /> },
];

const REPORT_SUB: { label: string; href: string }[] = [
  { label: "Overview", href: "/school/reports/overview" },
  { label: "Trends", href: "/school/reports/trends" },
  { label: "At-Risk", href: "/school/reports/at-risk" },
  { label: "Unit Performance", href: "/school/reports/units" },
  { label: "Engagement", href: "/school/reports/engagement" },
  { label: "Feedback", href: "/school/reports/feedback" },
  { label: "Export CSV", href: "/school/reports/export" },
];

export function SchoolNav() {
  const rawPathname = usePathname();
  const pathname = rawPathname ?? "";
  const teacher = useTeacher();
  const schoolId = teacher?.school_id ?? "";

  const { data: alertsData } = useQuery({
    queryKey: ["alerts", schoolId],
    queryFn: () => getAlerts(schoolId),
    enabled: !!schoolId,
    staleTime: 60_000,
  });

  const unreadAlerts = alertsData?.alerts.filter((a) => !a.acknowledged).length ?? 0;
  const inReports = pathname.startsWith("/school/reports");

  function handleLogout() {
    if (typeof window !== "undefined") {
      localStorage.removeItem("sb_teacher_token");
      window.location.href = "/api/auth/logout";
    }
  }

  return (
    <aside className="flex min-h-screen w-56 shrink-0 flex-col border-r border-gray-100 bg-white">
      {/* Logo */}
      <div className="flex h-14 items-center border-b border-gray-100 px-4">
        <Link href="/school/dashboard" className="flex items-center gap-2">
          <BookOpen className="h-5 w-5 text-blue-600" />
          <span className="text-sm font-bold text-gray-900">StudyBuddy</span>
          <span className="text-xs font-medium text-gray-400">School</span>
        </Link>
      </div>

      {/* Navigation */}
      <nav className="flex-1 space-y-0.5 overflow-y-auto px-2 py-3">
        {NAV_ITEMS.filter(
          (item) => !item.adminOnly || teacher?.role === "school_admin",
        ).map((item) => {
          const isAlerts = item.href === "/school/alerts";
          const isReports = item.href.startsWith("/school/reports");
          const isActive = isReports ? inReports : pathname === item.href;

          return (
            <div key={item.href}>
              <Link
                href={item.href}
                className={cn(
                  "flex items-center gap-2.5 rounded-md px-3 py-2 text-sm transition-colors",
                  isActive
                    ? "bg-blue-50 font-medium text-blue-700"
                    : "text-gray-600 hover:bg-gray-50 hover:text-gray-900",
                )}
              >
                {item.icon}
                <span className="flex-1">{item.label}</span>
                {isAlerts && unreadAlerts > 0 && (
                  <span className="ml-auto flex h-4 w-4 items-center justify-center rounded-full bg-red-500 text-xs font-medium text-white">
                    {unreadAlerts > 9 ? "9+" : unreadAlerts}
                  </span>
                )}
              </Link>

              {/* Reports sub-nav */}
              {isReports && inReports && (
                <div className="mt-0.5 ml-4 space-y-0.5">
                  {REPORT_SUB.map((sub) => (
                    <Link
                      key={sub.href}
                      href={sub.href}
                      className={cn(
                        "block rounded px-3 py-1.5 text-xs transition-colors",
                        pathname === sub.href
                          ? "bg-blue-100 font-medium text-blue-700"
                          : "text-gray-500 hover:text-gray-800",
                      )}
                    >
                      {sub.label}
                    </Link>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="border-t border-gray-100 px-2 py-3">
        {teacher && (
          <p className="mb-2 truncate px-3 text-xs text-gray-400">
            {teacher.role === "school_admin" ? "Admin" : "Teacher"}
          </p>
        )}
        <button
          onClick={handleLogout}
          className="flex w-full items-center gap-2.5 rounded-md px-3 py-2 text-sm text-gray-500 transition-colors hover:bg-gray-50 hover:text-gray-900"
        >
          <LogOut className="h-4 w-4" />
          Sign out
        </button>
      </div>
    </aside>
  );
}
