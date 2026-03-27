import type { Metadata } from "next";

export const metadata: Metadata = { title: "Terms of Service" };

export default function TermsPage() {
  return (
    <div className="mx-auto max-w-3xl px-4 py-16">
      <h1 className="text-3xl font-bold text-gray-900 mb-8">Terms of Service</h1>
      <div className="prose prose-gray max-w-none space-y-6 text-gray-600">
        <p className="text-sm text-gray-400">Last updated: March 2026</p>

        <section>
          <h2 className="text-xl font-semibold text-gray-800 mb-3">1. Acceptance of Terms</h2>
          <p>
            By accessing or using StudyBuddy OnDemand (&ldquo;Service&rdquo;), you agree to be bound
            by these Terms of Service. If you are under 18, your parent or guardian must agree on
            your behalf.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold text-gray-800 mb-3">2. Subscription and Payments</h2>
          <p>
            Paid plans are billed monthly or annually via Stripe. You may cancel at any time;
            access continues until the end of your billing period. No refunds are issued for
            partial periods.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold text-gray-800 mb-3">3. Acceptable Use</h2>
          <p>
            You may not share your account credentials, reverse-engineer the platform, or use the
            Service in any way that violates applicable law.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold text-gray-800 mb-3">4. Content</h2>
          <p>
            All AI-generated educational content is provided for informational purposes. While we
            strive for accuracy, you should verify important information with a qualified teacher.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold text-gray-800 mb-3">5. Children&apos;s Privacy</h2>
          <p>
            Users under 13 require verifiable parental consent before account activation, in
            compliance with COPPA. See our Privacy Policy for details.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold text-gray-800 mb-3">6. Limitation of Liability</h2>
          <p>
            StudyBuddy is provided &ldquo;as is&rdquo; without warranties of any kind. Our liability
            is limited to the amount paid by you in the 12 months preceding any claim.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold text-gray-800 mb-3">7. Contact</h2>
          <p>
            Questions about these terms? Contact us at{" "}
            <a href="mailto:legal@studybuddy.com" className="text-blue-600 hover:underline">
              legal@studybuddy.com
            </a>
            .
          </p>
        </section>
      </div>
    </div>
  );
}
