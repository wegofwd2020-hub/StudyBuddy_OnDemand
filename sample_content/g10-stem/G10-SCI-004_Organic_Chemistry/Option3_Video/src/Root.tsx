import React from "react";
import { Composition } from "remotion";
import { z } from "zod";

import { SingleBondScene } from "./scenes/SingleBondScene";
import { DoubleBondScene } from "./scenes/DoubleBondScene";
import { TripleBondScene } from "./scenes/TripleBondScene";
import { AromaticBenzeneScene } from "./scenes/AromaticBenzeneScene";
import { FPS, SCENE_DURATION_FRAMES } from "./theme";

const schema = z.object({});
const W = 1920;
const H = 1080;

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="hydrocarbon-single-bond"
        component={SingleBondScene}
        durationInFrames={SCENE_DURATION_FRAMES}
        fps={FPS}
        width={W}
        height={H}
        schema={schema}
        defaultProps={{}}
      />
      <Composition
        id="hydrocarbon-double-bond"
        component={DoubleBondScene}
        durationInFrames={SCENE_DURATION_FRAMES}
        fps={FPS}
        width={W}
        height={H}
        schema={schema}
        defaultProps={{}}
      />
      <Composition
        id="hydrocarbon-triple-bond"
        component={TripleBondScene}
        durationInFrames={SCENE_DURATION_FRAMES}
        fps={FPS}
        width={W}
        height={H}
        schema={schema}
        defaultProps={{}}
      />
      <Composition
        id="hydrocarbon-aromatic"
        component={AromaticBenzeneScene}
        durationInFrames={SCENE_DURATION_FRAMES}
        fps={FPS}
        width={W}
        height={H}
        schema={schema}
        defaultProps={{}}
      />
    </>
  );
};
