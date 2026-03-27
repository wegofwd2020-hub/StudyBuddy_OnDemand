import type { Metadata } from "next";

export const metadata: Metadata = { title: "Privacy Policy" };

export default function PrivacyPage() {
  return (
    <div className="mx-auto max-w-3xl px-4 py-16">
      <h1 className="text-3xl font-bold text-gray-900 mb-8">Privacy Policy</h1>
      <div className="space-y-6 text-gray-600">
        <p className="text-sm text-gray-400">Last updated: March 2026</p>

        <section>
          <h2 className="text-xl font-semibold text-gray-800 mb-3">Data We Collect</h2>
          <ul className="list-disc pl-5 space-y-1 text-sm">
            <li>Account information (name, email, grade)</li>
            <li>Progress data (lesson views, quiz attempts, scores)</li>
            <li>Usage analytics (session duration, device type)</li>
            <li>Payment information (handled by Stripe — we never store card numbers)</li>
          </ul>
        </section>

        <section>
          <h2 className="text-xl font-semibold text-gray-800 mb-3">COPPA (Children Under 13)</h2>
          <p className="text-sm">
            We collect only the minimum data necessary for students under 13 and require verifiable
            parental consent before account activation. Parents may request deletion of their
            child&apos;s data at any time by contacting{" "}
            <a href="mailto:privacy@studybuddy.com" className="text-blue-600 hover:underline">
              privacy@studybuddy.com
            </a>
            .
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold text-gray-800 mb-3">GDPR (EU Users)</h2>
          <p className="text-sm">
            EU users have the right to access, rectify, erase, and port their data. To exercise
            these rights, contact our Data Protection Officer at{" "}
            <a href="mailto:dpo@studybuddy.com" className="text-blue-600 hover:underline">
              dpo@studybuddy.com
            </a>
            .
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold text-gray-800 mb-3">FERPA (School Users)</h2>
          <p className="text-sm">
            For students enrolled through a school, we act as a school official under FERPA.
            Student educational records are not shared with third parties without consent.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold text-gray-800 mb-3">Data Retention</h2>
          <p className="text-sm">
            Active account data is retained while your account is active. Upon account deletion,
            personal data is removed within 30 days. Anonymised analytics data may be retained
            indefinitely.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold text-gray-800 mb-3">Third-Party Services</h2>
          <ul className="list-disc pl-5 space-y-1 text-sm">
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
