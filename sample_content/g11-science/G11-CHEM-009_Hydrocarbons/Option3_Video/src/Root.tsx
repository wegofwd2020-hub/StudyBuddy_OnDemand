import React from 'react';
import { Composition } from 'remotion';
import { z } from 'zod';
import { MarkovnikovAdditionScene } from './scenes/MarkovnikovAdditionScene';

const schema = z.object({});

const FPS = 30;
const W = 1920;
const H = 1080;

// 28 s @ 30 fps = 840 frames
const DURATION_FRAMES = 30 * 28;

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="hydrocarbons-markovnikov-addition"
        component={MarkovnikovAdditionScene}
        durationInFrames={DURATION_FRAMES}
        fps={FPS}
        width={W}
        height={H}
        schema={schema}
        defaultProps={{}}
      />
    </>
  );
};
