import { Activity, ArrowRight, CheckCheck, ShieldCheck, Sparkles } from 'lucide-react';
export function ProductVisual() {
  return (
    <div
      className="product-visual"
      aria-label="Illustrated sample incident journey; a concept preview, not live monitoring"
    >
      <div className="visual-window">
        <span className="window-dots" aria-hidden>
          ● ● ●
        </span>
        <span>YOUR INCIDENT, EXPLAINED</span>
        <ShieldCheck size={17} />
      </div>
      <div className="visual-body">
        <div className="visual-app">
          <span className="visual-icon">
            <Activity />
          </span>
          <div>
            <small>LOCAL SAMPLE APPLICATION</small>
            <h3>Registration API</h3>
          </div>
          <span className="concept-label">Concept preview</span>
        </div>
        <div className="visual-signal">
          <span className="signal-dot" />
          <div>
            <strong>A missing profile interrupted registration.</strong>
            <p>Let’s understand it before changing anything.</p>
          </div>
        </div>
        <div className="visual-path">
          <span>
            <Sparkles size={19} /> Understand
          </span>
          <ArrowRight size={15} />
          <span>
            <CheckCheck size={19} /> Test
          </span>
          <ArrowRight size={15} />
          <span>
            <ShieldCheck size={19} /> You decide
          </span>
        </div>
        <div className="visual-code">
          <span className="code-caption">A SMALL, REVIEWABLE SUGGESTION</span>
          <code>− name = profile["name"]</code>
          <code>+ name = profile.get("name", "Guest")</code>
        </div>
        <div className="visual-human">
          <ShieldCheck size={21} />
          <div>
            <strong>Human approval comes first.</strong>
            <p>A suggestion is never permission to apply.</p>
          </div>
        </div>
      </div>
    </div>
  );
}
