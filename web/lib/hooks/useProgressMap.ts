import { useQuery } from "@tanstack/react-query";

import api from "@/lib/api/client";
import type { UnitStatus } from "@/lib/types/api";

export interface ProgressMapUnit {
  unit_id: string;
  title: string;
  status: UnitStatus;
  best_score: number | null;
  attempts: number;
  last_attempt_at: string | null;
}

export interface ProgressMapSubject {
  subject: string;
  units_total: number;
  units_completed: number;
  units: ProgressMapUnit[];
}

export interface ProgressMap {
  curriculum_id: string;
  pending_count: number;
  needs_retry_count: number;
  subjects: ProgressMapSubject[];
}

/**
 * Per-unit status, from the server (#677).
 *
 * The one place a unit's status comes from. The Curriculum Map used to derive
 * it in the browser out of quiz sessions:
 *
 *     if (passed.length > 0)         status = "completed";
 *     else if (completed.length > 0) status = "needs_retry";
 *     else                           status = "in_progress";
 *
 * which is a separate definition from the server's, has no lesson input at all,
 * and cannot produce `not_started`. #675 fixed the server's definition to count
 * lessons — but this endpoint had no callers, so the screen kept showing the
 * browser's version and the fix was invisible.
 */
export function useProgressMap() {
  return useQuery({
    queryKey: ["progress-map"],
    queryFn: async () => {
      const res = await api.get<ProgressMap>("/student/progress");
      return res.data;
    },
  });
}

/** unit_id -> status, for pages that render units from the curriculum tree. */
export function useUnitStatuses() {
  const query = useProgressMap();
  const map = new Map<string, UnitStatus>();
  query.data?.subjects.forEach((s) =>
    s.units.forEach((u) => map.set(u.unit_id, u.status)),
  );
  return { ...query, statusByUnit: map };
}
