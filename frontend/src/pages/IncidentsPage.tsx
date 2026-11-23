import { useSearchParams, Link } from 'react-router-dom';
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  ArrowUpRight,
  CheckCircle2,
  Clock3,
  Filter,
  Search,
  ShieldAlert,
  Wrench,
} from 'lucide-react';
import { useApplications, useIncidents } from '../hooks/queries';
import { useDebouncedValue } from '../hooks/useDebouncedValue';
import { runStateSchema, severitySchema, incidentSortSchema } from '../contracts/schemas';
import { Badge, Empty, Heading, Panel, QueryState } from '../components/ui';
import { Pagination } from '../components/Pagination';
import { filterParams } from '../lib/pagination';
import { label, time } from '../lib/format';

export function IncidentsPage({ history = false }: { history?: boolean }) {
  const [params, setParams] = useSearchParams(),
    applications = useApplications();
  const search = params.get('search') || '',
    settledSearch = useDebouncedValue(search);
  const status = runStateSchema.safeParse(params.get('status')),
    severity = severitySchema.safeParse(params.get('severity'));
  const sort = incidentSortSchema.safeParse(params.get('sort'));
  const scope = history ? 'closed' : params.get('view') === 'open' ? 'open' : 'all';

  const query = useIncidents({
    status: status.success ? status.data : undefined,
    severity: severity.success ? severity.data : undefined,
    search: settledSearch,
    application_id: params.get('application_id') || undefined,
    cursor: params.get('cursor') || undefined,
    limit: 10,
    scope,
    sort: sort.success ? sort.data : 'detected_desc',
  });

  const update = (key: string, value: string, replace = false) =>
    setParams(filterParams(params, key, value), { replace });

  const items = query.data?.data.items || [];

  return (
    <>
      <Heading
        title={history ? 'Incident History' : 'Incidents'}
        description={
          history
            ? 'Decisions, verification and actual outcomes. Open a record to read its post-mortem report.'
            : 'Autonomous detection, live error logs, and investigation statuses across monitored applications.'
        }
      />

      {/* Overview Metric Bar */}
      {!history && (
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
              <Activity size={20} />
            </div>
            <div>
              <span style={{ fontSize: '11px', color: 'var(--muted)', fontWeight: 600 }}>
                ACTIVE QUEUE
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
              <Wrench size={20} />
            </div>
            <div>
              <span style={{ fontSize: '11px', color: 'var(--muted)', fontWeight: 600 }}>
                CANDIDATES & TESTS
              </span>
              <h3 style={{ fontSize: '20px', marginTop: '2px' }}>
                <Link to="/repair-testing" style={{ color: 'inherit' }}>
                  Explore Queue →
                </Link>
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
                color: 'var(--purple)',
              }}
            >
              <CheckCircle2 size={20} />
            </div>
            <div>
              <span style={{ fontSize: '11px', color: 'var(--muted)', fontWeight: 600 }}>
                HUMAN APPROVALS
              </span>
              <h3 style={{ fontSize: '20px', marginTop: '2px' }}>
                <Link to="/approval-recovery" style={{ color: 'inherit' }}>
                  Review Now →
                </Link>
              </h3>
            </div>
          </div>
        </div>
      )}

      {/* Filter Toolbar */}
      <div className="filters">
        <label className="search-input">
          <Search size={17} aria-hidden />
          <input
            aria-label="Search incidents"
            placeholder="Search ID, error type, or description…"
            value={search}
            onChange={(e) => update('search', e.target.value, true)}
          />
        </label>
        {!history && (
          <select
            aria-label="Incident scope"
            value={scope}
            onChange={(e) => update('view', e.target.value === 'open' ? 'open' : '')}
          >
            <option value="all">All incidents</option>
            <option value="open">Open incidents only</option>
          </select>
        )}
        <select
          aria-label="Filter status"
          value={status.success ? status.data : ''}
          onChange={(e) => update('status', e.target.value)}
        >
          <option value="">All statuses</option>
          {runStateSchema.options.map((value) => (
            <option key={value} value={value}>
              {label(value)}
            </option>
          ))}
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
          aria-label="Sort incidents"
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

      {applications.isError && (
        <p className="notice" role="status">
          Application names are unavailable. Incident IDs and filters remain usable.
        </p>
      )}

      {/* Incident List */}
      <Panel
        title={history ? 'Closed incident records' : 'Incident Queue'}
        action={<span className="muted-caption">{query.data?.data.total ?? '—'} INCIDENTS</span>}
      >
        <QueryState query={query}>
          {items.length === 0 ? (
            <Empty message="No incidents match the active filter criteria." />
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <div className="incident-table-head" aria-hidden="true">
                <span>INCIDENT & SERVICE</span>
                <span>SEVERITY</span>
                <span>STATUS</span>
                <span>DETECTED</span>
                <span>ACTIONS</span>
              </div>
              <ul className="incident-list">
                {items.map((i) => {
                  const hasCandidate = [
                    'validating',
                    'awaiting_approval',
                    'approved',
                    'applying',
                    'verifying',
                  ].includes(i.status);

                  return (
                    <li key={i.id}>
                      <div
                        className="incident-row"
                        style={{
                          display: 'grid',
                          gridTemplateColumns: 'minmax(0, 2fr) 110px 140px 140px 130px',
                          alignItems: 'center',
                        }}
                      >
                        <div>
                          <span className="incident-id">{i.id.toUpperCase().replace('_', '–')}</span>
                          <strong>{i.message}</strong>
                          <small>
                            <code>{i.error_type}</code> <span>·</span>{' '}
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

                        <span className="incident-time">
                          {time(i.detected_at)}
                        </span>

                        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                          {hasCandidate && (
                            <Link
                              className="button"
                              to={`/repair-testing?incident=${i.id}`}
                              style={{
                                padding: '6px 8px',
                                fontSize: '11px',
                                display: 'inline-flex',
                                alignItems: 'center',
                                gap: '4px',
                              }}
                              title="Inspect tests & candidate diff"
                            >
                              <Wrench size={12} /> Tests
                            </Link>
                          )}
                          <Link
                            className="button"
                            to={`/incidents/${i.id}`}
                            style={{
                              padding: '6px 8px',
                              fontSize: '11px',
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: '4px',
                            }}
                            aria-label={`Open incident ${i.id}`}
                          >
                            Details <ArrowUpRight size={13} />
                          </Link>
                        </div>
                      </div>
                    </li>
                  );
                })}
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
