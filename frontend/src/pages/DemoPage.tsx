import { useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, ArrowRight, CheckCheck, RotateCcw, ShieldCheck } from 'lucide-react';
import { useLearningDemo } from '../hooks/useLearningDemo';
import { Badge, QueryState } from '../components/ui';
const steps = [
  [
    'A small interruption',
    'Registration API receives a request without a profile. The sample error is the beginning of our story.',
  ],
  [
    'A signal becomes an incident',
    'Monitoring recognizes the supported error and records inc_001. The Manager coordinates the next stage.',
  ],
  [
    'An explanation, with evidence',
    'Diagnosis finds a profile access without a null check. This is a likely cause, not an unsupported certainty.',
  ],
  [
    'A focused suggestion',
    'Repair proposes a minimal guard. The exact diff, hash and source revision travel with this candidate.',
  ],
  [
    'Check before deciding',
    'Testing evaluates this candidate in isolation. Both recorded sample checks passed. Missing or failed checks would block approval.',
  ],
  [
    'Time for your review',
    'Review the exact patch and its test evidence. Nothing has been approved or applied yet.',
  ],
  [
    'Your decision',
    'Approve this candidate or reject it. You remain in control. Approval still does not apply anything.',
  ],
  [
    'A separate application step',
    'Only an approved, unchanged candidate can proceed. Confirm the simulated local application separately.',
  ],
  [
    'Check the outcome',
    'Verification checks reproduction and smoke results. In this scenario, simulated verification passed. Other workspace examples show failed verification and restoration.',
  ],
  [
    'The complete record',
    'Reporting records the actual decision and outcome, along with the limitations of this simulated example.',
  ],
];
export function DemoPage() {
  const [step, setStep] = useState(0),
    { query, mutation, restart } = useLearningDemo(),
    incident = query.data?.data;
  const rejected = incident?.decision?.decision === 'reject';
  const busy = mutation.isPending;
  const move = (direction: number) =>
    setStep((current) =>
      direction > 0 && current === 6 && rejected
        ? 9
        : direction < 0 && current === 9 && rejected
          ? 6
          : Math.max(0, Math.min(9, current + direction)),
    );
  const blocked =
    (step === 6 && !incident?.decision) || (step === 7 && incident?.status !== 'resolved');
  return (
    <section className="guided-page">
      <div className="guided-top">
        <Link className="text-link" to="/">
          <ArrowLeft size={15} /> Exit demo
        </Link>
        <span className="demo-label">Simulated Demo · no real application changes</span>
      </div>
      <div className="guided-intro">
        <span className="product-kicker">A HANDS-ON INTRODUCTION</span>
        <h1>
          Understand one incident,
          <br />
          one step at a time.
        </h1>
        <p>
          This learning space is isolated from your workspace. It uses a dedicated mock adapter,
          even in API mode.
        </p>
      </div>
      <div className="guided-layout">
        <aside className="tour-index" aria-label="Demo progress">
          <p>YOUR WALKTHROUGH</p>
          {steps.map(([title], index) => (
            <div
              key={title}
              className={index === step ? 'current' : ''}
              aria-current={index === step ? 'step' : undefined}
            >
              <span>
                {index < step ? <CheckCheck size={15} /> : String(index + 1).padStart(2, '0')}
              </span>
              {title}
            </div>
          ))}
        </aside>
        <div className="tour-panel">
          <div className="tour-progress">
            <span>Step {step + 1} of 10</span>
            <progress aria-label="Demo progress" max={10} value={step + 1} />
          </div>
          <div key={step} className="page-enter">
            <span className="tour-large-number">{String(step + 1).padStart(2, '0')}</span>
            <h2>{steps[step][0]}</h2>
            <p className="tour-description">{steps[step][1]}</p>
            <QueryState query={query}>
              {incident && (
                <div className="demo-evidence">
                  {step < 2 ? (
                    <>
                      <small>LOCAL SAMPLE · REGISTRATION API</small>
                      <h3>Registration fails on missing profile</h3>
                      <pre className="code-block">{incident.source_log}</pre>
                    </>
                  ) : step === 2 ? (
                    <>
                      <h3>{incident.diagnosis?.hypothesis}</h3>
                      <p>Confidence: medium. Limited to the sample fixtures.</p>
                      <code>src/registration.py:42–49 · revision abc123</code>
                    </>
                  ) : step === 3 || step === 5 ? (
                    <>
                      <h3>Candidate {incident.patches[0].id}</h3>
                      <pre className="code-block">{incident.patches[0].diff}</pre>
                      <p>Base revision: {incident.patches[0].base_revision}</p>
                      <details>
                        <summary>Exact candidate hash</summary>
                        <code>{incident.patches[0].patch_hash}</code>
                      </details>
                      {step === 5 && (
                        <p className="notice">
                          Both sample checks passed. At the next step, you can approve or reject
                          this exact candidate.
                        </p>
                      )}
                    </>
                  ) : step === 4 ? (
                    <>
                      <h3>Isolated test evidence</h3>
                      {incident.validation?.checks.map((check) => (
                        <div className="demo-check" key={check.name}>
                          <span>{check.name.replaceAll('_', ' ')}</span>
                          <Badge value={check.status} />
                        </div>
                      ))}
                      <p className="notice">Passing tests are not approval.</p>
                    </>
                  ) : step === 6 ? (
                    <>
                      <ShieldCheck size={32} />
                      <h3>
                        {incident.decision
                          ? 'Your decision is recorded.'
                          : 'What would you like to do?'}
                      </h3>
                      <p>Candidate patch_001 · base abc123 · two passed checks.</p>
                      <div className="hero-actions">
                        <button
                          className="button primary"
                          disabled={busy || !incident.can_approve}
                          onClick={() => mutation.mutate('approve')}
                        >
                          Approve candidate
                        </button>
                        <button
                          className="button danger"
                          disabled={busy || !incident.can_reject}
                          onClick={() => mutation.mutate('reject')}
                        >
                          Reject candidate
                        </button>
                      </div>
                      {incident.decision && (
                        <p role="status" className="notice">
                          {rejected
                            ? 'Rejected. No application will occur. Next opens the report.'
                            : 'Approved. Application is still a separate action at the next step.'}
                        </p>
                      )}
                    </>
                  ) : step === 7 ? (
                    <>
                      <h3>Approved is not applied.</h3>
                      <p>
                        This button only changes isolated demo state. No filesystem, repository or
                        production application is modified.
                      </p>
                      <button
                        className="button primary spaced"
                        disabled={busy || !incident.can_apply}
                        onClick={() => mutation.mutate('apply')}
                      >
                        {busy
                          ? 'Simulating application & verification…'
                          : 'Apply approved patch in simulation'}
                      </button>
                      {incident.status === 'resolved' && (
                        <p role="status" className="notice">
                          Simulated application and verification complete. Inspect the evidence
                          next.
                        </p>
                      )}
                    </>
                  ) : step === 8 ? (
                    <>
                      <Badge value={incident.verification?.status || 'not_run'} />
                      <p className="spaced">
                        {incident.verification?.monitoring_observation ||
                          'Verification has not run. Return to the application step.'}
                      </p>
                    </>
                  ) : (
                    <>
                      <Badge value={incident.report?.outcome || incident.status} />
                      <h3 className="spaced">
                        {rejected
                          ? 'A decision to stop is a valid outcome.'
                          : 'A verified outcome, with clear limits.'}
                      </h3>
                      <p>
                        {incident.report?.summary ||
                          'Complete the decision and application steps to produce a report.'}
                      </p>
                      <p className="notice">
                        Simulated evidence only. No code was executed. This does not establish
                        production recovery.
                      </p>
                      <Link className="text-link" to="/onboarding">
                        Explore the workspace next <ArrowRight size={15} />
                      </Link>
                    </>
                  )}
                </div>
              )}
            </QueryState>
            {mutation.isError && (
              <p role="alert" className="error-notice">
                {mutation.error.message}
              </p>
            )}
          </div>
          <div className="tour-controls">
            <button className="button" disabled={step === 0 || busy} onClick={() => move(-1)}>
              <ArrowLeft size={15} /> Previous
            </button>
            <button
              className="button"
              disabled={busy}
              onClick={async () => {
                await restart();
                setStep(0);
                mutation.reset();
              }}
            >
              <RotateCcw size={15} /> Restart
            </button>
            <button
              className="button primary"
              disabled={step === 9 || busy || blocked}
              onClick={() => move(1)}
            >
              Next <ArrowRight size={15} />
            </button>
          </div>
          {blocked && (
            <p className="tour-hint">
              {step === 6
                ? 'Choose approval or rejection to continue.'
                : 'Use the separate simulation button before viewing verification.'}
            </p>
          )}
        </div>
      </div>
    </section>
  );
}
