import { useTranslations } from "next-intl";
import { Card, CardContent } from "@/components/ui/card";
import { Flame } from "lucide-react";

interface StreakCardProps {
  streakDays: number;
  sessionDates: string[] | undefined;
}

export function StreakCard({ streakDays, sessionDates }: StreakCardProps) {
  const t = useTranslations("dashboard_screen");

  // Show last 7 dates as dots
  const today = new Date();
  const last7 = Array.from({ length: 7 }, (_, i) => {
    const d = new Date(today);
    d.setDate(today.getDate() - (6 - i));
    return d.toISOString().slice(0, 10);
  });

  return (
    <Card className="border shadow-sm">
      <CardContent className="p-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-orange-50">
            <Flame className="h-5 w-5 text-orange-500" />
          </div>
          <div>
            <p className="text-2xl font-bold text-gray-900">{streakDays}</p>
            <p className="text-xs text-gray-500">
              {streakDays > 0 ? t("streak_label", { count: streakDays }) : t("no_streak")}
            </p>
          </div>
        </div>
        {/* 7-day activity dots */}
        <div className="flex gap-1">
          {last7.map((date) => (
            <div
              key={date}
              title={date}
              className={`h-3 w-3 rounded-full ${
                sessionDates?.includes(date) ? "bg-orange-400" : "bg-gray-100"
              }`}
            />
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
