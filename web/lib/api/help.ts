/**
 * web/lib/api/help.ts
 *
 * Client for POST /api/v1/help/ask.
 *
 * The endpoint is public — no JWT is required.  We use plain fetch rather than
 * the authenticated schoolApi Axios instance so the widget can render on any
 * portal page regardless of session state.
 *
 * Deliver-3: account_state carries context signals collected by HelpWidget
 * (first_login, teacher_count, etc.) that the backend threads into the prompt.
 */

export const HELP_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

/** Recognised account_state signal keys (mirrors backend schema). */
export interface AccountState {
  first_login?: boolean;
  teacher_count?: number;
  student_count?: number;
  classroom_count?: number;
  curriculum_assigned?: boolean;
}

export interface HelpAskRequest {
  question: string;
  page?: string;
  role: "school_admin" | "teacher" | "student";
  account_state?: AccountState;
}

export interface HelpAskResponse {
  title: string;
  steps: string[];
  result: string;
  related: string[];
  sources: string[];
  /** UUID of the logged interaction. Pass to submitFeedback() to rate the answer. */
  interaction_id: string | null;
}

export async function askHelp(body: HelpAskRequest): Promise<HelpAskResponse> {
  const res = await fetch(`${HELP_BASE_URL}/help/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(
      err?.detail ?? err?.error ?? `Help request failed (${res.status})`,
    );
  }

  return res.json() as Promise<HelpAskResponse>;
}

/**
 * Submit thumbs-up (helpful=true) or thumbs-down (helpful=false) feedback on
 * a help response. Fire-and-forget — failures are silently swallowed so a
 * network error never breaks the widget.
 */
export async function submitFeedback(
  interactionId: string,
  helpful: boolean,
): Promise<void> {
  try {
    await fetch(`${HELP_BASE_URL}/help/feedback`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ interaction_id: interactionId, helpful }),
    });
  } catch {
    // best-effort — feedback failure must never surface as a UI error
  }
}
