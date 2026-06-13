"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import Link from "next/link";
import { useTeacher } from "@/lib/hooks/useTeacher";
import { updateAlertSettings, type AlertSettings } from "@/lib/api/reports";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { ArrowLeft, Check } from "lucide-react";

// The backend has no GET for current settings yet, so the form starts from the
// same defaults the server applies (src/reports/service.py::save_alert_settings).
const DEFAULTS: AlertSettings = {
  pass_rate_threshold: 50,
  feedback_count_threshold: 3,
  inactive_days_threshold: 14,
  score_drop_threshold: 10,
  new_feedback_immediate: true,
};

export default function AlertSettingsPage() {
  const teacher = useTeacher();
  const schoolId = teacher?.school_id ?? "";
  const [settings, setSettings] = useState<AlertSettings>(DEFAULTS);

  const { mutate, isPending, isSuccess, isError } = useMutation({
    mutationFn: () => updateAlertSettings(schoolId, settings),
  });

  function num(key: keyof AlertSettings, value: string) {
    setSettings((s) => ({ ...s, [key]: Number(value) }));
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
                setSettings((s) => ({
                  ...s,
                  new_feedback_immediate: e.target.checked,
                }))
              }
            />
            Notify immediately on new feedback
          </label>
        </CardContent>
      </Card>
      {isError && (
        <p className="text-sm text-red-600">Could not save settings. Please try again.</p>
      )}
      <Button
        onClick={() => mutate()}
        disabled={isPending || !schoolId}
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
    </div>
  );
}
