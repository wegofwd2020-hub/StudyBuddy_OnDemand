"use client";

import { use } from "react";
import { useQuery } from "@tanstack/react-query";
import { getTutorial } from "@/lib/api/content";
import { TutorialRenderer } from "@/components/content/TutorialRenderer";
import { FeedbackWidget } from "@/components/feedback/FeedbackWidget";
import { OfflineBanner } from "@/components/student/OfflineBanner";
import { LinkButton } from "@/components/ui/link-button";
import { Skeleton } from "@/components/ui/skeleton";

interface PageProps {
  params: Promise<{ unit_id: string }>;
}

export default function TutorialPage({ params }: PageProps) {
  const { unit_id } = use(params);
  const { data: tutorial, isLoading, isError } = useQuery({
    queryKey: ["tutorial", unit_id],
    queryFn: () => getTutorial(unit_id),
    enabled: !!unit_id,
  });

  if (isLoading) {
    return (
      <div className="p-6 max-w-3xl space-y-4">
        <Skeleton className="h-8 w-2/3" />
        {[...Array(4)].map((_, i) => <Skeleton key={i} className="h-16 rounded-lg" />)}
      </div>
    );
  }

  if (isError || !tutorial) {
    return (
      <div className="p-6">
        <p className="text-red-500 text-sm">Could not load tutorial. Please try again.</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col">
      <OfflineBanner />
      <div className="p-6 max-w-3xl space-y-6">
        <TutorialRenderer tutorial={tutorial} />
        <div className="flex items-center justify-between border-t pt-4">
          <FeedbackWidget unitId={unit_id} contentType="tutorial" />
          <LinkButton href={`/quiz/${unit_id}`} size="sm">Take Quiz</LinkButton>
        </div>
      </div>
    </div>
  );
}
