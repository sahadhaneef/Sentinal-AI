import { useSearchParams, Link } from 'react-router-dom';
import {
  ArrowUpRight,
  CheckCircle2,
  ClipboardCheck,
  FileCode2,
  FlaskConical,
  GitBranch,
  History,
  Lock,
  Play,
  RotateCcw,
  ShieldAlert,
  ShieldCheck,
  Terminal,
} from 'lucide-react';
import { useIncident, useIncidents, useApplications } from '../hooks/queries';
import { Badge, CopyButton, Empty, Heading, Panel, QueryState } from '../components/ui';
import { PatchReview } from '../components/patches';
import { ReviewActions } from '../components/ReviewActions';
import { Outcome } from '../components/Outcome';
import { time } from '../lib/format';
import { reviewAccess } from '../lib/approval';
import { isDemo } from '../api/client';

export function ApprovalRecoveryPage() {
  const [params, setParams] = useSearchParams();
  const applications = useApplications();
  const viewFilter = params.get('view') || 'pending';
  const isPendingOnly = viewFilter === 'pending';

  // Load incidents in review queue
  const qQueue = useIncidents({
    limit: 10,
    scope: isPendingOnly ? 'pending' : 'candidates',
    sort: 'detected_desc',
  });

  const items = qQueue.data?.data.items || [];
  const selectedId = params.get('incident') || items[0]?.id || '';

  const qIncident = useIncident(selectedId);
  const incident = qIncident.data?.data;
  const currentPatch = incident?.patches.at(-1);
  const validation = incident?.validation;
  const access = incident ? reviewAccess(incident) : { canApprove: false, canReject: false, canApply: false };

  const appName =
    applications.data?.data.find((a) => a.id === incident?.application_id)?.name ||
    incident?.application_id ||
    'Application';

  // Determine recovery steps state
  const isApproved = ['approved', 'applying', 'verifying', 'resolved', 'unresolved'].includes(incident?.status || '');
  const isApplying = ['applying', 'verifying', 'resolved', 'unresolved'].includes(incident?.status || '');
  const isVerifying = ['verifying', 'resolved', 'unresolved'].includes(incident?.status || '');
  const isResolved = incident?.status === 'resolved';
  const isUnresolved = incident?.status === 'unresolved';
  const isRejected = incident?.status === 'rejected';

  return (
    <>
      <Heading
        title="Approval & Recovery"
        description="The human decision checkpoint. Review verified candidate patches, grant explicit developer approval, and supervise controlled recovery."
      />

      {/* Human in the loop Banner */}
      <div className="review-banner" style={{ marginBottom: '24px' }}>
        <span>
          <ClipboardCheck size={26} />
        </span>
        <div>
          <strong>Human-in-the-Loop Governance: Your Authorization Required</strong>
          <p>
            Automated test results inform your decision. No patch is ever applied without direct developer approval.
            Patch application and verification are executed as separate controlled steps.
          </p>
        </div>
        <span className="review-banner-tag">STAGE: HUMAN APPROVAL</span>
      </div>

      {/* Queue Filter Tabs */}
      <div className="filters" style={{ marginBottom: '20px' }}>
        <button
          type="button"
          className={`button ${isPendingOnly ? 'primary' : ''}`}
          onClick={() => {
            const next = new URLSearchParams(params);
            next.set('view', 'pending');
            setParams(next);
          }}
        >
          Awaiting Decision
        </button>
        <button
          type="button"
          className={`button ${!isPendingOnly ? 'primary' : ''}`}
          onClick={() => {
            const next = new URLSearchParams(params);
            next.set('view', 'all');
            setParams(next);
          }}
        >
          All Candidates
        </button>
      </div>

      <QueryState query={qQueue}>
        {items.length === 0 ? (
          <Panel>
            <Empty
              message={
                isPendingOnly
                  ? 'No incidents currently awaiting your decision. Switch to "All Candidates" to inspect past reviews.'
                  : 'No candidate patches available in the queue.'
              }
            />
          </Panel>
        ) : (
          <div className="detail-grid" style={{ gridTemplateColumns: '320px minmax(0, 1fr)' }}>
            {/* Left Queue List */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <Panel
                title="Review Queue"
                action={<span className="muted-caption">{items.length} ITEMS</span>}
              >
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {items.map((item) => {
                    const isSelected = item.id === selectedId;
                    return (
                      <button
                        key={item.id}
                        type="button"
                        onClick={() => {
                          const next = new URLSearchParams(params);
                          next.set('incident', item.id);
                          setParams(next);
                        }}
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
                          <span>{time(item.detected_at)}</span>
                        </div>
                      </button>
                    );
                  })}
                </div>
              </Panel>
            </div>

            {/* Right Review & Decision Workspace */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
              <QueryState query={qIncident}>
                {incident && (
                  <>
                    {/* Header Summary */}
                    <div
                      style={{
                        padding: '16px 20px',
                        background: 'var(--surface)',
                        border: '1px solid var(--border)',
                        borderRadius: '10px',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'flex-start',
                        flexWrap: 'wrap',
                        gap: '12px',
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
                          <Badge value={incident.status} />
                        </div>
                        <h2 style={{ fontSize: '18px', marginTop: '4px' }}>{incident.message}</h2>
                        <p style={{ fontSize: '12px', marginTop: '4px' }}>
                          Repository Revision: <code>{incident.repository_revision}</code> · Severity:{' '}
                          <Badge value={incident.severity} />
                        </p>
                      </div>

                      <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                        <Link
                          className="button"
                          to={`/repair-testing?incident=${incident.id}`}
                          style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}
                        >
                          View Full Tests <ArrowUpRight size={14} />
                        </Link>
                        <Link
                          className="button"
                          to={`/incidents/${incident.id}`}
                          style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}
                        >
                          Incident Details <ArrowUpRight size={14} />
                        </Link>
                      </div>
                    </div>

                    {/* 4-Step Recovery Tracker */}
                    <Panel title="Controlled Recovery Workflow">
                      <div
                        style={{
                          display: 'grid',
                          gridTemplateColumns: 'repeat(4, 1fr)',
                          gap: '12px',
                          margin: '8px 0',
                        }}
                      >
                        {/* Step 1: Human Approval */}
                        <div
                          style={{
                            padding: '12px',
                            borderRadius: '8px',
                            border: `1px solid ${isApproved ? 'var(--teal)' : isRejected ? 'var(--danger-text)' : 'var(--border)'}`,
                            background: isApproved ? 'var(--tint)' : 'var(--surface)',
                            display: 'flex',
                            flexDirection: 'column',
                            gap: '4px',
                          }}
                        >
                          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px' }}>
                            <span style={{ fontWeight: 700 }}>1. Approval</span>
                            {isApproved && <CheckCircle2 size={14} style={{ color: 'var(--teal)' }} />}
                            {isRejected && <span style={{ color: 'var(--danger-text)' }}>✕</span>}
                          </div>
                          <span style={{ fontSize: '11px', color: 'var(--muted)' }}>
                            {isRejected ? 'Rejected by developer' : isApproved ? 'Approved by developer' : 'Awaiting decision'}
                          </span>
                        </div>

                        {/* Step 2: Application */}
                        <div
                          style={{
                            padding: '12px',
                            borderRadius: '8px',
                            border: `1px solid ${isApplying ? 'var(--teal)' : 'var(--border)'}`,
                            background: isApplying ? 'var(--tint)' : 'var(--surface)',
                            display: 'flex',
                            flexDirection: 'column',
                            gap: '4px',
                          }}
                        >
                          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px' }}>
                            <span style={{ fontWeight: 700 }}>2. Applying</span>
                            {isApplying && <CheckCircle2 size={14} style={{ color: 'var(--teal)' }} />}
                          </div>
                          <span style={{ fontSize: '11px', color: 'var(--muted)' }}>
                            {isApplying ? 'Patch safely applied' : 'Requires separate action'}
                          </span>
                        </div>

                        {/* Step 3: Verification */}
                        <div
                          style={{
                            padding: '12px',
                            borderRadius: '8px',
                            border: `1px solid ${isVerifying ? (isUnresolved ? 'var(--danger-text)' : 'var(--teal)') : 'var(--border)'}`,
                            background: isVerifying ? 'var(--tint)' : 'var(--surface)',
                            display: 'flex',
                            flexDirection: 'column',
                            gap: '4px',
                          }}
                        >
                          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px' }}>
                            <span style={{ fontWeight: 700 }}>3. Verifying</span>
                            {isResolved && <CheckCircle2 size={14} style={{ color: 'var(--teal)' }} />}
                          </div>
                          <span style={{ fontSize: '11px', color: 'var(--muted)' }}>
                            {isResolved ? 'Post-apply tests passed' : isUnresolved ? 'Verification failed' : 'Pending patch'}
                          </span>
                        </div>

                        {/* Step 4: Outcome */}
                        <div
                          style={{
                            padding: '12px',
                            borderRadius: '8px',
                            border: `1px solid ${isResolved ? 'var(--teal)' : isUnresolved ? 'var(--danger-text)' : 'var(--border)'}`,
                            background: isResolved ? 'var(--tint)' : 'var(--surface)',
                            display: 'flex',
                            flexDirection: 'column',
                            gap: '4px',
                          }}
                        >
                          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px' }}>
                            <span style={{ fontWeight: 700 }}>4. Recovered</span>
                            {isResolved && <CheckCircle2 size={14} style={{ color: 'var(--teal)' }} />}
                          </div>
                          <span style={{ fontSize: '11px', color: 'var(--muted)' }}>
                            {isResolved ? 'Recovered & logged' : isUnresolved ? 'Restored & recorded' : 'Final state'}
                          </span>
                        </div>
                      </div>
                    </Panel>

                    {/* Developer Decision Controls (Approve, Reject, Apply) */}
                    <div style={{ margin: '8px 0' }}>
                      <ReviewActions incident={incident} />
                    </div>

                    {/* Proposed Code Patch & Diff Review */}
                    {currentPatch ? (
                      <PatchReview patch={currentPatch} validation={validation || null} />
                    ) : (
                      <Panel>
                        <Empty message="No candidate patch available for this incident." />
                      </Panel>
                    )}

                    {/* Post-Resolution Outcome Report (if applied or resolved) */}
                    <div style={{ marginTop: '8px' }}>
                      <Outcome incident={incident} />
                    </div>
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
