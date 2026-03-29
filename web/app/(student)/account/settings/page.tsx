"use client";

import { useState, useEffect } from "react";
import { useTranslations } from "next-intl";
import { getAccountSettings, saveAccountSettings, type AccountSettings } from "@/lib/api/settings";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Check, Eye } from "lucide-react";

const LOCALES = [
  { value: "en", label: "English" },
  { value: "fr", label: "Français" },
  { value: "es", label: "Español" },
] as const;

export default function SettingsPage() {
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
        document.documentElement.setAttribute("data-dyslexic", "true");
      } else {
        localStorage.removeItem("sb_dyslexic");
        document.documentElement.removeAttribute("data-dyslexic");
      }
    } catch {
      // localStorage unavailable — ignore
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
    <div className="p-6 max-w-2xl space-y-8">
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
                    className={`px-4 py-2 rounded-lg border text-sm font-medium transition-colors ${
                      settings.locale === loc.value
                        ? "bg-blue-600 text-white border-blue-600"
                        : "bg-white text-gray-600 border-gray-200 hover:border-gray-400"
                    }`}
                  >
                    {loc.label}
                  </button>
                ))}
              </div>
              <p className="text-xs text-gray-400 mt-2">
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
                <label
                  key={key}
                  className="flex items-start gap-3 cursor-pointer group"
                >
                  <div className="relative mt-0.5">
                    <input
                      type="checkbox"
                      className="sr-only"
                      checked={settings.notifications[key]}
                      onChange={(e) => setNotif(key, e.target.checked)}
                    />
                    <div
                      className={`w-5 h-5 rounded border-2 flex items-center justify-center transition-colors ${
                        settings.notifications[key]
                          ? "bg-blue-600 border-blue-600"
                          : "bg-white border-gray-300 group-hover:border-gray-400"
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
              <CardTitle className="text-base flex items-center gap-2">
                <Eye className="h-4 w-4 text-gray-500" />
                Accessibility
              </CardTitle>
            </CardHeader>
            <CardContent>
              <label className="flex items-start gap-3 cursor-pointer group">
                <div className="relative mt-0.5">
                  <input
                    type="checkbox"
                    className="sr-only"
                    checked={dyslexicFont}
                    onChange={(e) => toggleDyslexicFont(e.target.checked)}
                  />
                  <div
                    className={`w-5 h-5 rounded border-2 flex items-center justify-center transition-colors ${
                      dyslexicFont
                        ? "bg-blue-600 border-blue-600"
                        : "bg-white border-gray-300 group-hover:border-gray-400"
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
                    Switches body text to OpenDyslexic — a font designed to reduce
                    letter confusion for readers with dyslexia. Takes effect immediately.
                  </p>
                </div>
              </label>
            </CardContent>
          </Card>

          {error && (
            <p className="text-sm text-red-600">{error}</p>
          )}

          <div className="flex items-center gap-3">
            <Button onClick={handleSave} disabled={isSaving}>
              {isSaving ? "Saving…" : t("save_btn")}
            </Button>
            {saved && (
              <span className="text-sm text-green-600 flex items-center gap-1">
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
