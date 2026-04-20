import type { Metadata } from "next";
import { AdminAuthShell } from "./AdminAuthShell";

// Server layout (no `"use client"`) so the Metadata API can set <title>.
// All interactive/auth-guard logic lives in the AdminAuthShell client component.
export const metadata: Metadata = {
  title: "Admin | StudyBuddy",
};

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return <AdminAuthShell>{children}</AdminAuthShell>;
}
