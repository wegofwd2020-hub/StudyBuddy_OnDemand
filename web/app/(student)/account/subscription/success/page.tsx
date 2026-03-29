"use client";

import { useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { LinkButton } from "@/components/ui/link-button";
import { CheckCircle } from "lucide-react";

export default function SubscriptionSuccessPage() {
  const qc = useQueryClient();

  // Invalidate cached subscription status so the rest of the app
  // reflects the new active plan immediately.
  useEffect(() => {
    qc.invalidateQueries({ queryKey: ["subscription"] });
  }, [qc]);

  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center p-6 text-center">
      <div className="max-w-sm space-y-4">
        <CheckCircle className="mx-auto h-16 w-16 text-green-500" />
        <h1 className="text-2xl font-bold text-gray-900">You&apos;re subscribed!</h1>
        <p className="text-gray-600">
          Welcome to StudyBuddy OnDemand. You now have full access to all lessons,
          quizzes, and offline content.
        </p>
        <div className="flex flex-col justify-center gap-2 pt-2 sm:flex-row">
          <LinkButton href="/dashboard">Go to dashboard</LinkButton>
          <LinkButton href="/subjects" variant="outline">
            Browse subjects
          </LinkButton>
        </div>
      </div>
    </div>
  );
}
