import React from "react";
import { Composition, Sequence } from "remotion";
import { z } from "zod";

import { Slide01_TitleCard } from "./scenes/Slide01_TitleCard";
import { Slide02_MeetMaya } from "./scenes/Slide02_MeetMaya";
import { Slide03_LayerText } from "./scenes/Slide03_LayerText";
import { Slide04_LayerImages } from "./scenes/Slide04_LayerImages";
import { Slide05_LayerAnimation } from "./scenes/Slide05_LayerAnimation";
import { Slide06_LayerQuiz } from "./scenes/Slide06_LayerQuiz";
import { Slide07_LayerTutorial } from "./scenes/Slide07_LayerTutorial";
import { Slide08_LayersTogether } from "./scenes/Slide08_LayersTogether";
import { Slide09_StreakCounter } from "./scenes/Slide09_StreakCounter";
import { Slide10_Accessibility } from "./scenes/Slide10_Accessibility";
import { Slide11_ScopedToHer } from "./scenes/Slide11_ScopedToHer";
import { Slide12_CallToAction } from "./scenes/Slide12_CallToAction";
import { FPS, SLIDE_DURATION_FRAMES } from "./theme";

const schema = z.object({});

const W = 1920;
const H = 1080;
const TOTAL_SLIDES = 12;
const TOTAL_FRAMES = TOTAL_SLIDES * SLIDE_DURATION_FRAMES;

/**
 * Student-story root composition. Same 12-slide × 16-second cadence
 * as the teacher story so audio + caption timings are interchangeable.
 */
const Story: React.FC = () => {
  const slides = [
    Slide01_TitleCard,
    Slide02_MeetMaya,
    Slide03_LayerText,
    Slide04_LayerImages,
    Slide05_LayerAnimation,
    Slide06_LayerQuiz,
    Slide07_LayerTutorial,
    Slide08_LayersTogether,
    Slide09_StreakCounter,
    Slide10_Accessibility,
    Slide11_ScopedToHer,
    Slide12_CallToAction,
  ];

  return (
    <>
      {slides.map((Scene, i) => (
        <Sequence
          key={i}
          from={i * SLIDE_DURATION_FRAMES}
          durationInFrames={SLIDE_DURATION_FRAMES}
        >
          <Scene />
        </Sequence>
      ))}
    </>
  );
};

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="student-story"
      component={Story}
      durationInFrames={TOTAL_FRAMES}
      fps={FPS}
      width={W}
      height={H}
      schema={schema}
      defaultProps={{}}
    />
  );
};
