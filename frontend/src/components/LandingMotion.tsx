import { motion, useReducedMotion, type HTMLMotionProps } from 'motion/react';
import { usePreferences } from '../app/preferences';

export function useLandingReducedMotion() {
  const system = useReducedMotion();
  const { preferences } = usePreferences();
  return Boolean(system || preferences.motion === 'reduce');
}

export function LandingSection(props: HTMLMotionProps<'section'>) {
  const reduce = useLandingReducedMotion();
  return (
    <motion.section
      initial={reduce ? false : { opacity: 0, y: 24 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, amount: 0.08 }}
      transition={{ duration: 0.65, ease: [0.22, 1, 0.36, 1] }}
      {...props}
    />
  );
}
