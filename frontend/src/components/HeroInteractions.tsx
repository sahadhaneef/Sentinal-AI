import { type PointerEvent, type ReactNode } from 'react';
import { motion, useMotionValue, useSpring } from 'motion/react';
import { Link } from 'react-router-dom';
import { ProductVisual } from './ProductVisual';
import { useLandingReducedMotion } from './LandingMotion';

const MotionLink = motion.create(Link);
const spring = { stiffness: 180, damping: 24, mass: 0.7 };

export function HeroPreview() {
  const reduce = useLandingReducedMotion();
  const x = useMotionValue(0);
  const y = useMotionValue(0);
  const rotateX = useSpring(x, spring);
  const rotateY = useSpring(y, spring);
  const reset = () => {
    x.set(0);
    y.set(0);
  };
  const tilt = (event: PointerEvent<HTMLDivElement>) => {
    if (reduce || event.pointerType !== 'mouse') return;
    const bounds = event.currentTarget.getBoundingClientRect();
    x.set(-((event.clientY - bounds.top) / bounds.height - 0.5) * 5);
    y.set(((event.clientX - bounds.left) / bounds.width - 0.5) * 5);
  };

  return (
    <motion.div
      className="hero-preview-entrance"
      initial={reduce ? false : { opacity: 0, y: 24, rotate: -1 }}
      whileInView={{ opacity: 1, y: 0, rotate: 0 }}
      viewport={{ once: true, amount: 0.2 }}
      transition={{ duration: 0.85, ease: [0.22, 1, 0.36, 1] }}
    >
      <motion.div
        className="hero-preview-shell"
        style={reduce ? undefined : { rotateX, rotateY, transformPerspective: 1000 }}
        whileHover={reduce ? undefined : { y: -6 }}
        transition={spring}
        onPointerMove={tilt}
        onPointerLeave={reset}
        onPointerCancel={reset}
      >
        <ProductVisual />
      </motion.div>
    </motion.div>
  );
}

export function HeroButton({
  to,
  primary,
  children,
}: {
  to: string;
  primary?: boolean;
  children: ReactNode;
}) {
  const reduce = useLandingReducedMotion();
  const x = useMotionValue(0);
  const y = useMotionValue(0);
  const springX = useSpring(x, spring);
  const springY = useSpring(y, spring);
  const reset = () => {
    x.set(0);
    y.set(0);
  };

  return (
    <MotionLink
      to={to}
      className={`button hero-motion-button${primary ? ' primary' : ''}`}
      style={reduce ? undefined : { x: springX, y: springY }}
      whileHover={reduce ? undefined : { scale: 1.025 }}
      whileFocus={reduce ? undefined : { scale: 1.025 }}
      whileTap={reduce ? undefined : { scale: 0.97 }}
      transition={spring}
      onPointerMove={(event) => {
        if (reduce || event.pointerType !== 'mouse') return;
        const bounds = event.currentTarget.getBoundingClientRect();
        x.set(((event.clientX - bounds.left) / bounds.width - 0.5) * 7);
        y.set(((event.clientY - bounds.top) / bounds.height - 0.5) * 5);
      }}
      onPointerLeave={reset}
      onPointerCancel={reset}
      onBlur={reset}
    >
      {children}
    </MotionLink>
  );
}
