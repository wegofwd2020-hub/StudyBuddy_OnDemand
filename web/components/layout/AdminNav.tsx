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
];

function handleLogout() {
  if (typeof window !== "undefined") {
    localStorage.removeItem("sb_admin_token");
    window.location.href = "/admin/login";
  }
}

export function AdminNav() {
  const pathname = usePathname();
  const admin = useAdmin();

  const visibleItems = NAV_ITEMS.filter(
    (item) => !item.minRole || (admin && hasPermission(admin.role, item.minRole)),
  );

  return (
    <aside className="w-56 shrink-0 bg-gray-900 text-gray-100 flex flex-col min-h-screen">
      {/* Logo */}
      <div className="h-14 flex items-center px-4 border-b border-gray-700">
        <Link href="/admin/dashboard" className="flex items-center gap-2">
          <BookOpen className="h-5 w-5 text-indigo-400" />
          <span className="font-bold text-white text-sm">StudyBuddy</span>
          <span className="text-xs text-gray-400 font-medium">Admin</span>
        </Link>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-2 py-3 space-y-0.5 overflow-y-auto">
        {visibleItems.map((item) => {
          const isActive =
            pathname === item.href || pathname.startsWith(item.href + "/");

          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-2.5 px-3 py-2 rounded-md text-sm transition-colors",
                isActive
                  ? "bg-indigo-600 text-white font-medium"
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
      <div className="px-2 py-3 border-t border-gray-700">
        {admin && (
          <div className="px-3 mb-2 flex items-center gap-2">
            <Shield className="h-3 w-3 text-indigo-400" />
            <span className="text-xs text-gray-400 truncate">{admin.role}</span>
          </div>
        )}
        <button
          onClick={handleLogout}
          className="flex items-center gap-2.5 w-full px-3 py-2 rounded-md text-sm text-gray-400 hover:bg-gray-800 hover:text-gray-100 transition-colors"
        >
          <LogOut className="h-4 w-4" />
          Sign out
        </button>
      </div>
    </aside>
  );
}
