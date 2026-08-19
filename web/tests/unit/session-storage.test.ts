/**
 * Storage behaviour for the session rules (#601).
 *
 * The decision logic is tested in session-policy.test.ts; this covers the part
 * that touches the browser — that credentials are actually discarded when a
 * session ends, and kept when it has not.
 */

import { beforeEach, describe, expect, it } from "vitest";
import {
  clearSession,
  enforceSessionPolicy,
  hasStoredSession,
  markSessionAlive,
  recordActivity,
  setRemembered,
} from "@/lib/auth/session";
import { ALIVE_KEY, INACTIVITY_LIMIT_MS, LAST_SEEN_KEY } from "@/lib/auth/session-policy";

function signIn() {
  localStorage.setItem("sb_token", "student-jwt");
  localStorage.setItem("sb_teacher_token", "teacher-jwt");
  localStorage.setItem("sb_teacher_refresh_token", "refresh-jwt");
}

describe("session storage", () => {
  beforeEach(() => {
    localStorage.clear();
    sessionStorage.clear();
  });

  it("reports whether anything is stored", () => {
    expect(hasStoredSession()).toBe(false);
    signIn();
    expect(hasStoredSession()).toBe(true);
  });

  it("discards every credential when the session ends", () => {
    signIn();
    clearSession();

    expect(localStorage.getItem("sb_token")).toBeNull();
    expect(localStorage.getItem("sb_teacher_token")).toBeNull();
    expect(localStorage.getItem("sb_teacher_refresh_token")).toBeNull();
    expect(hasStoredSession()).toBe(false);
  });

  it("signs the user out when the browser was closed and re-opened", () => {
    // A stored token with no liveness marker is exactly the reported bug:
    // reopening the browser landed on the previous user's dashboard.
    signIn();
    recordActivity();
    sessionStorage.clear(); // what the browser does on close

    expect(enforceSessionPolicy()).toBe("expired_browser_closed");
    expect(hasStoredSession()).toBe(false);
  });

  it("keeps the user signed in across a restart when they asked for it", () => {
    signIn();
    setRemembered(true);
    recordActivity();
    sessionStorage.clear();

    expect(enforceSessionPolicy()).toBe("keep");
    expect(hasStoredSession()).toBe(true);
  });

  it("signs the user out after the inactivity limit", () => {
    signIn();
    markSessionAlive();
    localStorage.setItem(LAST_SEEN_KEY, String(Date.now() - INACTIVITY_LIMIT_MS - 1000));

    expect(enforceSessionPolicy()).toBe("expired_idle");
    expect(hasStoredSession()).toBe(false);
  });

  it("keeps an active session and refreshes the liveness marker", () => {
    signIn();
    markSessionAlive();
    recordActivity();

    expect(enforceSessionPolicy()).toBe("keep");
    expect(hasStoredSession()).toBe(true);
    expect(sessionStorage.getItem(ALIVE_KEY)).toBe("1");
  });

  it("does nothing when nobody is signed in", () => {
    expect(enforceSessionPolicy()).toBe("keep");
    expect(hasStoredSession()).toBe(false);
  });

  it("forgets the remember-me choice on sign out, so it cannot leak to the next user", () => {
    signIn();
    setRemembered(true);
    clearSession();
    signIn();
    sessionStorage.clear();

    expect(enforceSessionPolicy()).toBe("expired_browser_closed");
  });
});
