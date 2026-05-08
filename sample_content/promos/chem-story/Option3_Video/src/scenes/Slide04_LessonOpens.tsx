import React from "react";
import { interpolate, useCurrentFrame } from "remotion";
import { SceneFrame } from "../components/SceneFrame";
import { AppFrame } from "../components/app/AppFrame";
import { LessonPage } from "../components/app/LessonPage";
import { ALKENES_LESSON } from "../data/lesson";

/**
 * Slide 4 — lesson page opens, section 1 visible.
 *
 * The lesson card fades in within the AppFrame. Only the first section
 * ("What is an alkene?") is rendered — sections 2/3 + key-points come
 * in on slides 5/6.
 */
export const Slide04_LessonOpens: React.FC = () => {
  const frame = useCurrentFrame();
  const fadeIn = interpolate(frame, [0, 24], [0, 1], { extrapolateRight: "clamp" });

  return (
    <SceneFrame
      slideNumber={4}
      totalSlides={12}
      audioFile="slide-04.wav"
      caption="The lesson page opens. Title, the first section — what an alkene is — and a definition pitched two grades below her own."
    >
      <div style={{ position: "absolute", inset: 0, opacity: fadeIn }}>
        <AppFrame userName="Aditi K." clockTime="9:15 PM">
          <LessonPage
            title={ALKENES_LESSON.title}
            sections={ALKENES_LESSON.sections as any}
            keyPoints={ALKENES_LESSON.keyPoints as any}
            revealUpTo={0}
            showKeyPoints={false}
          />
        </AppFrame>
      </div>
    </SceneFrame>
  );
};
