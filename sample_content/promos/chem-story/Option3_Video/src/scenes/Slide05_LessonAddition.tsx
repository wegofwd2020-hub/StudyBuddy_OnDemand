import React from "react";
import { interpolate, useCurrentFrame } from "remotion";
import { SceneFrame } from "../components/SceneFrame";
import { AppFrame } from "../components/app/AppFrame";
import { LessonPage } from "../components/app/LessonPage";
import { ALKENES_LESSON } from "../data/lesson";

/**
 * Slide 5 — section 2 "Electrophilic addition" appears.
 *
 * Lesson page now reveals through section 2. Page scrolls slightly
 * upward to keep the new content centred in the viewport (simulating
 * the natural reading scroll).
 */
export const Slide05_LessonAddition: React.FC = () => {
  const frame = useCurrentFrame();
  // Smooth scroll the article up by ~120 px as section 2 renders, so
  // the new content sits centred rather than below the fold.
  const scrollOffset = interpolate(frame, [30, 90], [0, -120], { extrapolateRight: "clamp" });

  return (
    <SceneFrame
      slideNumber={5}
      totalSlides={12}
      audioFile="slide-05.wav"
      caption="Electrophilic addition — the defining reaction class. Hydrogen, HBr, water, bromine: all add across the double bond."
    >
      <div style={{ position: "absolute", inset: 0 }}>
        <AppFrame userName="Aditi K." clockTime="9:16 PM">
          <LessonPage
            title="Reactions of Alkenes"
            sections={ALKENES_LESSON.sections as any}
            keyPoints={ALKENES_LESSON.keyPoints as any}
            revealUpTo={1}
            showKeyPoints={false}
            scrollOffsetPx={scrollOffset}
          />
        </AppFrame>
      </div>
    </SceneFrame>
  );
};
