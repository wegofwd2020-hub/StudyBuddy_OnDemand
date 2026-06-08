"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { useTeacher } from "@/lib/hooks/useTeacher";
import { useSchoolTheme } from "@/lib/theme/SchoolThemeContext";
import { useQuery } from "@tanstack/react-query";
import { getAlerts } from "@/lib/api/reports";
import { cn } from "@/lib/utils";
import {
  LayoutDashboard,
  LineChart,
  BarChart2,
  Bell,
  BookOpen,
  CreditCard,
  Archive,
  HardDrive,
  Images,
  DoorOpen,
  Database,
  ChevronDown,
  ChevronRight,
} from "lucide-react";

interface NavItem {
  label: string;
  href: string;
  icon: React.ReactNode;
  adminOnly?: boolean;
}

interface NavGroup {
  /** Section heading; omit for the standalone top group (Dashboard). */
  heading?: string;
  items: NavItem[];
  /** Collapsible groups render a toggle and hide items until expanded. */
  collapsible?: boolean;
  /** Whole group is hidden from non-admins. */
  adminOnly?: boolean;
}

// Grouped navigation (issue #367, AP-1). Curriculum nav AND the People group
// (Students / Teachers) now live in the top-bar AdministrationMenu (#415) — the
// two school_admin task clusters were pulled off this rail. Per-user config +
// sign out live in the top-bar AccountMenu (#367 AP-4). Teachers still reach the
// per-student performance table via "Student Progress" (Teach) below.
const NAV_GROUPS: NavGroup[] = [
  {
    items: [
      {
        label: "Dashboard",
        href: "/school/dashboard",
        icon: <LayoutDashboard className="h-4 w-4" />,
      },
    ],
  },
  {
    heading: "Teach",
    items: [
      {
        label: "Classrooms",
        href: "/school/classrooms",
        icon: <DoorOpen className="h-4 w-4" />,
      },
      {
        // Renamed from "Class Overview" (AP-2): this is a per-student
        // performance table, not a per-class view. Distinct icon from
        // "Students" (was a duplicate <Users>) per VT-5.
        label: "Student Progress",
        href: "/school/class/all",
        icon: <LineChart className="h-4 w-4" />,
      },
      { label: "Alerts", href: "/school/alerts", icon: <Bell className="h-4 w-4" /> },
    ],
  },
  {
    heading: "Insights",
    items: [
      {
        label: "Reports",
        href: "/school/reports/overview",
        icon: <BarChart2 className="h-4 w-4" />,
        adminOnly: true,
      },
    ],
  },
  {
    // Renamed from "Administration" (#415): the top-bar Administration menu is
    // now the single "Administration" surface; this rail group holds infra/config.
    heading: "Settings",
    collapsible: true,
    adminOnly: true,
    items: [
      {
        label: "Subscription",
        href: "/school/subscription",
        icon: <CreditCard className="h-4 w-4" />,
      },
      {
        label: "Storage",
        href: "/school/storage",
        icon: <HardDrive className="h-4 w-4" />,
      },
      {
        label: "Visual Library",
        href: "/school/visuals",
        icon: <Images className="h-4 w-4" />,
      },
      {
        label: "Content Retention",
        href: "/school/retention",
        icon: <Archive className="h-4 w-4" />,
      },
      {
        label: "Backups",
        href: "/school/backups",
        icon: <Database className="h-4 w-4" />,
      },
    ],
  },
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
  const isAdmin = teacher?.role === "school_admin";
  const schoolId = teacher?.school_id ?? "";
  const schoolTheme = useSchoolTheme();
  const schoolLogoText = schoolTheme.school.logoText;

  const { data: alertsData } = useQuery({
    queryKey: ["alerts", schoolId],
    queryFn: () => getAlerts(schoolId),
    enabled: !!schoolId,
    staleTime: 60_000,
  });

  const unreadAlerts = alertsData?.alerts?.filter((a) => !a.acknowledged).length ?? 0;
  const inReports = pathname.startsWith("/school/reports");

  function itemIsActive(href: string): boolean {
    if (href === "/school/reports/overview") return inReports;
    return pathname === href || pathname.startsWith(href + "/");
  }

  return (
    <aside className="flex min-h-screen w-56 shrink-0 flex-col border-r border-gray-100 bg-white">
      {/* Logo */}
      <div className="flex h-14 items-center border-b border-gray-100 px-4">
        <Link href="/school/dashboard" className="flex items-center gap-2">
          <BookOpen className="h-5 w-5 text-blue-600" />
          <span className="text-sm font-bold text-gray-900">{schoolLogoText}</span>
          <span className="text-xs font-medium text-gray-400">School</span>
        </Link>
      </div>

      {/* Navigation */}
      <nav className="flex-1 space-y-3 overflow-y-auto px-2 py-3">
        {NAV_GROUPS.map((group, gi) => {
          if (group.adminOnly && !isAdmin) return null;
          const visibleItems = group.items.filter((it) => !it.adminOnly || isAdmin);
          if (visibleItems.length === 0) return null;
          return (
            <NavSection
              key={group.heading ?? `group-${gi}`}
              group={group}
              items={visibleItems}
              pathname={pathname}
              inReports={inReports}
              unreadAlerts={unreadAlerts}
              itemIsActive={itemIsActive}
            />
          );
        })}
      </nav>

      {/* Footer — role label only; sign out moved to the top-bar AccountMenu (AP-4) */}
      {teacher && (
        <div className="border-t border-gray-100 px-5 py-3">
          <p className="truncate text-xs text-gray-400">
            {isAdmin ? "Admin" : "Teacher"}
          </p>
        </div>
      )}
    </aside>
  );
}

function NavSection({
  group,
  items,
  pathname,
  inReports,
  unreadAlerts,
  itemIsActive,
}: {
  group: NavGroup;
  items: NavItem[];
  pathname: string;
  inReports: boolean;
  unreadAlerts: number;
  itemIsActive: (href: string) => boolean;
}) {
  const containsActive = items.some((it) => itemIsActive(it.href));
  // Collapsible groups start open only when one of their routes is active.
  const [open, setOpen] = useState(containsActive);

  const links = (
    <div className="space-y-0.5">
      {items.map((item) => {
        const isActive = itemIsActive(item.href);
        const isAlerts = item.href === "/school/alerts";
        const isReports = item.href === "/school/reports/overview";
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
    </div>
  );

  // Standalone group (no heading) — render links directly.
  if (!group.heading) return links;

  if (group.collapsible) {
    return (
      <div>
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          aria-expanded={open}
          className="flex w-full items-center justify-between px-3 py-1 text-xs font-semibold tracking-wide text-gray-400 uppercase transition-colors hover:text-gray-600"
        >
          {group.heading}
          {open ? (
            <ChevronDown className="h-3.5 w-3.5" aria-hidden />
          ) : (
            <ChevronRight className="h-3.5 w-3.5" aria-hidden />
          )}
        </button>
        {open && <div className="mt-0.5">{links}</div>}
      </div>
    );
  }

  return (
    <div>
      <p className="px-3 py-1 text-xs font-semibold tracking-wide text-gray-400 uppercase">
        {group.heading}
      </p>
      <div className="mt-0.5">{links}</div>
    </div>
  );
}
