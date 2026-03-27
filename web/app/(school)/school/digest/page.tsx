"use client";

import { useState } from "react";
import { useTeacher } from "@/lib/hooks/useTeacher";
import { subscribeDigest } from "@/lib/api/reports";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Check, Mail } from "lucide-react";

const TIMEZONES = ["UTC","America/New_York","America/Chicago","America/Denver","America/Los_Angeles","Europe/London","Europe/Paris","Asia/Kolkata","Australia/Sydney"];

export default function DigestSettingsPage() {
  const teacher = useTeacher();
  const schoolId = teacher?.school_id ?? "";
  const [email, setEmail] = useState("");
  const [timezone, setTimezone] = useState("UTC");
  const [enabled, setEnabled] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSave() {
    if (!schoolId || !email) return;
    setSaving(true); setSaved(false); setError(null);
    try {
      await subscribeDigest(schoolId, email, timezone, enabled);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch {
      setError("Failed to save digest settings. Please try again.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="p-6 max-w-xl space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Weekly Digest</h1>
      <p className="text-sm text-gray-500">Receive a weekly summary of your class performance every Monday morning.</p>
      <Card className="border shadow-sm">
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2"><Mail className="h-4 w-4 text-blue-600" />Digest settings</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="digest_email">Email address</Label>
            <Input id="digest_email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@school.edu" />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="timezone">Timezone</Label>
            <select id="timezone" value={timezone} onChange={(e) => setTimezone(e.target.value)} className="w-full h-9 rounded-md border border-gray-200 px-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white">
              {TIMEZONES.map((tz) => <option key={tz} value={tz}>{tz}</option>)}
            </select>
          </div>
          <label className="flex items-center gap-3 cursor-pointer">
            <div className="relative">
              <input type="checkbox" className="sr-only" checked={enabled} onChange={(e) => setEnabled(e.target.checked)} />
              <div className={`w-10 h-6 rounded-full transition-colors ${enabled ? "bg-blue-600" : "bg-gray-200"}`}>
                <div className={`w-4 h-4 bg-white rounded-full shadow-sm transition-transform mt-1 ${enabled ? "translate-x-5" : "translate-x-1"}`} />
              </div>
            </div>
            <span className="text-sm text-gray-700">{enabled ? "Digest enabled — sent every Monday" : "Digest disabled"}</span>
          </label>
          {error && <p className="text-sm text-red-600">{error}</p>}
          <div className="flex items-center gap-3 pt-1">
            <Button onClick={handleSave} disabled={saving || !email}>{saving ? "Saving…" : "Save settings"}</Button>
            {saved && <span className="text-sm text-green-600 flex items-center gap-1"><Check className="h-4 w-4" />Saved</span>}
          </div>
        </CardContent>
      </Card>
      <Card className="border shadow-sm bg-blue-50/50">
        <CardContent className="p-4">
          <p className="text-sm text-blue-800 font-medium mb-1">What&apos;s in the digest?</p>
          <ul className="text-xs text-blue-700 space-y-1 list-disc list-inside">
            <li>Active student count and activity rate vs prior week</li>
            <li>Top 3 best-performing units</li>
            <li>Units flagged as struggling or watch</li>
            <li>New unreviewed feedback count</li>
            <li>First-attempt pass rate trend</li>
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}
