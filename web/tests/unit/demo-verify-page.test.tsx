import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import DemoVerifyPage from "@/app/(public)/demo/verify/[token]/page";

// ── Mocks ─────────────────────────────────────────────────────────────────────

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string) => key,
}));

vi.mock("next/navigation", () => ({
  useParams: vi.fn(() => ({ token: "valid-token-abc123" })),
}));

vi.mock("@/lib/api/demo", () => ({
  verifyDemoEmail: vi.fn(),
}));

import { useParams } from "next/navigation";
import { verifyDemoEmail } from "@/lib/api/demo";

const mockUseParams = vi.mocked(useParams);
const mockVerify = vi.mocked(verifyDemoEmail);

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("DemoVerifyPage — loading state", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseParams.mockReturnValue({ token: "valid-token" });
    // Never resolves so we observe loading state
    mockVerify.mockReturnValue(new Promise(() => {}));
  });

  it("shows loading spinner while verifying", () => {
    render(<DemoVerifyPage />);
    expect(screen.getByText("verify_loading")).toBeInTheDocument();
  });
});

describe("DemoVerifyPage — success", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseParams.mockReturnValue({ token: "valid-token" });
    mockVerify.mockResolvedValue({ message: "Account created." });
  });

  it("shows success title after verification", async () => {
    render(<DemoVerifyPage />);
    await waitFor(() =>
      expect(screen.getByText("verify_success_title")).toBeInTheDocument(),
    );
  });

  it("shows success body text", async () => {
    render(<DemoVerifyPage />);
    await waitFor(() =>
      expect(screen.getByText("verify_success_body")).toBeInTheDocument(),
    );
  });

  it("renders sign-in CTA link pointing to /demo/login", async () => {
    render(<DemoVerifyPage />);
    await waitFor(() =>
      expect(screen.getByRole("link", { name: "verify_success_cta" })).toHaveAttribute(
        "href",
        "/demo/login",
      ),
    );
  });
});

describe("DemoVerifyPage — token_already_used (409)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseParams.mockReturnValue({ token: "used-token" });
    mockVerify.mockRejectedValue({
      response: { status: 409, data: { error: "token_already_used" } },
    });
  });

  it("shows 'used' title", async () => {
    render(<DemoVerifyPage />);
    await waitFor(() =>
      expect(screen.getByText("verify_used_title")).toBeInTheDocument(),
    );
  });

  it("renders sign-in CTA pointing to /demo/login", async () => {
    render(<DemoVerifyPage />);
    await waitFor(() =>
      expect(screen.getByRole("link", { name: "verify_used_cta" })).toHaveAttribute(
        "href",
        "/demo/login",
      ),
    );
  });
});

describe("DemoVerifyPage — token_expired", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseParams.mockReturnValue({ token: "expired-token" });
    mockVerify.mockRejectedValue({
      response: { status: 410, data: { error: "token_expired" } },
    });
  });

  it("shows 'expired' title", async () => {
    render(<DemoVerifyPage />);
    await waitFor(() =>
      expect(screen.getByText("verify_expired_title")).toBeInTheDocument(),
    );
  });

  it("renders CTA pointing back to home", async () => {
    render(<DemoVerifyPage />);
    await waitFor(() =>
      expect(screen.getByRole("link", { name: "verify_expired_cta" })).toHaveAttribute(
        "href",
        "/",
      ),
    );
  });
});

describe("DemoVerifyPage — token_not_found (404)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseParams.mockReturnValue({ token: "bad-token" });
    mockVerify.mockRejectedValue({
      response: { status: 404, data: { error: "token_not_found" } },
    });
  });

  it("shows 'invalid' title", async () => {
    render(<DemoVerifyPage />);
    await waitFor(() =>
      expect(screen.getByText("verify_invalid_title")).toBeInTheDocument(),
    );
  });
});

describe("DemoVerifyPage — demo_capacity_reached", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseParams.mockReturnValue({ token: "valid-token" });
    mockVerify.mockRejectedValue({
      response: { status: 503, data: { error: "demo_capacity_reached" } },
    });
  });

  it("shows 'capacity' title", async () => {
    render(<DemoVerifyPage />);
    await waitFor(() =>
      expect(screen.getByText("verify_capacity_title")).toBeInTheDocument(),
    );
  });
});

describe("DemoVerifyPage — unknown error", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseParams.mockReturnValue({ token: "valid-token" });
    mockVerify.mockRejectedValue(new Error("network failure"));
  });

  it("shows generic error title", async () => {
    render(<DemoVerifyPage />);
    await waitFor(() =>
      expect(screen.getByText("verify_error_title")).toBeInTheDocument(),
    );
  });
});

describe("DemoVerifyPage — missing token", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseParams.mockReturnValue({ token: "" });
  });

  it("shows invalid state immediately without calling API", () => {
    render(<DemoVerifyPage />);
    expect(screen.getByText("verify_invalid_title")).toBeInTheDocument();
    expect(mockVerify).not.toHaveBeenCalled();
  });
});
