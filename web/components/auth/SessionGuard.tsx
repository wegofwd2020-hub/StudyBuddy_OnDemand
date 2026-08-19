"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { enforceSessionPolicy, recordActivity } from "@/lib/auth/session";
import { INACTIVITY_LIMIT_MS } from "@/lib/auth/session-policy";

/**
 * Enforces the session rules on every portal page (#601).
 *
 * Two jobs:
 *   - on mount, decide whether the stored session may continue at all
 *   - while mounted, keep the idle clock honest and sign the user out when it
 *     runs out
 *
 * Rendered inside the portal layouts so it covers every authenticated page
 * rather than relying on individual pages to remember.
 */

/** How often to re-check idleness. Coarse on purpose — this is not a stopwatch. */
const CHECK_INTERVAL_MS = 60 * 1000;

const ACTIVITY_EVENTS = ["click", "keydown", "pointerdown", "scroll"] as const;

export function SessionGuard({ signInPath = "/signin" }: { signInPath?: string }) {
  const router = useRouter();

  useEffect(() => {
    function expireIfNeeded() {
      const verdict = enforceSessionPolicy();
      if (verdict !== "keep") {
        // `reason` lets the sign-in page explain why they are back here rather
        // than appearing to have logged them out at random.
        router.replace(`${signInPath}?reason=${verdict}`);
      }
    }

    expireIfNeeded();

    // Throttle: every interaction would otherwise write to localStorage.
    let lastWrite = 0;
    function onActivity() {
      const now = Date.now();
      if (now - lastWrite < 30_000) return;
      lastWrite = now;
      recordActivity();
    }

    for (const evt of ACTIVITY_EVENTS) {
      window.addEventListener(evt, onActivity, { passive: true });
    }
    const timer = window.setInterval(expireIfNeeded, CHECK_INTERVAL_MS);
    // Returning to a tab that sat untouched is the moment the idle rule matters.
    document.addEventListener("visibilitychange", expireIfNeeded);

    return () => {
      for (const evt of ACTIVITY_EVENTS) window.removeEventListener(evt, onActivity);
      window.clearInterval(timer);
      document.removeEventListener("visibilitychange", expireIfNeeded);
    };
  }, [router, signInPath]);

  return null;
}

export { INACTIVITY_LIMIT_MS };
