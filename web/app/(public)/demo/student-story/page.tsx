import type { Metadata } from "next";
import Link from "next/link";
import { LinkButton } from "@/components/ui/link-button";
import { Mail, Download, ArrowLeft, Sparkles, BookOpen, Clock } from "lucide-react";

/**
 * /demo/student-story — Grade 11 Science Student user-story landing page.
 *
 * Embeds the produced MP4 of the "A Study Night with Fatima" narrative
 * (storyboard: studybuddy-docs/docs/promos/USER_STORY_STORYBOARD.md §B,
 * production guide: studybuddy-docs/docs/promos/USER_STORY_PRODUCTION_GUIDE.md).
 *
 * The video file is served by Nginx at /content/promos/StudyBuddy_StudentStory.mp4
 * (mapped from /data/content/promos/ on the demo VPS per scripts/demo/nginx.conf).
 *
 * Until production completes, the <video> element renders a placeholder
 * notice. Swap the `src` URL when the MP4 is uploaded.
 */

export const metadata: Metadata = {
  title: "A Study Night with Fatima — Grade 11 Science Student Story",
  description:
    "How a Grade 11 Science student moved from re-reading the textbook to walking into class confident. A 3-minute walkthrough.",
};

const VIDEO_SRC = "/content/promos/StudyBuddy_StudentStory.mp4";
const POSTER_SRC = "/content/promos/StudyBuddy_StudentStory_poster.jpg";
const CAPTIONS_SRC = "/content/promos/StudyBuddy_StudentStory.en.vtt";

const MAILTO_HREF =
  "mailto:support@studybuddy.app" +
  "?subject=" +
  encodeURIComponent("Request a demo — Grade 11 Science Student story") +
  "&body=" +
  encodeURIComponent(
    "Hi StudyBuddy team,\n\n" +
      "I just watched the Grade 11 Science Student story and would like to talk about " +
      "how this could work for my school or my child.\n\n" +
      "I'm reaching out as a:\n" +
      "  [ ] Parent\n" +
      "  [ ] School administrator\n" +
      "  [ ] Teacher\n" +
      "  [ ] Student\n" +
      "  [ ] Other:\n\n" +
      "About me / my school:\n" +
      "  - Name:\n" +
      "  - Country / region:\n" +
      "  - Grade level(s) of interest:\n\n" +
      "What I'd like to learn more about:\n  - \n\n" +
      "Best time to talk:\n  - \n\n" +
      "Thanks,\n",
  );

export default function StudentStoryPage() {
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
        <div className="mb-4 inline-flex items-center gap-2 rounded-full bg-blue-100 px-4 py-1 text-sm font-medium text-blue-800">
          <BookOpen className="h-4 w-4" />
          For students
        </div>
        <h1 className="text-4xl font-bold tracking-tight text-slate-900 sm:text-5xl">
          A Study Night with Fatima
        </h1>
        <p className="mt-6 text-xl text-slate-600">
          From re-reading the textbook to walking into class
          <span className="font-semibold"> confident</span>.
        </p>
        <p className="mt-3 text-sm text-slate-500">
          A 3-minute walkthrough · with captions · download to share with
          your study group
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
          download="StudyBuddy_StudentStory.mp4"
          className="inline-flex items-center justify-center gap-2 rounded-md border border-slate-300 bg-white px-6 py-3 text-base font-medium text-slate-700 shadow-sm hover:bg-slate-50"
        >
          <Download className="h-5 w-5" />
          Download MP4
        </a>
        <a
          href={MAILTO_HREF}
          className="inline-flex items-center justify-center gap-2 rounded-md bg-blue-600 px-6 py-3 text-base font-medium text-white shadow-sm hover:bg-blue-700"
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
          Grade 11 and 12 Science students in their first year of stream-specific
          coursework — Physics, Chemistry, Biology — when textbooks suddenly get
          dense and the gap between "I read it" and "I understand it" widens fast.
          Fatima's story shows how StudyBuddy closes that gap.
        </p>

        <div className="mt-10 grid gap-6 sm:grid-cols-3">
          <ContextCard
            icon={<BookOpen className="h-6 w-6 text-blue-600" />}
            title="Lessons with priorities"
            body="Each lesson opens with three learning objectives. You know what to focus on before the textbook tries to drown you."
          />
          <ContextCard
            icon={<Sparkles className="h-6 w-6 text-blue-600" />}
            title="Worked examples that don't skip"
            body="Every line of algebra has a reason next to it. No leaps of logic. You read it once, then you read it again — and it sticks."
          />
          <ContextCard
            icon={<Clock className="h-6 w-6 text-blue-600" />}
            title="Time back, sleep included"
            body="A study session that gets you ready in 90 minutes is a study session that lets you sleep before the test."
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
          Want to study a unit yourself?
        </p>
        <LinkButton href="/demo" size="lg" variant="secondary">
          Try the demo
        </LinkButton>
      </div>
    </section>
  );
}
