import demoVideos from "@/data/demo-videos.json";

type SampleVisual = {
  slug: string;
  label: string;
  alt: string;
  src: string;
};

const SAMPLE_VISUALS = demoVideos.sample_visuals as SampleVisual[];

type Props = {
  title?: string;
  subtitle?: string;
};

export function SampleVisuals({
  title = "Visuals from real lessons",
  subtitle = "StudyBuddy renders concept-specific visuals as part of every lesson. These are real organic-chemistry visuals from the Grade 11 Science curriculum.",
}: Props) {
  return (
    <section className="bg-gray-50 px-4 py-16">
      <div className="mx-auto max-w-5xl">
        <div className="text-center">
          <h2 className="text-2xl font-bold text-gray-900 sm:text-3xl">{title}</h2>
          <p className="mx-auto mt-2 max-w-2xl text-base text-gray-600">{subtitle}</p>
        </div>
        <div className="mt-10 grid grid-cols-2 gap-4 md:grid-cols-4">
          {SAMPLE_VISUALS.map((visual) => (
            <figure
              key={visual.slug}
              className="overflow-hidden rounded-lg border border-gray-200 bg-white"
            >
              <video
                src={visual.src}
                autoPlay
                loop
                muted
                playsInline
                preload="metadata"
                className="aspect-square w-full bg-gray-100 object-cover"
                aria-label={visual.alt}
              >
                Your browser doesn&apos;t support HTML5 video.
              </video>
              <figcaption className="p-2.5 text-center font-mono text-xs text-gray-500">
                {visual.label}
              </figcaption>
            </figure>
          ))}
        </div>
      </div>
    </section>
  );
}
