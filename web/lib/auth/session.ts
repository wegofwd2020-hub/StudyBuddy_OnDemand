"use client";

/**
 * Browser-side plumbing for the session rules in `session-policy.ts` (#601).
 *
 * The decision logic lives there and is pure; this file only reads and writes
 * storage. Tokens deliberately stay in localStorage — see the note in
 * session-policy.ts for why sessionStorage holds only a liveness marker.
 */

import {
  ALIVE_KEY,
  LAST_SEEN_KEY,
  REMEMBER_KEY,
  evaluateSession,
  shouldClear,
  type SessionVerdict,
} from "./session-policy";

/** Everything that authenticates a user or names them on screen. */
const SESSION_KEYS = [
  "sb_token",
  "sb_teacher_token",
  "sb_teacher_refresh_token",
  "sb_admin_token",
];

const SESSION_COOKIES = [
  "sb_local_student_session",
  "sb_local_teacher_session",
  "sb_dev_session",
  "sb_demo_teacher_session",
];

/** Record whether this sign-in should survive closing the browser. */
export function setRemembered(remember: boolean): void {
  if (typeof window === "undefined") return;
  if (remember) localStorage.setItem(REMEMBER_KEY, "1");
  else localStorage.removeItem(REMEMBER_KEY);
}

/** Stamp the current browser session as alive and note the time. */
export function markSessionAlive(): void {
  if (typeof window === "undefined") return;
  sessionStorage.setItem(ALIVE_KEY, "1");
  localStorage.setItem(LAST_SEEN_KEY, String(Date.now()));
}

export function recordActivity(): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(LAST_SEEN_KEY, String(Date.now()));
}

/** Drop every credential and session cookie. */
export function clearSession(): void {
  if (typeof window === "undefined") return;
  for (const key of SESSION_KEYS) localStorage.removeItem(key);
  localStorage.removeItem(LAST_SEEN_KEY);
  localStorage.removeItem(REMEMBER_KEY);
  sessionStorage.removeItem(ALIVE_KEY);
  for (const name of SESSION_COOKIES) {
    document.cookie = `${name}=; path=/; Max-Age=0; SameSite=Strict`;
  }
}

/** True when any credential is currently stored. */
export function hasStoredSession(): boolean {
  if (typeof window === "undefined") return false;
  return SESSION_KEYS.some((key) => localStorage.getItem(key));
}

/**
 * Apply the policy to whatever is currently stored.
 *
 * Returns the verdict so the caller can decide where to send the user; the
 * credentials are already gone by then if the session ended.
 */
export function enforceSessionPolicy(): SessionVerdict {
  if (typeof window === "undefined") return "keep";
  if (!hasStoredSession()) {
    markSessionAlive();
    return "keep";
  }

  const lastSeenRaw = localStorage.getItem(LAST_SEEN_KEY);
  const verdict = evaluateSession({
    remembered: localStorage.getItem(REMEMBER_KEY) === "1",
    aliveMarker: sessionStorage.getItem(ALIVE_KEY) === "1",
    lastSeen: lastSeenRaw ? Number(lastSeenRaw) : null,
    now: Date.now(),
  });

  if (shouldClear(verdict)) {
    clearSession();
  } else {
    markSessionAlive();
  }
  return verdict;
}
