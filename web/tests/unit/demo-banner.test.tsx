import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { DemoBanner } from "@/components/demo/DemoBanner";
import { DemoGate } from "@/components/demo/DemoGate";

// ── Mocks ─────────────────────────────────────────────────────────────────────

vi.mock("next/link", () => ({
  default: ({ href, children }: { href: string; children: React.ReactNode }) => (
    <a href={href}>{children}</a>
  ),
}));

vi.mock("@/lib/api/demo", () => ({
  demoLogout: vi.fn().mockResolvedValue(undefined),
}));

type DemoStudentReturn = ReturnType<
  typeof import("@/lib/hooks/useDemoStudent").useDemoStudent
>;
const mockDemoStudent = vi.fn<() => DemoStudentReturn>();
vi.mock("@/lib/hooks/useDemoStudent", () => ({
  useDemoStudent: () => mockDemoStudent(),
}));

import { demoLogout } from "@/lib/api/demo";
const mockDemoLogout = vi.mocked(demoLogout);

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

const DEMO_EXPIRES_24H = new Date(Date.now() + 24 * 60 * 60 * 1_000).toISOString();
const DEMO_EXPIRES_1H = new Date(Date.now() + 60 * 60 * 1_000).toISOString();
const DEMO_EXPIRED = new Date(Date.now() - 1_000).toISOString();

const DEMO_CLAIMS = {
  student_id: "stu-1",
  grade: 8,
  locale: "en",
  demo_account_id: "demo-acct-1",
  demo_expires_at: DEMO_EXPIRES_24H,
};

// ── DemoBanner tests ──────────────────────────────────────────────────────────

describe("DemoBanner — not a demo session", () => {
  beforeEach(() => {
    mockDemoStudent.mockReturnValue(null);
  });

  it("renders nothing when useDemoStudent returns null", () => {
    const { container } = render(<DemoBanner />);
    expect(container.firstChild).toBeNull();
  });
});

describe("DemoBanner — active demo session", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorageMock.clear();
    mockDemoStudent.mockReturnValue(DEMO_CLAIMS);
  });

  it("renders the banner when demo claims are present", () => {
    render(<DemoBanner />);
    expect(screen.getByRole("status")).toBeInTheDocument();
  });

  it("shows 'Demo account' label", () => {
    render(<DemoBanner />);
    expect(screen.getByText("Demo account")).toBeInTheDocument();
  });

  it("shows hours remaining for a 24h demo", () => {
    render(<DemoBanner />);
    expect(screen.getByText(/left in your demo/i)).toBeInTheDocument();
  });

  it("renders 'Get full access' link pointing to /signup", () => {
    render(<DemoBanner />);
    expect(screen.getByRole("link", { name: "Get full access" })).toHaveAttribute(
      "href",
      "/signup",
    );
  });

  it("renders a sign-out button", () => {
    render(<DemoBanner />);
    expect(screen.getByRole("button", { name: /sign out/i })).toBeInTheDocument();
  });
});

describe("DemoBanner — urgent (< 2 hours remaining)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockDemoStudent.mockReturnValue({ ...DEMO_CLAIMS, demo_expires_at: DEMO_EXPIRES_1H });
  });

  it("applies red styling when under 2 hours remain", () => {
    render(<DemoBanner />);
    const banner = screen.getByRole("status");
    expect(banner.className).toContain("red");
  });

  it("shows minutes remaining for < 2h demo", () => {
    render(<DemoBanner />);
    expect(screen.getByText(/minute|left in your demo/i)).toBeInTheDocument();
  });
});

describe("DemoBanner — expired", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockDemoStudent.mockReturnValue({ ...DEMO_CLAIMS, demo_expires_at: DEMO_EXPIRED });
  });

  it("shows 'Demo expired' when past expiry", () => {
    render(<DemoBanner />);
    expect(screen.getByText(/demo expired/i)).toBeInTheDocument();
  });
});

describe("DemoBanner — sign out", () => {
  const TOKEN = "eyJ.demo.jwt";

  beforeEach(() => {
    vi.clearAllMocks();
    localStorageMock.clear();
    localStorageMock.setItem("sb_token", TOKEN);
    mockDemoStudent.mockReturnValue(DEMO_CLAIMS);
    mockDemoLogout.mockResolvedValue(undefined);
  });

  it("calls demoLogout with the stored token on sign-out click", async () => {
    render(<DemoBanner />);
    fireEvent.click(screen.getByRole("button", { name: /sign out/i }));
    await waitFor(() => expect(mockDemoLogout).toHaveBeenCalledWith(TOKEN));
  });

  it("removes sb_token from localStorage on sign-out", async () => {
    render(<DemoBanner />);
    fireEvent.click(screen.getByRole("button", { name: /sign out/i }));
    await waitFor(() => expect(localStorageMock.getItem("sb_token")).toBeNull());
  });

  it("clears sb_token even when demoLogout API call fails", async () => {
    mockDemoLogout.mockRejectedValue(new Error("network error"));
    render(<DemoBanner />);
    fireEvent.click(screen.getByRole("button", { name: /sign out/i }));
    await waitFor(() => expect(localStorageMock.getItem("sb_token")).toBeNull());
  });
});

// ── DemoGate tests ────────────────────────────────────────────────────────────

describe("DemoGate — regular student (no demo)", () => {
  beforeEach(() => {
    mockDemoStudent.mockReturnValue(null);
  });

  it("renders children when user is not a demo student", () => {
    render(
      <DemoGate>
        <p>Real content</p>
      </DemoGate>,
    );
    expect(screen.getByText("Real content")).toBeInTheDocument();
  });

  it("does not show the blocked screen for regular students", () => {
    render(
      <DemoGate>
        <p>Real content</p>
      </DemoGate>,
    );
    expect(screen.queryByText(/not available in demo/i)).toBeNull();
  });
});

describe("DemoGate — demo student", () => {
  beforeEach(() => {
    mockDemoStudent.mockReturnValue(DEMO_CLAIMS);
  });

  it("does not render children for demo students", () => {
    render(
      <DemoGate>
        <p>Real content</p>
      </DemoGate>,
    );
    expect(screen.queryByText("Real content")).toBeNull();
  });

  it("shows the default blocked heading", () => {
    render(
      <DemoGate>
        <p>x</p>
      </DemoGate>,
    );
    expect(screen.getByText("Not available in demo")).toBeInTheDocument();
  });

  it("shows a custom heading when provided", () => {
    render(
      <DemoGate heading="Subscription locked">
        <p>x</p>
      </DemoGate>,
    );
    expect(screen.getByText("Subscription locked")).toBeInTheDocument();
  });

  it("renders 'Sign up for full access' link pointing to /signup", () => {
    render(
      <DemoGate>
        <p>x</p>
      </DemoGate>,
    );
    expect(screen.getByRole("link", { name: "Sign up for full access" })).toHaveAttribute(
      "href",
      "/signup",
    );
  });

  it("renders a 'Back to dashboard' link", () => {
    render(
      <DemoGate>
        <p>x</p>
      </DemoGate>,
    );
    expect(screen.getByRole("link", { name: "Back to dashboard" })).toHaveAttribute(
      "href",
      "/dashboard",
    );
  });
});
