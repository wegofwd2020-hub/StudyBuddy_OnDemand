"use client";

/**
 * Review a unit's quiz answers (#762).
 *
 * The page a reviewer opens when a student says "question 4 is wrong". It
 * lists every quiz question of the unit AS THIS SCHOOL IS SERVED IT — the
 * school's own override where it has one, the platform's content otherwise —
 * marks which option grades, and lets a reviewer change it.
 *
 * Three rules this page is built around, each of them a fact about the data
 * rather than a styling choice:
 *
 * 1. ONE ROW PER QUESTION, NOT PER SET. `stable_question_id` hashes the stem,
 *    not the set number, so one question can be present in all three quiz sets.
 *    Both writes act on the identity and correct EVERY set (the server's
 *    rotation picks which set a student sits), so three rows would be three
 *    copies of one control — and a tick written through one would appear on all
 *    three, which reads as a bug rather than as a fact. The sets are named on
 *    the row instead. When they DISAGREE about the answer — possible before a
 *    correction, when a school has overridden only some sets — the row says so
 *    rather than picking one silently.
 *
 * 2. THE CONTROLS ARE HIDDEN WITHOUT `curriculum.review`. The backend guard is
 *    the control; this only avoids offering a button that 403s.
 *
 * 3. A CORRECTION MAY FORK THE CURRICULUM, and that is confirmed BEFORE the
 *    call, not reported after it: the school stops receiving platform
 *    regeneration for the unit and the whole grade is repointed at the copy.
 *    Afterwards the page says what actually happened by reading `created.fork`
 *    and `grade_repointed` off the response, never by inferring it.
 */

import { useMemo, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertCircle, ArrowLeft, CheckCircle2, Flag, ShieldCheck } from "lucide-react";

import {
  answerErrorCode,
  answerErrorMessage,
  correctAnswer,
  listUnitAnswers,
  validateAnswer,
  type AnswerOption,
  type AnswerReviewQuestion,
  type AnswerValidationState,
  type CorrectAnswerResult,
} from "@/lib/api/answers";
import { hasCapability, useTeacher } from "@/lib/hooks/useTeacher";
import { formatDateTime } from "@/lib/utils/date";

/** Content is English-only today; the endpoint takes the language because the
 *  identity is hashed with the one the file was actually read in. */
const LANG = "en";

interface GroupedQuestion {
  stable_question_id: string;
  question_text: string;
  /** From the LOWEST set present, the same tie-break `validate_answer` uses
   *  server-side when one identity spans sets. */
  options: AnswerOption[];
  correct_option: string | null;
  correct_option_resolves: boolean;
  sets: number[];
  /** Per (school, question), so every entry carries the same number. */
  flag_count: number;
  validated: AnswerValidationState | null;
  /** True when at least one of this question's sets is answered by the
   *  school's own copy rather than the platform's. */
  school_edited: boolean;
  /** [set number, that set's correct answer text] — only when the sets do not
   *  agree, which is a defect worth naming rather than resolving quietly. */
  disagreement: Array<{ set_number: number; text: string }> | null;
}

function optionText(options: AnswerOption[], optionId: string | null): string {
  return options.find((o) => o.option_id === optionId)?.text?.trim() ?? "";
}

/** `[1,2,3]` -> "Quiz sets 1, 2 and 3"; `[2]` -> "Quiz set 2". */
export function setsLabel(sets: number[]): string {
  if (sets.length === 1) return `Quiz set ${sets[0]}`;
  const head = sets.slice(0, -1).join(", ");
  return `Quiz sets ${head} and ${sets[sets.length - 1]}`;
}

/** Collapse the per-(question, set) listing into one row per question. */
export function groupQuestions(questions: AnswerReviewQuestion[]): GroupedQuestion[] {
  const order: string[] = [];
  const bySid = new Map<string, AnswerReviewQuestion[]>();
  for (const q of questions) {
    if (!bySid.has(q.stable_question_id)) {
      bySid.set(q.stable_question_id, []);
      order.push(q.stable_question_id);
    }
    bySid.get(q.stable_question_id)!.push(q);
  }

  const grouped = order.map((sid) => {
    const entries = [...bySid.get(sid)!].sort((a, b) => a.set_number - b.set_number);
    const lead = entries[0];
    const texts = entries.map((e) => ({
      set_number: e.set_number,
      text: optionText(e.options, e.correct_option),
    }));
    const distinct = new Set(texts.map((t) => t.text));
    return {
      stable_question_id: sid,
      question_text: lead.question_text,
      options: lead.options,
      correct_option: lead.correct_option,
      correct_option_resolves: entries.every((e) => e.correct_option_resolves !== false),
      sets: entries.map((e) => e.set_number),
      flag_count: Math.max(...entries.map((e) => e.flag_count ?? 0)),
      validated: lead.validated ?? null,
      school_edited: entries.some((e) => e.served_from === "override"),
      disagreement: distinct.size > 1 ? texts : null,
    };
  });

  // Most-flagged first, by default (design §6): the count is the only signal a
  // reviewer has about WHERE to look, which is the whole reason it is here.
  // Stable within a count, so the page does not reshuffle on every refetch.
  return grouped
    .map((q, i) => ({ q, i }))
    .sort((a, b) => b.q.flag_count - a.q.flag_count || a.i - b.i)
    .map(({ q }) => q);
}

/** What the reviewer is told AFTER a correction — built from the response, not
 *  from what the page asked for. */
export function correctionMessages(result: CorrectAnswerResult): string[] {
  const messages = [
    `Answer updated in ${setsLabel(result.sets_corrected).toLowerCase()}.`,
  ];
  if (result.created.fork) {
    messages.push(
      "Your school now keeps its own copy of this unit — platform updates will no longer reach it.",
    );
  }
  if (result.grade_repointed) {
    messages.push("This grade's curriculum now points at your copy.");
  }
  return messages;
}

export default function AnswerReviewPage() {
  const params = useParams();
  const curriculumId = params.curriculum_id as string;
  const unitId = params.unit_id as string;

  const teacher = useTeacher();
  const schoolId = teacher?.school_id ?? "";
  const canReview = hasCapability(teacher, "curriculum.review");
  const queryClient = useQueryClient();

  const [notice, setNotice] = useState<{ kind: "error"; msg: string } | null>(null);
  const [result, setResult] = useState<CorrectAnswerResult | null>(null);
  // A correction the reviewer has chosen but not yet confirmed. Only ever set
  // when the school owns no copy of this curriculum, which is exactly when the
  // backend requires `confirm_fork`.
  const [pending, setPending] = useState<{
    stableQuestionId: string;
    optionId: string;
    optionText: string;
  } | null>(null);

  const queryKey = ["unit-answers", schoolId, curriculumId, unitId, LANG];
  const { data, isLoading, error } = useQuery({
    queryKey,
    queryFn: () => listUnitAnswers(schoolId, curriculumId, unitId, LANG),
    enabled: !!schoolId && !!curriculumId && !!unitId,
    staleTime: 30_000,
  });

  const questions = useMemo(() => groupQuestions(data?.questions ?? []), [data]);

  const correctMutation = useMutation({
    mutationFn: (vars: {
      stableQuestionId: string;
      optionId: string;
      confirm: boolean;
    }) =>
      correctAnswer(
        schoolId,
        curriculumId,
        unitId,
        vars.stableQuestionId,
        vars.optionId,
        vars.confirm,
        LANG,
      ),
    onSuccess: (res) => {
      setPending(null);
      setNotice(null);
      setResult(res);
      queryClient.invalidateQueries({ queryKey });
    },
    onError: (err: unknown, vars) => {
      // The server is the control, and it may know something the listing did
      // not: re-ask rather than failing a correction the reviewer is entitled
      // to make.
      if (answerErrorCode(err) === "fork_confirmation_required") {
        const q = questions.find((x) => x.stable_question_id === vars.stableQuestionId);
        setPending({
          stableQuestionId: vars.stableQuestionId,
          optionId: vars.optionId,
          optionText: optionText(q?.options ?? [], vars.optionId),
        });
        return;
      }
      setNotice({
        kind: "error",
        msg: answerErrorMessage(
          err,
          "That answer could not be changed. Please try again.",
        ),
      });
    },
  });

  const validateMutation = useMutation({
    mutationFn: (stableQuestionId: string) =>
      validateAnswer(schoolId, curriculumId, unitId, stableQuestionId, LANG),
    onSuccess: () => {
      setNotice(null);
      queryClient.invalidateQueries({ queryKey });
    },
    onError: (err: unknown) =>
      setNotice({
        kind: "error",
        msg: answerErrorMessage(err, "That check could not be saved. Please try again."),
      }),
  });

  function chooseOption(q: GroupedQuestion, option: AnswerOption) {
    if (option.option_id === q.correct_option) return;
    setResult(null);
    if (data?.ownership === "none") {
      // Ask BEFORE the call. The confirmation is per curriculum, not per
      // question (design §3) — and after the first correction the school owns
      // a copy, so `ownership` is no longer "none" and this never fires again.
      setPending({
        stableQuestionId: q.stable_question_id,
        optionId: option.option_id,
        optionText: option.text,
      });
      return;
    }
    correctMutation.mutate({
      stableQuestionId: q.stable_question_id,
      optionId: option.option_id,
      confirm: false,
    });
  }

  const busy = correctMutation.isPending || validateMutation.isPending;

  return (
    <div className="max-w-3xl space-y-6 p-6">
      <div className="flex items-start gap-3">
        <Link
          href={`/school/content/${curriculumId}`}
          className="mt-1 rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
          aria-label="Back to unit list"
        >
          <ArrowLeft className="h-4 w-4" />
        </Link>
        <div>
          <h1 className="text-xl font-bold text-gray-900">Review quiz answers</h1>
          <p className="mt-1 text-sm text-gray-500">
            {unitId} — every quiz question in this unit, as your students are served it.
            Changing the correct answer here changes what grades them.
          </p>
        </div>
      </div>

      {data?.ownership === "none" && canReview && (
        <p className="rounded-md border border-amber-200 bg-amber-50 px-4 py-2.5 text-sm text-amber-800">
          Your school has not taken a copy of this curriculum. Correcting an answer here
          will create one — you will be asked to confirm first.
        </p>
      )}

      {notice && (
        <div className="flex items-center gap-2 rounded-md border border-red-200 bg-red-50 px-4 py-2.5 text-sm text-red-700">
          <AlertCircle className="h-4 w-4 shrink-0" />
          {notice.msg}
        </div>
      )}

      {result && (
        <div
          data-testid="correction-result"
          className="space-y-1 rounded-md border border-green-200 bg-green-50 px-4 py-2.5 text-sm text-green-800"
        >
          {correctionMessages(result).map((msg) => (
            <p key={msg} className="flex items-start gap-2">
              <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
              <span>{msg}</span>
            </p>
          ))}
        </div>
      )}

      {isLoading && (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-28 animate-pulse rounded-lg bg-gray-100" />
          ))}
        </div>
      )}

      {!isLoading && error && (
        <p className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          This unit&apos;s quiz answers could not be loaded. Please refresh and try again.
        </p>
      )}

      {!isLoading && !error && questions.length === 0 && (
        <p className="py-12 text-center text-sm text-gray-400">
          This unit has no quiz questions to review.
        </p>
      )}

      <div className="space-y-4">
        {questions.map((q) => (
          <article
            key={q.stable_question_id}
            data-testid="answer-question"
            data-question={q.stable_question_id}
            className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm"
          >
            <div className="flex flex-wrap items-center gap-2">
              <span
                data-testid="answer-sets"
                className="rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-600"
              >
                {setsLabel(q.sets)}
              </span>
              {q.school_edited && (
                <span className="rounded-full bg-indigo-50 px-2 py-0.5 text-xs font-medium text-indigo-700">
                  School-edited
                </span>
              )}
              {q.flag_count > 0 && (
                <span className="inline-flex items-center gap-1 rounded-full bg-red-50 px-2 py-0.5 text-xs font-medium text-red-700">
                  <Flag className="h-3 w-3" />
                  {q.flag_count} student {q.flag_count === 1 ? "flag" : "flags"}
                </span>
              )}
              <ValidationState validated={q.validated} />
            </div>

            <p className="mt-3 text-sm font-medium text-gray-900">{q.question_text}</p>

            {!q.correct_option_resolves && (
              <p className="mt-2 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
                This question has no answer that can be marked — its correct answer names
                an option the question does not have, so students are not scored on it.
                Pick the right option below to repair it.
              </p>
            )}

            {q.disagreement && (
              <p
                data-testid="sets-disagree"
                className="mt-2 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800"
              >
                The quiz sets disagree about this answer:{" "}
                {q.disagreement
                  .map((d) => `set ${d.set_number} says “${d.text}”`)
                  .join(", ")}
                . Correcting it here sets the same answer in every set.
              </p>
            )}

            <ul className="mt-3 space-y-1.5">
              {q.options.map((opt) => {
                const isCorrect = opt.option_id === q.correct_option;
                return (
                  <li
                    key={opt.option_id}
                    data-option={opt.option_id}
                    className={`flex items-center gap-2 rounded-md border px-3 py-2 text-sm ${
                      isCorrect
                        ? "border-green-200 bg-green-50"
                        : "border-gray-100 bg-gray-50"
                    }`}
                  >
                    {canReview && (
                      <input
                        type="radio"
                        name={`correct-${q.stable_question_id}`}
                        aria-label={opt.text}
                        value={opt.option_id}
                        checked={isCorrect}
                        disabled={busy}
                        onChange={() => chooseOption(q, opt)}
                        className="h-4 w-4 text-indigo-600 focus:ring-indigo-500"
                      />
                    )}
                    <span className="w-4 text-xs font-bold text-gray-500">
                      {opt.option_id}
                    </span>
                    <span className="flex-1 text-gray-800">{opt.text}</span>
                    {isCorrect && (
                      <span className="rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-800">
                        Correct answer
                      </span>
                    )}
                  </li>
                );
              })}
            </ul>

            {canReview && (
              <div className="mt-3 flex items-center gap-3">
                <button
                  type="button"
                  onClick={() => validateMutation.mutate(q.stable_question_id)}
                  disabled={busy}
                  className="inline-flex items-center gap-1.5 rounded-md bg-white px-3 py-1.5 text-sm font-medium text-gray-700 shadow-sm ring-1 ring-gray-200 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  <ShieldCheck className="h-4 w-4" />
                  Mark as checked
                </button>
                <Link
                  href={`/school/content/${curriculumId}/units/${unitId}/edit`}
                  className="text-xs font-medium text-indigo-600 hover:underline"
                >
                  Edit the question text
                </Link>
              </div>
            )}
          </article>
        ))}
      </div>

      {pending && (
        <ForkConfirmation
          optionText={pending.optionText}
          busy={correctMutation.isPending}
          onCancel={() => setPending(null)}
          onConfirm={() =>
            correctMutation.mutate({
              stableQuestionId: pending.stableQuestionId,
              optionId: pending.optionId,
              confirm: true,
            })
          }
        />
      )}
    </div>
  );
}

function ValidationState({ validated }: { validated: AnswerValidationState | null }) {
  if (!validated) return null;
  const who = validated.by_name ?? "a reviewer";
  const when = formatDateTime(validated.at);
  if (validated.stale) {
    // The answer has changed since somebody vouched for it, so the tick no
    // longer vouches for anything — say that, rather than show a green tick
    // against an answer nobody checked.
    return (
      <span
        data-testid="validation-state"
        className="rounded-full bg-amber-50 px-2 py-0.5 text-xs font-medium text-amber-800"
      >
        Needs re-checking — the answer changed since {who} checked it on {when}
      </span>
    );
  }
  return (
    <span
      data-testid="validation-state"
      className="rounded-full bg-green-50 px-2 py-0.5 text-xs font-medium text-green-800"
    >
      Checked by {who} on {when}
    </span>
  );
}

function ForkConfirmation({
  optionText: chosen,
  busy,
  onCancel,
  onConfirm,
}: {
  optionText: string;
  busy: boolean;
  onCancel: () => void;
  onConfirm: () => void;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="fork-confirm-title"
        className="w-full max-w-lg rounded-lg bg-white p-6 shadow-xl"
      >
        <h2 id="fork-confirm-title" className="text-base font-semibold text-gray-900">
          Correct this answer for your school?
        </h2>
        <div className="mt-3 space-y-2 text-sm text-gray-600">
          <p>
            Setting “{chosen}” as the correct answer means your school keeps its own copy
            of this unit.
          </p>
          <p>Platform updates to this unit will no longer reach it.</p>
          <p>This grade&apos;s curriculum will point at your copy.</p>
          <p className="text-gray-500">
            You will only be asked this once for this curriculum.
          </p>
        </div>
        <div className="mt-5 flex items-center justify-end gap-3">
          <button
            type="button"
            onClick={onCancel}
            disabled={busy}
            className="rounded-md px-3 py-1.5 text-sm font-medium text-gray-600 hover:bg-gray-100 disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={busy}
            className="rounded-md bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white shadow-sm hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {busy ? "Correcting…" : "Keep our own copy and correct it"}
          </button>
        </div>
      </div>
    </div>
  );
}
