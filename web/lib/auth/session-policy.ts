/**
 * Session lifetime policy (issue #601).
 *
 * Signing in used to leave a refresh token valid for 30 days in localStorage,
 * with no idle timeout and no way to opt out. Reopening the browser dropped the
 * next person straight into the previous user's account — fine for a shopping
 * site, not for a shared classroom or lab machine holding student records.
 *
 * Two rules now apply:
 *
 *   1. A session ends when the browser closes, UNLESS the user ticked
 *      "Keep me signed in".
 *   2. A session ends after INACTIVITY_LIMIT_MS with no interaction, either way.
 *
 * Implementation note: the tokens stay in localStorage rather than moving to
 * sessionStorage. Around forty files read those keys directly, and moving them
 * would mean touching every one. Instead sessionStorage holds a single liveness
 * marker — it is wiped when the browser closes, so its absence on load is
 * exactly the "new browser session" signal we need. Same behaviour, far less
 * surface area.
 */

export const INACTIVITY_LIMIT_MS = 30 * 60 * 1000; // 30 minutes

/** Set when the user opts into surviving a browser restart. */
export const REMEMBER_KEY = "sb_remember_me";
/** Wiped by the browser on close — its absence means a fresh browser session. */
export const ALIVE_KEY = "sb_session_alive";
/** Epoch ms of the last interaction, used for the idle check across reloads. */
export const LAST_SEEN_KEY = "sb_last_seen";

export interface SessionSnapshot {
  /** Did the user tick "Keep me signed in" when they signed in? */
  remembered: boolean;
  /** Was this browser session already alive (i.e. not a fresh browser start)? */
  aliveMarker: boolean;
  /** Epoch ms of last recorded activity, or null if never recorded. */
  lastSeen: number | null;
  /** Epoch ms now. */
  now: number;
}

export type SessionVerdict = "keep" | "expired_browser_closed" | "expired_idle";

/**
 * Decide whether a stored session may continue.
 *
 * Kept pure so the rules can be tested without a DOM: the interesting part is
 * the decision, not the storage plumbing.
 */
export function evaluateSession(snapshot: SessionSnapshot): SessionVerdict {
  const { remembered, aliveMarker, lastSeen, now } = snapshot;

  // A fresh browser session with no opt-in means the previous session ended
  // when the browser closed, even though the token is technically still valid.
  if (!aliveMarker && !remembered) return "expired_browser_closed";

  // Idle expiry applies whether or not the user opted in — an unattended
  // machine is the risk, and "keep me signed in" is not consent to that.
  if (lastSeen !== null && now - lastSeen > INACTIVITY_LIMIT_MS) {
    return "expired_idle";
  }

  return "keep";
}

/** True when the verdict means the stored credentials must be discarded. */
export function shouldClear(verdict: SessionVerdict): boolean {
  return verdict !== "keep";
}
