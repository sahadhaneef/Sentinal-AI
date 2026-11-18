import { useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { ArrowLeft, ArrowRight, ShieldCheck } from 'lucide-react';
import { ProductVisual } from '../components/ProductVisual';
const lessons = [
  [
    'Welcome to a clearer workspace.',
    'SENTINEL AI helps you understand a local sample incident before making a change. No registration or real application connection is needed for this prototype.',
    'Your first step is understanding, not configuration.',
  ],
  [
    'Meet the team behind the process.',
    'The Manager coordinates Monitoring, Diagnosis, Repair, Testing and Reporting. Human approval is your responsibility, not a seventh agent.',
    'Six roles. One coordinated workflow.',
  ],
  [
    'Start with the sample application.',
    'Registration API is the designated local example. Its monitoring and incident data are explicitly simulated in mock mode. You are not registering a real application.',
    'Explore Applications when you want to see its details.',
  ],
  [
    'Follow a signal to its evidence.',
    'An incident brings the error, a likely cause, source citations and the proposed change together. Uncertain or unsupported cases require manual review.',
    'The explanation comes before the technical detail.',
  ],
  [
    'Keep the final say.',
    'Inspect the exact patch and passing tests. Approve or reject that candidate. Applying it requires another confirmation, and verification determines the outcome.',
    'Approval and application are always separate.',
  ],
  [
    'You’re ready to explore.',
    'Begin with application health, open incidents and anything awaiting your review. You can return to this introduction or the interactive demo whenever you need.',
    'Your workspace is ready to explore—not connected to a production system.',
  ],
];
export function readOnboarding() {
  try {
    const value = JSON.parse(localStorage.getItem('sentinel.onboarding') || '{}');
    return {
      step: Number.isInteger(value.step) && value.step >= 0 && value.step < 6 ? value.step : 0,
      done: value.done === true,
    };
  } catch {
    return { step: 0, done: false };
  }
}
function save(step: number, done = false) {
  try {
    localStorage.setItem('sentinel.onboarding', JSON.stringify({ step, done }));
  } catch {
    /* Session use remains available. */
  }
}
export function OnboardingPage() {
  const [params] = useSearchParams(),
    [step, setStep] = useState(() => (params.has('restart') ? 0 : readOnboarding().step)),
    navigate = useNavigate();
  const change = (next: number) => {
    save(next);
    setStep(next);
  };
  const finish = () => {
    save(step, true);
    navigate('/dashboard');
  };
  return (
    <section className="guided-page onboarding">
      <div className="guided-top">
        <Link className="text-link" to="/">
          <ArrowLeft size={15} /> Back to product
        </Link>
        <button className="text-link" onClick={finish}>
          Skip introduction
        </button>
      </div>
      <div className="onboarding-card">
        <div className="onboarding-copy">
          <span className="product-kicker">YOUR WORKSPACE INTRODUCTION</span>
          <div className="tour-progress">
            <span>Step {step + 1} of 6</span>
            <progress max={6} value={step + 1} aria-label="Onboarding progress" />
          </div>
          <div key={step} className="page-enter">
            <h1>{lessons[step][0]}</h1>
            <p>{lessons[step][1]}</p>
            <div className="onboarding-note">
              <ShieldCheck size={20} />
              {lessons[step][2]}
            </div>
          </div>
          <div className="tour-controls">
            <button className="button" disabled={step === 0} onClick={() => change(step - 1)}>
              Back
            </button>
            <button
              className="button primary"
              onClick={() => (step === 5 ? finish() : change(step + 1))}
            >
              {step === 5 ? 'Enter dashboard' : 'Next'} <ArrowRight size={15} />
            </button>
          </div>
          <button className="text-link" onClick={() => change(0)}>
            Restart introduction
          </button>
        </div>
        <div className="onboarding-art">
          <ProductVisual />
          <span>Learn at your own pace. Resume where you left off.</span>
        </div>
      </div>
    </section>
  );
}
