import { Link, useParams, useSearchParams } from 'react-router-dom';
import {
  ArrowLeft,
  ArrowRight,
  ArrowUpRight,
  CheckCircle2,
  ClipboardCheck,
  Clock3,
  FileCode2,
  FileText,
  FlaskConical,
  Layers,
  ShieldCheck,
  Wrench,
} from 'lucide-react';
import { terminalStates, useEvents, useIncident, useApplication } from '../hooks/queries';
import { Badge, CopyButton, Empty, Heading, Panel, QueryState } from '../components/ui';
import { useNotify } from '../components/feedback';
import { PatchReview } from '../components/patches';
import { ReviewActions } from '../components/ReviewActions';
import { label, time } from '../lib/format';
import { Outcome } from '../components/Outcome';
import { Workflow } from '../components/workflow';
import { isDemo } from '../api/client';

export function IncidentDetailPage() {
  const { id = '' } = useParams(),
    [params, setParams] = useSearchParams(),
    q = useIncident(id),
    i = q.data?.data,
    application = useApplication(i?.application_id || ''),
    events = useEvents(id, !!i && !terminalStates.includes(i.status)),
    notify = useNotify();

  const tabs = ['overview', 'diagnosis', 'patch & tests', 'timeline', 'report'];
  const selected = params.get('tab') || 'overview';

  const hasCandidate = !!(i?.patches && i.patches.length > 0);
  const isValidated = i?.validation?.status === 'passed';

  return (
    <>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '18px' }}>
        <Link to="/incidents" className="text-link back-link" style={{ marginBottom: 0 }}>
          <ArrowLeft size={14} /> Back to all incidents
        </Link>
        <div style={{ display: 'flex', gap: '10px' }}>
          {hasCandidate && (
            <Link
              className="button"
              to={`/repair-testing?incident=${id}`}
              style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', fontSize: '12px' }}
            >
              <Wrench size={14} /> Repair & Testing <ArrowUpRight size={13} />
            </Link>
          )}
          {hasCandidate && (
            <Link
              className="button primary"
              to={`/approval-recovery?incident=${id}`}
              style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', fontSize: '12px' }}
            >
              <ClipboardCheck size={14} /> Approval & Recovery <ArrowRight size={13} />
            </Link>
          )}
        </div>
      </div>

      <Heading
        eyebrow={id.toUpperCase().replace('_', '–')}
        title={i?.message || 'Incident details'}
        description="Autonomous evidence, AI root-cause diagnosis, isolated candidate tests, and developer decisions."
        action={
          i && (
            <span role="status" aria-label="Incident status">
              <Badge value={i.status} />
            </span>
          )
        }
      />

      <QueryState query={q}>
        {i && (
          <>
            <div className="incident-meta">
              <Badge value={i.severity} />
              <Link className="text-link" to={`/applications/${i.application_id}`}>
                {application.data?.data.name || i.application_id} <ArrowUpRight size={13} />
              </Link>
              <span>
                <Clock3 size={14} /> {time(i.detected_at)}
              </span>
              <code>rev {i.repository_revision}</code>
            </div>

            <Workflow state={i.status} />

            <nav className="tabs" aria-label="Incident sections">
              {tabs.map((tab) => (
                <button
                  key={tab}
                  aria-current={selected === tab ? 'page' : undefined}
                  className={selected === tab ? 'selected' : ''}
                  onClick={() => setParams({ tab })}
                >
                  {label(tab)}
                </button>
              ))}
            </nav>

            <div className="page-enter" key={selected}>
              {selected === 'overview' && (
                <>
                  <div className="detail-grid">
                    <Panel title="Incident Summary">
                      <dl className="key-values">
                        <div>
                          <dt>Error type</dt>
                          <dd>
                            <code>{i.error_type}</code>
                          </dd>
                        </div>
                        <div>
                          <dt>Current stage</dt>
                          <dd>{label(i.current_stage)}</dd>
                        </div>
                        <div>
                          <dt>Active run</dt>
                          <dd>{i.active_run_id || 'No active run'}</dd>
                        </div>
                        <div>
                          <dt>Base revision</dt>
                          <dd>
                            <code>{i.repository_revision}</code>
                          </dd>
                        </div>
                        <div>
                          <dt>Candidate patches</dt>
                          <dd>{i.patches.length} candidate(s) formulated</dd>
                        </div>
                      </dl>

                      <p className="notice">
                        {i.permission_reason ||
                          (isDemo
                            ? 'Simulated evidence for local demonstration. Real changes require developer confirmation.'
                            : 'Review evidence at the recorded repository revision. Permissions independently enforced.')}
                      </p>

                      <div style={{ display: 'flex', gap: '12px', marginTop: '16px' }}>
                        <Link className="text-link" to={`/incidents/${id}?tab=diagnosis`}>
                          Inspect diagnosis <ArrowUpRight size={14} />
                        </Link>
                        {hasCandidate && (
                          <Link className="text-link" to={`/repair-testing?incident=${id}`}>
                            Open Repair & Testing <ArrowUpRight size={14} />
                          </Link>
                        )}
                      </div>
                    </Panel>

                    <Panel
                      title="Source Error Log & Stack Trace"
                      action={<CopyButton value={i.source_log} notify={notify} />}
                    >
                      <pre
                        className="code-block"
                        style={{ maxHeight: '260px', overflowY: 'auto' }}
                      >
                        {i.source_log}
                      </pre>
                      <p className="spaced" style={{ fontSize: '11px', color: 'var(--muted)' }}>
                        Source event ID: <code>{i.source_event_id}</code>. Monitored service: <strong>{application.data?.data.name || i.application_id}</strong>.
                      </p>
                    </Panel>
                  </div>

                  <div className="spaced">
                    <ReviewActions key={i.id} incident={i} />
                  </div>

                  <div className="spaced">
                    <Outcome incident={i} />
                  </div>
                </>
              )}

              {selected === 'diagnosis' &&
                (i.diagnosis ? (
                  <Panel
                    title="Evidence-backed diagnosis"
                    action={<Badge value={i.diagnosis.status} />}
                  >
                    <h3>{i.diagnosis.hypothesis}</h3>
                    <p className="spaced">
                      Confidence: <strong>{i.diagnosis.confidence_label}</strong>. {i.diagnosis.uncertainty}
                    </p>
                    <p className="notice">Suggested direction: {i.diagnosis.suggested_direction}</p>
                    {i.diagnosis.evidence.map((e) => (
                      <div className="evidence" key={e.artifact_id}>
                        <h3>
                          {e.file_path}:{e.start_line}–{e.end_line}
                        </h3>
                        <p>
                          {e.symbol} · revision <code>{e.repository_revision}</code>
                        </p>
                        <pre className="code-block">{e.excerpt}</pre>
                        <small>Evidence artifact {e.artifact_id}</small>
                      </div>
                    ))}
                    <div style={{ display: 'flex', gap: '12px', marginTop: '16px' }}>
                      <Link className="button" to={`/incidents/${id}?tab=patch%20%26%20tests`}>
                        Review patch & tests <ArrowUpRight size={15} />
                      </Link>
                      <Link className="button primary" to={`/repair-testing?incident=${id}`}>
                        Open in Repair & Testing <ArrowRight size={15} />
                      </Link>
                    </div>
                  </Panel>
                ) : (
                  <Panel>
                    <Empty message="Needs manual review. No supported diagnosis available for this incident." />
                  </Panel>
                ))}

              {selected === 'patch & tests' &&
                (i.patches.length ? (
                  <>
                    <PatchReview patch={i.patches.at(-1)!} validation={i.validation} />
                    <div style={{ display: 'flex', gap: '12px', marginTop: '16px', marginBottom: '16px' }}>
                      <Link className="button primary" to={`/repair-testing?incident=${id}`}>
                        Detailed Testing Console <ArrowUpRight size={14} />
                      </Link>
                      <Link className="button" to={`/approval-recovery?incident=${id}`}>
                        Approval & Recovery <ArrowRight size={14} />
                      </Link>
                    </div>
                    <div className="spaced">
                      <ReviewActions incident={i} />
                    </div>
                  </>
                ) : (
                  <Panel>
                    <Empty message="No patch candidate available for this incident yet." />
                  </Panel>
                ))}

              {selected === 'timeline' && (
                <Panel title="Incident audit timeline">
                  <QueryState query={events}>
                    <ol className="timeline">
                      {events.data?.data.map((e) => (
                        <li key={e.id}>
                          <span className="timeline-dot">
                            <ShieldCheck size={15} />
                          </span>
                          <div>
                            <h3>{label(e.event_type)}</h3>
                            <p>{String(e.payload.message || 'Event recorded')}</p>
                            <small>
                              {e.actor_type} · {e.actor_id} · {time(e.occurred_at)}
                            </small>
                          </div>
                        </li>
                      ))}
                    </ol>
                  </QueryState>
                </Panel>
              )}

              {selected === 'report' && <Outcome incident={i} />}

              {!tabs.includes(selected) && (
                <Empty message="Unknown incident section. Choose a section above." />
              )}
            </div>
          </>
        )}
      </QueryState>
    </>
  );
}
