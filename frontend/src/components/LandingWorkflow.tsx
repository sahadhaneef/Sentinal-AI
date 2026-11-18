import { useEffect, useRef, useState } from 'react';
import { AnimatePresence, motion, useInView } from 'motion/react';
import { ArrowRight, Network, ShieldCheck } from 'lucide-react';
import { stages } from '../content/product';
import { useLandingReducedMotion } from './LandingMotion';

export function LandingWorkflow() {
  const [stage, setStage] = useState(0);
  const [reading, setReading] = useState(false);
  const [tabVisible, setTabVisible] = useState(!document.hidden);
  const reduce = useLandingReducedMotion();
  const container = useRef<HTMLDivElement>(null);
  const visible = useInView(container, { amount: 'some' });
  const active = !reading && tabVisible && !reduce;
  const selected = stages[stage];

  useEffect(() => {
    if (!active || !visible) return;
    const timer = window.setTimeout(() => {
      setStage((current) => (current + 1) % stages.length);
    }, 5000);
    return () => window.clearTimeout(timer);
  }, [active, stage, visible]);

  useEffect(() => {
    const pause = () => setTabVisible(!document.hidden);
    document.addEventListener('visibilitychange', pause);
    return () => document.removeEventListener('visibilitychange', pause);
  }, []);

  return (
    <div className="workflow-experience" ref={container}
      data-running={active && visible}
      onPointerEnter={(event) => { if (event.pointerType === 'mouse') setReading(true); }}
      onPointerLeave={() => setReading(false)}
      onFocusCapture={() => setReading(true)}
      onBlurCapture={(event) => {
        if (!event.currentTarget.contains(event.relatedTarget)) setReading(false);
      }}
    >
      <div className="workflow-toolbar">
        <div className="coordinator-label">
          <Network size={20} aria-hidden />
          <div>
            <strong>Manager Agent</strong>
            <span>Coordinates every handoff</span>
          </div>
        </div>
        <span className="workflow-loop-label">
          <span aria-hidden="true" />
          {reduce ? 'Explore each stage' : reading ? 'Explore at your own pace' : 'Illustrated workflow · auto loop'}
        </span>
      </div>
      <div className="public-workflow" role="group" aria-label="Explore workflow stages">
        {stages.map((item, index) => (
          <motion.div
            className="workflow-stage-slot"
            data-stage={index}
            key={item.name}
            initial={reduce ? false : { opacity: 0, y: 12 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, amount: 0.2 }}
            transition={{ duration: 0.4, delay: index * 0.045, ease: [0.22, 1, 0.36, 1] }}
          >
            <motion.button
              className={index < stage ? 'stage-complete' : ''}
              aria-pressed={stage === index}
              animate={{ y: reduce ? 0 : stage === index ? -3 : 0 }}
              whileHover={reduce ? undefined : { y: -6, scale: 1.025 }}
              whileFocus={reduce ? undefined : { y: -6, scale: 1.025 }}
              whileTap={reduce ? undefined : { y: -1, scale: 0.98 }}
              transition={{ type: 'spring', stiffness: 240, damping: 24 }}
              onClick={() => {
                setStage(index);
              }}
            >
              {stage === index && <span className="stage-timer" key={`${stage}-${active}`} aria-hidden="true" />}
              <small>{String(index + 1).padStart(2, '0')}</small>
              <span>{item.name}</span>
              <ArrowRight size={14} aria-hidden />
            </motion.button>
          </motion.div>
        ))}
      </div>
      <div className="stage-detail-frame" aria-live={active ? 'off' : 'polite'}>
        <AnimatePresence mode="wait" initial={false}>
          <motion.article
            key={selected.name}
            className="stage-explainer"
            data-stage={stage}
            initial={reduce ? false : { opacity: 0, x: 28, scale: 0.98 }}
            animate={{ opacity: 1, x: 0, scale: 1 }}
            exit={reduce ? undefined : { opacity: 0, x: -16, scale: 0.99 }}
            transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
          >
            <div>
              <span className="stage-role">{selected.agent}</span>
              <h3>
                {selected.name}: {selected.description}
              </h3>
              <p>{selected.action}</p>
            </div>
            <dl>
              <div>
                <dt>Needs</dt>
                <dd>{selected.input}</dd>
              </div>
              <div>
                <dt>Produces</dt>
                <dd>{selected.output}</dd>
              </div>
            </dl>
          </motion.article>
        </AnimatePresence>
      </div>
      <div className="workflow-safety">
        <ShieldCheck size={17} aria-hidden />
        <p>
          {stage === 4
            ? 'Human approval is a separate checkpoint. This illustration does not approve or apply a change.'
            : reduce
              ? 'Reduced motion is on. Select any stage to explore at your own pace.'
              : 'Six agents. Your approval. Application and verification remain separate steps.'}
        </p>
      </div>
    </div>
  );
}
