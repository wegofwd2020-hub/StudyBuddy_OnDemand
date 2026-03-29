"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { confirmEnrolment } from "@/lib/api/school";
import { LinkButton } from "@/components/ui/link-button";
import { Skeleton } from "@/components/ui/skeleton";
import { CheckCircle, XCircle } from "lucide-react";

type State = "loading" | "success" | "error";

export default function EnrolConfirmPage() {
  const { token } = useParams<{ token: string }>();
  const [state, setState] = useState<State>("loading");
  const [schoolName, setSchoolName] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    if (!token) return;
    confirmEnrolment(token)
      .then(({ school_name }) => {
        setSchoolName(school_name);
        setState("success");
      })
      .catch((err) => {
        const msg =
          err?.response?.data?.detail ?? "This enrolment link is invalid or has expired.";
        setErrorMsg(msg);
        setState("error");
      });
  }, [token]);

  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center p-6 text-center">
      {state === "loading" && (
        <div className="w-full max-w-sm space-y-4">
          <Skeleton className="mx-auto h-16 w-16 rounded-full" />
          <Skeleton className="mx-auto h-6 w-48" />
          <Skeleton className="mx-auto h-4 w-64" />
        </div>
      )}

      {state === "success" && (
        <div className="max-w-sm space-y-4">
          <CheckCircle className="mx-auto h-16 w-16 text-green-500" />
          <h1 className="text-2xl font-bold text-gray-900">You&apos;re enrolled!</h1>
          <p className="text-gray-600">
            You&apos;ve been successfully enrolled in{" "}
            <span className="font-semibold">{schoolName}</span>. Your curriculum has been
            updated.
          </p>
          <LinkButton href="/dashboard" className="mt-2">
            Go to dashboard
          </LinkButton>
        </div>
      )}

      {state === "error" && (
        <div className="max-w-sm space-y-4">
          <XCircle className="mx-auto h-16 w-16 text-red-400" />
          <h1 className="text-2xl font-bold text-gray-900">Enrolment failed</h1>
          <p className="text-gray-600">{errorMsg}</p>
          <LinkButton href="/dashboard" variant="outline">
            Back to dashboard
          </LinkButton>
        </div>
      )}
    </div>
  );
}
