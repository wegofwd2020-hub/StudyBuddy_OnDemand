import { useQuery } from "@tanstack/react-query";
import { getSubscriptionStatus } from "@/lib/api/subscription";

export function useSubscription() {
  return useQuery({
    queryKey: ["subscription", "status"],
    queryFn: getSubscriptionStatus,
    staleTime: 60_000,
  });
}

/** Returns days remaining in trial, or null if not in trial */
export function trialDaysRemaining(trialEndsAt: string | null): number | null {
  if (!trialEndsAt) return null;
  const diff = new Date(trialEndsAt).getTime() - Date.now();
  if (diff <= 0) return 0;
  return Math.ceil(diff / (1000 * 60 * 60 * 24));
}
