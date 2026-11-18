import { useEffect, useRef, useState, type ReactNode } from 'react';
import { motion, useInView, useMotionValue, useSpring } from 'motion/react';
import { LandingSection, useLandingReducedMotion } from './LandingMotion';

export function HeroScene({ children }: { children: ReactNode }) {
  const container = useRef<HTMLDivElement>(null);
  const inView = useInView(container, { amount: 'some' });
  const [visible, setVisible] = useState(() => !document.hidden);
  const reduce = useLandingReducedMotion();
  // Move one prepainted radial layer; pointer updates never rerender React.
  const pointerX = useMotionValue(0);
  const pointerY = useMotionValue(0);
  const presence = useMotionValue(0);
  const x = useSpring(pointerX, { stiffness: 120, damping: 30 });
  const y = useSpring(pointerY, { stiffness: 120, damping: 30 });
  const opacity = useSpring(presence, { stiffness: 100, damping: 25 });
  useEffect(() => {
    const update = () => setVisible(!document.hidden);
    document.addEventListener('visibilitychange', update);
    return () => document.removeEventListener('visibilitychange', update);
  }, []);
  return (
    <div className="hero-scene" ref={container} data-running={inView && visible && !reduce}
      onPointerMove={(event) => {
        if (reduce || event.pointerType !== 'mouse' || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
        const bounds = event.currentTarget.getBoundingClientRect();
        pointerX.set(event.clientX - bounds.left - 320);
        pointerY.set(event.clientY - bounds.top - 320);
        presence.set(1);
      }}
      onPointerLeave={() => presence.set(0)}
      onPointerCancel={() => presence.set(0)}
    >
      <div className="hero-scene-background" aria-hidden="true">
        <motion.div className="hero-cursor-light" style={{ x, y, opacity }} />
        <div className="hero-reading-veil" />
      </div>
      <LandingSection className="landing-hero">{children}</LandingSection>
    </div>
  );
}
