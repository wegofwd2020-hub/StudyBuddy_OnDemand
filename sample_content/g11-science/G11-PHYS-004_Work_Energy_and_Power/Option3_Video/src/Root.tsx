import React from 'react';
import { Composition } from 'remotion';
import { z } from 'zod';
import { RollerCoasterScene } from './scenes/RollerCoasterScene';

const schema = z.object({});

const FPS = 30;
const W = 1920;
const H = 1080;

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="work-energy-roller-coaster"
        component={RollerCoasterScene}
        durationInFrames={30 * 32}     // 32 s
        fps={FPS}
        width={W}
        height={H}
        schema={schema}
        defaultProps={{}}
      />
    </>
  );
};
