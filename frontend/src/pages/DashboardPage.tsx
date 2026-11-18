import {
  Activity,
  ArrowRight,
  ArrowUpRight,
  CheckCheck,
  ClipboardCheck,
  Layers,
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { useAgents, useDashboard, useIncidents, useApplications } from '../hooks/queries';
import { readOnboarding } from './OnboardingPage';
import { isDemo } from '../api/client';
import { Heading, Panel, QueryState, Badge } from '../components/ui';
import { Workflow, agentIcons } from '../components/workflow';
import { IncidentList } from '../components/incidents';
export function DashboardPage() {
  const q = useDashboard(),
    inc = useIncidents({ limit: 4 }),
    agents = useAgents(),
    d = q.data?.data,
    applications = useApplications();
  return (
    <>
      <Heading
        title="A clearer view. A calmer workflow."
        eyebrow="SENTINEL OVERVIEW"
        description="Understand what needs attention, review the evidence, and move forward with confidence."
        action={
          <Link className="button primary" to="/approval-recovery">
            <ClipboardCheck size={16} /> Review approvals
          </Link>
        }
      />
      <div className="dashboard-welcome">
        <div>
          <span className="product-kicker">A GOOD PLACE TO START</span>
          <h2>What needs your attention?</h2>
          <p>Check your sample, follow an issue, or review a suggested change.</p>
        </div>
        <Link className="button" to="/onboarding">
          {readOnboarding().done
            ? 'Take the guided tour ?'
            : readOnboarding().step > 0
              ? 'Resume your introduction ?'
              : 'New here? Start your introduction ?'}
        </Link>
      </div>
      <QueryState query={applications}>
        <div className="health-overview">
          {applications.data?.data.map((app) => (
            <Link key={app.id} to={`/applications/${app.id}`}>
              <span className="feature-icon">
                <Activity size={22} />
              </span>
              <div>
                <small>APPLICATION HEALTH</small>
                <h3>{app.name}</h3>
                <p>
                  {app.status === 'healthy'
                    ? 'No current health issue reported.'
                    : app.status === 'degraded'
                      ? 'An issue needs attention. Open the sample to understand it.'
                      : 'Application unavailable. Inspect its details.'}
                </p>
              </div>
              <Badge value={app.status} />
            </Link>
          ))}
        </div>
      </QueryState>
      <QueryState query={q}>
        {d && (
          <div className="kpi-grid">
            {[
              [d.total_incidents, 'Total incidents', Layers, 'All sample incidents', '/incidents'],
              [
                d.open_incidents,
                'Open incidents',
                Activity,
                'Ready for your attention',
                '/incidents?view=open',
              ],
              [
                d.awaiting_approval,
                'Awaiting approval',
                ClipboardCheck,
                'Human decisions needed',
                '/approval-recovery',
              ],
              [
                d.resolved,
                'Verified resolved',
                CheckCheck,
                isDemo ? 'Simulated recovery confirmed' : 'Backend verification confirmed',
                '/history?status=resolved',
              ],
            ].map(([value, title, Icon, caption, path], index) => {
              const I = Icon as typeof Activity;
              return (
                <Link to={path as string} className={`kpi kpi-${index}`} key={String(title)}>
                  <div>
                    <span className="kpi-title">{String(title)}</span>
                    <I size={18} />
                  </div>
                  <strong>{String(value).padStart(2, '0')}</strong>
                  <span className="kpi-caption">
                    {String(caption)} <ArrowUpRight size={13} />
                  </span>
                </Link>
              );
            })}
          </div>
        )}
      </QueryState>
      <Workflow />
      <div className="dashboard-grid">
        <Panel
          title="Recent incidents"
          action={
            <Link className="text-link" to="/incidents">
              View all <ArrowRight size={14} />
            </Link>
          }
        >
          <QueryState query={inc}>
            <IncidentList incidents={inc.data?.data.items || []} />
          </QueryState>
        </Panel>
        <Panel
          title="Agent overview"
          action={
            <Link className="text-link" to="/agents">
              All agents <ArrowRight size={14} />
            </Link>
          }
        >
          <p className="overview-caption">
            {q.isPending || agents.isPending
              ? 'Loading agent activity…'
              : q.isError || agents.isError
                ? 'Agent activity unavailable.'
                : `${d?.active_agents ?? 0} running · ${agents.data?.data.length ?? 0} specialized agents`}
          </p>
          <QueryState query={agents}>
            <div className="compact-agents">
              {agents.data?.data.map((a) => {
                const Icon = agentIcons[a.agent_type];
                return (
                  <Link to={`/agents/${a.agent_type}`} key={a.agent_type}>
                    <span className={`mini-agent agent-${a.agent_type}`}>
                      <Icon size={17} />
                    </span>
                    <span>{a.name}</span>
                    <Badge value={a.status} />
                  </Link>
                );
              })}
            </div>
          </QueryState>
        </Panel>
      </div>
      <div className="notice inline-notice">
        <ClipboardCheck size={19} />
        <div>
          <strong>Automation with a human checkpoint.</strong>
          <p>
            A passing test is evidence. You make the decision. An approved candidate still needs a
            separate apply action.
          </p>
        </div>
        <Link className="text-link" to="/incidents/inc_001">
          Explore sample <ArrowRight size={15} />
        </Link>
      </div>
    </>
  );
}
