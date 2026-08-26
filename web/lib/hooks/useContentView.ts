import { useEffect, useRef } from "react";

import { endLessonViewBeacon, startLessonView } from "@/lib/api/analytics";

/**
 * Record time spent on a content page (issue #569).
 *
 * Only the Lesson page ever did this. Tutorial and Experiment — where the
 * worked examples and diagrams actually live — recorded nothing at all, so
 * every second a student spent there counted as zero: their own "Time spent",
 * the school admin's per-unit Time column, "Lessons viewed", and the
 * struggle / health / at-risk logic that reads the same tables to recommend
 * interventions.
 *
 * This is one hook rather than three copies of the same effect. The original
 * lived inline on the Lesson page, and duplicating it onto two more pages is
 * how the copies drift — the failure this codebase has hit repeatedly
 * (pitfall #31, and #464 below).
 *
 * Two behaviours worth preserving exactly, both learned the hard way:
 *
 *   - the end is flushed on BOTH effect cleanup (navigating within the app) and
 *     `pagehide` (closing or refreshing the tab), guarded by `endedRef` so it
 *     happens exactly once. Recording only on cleanup lost the duration
 *     whenever a student simply closed the tab, which is why "Time" showed 0m
 *     (#464).
 *   - `keepalive` on the beacon, so the write survives page unload.
 *
 * Deliberately does NOT open a progress session: a session is a quiz attempt.
 * The lesson page used to create one, producing phantom never-completed
 * attempts in Progress History (#465, #579).
 */
export type ContentKind = "lesson" | "tutorial" | "experiment";

export function useContentView(
  unitId: string,
  ready: boolean,
  kind: ContentKind,
  audioPlayedRef?: React.MutableRefObject<boolean>,
) {
  const viewIdRef = useRef<string | null>(null);
  const startTimeRef = useRef<number>(0);
  const endedRef = useRef(false);

  useEffect(() => {
    if (!ready) return;
    endedRef.current = false;
    startLessonView(unitId)
      .then((r) => {
        viewIdRef.current = r.view_id;
      })
      .catch(() => {});
    startTimeRef.current = Date.now();

    const flushEnd = () => {
      if (endedRef.current || !viewIdRef.current) return;
      endedRef.current = true;
      const duration = Math.round((Date.now() - startTimeRef.current) / 1000);
      endLessonViewBeacon(
        viewIdRef.current,
        duration,
        audioPlayedRef?.current ?? false,
        kind === "experiment",
        kind === "tutorial",
      );
    };

    window.addEventListener("pagehide", flushEnd);
    return () => {
      window.removeEventListener("pagehide", flushEnd);
      flushEnd();
    };
  }, [ready, unitId, kind, audioPlayedRef]);
}
