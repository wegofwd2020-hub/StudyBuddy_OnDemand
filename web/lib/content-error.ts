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
} {
  const status = error instanceof AxiosError ? error.response?.status : undefined;

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
