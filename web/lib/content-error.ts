import { AxiosError } from "axios";

/**
 * Map a content-fetch error to student-facing, non-technical copy (Content
 * Rule #5 — never expose status codes or internal identifiers to students).
 *
 * Distinguishes "not generated yet" (HTTP 404 from the content endpoints —
 * unit not in the curriculum, subject unpublished, or the file is missing)
 * from a genuine transient failure, so a student who opens an ungenerated
 * unit sees "not available yet" instead of a misleading "try again" (#468).
 */
export function contentErrorMessage(error: unknown): {
  message: string;
  unavailable: boolean;
  /** The student has to do something first, and the caller should offer it. */
  lessonRequired?: boolean;
} {
  const status = error instanceof AxiosError ? error.response?.status : undefined;

  // The API's exception handler FLATTENS an HTTPException's `detail` dict onto
  // the response body, so the live shape is `{error, detail, correlation_id}`,
  // not `{detail: {error, ...}}`. Both are read because the nested form is what
  // the raising code literally writes, and one handler change would otherwise
  // silently turn the gate screen back into a generic error.
  const data = error instanceof AxiosError ? error.response?.data : undefined;
  const body = data as
    | { error?: string; detail?: { error?: string } | string }
    | undefined;
  const code =
    body?.error ?? (typeof body?.detail === "object" ? body.detail?.error : undefined);

  // The quiz is gated on reading the lesson first (product decision
  // 2026-09-01). This is not a failure — the student simply arrived in the
  // wrong order — so it must not be worded, or coloured, like one.
  if (status === 403 && code === "lesson_required") {
    return {
      message: "Read the lesson first, then come back for the quiz.",
      unavailable: false,
      lessonRequired: true,
    };
  }

  // 404 = the content does not exist (yet). Retrying will never help, so don't
  // imply it might. 402 (subscription required) is handled by the paywall flow.
  if (status === 404) {
    return {
      message: "This isn't available yet. Please check back soon.",
      unavailable: true,
    };
  }

  return {
    message: "Something went wrong loading this. Please try again.",
    unavailable: false,
  };
}
