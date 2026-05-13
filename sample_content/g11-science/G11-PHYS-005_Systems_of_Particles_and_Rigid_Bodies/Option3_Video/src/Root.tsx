import React from 'react';
import { Composition } from 'remotion';
import { z } from 'zod';
import { AngularMomentumScene } from './scenes/AngularMomentumScene';

const schema = z.object({});

const FPS = 30;
const W = 1920;
const H = 1080;

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="rigid-body-angular-momentum"
        component={AngularMomentumScene}
        durationInFrames={30 * 28}     // 28 s
        fps={FPS}
        width={W}
        height={H}
        schema={schema}
        defaultProps={{}}
      />
    </>
  );
};
