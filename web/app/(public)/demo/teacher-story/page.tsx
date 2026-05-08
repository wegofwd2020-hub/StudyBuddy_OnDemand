import type { Metadata } from "next";
import Link from "next/link";
import { LinkButton } from "@/components/ui/link-button";
import { Mail, Download, ArrowLeft, Clock, GraduationCap, BookOpen } from "lucide-react";

/**
 * /demo/teacher-story — Grade 11 Science Teacher user-story landing page.
 *
 * Embeds the produced MP4 of the "A Monday Morning with Linda" narrative
 * (storyboard: studybuddy-docs/docs/promos/USER_STORY_STORYBOARD.md §A,
 * production guide: studybuddy-docs/docs/promos/USER_STORY_PRODUCTION_GUIDE.md).
 *
 * The video file is served by Nginx at /content/promos/StudyBuddy_TeacherStory.mp4
 * (mapped from /data/content/promos/ on the demo VPS per scripts/demo/nginx.conf).
 *
 * Until production completes, the <video> element renders a placeholder
 * notice. Swap the `src` URL when the MP4 is uploaded.
 */

export const metadata: Metadata = {
  title: "A Monday Morning with Linda — Grade 11 Science Teacher Story",
  description:
    "How a Grade 11 Science teacher cut her Monday-morning prep from 90 minutes to 20. A 3-minute walkthrough.",
};

const VIDEO_SRC = "/content/promos/StudyBuddy_TeacherStory.mp4";
const POSTER_SRC = "/content/promos/StudyBuddy_TeacherStory_poster.jpg";
const CAPTIONS_SRC = "/content/promos/StudyBuddy_TeacherStory.en.vtt";

const MAILTO_HREF =
  "mailto:support@studybuddy.app" +
  "?subject=" +
  encodeURIComponent("Request a demo — Grade 11 Science Teacher story") +
  "&body=" +
  encodeURIComponent(
    "Hi StudyBuddy team,\n\n" +
      "I just watched the Grade 11 Science Teacher story and would like to talk about " +
      "how this could work at my school.\n\n" +
      "About my school:\n" +
      "  - Name:\n" +
      "  - Country / region:\n" +
      "  - Approximate number of teachers / students:\n" +
      "  - Stream(s) you'd like to discuss:\n\n" +
      "What I'd like to learn more about:\n  - \n\n" +
      "Best time to talk:\n  - \n\n" +
      "Thanks,\n",
  );

export default function TeacherStoryPage() {
  return (
    <main className="bg-slate-50">
      <BackLink />
      <Hero />
      <VideoSection />
      <CtaSection />
      <ContextSection />
      <FootnoteSection />
    </main>
  );
}

function BackLink() {
  return (
    <div className="mx-auto max-w-5xl px-4 pt-8">
      <Link
        href="/demo"
        className="inline-flex items-center gap-2 text-sm text-slate-600 hover:text-slate-900"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to demo home
      </Link>
    </div>
  );
}

function Hero() {
  return (
    <section className="px-4 py-16 text-center">
      <div className="mx-auto max-w-3xl">
        <div className="mb-4 inline-flex items-center gap-2 rounded-full bg-purple-100 px-4 py-1 text-sm font-medium text-purple-800">
          <GraduationCap className="h-4 w-4" />
          For teachers
        </div>
        <h1 className="text-4xl font-bold tracking-tight text-slate-900 sm:text-5xl">
          A Monday Morning with Linda
        </h1>
        <p className="mt-6 text-xl text-slate-600">
          How a Grade 11 Science teacher cut her Monday-morning prep
          from <span className="font-semibold">90 minutes to 20</span>.
        </p>
        <p className="mt-3 text-sm text-slate-500">
          A 3-minute walkthrough · with captions · download to share with
          your principal
        </p>
      </div>
    </section>
  );
}

function VideoSection() {
  return (
    <section className="px-4 pb-12">
      <div className="mx-auto max-w-4xl">
        <div className="overflow-hidden rounded-lg bg-slate-900 shadow-xl ring-1 ring-slate-200">
          <video
            controls
            preload="metadata"
            poster={POSTER_SRC}
            className="aspect-video w-full"
            // Until the MP4 is produced, the <video> element will render
            // a "Your browser does not support the video tag" message.
            // After upload, this works automatically — no code change needed.
          >
            <source src={VIDEO_SRC} type="video/mp4" />
            <track
              kind="captions"
              srcLang="en"
              src={CAPTIONS_SRC}
              label="English"
              default
            />
            Your browser does not support the video tag.
            <a href={VIDEO_SRC}>Download the video</a>
          </video>
        </div>
      </div>
    </section>
  );
}

function CtaSection() {
  return (
    <section className="px-4 pb-16">
      <div className="mx-auto flex max-w-3xl flex-col items-center justify-center gap-4 sm:flex-row">
        <a
          href={VIDEO_SRC}
          download="StudyBuddy_TeacherStory.mp4"
          className="inline-flex items-center justify-center gap-2 rounded-md border border-slate-300 bg-white px-6 py-3 text-base font-medium text-slate-700 shadow-sm hover:bg-slate-50"
        >
          <Download className="h-5 w-5" />
          Download MP4
        </a>
        <a
          href={MAILTO_HREF}
          className="inline-flex items-center justify-center gap-2 rounded-md bg-purple-600 px-6 py-3 text-base font-medium text-white shadow-sm hover:bg-purple-700"
        >
          <Mail className="h-5 w-5" />
          Request a demo
        </a>
      </div>
      <p className="mx-auto mt-3 max-w-3xl text-center text-xs text-slate-500">
        The Request-a-demo button opens your email client with a
        pre-filled message to <span className="font-mono">support@studybuddy.app</span>.
      </p>
    </section>
  );
}

function ContextSection() {
  return (
    <section className="border-t border-slate-200 bg-white px-4 py-16">
      <div className="mx-auto max-w-3xl">
        <h2 className="text-2xl font-bold text-slate-900">
          Who this is for
        </h2>
        <p className="mt-4 text-slate-600">
          Grade 11 and 12 Science teachers in schools that already have a
          curriculum and don't want to throw it out — they want their
          existing curriculum to <em>age with the world</em>. Linda's
          story is the canonical case for that.
        </p>

        <div className="mt-10 grid gap-6 sm:grid-cols-3">
          <ContextCard
            icon={<Clock className="h-6 w-6 text-purple-600" />}
            title="Less prep time"
            body="Lessons that pull current examples mean Linda's Monday-morning prep ritual shrinks from 90 minutes to 20."
          />
          <ContextCard
            icon={<BookOpen className="h-6 w-6 text-purple-600" />}
            title="Same curriculum"
            body="StudyBuddy fits her school's existing curriculum. The framework doesn't change; the examples stay current."
          />
          <ContextCard
            icon={<GraduationCap className="h-6 w-6 text-purple-600" />}
            title="Reports she trusts"
            body="At-risk students surface automatically — no spreadsheet, no guessing, just the names that need a check-in."
          />
        </div>
      </div>
    </section>
  );
}

function ContextCard({
  icon,
  title,
  body,
}: {
  icon: React.ReactNode;
  title: string;
  body: string;
}) {
  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 p-6">
      <div className="mb-3">{icon}</div>
      <h3 className="text-lg font-semibold text-slate-900">{title}</h3>
      <p className="mt-2 text-sm text-slate-600">{body}</p>
    </div>
  );
}

function FootnoteSection() {
  return (
    <section className="bg-slate-50 px-4 py-12 text-center">
      <div className="mx-auto max-w-3xl space-y-4">
        <p className="text-sm text-slate-600">
          Want to walk through Linda's day yourself?
        </p>
        <LinkButton href="/demo" size="lg" variant="secondary">
          Try the demo
        </LinkButton>
      </div>
    </section>
  );
}
