import React from 'react';
import { Composition } from 'remotion';
import { z } from 'zod';
import { CardiacCycleScene } from './scenes/CardiacCycleScene';

const schema = z.object({});

const FPS = 30;
const W = 1920;
const H = 1080;

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="physiol-cardiac-cycle"
        component={CardiacCycleScene}
        durationInFrames={30 * 28}
        fps={FPS}
        width={W}
        height={H}
        schema={schema}
        defaultProps={{}}
      />
    </>
  );
};
