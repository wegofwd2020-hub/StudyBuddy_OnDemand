"use client";

import { useQuery } from "@tanstack/react-query";
import { useTeacher } from "@/lib/hooks/useTeacher";
import { getSchoolProfile } from "@/lib/api/school-admin";
import { getBillingPortalUrl } from "@/lib/api/subscription";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Copy, Check, CreditCard, Building2, Globe } from "lucide-react";
import { useState } from "react";

export default function SchoolSettingsPage() {
  const teacher = useTeacher();
  const schoolId = teacher?.school_id ?? "";
  const isAdmin = teacher?.role === "school_admin";

  const { data: profile, isLoading } = useQuery({
    queryKey: ["school-profile", schoolId],
    queryFn: () => getSchoolProfile(schoolId),
    enabled: !!schoolId,
    staleTime: 300_000,
  });

  const [copiedCode, setCopiedCode] = useState(false);
  const [loadingBilling, setLoadingBilling] = useState(false);

  function copyEnrolmentCode() {
    if (!profile?.enrolment_code) return;
    navigator.clipboard.writeText(profile.enrolment_code).then(() => {
      setCopiedCode(true);
      setTimeout(() => setCopiedCode(false), 2000);
    });
  }

  async function openBillingPortal() {
    setLoadingBilling(true);
    try {
      const url = await getBillingPortalUrl();
      window.location.href = url;
    } catch {
      setLoadingBilling(false);
    }
  }

  return (
    <div className="p-6 max-w-2xl space-y-6">
      <div className="flex items-center gap-2">
        <Building2 className="h-6 w-6 text-blue-600" />
        <h1 className="text-2xl font-bold text-gray-900">School Settings</h1>
      </div>

      {isLoading && <Skeleton className="h-48 rounded-lg" />}

      {profile && (
        <>
          {/* Profile card */}
          <Card className="border shadow-sm">
            <CardHeader className="pb-2">
              <CardTitle className="text-base">School profile</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <p className="text-xs text-gray-400 font-medium uppercase tracking-wide mb-0.5">School name</p>
                  <p className="font-semibold text-gray-900">{profile.name}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-400 font-medium uppercase tracking-wide mb-0.5">Contact email</p>
                  <p className="text-gray-700">{profile.contact_email}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-400 font-medium uppercase tracking-wide mb-0.5">Country</p>
                  <p className="flex items-center gap-1 text-gray-700">
                    <Globe className="h-3.5 w-3.5 text-gray-400" />
                    {profile.country}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-gray-400 font-medium uppercase tracking-wide mb-0.5">Account status</p>
                  <Badge className="bg-green-50 text-green-700 border-green-200 text-xs">{profile.status}</Badge>
                </div>
                <div>
                  <p className="text-xs text-gray-400 font-medium uppercase tracking-wide mb-0.5">Member since</p>
                  <p className="text-gray-500 text-xs">{new Date(profile.created_at).toLocaleDateString()}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-400 font-medium uppercase tracking-wide mb-0.5">School ID</p>
                  <p className="font-mono text-xs text-gray-400">{profile.school_id}</p>
                </div>
              </div>

              {!isAdmin && (
                <p className="text-xs text-gray-400 pt-2">
                  Contact your school administrator to update school details.
                </p>
              )}
            </CardContent>
          </Card>

          {/* Enrolment code */}
          {profile.enrolment_code && (
            <Card className="border shadow-sm">
              <CardHeader className="pb-2">
                <CardTitle className="text-base">Enrolment code</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-xs text-gray-500 mb-3">
                  Students use this code to self-enrol. Share via the invite link or paste it directly.
                </p>
                <div className="flex items-center gap-2">
                  <code className="bg-gray-50 border rounded px-4 py-2 text-lg font-mono font-bold tracking-widest text-gray-800">
                    {profile.enrolment_code}
                  </code>
                  <Button variant="outline" size="sm" onClick={copyEnrolmentCode} className="gap-1.5">
                    {copiedCode ? <Check className="h-3.5 w-3.5 text-green-500" /> : <Copy className="h-3.5 w-3.5" />}
                    {copiedCode ? "Copied" : "Copy"}
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Billing portal — admin only */}
          {isAdmin && (
            <Card className="border shadow-sm">
              <CardHeader className="pb-2">
                <CardTitle className="text-base">Billing</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-gray-600 mb-3">
                  Manage your school subscription, update payment details, and download invoices.
                </p>
                <Button
                  variant="outline"
                  onClick={openBillingPortal}
                  disabled={loadingBilling}
                  className="gap-2"
                >
                  <CreditCard className="h-4 w-4" />
                  {loadingBilling ? "Opening portal…" : "Open billing portal"}
                </Button>
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
