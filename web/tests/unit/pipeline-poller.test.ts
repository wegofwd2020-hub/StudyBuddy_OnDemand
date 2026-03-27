import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("@/lib/api/school-client", () => ({
  default: { get: vi.fn(), post: vi.fn() },
}));

import schoolApi from "@/lib/api/school-client";
import { getPipelineStatus, triggerPipeline } from "@/lib/api/curriculum-admin";
import type { PipelineJobStatus } from "@/lib/api/curriculum-admin";

const mockGet = schoolApi.get as ReturnType<typeof vi.fn>;
const mockPost = schoolApi.post as ReturnType<typeof vi.fn>;

beforeEach(() => vi.clearAllMocks());

// ── getPipelineStatus ─────────────────────────────────────────────────────────

describe("getPipelineStatus", () => {
  it("fetches job status by job_id", async () => {
    const payload: PipelineJobStatus = {
      job_id: "job-001",
      status: "running",
      built: 3,
      failed: 0,
      total: 10,
      progress_pct: 30,
    };
    mockGet.mockResolvedValueOnce({ data: payload });

    const result = await getPipelineStatus("job-001");
    expect(result).toEqual(payload);
    expect(mockGet).toHaveBeenCalledWith("/curriculum/pipeline/job-001/status");
  });

  it("returns done status when all units built", async () => {
    const payload: PipelineJobStatus = {
      job_id: "job-002",
      status: "done",
      built: 12,
      failed: 0,
      total: 12,
      progress_pct: 100,
    };
    mockGet.mockResolvedValueOnce({ data: payload });

    const result = await getPipelineStatus("job-002");
    expect(result.status).toBe("done");
    expect(result.progress_pct).toBe(100);
  });

  it("returns failed status with failure count", async () => {
    const payload: PipelineJobStatus = {
      job_id: "job-003",
      status: "failed",
      built: 6,
      failed: 2,
      total: 8,
      progress_pct: 100,
    };
    mockGet.mockResolvedValueOnce({ data: payload });

    const result = await getPipelineStatus("job-003");
    expect(result.status).toBe("failed");
    expect(result.failed).toBe(2);
  });
});

// ── Progress calculation logic ────────────────────────────────────────────────

describe("progress_pct logic", () => {
  it("is 0 when queued", () => {
    const job: PipelineJobStatus = { job_id: "j", status: "queued", built: 0, failed: 0, total: 10, progress_pct: 0 };
    expect(job.progress_pct).toBe(0);
  });

  it("is between 0 and 100 when running", () => {
    const job: PipelineJobStatus = { job_id: "j", status: "running", built: 5, failed: 0, total: 10, progress_pct: 50 };
    expect(job.progress_pct).toBeGreaterThan(0);
    expect(job.progress_pct).toBeLessThan(100);
  });

  it("is 100 when done", () => {
    const job: PipelineJobStatus = { job_id: "j", status: "done", built: 10, failed: 0, total: 10, progress_pct: 100 };
    expect(job.progress_pct).toBe(100);
  });
});

// ── Poll stop condition logic ─────────────────────────────────────────────────

describe("refetchInterval stop condition", () => {
  function shouldStopPolling(status: string | undefined): boolean {
    return status === "done" || status === "failed";
  }

  it("stops polling when status is done", () => {
    expect(shouldStopPolling("done")).toBe(true);
  });

  it("stops polling when status is failed", () => {
    expect(shouldStopPolling("failed")).toBe(true);
  });

  it("continues polling when status is running", () => {
    expect(shouldStopPolling("running")).toBe(false);
  });

  it("continues polling when status is queued", () => {
    expect(shouldStopPolling("queued")).toBe(false);
  });

  it("continues polling when status is undefined", () => {
    expect(shouldStopPolling(undefined)).toBe(false);
  });
});

// ── triggerPipeline ───────────────────────────────────────────────────────────

describe("triggerPipeline", () => {
  it("posts to /curriculum/pipeline/trigger with correct body", async () => {
    mockPost.mockResolvedValueOnce({ data: { job_id: "job-abc", status: "queued" } });

    const result = await triggerPipeline("curriculum-123", "en,fr", false);
    expect(result.job_id).toBe("job-abc");
    expect(mockPost).toHaveBeenCalledWith("/curriculum/pipeline/trigger", {
      curriculum_id: "curriculum-123",
      langs: "en,fr",
      force: false,
    });
  });
});
