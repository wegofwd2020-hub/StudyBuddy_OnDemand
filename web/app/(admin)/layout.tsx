"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { AdminNav } from "@/components/layout/AdminNav";
import { QueryProvider } from "@/lib/providers/QueryProvider";
import { PortalHeader } from "@/components/layout/PortalHeader";
import { PortalFooter } from "@/components/layout/PortalFooter";

function parseAdminName(token: string): string | undefined {
  try {
    const payload = JSON.parse(
      atob(token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/")),
    );
    return payload.admin_id ?? payload.sub ?? payload.email ?? undefined;
  } catch {
    return undefined;
  }
}

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const [userName, setUserName] = useState<string | undefined>(undefined);

  useEffect(() => {
    const token = localStorage.getItem("sb_admin_token");
    if (!token) {
      router.replace("/admin/login");
    } else {
      setUserName(parseAdminName(token));
    }
  }, [router]);

  return (
    <QueryProvider>
      <div className="flex min-h-screen bg-gray-50">
        <AdminNav />
        <div className="flex flex-1 flex-col overflow-auto">
          <PortalHeader portal="admin" userName={userName} />
          <main id="main-content" className="flex-1">
            {children}
          </main>
          <PortalFooter />
        </div>
      </div>
    </QueryProvider>
  );
}
