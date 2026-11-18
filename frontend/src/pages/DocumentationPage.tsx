import { Link } from 'react-router-dom';
import { Heading, Panel } from '../components/ui';
export function DocumentationPage() {
  return (
    <section className="guided-page">
      <Heading
        title="A short guide to SENTINEL AI"
        description="The essentials for exploring this local prototype."
      />
      <div className="detail-grid">
        <Panel title="Start with a question">
          <p>
            Open the dashboard to understand application health, active incidents and pending
            decisions. Follow an incident to its explanation, proposed diff and checks.
          </p>
          <Link className="text-link" to="/demo">
            Walk through an example →
          </Link>
        </Panel>
        <Panel title="Review before changing anything">
          <p>
            Approval requires passing evidence for the exact candidate, hash and source revision.
            Application is a separate confirmation. Changed candidates require fresh review.
          </p>
          <Link className="text-link" to="/approval-recovery">
            Explore human review →
          </Link>
        </Panel>
        <Panel title="Read the actual outcome">
          <p>
            A rejected candidate does not apply changes. Failed verification may require restoration
            or manual intervention. Reports include limitations, not just success labels.
          </p>
          <Link className="text-link" to="/history">
            Explore recorded outcomes →
          </Link>
        </Panel>
        <Panel title="Prototype boundaries">
          <p>
            Mock mode is visibly labeled. It executes no code and does not modify real applications.
            The future FastAPI backend must independently enforce authentication, permissions and
            patch safety. Arbitrary repositories are not supported.
          </p>
          <Link className="text-link" to="/#faq">
            Read frequently asked questions →
          </Link>
        </Panel>
      </div>
    </section>
  );
}
