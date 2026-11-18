import { ArrowUpRight, ChevronRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import type { Incident } from '../contracts/types';
import { time } from '../lib/format';
import { Badge, Empty } from './ui';
import { useApplications } from '../hooks/queries';
export function IncidentList({ incidents }: { incidents: Incident[] }) {
  const applications = useApplications();
  if (!incidents.length) return <Empty />;
  return (
    <>
      <div className="incident-table-head" aria-hidden="true">
        <span>INCIDENT</span>
        <span>SEVERITY</span>
        <span>STATUS</span>
        <span>DETECTED</span>
        <span />
      </div>
      <ul className="incident-list">
        {incidents.map((i) => (
          <li key={i.id}>
            <Link to={`/incidents/${i.id}`} key={i.id} className="incident-row">
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
                <span className="sr-only">Severity: </span>
                <Badge value={i.severity} />
              </span>
              <span>
                <span className="sr-only">Status: </span>
                <Badge value={i.status} />
              </span>
              <span className="incident-time">
                <span className="sr-only">Detected: </span>
                {time(i.detected_at)}
              </span>
              <ArrowUpRight size={17} className="row-arrow" aria-hidden />
            </Link>
          </li>
        ))}
      </ul>
    </>
  );
}
export function DetailLink({ id, children }: { id: string; children?: React.ReactNode }) {
  return (
    <Link to={`/incidents/${id}`} className="text-link">
      {children || 'Open incident'}
      <ChevronRight size={15} />
    </Link>
  );
}
