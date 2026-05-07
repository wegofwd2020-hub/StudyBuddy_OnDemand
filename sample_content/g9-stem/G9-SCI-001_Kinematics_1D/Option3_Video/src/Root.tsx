import React from 'react';
import { Composition } from 'remotion';
import { z } from 'zod';
import { MotionAlongStripScene } from './scenes/MotionAlongStripScene';

const schema = z.object({});

const FPS = 30;
const W = 1920;
const H = 1080;

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="g9-motion-along-strip"
      component={MotionAlongStripScene}
      durationInFrames={30 * 24}
      fps={FPS}
      width={W}
      height={H}
      schema={schema}
      defaultProps={{}}
    />
  );
};
