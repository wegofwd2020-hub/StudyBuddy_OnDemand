import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import DemoLoginPage from "@/app/(public)/demo/login/page";

// ── Mocks ─────────────────────────────────────────────────────────────────────

const mockPush = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: vi.fn(() => ({ push: mockPush })),
}));

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string) => key,
}));

vi.mock("next/link", () => ({
  default: ({ href, children }: { href: string; children: React.ReactNode }) => (
    <a href={href}>{children}</a>
  ),
}));

vi.mock("@/lib/api/demo", () => ({
  demoLogin: vi.fn(),
  resendDemoVerification: vi.fn(),
}));

import { demoLogin, resendDemoVerification } from "@/lib/api/demo";

const mockDemoLogin = vi.mocked(demoLogin);
const mockResend = vi.mocked(resendDemoVerification);

// ── localStorage stub ─────────────────────────────────────────────────────────

const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: (k: string) => store[k] ?? null,
    setItem: (k: string, v: string) => {
      store[k] = v;
    },
    removeItem: (k: string) => {
      delete store[k];
    },
    clear: () => {
      store = {};
    },
  };
})();
Object.defineProperty(window, "localStorage", { value: localStorageMock });

// ── Helpers ───────────────────────────────────────────────────────────────────

const EMAIL = "demo@example.com";
const PASSWORD = "Study1a2b3c4d";
const TOKEN = "eyJ.demo.token";

function fillAndSubmit(email = EMAIL, password = PASSWORD) {
  fireEvent.change(screen.getByLabelText("email_label"), {
    target: { value: email },
  });
  fireEvent.change(screen.getByLabelText("password_label"), {
    target: { value: password },
  });
  fireEvent.click(screen.getByRole("button", { name: "login_btn" }));
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("DemoLoginPage — renders", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorageMock.clear();
    mockDemoLogin.mockResolvedValue({
      access_token: TOKEN,
      token_type: "bearer",
      demo_expires_at: new Date(Date.now() + 86400_000).toISOString(),
    });
  });

  it("renders the page heading", () => {
    render(<DemoLoginPage />);
    expect(screen.getByText("login_title")).toBeInTheDocument();
  });

  it("renders the email input", () => {
    render(<DemoLoginPage />);
    expect(screen.getByLabelText("email_label")).toBeInTheDocument();
  });

  it("renders the password input", () => {
    render(<DemoLoginPage />);
    expect(screen.getByLabelText("password_label")).toBeInTheDocument();
  });

  it("renders the sign-in button", () => {
    render(<DemoLoginPage />);
    expect(screen.getByRole("button", { name: "login_btn" })).toBeInTheDocument();
  });

  it("renders the resend credentials link", () => {
    render(<DemoLoginPage />);
    expect(screen.getByText("resend_link")).toBeInTheDocument();
  });
});

describe("DemoLoginPage — successful login", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorageMock.clear();
    mockDemoLogin.mockResolvedValue({
      access_token: TOKEN,
      token_type: "bearer",
      demo_expires_at: new Date(Date.now() + 86400_000).toISOString(),
    });
  });

  it("calls demoLogin with email and password", async () => {
    render(<DemoLoginPage />);
    fillAndSubmit();
    await waitFor(() => expect(mockDemoLogin).toHaveBeenCalledWith(EMAIL, PASSWORD));
  });

  it("stores access_token in localStorage as sb_token", async () => {
    render(<DemoLoginPage />);
    fillAndSubmit();
    await waitFor(() => expect(localStorageMock.getItem("sb_token")).toBe(TOKEN));
  });

  it("redirects to /dashboard on success", async () => {
    render(<DemoLoginPage />);
    fillAndSubmit();
    await waitFor(() => expect(mockPush).toHaveBeenCalledWith("/dashboard"));
  });
});

describe("DemoLoginPage — validation errors", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorageMock.clear();
  });

  it("shows validation error when submitting empty fields", async () => {
    render(<DemoLoginPage />);
    fireEvent.click(screen.getByRole("button", { name: "login_btn" }));
    await waitFor(() =>
      expect(screen.getByText("Valid email required")).toBeInTheDocument(),
    );
    expect(mockDemoLogin).not.toHaveBeenCalled();
  });
});

describe("DemoLoginPage — login errors", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorageMock.clear();
  });

  it("shows login_error_invalid on 401", async () => {
    mockDemoLogin.mockRejectedValue({
      response: { status: 401, data: { error: "invalid_credentials" } },
    });
    render(<DemoLoginPage />);
    fillAndSubmit();
    await waitFor(() =>
      expect(screen.getByText("login_error_invalid")).toBeInTheDocument(),
    );
  });

  it("shows login_error_expired when demo account expired", async () => {
    mockDemoLogin.mockRejectedValue({
      response: { status: 403, data: { error: "demo_expired" } },
    });
    render(<DemoLoginPage />);
    fillAndSubmit();
    await waitFor(() =>
      expect(screen.getByText("login_error_expired")).toBeInTheDocument(),
    );
  });

  it("shows login_error_generic on unknown error", async () => {
    mockDemoLogin.mockRejectedValue(new Error("network error"));
    render(<DemoLoginPage />);
    fillAndSubmit();
    await waitFor(() =>
      expect(screen.getByText("login_error_generic")).toBeInTheDocument(),
    );
  });

  it("does not store token on failure", async () => {
    mockDemoLogin.mockRejectedValue({
      response: { status: 401, data: { error: "invalid_credentials" } },
    });
    render(<DemoLoginPage />);
    fillAndSubmit();
    await waitFor(() => screen.getByText("login_error_invalid"));
    expect(localStorageMock.getItem("sb_token")).toBeNull();
  });

  it("does not redirect on failure", async () => {
    mockDemoLogin.mockRejectedValue({ response: { status: 401 } });
    render(<DemoLoginPage />);
    fillAndSubmit();
    await waitFor(() => screen.getByText("login_error_invalid"));
    expect(mockPush).not.toHaveBeenCalled();
  });
});

describe("DemoLoginPage — loading state", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorageMock.clear();
    mockDemoLogin.mockReturnValue(new Promise(() => {}));
  });

  it("shows login_loading while submitting", async () => {
    render(<DemoLoginPage />);
    fillAndSubmit();
    await waitFor(() => expect(screen.getByText("login_loading")).toBeInTheDocument());
  });

  it("disables the submit button while loading", async () => {
    render(<DemoLoginPage />);
    fillAndSubmit();
    await waitFor(() =>
      expect(screen.getByText("login_loading").closest("button")).toBeDisabled(),
    );
  });
});

describe("DemoLoginPage — resend credentials", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorageMock.clear();
    mockResend.mockResolvedValue(undefined);
  });

  it("calls resendDemoVerification with the entered email", async () => {
    render(<DemoLoginPage />);
    fireEvent.change(screen.getByLabelText("email_label"), {
      target: { value: EMAIL },
    });
    fireEvent.click(screen.getByText("resend_link"));
    await waitFor(() => expect(mockResend).toHaveBeenCalledWith(EMAIL));
  });

  it("shows confirmation after successful resend", async () => {
    render(<DemoLoginPage />);
    fireEvent.change(screen.getByLabelText("email_label"), {
      target: { value: EMAIL },
    });
    fireEvent.click(screen.getByText("resend_link"));
    await waitFor(() => expect(screen.getByText(/resent/i)).toBeInTheDocument());
  });
});
