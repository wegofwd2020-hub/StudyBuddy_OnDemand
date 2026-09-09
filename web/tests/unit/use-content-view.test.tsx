/**
 * `useContentView` — the hook that records how long a student spends on a page.
 *
 * #741: `lesson_views.duration_s` is NULL for every row on the demo, so
 * `avg_lesson_duration_s` is null across 15 recorded views and every
 * reading-time report rests on a permanently empty column.
 *
 * The backend chain was measured end to end before writing this and it works:
 * POST /analytics/lesson/start -> 201, POST /analytics/lesson/end -> 200, and
 * `duration_s` lands in the row within two seconds via the Celery task. So the
 * defect is on this side of the seam.
 *
 * The hook had NO tests. It is the only caller of the beacon, and the beacon is
 * the only writer of the column.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";

const startLessonView = vi.fn();
const endLessonViewBeacon = vi.fn();

vi.mock("@/lib/api/analytics", () => ({
  startLessonView: (...a: unknown[]) => startLessonView(...a),
  endLessonViewBeacon: (...a: unknown[]) => endLessonViewBeacon(...a),
}));

import { useContentView } from "@/lib/hooks/useContentView";

beforeEach(() => {
  startLessonView.mockReset();
  endLessonViewBeacon.mockReset();
  startLessonView.mockResolvedValue({ view_id: "view-1" });
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
});

/** Let the `startLessonView` promise settle so `viewIdRef` is populated. */
async function settle() {
  await act(async () => {
    await Promise.resolve();
    await Promise.resolve();
  });
}

describe("useContentView", () => {
  it("does nothing until the content has loaded", () => {
    renderHook(() => useContentView("U1", false, "lesson"));
    expect(startLessonView).not.toHaveBeenCalled();
  });

  it("opens a view once the content is ready", async () => {
    renderHook(() => useContentView("U1", true, "lesson"));
    await settle();
    expect(startLessonView).toHaveBeenCalledWith("U1");
  });

  it("reports the elapsed time when the student navigates away", async () => {
    const { unmount } = renderHook(() => useContentView("U1", true, "lesson"));
    await settle();

    vi.advanceTimersByTime(137_000);
    act(() => unmount());

    expect(endLessonViewBeacon).toHaveBeenCalledTimes(1);
    const [viewId, duration] = endLessonViewBeacon.mock.calls[0];
    expect(viewId).toBe("view-1");
    expect(duration).toBe(137);
  });

  it("reports the elapsed time when the tab is closed", async () => {
    renderHook(() => useContentView("U1", true, "lesson"));
    await settle();

    vi.advanceTimersByTime(60_000);
    act(() => {
      window.dispatchEvent(new Event("pagehide"));
    });

    expect(endLessonViewBeacon).toHaveBeenCalledTimes(1);
    expect(endLessonViewBeacon.mock.calls[0][1]).toBe(60);
  });

  it("reports exactly once when the tab is closed AND the page unmounts", async () => {
    const { unmount } = renderHook(() => useContentView("U1", true, "lesson"));
    await settle();

    vi.advanceTimersByTime(30_000);
    act(() => {
      window.dispatchEvent(new Event("pagehide"));
    });
    act(() => unmount());

    // A second write is rejected by the API with 409 (`view_already_ended`),
    // which the beacon swallows -- so a duplicate is invisible rather than loud.
    expect(endLessonViewBeacon).toHaveBeenCalledTimes(1);
  });

  it("flags the content kind so tutorial and experiment time is attributable", async () => {
    const { unmount } = renderHook(() => useContentView("U1", true, "tutorial"));
    await settle();
    act(() => unmount());

    const [, , , experimentViewed, tutorialViewed] = endLessonViewBeacon.mock.calls[0];
    expect(tutorialViewed).toBe(true);
    expect(experimentViewed).toBe(false);
  });

  it("does not report a view that never opened", async () => {
    // The student left before `startLessonView` resolved: there is no view_id to
    // end, and sending one would 404.
    startLessonView.mockReturnValue(new Promise(() => {}));
    const { unmount } = renderHook(() => useContentView("U1", true, "lesson"));
    act(() => unmount());
    expect(endLessonViewBeacon).not.toHaveBeenCalled();
  });
});
