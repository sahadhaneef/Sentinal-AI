import { AlertCircle, CheckCheck, FileText } from 'lucide-react';
import type { IncidentDetail } from '../contracts/types';
import { label, time } from '../lib/format';
import { Badge, Panel } from './ui';

export function Outcome({ incident }: { incident: IncidentDetail }) {
  const verification = incident.verification;
  const passed = verification?.status === 'passed';
  return (
    <Panel
      title="Verification & report"
      action={incident.report && <Badge value={incident.report.outcome} />}
    >
      {verification ? (
        <>
          <p className={`verification-result ${passed ? 'positive' : 'negative'}`}>
            {passed ? <CheckCheck size={20} aria-hidden /> : <AlertCircle size={20} aria-hidden />}{' '}
            Verification {label(verification.status)}
          </p>
          <p>{verification.monitoring_observation}</p>
          <ul className="plain-list">
            {verification.checks.map((check) => (
              <li key={check.name}>
                {label(check.name)} · {label(check.status)} · {check.duration_ms} ms
              </li>
            ))}
          </ul>
        </>
      ) : (
        <p>
          {incident.status === 'rejected'
            ? 'Candidate rejected. No patch was applied.'
            : 'No post-apply verification is available yet.'}
        </p>
      )}
      {incident.application_attempt && (
        <p className="notice">
          Snapshot: {incident.application_attempt.snapshot_ref} · Restore:{' '}
          {label(incident.application_attempt.restore_status)}
        </p>
      )}
      {incident.report ? (
        <article className="report-content" aria-label="Incident report">
          <h3>
            <FileText size={17} aria-hidden /> Report v{incident.report.version}
          </h3>
          <p>{incident.report.summary}</p>
          <h4>Limitations</h4>
          <ul className="plain-list">
            {incident.report.limitations.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
          <small>
            Generated {time(incident.report.generated_at)} · {incident.report.report_artifact_id}
          </small>
        </article>
      ) : (
        <p className="notice">A report appears after a final decision or verification outcome.</p>
      )}
    </Panel>
  );
}
