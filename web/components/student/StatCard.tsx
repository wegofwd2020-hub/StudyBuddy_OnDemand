import { Card, CardContent } from "@/components/ui/card";
import type { LucideIcon } from "lucide-react";

interface StatCardProps {
  label: string;
  value: string | number;
  icon: LucideIcon;
  color?: "blue" | "green" | "purple" | "orange";
  /**
   * What the number actually counts, when the label alone is ambiguous.
   *
   * "Pass rate" means one thing on this screen (every attempt) and another on
   * the teacher's report card for the same student (first attempt only). Both
   * are right; neither said which, so the two screens showed 65% and 43% for one
   * child on one afternoon and read as a data bug. A parenthetical would crowd a
   * card this small, so the qualifier gets its own line.
   */
  hint?: string;
}

const COLOR_MAP = {
  blue: { bg: "bg-blue-50", text: "text-blue-600" },
  green: { bg: "bg-green-50", text: "text-green-600" },
  purple: { bg: "bg-purple-50", text: "text-purple-600" },
  orange: { bg: "bg-orange-50", text: "text-orange-600" },
};

export function StatCard({
  label,
  value,
  icon: Icon,
  color = "blue",
  hint,
}: StatCardProps) {
  const { bg, text } = COLOR_MAP[color];

  return (
    <Card className="border shadow-sm">
      <CardContent className="flex items-center gap-4 p-4">
        <div className={`flex h-10 w-10 items-center justify-center rounded-lg ${bg}`}>
          <Icon className={`h-5 w-5 ${text}`} />
        </div>
        <div>
          <p className="text-2xl font-bold text-gray-900">{value}</p>
          <p className="text-xs text-gray-500">{label}</p>
          {hint && <p className="mt-0.5 text-[11px] text-gray-400">{hint}</p>}
        </div>
      </CardContent>
    </Card>
  );
}
