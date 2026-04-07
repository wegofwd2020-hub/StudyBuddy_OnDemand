import type { Metadata } from "next";
import { Inter, Merriweather, JetBrains_Mono } from "next/font/google";
import { cookies } from "next/headers";
import { NextIntlClientProvider } from "next-intl";
import { getLocale, getMessages } from "next-intl/server";
import { Toaster } from "@/components/ui/sonner";
import "./globals.css";

// Headings & labels — Inter (sans-serif, clear, scannable)
const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
  display: "swap",
});

// Body text — Merriweather (serif, warm, readable for longer content)
const merriweather = Merriweather({
  variable: "--font-merriweather",
  subsets: ["latin"],
  weight: ["300", "400", "700"],
  display: "swap",
});

// Numbers, IDs, code — JetBrains Mono (tabular, developer-friendly)
const jetbrainsMono = JetBrains_Mono({
  variable: "--font-jetbrains-mono",
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  title: {
    default: "StudyBuddy \u2014 AI-powered study material for Grades 5\u201312",
    template: "%s | StudyBuddy",
  },
  description:
    "Instant AI-powered lessons, quizzes, and audio for any subject. Available in English, French, and Spanish.",
};

export default async function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  const locale = await getLocale();
  const messages = await getMessages();

  // Read the dyslexic-font preference from the cookie set by the settings page.
  // Setting the attribute here (SSR) means the correct font is in the HTML before
  // React hydrates — no inline script needed, no React 19 script warning.
  const cookieStore = await cookies();
  const dyslexic = cookieStore.get("sb_dyslexic")?.value === "1";

  return (
    <html
      lang={locale}
      className={`${inter.variable} ${merriweather.variable} ${jetbrainsMono.variable} h-full antialiased`}
      suppressHydrationWarning
      {...(dyslexic ? { "data-dyslexic": "true" } : {})}
    >
      <body className="flex min-h-full flex-col">
        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-50 focus:rounded focus:bg-blue-600 focus:px-4 focus:py-2 focus:text-white"
        >
          Skip to main content
        </a>
        <NextIntlClientProvider messages={messages}>
          {children}
          <Toaster />
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
