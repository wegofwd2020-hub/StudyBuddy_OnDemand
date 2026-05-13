import React from 'react';
import { Composition } from 'remotion';
import { z } from 'zod';
import { QuadraticTransformScene } from './scenes/QuadraticTransformScene';

const schema = z.object({});

const FPS = 30;
const W = 1920;
const H = 1080;

// 5 transformation steps × 150 frames = 750 frames + 30 frame outro = 780 frames ≈ 26s @ 30fps
const TOTAL_FRAMES = 30 * 26;

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="advanced-algebra-quadratic-transform"
        component={QuadraticTransformScene}
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
