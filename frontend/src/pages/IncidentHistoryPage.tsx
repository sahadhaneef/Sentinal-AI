import { useState } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import {
  Archive,
  ArrowUpRight,
  CheckCircle2,
  Clock,
  FileCheck2,
  FileClock,
  FileText,
  Filter,
  Search,
  ShieldAlert,
  ShieldCheck,
  XCircle,
} from 'lucide-react';
import { useApplications, useIncidents } from '../hooks/queries';
import { useDebouncedValue } from '../hooks/useDebouncedValue';
import { runStateSchema, severitySchema, incidentSortSchema } from '../contracts/schemas';
import { Badge, Dialog, Empty, Heading, Panel, QueryState } from '../components/ui';
import { Pagination } from '../components/Pagination';
import { filterParams } from '../lib/pagination';
import { label, time } from '../lib/format';
import type { Incident } from '../contracts/types';

export function IncidentHistoryPage() {
  const [params, setParams] = useSearchParams(),
    applications = useApplications();

  const [activeReportIncident, setActiveReportIncident] = useState<Incident | null>(null);

  const search = params.get('search') || '',
    settledSearch = useDebouncedValue(search);

  const status = runStateSchema.safeParse(params.get('status')),
    severity = severitySchema.safeParse(params.get('severity'));
  const sort = incidentSortSchema.safeParse(params.get('sort'));

  // Closed / historical incidents scope
  const query = useIncidents({
    status: status.success ? status.data : undefined,
    severity: severity.success ? severity.data : undefined,
    search: settledSearch,
    application_id: params.get('application_id') || undefined,
    cursor: params.get('cursor') || undefined,
    limit: 10,
    scope: 'closed',
    sort: sort.success ? sort.data : 'detected_desc',
  });

  const update = (key: string, value: string, replace = false) =>
    setParams(filterParams(params, key, value), { replace });

  const items = query.data?.data.items || [];

  // Compute metrics from query results
  const resolvedCount = items.filter((i) => i.status === 'resolved').length;
  const rejectedCount = items.filter((i) => i.status === 'rejected').length;
  const unresolvedCount = items.filter((i) => i.status === 'unresolved').length;

  return (
    <>
      <Heading
        title="Incident History & Audit"
        description="Permanent archive of past incidents, human decisions, verification outcomes, and post-mortem resolution reports."
      />

      {/* Historical Summary Metric Cards */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
          gap: '16px',
          marginBottom: '24px',
        }}
      >
        <div
          style={{
            padding: '16px',
            background: 'var(--surface)',
            border: '1px solid var(--border)',
            borderRadius: '10px',
            display: 'flex',
            alignItems: 'center',
            gap: '12px',
          }}
        >
          <div
            style={{
              padding: '10px',
              borderRadius: '8px',
              background: 'var(--tint)',
              color: 'var(--primary)',
            }}
          >
            <Archive size={20} />
          </div>
          <div>
            <span style={{ fontSize: '11px', color: 'var(--muted)', fontWeight: 600 }}>
              TOTAL ARCHIVED
            </span>
            <h3 style={{ fontSize: '20px', marginTop: '2px' }}>
              {query.data?.data.total ?? '—'}
            </h3>
          </div>
        </div>

        <div
          style={{
            padding: '16px',
            background: 'var(--surface)',
            border: '1px solid var(--border)',
            borderRadius: '10px',
            display: 'flex',
            alignItems: 'center',
            gap: '12px',
          }}
        >
          <div
            style={{
              padding: '10px',
              borderRadius: '8px',
              background: 'var(--tint)',
              color: 'var(--teal)',
            }}
          >
            <CheckCircle2 size={20} />
          </div>
          <div>
            <span style={{ fontSize: '11px', color: 'var(--muted)', fontWeight: 600 }}>
              RECOVERED & RESOLVED
            </span>
            <h3 style={{ fontSize: '20px', marginTop: '2px' }}>{resolvedCount}</h3>
          </div>
        </div>

        <div
          style={{
            padding: '16px',
            background: 'var(--surface)',
            border: '1px solid var(--border)',
            borderRadius: '10px',
            display: 'flex',
            alignItems: 'center',
            gap: '12px',
          }}
        >
          <div
            style={{
              padding: '10px',
              borderRadius: '8px',
              background: 'var(--danger-surface)',
              color: 'var(--danger-text)',
            }}
          >
            <XCircle size={20} />
          </div>
          <div>
            <span style={{ fontSize: '11px', color: 'var(--muted)', fontWeight: 600 }}>
              REJECTED CANDIDATES
            </span>
            <h3 style={{ fontSize: '20px', marginTop: '2px' }}>{rejectedCount}</h3>
          </div>
        </div>

        <div
          style={{
            padding: '16px',
            background: 'var(--surface)',
            border: '1px solid var(--border)',
            borderRadius: '10px',
            display: 'flex',
            alignItems: 'center',
            gap: '12px',
          }}
        >
          <div
            style={{
              padding: '10px',
              borderRadius: '8px',
              background: 'var(--surface)',
              color: 'var(--muted)',
            }}
          >
            <ShieldAlert size={20} />
          </div>
          <div>
            <span style={{ fontSize: '11px', color: 'var(--muted)', fontWeight: 600 }}>
              UNRESOLVED / RESTORED
            </span>
            <h3 style={{ fontSize: '20px', marginTop: '2px' }}>{unresolvedCount}</h3>
          </div>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="filters">
        <label className="search-input">
          <Search size={17} aria-hidden />
          <input
            aria-label="Search incident history"
            placeholder="Search past ID, error type, or message…"
            value={search}
            onChange={(e) => update('search', e.target.value, true)}
          />
        </label>

        <select
          aria-label="Filter status"
          value={status.success ? status.data : ''}
          onChange={(e) => update('status', e.target.value)}
        >
          <option value="">All terminal outcomes</option>
          <option value="resolved">Resolved</option>
          <option value="rejected">Rejected</option>
          <option value="unresolved">Unresolved / Restored</option>
        </select>

        <select
          aria-label="Filter severity"
          value={severity.success ? severity.data : ''}
          onChange={(e) => update('severity', e.target.value)}
        >
          <option value="">All severities</option>
          {severitySchema.options.map((value) => (
            <option key={value} value={value}>
              {label(value)}
            </option>
          ))}
        </select>

        <select
          aria-label="Filter application"
          value={params.get('application_id') || ''}
          onChange={(e) => update('application_id', e.target.value)}
        >
          <option value="">All applications</option>
          {applications.data?.data.map((app) => (
            <option key={app.id} value={app.id}>
              {app.name}
            </option>
          ))}
        </select>

        <select
          aria-label="Sort history"
          value={sort.success ? sort.data : 'detected_desc'}
          onChange={(e) => update('sort', e.target.value)}
        >
          <option value="detected_desc">Newest first</option>
          <option value="detected_asc">Oldest first</option>
          <option value="severity_desc">Highest severity</option>
        </select>

        {params.size > 0 && (
          <button className="button" onClick={() => setParams({})}>
            Clear filters
          </button>
        )}
      </div>

      {/* Historical Incidents Table */}
      <Panel
        title="Historical Incident Records"
        action={
          <span className="muted-caption">
            {query.data?.data.total ?? '—'} ARCHIVED RECORDS
          </span>
        }
      >
        <QueryState query={query}>
          {items.length === 0 ? (
            <Empty message="No archived incidents matched the selected filters." />
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <div className="incident-table-head" aria-hidden="true">
                <span>INCIDENT & CAUSE</span>
                <span>SEVERITY</span>
                <span>OUTCOME</span>
                <span>DETECTED / RESOLVED</span>
                <span>ACTIONS</span>
              </div>

              <ul className="incident-list">
                {items.map((i) => (
                  <li key={i.id}>
                    <div
                      className="incident-row"
                      style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 2fr) 110px 130px 150px 140px', alignItems: 'center' }}
                    >
                      <div>
                        <span className="incident-id">{i.id.toUpperCase().replace('_', '–')}</span>
                        <strong>{i.message}</strong>
                        <small>
                          {i.error_type} <span>·</span>{' '}
                          {applications.data?.data.find((a) => a.id === i.application_id)?.name ||
                            i.application_id}
                        </small>
                      </div>

                      <span>
                        <Badge value={i.severity} />
                      </span>

                      <span>
                        <Badge value={i.status} />
                      </span>

                      <span className="incident-time" style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                        <span>{time(i.detected_at)}</span>
                        {i.resolved_at && (
                          <small style={{ fontSize: '10px', color: 'var(--muted)' }}>
                            Resolved {time(i.resolved_at)}
                          </small>
                        )}
                      </span>

                      <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                        <Link
                          className="button"
                          to={`/incidents/${i.id}?tab=report`}
                          style={{
                            padding: '6px 10px',
                            fontSize: '11px',
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '4px',
                          }}
                        >
                          <FileText size={13} /> Report
                        </Link>
                        <Link
                          className="button"
                          to={`/incidents/${i.id}`}
                          style={{
                            padding: '6px 8px',
                            fontSize: '11px',
                          }}
                          aria-label="Open incident details"
                        >
                          <ArrowUpRight size={13} />
                        </Link>
                      </div>
                    </div>
                  </li>
                ))}
              </ul>

              <Pagination
                nextCursor={query.data?.data.next_cursor}
                total={query.data?.data.total || 0}
                busy={query.isFetching}
              />
            </div>
          )}
        </QueryState>
      </Panel>
    </>
  );
}
