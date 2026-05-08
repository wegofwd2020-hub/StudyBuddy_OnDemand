import React from "react";
import { Composition, Sequence } from "remotion";
import { z } from "zod";

import { Slide01_TitleCard } from "./scenes/Slide01_TitleCard";
import { Slide02_LindaAsks } from "./scenes/Slide02_LindaAsks";
import { Slide03_ScopingHexagon } from "./scenes/Slide03_ScopingHexagon";
import { Slide04_LessonText } from "./scenes/Slide04_LessonText";
import { Slide05_LessonImages } from "./scenes/Slide05_LessonImages";
import { Slide06_LessonVideo } from "./scenes/Slide06_LessonVideo";
import { Slide07_LessonQuiz } from "./scenes/Slide07_LessonQuiz";
import { Slide08_TutorialSection } from "./scenes/Slide08_TutorialSection";
import { Slide09_StreamMontage } from "./scenes/Slide09_StreamMontage";
import { Slide10_AtRiskReports } from "./scenes/Slide10_AtRiskReports";
import { Slide11_Accessibility } from "./scenes/Slide11_Accessibility";
import { Slide12_CallToAction } from "./scenes/Slide12_CallToAction";
import { FPS, SLIDE_DURATION_FRAMES } from "./theme";

const schema = z.object({});

const W = 1920;
const H = 1080;
const TOTAL_SLIDES = 12;
const TOTAL_FRAMES = TOTAL_SLIDES * SLIDE_DURATION_FRAMES;

/**
 * Root composition: 12 sequential slides, each 16s × 30fps = 480 frames.
 * Total runtime = 192 seconds = 3:12.
 *
 * Per slide structure (handled inside SceneFrame):
 *   frames 0–14    : visual settle (caption fades in over frames 15–30)
 *   frames 30–450  : main narration window
 *   frames 450–480 : caption holds, scene fades to black
 */
const Story: React.FC = () => {
  return (
    <>
      <Sequence from={0 * SLIDE_DURATION_FRAMES} durationInFrames={SLIDE_DURATION_FRAMES}>
        <Slide01_TitleCard />
      </Sequence>
      <Sequence from={1 * SLIDE_DURATION_FRAMES} durationInFrames={SLIDE_DURATION_FRAMES}>
        <Slide02_LindaAsks />
      </Sequence>
      <Sequence from={2 * SLIDE_DURATION_FRAMES} durationInFrames={SLIDE_DURATION_FRAMES}>
        <Slide03_ScopingHexagon />
      </Sequence>
      <Sequence from={3 * SLIDE_DURATION_FRAMES} durationInFrames={SLIDE_DURATION_FRAMES}>
        <Slide04_LessonText />
      </Sequence>
      <Sequence from={4 * SLIDE_DURATION_FRAMES} durationInFrames={SLIDE_DURATION_FRAMES}>
        <Slide05_LessonImages />
      </Sequence>
      <Sequence from={5 * SLIDE_DURATION_FRAMES} durationInFrames={SLIDE_DURATION_FRAMES}>
        <Slide06_LessonVideo />
      </Sequence>
      <Sequence from={6 * SLIDE_DURATION_FRAMES} durationInFrames={SLIDE_DURATION_FRAMES}>
        <Slide07_LessonQuiz />
      </Sequence>
      <Sequence from={7 * SLIDE_DURATION_FRAMES} durationInFrames={SLIDE_DURATION_FRAMES}>
        <Slide08_TutorialSection />
      </Sequence>
      <Sequence from={8 * SLIDE_DURATION_FRAMES} durationInFrames={SLIDE_DURATION_FRAMES}>
        <Slide09_StreamMontage />
      </Sequence>
      <Sequence from={9 * SLIDE_DURATION_FRAMES} durationInFrames={SLIDE_DURATION_FRAMES}>
        <Slide10_AtRiskReports />
      </Sequence>
      <Sequence from={10 * SLIDE_DURATION_FRAMES} durationInFrames={SLIDE_DURATION_FRAMES}>
        <Slide11_Accessibility />
      </Sequence>
      <Sequence from={11 * SLIDE_DURATION_FRAMES} durationInFrames={SLIDE_DURATION_FRAMES}>
        <Slide12_CallToAction />
      </Sequence>
    </>
  );
};

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="teacher-story"
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
