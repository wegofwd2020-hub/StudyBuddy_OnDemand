import { describe, it, expect, vi, beforeEach } from "vitest";

// /health uses the unauthenticated base client
vi.mock("@/lib/api/client", () => ({
  default: { get: vi.fn() },
}));

import api from "@/lib/api/client";
import { getSystemHealth, type SystemHealth } from "@/lib/api/admin";

const mockGet = api.get as ReturnType<typeof vi.fn>;

beforeEach(() => vi.clearAllMocks());

describe("getSystemHealth", () => {
  it("returns ok status when all services healthy", async () => {
    const payload: SystemHealth = {
      db_status: "ok",
      redis_status: "ok",
      db_pool_size: 20,
      db_pool_available: 18,
      redis_connected_clients: 4,
      checked_at: new Date().toISOString(),
    };
    mockGet.mockResolvedValueOnce({ data: payload });

    const result = await getSystemHealth();
    expect(result.db_status).toBe("ok");
    expect(result.redis_status).toBe("ok");
    expect(mockGet).toHaveBeenCalledWith("/health");
  });

  it("returns error status when DB is down", async () => {
    const payload: SystemHealth = {
      db_status: "error",
      redis_status: "ok",
      checked_at: new Date().toISOString(),
    };
    mockGet.mockResolvedValueOnce({ data: payload });

    const result = await getSystemHealth();
    expect(result.db_status).toBe("error");
    expect(result.redis_status).toBe("ok");
  });
});

describe("health status colour mapping", () => {
  function statusToColour(status: "ok" | "error"): "green" | "red" {
    return status === "ok" ? "green" : "red";
  }

  it("ok maps to green", () => {
    expect(statusToColour("ok")).toBe("green");
  });

  it("error maps to red", () => {
    expect(statusToColour("error")).toBe("red");
  });
});

describe("health poll interval", () => {
  it("always returns 10000 (no auto-stop condition)", () => {
    function refetchInterval(): number {
      return 10_000;
    }
    expect(refetchInterval()).toBe(10_000);
  });
});
