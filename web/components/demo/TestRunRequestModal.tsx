"use client";

/**
 * "Try a test run" modal — collects Name + Email and POSTs to
 * /demo/test-run/request. The backend provisions both a demo teacher AND a
 * demo student account, then emails the combined credentials.
 *
 * Used on the demo landing page (IS_DEMO_MODE) by PublicNav. Mirrors the
 * existing DemoRequestModal pattern but uses the unified test-run endpoint
 * and asks for the visitor's name so the credentials email can address them.
 */

import { useState, type ReactElement } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { CheckCircle } from "lucide-react";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { requestTestRun } from "@/lib/api/demo";

const schema = z.object({
  name: z
    .string()
    .trim()
    .min(1, "Name is required")
    .max(120, "Name must be 120 characters or fewer"),
  email: z.string().email("Valid email required"),
});

type FormData = z.infer<typeof schema>;

type ErrorKey =
  | "error_rate_limited"
  | "error_pending"
  | "error_already_active"
  | "error_generic";

function resolveErrorKey(status: number | undefined, code: string | undefined): ErrorKey {
  if (status === 429) return "error_rate_limited";
  if (status === 409 && code === "verification_pending") return "error_pending";
  if (status === 409 && code === "demo_already_active") return "error_already_active";
  return "error_generic";
}

const ERROR_COPY: Record<ErrorKey, string> = {
  error_rate_limited:
    "Too many test-run requests from this network. Please try again in an hour.",
  error_pending:
    "A verification email was already sent to this address. Please check your inbox.",
  error_already_active:
    "A test run for this email is already active. Please check your inbox for the credentials.",
  error_generic: "Something went wrong. Please try again.",
};

interface TestRunRequestModalProps {
  /**
   * Optional custom trigger element. When omitted the modal renders a default
   * solid "Try a test run" button. Mobile menus pass a full-width variant.
   * Must be a single ReactElement — DialogTrigger uses `render` cloning.
   */
  trigger?: ReactElement;
}

export function TestRunRequestModal({ trigger }: TestRunRequestModalProps) {
  const [open, setOpen] = useState(false);
  const [submittedEmail, setSubmittedEmail] = useState("");
  const [errorKey, setErrorKey] = useState<ErrorKey | null>(null);

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({ resolver: zodResolver(schema) });

  function handleOpenChange(next: boolean) {
    setOpen(next);
    if (!next) {
      reset();
      setErrorKey(null);
      setSubmittedEmail("");
    }
  }

  async function onSubmit(data: FormData) {
    setErrorKey(null);
    try {
      await requestTestRun({ name: data.name, email: data.email });
      setSubmittedEmail(data.email);
    } catch (err: unknown) {
      const axiosErr = err as {
        response?: { status?: number; data?: { error?: string } };
      };
      setErrorKey(
        resolveErrorKey(axiosErr.response?.status, axiosErr.response?.data?.error),
      );
    }
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger render={trigger ?? <Button size="default">Try a test run</Button>} />

      <DialogContent className="sm:max-w-md">
        {submittedEmail ? (
          /* ── Success state ─────────────────────────────────────────── */
          <>
            <DialogHeader>
              <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-green-50">
                <CheckCircle className="h-6 w-6 text-green-600" />
              </div>
              <DialogTitle className="text-center">Check your inbox</DialogTitle>
              <DialogDescription className="text-center">
                We&apos;ve sent a verification link to{" "}
                <span className="font-medium">{submittedEmail}</span>. Click the link in
                the email — we&apos;ll then send you the teacher and student login
                credentials in a second email.
              </DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <Button className="w-full" onClick={() => handleOpenChange(false)}>
                Got it
              </Button>
            </DialogFooter>
          </>
        ) : (
          /* ── Request form ──────────────────────────────────────────── */
          <>
            <DialogHeader>
              <DialogTitle>Try a test run</DialogTitle>
              <DialogDescription>
                Enter your name and email. We&apos;ll send you teacher and student login
                credentials so you can explore StudyBuddy from both sides.
              </DialogDescription>
            </DialogHeader>

            <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
              <div className="space-y-1">
                <Label htmlFor="test-run-name">Name</Label>
                <Input
                  id="test-run-name"
                  type="text"
                  autoComplete="name"
                  placeholder="Your name"
                  aria-invalid={!!errors.name}
                  {...register("name")}
                />
                {errors.name && (
                  <p className="text-xs text-red-500">{errors.name.message}</p>
                )}
              </div>

              <div className="space-y-1">
                <Label htmlFor="test-run-email">Email</Label>
                <Input
                  id="test-run-email"
                  type="email"
                  autoComplete="email"
                  placeholder="you@example.com"
                  aria-invalid={!!errors.email}
                  {...register("email")}
                />
                {errors.email && (
                  <p className="text-xs text-red-500">{errors.email.message}</p>
                )}
              </div>

              {errorKey && (
                <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
                  {ERROR_COPY[errorKey]}
                </p>
              )}

              <div className="flex justify-center">
                <Button type="submit" disabled={isSubmitting}>
                  {isSubmitting ? "Sending…" : "Send me credentials"}
                </Button>
              </div>
            </form>

            <p className="mt-2 text-center text-xs text-gray-500">
              Already have credentials?{" "}
              <Link
                href="/signin"
                className="text-blue-600 underline underline-offset-2 hover:text-blue-800"
                onClick={() => handleOpenChange(false)}
              >
                Sign in
              </Link>
            </p>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}
