import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";
import { DemoRequestModal } from "@/components/demo/DemoRequestModal";

// ── Mocks ────────────────────────────────────────────────────────────────────

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string, params?: Record<string, string>) => {
    if (params?.email) return `Check your email at ${params.email}`;
    return key;
  },
}));

vi.mock("next/link", () => ({
  default: ({
    href,
    children,
    onClick,
  }: {
    href: string;
    children: React.ReactNode;
    onClick?: () => void;
  }) => (
    <a href={href} onClick={onClick}>
      {children}
    </a>
  ),
}));

vi.mock("@/lib/api/demo", () => ({
  requestDemo: vi.fn(),
}));

import { requestDemo } from "@/lib/api/demo";

const mockRequestDemo = vi.mocked(requestDemo);

// ── Helpers ───────────────────────────────────────────────────────────────────

function openDialog() {
  const trigger = screen.getByRole("button", { name: "hero_cta" });
  fireEvent.click(trigger);
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("DemoRequestModal", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockRequestDemo.mockResolvedValue({ message: "ok" });
  });

  it("renders the trigger button", () => {
    render(<DemoRequestModal />);
    expect(screen.getByRole("button", { name: "hero_cta" })).toBeTruthy();
  });

  it("opens the dialog when trigger button is clicked", async () => {
    render(<DemoRequestModal />);
    openDialog();
    await waitFor(() => {
      expect(screen.getByText("modal_title")).toBeTruthy();
    });
  });

  it("renders the email input inside the dialog", async () => {
    render(<DemoRequestModal />);
    openDialog();
    await waitFor(() => {
      expect(screen.getByRole("textbox")).toBeTruthy();
    });
  });

  it("shows validation error when submitting empty email", async () => {
    render(<DemoRequestModal />);
    openDialog();
    await waitFor(() => screen.getByRole("button", { name: "submit_btn" }));

    fireEvent.click(screen.getByRole("button", { name: "submit_btn" }));
    await waitFor(() => {
      expect(screen.getByText("Valid email required")).toBeTruthy();
    });
    expect(mockRequestDemo).not.toHaveBeenCalled();
  });

  it("calls requestDemo with the entered email on submit", async () => {
    render(<DemoRequestModal />);
    openDialog();
    await waitFor(() => screen.getByRole("textbox"));

    fireEvent.change(screen.getByRole("textbox"), {
      target: { value: "test@example.com" },
    });
    fireEvent.click(screen.getByRole("button", { name: "submit_btn" }));

    await waitFor(() => {
      expect(mockRequestDemo).toHaveBeenCalledWith("test@example.com");
    });
  });

  it("shows success state after successful submission", async () => {
    render(<DemoRequestModal />);
    openDialog();
    await waitFor(() => screen.getByRole("textbox"));

    fireEvent.change(screen.getByRole("textbox"), {
      target: { value: "test@example.com" },
    });
    fireEvent.click(screen.getByRole("button", { name: "submit_btn" }));

    await waitFor(() => {
      expect(screen.getByText("success_title")).toBeTruthy();
    });
  });

  it("shows rate_limited error on 429", async () => {
    mockRequestDemo.mockRejectedValue({
      response: { status: 429, data: { error: "rate_limited" } },
    });

    render(<DemoRequestModal />);
    openDialog();
    await waitFor(() => screen.getByRole("textbox"));

    fireEvent.change(screen.getByRole("textbox"), {
      target: { value: "test@example.com" },
    });
    fireEvent.click(screen.getByRole("button", { name: "submit_btn" }));

    await waitFor(() => {
      expect(screen.getByText("error_rate_limited")).toBeTruthy();
    });
  });

  it("shows error_pending on 409 verification_pending", async () => {
    mockRequestDemo.mockRejectedValue({
      response: { status: 409, data: { error: "verification_pending" } },
    });

    render(<DemoRequestModal />);
    openDialog();
    await waitFor(() => screen.getByRole("textbox"));

    fireEvent.change(screen.getByRole("textbox"), {
      target: { value: "test@example.com" },
    });
    fireEvent.click(screen.getByRole("button", { name: "submit_btn" }));

    await waitFor(() => {
      expect(screen.getByText("error_pending")).toBeTruthy();
    });
  });

  it("shows error_already_active on 409 demo_already_active", async () => {
    mockRequestDemo.mockRejectedValue({
      response: { status: 409, data: { error: "demo_already_active" } },
    });

    render(<DemoRequestModal />);
    openDialog();
    await waitFor(() => screen.getByRole("textbox"));

    fireEvent.change(screen.getByRole("textbox"), {
      target: { value: "test@example.com" },
    });
    fireEvent.click(screen.getByRole("button", { name: "submit_btn" }));

    await waitFor(() => {
      expect(screen.getByText("error_already_active")).toBeTruthy();
    });
  });

  it("shows generic error on unknown failure", async () => {
    mockRequestDemo.mockRejectedValue(new Error("network error"));

    render(<DemoRequestModal />);
    openDialog();
    await waitFor(() => screen.getByRole("textbox"));

    fireEvent.change(screen.getByRole("textbox"), {
      target: { value: "test@example.com" },
    });
    fireEvent.click(screen.getByRole("button", { name: "submit_btn" }));

    await waitFor(() => {
      expect(screen.getByText("error_generic")).toBeTruthy();
    });
  });

  it("renders the demo sign-in link inside the form", async () => {
    render(<DemoRequestModal />);
    openDialog();
    await waitFor(() => screen.getByRole("link", { name: "sign_in_demo" }));
    expect(screen.getByRole("link", { name: "sign_in_demo" })).toHaveAttribute(
      "href",
      "/demo/login",
    );
  });

  it("closes and resets form when success close button is clicked", async () => {
    render(<DemoRequestModal />);
    openDialog();
    await waitFor(() => screen.getByRole("textbox"));

    fireEvent.change(screen.getByRole("textbox"), {
      target: { value: "reset@example.com" },
    });
    fireEvent.click(screen.getByRole("button", { name: "submit_btn" }));

    await waitFor(() => screen.getByRole("button", { name: "success_close" }));

    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "success_close" }));
    });

    // Dialog should be closed — trigger button should still exist
    await waitFor(() => {
      expect(screen.queryByText("success_title")).toBeNull();
    });
  });
});
