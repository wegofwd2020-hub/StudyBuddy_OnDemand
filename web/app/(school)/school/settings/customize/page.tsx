"use client";

import { useEffect, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useTeacher } from "@/lib/hooks/useTeacher";
import { getSchoolTheme, updateSchoolTheme } from "@/lib/api/school-admin";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "sonner";
import { Check, Loader2, ExternalLink, Palette } from "lucide-react";
import { SchoolThemeProvider, useSchoolTheme } from "@/lib/theme/SchoolThemeContext";
import { getSubjectPalette } from "@/lib/theme/getSubjectPalette";
import { DEFAULT_THEME, SUBJECT_ORDER, type SchoolTheme } from "@/lib/theme/defaults";

// ── Mini live preview ─────────────────────────────────────────────────────────

function MiniSubjectCard({ subjectKey }: { subjectKey: string }) {
  const theme = useSchoolTheme();
  const accent =
    theme.subjects[subjectKey]?.accent ??
    DEFAULT_THEME.subjects[subjectKey]?.accent ??
    "#4f46e5";
  const palette = getSubjectPalette(accent);
  const label = theme.subjects[subjectKey]?.label ?? subjectKey;

  return (
    <div
      style={{
        background: palette.bg1,
        border: `1px solid ${palette.border}`,
        borderRadius: 10,
        padding: "10px 14px",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <div
          style={{
            width: 8,
            height: 8,
            borderRadius: 999,
            background: palette.accent,
            flexShrink: 0,
          }}
        />
        <span style={{ fontSize: 13, fontWeight: 600, color: palette.ink }}>{label}</span>
      </div>
      <div style={{ marginTop: 6, display: "flex", gap: 4 }}>
        {[1, 2, 3].map((i) => (
          <div
            key={i}
            style={{ height: 6, flex: 1, borderRadius: 3, background: palette.bg2 }}
          />
        ))}
      </div>
    </div>
  );
}

function MiniLibraryPreview({ schoolName }: { schoolName: string }) {
  return (
    <div className="sticky top-6 space-y-3">
      <p className="text-xs font-semibold tracking-wide text-gray-400 uppercase">
        Live preview
      </p>
      <div className="rounded-xl border bg-white p-5 shadow-sm">
        <p className="mb-1 text-xs font-medium text-gray-400">Student library</p>
        <p className="mb-4 text-sm font-bold text-gray-900">
          {schoolName || "Your school"}
        </p>
        <div className="grid grid-cols-2 gap-2">
          {SUBJECT_ORDER.map((key) => (
            <MiniSubjectCard key={key} subjectKey={key} />
          ))}
        </div>
        <p className="mt-4 text-xs text-gray-400">
          Colors update instantly as you edit. Save to publish to students.
        </p>
      </div>
    </div>
  );
}

// ── Subject color row ─────────────────────────────────────────────────────────

function SubjectColorRow({
  subjectKey,
  accent,
  disabled,
  onChange,
}: {
  subjectKey: string;
  accent: string;
  disabled: boolean;
  onChange: (hex: string) => void;
}) {
  const [localHex, setLocalHex] = useState(accent);
  useEffect(() => setLocalHex(accent), [accent]);

  function commitHex(val: string) {
    if (/^#[0-9a-fA-F]{6}$/.test(val)) onChange(val.toLowerCase());
  }

  const valid = /^#[0-9a-fA-F]{6}$/.test(localHex);

  return (
    <div className="flex items-center gap-3">
      <span className="w-20 text-sm font-medium text-gray-700">{subjectKey}</span>
      <input
        type="color"
        value={valid ? localHex : accent}
        disabled={disabled}
        onChange={(e) => {
          setLocalHex(e.target.value);
          onChange(e.target.value);
        }}
        className="h-9 w-9 cursor-pointer rounded-lg border border-gray-200 p-0.5 disabled:cursor-not-allowed disabled:opacity-50"
        aria-label={`${subjectKey} color picker`}
      />
      <Input
        value={localHex}
        disabled={disabled}
        onChange={(e) => setLocalHex(e.target.value)}
        onBlur={(e) => commitHex(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter") commitHex(localHex);
        }}
        className="h-9 w-32 font-mono text-sm"
        placeholder="#000000"
        maxLength={7}
        aria-label={`${subjectKey} hex color`}
      />
      <div
        className="h-7 w-7 rounded-md border border-gray-200 transition-colors"
        style={{ background: valid ? localHex : accent }}
      />
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function CustomizeSchoolPage() {
  const queryClient = useQueryClient();
  const teacher = useTeacher();
  const schoolId = teacher?.school_id ?? "";
  const isAdmin = teacher?.role === "school_admin";

  const { data: fetchedTheme, isLoading } = useQuery({
    queryKey: ["school-theme", schoolId],
    queryFn: () => getSchoolTheme(schoolId),
    enabled: !!schoolId,
    staleTime: 300_000,
  });

  const [workingTheme, setWorkingTheme] = useState<SchoolTheme>(DEFAULT_THEME);
  const [savedTheme, setSavedTheme] = useState<SchoolTheme>(DEFAULT_THEME);
  const [, setHistory] = useState<SchoolTheme[]>([]);
  const [saveState, setSaveState] = useState<"idle" | "saving" | "saved">("idle");

  // Sync fetched theme into local state on first load
  useEffect(() => {
    if (fetchedTheme) {
      const theme = fetchedTheme as unknown as SchoolTheme;
      setWorkingTheme(theme);
      setSavedTheme(theme);
    }
  }, [fetchedTheme]);

  const dirty = JSON.stringify(workingTheme) !== JSON.stringify(savedTheme);

  // Cmd/Ctrl-Z undo
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "z") {
        e.preventDefault();
        setHistory((h) => {
          if (h.length === 0) return h;
          const prev = h[h.length - 1];
          setWorkingTheme(prev);
          toast.info("Undid last change");
          return h.slice(0, -1);
        });
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  // Warn before navigating away with unsaved changes
  useEffect(() => {
    if (!dirty) return;
    const handler = (e: BeforeUnloadEvent) => {
      e.preventDefault();
      e.returnValue = "";
    };
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, [dirty]);

  const mutation = useMutation({
    mutationFn: (theme: SchoolTheme) =>
      updateSchoolTheme(schoolId, theme as unknown as Record<string, unknown>),
    onSuccess: () => {
      const before = savedTheme;
      const published = workingTheme;
      setSavedTheme(published);
      queryClient.invalidateQueries({ queryKey: ["school-theme", schoolId] });
      setSaveState("saved");
      toast.success("Changes saved · Students will see this on next sign-in", {
        action: {
          label: "Undo",
          onClick: () => {
            setWorkingTheme(before);
            setSavedTheme(before);
            toast.info("Reverted to previous version");
          },
        },
        duration: 5000,
      });
      setTimeout(() => setSaveState("idle"), 1800);
    },
    onError: () => {
      setSaveState("idle");
      toast.error("Could not save. Please try again.");
    },
  });

  function pushHistory(prev: SchoolTheme) {
    setHistory((h) => [...h.slice(-19), prev]);
  }

  function updateTheme(updater: (t: SchoolTheme) => SchoolTheme) {
    setWorkingTheme((t) => {
      pushHistory(t);
      return updater(t);
    });
  }

  function discard() {
    if (!dirty) return;
    pushHistory(workingTheme);
    setWorkingTheme(savedTheme);
    toast.info("Discarded unsaved changes");
  }

  function save() {
    if (!dirty || saveState !== "idle") return;
    setSaveState("saving");
    mutation.mutate(workingTheme);
  }

  if (isLoading) {
    return (
      <div className="max-w-5xl space-y-6 p-6">
        <Skeleton className="h-10 w-48 rounded-lg" />
        <div className="grid grid-cols-[380px_1fr] gap-8">
          <Skeleton className="h-80 rounded-xl" />
          <Skeleton className="h-64 rounded-xl" />
        </div>
      </div>
    );
  }

  return (
    <div className="p-6">
      {/* Header */}
      <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="mb-1 text-xs font-semibold tracking-wider text-blue-700 uppercase">
            Settings · Customize
          </p>
          <h1 className="flex items-center gap-2 text-2xl font-bold text-gray-900">
            <Palette className="h-6 w-6 text-blue-600" />
            Customize for your school
          </h1>
          <p className="mt-1 max-w-xl text-sm text-gray-500">
            Set your school&apos;s name and a color for each subject. Students see these
            throughout the library, lessons, and dashboard.
          </p>
        </div>

        <div className="flex shrink-0 flex-wrap items-center gap-2">
          {dirty && (
            <span className="flex items-center gap-1.5 rounded-full bg-gray-100 px-3 py-1.5 text-xs font-medium text-gray-600">
              <span className="h-1.5 w-1.5 rounded-full bg-amber-500" />
              Unsaved changes
            </span>
          )}
          <Button
            variant="outline"
            size="sm"
            onClick={() => window.open("/subjects", "_blank")}
            className="gap-1.5"
          >
            <ExternalLink className="h-3.5 w-3.5" />
            Preview as student
          </Button>
          <Button variant="outline" size="sm" onClick={discard} disabled={!dirty}>
            Discard
          </Button>
          {isAdmin && (
            <Button
              size="sm"
              onClick={save}
              disabled={!dirty || saveState !== "idle"}
              className="gap-1.5"
            >
              {saveState === "saving" && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
              {saveState === "saved" && <Check className="h-3.5 w-3.5" />}
              {saveState === "saving"
                ? "Saving…"
                : saveState === "saved"
                  ? "Saved"
                  : "Save changes"}
            </Button>
          )}
        </div>
      </div>

      {!isAdmin && (
        <div className="mb-5 rounded-lg border border-amber-200 bg-amber-50 px-4 py-2.5 text-sm text-amber-800">
          Teachers can preview the school theme but cannot save changes.
        </div>
      )}

      {/* Two-column editor / preview */}
      <div className="grid grid-cols-1 gap-8 lg:grid-cols-[380px_1fr]">
        {/* LEFT — editor */}
        <div className="space-y-5">
          {/* School identity */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">School identity</CardTitle>
              <p className="text-xs text-gray-500">
                Shown in the sidebar and on lesson covers.
              </p>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-xs font-semibold tracking-wide text-gray-400 uppercase">
                  School name
                </label>
                <Input
                  value={workingTheme.school.name}
                  disabled={!isAdmin}
                  onChange={(e) =>
                    updateTheme((t) => ({
                      ...t,
                      school: {
                        ...t.school,
                        name: e.target.value,
                        logoText: e.target.value,
                      },
                    }))
                  }
                  placeholder="Your school name"
                />
              </div>
              <div className="space-y-1.5">
                <label className="text-xs font-semibold tracking-wide text-gray-400 uppercase">
                  Logo URL
                </label>
                <Input
                  value={workingTheme.school.logoUrl ?? ""}
                  disabled={!isAdmin}
                  onChange={(e) =>
                    updateTheme((t) => ({
                      ...t,
                      school: { ...t.school, logoUrl: e.target.value || null },
                    }))
                  }
                  placeholder="https://… (PNG or SVG, 200×200 or larger)"
                />
                <p className="text-xs text-gray-400">
                  Leave blank to use the default logo.
                </p>
              </div>
            </CardContent>
          </Card>

          {/* Subject colors */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Subject colors</CardTitle>
              <p className="text-xs text-gray-500">
                Pick one accent per subject. Background tints are derived automatically.
              </p>
            </CardHeader>
            <CardContent className="space-y-4">
              {SUBJECT_ORDER.map((key) => (
                <SubjectColorRow
                  key={key}
                  subjectKey={key}
                  accent={
                    workingTheme.subjects[key]?.accent ??
                    DEFAULT_THEME.subjects[key].accent
                  }
                  disabled={!isAdmin}
                  onChange={(hex) =>
                    updateTheme((t) => ({
                      ...t,
                      subjects: {
                        ...t.subjects,
                        [key]: { ...t.subjects[key], accent: hex },
                      },
                    }))
                  }
                />
              ))}
            </CardContent>
          </Card>
        </div>

        {/* RIGHT — live preview (wrapped in SchoolThemeProvider so it re-skins from workingTheme) */}
        <SchoolThemeProvider value={workingTheme}>
          <MiniLibraryPreview schoolName={workingTheme.school.name} />
        </SchoolThemeProvider>
      </div>
    </div>
  );
}
