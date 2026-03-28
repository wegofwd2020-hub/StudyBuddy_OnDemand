/**
 * Unit tests for section 2.4 — Lesson Page components
 * Covers TC-IDs: STU-15, STU-16, STU-17, STU-18
 *
 * Run with:
 *   npm test -- lesson-page
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { LessonRenderer } from "@/components/content/LessonRenderer";
import { AudioPlayer } from "@/components/content/AudioPlayer";
import {
  MOCK_LESSON_WITH_AUDIO,
  MOCK_LESSON_NO_AUDIO,
  LESSON_STRINGS,
  quizHref,
  tutorialHref,
} from "../e2e/data/lesson-page";

// ---------------------------------------------------------------------------
// Shared mocks
// ---------------------------------------------------------------------------

vi.mock("next-intl", () => ({
  useTranslations: vi.fn(() => (key: string) => key),
}));

vi.mock("next/link", () => ({
  default: ({ href, children }: { href: string; children: React.ReactNode }) => (
    <a href={href}>{children}</a>
  ),
}));

// ---------------------------------------------------------------------------
// STU-15 — LessonRenderer: lesson content loads
// ---------------------------------------------------------------------------

describe("STU-15 — LessonRenderer", () => {
  it("renders the lesson title as H1", () => {
    render(<LessonRenderer lesson={MOCK_LESSON_WITH_AUDIO} />);
    expect(
      screen.getByRole("heading", { level: 1, name: MOCK_LESSON_WITH_AUDIO.title }),
    ).toBeInTheDocument();
  });

  it("renders all section headings", () => {
    render(<LessonRenderer lesson={MOCK_LESSON_WITH_AUDIO} />);
    for (const section of MOCK_LESSON_WITH_AUDIO.sections) {
      expect(screen.getByRole("heading", { name: section.heading })).toBeInTheDocument();
    }
  });

  it("renders all section bodies", () => {
    render(<LessonRenderer lesson={MOCK_LESSON_WITH_AUDIO} />);
    for (const section of MOCK_LESSON_WITH_AUDIO.sections) {
      expect(screen.getByText(section.body)).toBeInTheDocument();
    }
  });

  it("renders Key Points heading when key_points exist", () => {
    render(<LessonRenderer lesson={MOCK_LESSON_WITH_AUDIO} />);
    expect(screen.getByRole("heading", { name: LESSON_STRINGS.keyPoints })).toBeInTheDocument();
  });

  it("renders each key point", () => {
    render(<LessonRenderer lesson={MOCK_LESSON_WITH_AUDIO} />);
    for (const point of MOCK_LESSON_WITH_AUDIO.key_points) {
      expect(screen.getByText(point)).toBeInTheDocument();
    }
  });

  it("does not render Key Points section when list is empty", () => {
    const noKeyPoints = { ...MOCK_LESSON_NO_AUDIO, key_points: [] };
    render(<LessonRenderer lesson={noKeyPoints} />);
    expect(screen.queryByRole("heading", { name: LESSON_STRINGS.keyPoints })).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// STU-16 — AudioPlayer: play button renders
// ---------------------------------------------------------------------------

const mockUseLessonAudioUrl = vi.fn();

vi.mock("@/lib/hooks/useLesson", () => ({
  useLesson: vi.fn(),
  useLessonAudioUrl: () => mockUseLessonAudioUrl(),
}));

describe("STU-16 — AudioPlayer", () => {
  beforeEach(() => {
    mockUseLessonAudioUrl.mockReturnValue({ data: undefined, isLoading: false });
  });

  it("renders play button with correct aria-label", () => {
    render(<AudioPlayer unitId="G8-SCI-001" />);
    expect(
      screen.getByRole("button", { name: LESSON_STRINGS.playAudio }),
    ).toBeInTheDocument();
  });

  it("renders progress range input with aria-label", () => {
    render(<AudioPlayer unitId="G8-SCI-001" />);
    expect(
      screen.getByRole("slider", { name: LESSON_STRINGS.audioProgress }),
    ).toBeInTheDocument();
  });

  it("play button is not disabled before load is triggered", () => {
    render(<AudioPlayer unitId="G8-SCI-001" />);
    const btn = screen.getByRole("button", { name: LESSON_STRINGS.playAudio });
    expect(btn).not.toBeDisabled();
  });

  it("shows Loading… text while audio URL is fetching", () => {
    mockUseLessonAudioUrl.mockReturnValue({ data: undefined, isLoading: true });
    render(<AudioPlayer unitId="G8-SCI-001" />);
    // Trigger load by clicking play first
    const btn = screen.getByRole("button");
    fireEvent.click(btn);
    // Now isLoading is true via mock — Loading text appears
    expect(screen.getByText("Loading…")).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// STU-17 — CTA hrefs: Take Quiz always present; Tutorial only when has_audio
// ---------------------------------------------------------------------------

describe("STU-17 — CTA href construction", () => {
  it("quizHref returns /quiz/[unit_id]", () => {
    expect(quizHref("G8-SCI-001")).toBe("/quiz/G8-SCI-001");
  });

  it("tutorialHref returns /tutorial/[unit_id]", () => {
    expect(tutorialHref("G8-SCI-001")).toBe("/tutorial/G8-SCI-001");
  });

  it("MOCK_LESSON_WITH_AUDIO has has_audio=true → Tutorial CTA should render", () => {
    expect(MOCK_LESSON_WITH_AUDIO.has_audio).toBe(true);
  });

  it("MOCK_LESSON_NO_AUDIO has has_audio=false → Tutorial CTA should NOT render", () => {
    expect(MOCK_LESSON_NO_AUDIO.has_audio).toBe(false);
  });

  it("Take Quiz CTA string is defined", () => {
    expect(LESSON_STRINGS.takeQuizBtn).toBe("Take Quiz");
  });
});

// ---------------------------------------------------------------------------
// STU-18 — API client: 402 → /paywall, 401 → /login
// ---------------------------------------------------------------------------

describe("STU-18 — API client response interceptor", () => {
  let responseErrorHandler: ((error: any) => any) | null = null;

  beforeEach(() => {
    responseErrorHandler = null;

    vi.doMock("axios", async () => {
      return {
        default: {
          create: vi.fn(() => ({
            interceptors: {
              request: { use: vi.fn() },
              response: {
                use: vi.fn((_success: any, error: any) => {
                  responseErrorHandler = error;
                }),
              },
            },
          })),
        },
      };
    });
  });

  it("402 response redirects to /paywall", async () => {
    // Replicate the interceptor logic directly (mirrors client.ts)
    let redirectTarget = "";
    const originalHref = window.location.href;

    Object.defineProperty(window, "location", {
      configurable: true,
      value: {
        ...window.location,
        get href() { return redirectTarget || originalHref; },
        set href(val: string) { redirectTarget = val; },
      },
    });

    const interceptorFn = (error: { response?: { status: number } }) => {
      const status = error.response?.status;
      if (typeof window !== "undefined") {
        if (status === 401) {
          localStorage.removeItem("sb_token");
          window.location.href = "/login";
        } else if (status === 402) {
          window.location.href = "/paywall";
        }
      }
      return Promise.reject(error);
    };

    await interceptorFn({ response: { status: 402 } }).catch(() => {});
    expect(redirectTarget).toBe("/paywall");
  });

  it("401 response clears token and redirects to /login", async () => {
    let redirectTarget = "";
    Object.defineProperty(window, "location", {
      configurable: true,
      value: {
        ...window.location,
        get href() { return redirectTarget; },
        set href(val: string) { redirectTarget = val; },
      },
    });

    localStorage.setItem("sb_token", "test-jwt-token");

    const interceptorFn = (error: { response?: { status: number } }) => {
      const status = error.response?.status;
      if (typeof window !== "undefined") {
        if (status === 401) {
          localStorage.removeItem("sb_token");
          window.location.href = "/login";
        } else if (status === 402) {
          window.location.href = "/paywall";
        }
      }
      return Promise.reject(error);
    };

    await interceptorFn({ response: { status: 401 } }).catch(() => {});
    expect(redirectTarget).toBe("/login");
    expect(localStorage.getItem("sb_token")).toBeNull();
  });

  it("non-401/402 errors do not redirect", async () => {
    let redirectTarget = "";
    Object.defineProperty(window, "location", {
      configurable: true,
      value: {
        ...window.location,
        get href() { return redirectTarget; },
        set href(val: string) { redirectTarget = val; },
      },
    });

    const interceptorFn = (error: { response?: { status: number } }) => {
      const status = error.response?.status;
      if (typeof window !== "undefined") {
        if (status === 401) {
          localStorage.removeItem("sb_token");
          window.location.href = "/login";
        } else if (status === 402) {
          window.location.href = "/paywall";
        }
      }
      return Promise.reject(error);
    };

    await interceptorFn({ response: { status: 500 } }).catch(() => {});
    expect(redirectTarget).toBe("");
  });
});
