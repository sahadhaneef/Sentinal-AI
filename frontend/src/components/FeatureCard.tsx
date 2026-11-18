import { type ReactNode } from 'react';
import { motion, useMotionValue, useSpring } from 'motion/react';
import { useLandingReducedMotion } from './LandingMotion';

const spring = { type: 'spring' as const, stiffness: 180, damping: 24, mass: 0.7 };

export function FeatureCard({
  children,
  index,
  className = 'benefit-card',
  decoration,
  motionStyle = 'tilt',
  reveal = true,
}: {
  children: ReactNode;
  index: number;
  className?: string;
  decoration?: ReactNode;
  motionStyle?: 'tilt' | 'signal';
  reveal?: boolean;
}) {
  const reduce = useLandingReducedMotion();
  const x = useMotionValue(0);
  const y = useMotionValue(0);
  const rotateX = useSpring(x, spring);
  const rotateY = useSpring(y, spring);
  const reset = () => {
    x.set(0);
    y.set(0);
  };

  return (
    <motion.article
      className={className}
      initial={reduce || !reveal ? false : motionStyle === 'signal' ? { opacity: 0, x: index % 2 ? 18 : -18 } : { opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0, x: 0 }}
      whileHover={reduce ? undefined : motionStyle === 'signal' ? { scale: 1.012 } : { y: -7 }}
      viewport={{ once: true, amount: 0.3 }}
      style={reduce || motionStyle === 'signal' ? undefined : { rotateX, rotateY, transformPerspective: 1000 }}
      transition={{
        opacity: { duration: 0.5, delay: (index % 2) * 0.06 },
        y: spring,
      }}
      onPointerMove={(event) => {
        if (reduce || motionStyle === 'signal' || event.pointerType !== 'mouse') return;
        if (event.target instanceof Element && event.target.closest('summary, button, a')) {
          reset();
          return;
        }
        const bounds = event.currentTarget.getBoundingClientRect();
        x.set(-((event.clientY - bounds.top) / bounds.height - 0.5) * 6);
        y.set(((event.clientX - bounds.left) / bounds.width - 0.5) * 6);
      }}
      onPointerLeave={reset}
      onPointerCancel={reset}
      onFocusCapture={reset}
    >
      {decoration}
      <div className="benefit-card-content">{children}</div>
    </motion.article>
  );
}
