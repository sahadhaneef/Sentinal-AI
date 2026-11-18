import { useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
  ArrowRight,
  Activity,
  BrainCircuit,
  Play,
  Plus,
  ShieldCheck,
  Wrench,
} from 'lucide-react';
import { faq } from '../content/product';
import { ProductTourVideo } from '../components/ProductTourVideo';
import { HeroButton, HeroPreview } from '../components/HeroInteractions';
import { FeatureCard } from '../components/FeatureCard';
import { WorkflowPanel } from '../components/WorkflowPanel';
import { LandingSection } from '../components/LandingMotion';
import { AgentTeam } from '../components/AgentTeam';
import { LandingWorkflow } from '../components/LandingWorkflow';
import { WorkspaceExplorer } from '../components/WorkspaceExplorer';
import { LandingAtmosphere } from '../components/LandingAtmosphere';
import { HeroScene } from '../components/HeroScene';
import { ScrollFeatureStack } from '../components/ScrollFeatureStack';
export function LandingPage() {
  const location = useLocation();
  useEffect(() => {
    if (location.hash) document.getElementById(location.hash.slice(1))?.scrollIntoView();
  }, [location.hash]);
  return (
    <div className="premium-landing">
      <LandingAtmosphere />
      <HeroScene>
        <div className="hero-copy">
          <span className="product-kicker">HUMAN-GUIDED INCIDENT INTELLIGENCE</span>
          <h1>
            Understand the issue.
            <em> Own the next move.</em>
          </h1>
          <p>
            Six AI agents turn application errors into evidence and reviewable fixes. You stay in
            control of every change.
          </p>
          <div className="hero-actions">
            <HeroButton primary to="/onboarding">
              Get Started{' '}
              <span className="cta-icon">
                <ArrowRight size={17} />
              </span>
            </HeroButton>
            <HeroButton to="/demo">
              <Play size={16} /> Explore Interactive Demo
            </HeroButton>
          </div>
          <p className="hero-footnote">
            <ShieldCheck size={15} /> One local sample. Simulated data. No production changes.
          </p>
        </div>
        <div className="hero-art">
          <div className="hero-orbit" aria-hidden />
          <HeroPreview />
          <div className="visual-caption">
            <span>THE WORKSPACE, AT A GLANCE</span>
            <span>Illustrated sample incident</span>
          </div>
        </div>
      </HeroScene>
      <LandingSection className="product-section scroll-story-section" id="about">
        <div className="section-intro">
          <span className="product-kicker">LESS GUESSWORK. MORE UNDERSTANDING.</span>
          <h2>
            A clearer way to handle
            <br />
            “something went wrong.”
          </h2>
          <p>
            SENTINEL AI brings the important questions into one place. What happened? Why might it
            have happened? What should we review next?
          </p>
        </div>
        <ScrollFeatureStack>
          {[
            [
              Activity,
              'Notice the issue',
              'Supported sample errors become incidents you can follow.',
            ],
            [
              BrainCircuit,
              'Understand the cause',
              'Read a likely explanation with source evidence and uncertainty.',
            ],
            [
              Wrench,
              'Review a suggestion',
              'Inspect a focused patch and the tests that evaluated it.',
            ],
            [
              ShieldCheck,
              'Stay in control',
              'Approve or reject, apply separately, and inspect the outcome.',
            ],
          ].map(([Icon, title, description], index) => {
            const I = Icon as typeof Activity;
            return (
              <FeatureCard key={String(title)} index={index} motionStyle="signal" reveal={false}
                className={`benefit-card benefit-signal benefit-tone-${index}`}
                decoration={<span className="benefit-light-sweep" aria-hidden="true" />}
              >
                <span className="feature-icon">
                  <I size={23} aria-hidden="true" />
                </span>
                <h3>{String(title)}</h3>
                <p>{String(description)}</p>
              </FeatureCard>
            );
          })}
        </ScrollFeatureStack>
      </LandingSection>
      <WorkflowPanel>
        <div className="section-intro">
          <h2>From first signal to final say.</h2>
          <p>
            Six specialized agents. One coordinated workflow. Follow each handoff and see exactly
            where your judgment matters.
          </p>
        </div>
        <LandingWorkflow />
      </WorkflowPanel>
      <LandingSection className="product-section" id="team">
        <div className="section-intro">
          <h2>Meet your six-agent team.</h2>
          <p>
            Each role has a clear responsibility. Human approval stays a separate, mandatory
            checkpoint.
          </p>
        </div>
        <AgentTeam />
      </LandingSection>
      <LandingSection className="product-section demo-invitation" id="demo">
        <div>
          <h2>
            One incident.
            <br />
            Every decision, explained.
          </h2>
          <p>
            Watch the six agents at work and take a guided tour of the workspace. Then try the
            interactive demo to practice an approval or rejection.
          </p>
          <Link className="button primary" to="/demo">
            Launch guided demo{' '}
            <span className="cta-icon">
              <ArrowRight size={16} />
            </span>
          </Link>
        </div>
        <ProductTourVideo />
      </LandingSection>
      <LandingSection className="product-section" id="platform">
        <div className="section-intro">
          <h2>Explore the workspace.</h2>
          <p>Start with the overview. Open the details when you need them.</p>
        </div>
        <WorkspaceExplorer />
      </LandingSection>
      <LandingSection className="product-section faq-section" id="faq">
        <div className="section-intro">
          <h2>Before you get started.</h2>
          <p>Clear answers about the prototype and its limits.</p>
        </div>
        <div className="faq-cards">
          {faq.map(([question, answer]) => (
            <details className="faq-item" key={question}>
              <summary>
                <span>{question}</span>
                <span className="faq-toggle" aria-hidden="true"><Plus size={18} /></span>
              </summary>
              <p>{answer}</p>
            </details>
          ))}
        </div>
      </LandingSection>
      <LandingSection className="closing-cta">
        <h2>
          Make the next decision
          <br />
          with a little more confidence.
        </h2>
        <p>Explore safely, understand the workflow, and keep the final say.</p>
        <div className="hero-actions">
          <Link className="button primary" to="/demo">
            Try the guided demo{' '}
            <span className="cta-icon">
              <ArrowRight size={16} />
            </span>
          </Link>
          <Link className="button" to="/onboarding">
            Enter the workspace
          </Link>
        </div>
      </LandingSection>
    </div>
  );
}
