import React from "react";
import { Composition, Sequence } from "remotion";
import { z } from "zod";

import { Slide01_TitleCard } from "./scenes/Slide01_TitleCard";
import { Slide02_MeetAditi } from "./scenes/Slide02_MeetAditi";
import { Slide03_Dashboard } from "./scenes/Slide03_Dashboard";
import { Slide04_LessonOpens } from "./scenes/Slide04_LessonOpens";
import { Slide05_LessonAddition } from "./scenes/Slide05_LessonAddition";
import { Slide06_LessonMarkovnikov } from "./scenes/Slide06_LessonMarkovnikov";
import { Slide07_ReactionDiagram } from "./scenes/Slide07_ReactionDiagram";
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
    Slide02_MeetAditi,
    Slide03_Dashboard,
    Slide04_LessonOpens,
    Slide05_LessonAddition,
    Slide06_LessonMarkovnikov,
    Slide07_ReactionDiagram,
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
      id="chem-story"
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
