import React from "react";
import { Composition, Sequence } from "remotion";
import { z } from "zod";

import { Slide01_TitleCard } from "./scenes/Slide01_TitleCard";
import { Slide02_MeetDaniel } from "./scenes/Slide02_MeetDaniel";
import { Slide03_Dashboard } from "./scenes/Slide03_Dashboard";
import { Slide04_LessonOpens } from "./scenes/Slide04_LessonOpens";
import { Slide05_LessonLight } from "./scenes/Slide05_LessonLight";
import { Slide06_LessonCalvin } from "./scenes/Slide06_LessonCalvin";
import { Slide07_PigmentSpectrum } from "./scenes/Slide07_PigmentSpectrum";
import { Slide08_QuizAnswer } from "./scenes/Slide08_QuizAnswer";
import { Slide09_QuizFeedback } from "./scenes/Slide09_QuizFeedback";
import { Slide10_TutorialAccordion } from "./scenes/Slide10_TutorialAccordion";
import { Slide11_StreakAccessibility } from "./scenes/Slide11_StreakAccessibility";
import { Slide12_CallToAction } from "./scenes/Slide12_CallToAction";
import { FPS, SLIDE_DURATION_FRAMES } from "./theme";

const schema = z.object({});

const W = 1920;
const H = 1080;
const TOTAL_SLIDES = 12;
const TOTAL_FRAMES = TOTAL_SLIDES * SLIDE_DURATION_FRAMES;

const Story: React.FC = () => {
  const slides = [
    Slide01_TitleCard,
    Slide02_MeetDaniel,
    Slide03_Dashboard,
    Slide04_LessonOpens,
    Slide05_LessonLight,
    Slide06_LessonCalvin,
    Slide07_PigmentSpectrum,
    Slide08_QuizAnswer,
    Slide09_QuizFeedback,
    Slide10_TutorialAccordion,
    Slide11_StreakAccessibility,
    Slide12_CallToAction,
  ];

  return (
    <>
      {slides.map((Scene, i) => (
        <Sequence key={i} from={i * SLIDE_DURATION_FRAMES} durationInFrames={SLIDE_DURATION_FRAMES}>
          <Scene />
        </Sequence>
      ))}
    </>
  );
};

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="bio-story"
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
