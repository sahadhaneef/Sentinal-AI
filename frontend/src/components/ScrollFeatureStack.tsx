import { Children, useRef, type CSSProperties, type ReactNode } from 'react';
import { motion, useScroll, useTransform, type MotionValue } from 'motion/react';
import { useLandingReducedMotion } from './LandingMotion';

function StackCard({ children, index, total, progress }: {
  children: ReactNode; index: number; total: number; progress: MotionValue<number>;
}) {
  const reduce = useLandingReducedMotion();
  const scale = useTransform(progress, [index / total, (index + 1) / total], [1, 0.94 + index * 0.015]);
  const rotateX = useTransform(progress, [index / total, (index + 1) / total], [0, -3]);
  return (
    <motion.div className="scroll-stack-card"
      style={{ '--stack-index': index, zIndex: index + 1, ...(reduce ? {} : { scale, rotateX, transformPerspective: 1200 }) } as CSSProperties}
    >
      <span className="scroll-stack-number" aria-hidden="true">0{index + 1} / 0{total}</span>
      {children}
    </motion.div>
  );
}

export function ScrollFeatureStack({ children }: { children: ReactNode }) {
  const container = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({ target: container, offset: ['start start', 'end end'] });
  const cards = Children.toArray(children);
  return (
    <div className="benefit-grid scroll-feature-stack" ref={container}>
      {cards.map((child, index) => (
        <StackCard key={index} index={index} total={cards.length} progress={scrollYProgress}>
          {child}
        </StackCard>
      ))}
    </div>
  );
}
