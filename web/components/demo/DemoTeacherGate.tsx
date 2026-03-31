"use client";

import Link from "next/link";
import { ShieldOff } from "lucide-react";
import { useDemoTeacher } from "@/lib/hooks/useDemoTeacher";
import { LinkButton } from "@/components/ui/link-button";

interface DemoTeacherGateProps {
  children: React.ReactNode;
  heading?: string;
  description?: string;
}

/**
 * Wraps page content that demo teachers should not access.
 * Renders a friendly blocked screen instead of the real content when
 * `useDemoTeacher()` returns a non-null value.
 *
 * Usage:
 *   <DemoTeacherGate>
 *     <RealTeacherContent />
 *   </DemoTeacherGate>
 */
export function DemoTeacherGate({
  children,
  heading = "Not available in teacher demo",
  description = "This feature requires a full teacher account. Sign up to access everything StudyBuddy has to offer.",
}: DemoTeacherGateProps) {
  const demo = useDemoTeacher();

  if (!demo) {
    return <>{children}</>;
  }

  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center px-4 py-16 text-center">
      <div className="flex h-16 w-16 items-center justify-center rounded-full bg-cyan-50">
        <ShieldOff className="h-8 w-8 text-cyan-500" />
      </div>

      <h1 className="mt-5 text-xl font-bold text-gray-900">{heading}</h1>
      <p className="mt-2 max-w-sm text-sm text-gray-500">{description}</p>

      <div className="mt-6 flex flex-col items-center gap-3 sm:flex-row">
        <LinkButton href="/signup/teacher" size="lg">
          Sign up for full access
        </LinkButton>
        <Link
          href="/teacher/dashboard"
          className="text-sm text-gray-500 underline underline-offset-2 hover:text-gray-700"
        >
          Back to dashboard
        </Link>
      </div>

      <p className="mt-8 text-xs text-gray-400">
        Your teacher demo account gives you access to a sample class for 48 hours.
      </p>
    </div>
  );
}
