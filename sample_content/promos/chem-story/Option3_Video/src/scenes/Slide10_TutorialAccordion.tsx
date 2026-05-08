import React from "react";
import { interpolate, useCurrentFrame } from "remotion";
import { SceneFrame } from "../components/SceneFrame";
import { AppFrame } from "../components/app/AppFrame";
import { TutorialPage } from "../components/app/TutorialPage";
import { ALKENES_TUTORIAL } from "../data/lesson";

/**
 * Slide 10 — tutorial accordion expanding.
 *
 * Three-step tutorial. Section 1 starts open; at frame ~180, section 2
 * also opens (animated chevron rotation handled by the TutorialPage).
 * Common-mistakes amber callout is part of the same component so it's
 * always visible at the bottom.
 */
export const Slide10_TutorialAccordion: React.FC = () => {
  const frame = useCurrentFrame();
  const fadeIn = interpolate(frame, [0, 24], [0, 1], { extrapolateRight: "clamp" });

  // Start with step 1 open. Step 2 opens at frame 180. Step 3 stays closed.
  const sections = ALKENES_TUTORIAL.sections.map((s, i) => ({
    ...s,
    open: i === 0 || (i === 1 && frame >= 180),
  }));

  return (
    <SceneFrame
      slideNumber={10}
      totalSlides={12}
      audioFile="slide-10.wav"
      caption="A tutorial section opens. Step by step. Each substep can expand for more detail."
    >
      <div style={{ position: "absolute", inset: 0, opacity: fadeIn }}>
        <AppFrame userName="Aditi K." clockTime="9:24 PM">
          <TutorialPage
            title={ALKENES_TUTORIAL.title}
            sections={sections}
            commonMistakes={ALKENES_TUTORIAL.commonMistakes}
          />
        </AppFrame>
      </div>
    </SceneFrame>
  );
};
