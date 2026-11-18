import { useSearchParams } from 'react-router-dom';
import { Search } from 'lucide-react';
import { useApplications, useIncidents } from '../hooks/queries';
import { useDebouncedValue } from '../hooks/useDebouncedValue';
import { runStateSchema, severitySchema, incidentSortSchema } from '../contracts/schemas';
import { Heading, Panel, QueryState } from '../components/ui';
import { IncidentList } from '../components/incidents';
import { Pagination } from '../components/Pagination';
import { filterParams } from '../lib/pagination';
import { label } from '../lib/format';

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
    limit: 5,
    scope,
    sort: sort.success ? sort.data : 'detected_desc',
  });
  const update = (key: string, value: string, replace = false) =>
    setParams(filterParams(params, key, value), { replace });
  return (
    <>
      <Heading
        title={history ? 'Incident History' : 'Incidents'}
        description={
          history
            ? 'Decisions, verification and actual outcomes. Open a record to read its report.'
            : 'Find the signal that needs your attention, then explore its evidence and next steps.'
        }
      />
      <div className="filters">
        <label className="search-input">
          <Search size={17} aria-hidden />
          <input
            aria-label="Search incidents"
            placeholder="Search ID, error or description…"
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
            <option value="open">Open incidents</option>
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
      <Panel
        title={history ? 'Closed incident records' : 'Incident queue'}
        action={<span className="muted-caption">{query.data?.data.total ?? '—'} INCIDENTS</span>}
      >
        <QueryState query={query}>
          <IncidentList incidents={query.data?.data.items || []} />
          <Pagination
            nextCursor={query.data?.data.next_cursor}
            total={query.data?.data.total || 0}
            busy={query.isFetching}
          />
        </QueryState>
      </Panel>
    </>
  );
}
