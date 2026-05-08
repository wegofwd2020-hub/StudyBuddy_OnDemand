import React from "react";
import { interpolate, useCurrentFrame } from "remotion";
import { SceneFrame } from "../components/SceneFrame";
import { AppFrame } from "../components/app/AppFrame";
import { LessonPage } from "../components/app/LessonPage";
import { PHOTOSYNTHESIS_LESSON } from "../data/lesson";

/**
 * Slide 6 — section 3 "The Calvin cycle" + Key Points reveal.
 *
 * Final lesson section types in, then the blue Key Points callout
 * fades in below it. Page is scrolled so the Calvin cycle + key
 * points are visible together.
 */
export const Slide06_LessonCalvin: React.FC = () => {
  const frame = useCurrentFrame();
  const scrollOffset = interpolate(frame, [0, 60], [-120, -360], { extrapolateRight: "clamp" });
  const showKeyPoints = frame >= 240;

  return (
    <SceneFrame
      slideNumber={6}
      totalSlides={12}
      audioFile="slide-06.wav"
      caption="Stage two — the Calvin cycle. RuBisCO grabs CO₂. ATP and NADPH from stage one fuel the assembly of glucose."
    >
      <div style={{ position: "absolute", inset: 0 }}>
        <AppFrame userName="Daniel M." clockTime="9:17 PM">
          <LessonPage
            title="Photosynthesis"
            sections={PHOTOSYNTHESIS_LESSON.sections as any}
            keyPoints={PHOTOSYNTHESIS_LESSON.keyPoints as any}
            revealUpTo={2}
            showKeyPoints={showKeyPoints}
            scrollOffsetPx={scrollOffset}
          />
        </AppFrame>
      </div>
    </SceneFrame>
  );
};
