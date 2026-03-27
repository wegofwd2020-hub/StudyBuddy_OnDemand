import { useQuery } from "@tanstack/react-query";
import { getStudentStats } from "@/lib/api/analytics";

export function useStudentStats(period: "7d" | "30d" | "all" = "30d") {
  return useQuery({
    queryKey: ["stats", period],
    queryFn: () => getStudentStats(period),
  });
}
