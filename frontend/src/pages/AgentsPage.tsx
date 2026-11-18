import { ArrowRight, CheckCheck, Clock3, Info } from 'lucide-react';
import { Link, useParams } from 'react-router-dom';
import { motion, useReducedMotion } from 'motion/react';
import { usePreferences } from '../app/preferences';
import { isDemo } from '../api/client';
import { useAgent, useAgents } from '../hooks/queries';
import { agentTypeSchema } from '../contracts/schemas';
import { Badge, Heading, Panel, QueryState, Empty } from '../components/ui';
import { Workflow, agentIcons } from '../components/workflow';
import { time } from '../lib/format';

export function AgentsPage() {
  const reducedMotion = useReducedMotion();
  const { preferences } = usePreferences();
  const reduce = reducedMotion || preferences.motion === 'reduce';
  const q = useAgents(),
    agents = q.data?.data || [],
    running = agents.filter((a) => a.status === 'running').length,
    attention = agents.filter((a) => a.status === 'error' || a.status === 'offline').length;
  return (
    <>
      <Heading
        title="AI Agents"
        description="Meet the team behind every incident. Six specialized agents, working together with you."
        action={
          <span className="agent-summary" role="status">
            {q.isPending ? (
              'Loading agent status…'
            ) : q.isError ? (
              'Agent statuses unavailable'
            ) : (
              <>
                <span className={attention ? 'attention-dot' : 'status-dot'} />
                {agents.length} agents <span>·</span>{' '}
                {attention ? `${attention} needs attention` : `${running} running`}
              </>
            )}
          </span>
        }
      />
      <Workflow />
      <div className="section-label">
        <div>
          <h2>
            Your agent team <span>{q.data ? String(agents.length).padStart(2, '0') : '—'}</span>
          </h2>
          <p>Specialized by role. Connected by purpose.</p>
        </div>
        <span className="muted-caption">
          {isDemo ? 'SIMULATED AGENT ACTIVITY' : 'BACKEND AGENT ACTIVITY'}
        </span>
      </div>
      <QueryState query={q}>
        {!agents.length && <Empty message="No agent records returned." />}
        <div className="agent-grid">
          {agents.map((agent, index) => {
            const Icon = agentIcons[agent.agent_type];
            return (
              <motion.div
                key={agent.agent_type}
                initial={reduce ? false : { opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.18, delay: index * 0.035 }}
              >
                <Link
                  to={`/agents/${agent.agent_type}`}
                  className={`agent-card agent-${agent.agent_type}`}
                >
                  <div className="agent-card-top">
                    <span className="agent-icon">
                      <Icon size={25} strokeWidth={1.6} />
                    </span>
                    <Badge value={agent.status} />
                  </div>
                  <div className="agent-number">AGENT {String(index + 1).padStart(2, '0')}</div>
                  <h3>{agent.name}</h3>
                  <p className="agent-description">{agent.responsibility}</p>
                  <div className="agent-task">
                    <span className="task-caption">CURRENT TASK</span>
                    <p>{agent.current_task || 'No active task'}</p>
                    <div className="last-activity">
                      <Clock3 size={13} />
                      <span>{agent.last_activity || 'No recent activity'}</span>
                    </div>
                  </div>
                  <div className="agent-card-footer">
                    <span>
                      View details <ArrowRight size={14} />
                    </span>
                    <small>{agent.owner}</small>
                  </div>
                </Link>
              </motion.div>
            );
          })}
        </div>
      </QueryState>
      <div className="agent-bottom-note">
        <span>
          <Info size={15} /> A coordinated team, with clear boundaries.
        </span>
        <p>Agents propose and validate. You review and authorize every local change.</p>
        <Link to="/approval-recovery">
          Explore human review <ArrowRight size={14} />
        </Link>
      </div>
    </>
  );
}
export function AgentDetailPage() {
  const { type = '' } = useParams(),
    parsed = agentTypeSchema.safeParse(type);
  const q = useAgent(parsed.success ? parsed.data : (type as 'manager')),
    a = q.data?.data;
  return (
    <>
      <Heading
        title={a?.name || 'Agent details'}
        description={
          isDemo
            ? 'Responsibilities, handoffs, and evidence from simulated executions.'
            : 'Responsibilities, handoffs, and evidence returned by the backend.'
        }
      />
      <QueryState query={q}>
        {a && (
          <div className="detail-grid">
            <Panel title="Role and boundaries">
              <div className={`agent-icon agent-${a.agent_type}`}>
                {(() => {
                  const Icon = agentIcons[a.agent_type];
                  return <Icon size={28} />;
                })()}
              </div>
              <h3 className="spaced">{a.responsibility}</h3>
              <p className="spaced">
                Owned by {a.owner}. <Badge value={a.status} />
              </p>
              <p>{a.current_task || 'No active task'}</p>
              <h3 className="spaced">Inputs</h3>
              <ul className="plain-list">
                {a.inputs.map((v) => (
                  <li key={v}>{v}</li>
                ))}
              </ul>
              <h3 className="spaced">Outputs</h3>
              <ul className="plain-list">
                {a.outputs.map((v) => (
                  <li key={v}>{v}</li>
                ))}
              </ul>
              <p className="notice">
                This agent has no manual run control. The Manager coordinates supported stages
                through the incident workflow.
              </p>
            </Panel>
            <Panel title="Recent executions">
              {!a.recent_runs.length && <Empty message="No executions recorded yet." />}
              {a.recent_runs.map((run, index) => (
                <div className="execution" key={index}>
                  <CheckCheck size={20} />
                  <div>
                    <Link className="text-link" to={`/incidents/${run.incident_id}`}>
                      {run.incident_id} <ArrowRight size={14} />
                    </Link>
                    <p>{time(run.created_at)}</p>
                    <small>Revision {run.input_revision}</small>
                    {run.error && <p className="error-text">{run.error}</p>}
                  </div>
                  <Badge value={run.status} />
                </div>
              ))}
            </Panel>
          </div>
        )}
      </QueryState>
    </>
  );
}
