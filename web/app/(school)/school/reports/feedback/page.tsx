"use client";

import { useQuery } from "@tanstack/react-query";
import { useTeacher } from "@/lib/hooks/useTeacher";
import { getFeedbackReport } from "@/lib/api/reports";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { MessageSquare, TrendingUp, Star } from "lucide-react";
import { cn } from "@/lib/utils";

const CATEGORY_COLOR: Record<string, string> = {
  content: "bg-blue-50 text-blue-700 border-blue-100",
  ux: "bg-purple-50 text-purple-700 border-purple-100",
  general: "bg-gray-100 text-gray-600 border-gray-200",
};

function StarRating({ rating }: { rating: number | null }) {
  if (rating === null) return <span className="text-gray-300 text-xs">No rating</span>;
  return (
    <span className="flex items-center gap-0.5">
      {Array.from({ length: 5 }).map((_, i) => (
        <Star key={i} className={cn("h-3 w-3", i < Math.round(rating) ? "text-yellow-400 fill-yellow-400" : "text-gray-200 fill-gray-100")} />
      ))}
    </span>
  );
}

export default function FeedbackReportPage() {
  const teacher = useTeacher();
  const schoolId = teacher?.school_id ?? "";

  const { data, isLoading } = useQuery({
    queryKey: ["feedback-report", schoolId],
    queryFn: () => getFeedbackReport(schoolId),
    enabled: !!schoolId,
    staleTime: 120_000,
  });

  return (
    <div className="p-6 max-w-4xl space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Student Feedback</h1>
        {data && (
          <div className="flex items-center gap-4 text-sm text-gray-500">
            <span><span className="font-semibold text-gray-900">{data.total_feedback_count}</span> total</span>
            {data.unreviewed_count > 0 && <Badge className="bg-red-50 text-red-600 border-red-200">{data.unreviewed_count} unreviewed</Badge>}
            {data.avg_rating_overall !== null && <span className="flex items-center gap-1"><Star className="h-4 w-4 text-yellow-400 fill-yellow-400" />{data.avg_rating_overall.toFixed(1)} overall</span>}
          </div>
        )}
      </div>
      {isLoading && <Skeleton className="h-60 rounded-lg" />}
      {data?.by_unit.map((unit) => (
        <Card key={unit.unit_id} className="border shadow-sm">
          <CardHeader className="pb-2">
            <div className="flex items-start justify-between gap-3">
              <div>
                <CardTitle className="text-base">{unit.unit_name ?? unit.unit_id}</CardTitle>
                <div className="flex items-center gap-2 mt-1">
                  <span className="text-xs text-gray-400">{unit.feedback_count} item{unit.feedback_count !== 1 ? "s" : ""}</span>
                  {unit.trending && <span className="flex items-center gap-1 text-xs text-orange-600"><TrendingUp className="h-3 w-3" />Trending</span>}
                  {Object.entries(unit.category_breakdown).map(([cat, count]) => (
                    <Badge key={cat} className={cn("text-xs", CATEGORY_COLOR[cat] ?? CATEGORY_COLOR.general)}>{cat} ({count})</Badge>
                  ))}
                </div>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            {unit.feedback_items.map((item) => (
              <div key={item.feedback_id} className={cn("border rounded-lg p-3 space-y-1", item.reviewed ? "bg-gray-50 border-gray-100" : "bg-white border-gray-200")}>
                <div className="flex items-center gap-2">
                  <Badge className={cn("text-xs", CATEGORY_COLOR[item.category] ?? CATEGORY_COLOR.general)}>{item.category}</Badge>
                  <StarRating rating={item.rating} />
                  {!item.reviewed && <Badge className="text-xs bg-red-50 text-red-600 border-red-100 ml-auto">Unreviewed</Badge>}
                </div>
                <p className="text-sm text-gray-700">{item.message}</p>
                <p className="text-xs text-gray-400">{new Date(item.submitted_at).toLocaleDateString()}</p>
              </div>
            ))}
          </CardContent>
        </Card>
      ))}
      {!isLoading && data?.by_unit.length === 0 && (
        <div className="flex flex-col items-center py-12 text-gray-400 gap-2">
          <MessageSquare className="h-10 w-10" /><p className="text-sm">No feedback submitted yet.</p>
        </div>
      )}
    </div>
  );
}
