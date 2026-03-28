/**
 * Unit tests for section 4.1 — Admin Login (`/admin/login`)
 * Covers TC-IDs: ADM-01, ADM-02, ADM-03, ADM-04
 *
 * Run with:
 *   npm test -- admin-login-page
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import AdminLoginPage from "@/app/(public)/admin/login/page";
import {
  LOGIN_STRINGS,
  VALID_CREDENTIALS,
} from "../e2e/data/admin-login-page";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

const mockPush = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: vi.fn(() => ({ push: mockPush, replace: mockPush })),
}));

const mockAdminLogin = vi.fn();
vi.mock("@/lib/api/admin", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api/admin")>();
  return {
    ...actual,
    adminLogin: (...args: unknown[]) => mockAdminLogin(...args),
  };
});

// Stub localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: (key: string) => store[key] ?? null,
    setItem: (key: string, value: string) => { store[key] = value; },
    removeItem: (key: string) => { delete store[key]; },
    clear: () => { store = {}; },
  };
})();
Object.defineProperty(window, "localStorage", { value: localStorageMock });

// ---------------------------------------------------------------------------
// ADM-01 — Login form renders
// ---------------------------------------------------------------------------

describe("ADM-01 — Login form renders", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorageMock.clear();
  });

  it("renders the page heading", () => {
    render(<AdminLoginPage />);
    expect(screen.getByText(LOGIN_STRINGS.pageHeading)).toBeInTheDocument();
  });

  it("renders the Email input field", () => {
    render(<AdminLoginPage />);
    expect(screen.getByLabelText(LOGIN_STRINGS.emailLabel)).toBeInTheDocument();
  });

  it("renders the Password input field", () => {
    render(<AdminLoginPage />);
    expect(screen.getByLabelText(LOGIN_STRINGS.passwordLabel)).toBeInTheDocument();
  });

  it("renders the Sign in button", () => {
    render(<AdminLoginPage />);
    expect(
      screen.getByRole("button", { name: LOGIN_STRINGS.signInBtn }),
    ).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// ADM-02 — Successful login stores token and redirects
// ---------------------------------------------------------------------------

describe("ADM-02 — Successful login stores token and redirects", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorageMock.clear();
    mockAdminLogin.mockResolvedValue({
      token: VALID_CREDENTIALS.token,
      admin_id: VALID_CREDENTIALS.admin_id,
    });
  });

  it("stores sb_admin_token in localStorage on success", async () => {
    render(<AdminLoginPage />);
    fireEvent.change(screen.getByLabelText(LOGIN_STRINGS.emailLabel), {
      target: { value: VALID_CREDENTIALS.email },
    });
    fireEvent.change(screen.getByLabelText(LOGIN_STRINGS.passwordLabel), {
      target: { value: VALID_CREDENTIALS.password },
    });
    fireEvent.click(screen.getByRole("button", { name: LOGIN_STRINGS.signInBtn }));
    await waitFor(() =>
      expect(localStorageMock.getItem("sb_admin_token")).toBe(VALID_CREDENTIALS.token),
    );
  });

  it("redirects to /admin/dashboard after successful login", async () => {
    render(<AdminLoginPage />);
    fireEvent.change(screen.getByLabelText(LOGIN_STRINGS.emailLabel), {
      target: { value: VALID_CREDENTIALS.email },
    });
    fireEvent.change(screen.getByLabelText(LOGIN_STRINGS.passwordLabel), {
      target: { value: VALID_CREDENTIALS.password },
    });
    fireEvent.click(screen.getByRole("button", { name: LOGIN_STRINGS.signInBtn }));
    await waitFor(() =>
      expect(mockPush).toHaveBeenCalledWith("/admin/dashboard"),
    );
  });
});

// ---------------------------------------------------------------------------
// ADM-03 — Failed login shows error message
// ---------------------------------------------------------------------------

describe("ADM-03 — Failed login shows error message", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorageMock.clear();
    mockAdminLogin.mockRejectedValue(new Error("401 Unauthorized"));
  });

  it("shows 'Invalid credentials' error on login failure", async () => {
    render(<AdminLoginPage />);
    fireEvent.change(screen.getByLabelText(LOGIN_STRINGS.emailLabel), {
      target: { value: "wrong@email.com" },
    });
    fireEvent.change(screen.getByLabelText(LOGIN_STRINGS.passwordLabel), {
      target: { value: "wrongpass" },
    });
    fireEvent.click(screen.getByRole("button", { name: LOGIN_STRINGS.signInBtn }));
    expect(await screen.findByText(LOGIN_STRINGS.errorMsg)).toBeInTheDocument();
  });

  it("does NOT store a token on login failure", async () => {
    render(<AdminLoginPage />);
    fireEvent.change(screen.getByLabelText(LOGIN_STRINGS.emailLabel), {
      target: { value: "wrong@email.com" },
    });
    fireEvent.change(screen.getByLabelText(LOGIN_STRINGS.passwordLabel), {
      target: { value: "wrongpass" },
    });
    fireEvent.click(screen.getByRole("button", { name: LOGIN_STRINGS.signInBtn }));
    await screen.findByText(LOGIN_STRINGS.errorMsg);
    expect(localStorageMock.getItem("sb_admin_token")).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// ADM-04 — Sign in button shows "Signing in…" while submitting
// ---------------------------------------------------------------------------

describe("ADM-04 — Sign in button shows loading state during submit", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorageMock.clear();
    // Never resolve so we can observe the loading state
    mockAdminLogin.mockReturnValue(new Promise(() => {}));
  });

  it("shows 'Signing in…' text while submitting", async () => {
    render(<AdminLoginPage />);
    fireEvent.change(screen.getByLabelText(LOGIN_STRINGS.emailLabel), {
      target: { value: VALID_CREDENTIALS.email },
    });
    fireEvent.change(screen.getByLabelText(LOGIN_STRINGS.passwordLabel), {
      target: { value: VALID_CREDENTIALS.password },
    });
    fireEvent.click(screen.getByRole("button", { name: LOGIN_STRINGS.signInBtn }));
    expect(await screen.findByText(LOGIN_STRINGS.signingInBtn)).toBeInTheDocument();
  });

  it("disables the button while submitting", async () => {
    render(<AdminLoginPage />);
    fireEvent.change(screen.getByLabelText(LOGIN_STRINGS.emailLabel), {
      target: { value: VALID_CREDENTIALS.email },
    });
    fireEvent.change(screen.getByLabelText(LOGIN_STRINGS.passwordLabel), {
      target: { value: VALID_CREDENTIALS.password },
    });
    fireEvent.click(screen.getByRole("button", { name: LOGIN_STRINGS.signInBtn }));
    await waitFor(() =>
      expect(screen.getByText(LOGIN_STRINGS.signingInBtn).closest("button")).toBeDisabled(),
    );
  });
});
