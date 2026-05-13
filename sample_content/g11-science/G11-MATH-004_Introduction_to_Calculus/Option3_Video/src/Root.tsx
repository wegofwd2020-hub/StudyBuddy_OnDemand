import React from 'react';
import { Composition } from 'remotion';
import { z } from 'zod';
import { SecantToTangentScene } from './scenes/SecantToTangentScene';

const schema = z.object({});

const FPS = 30;
const W = 1920;
const H = 1080;

// 5 stages × 150 frames + 60-frame outro = 810 frames ≈ 27 s @ 30fps.
const TOTAL_FRAMES = 810;

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="calculus-secant-to-tangent"
        component={SecantToTangentScene}
        durationInFrames={TOTAL_FRAMES}
        fps={FPS}
        width={W}
        height={H}
        schema={schema}
        defaultProps={{}}
      />
    </>
  );
};
