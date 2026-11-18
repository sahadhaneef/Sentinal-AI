import { Link, useParams, useSearchParams } from 'react-router-dom';
import { ArrowLeft, ArrowUpRight, Clock3, ShieldCheck } from 'lucide-react';
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
  return (
    <>
      <Link to="/incidents" className="text-link back-link">
        <ArrowLeft size={14} /> All incidents
      </Link>
      <Heading
        eyebrow={id.toUpperCase().replace('_', '–')}
        title={i?.message || 'Incident details'}
        description="Evidence, decisions and outcomes — connected in one reviewable record."
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
                    <Panel title="Incident summary">
                      <dl className="key-values">
                        <div>
                          <dt>Error type</dt>
                          <dd>{i.error_type}</dd>
                        </div>
                        <div>
                          <dt>Current stage</dt>
                          <dd>{label(i.current_stage)}</dd>
                        </div>
                        <div>
                          <dt>Run</dt>
                          <dd>{i.active_run_id || 'No active run'}</dd>
                        </div>
                        <div>
                          <dt>Repository revision</dt>
                          <dd>
                            <code>{i.repository_revision}</code>
                          </dd>
                        </div>
                      </dl>
                      <p className="notice">
                        {i.permission_reason ||
                          (isDemo
                            ? 'This incident is linked to an exact source revision and candidate. All evidence in this workspace is simulated.'
                            : 'Review evidence at the recorded repository revision. The backend independently enforces approval and apply permissions.')}
                      </p>
                      <Link className="text-link" to={`/incidents/${id}?tab=diagnosis`}>
                        Inspect diagnosis <ArrowUpRight size={14} />
                      </Link>
                    </Panel>
                    <Panel
                      title="Source log (redacted)"
                      action={<CopyButton value={i.source_log} notify={notify} />}
                    >
                      <pre className="code-block">{i.source_log}</pre>
                      <p className="spaced">
                        Source event {i.source_event_id}. Unsupported patterns require manual
                        review.
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
                      Confidence: {i.diagnosis.confidence_label}. {i.diagnosis.uncertainty}
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
                    <Link className="button spaced" to={`/incidents/${id}?tab=patch%20%26%20tests`}>
                      Review patch & tests <ArrowUpRight size={15} />
                    </Link>
                  </Panel>
                ) : (
                  <Panel>
                    <Empty message="Needs manual review. No supported diagnosis." />
                  </Panel>
                ))}
              {selected === 'patch & tests' &&
                (i.patches.length ? (
                  <>
                    <PatchReview patch={i.patches.at(-1)!} validation={i.validation} />
                    <div className="spaced">
                      <ReviewActions incident={i} />
                    </div>
                  </>
                ) : (
                  <Panel>
                    <Empty message="No patch candidate available." />
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
              {selected === 'report' && <Outcome incident={i} />}{' '}
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
