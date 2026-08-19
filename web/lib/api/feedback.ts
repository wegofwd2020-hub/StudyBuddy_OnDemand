import api from "./client";
import type { FeedbackPayload } from "@/lib/types/api";

/**
 * Submit student feedback from the lesson/tutorial/experiment thumbs widget.
 *
 * This used to POST the widget's own shape to `/feedback/submit`, a path the API
 * never served — so every submission 404'd and the feedback table stayed empty
 * for the life of the deployment (issue #600). The widget's vocabulary
 * ("up"/"down") is translated here into what the API accepts, rather than the
 * two sides quietly disagreeing.
 *
 * Note there is deliberately no `message` unless the student actually typed one:
 * the admin review list shows `message` as the student's own words, so a thumbs
 * vote must not manufacture text they never wrote.
 */
export async function submitFeedback(payload: FeedbackPayload): Promise<void> {
  await api.post("/feedback", {
    category: "content",
    unit_id: payload.unit_id,
    content_type: payload.content_type,
    helpful: payload.rating === "up",
    ...(payload.comment ? { message: payload.comment } : {}),
  });
}
