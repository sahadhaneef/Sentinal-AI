import { useSearchParams, Link } from 'react-router-dom';
import {
  ArrowRight,
  ArrowUpRight,
  CheckCircle2,
  Clock,
  Code2,
  FileCode2,
  FlaskConical,
  GitBranch,
  Hash,
  Layers,
  RotateCcw,
  ShieldAlert,
  ShieldCheck,
  Wrench,
  XCircle,
} from 'lucide-react';
import { useIncident, useIncidents, useApplications } from '../hooks/queries';
import { Badge, CopyButton, Empty, Heading, Panel, QueryState } from '../components/ui';
import { PatchReview } from '../components/patches';
import { label, time } from '../lib/format';
import { useNotify } from '../components/feedback';

export function RepairTestingPage() {
  const [params, setParams] = useSearchParams(),
    notify = useNotify();

  // Load candidate incidents
  const qQueue = useIncidents({
    limit: 10,
    scope: 'candidates',
    sort: 'detected_desc',
  });

  const applications = useApplications();
  const items = qQueue.data?.data.items || [];
  const selectedId = params.get('incident') || items[0]?.id || '';

  const qIncident = useIncident(selectedId);
  const incident = qIncident.data?.data;
  const currentPatch = incident?.patches.at(-1);
  const validation = incident?.validation;

  const appName =
    applications.data?.data.find((a) => a.id === incident?.application_id)?.name ||
    incident?.application_id ||
    'Application';

  return (
    <>
      <Heading
        title="Repair & Testing"
        description="Isolated validation and AI repair verification. Review candidate code diffs, automated reproduction checks, and regression suites."
      />

      {/* Testing Agent Banner */}
      <div className="review-banner" style={{ marginBottom: '24px' }}>
        <span>
          <Wrench size={24} />
        </span>
        <div>
          <strong>Testing Agent & Local Sandbox Verification</strong>
          <p>
            Candidate diffs are executed in temporary isolated sandboxes with stripped secrets and
            timeout limits. Diffs must pass reproduction and regression test suites before human approval.
          </p>
        </div>
        <span className="review-banner-tag">AGENT STAGE: TESTING</span>
      </div>

      <QueryState query={qQueue}>
        {items.length === 0 ? (
          <Panel>
            <Empty message="No candidate patches in queue. Incidents awaiting repair or testing will appear here." />
          </Panel>
        ) : (
          <div className="detail-grid" style={{ gridTemplateColumns: '320px minmax(0, 1fr)' }}>
            {/* Candidate Queue Sidebar */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <Panel
                title="Repair Queue"
                action={<span className="muted-caption">{items.length} CANDIDATES</span>}
              >
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {items.map((item) => {
                    const isSelected = item.id === selectedId;
                    return (
                      <button
                        key={item.id}
                        type="button"
                        onClick={() => setParams({ incident: item.id })}
                        style={{
                          textAlign: 'left',
                          padding: '12px 14px',
                          borderRadius: '8px',
                          border: `1px solid ${isSelected ? 'var(--primary)' : 'var(--border)'}`,
                          background: isSelected ? 'var(--tint)' : 'var(--surface)',
                          transition: 'all 0.15s ease',
                          display: 'flex',
                          flexDirection: 'column',
                          gap: '6px',
                        }}
                      >
                        <div
                          style={{
                            display: 'flex',
                            justifyContent: 'space-between',
                            alignItems: 'center',
                          }}
                        >
                          <span
                            style={{
                              fontSize: '11px',
                              fontFamily: 'monospace',
                              fontWeight: 700,
                              color: isSelected ? 'var(--primary)' : 'var(--muted)',
                            }}
                          >
                            {item.id.toUpperCase().replace('_', '–')}
                          </span>
                          <Badge value={item.status} />
                        </div>
                        <strong
                          style={{
                            fontSize: '13px',
                            color: 'var(--text)',
                            lineHeight: 1.3,
                          }}
                        >
                          {item.message}
                        </strong>
                        <div
                          style={{
                            display: 'flex',
                            justifyContent: 'space-between',
                            alignItems: 'center',
                            fontSize: '11px',
                            color: 'var(--muted)',
                          }}
                        >
                          <span>{item.error_type}</span>
                          <Badge value={item.severity} />
                        </div>
                      </button>
                    );
                  })}
                </div>
              </Panel>

              {/* Sandbox Specifications Card */}
              <Panel title="Sandbox Architecture">
                <div style={{ fontSize: '12px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  <div style={{ display: 'flex', gap: '8px', alignItems: 'flex-start' }}>
                    <ShieldCheck size={16} style={{ color: 'var(--teal)', marginTop: '2px' }} />
                    <div>
                      <strong>Pre-flight Reproduction</strong>
                      <p style={{ fontSize: '11px', marginTop: '2px' }}>
                        Reproduction test must fail on the base code before applying candidate diff.
                      </p>
                    </div>
                  </div>
                  <div style={{ display: 'flex', gap: '8px', alignItems: 'flex-start' }}>
                    <Layers size={16} style={{ color: 'var(--primary)', marginTop: '2px' }} />
                    <div>
                      <strong>Isolated Execution</strong>
                      <p style={{ fontSize: '11px', marginTop: '2px' }}>
                        Ephemeral temporary sandbox, stripped environment variables, and strict timeouts.
                      </p>
                    </div>
                  </div>
                  <div style={{ display: 'flex', gap: '8px', alignItems: 'flex-start' }}>
                    <Hash size={16} style={{ color: 'var(--purple)', marginTop: '2px' }} />
                    <div>
                      <strong>Revision Hashing</strong>
                      <p style={{ fontSize: '11px', marginTop: '2px' }}>
                        Deterministic SHA-256 tree hashing guarantees base application immutability.
                      </p>
                    </div>
                  </div>
                </div>
              </Panel>
            </div>

            {/* Active Candidate Inspection & Testing Details */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
              <QueryState query={qIncident}>
                {incident && (
                  <>
                    {/* Header Bar */}
                    <div
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'flex-start',
                        flexWrap: 'wrap',
                        gap: '12px',
                        padding: '16px 20px',
                        background: 'var(--surface)',
                        border: '1px solid var(--border)',
                        borderRadius: '10px',
                      }}
                    >
                      <div>
                        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                          <span
                            style={{
                              fontSize: '11px',
                              fontFamily: 'monospace',
                              fontWeight: 700,
                              color: 'var(--primary)',
                            }}
                          >
                            {incident.id.toUpperCase().replace('_', '–')}
                          </span>
                          <span>·</span>
                          <span style={{ fontSize: '12px', color: 'var(--muted)' }}>{appName}</span>
                          <Badge value={incident.severity} />
                        </div>
                        <h2 style={{ fontSize: '18px', marginTop: '4px' }}>{incident.message}</h2>
                        <div
                          style={{
                            display: 'flex',
                            gap: '12px',
                            alignItems: 'center',
                            marginTop: '6px',
                            fontSize: '12px',
                            color: 'var(--muted)',
                          }}
                        >
                          <span>Error: <code>{incident.error_type}</code></span>
                          <span>Base Rev: <code>{incident.repository_revision}</code></span>
                          <span>Detected: {time(incident.detected_at)}</span>
                        </div>
                      </div>

                      <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                        <Link
                          className="button"
                          to={`/incidents/${incident.id}`}
                          style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}
                        >
                          Incident Details <ArrowUpRight size={14} />
                        </Link>
                        {validation?.status === 'passed' && (
                          <Link
                            className="button primary"
                            to={`/approval-recovery?incident=${incident.id}`}
                            style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}
                          >
                            Review for Approval <ArrowRight size={14} />
                          </Link>
                        )}
                      </div>
                    </div>

                    {/* Patch & Diff Review Component */}
                    {currentPatch ? (
                      <>
                        <PatchReview patch={currentPatch} validation={validation || null} />

                        {/* Detailed Test Suite Breakdown */}
                        {validation && (
                          <Panel
                            title="Automated Test Suite Breakdown"
                            action={
                              <span className="muted-caption">
                                {validation.duration_ms} MS TOTAL EXECUTION
                              </span>
                            }
                          >
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                              {validation.checks.map((check) => {
                                const isPassed = check.status === 'passed';
                                return (
                                  <div
                                    key={check.name}
                                    style={{
                                      padding: '14px',
                                      borderRadius: '8px',
                                      border: `1px solid ${isPassed ? 'var(--border)' : 'var(--danger-text)'}`,
                                      background: isPassed ? 'var(--surface)' : 'var(--danger-surface)',
                                      display: 'flex',
                                      flexDirection: 'column',
                                      gap: '8px',
                                    }}
                                  >
                                    <div
                                      style={{
                                        display: 'flex',
                                        justifyContent: 'space-between',
                                        alignItems: 'center',
                                      }}
                                    >
                                      <div
                                        style={{
                                          display: 'flex',
                                          alignItems: 'center',
                                          gap: '8px',
                                        }}
                                      >
                                        {isPassed ? (
                                          <CheckCircle2 size={17} style={{ color: 'var(--teal)' }} />
                                        ) : (
                                          <XCircle size={17} style={{ color: 'var(--danger-text)' }} />
                                        )}
                                        <strong style={{ fontSize: '13px' }}>
                                          {label(check.name)}
                                        </strong>
                                      </div>
                                      <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                                        <span style={{ fontSize: '11px', color: 'var(--muted)' }}>
                                          Exit Code {check.exit_code} · {check.duration_ms} ms
                                        </span>
                                        <Badge value={check.status} />
                                      </div>
                                    </div>
                                    <pre
                                      className="code-block"
                                      style={{
                                        margin: 0,
                                        fontSize: '11px',
                                        maxHeight: '120px',
                                        overflowY: 'auto',
                                      }}
                                    >
                                      {check.evidence}
                                    </pre>
                                  </div>
                                );
                              })}
                            </div>
                          </Panel>
                        )}

                        {/* Next Actions & Stage Handoff */}
                        <div
                          className="notice inline-notice"
                          style={{
                            background:
                              validation?.status === 'passed'
                                ? 'var(--tint)'
                                : 'var(--surface)',
                          }}
                        >
                          {validation?.status === 'passed' ? (
                            <ShieldCheck size={24} style={{ color: 'var(--teal)' }} />
                          ) : (
                            <ShieldAlert size={24} style={{ color: 'var(--danger-text)' }} />
                          )}
                          <div style={{ flex: 1 }}>
                            <strong>
                              {validation?.status === 'passed'
                                ? 'All validation checks passed'
                                : 'Validation checks require attention'}
                            </strong>
                            <p>
                              {validation?.status === 'passed'
                                ? 'The candidate diff successfully fixed reproduction errors without regressing other features. Ready for human developer review.'
                                : 'Automated test suite reported failures. The repair agent may need to formulate a revised candidate patch.'}
                            </p>
                          </div>
                          {validation?.status === 'passed' ? (
                            <Link
                              className="button primary"
                              to={`/approval-recovery?incident=${incident.id}`}
                            >
                              Open in Approval & Recovery <ArrowRight size={14} />
                            </Link>
                          ) : (
                            <Link
                              className="button"
                              to={`/incidents/${incident.id}?tab=diagnosis`}
                            >
                              Inspect Diagnosis <ArrowUpRight size={14} />
                            </Link>
                          )}
                        </div>
                      </>
                    ) : (
                      <Panel>
                        <Empty message="No candidate patch generated for this incident yet. Review the incident diagnosis or logs." />
                      </Panel>
                    )}
                  </>
                )}
              </QueryState>
            </div>
          </div>
        )}
      </QueryState>
    </>
  );
}
