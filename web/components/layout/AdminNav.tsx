"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAdmin, hasPermission, type AdminRole } from "@/lib/hooks/useAdmin";
import { cn } from "@/lib/utils";
import {
  LayoutDashboard,
  BarChart2,
  GitBranch,
  ClipboardList,
  MessageSquare,
  Activity,
  FileText,
  Shield,
  BookOpen,
  LogOut,
  Hammer,
  FlaskConical,
  GraduationCap,
  HelpCircle,
  School,
  Users,
} from "lucide-react";

interface NavItem {
  label: string;
  href: string;
  icon: React.ReactNode;
  minRole?: AdminRole;
}

const NAV_ITEMS: NavItem[] = [
  {
    label: "Dashboard",
    href: "/admin/dashboard",
    icon: <LayoutDashboard className="h-4 w-4" />,
  },
  {
    label: "Analytics",
    href: "/admin/analytics",
    icon: <BarChart2 className="h-4 w-4" />,
  },
  {
    label: "Pipeline",
    href: "/admin/pipeline",
    icon: <GitBranch className="h-4 w-4" />,
  },
  {
    label: "Content Review",
    href: "/admin/content-review",
    icon: <ClipboardList className="h-4 w-4" />,
  },
  {
    label: "Feedback",
    href: "/admin/feedback",
    icon: <MessageSquare className="h-4 w-4" />,
    minRole: "product_admin",
  },
  {
    label: "Audit Log",
    href: "/admin/audit",
    icon: <FileText className="h-4 w-4" />,
    minRole: "product_admin",
  },
  {
    label: "Health",
    href: "/admin/health",
    icon: <Activity className="h-4 w-4" />,
  },
  {
    label: "Demo Accounts",
    href: "/admin/demo-accounts",
    icon: <FlaskConical className="h-4 w-4" />,
    minRole: "product_admin",
  },
  {
    label: "Teacher Demo Accounts",
    href: "/admin/demo-teacher-accounts",
    icon: <GraduationCap className="h-4 w-4" />,
    minRole: "product_admin",
  },
  {
    label: "Schools",
    href: "/admin/schools",
    icon: <School className="h-4 w-4" />,
    minRole: "product_admin",
  },
  {
    label: "Private Teachers",
    href: "/admin/private-teachers",
    icon: <Users className="h-4 w-4" />,
    minRole: "product_admin",
  },
  {
    label: "Build Reports",
    href: "/admin/build-reports",
    icon: <Hammer className="h-4 w-4" />,
    minRole: "super_admin",
  },
  {
    label: "Help",
    href: "/admin/help",
    icon: <HelpCircle className="h-4 w-4" />,
  },
];

function handleLogout() {
  if (typeof window !== "undefined") {
    localStorage.removeItem("sb_admin_token");
    window.location.href = "/admin/login";
  }
}

export function AdminNav() {
  const pathname = usePathname() ?? "";
  const admin = useAdmin();

  const visibleItems = NAV_ITEMS.filter(
    (item) => !item.minRole || (admin && hasPermission(admin.role, item.minRole)),
  );

  return (
    <aside className="flex min-h-screen w-56 shrink-0 flex-col bg-gray-900 text-gray-100">
      {/* Logo */}
      <div className="flex h-14 items-center border-b border-gray-700 px-4">
        <Link href="/admin/dashboard" className="flex items-center gap-2">
          <BookOpen className="h-5 w-5 text-indigo-400" />
          <span className="text-sm font-bold text-white">StudyBuddy</span>
          <span className="text-xs font-medium text-gray-400">Admin</span>
        </Link>
      </div>

      {/* Navigation */}
      <nav className="flex-1 space-y-0.5 overflow-y-auto px-2 py-3">
        {visibleItems.map((item) => {
          const isActive = pathname === item.href || pathname.startsWith(item.href + "/");

          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-2.5 rounded-md px-3 py-2 text-sm transition-colors",
                isActive
                  ? "bg-indigo-600 font-medium text-white"
                  : "text-gray-400 hover:bg-gray-800 hover:text-gray-100",
              )}
            >
              {item.icon}
              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="border-t border-gray-700 px-2 py-3">
        {admin && (
          <div className="mb-2 flex items-center gap-2 px-3">
            <Shield className="h-3 w-3 text-indigo-400" />
            <span className="truncate text-xs text-gray-400">{admin.role}</span>
          </div>
        )}
        <button
          onClick={handleLogout}
          className="flex w-full items-center gap-2.5 rounded-md px-3 py-2 text-sm text-gray-400 transition-colors hover:bg-gray-800 hover:text-gray-100"
        >
          <LogOut className="h-4 w-4" />
          Sign out
        </button>
      </div>
    </aside>
  );
}
