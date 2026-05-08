import React from 'react';
import { Composition } from 'remotion';
import { z } from 'zod';
import { InterferenceScene } from './scenes/InterferenceScene';
import { SingleSlitDiffractionScene } from './scenes/SingleSlitDiffractionScene';

const schema = z.object({});

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="optics-interference"
        component={InterferenceScene}
        durationInFrames={30 * 24}
        fps={30}
        width={1920}
        height={1080}
        schema={schema}
        defaultProps={{}}
      />
      <Composition
        id="optics-single-slit-diffraction"
        component={SingleSlitDiffractionScene}
        durationInFrames={30 * 24}
        fps={30}
        width={1920}
        height={1080}
        schema={schema}
        defaultProps={{}}
      />
    </>
  );
};
