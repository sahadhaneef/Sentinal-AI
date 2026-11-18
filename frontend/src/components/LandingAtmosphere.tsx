import { useEffect, useState } from 'react';
import { useLandingReducedMotion } from './LandingMotion';
import { PlanetBackdrop } from './PlanetBackdrop';

export function LandingAtmosphere() {
  const [visible, setVisible] = useState(() => !document.hidden);
  const reduce = useLandingReducedMotion();
  useEffect(() => {
    const update = () => setVisible(!document.hidden);
    document.addEventListener('visibilitychange', update);
    return () => document.removeEventListener('visibilitychange', update);
  }, []);
  return (
    <>
      <div
        className="landing-atmosphere"
        aria-hidden="true"
        data-running={visible && !reduce}
      >
        <PlanetBackdrop running={visible && !reduce} />
      </div>
    </>
  );
}
