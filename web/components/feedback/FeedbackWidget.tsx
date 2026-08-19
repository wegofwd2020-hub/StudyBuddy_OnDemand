"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { ThumbsUp, ThumbsDown } from "lucide-react";
import { submitFeedback } from "@/lib/api/feedback";
import type { FeedbackPayload } from "@/lib/types/api";
import { cn } from "@/lib/utils";

interface FeedbackWidgetProps {
  unitId: string;
  contentType: FeedbackPayload["content_type"];
}

/** The API rejects a message longer than this, so stop the student at the limit. */
const MAX_REASON = 500;
/** Only start counting down once it is close enough to matter. */
const COUNTDOWN_FROM = 100;

type State = "idle" | "asking_why" | "submitting" | "done" | "error";

/**
 * Thumbs up/down on a lesson, tutorial or experiment.
 *
 * A thumbs-down tells a reviewer that something is wrong with a unit but not
 * what, which is the part a teacher can act on — so it opens an optional
 * comment box before submitting (#612). The reason stays optional on purpose:
 * requiring it would suppress the signal, and a bare verdict is still useful.
 *
 * A thumbs-up stays a single click. Asking a happy student to explain adds
 * friction for very little.
 */
export function FeedbackWidget({ unitId, contentType }: FeedbackWidgetProps) {
  const t = useTranslations("feedback");
  const [state, setState] = useState<State>("idle");
  const [selected, setSelected] = useState<"up" | "down" | null>(null);
  const [reason, setReason] = useState("");

  async function send(rating: "up" | "down", comment?: string) {
    setState("submitting");
    const trimmed = comment?.trim();
    try {
      await submitFeedback({
        unit_id: unitId,
        content_type: contentType,
        rating,
        // Omit rather than send an empty string — a blank message is not a
        // comment, and the reviewer view renders `message` as the student's
        // own words.
        ...(trimmed ? { comment: trimmed } : {}),
      });
      setState("done");
    } catch {
      setState("error");
    }
  }

  function handleClick(rating: "up" | "down") {
    if (state !== "idle") return;
    setSelected(rating);
    if (rating === "down") {
      setState("asking_why");
      return;
    }
    void send(rating);
  }

  if (state === "done") {
    return (
      <div className="flex items-center gap-2 text-sm text-gray-400">
        <span>{t("thanks")}</span>
      </div>
    );
  }

  if (state === "error") {
    return (
      <div className="flex items-center gap-2 text-sm text-red-600" role="status">
        <span>{t("error")}</span>
      </div>
    );
  }

  if (state === "asking_why" || (state === "submitting" && selected === "down")) {
    const remaining = MAX_REASON - reason.length;
    return (
      <div className="flex flex-col gap-2">
        <label htmlFor="feedback-reason" className="text-xs text-gray-500">
          {t("reason_prompt")}
        </label>
        <textarea
          id="feedback-reason"
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          maxLength={MAX_REASON}
          rows={3}
          placeholder={t("reason_placeholder")}
          disabled={state === "submitting"}
          className="w-full rounded-lg border border-gray-200 p-2 text-sm text-gray-700 focus:border-gray-400 focus:outline-none disabled:opacity-60"
        />
        <div className="flex items-center gap-2">
          <button
            onClick={() => void send("down", reason)}
            disabled={state === "submitting"}
            className="rounded-full bg-gray-900 px-3 py-1 text-xs font-medium text-white disabled:opacity-60"
          >
            {t("send")}
          </button>
          <button
            onClick={() => void send("down")}
            disabled={state === "submitting"}
            className="rounded-full px-3 py-1 text-xs text-gray-500 hover:text-gray-700 disabled:opacity-60"
          >
            {t("skip")}
          </button>
          {remaining <= COUNTDOWN_FROM && (
            <span className="ml-auto text-xs text-gray-400">
              {t("chars_left", { count: remaining })}
            </span>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-2">
      <span className="text-xs text-gray-400">{t("prompt")}</span>
      <button
        onClick={() => handleClick("up")}
        disabled={state !== "idle"}
        aria-label={t("thumbs_up")}
        className={cn(
          "rounded-full p-1.5 transition-colors",
          selected === "up"
            ? "bg-green-100 text-green-600"
            : "text-gray-400 hover:bg-gray-100 hover:text-gray-600",
        )}
      >
        <ThumbsUp className="h-4 w-4" />
      </button>
      <button
        onClick={() => handleClick("down")}
        disabled={state !== "idle"}
        aria-label={t("thumbs_down")}
        className={cn(
          "rounded-full p-1.5 transition-colors",
          selected === "down"
            ? "bg-red-100 text-red-600"
            : "text-gray-400 hover:bg-gray-100 hover:text-gray-600",
        )}
      >
        <ThumbsDown className="h-4 w-4" />
      </button>
    </div>
  );
}
