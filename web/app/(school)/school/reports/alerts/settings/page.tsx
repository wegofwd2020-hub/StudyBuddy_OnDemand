"use client";

import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useTeacher } from "@/lib/hooks/useTeacher";
import {
  getAlertSettings,
  updateAlertSettings,
  type AlertSettings,
} from "@/lib/api/reports";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { ArrowLeft, Check } from "lucide-react";

export default function AlertSettingsPage() {
  const teacher = useTeacher();
  const schoolId = teacher?.school_id ?? "";
  const queryClient = useQueryClient();

  // The server owns the defaults now (#526): load the saved thresholds and seed
  // the form from them, so a saved value is shown on return instead of a
  // hardcoded placeholder that made saves look lost.
  const { data: loaded, isLoading } = useQuery({
    queryKey: ["alert-settings", schoolId],
    queryFn: () => getAlertSettings(schoolId),
    enabled: !!schoolId,
    staleTime: 60_000,
  });

  const [settings, setSettings] = useState<AlertSettings | null>(null);
  useEffect(() => {
    if (loaded) setSettings(loaded);
  }, [loaded]);

  const { mutate, isPending, isSuccess, isError } = useMutation({
    mutationFn: () => updateAlertSettings(schoolId, settings as AlertSettings),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["alert-settings", schoolId] });
    },
  });

  function num(key: keyof AlertSettings, value: string) {
    setSettings((s) => (s ? { ...s, [key]: Number(value) } : s));
  }

  return (
    <div className="max-w-2xl space-y-6 p-6">
      <Link
        href="/school/alerts"
        className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to alerts
      </Link>
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Alert thresholds</h1>
        <p className="mt-1 text-sm text-gray-500">
          Alerts fire when these limits are crossed. Changes apply to future alerts.
        </p>
      </div>
      {(isLoading || !settings) && <Skeleton className="h-72 rounded-lg" />}
      {settings && (
        <>
          <Card className="border shadow-sm">
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Thresholds</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-1.5">
                <Label htmlFor="pass_rate">Low pass-rate alert below (%)</Label>
                <Input
                  id="pass_rate"
                  type="number"
                  min={0}
                  max={100}
                  value={settings.pass_rate_threshold}
                  onChange={(e) => num("pass_rate_threshold", e.target.value)}
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="inactive_days">Inactive-student alert after (days)</Label>
                <Input
                  id="inactive_days"
                  type="number"
                  min={1}
                  value={settings.inactive_days_threshold}
                  onChange={(e) => num("inactive_days_threshold", e.target.value)}
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="feedback_count">Feedback-spike alert at (count)</Label>
                <Input
                  id="feedback_count"
                  type="number"
                  min={1}
                  value={settings.feedback_count_threshold}
                  onChange={(e) => num("feedback_count_threshold", e.target.value)}
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="score_drop">Score-drop alert at (% drop)</Label>
                <Input
                  id="score_drop"
                  type="number"
                  min={0}
                  max={100}
                  value={settings.score_drop_threshold}
                  onChange={(e) => num("score_drop_threshold", e.target.value)}
                />
              </div>
              <label className="flex items-center gap-2 pt-1 text-sm text-gray-700">
                <input
                  type="checkbox"
                  className="h-4 w-4 rounded border-gray-300"
                  checked={settings.new_feedback_immediate}
                  onChange={(e) =>
                    setSettings((s) =>
                      s ? { ...s, new_feedback_immediate: e.target.checked } : s,
                    )
                  }
                />
                Notify immediately on new feedback
              </label>
            </CardContent>
          </Card>
          {isError && (
            <p className="text-sm text-red-600">
              Could not save settings. Please try again.
            </p>
          )}
          <Button
            onClick={() => mutate()}
            disabled={isPending || !schoolId || !settings}
            className="gap-2"
          >
            {isPending ? (
              "Saving…"
            ) : isSuccess ? (
              <>
                <Check className="h-4 w-4" />
                Saved
              </>
            ) : (
              "Save thresholds"
            )}
          </Button>
        </>
      )}
    </div>
  );
}
