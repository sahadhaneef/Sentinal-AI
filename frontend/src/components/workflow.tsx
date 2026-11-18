import {
  Activity,
  ArrowRight,
  Bot,
  BrainCircuit,
  CheckCheck,
  ClipboardCheck,
  FileText,
  Network,
  ShieldCheck,
  Wrench,
} from 'lucide-react';
import type { RunState } from '../contracts/types';
import { Badge } from './ui';
export const agentIcons = {
  manager: Network,
  monitoring: Activity,
  diagnosis: BrainCircuit,
  repair: Wrench,
  testing: CheckCheck,
  reporting: FileText,
};
const steps = [
  ['Detect', Activity],
  ['Diagnose', BrainCircuit],
  ['Propose fix', Wrench],
  ['Test', CheckCheck],
  ['Human approval', ClipboardCheck],
  ['Local apply', ShieldCheck],
  ['Verify', CheckCheck],
  ['Report', FileText],
] as const;
export function Workflow({ state }: { state?: RunState }) {
  const stages: Partial<Record<RunState, number>> = {
    detected: 0,
    diagnosing: 1,
    generating_patch: 2,
    revision_requested: 2,
    validating: 3,
    awaiting_approval: 4,
    approved: 5,
    applying: 5,
    verifying: 6,
    resolved: 7,
  };
  const current = state ? stages[state] : undefined;
  return (
    <section className="workflow panel coordinator" id="workflow" aria-label="Agent workflow">
      <div className="workflow-title">
        <span className="workflow-emblem">
          <Bot size={19} />
        </span>
        <div>
          <h2>One connected workflow. You’re in control.</h2>
          <p>The Manager coordinates every stage. Human approval is a mandatory gate.</p>
        </div>
        <span className="workflow-tag">6 agents · 1 shared goal</span>
      </div>
      <ol
        className="workflow-track"
        aria-label="Incident workflow; scroll to explore all eight steps"
        tabIndex={0}
      >
        {steps.map(([name, Icon], index) => (
          <li
            key={name}
            aria-current={index === current ? 'step' : undefined}
            className={`${name === 'Human approval' ? 'human-step' : ''} ${current === index ? 'step-current' : current !== undefined && index < current ? 'step-finished' : ''}`}
          >
            <span className="step-icon">
              <Icon size={19} aria-hidden />
            </span>
            <span>{name}</span>
            {index < steps.length - 1 && (
              <ArrowRight className="step-arrow" size={14} aria-hidden />
            )}
          </li>
        ))}
      </ol>
      <div className="workflow-foot">
        <ShieldCheck size={13} />
        <span>Every proposed change is reviewed by you before it can be applied.</span>
        {state && <Badge value={state} />}
      </div>
    </section>
  );
}
