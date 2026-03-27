"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { AdminNav } from "@/components/layout/AdminNav";
import { QueryProvider } from "@/lib/providers/QueryProvider";

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();

  useEffect(() => {
    const token = localStorage.getItem("sb_admin_token");
    if (!token) {
      router.replace("/admin/login");
    }
  }, [router]);

  return (
    <QueryProvider>
      <div className="flex min-h-screen bg-gray-50">
        <AdminNav />
        <main id="main-content" className="flex-1 overflow-auto">
          {children}
        </main>
      </div>
    </QueryProvider>
  );
}
