"use client";

import { use } from "react";
import { useQuery } from "@tanstack/react-query";
import { getExperiment } from "@/lib/api/content";
import { ExperimentRenderer } from "@/components/content/ExperimentRenderer";
import { FeedbackWidget } from "@/components/feedback/FeedbackWidget";
import { OfflineBanner } from "@/components/student/OfflineBanner";
import { LinkButton } from "@/components/ui/link-button";
import { Skeleton } from "@/components/ui/skeleton";

interface PageProps {
  params: Promise<{ unit_id: string }>;
}

export default function ExperimentPage({ params }: PageProps) {
  const { unit_id } = use(params);
  const {
    data: experiment,
    isLoading,
    isError,
  } = useQuery({
    queryKey: ["experiment", unit_id],
    queryFn: () => getExperiment(unit_id),
    enabled: !!unit_id,
  });

  if (isLoading) {
    return (
      <div className="max-w-3xl space-y-4 p-6">
        <Skeleton className="h-8 w-2/3" />
        <Skeleton className="h-24 rounded-lg" />
        <Skeleton className="h-48 rounded-lg" />
      </div>
    );
  }

  if (isError || !experiment) {
    return (
      <div className="p-6">
        <p className="text-sm text-red-500">
          Could not load experiment. Please try again.
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col">
      <OfflineBanner />
      <div className="max-w-3xl space-y-6 p-6">
        <ExperimentRenderer experiment={experiment} />
        <div className="flex items-center justify-between border-t pt-4">
          <FeedbackWidget unitId={unit_id} contentType="experiment" />
          <LinkButton href={`/quiz/${unit_id}`} size="sm">
            Take Quiz
          </LinkButton>
        </div>
      </div>
    </div>
  );
}
