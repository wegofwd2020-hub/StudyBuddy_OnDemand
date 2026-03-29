"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { CheckCircle, Mail, School } from "lucide-react";

const schema = z.object({
  name: z.string().min(2, "Name is required"),
  email: z.string().email("Valid email required"),
  subject: z.string().min(3, "Subject is required"),
  message: z.string().min(10, "Please provide more detail"),
});

type FormData = z.infer<typeof schema>;

export default function ContactPage() {
  const [done, setDone] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({ resolver: zodResolver(schema) });

  async function onSubmit() {
    // In production, POST to /api/contact or a form service
    await new Promise((r) => setTimeout(r, 600));
    setDone(true);
  }

  if (done) {
    return (
      <div className="flex min-h-[80vh] items-center justify-center px-4">
        <div className="space-y-3 text-center">
          <CheckCircle className="mx-auto h-12 w-12 text-green-500" />
          <h1 className="text-2xl font-bold">Message sent!</h1>
          <p className="text-gray-500">
            We&apos;ll get back to you within 1 business day.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-5xl px-4 py-16">
      <div className="mb-12 text-center">
        <h1 className="text-4xl font-bold text-gray-900">Get in touch</h1>
        <p className="mt-4 text-lg text-gray-500">
          Questions about schools, pricing, or the platform? We&apos;d love to hear from
          you.
        </p>
      </div>

      <div className="grid items-start gap-8 md:grid-cols-2">
        {/* Contact info */}
        <div className="space-y-6">
          <div className="flex items-start gap-4">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-blue-50">
              <Mail className="h-5 w-5 text-blue-600" />
            </div>
            <div>
              <h3 className="font-semibold text-gray-900">General enquiries</h3>
              <p className="text-sm text-gray-500">hello@studybuddy.com</p>
            </div>
          </div>
          <div className="flex items-start gap-4">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-indigo-50">
              <School className="h-5 w-5 text-indigo-600" />
            </div>
            <div>
              <h3 className="font-semibold text-gray-900">School &amp; district sales</h3>
              <p className="text-sm text-gray-500">schools@studybuddy.com</p>
              <p className="mt-1 text-sm text-gray-400">
                We offer volume pricing, custom onboarding, and dedicated support for
                schools.
              </p>
            </div>
          </div>
        </div>

        {/* Form */}
        <Card className="shadow-sm">
          <CardHeader>
            <CardTitle className="text-lg">Send us a message</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1">
                  <Label htmlFor="name">Name</Label>
                  <Input id="name" {...register("name")} />
                  {errors.name && (
                    <p className="text-xs text-red-500">{errors.name.message}</p>
                  )}
                </div>
                <div className="space-y-1">
                  <Label htmlFor="email">Email</Label>
                  <Input id="email" type="email" {...register("email")} />
                  {errors.email && (
                    <p className="text-xs text-red-500">{errors.email.message}</p>
                  )}
                </div>
              </div>
              <div className="space-y-1">
                <Label htmlFor="subject">Subject</Label>
                <Input id="subject" {...register("subject")} />
                {errors.subject && (
                  <p className="text-xs text-red-500">{errors.subject.message}</p>
                )}
              </div>
              <div className="space-y-1">
                <Label htmlFor="message">Message</Label>
                <Textarea id="message" rows={4} {...register("message")} />
                {errors.message && (
                  <p className="text-xs text-red-500">{errors.message.message}</p>
                )}
              </div>
              <Button type="submit" className="w-full" disabled={isSubmitting}>
                {isSubmitting ? "Sending…" : "Send message"}
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
