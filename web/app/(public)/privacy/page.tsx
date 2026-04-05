import type { Metadata } from "next";

export const metadata: Metadata = { title: "Privacy Policy" };

export default function PrivacyPage() {
  return (
    <div className="mx-auto max-w-3xl px-4 py-16">
      <h1 className="mb-8 text-3xl font-bold text-gray-900">Privacy Policy</h1>
      <div className="space-y-6 text-gray-600">
        <p className="text-sm text-gray-400">Last updated: March 2026</p>

        <section>
          <h2 className="mb-3 text-xl font-semibold text-gray-800">Data We Collect</h2>
          <ul className="list-disc space-y-1 pl-5 text-sm">
            <li>Account information (name, email, grade)</li>
            <li>Progress data (lesson views, quiz attempts, scores)</li>
            <li>Usage analytics (session duration, device type)</li>
            <li>Payment information (handled by Stripe — we never store card numbers)</li>
          </ul>
        </section>

        <section>
          <h2 className="mb-3 text-xl font-semibold text-gray-800">
            COPPA (Children Under 13)
          </h2>
          <p className="text-sm">
            We collect only the minimum data necessary for students under 13 and require
            verifiable parental consent before account activation. Parents may request
            deletion of their child&apos;s data at any time by contacting{" "}
            <a
              href="mailto:privacy@studybuddy.com"
              className="text-blue-600 hover:underline"
            >
              privacy@studybuddy.com
            </a>
            .
          </p>
        </section>

        <section>
          <h2 className="mb-3 text-xl font-semibold text-gray-800">GDPR (EU Users)</h2>
          <p className="text-sm">
            EU users have the right to access, rectify, erase, and port their data. To
            exercise these rights, contact our Data Protection Officer at{" "}
            <a href="mailto:dpo@studybuddy.com" className="text-blue-600 hover:underline">
              dpo@studybuddy.com
            </a>
            .
          </p>
        </section>

        <section>
          <h2 className="mb-3 text-xl font-semibold text-gray-800">
            FERPA (School Users)
          </h2>
          <p className="text-sm">
            For students enrolled through a school, we act as a school official under
            FERPA. Student educational records are not shared with third parties without
            consent.
          </p>
        </section>

        <section>
          <h2 className="mb-3 text-xl font-semibold text-gray-800">
            SOPIPA (Student Data Privacy — California)
          </h2>
          <p className="text-sm">
            In compliance with the Student Online Personal Information Protection Act, we
            do not use student data to target advertising, build profiles for
            non-educational purposes, sell student information, or disclose it to third
            parties except as needed to provide the educational service. Student data is
            used solely to deliver and improve the StudyBuddy learning experience.
          </p>
        </section>

        <section>
          <h2 className="mb-3 text-xl font-semibold text-gray-800">
            CCPA / CPRA (California Residents)
          </h2>
          <p className="mb-2 text-sm">
            California residents have the right to know what personal information we
            collect, request deletion of their data, and opt out of the sale or sharing of
            personal information. We do not sell or share personal information as defined
            by the CCPA. To exercise your rights, contact{" "}
            <a
              href="mailto:privacy@studybuddy.com"
              className="text-blue-600 hover:underline"
            >
              privacy@studybuddy.com
            </a>
            .
          </p>
        </section>

        <section>
          <h2 className="mb-3 text-xl font-semibold text-gray-800">Data Retention</h2>
          <p className="text-sm">
            Active account data is retained while your account is active. Upon account
            deletion, personal data is removed within 30 days. Anonymised analytics data
            may be retained indefinitely.
          </p>
        </section>

        <section>
          <h2 className="mb-3 text-xl font-semibold text-gray-800">
            Third-Party Services
          </h2>
          <ul className="list-disc space-y-1 pl-5 text-sm">
            <li>Auth0 — authentication</li>
            <li>Stripe — payment processing</li>
            <li>AWS — infrastructure (S3, CloudFront, RDS)</li>
            <li>SendGrid — transactional email</li>
          </ul>
        </section>
      </div>
    </div>
  );
}
