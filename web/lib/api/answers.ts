/**
 * Quiz answer review (#762) — the school-portal client.
 *
 * HAND-WRITTEN, like every other module in `lib/api/`, and deliberately so:
 * these types do NOT derive from `types.gen.ts` (pitfall #40). Regenerating the
 * contract updates the generated file and leaves this one untouched, so a field
 * added to the API has to be added HERE as well or the page will never see it.
 * That is the other half of the 2026-08-31 red deploy. Every shape below is
 * transcribed from `backend/src/school/schemas.py`; keep them in step.
 */
import type { AxiosError } from "axios";

import schoolApi from "./school-client";

export interface AnswerOption {
  option_id: string;
  text: string;
}

/** Who checked this question FOR THIS SCHOOL, and whether the check still
 *  stands. `stale` is true once the current correct option's text no longer
 *  matches the one that was vouched for — the tick then reads as "needs
 *  re-checking" rather than silently vouching for an answer nobody saw. */
export interface AnswerValidationState {
  /** The reviewer's `teachers` id — an identifier, never shown to a reader. */
  by: string;
  /** The reviewer's name, resolved server-side. Null only if the join missed. */
  by_name?: string | null;
  at: string;
  stale: boolean;
}

export interface AnswerReviewQuestion {
  stable_question_id: string;
  set_number: number;
  /** `q1…qN` — a SLOT within one set, not an identity. Two sets' `q1` are
   *  different questions; `stable_question_id` is the identity. */
  question_id: string;
  question_text: string;
  options: AnswerOption[];
  correct_option: string | null;
  /** False when `correct_option` names no option this question actually has.
   *  The grader DROPS such a question, so nobody is scored on it — a live
   *  content defect, and one of the things a reviewer opens this page to find. */
  correct_option_resolves?: boolean;
  /** Which body answered THIS set. One response can mix the two: a school
   *  typically overrides one set and leaves the others on the platform's. */
  served_from: "override" | "store";
  validated?: AnswerValidationState | null;
  flag_count?: number;
}

export interface AnswerReviewList {
  /** What this school owns for this unit: `override` (an active school
   *  override answers at least one set), `fork` (owns a fork but has not
   *  overridden this unit's quiz), `none` (has not adopted at all — the demo's
   *  case for every curriculum a class actually uses). */
  ownership: "none" | "fork" | "override";
  /** The OOB curriculum the store content and every `stable_question_id` live
   *  under. */
  source_curriculum_id: string;
  /** The school's fork, when it has one. */
  owned_curriculum_id?: string | null;
  questions: AnswerReviewQuestion[];
}

export interface AnswerValidationResult {
  validated_by: string;
  validated_at: string;
  /** The snapshot the staleness comparison will be made against. */
  correct_text: string;
}

/** Which of the three ownership steps the correction had to perform. READ,
 *  never inferred: "did this fork the curriculum" is not derivable from the
 *  rest of the response, and the message the reviewer sees depends on it. */
export interface CorrectionCreated {
  adoption: boolean;
  fork: boolean;
  /** `import` is a reserved word in TS only as a statement; as a property name
   *  it is fine — and it is what the API sends (pydantic alias). */
  import: boolean;
}

export interface CorrectAnswerResult {
  ownership_before: "none" | "fork" | "override";
  created: CorrectionCreated;
  override_id: string;
  override_ids: string[];
  owned_curriculum_id: string;
  /** True when creating the fork also repointed this grade's curriculum
   *  assignment — a side effect on every student of the grade, not only on
   *  this unit. */
  grade_repointed: boolean;
  /** Every quiz set the question appeared in: one `stable_question_id` spans
   *  sets and a correction fixes all of them, because the set a student sits
   *  is chosen by the server's rotation. */
  sets_corrected: number[];
  old_correct_text: string;
  new_correct_text: string;
  validated_at: string;
}

function base(schoolId: string, curriculumId: string, unitId: string): string {
  return `/schools/${schoolId}/content/${curriculumId}/units/${unitId}/answers`;
}

export async function listUnitAnswers(
  schoolId: string,
  curriculumId: string,
  unitId: string,
  lang = "en",
): Promise<AnswerReviewList> {
  const res = await schoolApi.get<AnswerReviewList>(
    base(schoolId, curriculumId, unitId),
    {
      params: { lang },
    },
  );
  return res.data;
}

export async function validateAnswer(
  schoolId: string,
  curriculumId: string,
  unitId: string,
  stableQuestionId: string,
  lang = "en",
): Promise<AnswerValidationResult> {
  const res = await schoolApi.post<AnswerValidationResult>(
    `${base(schoolId, curriculumId, unitId)}/${stableQuestionId}/validate`,
    {},
    { params: { lang } },
  );
  return res.data;
}

export async function correctAnswer(
  schoolId: string,
  curriculumId: string,
  unitId: string,
  stableQuestionId: string,
  correctOption: string,
  confirmFork: boolean,
  lang = "en",
): Promise<CorrectAnswerResult> {
  const res = await schoolApi.post<CorrectAnswerResult>(
    `${base(schoolId, curriculumId, unitId)}/${stableQuestionId}/correct`,
    { correct_option: correctOption, confirm_fork: confirmFork },
    { params: { lang } },
  );
  return res.data;
}

interface ApiErrorDetail {
  error?: string;
  detail?: string;
}

/** The machine-readable `error` code the API puts in `detail`, when there is
 *  one. The client branches on `fork_confirmation_required` rather than on
 *  prose, which is exactly why the endpoint sends a code at all. */
export function answerErrorCode(err: unknown): string | null {
  const data = (err as AxiosError<{ detail?: ApiErrorDetail | string }>)?.response?.data;
  const detail = data?.detail;
  if (detail && typeof detail === "object" && typeof detail.error === "string") {
    return detail.error;
  }
  return null;
}

/** The API's own sentence, when it sent one. Falls back to a plain message —
 *  never a status code or a stack trace in front of a teacher. */
export function answerErrorMessage(err: unknown, fallback: string): string {
  const data = (err as AxiosError<{ detail?: ApiErrorDetail | string }>)?.response?.data;
  const detail = data?.detail;
  if (typeof detail === "string") return detail;
  if (detail && typeof detail === "object" && typeof detail.detail === "string") {
    return detail.detail;
  }
  return fallback;
}
