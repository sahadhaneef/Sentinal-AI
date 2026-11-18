import { type ReactNode } from 'react';
import { useMotionValue, useSpring } from 'motion/react';
import { LandingSection, useLandingReducedMotion } from './LandingMotion';

export function WorkflowPanel({ children }: { children: ReactNode }) {
  const reduce = useLandingReducedMotion();
  const x = useMotionValue(0);
  const y = useMotionValue(0);
  const rotateX = useSpring(x, { stiffness: 160, damping: 26 });
  const rotateY = useSpring(y, { stiffness: 160, damping: 26 });
  const reset = () => {
    x.set(0);
    y.set(0);
  };

  return (
    <LandingSection
      className="product-section workflow-section"
      id="how-it-works"
      style={reduce ? undefined : { rotateX, rotateY, transformPerspective: 1800 }}
      onPointerMove={(event) => {
        if (reduce || event.pointerType !== 'mouse') return;
        // Keep controls steady while the user selects or plays a stage.
        if (event.target instanceof Element && event.target.closest('button, a, input, summary')) {
          reset();
          return;
        }
        const bounds = event.currentTarget.getBoundingClientRect();
        x.set(-((event.clientY - bounds.top) / bounds.height - 0.5) * 1.6);
        y.set(((event.clientX - bounds.left) / bounds.width - 0.5) * 1.6);
      }}
      onPointerLeave={reset}
      onPointerCancel={reset}
      onFocusCapture={reset}
    >
      {children}
    </LandingSection>
  );
}
