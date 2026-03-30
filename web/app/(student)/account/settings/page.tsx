"use client";

import { useState, useEffect } from "react";
import { useTranslations } from "next-intl";
import {
  getAccountSettings,
  saveAccountSettings,
  type AccountSettings,
} from "@/lib/api/settings";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Check, Eye } from "lucide-react";
import { DemoGate } from "@/components/demo/DemoGate";

const LOCALES = [
  { value: "en", label: "English" },
  { value: "fr", label: "Français" },
  { value: "es", label: "Español" },
] as const;

export default function SettingsPage() {
  return (
    <DemoGate
      heading="Account settings not available in demo"
      description="Demo accounts are temporary and cannot be modified. Sign up for a full account to manage your settings."
    >
      <SettingsPageInner />
    </DemoGate>
  );
}

function SettingsPageInner() {
  const t = useTranslations("settings_screen");
  const [settings, setSettings] = useState<AccountSettings | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dyslexicFont, setDyslexicFont] = useState(false);

  // Read dyslexic preference from localStorage on mount
  useEffect(() => {
    try {
      setDyslexicFont(localStorage.getItem("sb_dyslexic") === "1");
    } catch {
      // localStorage unavailable — ignore
    }
  }, []);

  function toggleDyslexicFont(enabled: boolean) {
    setDyslexicFont(enabled);
    try {
      if (enabled) {
        localStorage.setItem("sb_dyslexic", "1");
        // Cookie lets the Server Component set data-dyslexic during SSR,
        // eliminating the need for an inline <script> anti-flash workaround.
        document.cookie = "sb_dyslexic=1; path=/; max-age=31536000; SameSite=Lax";
        document.documentElement.setAttribute("data-dyslexic", "true");
      } else {
        localStorage.removeItem("sb_dyslexic");
        document.cookie = "sb_dyslexic=; path=/; max-age=0; SameSite=Lax";
        document.documentElement.removeAttribute("data-dyslexic");
      }
    } catch {
      // localStorage/cookie unavailable — ignore
    }
  }

  useEffect(() => {
    getAccountSettings()
      .then(setSettings)
      .catch(() => setError("Failed to load settings."))
      .finally(() => setIsLoading(false));
  }, []);

  async function handleSave() {
    if (!settings) return;
    setIsSaving(true);
    setSaved(false);
    setError(null);
    try {
      await saveAccountSettings(settings);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch {
      setError("Failed to save settings. Please try again.");
    } finally {
      setIsSaving(false);
    }
  }

  function setNotif(key: keyof AccountSettings["notifications"], value: boolean) {
    if (!settings) return;
    setSettings({
      ...settings,
      notifications: { ...settings.notifications, [key]: value },
    });
  }

  return (
    <div className="max-w-2xl space-y-8 p-6">
      <h1 className="text-2xl font-bold text-gray-900">{t("title")}</h1>

      {isLoading && <Skeleton className="h-64 rounded-lg" />}

      {!isLoading && settings && (
        <>
          {/* Profile */}
          <Card className="border shadow-sm">
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Profile</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-1.5">
                <Label htmlFor="display_name">Display name</Label>
                <Input
                  id="display_name"
                  value={settings.display_name}
                  onChange={(e) =>
                    setSettings({ ...settings, display_name: e.target.value })
                  }
                  placeholder="Your name"
                  className="max-w-sm"
                />
              </div>
            </CardContent>
          </Card>

          {/* Language */}
          <Card className="border shadow-sm">
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Language</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex gap-2">
                {LOCALES.map((loc) => (
                  <button
                    key={loc.value}
                    onClick={() => setSettings({ ...settings, locale: loc.value })}
                    className={`rounded-lg border px-4 py-2 text-sm font-medium transition-colors ${
                      settings.locale === loc.value
                        ? "border-blue-600 bg-blue-600 text-white"
                        : "border-gray-200 bg-white text-gray-600 hover:border-gray-400"
                    }`}
                  >
                    {loc.label}
                  </button>
                ))}
              </div>
              <p className="mt-2 text-xs text-gray-400">
                Content is served in your selected language.
              </p>
            </CardContent>
          </Card>

          {/* Notifications */}
          <Card className="border shadow-sm">
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Notifications</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {(
                [
                  {
                    key: "streak_reminders" as const,
                    label: "Streak reminders",
                    description: "Daily reminder to keep your learning streak alive.",
                  },
                  {
                    key: "weekly_summary" as const,
                    label: "Weekly summary",
                    description: "Progress digest every Monday morning.",
                  },
                  {
                    key: "quiz_nudges" as const,
                    label: "Quiz nudges",
                    description: "Reminder when a unit has an unfinished quiz.",
                  },
                ] as const
              ).map(({ key, label, description }) => (
                <label key={key} className="group flex cursor-pointer items-start gap-3">
                  <div className="relative mt-0.5">
                    <input
                      type="checkbox"
                      className="sr-only"
                      checked={settings.notifications[key]}
                      onChange={(e) => setNotif(key, e.target.checked)}
                    />
                    <div
                      className={`flex h-5 w-5 items-center justify-center rounded border-2 transition-colors ${
                        settings.notifications[key]
                          ? "border-blue-600 bg-blue-600"
                          : "border-gray-300 bg-white group-hover:border-gray-400"
                      }`}
                    >
                      {settings.notifications[key] && (
                        <Check className="h-3 w-3 text-white" strokeWidth={3} />
                      )}
                    </div>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-gray-900">{label}</p>
                    <p className="text-xs text-gray-400">{description}</p>
                  </div>
                </label>
              ))}
            </CardContent>
          </Card>

          {/* Accessibility */}
          <Card className="border shadow-sm">
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center gap-2 text-base">
                <Eye className="h-4 w-4 text-gray-500" />
                Accessibility
              </CardTitle>
            </CardHeader>
            <CardContent>
              <label className="group flex cursor-pointer items-start gap-3">
                <div className="relative mt-0.5">
                  <input
                    type="checkbox"
                    className="sr-only"
                    checked={dyslexicFont}
                    onChange={(e) => toggleDyslexicFont(e.target.checked)}
                  />
                  <div
                    className={`flex h-5 w-5 items-center justify-center rounded border-2 transition-colors ${
                      dyslexicFont
                        ? "border-blue-600 bg-blue-600"
                        : "border-gray-300 bg-white group-hover:border-gray-400"
                    }`}
                  >
                    {dyslexicFont && (
                      <Check className="h-3 w-3 text-white" strokeWidth={3} />
                    )}
                  </div>
                </div>
                <div>
                  <p className="text-sm font-medium text-gray-900">
                    Use dyslexia-friendly font
                  </p>
                  <p className="text-xs text-gray-400">
                    Switches body text to OpenDyslexic — a font designed to reduce letter
                    confusion for readers with dyslexia. Takes effect immediately.
                  </p>
                </div>
              </label>
            </CardContent>
          </Card>

          {error && <p className="text-sm text-red-600">{error}</p>}

          <div className="flex items-center gap-3">
            <Button onClick={handleSave} disabled={isSaving}>
              {isSaving ? "Saving…" : t("save_btn")}
            </Button>
            {saved && (
              <span className="flex items-center gap-1 text-sm text-green-600">
                <Check className="h-4 w-4" /> Saved
              </span>
            )}
          </div>
        </>
      )}

      {!isLoading && error && !settings && (
        <p className="text-sm text-red-600">{error}</p>
      )}
    </div>
  );
}
