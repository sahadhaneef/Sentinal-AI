import { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ArrowRight, GitBranch, Radio, Search, Server } from 'lucide-react';
import { useApplication, useApplications, useIncidents, useMonitoring } from '../hooks/queries';
import { Badge, Busy, Dialog, Empty, Heading, Panel, QueryState } from '../components/ui';
import { useNotify } from '../components/feedback';
import { IncidentList } from '../components/incidents';
import { isDemo } from '../api/client';
export function ApplicationsPage() {
  const q = useApplications(),
    [search, setSearch] = useState(''),
    [status, setStatus] = useState('');
  const apps = (q.data?.data || []).filter(
    (a) => a.name.toLowerCase().includes(search.toLowerCase()) && (!status || a.status === status),
  );
  return (
    <>
      <Heading
        title="Applications"
        description="One designated local sample. A focused place to understand and validate the workflow."
      />
      <div className="filters">
        <label className="search-input">
          <Search size={17} />
          <input
            aria-label="Search applications"
            placeholder="Search applications…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </label>
        <select
          aria-label="Application status"
          value={status}
          onChange={(e) => setStatus(e.target.value)}
        >
          <option value="">All statuses</option>
          {['healthy', 'degraded', 'offline'].map((s) => (
            <option key={s}>{s}</option>
          ))}
        </select>
      </div>
      <QueryState query={q}>
        <div className="app-grid">
          {apps.map((a) => (
            <Panel key={a.id}>
              <div className="app-card-header">
                <span className="agent-icon">
                  <Server />
                </span>
                <Badge value={a.status} />
              </div>
              <h2 className="spaced">{a.name}</h2>
              <p className="spaced">{a.description}</p>
              <div className="metadata">
                <span>
                  <GitBranch size={14} /> {a.repository_revision}
                </span>
                <span>
                  <Radio size={14} /> Monitoring {a.monitoring_enabled ? 'enabled' : 'paused'}
                </span>
              </div>
              <Link className="text-link" to={`/applications/${a.id}`}>
                Open application <ArrowRight size={15} />
              </Link>
            </Panel>
          ))}
        </div>
        {!apps.length && <Empty />}
      </QueryState>
    </>
  );
}
export function ApplicationDetailPage() {
  const { id = '' } = useParams(),
    q = useApplication(id),
    inc = useIncidents({ application_id: id }),
    notify = useNotify(),
    [confirm, setConfirm] = useState(false);
  const a = q.data?.data;
  const mutation = useMonitoring(id);
  return (
    <>
      <Heading
        title={a?.name || 'Application details'}
        description="Configured sample, revision, monitoring preferences and linked incidents."
      />
      <QueryState query={q}>
        {a && (
          <>
            <Panel title="Sample application" action={<Badge value={a.status} />}>
              <p>{a.description}</p>
              <div className="metadata">
                <span>
                  <GitBranch size={15} /> Revision {a.repository_revision}
                </span>
                <span>
                  <Radio size={15} /> Monitoring {a.monitoring_enabled ? 'enabled' : 'paused'}
                </span>
              </div>
              <p>Supported errors: {a.supported_errors.join(', ')}</p>
              <button className="button spaced" disabled={!isDemo} onClick={() => setConfirm(true)}>
                {a.monitoring_enabled ? 'Stop' : 'Start'} monitoring
              </button>
              <p className="notice">
                {isDemo
                  ? 'Monitoring is simulated in demo mode. Server workspace paths remain backend-owned.'
                  : 'Read-only API phase. A monitoring worker and monitoring controls are not implemented yet.'}
              </p>
            </Panel>
            <Panel
              className="spaced"
              title="Related incidents"
              action={
                <Link
                  className="text-link"
                  to={`/incidents?application_id=${encodeURIComponent(id)}`}
                >
                  View all incidents <ArrowRight size={14} />
                </Link>
              }
            >
              <QueryState query={inc}>
                <IncidentList incidents={inc.data?.data.items || []} />
              </QueryState>
            </Panel>
          </>
        )}
      </QueryState>
      <Dialog
        open={confirm}
        title={`${a?.monitoring_enabled ? 'Stop' : 'Start'} monitoring?`}
        onClose={() => setConfirm(false)}
      >
        <p>
          This changes the designated sample’s monitoring preference. In demo mode no log reader is
          started or stopped.
        </p>
        <div className="dialog-actions">
          <button className="button" onClick={() => setConfirm(false)}>
            Cancel
          </button>
          <button
            className="button primary"
            disabled={mutation.isPending}
            onClick={() =>
              mutation.mutate(!a?.monitoring_enabled, {
                onSuccess: () => {
                  setConfirm(false);
                  notify('Monitoring preference updated.');
                },
                onError: (e) => notify(e.message),
              })
            }
          >
            {mutation.isPending ? <Busy /> : 'Confirm monitoring change'}
          </button>
        </div>
      </Dialog>
    </>
  );
}
