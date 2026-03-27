import api from "./client";
import type { FeedbackPayload } from "@/lib/types/api";

export async function submitFeedback(payload: FeedbackPayload): Promise<void> {
  await api.post("/feedback/submit", payload);
}
