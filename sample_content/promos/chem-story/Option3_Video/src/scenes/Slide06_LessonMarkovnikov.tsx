import React from "react";
import { interpolate, useCurrentFrame } from "remotion";
import { SceneFrame } from "../components/SceneFrame";
import { AppFrame } from "../components/app/AppFrame";
import { LessonPage } from "../components/app/LessonPage";
import { ALKENES_LESSON } from "../data/lesson";

/**
 * Slide 6 — section 3 "Markovnikov's rule" + Key Points reveal.
 *
 * Final lesson section types in, then the blue Key Points callout
 * fades in below it. Page is scrolled so Markovnikov's rule + key
 * points are visible together.
 */
export const Slide06_LessonMarkovnikov: React.FC = () => {
  const frame = useCurrentFrame();
  const scrollOffset = interpolate(frame, [0, 60], [-120, -360], { extrapolateRight: "clamp" });
  const showKeyPoints = frame >= 240;

  return (
    <SceneFrame
      slideNumber={6}
      totalSlides={12}
      audioFile="slide-06.wav"
      caption="Markovnikov's rule. The rich get richer — the heavy fragment lands on the more substituted carbon."
    >
      <div style={{ position: "absolute", inset: 0 }}>
        <AppFrame userName="Aditi K." clockTime="9:17 PM">
          <LessonPage
            title="Reactions of Alkenes"
            sections={ALKENES_LESSON.sections as any}
            keyPoints={ALKENES_LESSON.keyPoints as any}
            revealUpTo={2}
            showKeyPoints={showKeyPoints}
            scrollOffsetPx={scrollOffset}
          />
        </AppFrame>
      </div>
    </SceneFrame>
  );
};
