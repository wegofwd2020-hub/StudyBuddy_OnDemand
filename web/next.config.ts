import type { NextConfig } from "next";
import createNextIntlPlugin from "next-intl/plugin";

const withNextIntl = createNextIntlPlugin("./lib/i18n/request.ts");

// Derive the backend API origin so the CSP connect-src is scoped correctly.
// NEXT_PUBLIC_API_URL is set in .env.local / CI / production deploy config.
const apiOrigin = process.env.NEXT_PUBLIC_API_URL
  ? new URL(process.env.NEXT_PUBLIC_API_URL).origin
  : "http://localhost:8000";

// Content-Security-Policy
// - default-src 'self': baseline allowlist
// - script-src 'self' 'unsafe-inline': Next.js inline bootstrap scripts require unsafe-inline;
//   nonce-based CSP is the correct long-term fix but is left for a dedicated hardening sprint.
// - 'unsafe-eval' is added only in development: React dev builds use eval() for call-stack
//   reconstruction and debugging features. React never uses eval() in production.
// - connect-src: API origin + Stripe telemetry (JS.stripe.com requires it)
// - img-src 'self' data: blob: *.cloudfront.net: lesson images served from CDN
// - frame-src https://js.stripe.com: Stripe Checkout iframe
// - frame-ancestors 'none': equivalent to X-Frame-Options DENY, but honoured by modern browsers
const isDev = process.env.NODE_ENV === "development";
const csp = [
  "default-src 'self'",
  isDev
    ? "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://js.stripe.com"
    : "script-src 'self' 'unsafe-inline' https://js.stripe.com",
  `connect-src 'self' ${apiOrigin} https://api.stripe.com`,
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data: blob: https://*.cloudfront.net",
  "font-src 'self'",
  "frame-src https://js.stripe.com",
  "frame-ancestors 'none'",
  "object-src 'none'",
  "base-uri 'self'",
  "form-action 'self'",
]
  .join("; ")
  .trimEnd();

const nextConfig: NextConfig = {
  // Stamp build metadata into the bundle so the About page reflects each deployment.
  //
  // SNYK_HIGH_COUNT / SNYK_CRITICAL_COUNT / SNYK_SCAN_DATE are injected by the
  // CI workflow after parsing the Snyk SARIF outputs (see .github/workflows/test.yml).
  // LAST_PR_NUMBER / LAST_PR_TITLE / LAST_PR_URL / LAST_PR_MERGED_AT are injected
  // by the CI workflow from the GitHub API before running `npm run build`.
  // All values are empty strings locally — the About page renders a "pending" state.
  env: {
    NEXT_PUBLIC_BUILD_TIME: new Date().toISOString(),
    NEXT_PUBLIC_SNYK_HIGH_COUNT: process.env.SNYK_HIGH_COUNT ?? "",
    NEXT_PUBLIC_SNYK_CRITICAL_COUNT: process.env.SNYK_CRITICAL_COUNT ?? "",
    NEXT_PUBLIC_SNYK_SCAN_DATE: process.env.SNYK_SCAN_DATE ?? "",
    NEXT_PUBLIC_LAST_PR_NUMBER: process.env.LAST_PR_NUMBER ?? "",
    NEXT_PUBLIC_LAST_PR_TITLE: process.env.LAST_PR_TITLE ?? "",
    NEXT_PUBLIC_LAST_PR_URL: process.env.LAST_PR_URL ?? "",
    NEXT_PUBLIC_LAST_PR_MERGED_AT: process.env.LAST_PR_MERGED_AT ?? "",
  },
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "**.cloudfront.net",
      },
    ],
  },
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "X-Frame-Options", value: "DENY" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          // HSTS: 1-year max-age; includeSubDomains locks *.studybuddy.com too.
          // Only meaningful over HTTPS — ignored by browsers on plain HTTP.
          {
            key: "Strict-Transport-Security",
            value: "max-age=31536000; includeSubDomains",
          },
          { key: "Content-Security-Policy", value: csp },
          // Restrict browser feature APIs to same-origin only.
          // camera/microphone/geolocation are not needed by StudyBuddy.
          {
            key: "Permissions-Policy",
            value: "camera=(), microphone=(), geolocation=()",
          },
        ],
      },
    ];
  },
};

export default withNextIntl(nextConfig);
