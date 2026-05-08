import React from "react";
import { interpolate, useCurrentFrame } from "remotion";
import { SceneFrame } from "../components/SceneFrame";
import { AppFrame } from "../components/app/AppFrame";
import { QuizPage } from "../components/app/QuizPage";
import { ALKENES_QUIZ } from "../data/lesson";

/**
 * Slide 9 — quiz reviewing phase.
 *
 * Same QuizPage instance, but with phase="reviewing" — option B is
 * ringed green, the explanation panel slides in below. No cursor
 * activity; this is the "got it" moment.
 */
export const Slide09_QuizFeedback: React.FC = () => {
  const frame = useCurrentFrame();
  const fadeIn = interpolate(frame, [0, 24], [0, 1], { extrapolateRight: "clamp" });

  return (
    <SceneFrame
      slideNumber={9}
      totalSlides={12}
      audioFile="slide-09.wav"
      caption="Correct. The explanation tells her why — Markovnikov's rule, in two short sentences."
    >
      <div style={{ position: "absolute", inset: 0, opacity: fadeIn }}>
        <AppFrame userName="Aditi K." clockTime="9:22 PM">
          <QuizPage
            question={ALKENES_QUIZ}
            questionIndex={3}
            totalQuestions={8}
            selectedIndex={1}
            phase="reviewing"
          />
        </AppFrame>
      </div>
    </SceneFrame>
  );
};
