import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Accessibility Statement",
  description:
    "StudyBuddy's commitment to web accessibility — the standards we target, known limitations, and how to report an issue.",
};

const LAST_REVIEWED = "March 2026";

export default function AccessibilityStatementPage() {
  return (
    <div className="mx-auto max-w-3xl px-4 py-16">
      <h1 className="mb-2 text-3xl font-bold text-gray-900">Accessibility Statement</h1>
      <p className="mb-10 text-sm text-gray-400">Last reviewed: {LAST_REVIEWED}</p>

      <div className="space-y-10 text-gray-600">
        {/* Commitment */}
        <section aria-labelledby="commitment">
          <h2 id="commitment" className="mb-3 text-xl font-semibold text-gray-800">
            Our Commitment
          </h2>
          <p className="text-sm leading-relaxed">
            StudyBuddy is committed to ensuring that its web portal is accessible to the
            widest possible audience, regardless of technology, ability, or circumstance.
            This commitment extends to students with dyslexia, colour blindness, motor
            impairments, low vision, and users who rely on assistive technologies such as
            screen readers or keyboard-only navigation.
          </p>
        </section>

        {/* Standards */}
        <section aria-labelledby="standards">
          <h2 id="standards" className="mb-3 text-xl font-semibold text-gray-800">
            Standards We Target
          </h2>
          <p className="mb-3 text-sm leading-relaxed">
            We target conformance with the following accessibility standards:
          </p>
          <ul className="space-y-2 text-sm">
            {[
              {
                name: "WCAG 2.1 Level AA",
                spec: "W3C Recommendation, June 2018",
                note: "Our primary target. Automated testing runs on every build using axe-core across all three portals (student, teacher, admin).",
              },
              {
                name: "WCAG 2.2 Level AA",
                spec: "W3C Recommendation, October 2023",
                note: "We are actively working through the nine new success criteria, including SC 2.5.8 (Target Size Minimum — all interactive elements are at least 24×24 CSS pixels) and SC 3.2.6 (Consistent Help — help links appear in the same footer location on every page).",
              },
              {
                name: "Section 508 of the Rehabilitation Act",
                spec: "US Federal, 2018 Refresh",
                note: "Satisfied by our WCAG 2.1 AA compliance, which is the referenced technical standard.",
              },
              {
                name: "EN 301 549 v3.2.1",
                spec: "ETSI, 2021",
                note: "European standard for ICT accessibility. References WCAG 2.1 AA for web content.",
              },
              {
                name: "AODA — Accessibility for Ontarians with Disabilities Act",
                spec: "Ontario, Canada — IASR, 2012",
                note: "WCAG 2.0 Level AA is the required minimum; our WCAG 2.1 AA target exceeds this.",
              },
            ].map(({ name, spec, note }) => (
              <li key={name} className="rounded-lg border border-gray-100 bg-gray-50 p-4">
                <p className="font-medium text-gray-900">{name}</p>
                <p className="text-xs text-gray-400">{spec}</p>
                <p className="mt-1 text-sm text-gray-500">{note}</p>
              </li>
            ))}
          </ul>
          <p className="mt-3 text-sm">
            Full details of every standard we track are on the{" "}
            <Link href="/about" className="text-blue-600 hover:underline">
              About page
            </Link>
            .
          </p>
        </section>

        {/* Features */}
        <section aria-labelledby="features">
          <h2 id="features" className="mb-3 text-xl font-semibold text-gray-800">
            Accessibility Features
          </h2>
          <ul className="list-disc space-y-2 pl-5 text-sm">
            <li>
              <strong>Dyslexia-friendly font</strong> — enable OpenDyslexic in{" "}
              <Link href="/account/settings" className="text-blue-600 hover:underline">
                Settings
              </Link>{" "}
              to switch body text to a font designed to reduce letter confusion.
            </li>
            <li>
              <strong>Audio lessons</strong> — every lesson has a narrated audio version
              so content is available to users who find reading difficult.
            </li>
            <li>
              <strong>High-contrast mode</strong> — the site responds correctly to Windows
              High Contrast Mode and macOS Increase Contrast, using system colours so
              interactive elements remain visible.
            </li>
            <li>
              <strong>Keyboard navigation</strong> — all functionality is operable via
              keyboard alone. A skip-to-main-content link is the first focusable element
              on every page.
            </li>
            <li>
              <strong>Screen reader support</strong> — ARIA roles, labels, and live
              regions are used throughout. Decorative images are hidden from the
              accessibility tree.
            </li>
            <li>
              <strong>Multi-language</strong> — full content in English, French, and
              Spanish. The <code>lang</code> attribute on <code>&lt;html&gt;</code>{" "}
              reflects the active locale.
            </li>
          </ul>
        </section>

        {/* Known limitations */}
        <section aria-labelledby="limitations">
          <h2 id="limitations" className="mb-3 text-xl font-semibold text-gray-800">
            Known Limitations
          </h2>
          <ul className="list-disc space-y-2 pl-5 text-sm">
            <li>
              <strong>WCAG 2.2 full coverage</strong> — automated axe-core tests cover all
              three portals for WCAG 2.1 AA; WCAG 2.2 coverage is being expanded and is
              not yet complete across every page.
            </li>
            <li>
              <strong>Third-party embeds</strong> — Stripe Checkout and Auth0 login flows
              are provided by third parties. We work with those providers to maintain
              accessibility but cannot guarantee full conformance in those embedded
              components.
            </li>
            <li>
              <strong>Complex diagrams</strong> — Mermaid.js-rendered experiment diagrams
              include a text alternative in the surrounding content, but the SVG itself
              may not be fully navigable by screen readers.
            </li>
          </ul>
        </section>

        {/* Feedback */}
        <section aria-labelledby="feedback">
          <h2 id="feedback" className="mb-3 text-xl font-semibold text-gray-800">
            Feedback and Contact
          </h2>
          <p className="mb-3 text-sm leading-relaxed">
            We welcome feedback on the accessibility of StudyBuddy. If you encounter a
            barrier, need content in an alternative format, or would like to report a
            problem, please contact us:
          </p>
          <ul className="space-y-2 text-sm">
            <li>
              <strong>Email: </strong>
              <a
                href="mailto:accessibility@studybuddy.com"
                className="text-blue-600 hover:underline"
              >
                accessibility@studybuddy.com
              </a>
            </li>
            <li>
              <strong>Contact form: </strong>
              <Link href="/contact" className="text-blue-600 hover:underline">
                studybuddy.com/contact
              </Link>
            </li>
          </ul>
          <p className="mt-3 text-sm text-gray-500">
            We aim to respond to accessibility feedback within 2 business days. If you are
            not satisfied with our response, you may contact the relevant supervisory
            authority in your jurisdiction.
          </p>
        </section>

        {/* Enforcement */}
        <section aria-labelledby="enforcement">
          <h2 id="enforcement" className="mb-3 text-xl font-semibold text-gray-800">
            Enforcement
          </h2>
          <ul className="space-y-1 text-sm">
            <li>
              <strong>United States:</strong> US Access Board —{" "}
              <a
                href="https://www.access-board.gov"
                className="text-blue-600 hover:underline"
                rel="noopener noreferrer"
                target="_blank"
              >
                access-board.gov
              </a>
            </li>
            <li>
              <strong>Canada (Ontario):</strong> Accessibility Directorate of Ontario
            </li>
            <li>
              <strong>European Union:</strong> Your national accessibility supervisory
              authority
            </li>
            <li>
              <strong>United Kingdom:</strong> Equality and Human Rights Commission
            </li>
          </ul>
        </section>
      </div>
    </div>
  );
}
