import { useQuery } from "@tanstack/react-query";
import { getProgressHistory } from "@/lib/api/progress";

export function useProgressHistory(limit = 20) {
  return useQuery({
    queryKey: ["progress", "history", limit],
    queryFn: () => getProgressHistory(limit),
  });
}
