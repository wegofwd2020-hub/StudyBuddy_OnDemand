"use client";

import { useState } from "react";
import { ThumbsUp, ThumbsDown } from "lucide-react";
import { submitFeedback } from "@/lib/api/feedback";
import type { FeedbackPayload } from "@/lib/types/api";
import { cn } from "@/lib/utils";

interface FeedbackWidgetProps {
  unitId: string;
  contentType: FeedbackPayload["content_type"];
}

type State = "idle" | "submitting" | "done" | "error";

export function FeedbackWidget({ unitId, contentType }: FeedbackWidgetProps) {
  const [state, setState] = useState<State>("idle");
  const [selected, setSelected] = useState<"up" | "down" | null>(null);

  async function handleClick(rating: "up" | "down") {
    if (state !== "idle") return;
    setSelected(rating);
    setState("submitting");
    try {
      await submitFeedback({ unit_id: unitId, content_type: contentType, rating });
      setState("done");
    } catch {
      setState("error");
    }
  }

  if (state === "done") {
    return (
      <div className="flex items-center gap-2 text-sm text-gray-400">
        <span>Thanks for your feedback!</span>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-2">
      <span className="text-xs text-gray-400">Was this helpful?</span>
      <button
        onClick={() => handleClick("up")}
        disabled={state !== "idle"}
        aria-label="Thumbs up"
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
        aria-label="Thumbs down"
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
