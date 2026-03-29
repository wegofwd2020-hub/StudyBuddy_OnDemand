import type { Metadata } from "next";
import { Nunito, Lora, Geist_Mono } from "next/font/google";
import Script from "next/script";
import { NextIntlClientProvider } from "next-intl";
import { getLocale, getMessages } from "next-intl/server";
import { Toaster } from "@/components/ui/sonner";
import "./globals.css";

// Headings — Sans Serif (clear, scannable, modern)
const nunito = Nunito({
  variable: "--font-nunito",
  subsets: ["latin"],
  display: "swap",
});

// Body text — Serif (warm, readable for longer content)
const lora = Lora({
  variable: "--font-lora",
  subsets: ["latin"],
  display: "swap",
});

// Code / monospace
const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  title: {
    default: "StudyBuddy \u2014 STEM tutoring for Grades 5\u201312",
    template: "%s | StudyBuddy",
  },
  description:
    "Instant AI-powered lessons, quizzes, and audio for STEM subjects. Available in English, French, and Spanish.",
};

export default async function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  const locale = await getLocale();
  const messages = await getMessages();

  return (
    <html
      lang={locale}
      className={`${nunito.variable} ${lora.variable} ${geistMono.variable} h-full antialiased`}
      suppressHydrationWarning
    >
      <head>
        {/* Reads localStorage before React hydrates — prevents dyslexic font flash on reload */}
        <Script
          id="dyslexic-font-init"
          strategy="beforeInteractive"
          dangerouslySetInnerHTML={{
            __html: `(function(){try{if(localStorage.getItem('sb_dyslexic')==='1'){document.documentElement.setAttribute('data-dyslexic','true')}}catch(e){}})()`,
          }}
        />
      </head>
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
