import { CheckCircle2, Circle, AlertCircle, Clock, type LucideIcon } from "lucide-react";
import type { UnitStatus } from "@/lib/types/api";

export const STATUS_CONFIG: Record<
  UnitStatus,
  { icon: LucideIcon; color: string; label: string }
> = {
  completed: { icon: CheckCircle2, color: "text-green-500", label: "Completed" },
  needs_retry: { icon: AlertCircle, color: "text-amber-500", label: "Needs retry" },
  in_progress: { icon: Clock, color: "text-blue-500", label: "In progress" },
  not_started: { icon: Circle, color: "text-gray-300", label: "Not started" },
};
