import { describe, it, expect, vi, beforeEach } from "vitest";

// ---------------------------------------------------------------------------
// Alert dismiss — test the optimistic update logic
// ---------------------------------------------------------------------------

vi.mock("@/lib/api/school-client", () => ({
  default: {
    get: vi.fn(),
    put: vi.fn(),
  },
}));

import schoolApi from "@/lib/api/school-client";
import { getAlerts, updateAlertSettings } from "@/lib/api/reports";
import type { AlertItem } from "@/lib/api/reports";

const mockGet = schoolApi.get as ReturnType<typeof vi.fn>;
const mockPut = schoolApi.put as ReturnType<typeof vi.fn>;

beforeEach(() => {
  vi.clearAllMocks();
});

// Fixture
const ALERT_A: AlertItem = {
  alert_id: "alert-001",
  alert_type: "pass_rate_low",
  school_id: "school-abc",
  details: { unit_id: "G8-MATH-001", pass_rate: 42 },
  triggered_at: "2026-03-20T09:00:00Z",
  acknowledged: false,
};

const ALERT_B: AlertItem = {
  alert_id: "alert-002",
  alert_type: "feedback_spike",
  school_id: "school-abc",
  details: { unit_id: "G8-SCI-002", count: 8 },
  triggered_at: "2026-03-21T10:00:00Z",
  acknowledged: false,
};

describe("getAlerts", () => {
  it("fetches alerts for a school", async () => {
    mockGet.mockResolvedValueOnce({ data: { alerts: [ALERT_A, ALERT_B] } });

    const result = await getAlerts("school-abc");
    expect(result.alerts).toHaveLength(2);
    expect(result.alerts[0].alert_id).toBe("alert-001");
    expect(mockGet).toHaveBeenCalledWith("/reports/school/school-abc/alerts");
  });

  it("returns empty list when no alerts", async () => {
    mockGet.mockResolvedValueOnce({ data: { alerts: [] } });
    const result = await getAlerts("school-abc");
    expect(result.alerts).toHaveLength(0);
  });
});

describe("optimistic alert dismiss logic", () => {
  it("filters acknowledged alerts from visible list", () => {
    const alerts: AlertItem[] = [ALERT_A, ALERT_B];
    const dismissed = new Set<string>(["alert-001"]);
    const visible = alerts.filter((a) => !a.acknowledged && !dismissed.has(a.alert_id));
    expect(visible).toHaveLength(1);
    expect(visible[0].alert_id).toBe("alert-002");
  });

  it("marks alert as acknowledged in cache update", () => {
    const alerts: AlertItem[] = [ALERT_A, ALERT_B];
    const updated = alerts.map((a) =>
      a.alert_id === "alert-001" ? { ...a, acknowledged: true } : a,
    );
    expect(updated[0].acknowledged).toBe(true);
    expect(updated[1].acknowledged).toBe(false);
  });

  it("acknowledging a non-existent id leaves list unchanged", () => {
    const alerts: AlertItem[] = [ALERT_A, ALERT_B];
    const updated = alerts.map((a) =>
      a.alert_id === "alert-999" ? { ...a, acknowledged: true } : a,
    );
    expect(updated.every((a) => !a.acknowledged)).toBe(true);
  });

  it("all alerts dismissed → visible list is empty", () => {
    const alerts: AlertItem[] = [ALERT_A, ALERT_B];
    const dismissed = new Set<string>(["alert-001", "alert-002"]);
    const visible = alerts.filter((a) => !a.acknowledged && !dismissed.has(a.alert_id));
    expect(visible).toHaveLength(0);
  });
});

describe("updateAlertSettings", () => {
  it("sends correct payload to API", async () => {
    mockPut.mockResolvedValueOnce({});
    await updateAlertSettings("school-abc", {
      pass_rate_threshold: 60,
      feedback_count_threshold: 5,
      inactive_days_threshold: 7,
      score_drop_threshold: 15,
      new_feedback_immediate: true,
    });
    expect(mockPut).toHaveBeenCalledWith("/reports/school/school-abc/alerts/settings", {
      pass_rate_threshold: 60,
      feedback_count_threshold: 5,
      inactive_days_threshold: 7,
      score_drop_threshold: 15,
      new_feedback_immediate: true,
    });
  });
});
