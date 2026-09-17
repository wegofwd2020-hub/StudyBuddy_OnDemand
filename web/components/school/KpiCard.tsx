import { Card, CardContent } from "@/components/ui/card";

/**
 * KpiCard — the school portal's single headline-number treatment.
 *
 * Extracted from the dashboard (#640 redesign) so the reports can use it too.
 * It was private to `school/dashboard/page.tsx`, which is why the Engagement
 * report grew its own hand-rolled cards that drifted from it (#770): different
 * padding, different icon treatment, no accent, no subtitle slot.
 *
 * `accent` is decoration, never the only signal — a red card must still say in
 * words what is wrong (WCAG 1.4.1: colour is not information on its own).
 */
export function KpiCard({
  title,
  value,
  subtitle,
  icon,
  accent,
}: {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: React.ReactNode;
  accent?: "green" | "blue" | "red" | "gray";
}) {
  const colors = {
    green: "text-green-600 bg-green-50",
    blue: "text-blue-600 bg-blue-50",
    red: "text-red-500 bg-red-50",
    gray: "text-gray-500 bg-gray-100",
  };
  return (
    <Card className="border shadow-sm">
      <CardContent className="flex items-start gap-4 p-5">
        <div className={`rounded-lg p-2.5 ${colors[accent ?? "blue"]}`}>{icon}</div>
        <div>
          <p className="text-xs font-medium tracking-wide text-gray-400 uppercase">
            {title}
          </p>
          <p className="mt-0.5 text-2xl font-bold text-gray-900">{value}</p>
          {subtitle && <p className="mt-0.5 text-xs text-gray-500">{subtitle}</p>}
        </div>
      </CardContent>
    </Card>
  );
}
