/**
 * Session lifetime rules (#601).
 *
 * Reported by Venki: closing the browser without signing out and reopening
 * /dashboard showed the previous user's data. The refresh token was valid for
 * 30 days in localStorage with no idle timeout and no opt-out, so the session
 * simply never ended.
 *
 * These pin the two rules that replace that: a session dies with the browser
 * unless the user asked otherwise, and dies after inactivity either way.
 */

import { describe, expect, it } from "vitest";
import {
  INACTIVITY_LIMIT_MS,
  evaluateSession,
  shouldClear,
  type SessionSnapshot,
} from "@/lib/auth/session-policy";

const NOW = 1_700_000_000_000;

function snapshot(overrides: Partial<SessionSnapshot> = {}): SessionSnapshot {
  return {
    remembered: false,
    aliveMarker: true,
    lastSeen: NOW - 1000,
    now: NOW,
    ...overrides,
  };
}

describe("evaluateSession", () => {
  it("keeps an active session in the same browser session", () => {
    expect(evaluateSession(snapshot())).toBe("keep");
  });

  it("ends the session when the browser was closed and re-opened", () => {
    // sessionStorage is wiped on browser close, so a missing marker means a
    // fresh browser start — the case Venki actually hit.
    expect(evaluateSession(snapshot({ aliveMarker: false }))).toBe(
      "expired_browser_closed",
    );
  });

  it("survives a browser restart when the user asked to stay signed in", () => {
    expect(evaluateSession(snapshot({ aliveMarker: false, remembered: true }))).toBe(
      "keep",
    );
  });

  it("ends the session after the inactivity limit", () => {
    const stale = snapshot({ lastSeen: NOW - INACTIVITY_LIMIT_MS - 1 });
    expect(evaluateSession(stale)).toBe("expired_idle");
  });

  it("applies the idle limit even to a remembered session", () => {
    // "Keep me signed in" is not consent to leaving a machine unattended.
    const stale = snapshot({
      remembered: true,
      aliveMarker: true,
      lastSeen: NOW - INACTIVITY_LIMIT_MS - 1,
    });
    expect(evaluateSession(stale)).toBe("expired_idle");
  });

  it("does not expire a session exactly at the limit", () => {
    const edge = snapshot({ lastSeen: NOW - INACTIVITY_LIMIT_MS });
    expect(evaluateSession(edge)).toBe("keep");
  });

  it("keeps a session that has no recorded activity yet", () => {
    // A session that just started has nothing to compare against; expiring it
    // would sign the user out immediately after login.
    expect(evaluateSession(snapshot({ lastSeen: null }))).toBe("keep");
  });

  it("treats a fresh browser start as ended before checking idleness", () => {
    const both = snapshot({
      aliveMarker: false,
      lastSeen: NOW - INACTIVITY_LIMIT_MS - 1,
    });
    expect(evaluateSession(both)).toBe("expired_browser_closed");
  });
});

describe("shouldClear", () => {
  it("clears credentials for every expiry reason", () => {
    expect(shouldClear("expired_browser_closed")).toBe(true);
    expect(shouldClear("expired_idle")).toBe(true);
  });

  it("keeps credentials when the session is still valid", () => {
    expect(shouldClear("keep")).toBe(false);
  });
});

describe("INACTIVITY_LIMIT_MS", () => {
  it("is the agreed 30 minutes", () => {
    expect(INACTIVITY_LIMIT_MS).toBe(30 * 60 * 1000);
  });
});
