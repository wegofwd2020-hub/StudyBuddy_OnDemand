import type { Metadata } from "next";
import { AboutContent, type AboutBuildData } from "./_content";

export const metadata: Metadata = {
  title: "About",
  description:
    "About StudyBuddy — our mission, the accessibility and privacy standards we target, and how every build is verified.",
};

// All build-time constants are read server-side and passed as props so the
// client component never needs to touch process.env directly.
export default function AboutPage() {
  const data: AboutBuildData = {
    buildTime: process.env.NEXT_PUBLIC_BUILD_TIME ?? "",
    snykHigh: process.env.NEXT_PUBLIC_SNYK_HIGH_COUNT ?? "",
    snykCritical: process.env.NEXT_PUBLIC_SNYK_CRITICAL_COUNT ?? "",
    snykScanDate: process.env.NEXT_PUBLIC_SNYK_SCAN_DATE ?? "",
    lastPrNumber: process.env.NEXT_PUBLIC_LAST_PR_NUMBER ?? "",
    lastPrTitle: process.env.NEXT_PUBLIC_LAST_PR_TITLE ?? "",
    lastPrUrl: process.env.NEXT_PUBLIC_LAST_PR_URL ?? "",
    lastPrMergedAt: process.env.NEXT_PUBLIC_LAST_PR_MERGED_AT ?? "",
  };

  return <AboutContent data={data} />;
}
