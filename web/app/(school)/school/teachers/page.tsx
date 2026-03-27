"use client";

import { useState } from "react";
import { useTeacher } from "@/lib/hooks/useTeacher";
import { inviteTeacher } from "@/lib/api/school-admin";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { UserPlus, Check, GraduationCap, ShieldCheck } from "lucide-react";

interface InvitedTeacher {
  teacher_id: string;
  email: string;
  role: string;
}

export default function TeachersPage() {
  const teacher = useTeacher();
  const isAdmin = teacher?.role === "school_admin";

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [invited, setInvited] = useState<InvitedTeacher[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [successEmail, setSuccessEmail] = useState<string | null>(null);

  async function handleInvite() {
    if (!name || !email || !teacher?.school_id) return;
    setSubmitting(true);
    setError(null);
    setSuccessEmail(null);
    try {
      const res = await inviteTeacher(teacher.school_id, name, email);
      setInvited((prev) => [...prev, res]);
      setSuccessEmail(email);
      setName("");
      setEmail("");
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(detail ?? "Invite failed. The email may already be registered.");
    } finally {
      setSubmitting(false);
    }
  }

  if (!isAdmin) {
    return (
      <div className="p-6 max-w-2xl">
        <h1 className="text-2xl font-bold text-gray-900 mb-3">Teacher Management</h1>
        <p className="text-sm text-gray-500">
          Only school administrators can manage teachers. Contact your school admin to invite new teachers.
        </p>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-2xl space-y-6">
      <div className="flex items-center gap-2">
        <GraduationCap className="h-6 w-6 text-blue-600" />
        <h1 className="text-2xl font-bold text-gray-900">Teacher Management</h1>
        <Badge className="bg-purple-50 text-purple-700 border-purple-100 ml-1">Admin only</Badge>
      </div>

      {/* Invite form */}
      <Card className="border shadow-sm">
        <CardHeader className="pb-2">
          <CardTitle className="text-base flex items-center gap-2">
            <UserPlus className="h-4 w-4 text-blue-600" />
            Invite a teacher
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <Label htmlFor="teacher_name">Full name</Label>
              <Input
                id="teacher_name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Jane Smith"
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="teacher_email">Work email</Label>
              <Input
                id="teacher_email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="j.smith@school.edu"
              />
            </div>
          </div>

          {error && <p className="text-sm text-red-600">{error}</p>}
          {successEmail && (
            <div className="flex items-center gap-2 text-sm text-green-700 bg-green-50 border border-green-200 rounded-lg p-3">
              <Check className="h-4 w-4 shrink-0" />
              Invitation sent to <span className="font-medium">{successEmail}</span>. They will receive an Auth0 login link.
            </div>
          )}

          <Button
            onClick={handleInvite}
            disabled={submitting || !name || !email}
            className="gap-2"
          >
            {submitting ? "Sending…" : "Send invitation"}
          </Button>
        </CardContent>
      </Card>

      {/* Invited teachers in this session */}
      {invited.length > 0 && (
        <Card className="border shadow-sm">
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Invited this session</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b bg-gray-50">
                  <th className="text-left px-4 py-2.5 text-xs font-medium text-gray-500">Email</th>
                  <th className="text-left px-4 py-2.5 text-xs font-medium text-gray-500">Role</th>
                  <th className="text-left px-4 py-2.5 text-xs font-medium text-gray-500">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {invited.map((t) => (
                  <tr key={t.teacher_id}>
                    <td className="px-4 py-3 text-gray-700">{t.email}</td>
                    <td className="px-4 py-3">
                      {t.role === "school_admin" ? (
                        <span className="flex items-center gap-1 text-xs text-purple-600">
                          <ShieldCheck className="h-3.5 w-3.5" />Admin
                        </span>
                      ) : (
                        <span className="text-xs text-gray-500">Teacher</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <Badge className="bg-blue-50 text-blue-700 border-blue-100 text-xs">Invited</Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>
      )}

      <Card className="border shadow-sm bg-gray-50">
        <CardContent className="p-4">
          <p className="text-xs text-gray-500">
            Invited teachers receive an Auth0 link to set up their account. Once they sign in, they can
            access class reports and student progress. To change a teacher&apos;s role or deactivate their
            account, contact platform support.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
