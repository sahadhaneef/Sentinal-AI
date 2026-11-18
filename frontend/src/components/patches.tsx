import { FileCode2, FlaskConical, GitBranch } from 'lucide-react';
import type { PatchCandidate, ValidationResult } from '../contracts/types';
import { Badge, CopyButton, Panel } from './ui';
import { useNotify } from './feedback';
import { label } from '../lib/format';
export function PatchReview({
  patch,
  validation,
}: {
  patch: PatchCandidate;
  validation: ValidationResult | null;
}) {
  const notify = useNotify();
  return (
    <div className="patch-review">
      <Panel title={`Candidate v${patch.version}`} action={<Badge value={patch.status} />}>
        <p>{patch.rationale}</p>
        <details className="candidate-technical">
          <summary>Technical candidate details ? ID, revision & hash</summary>
          <dl className="key-values">
            <div>
              <dt>Candidate ID</dt>
              <dd>
                <code>{patch.id}</code>
              </dd>
            </div>
            <div>
              <dt>
                <GitBranch size={13} /> Base revision
              </dt>
              <dd>
                <code>{patch.base_revision}</code>
              </dd>
            </div>
            <div>
              <dt>Content hash</dt>
              <dd>
                <code>{patch.patch_hash}</code>
                <CopyButton value={patch.patch_hash} notify={notify} />
              </dd>
            </div>
            <div>
              <dt>
                <FileCode2 size={13} /> Changed files
              </dt>
              <dd>
                {patch.changed_files.map((f) => (
                  <code key={f}>{f}</code>
                ))}
              </dd>
            </div>
          </dl>
        </details>
        <div className="diff-header">
          <span>
            <FileCode2 size={15} /> Exact proposed diff
          </span>
          <CopyButton value={patch.diff} notify={notify} />
        </div>
        <div className="diff" role="region" aria-label="Patch diff" tabIndex={0}>
          {patch.diff.split('\n').map((line, index) => (
            <div
              key={index}
              className={
                line.startsWith('+') && !line.startsWith('+++')
                  ? 'added'
                  : line.startsWith('-') && !line.startsWith('---')
                    ? 'removed'
                    : ''
              }
            >
              <span aria-hidden="true" className="line-number">
                {index + 1}
              </span>
              <code>{line || ' '}</code>
            </div>
          ))}
        </div>
        <details className="spaced">
          <summary>Plain-text diff</summary>
          <pre className="code-block">{patch.diff}</pre>
        </details>
      </Panel>
      <Panel title="Isolated validation" action={validation && <Badge value={validation.status} />}>
        {validation ? (
          <>
            <div className="validation-caption">
              <FlaskConical size={16} />
              <span>
                {validation.checks.filter((c) => c.status === 'passed').length} of{' '}
                {validation.checks.length} checks passed · {validation.duration_ms} ms
              </span>
            </div>
            <p className="notice">
              Validation is evidence for human review. Passing tests do not authorize application.
            </p>
            {validation.checks.map((c) => (
              <details className="check-item" key={c.name}>
                <summary>
                  <span>
                    {label(c.name)}
                    <small>
                      {c.duration_ms} ms · exit {c.exit_code ?? 'not run'}
                    </small>
                  </span>
                  <Badge value={c.status} />
                </summary>
                <pre className="code-block">{c.evidence}</pre>
                <small>Evidence artifact: {c.evidence_artifact_id}</small>
              </details>
            ))}
            <p className="muted-caption spaced">ENVIRONMENT {validation.environment_id}</p>
          </>
        ) : (
          <p>No validation evidence available. Approval is unavailable.</p>
        )}
      </Panel>
    </div>
  );
}
