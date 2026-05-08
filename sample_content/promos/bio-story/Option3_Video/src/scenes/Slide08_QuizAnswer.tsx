import React from "react";
import { interpolate, useCurrentFrame } from "remotion";
import { SceneFrame } from "../components/SceneFrame";
import { CursorTrace } from "../components/CursorTrace";
import { AppFrame } from "../components/app/AppFrame";
import { QuizPage } from "../components/app/QuizPage";
import { PHOTOSYNTHESIS_QUIZ } from "../data/lesson";

/**
 * Slide 8 — quiz page, answering phase.
 *
 * Daniel works through the chlorophyll-wavelength question. The cursor moves to
 * options A and B in turn (a brief reconsider beat), settles on B,
 * then clicks "Submit answer". This slide ends just before the
 * "reviewing" phase highlights — that lands on slide 9.
 */
export const Slide08_QuizAnswer: React.FC = () => {
  const frame = useCurrentFrame();
  const fadeIn = interpolate(frame, [0, 20], [0, 1], { extrapolateRight: "clamp" });

  // Selection state: null → null → 0 (option A, briefly) → 1 (option B)
  let selectedIndex: number | null = null;
  if (frame >= 120 && frame < 180) selectedIndex = 0;
  else if (frame >= 180) selectedIndex = 2;

  return (
    <SceneFrame
      slideNumber={8}
      totalSlides={12}
      audioFile="slide-08.wav"
      caption="Quiz time. Eight questions. He hovers on red briefly, then lands on green — that's the colour chlorophyll reflects."
    >
      <div style={{ position: "absolute", inset: 0, opacity: fadeIn }}>
        <AppFrame userName="Daniel M." clockTime="9:21 PM">
          <QuizPage
            question={PHOTOSYNTHESIS_QUIZ}
            questionIndex={3}
            totalQuestions={8}
            selectedIndex={selectedIndex}
            phase="answering"
          />
        </AppFrame>
      </div>

      {/* Cursor: hover near top-right, dip to A, then to B, then to Submit */}
      <CursorTrace
        path={[
          { x: 1700, y: 200, atFrame: 60 },
          { x: 660, y: 510, atFrame: 130 },  // option A (Red)
          { x: 660, y: 510, atFrame: 175 },
          { x: 660, y: 650, atFrame: 200 },  // option C (Green)
          { x: 660, y: 650, atFrame: 270 },
          { x: 1320, y: 800, atFrame: 360 }, // Submit answer button
        ]}
        clickAt={350}
      />
    </SceneFrame>
  );
};
