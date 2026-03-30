"use client";

import Link from "next/link";
import { ShieldOff } from "lucide-react";
import { useDemoStudent } from "@/lib/hooks/useDemoStudent";
import { LinkButton } from "@/components/ui/link-button";

interface DemoGateProps {
  /** Content to render when the user is NOT a demo student. */
  children: React.ReactNode;
  /**
   * Optional override for the blocked-state heading.
   * Defaults to "Not available in demo".
   */
  heading?: string;
  /**
   * Optional override for the blocked-state description.
   * Defaults to a generic "sign up for full access" message.
   */
  description?: string;
}

/**
 * Wraps page content that demo students should not access.
 * Renders a friendly blocked screen instead of the real content when
 * `useDemoStudent()` returns a non-null value.
 *
 * Usage:
 *   <DemoGate>
 *     <RealPageContent />
 *   </DemoGate>
 */
export function DemoGate({
  children,
  heading = "Not available in demo",
  description = "This feature requires a full account. Sign up to access everything StudyBuddy has to offer.",
}: DemoGateProps) {
  const demo = useDemoStudent();

  if (!demo) {
    // Not a demo student — render children normally
    return <>{children}</>;
  }

  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center px-4 py-16 text-center">
      <div className="flex h-16 w-16 items-center justify-center rounded-full bg-amber-50">
        <ShieldOff className="h-8 w-8 text-amber-500" />
      </div>

      <h1 className="mt-5 text-xl font-bold text-gray-900">{heading}</h1>
      <p className="mt-2 max-w-sm text-sm text-gray-500">{description}</p>

      <div className="mt-6 flex flex-col items-center gap-3 sm:flex-row">
        <LinkButton href="/signup" size="lg">
          Sign up for full access
        </LinkButton>
        <Link
          href="/dashboard"
          className="text-sm text-gray-500 underline underline-offset-2 hover:text-gray-700"
        >
          Back to dashboard
        </Link>
      </div>

      <p className="mt-8 text-xs text-gray-400">
        Your demo account gives you access to Grade 8 content for 24 hours.
      </p>
    </div>
  );
}
