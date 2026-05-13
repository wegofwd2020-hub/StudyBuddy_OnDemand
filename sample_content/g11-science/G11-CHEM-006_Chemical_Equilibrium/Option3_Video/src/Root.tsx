import React from 'react';
import { Composition } from 'remotion';
import { z } from 'zod';
import { DynamicBalanceScene } from './scenes/DynamicBalanceScene';

const schema = z.object({});

const FPS = 30;
const W = 1920;
const H = 1080;

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="equilibrium-dynamic-balance"
        component={DynamicBalanceScene}
        durationInFrames={30 * 26}
        fps={FPS}
        width={W}
        height={H}
        schema={schema}
        defaultProps={{}}
      />
    </>
  );
};
