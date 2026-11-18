import { useId, useState } from 'react';
import { Link } from 'react-router-dom';
import { z } from 'zod';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { ClipboardCheck, ShieldCheck } from 'lucide-react';
import type { IncidentDetail, PatchCandidate } from '../contracts/types';
import { isDemo } from '../api/client';
import { reviewAccess } from '../lib/approval';
import { ApiClientError } from '../api/errors';
import { useWorkflowMutation } from '../hooks/queries';
import { useNotify } from './feedback';
import { Badge, Busy, Dialog, Panel } from './ui';
const formSchema = z.object({
  comment: z.string().max(2000, 'Keep the comment under 2,000 characters.'),
});
export function ReviewActions({ incident: i }: { incident: IncidentDetail }) {
  const [review, setReview] = useState<{
      kind: 'approve' | 'reject' | 'apply';
      patch: PatchCandidate;
      repository_revision: string;
      validation: string;
    } | null>(null),
    [error, setError] = useState(''),
    mutation = useWorkflowMutation(i.id),
    notify = useNotify();
  const form = useForm({ resolver: zodResolver(formSchema), defaultValues: { comment: '' } });
  const p = i.patches.at(-1);
  const commentErrorId = useId();
  const action = review?.kind ?? null,
    access = reviewAccess(i),
    reasonId = useId();
  const unchanged =
    !!review &&
    !!p &&
    review.patch.id === p.id &&
    review.patch.patch_hash === p.patch_hash &&
    review.patch.base_revision === p.base_revision &&
    review.patch.diff === p.diff &&
    review.repository_revision === i.repository_revision &&
    review.validation === JSON.stringify(i.validation);
  const openReview = (kind: 'approve' | 'reject' | 'apply') => {
    if (p) {
      setError('');
      form.reset();
      setReview({
        kind,
        patch: structuredClone(p),
        repository_revision: i.repository_revision,
        validation: JSON.stringify(i.validation),
      });
    }
  };
  const closeReview = () => setReview(null);
  async function submit({ comment }: { comment: string }) {
    if (!review || !action) return;
    if (
      !unchanged ||
      !(action === 'apply'
        ? access.canApply
        : action === 'approve'
          ? access.canApprove
          : access.canReject)
    ) {
      closeReview();
      setError(
        'Review required: Candidate, revision or validation changed. Inspect the current evidence before making a new decision.',
      );
      return;
    }
    setError('');
    const body = {
      candidate_id: review.patch.id,
      patch_hash: review.patch.patch_hash,
      base_revision: review.patch.base_revision,
    };
    try {
      await mutation.mutateAsync(
        action === 'apply'
          ? { type: 'apply', body }
          : { type: 'decide', body: { ...body, decision: action, comment } },
      );
      closeReview();
      form.reset();
      notify(
        action === 'apply'
          ? isDemo
            ? 'Simulated verification completed. Review the report below.'
            : 'Apply request accepted. Follow the incident for verification and its final report.'
          : action === 'approve'
            ? 'Candidate approved. Applying is a separate action.'
            : 'Rejection recorded. No patch application was requested.',
      );
    } catch (e) {
      const message = e instanceof Error ? e.message : 'The action could not be completed.';
      closeReview();
      setError(
        e instanceof ApiClientError && e.status === 409 ? `Review required: ${message}` : message,
      );
      notify(message);
    }
  }
  return (
    <>
      <Panel
        className="human-review"
        title="Your decision matters"
        action={<ClipboardCheck size={21} />}
      >
        <p>
          Review the exact diff, revision and test evidence before authorizing a local demo change.
        </p>
        <Link className="text-link" to={`/incidents/${i.id}?tab=patch%20%26%20tests`}>
          Inspect exact diff & test evidence
        </Link>
        {error && (
          <p className="error-notice" role="alert">
            {error}
          </p>
        )}
        {i.decision && (
          <div className="decision-record">
            <Badge value={i.decision.decision === 'approve' ? 'approved' : 'rejected'} />
            <span>Decision by {i.decision.actor_id}</span>
            {i.decision.comment && <p>{i.decision.comment}</p>}
          </div>
        )}
        <div className="review-buttons">
          <button
            className="button primary"
            disabled={!access.canApprove || mutation.isPending}
            aria-describedby={reasonId}
            onClick={() => openReview('approve')}
          >
            Approve candidate
          </button>
          <button
            className="button danger"
            disabled={!access.canReject || mutation.isPending}
            aria-describedby={reasonId}
            onClick={() => openReview('reject')}
          >
            Reject candidate
          </button>
          <button
            className="button"
            disabled={!access.canApply || mutation.isPending}
            aria-describedby={reasonId}
            onClick={() => openReview('apply')}
          >
            <ShieldCheck size={16} /> Apply approved patch to local demo
          </button>
        </div>
        <p className="review-reason" id={reasonId}>
          {access.reason ||
            (!i.can_approve && !i.can_apply
              ? 'No review action is available in this state.'
              : i.can_apply
                ? 'Approved for this exact candidate. A separate confirmation is required to apply.'
                : 'Approval authorizes this candidate only. It does not apply the patch.')}
        </p>
      </Panel>
      <Dialog
        open={action !== null}
        dismissible={!mutation.isPending}
        title={
          action === 'apply'
            ? 'Apply the approved local demo patch?'
            : action === 'reject'
              ? 'Reject this candidate?'
              : 'Approve this exact candidate?'
        }
        onClose={() => {
          if (!mutation.isPending) closeReview();
        }}
      >
        <form onSubmit={form.handleSubmit(submit)}>
          <p>
            {action === 'apply'
              ? isDemo
                ? 'This separately simulates application, verification and a final report. No real files are changed.'
                : 'This requests controlled application of the approved patch to the designated local sample. Follow verification before assuming recovery.'
              : action === 'approve'
                ? 'You are authorizing only the exact patch below for the designated local demo. Approval does not apply it.'
                : 'The candidate will be marked rejected and a report recorded. The demo will remain unchanged.'}
          </p>
          {review && (
            <dl className="key-values compact">
              <div>
                <dt>Candidate</dt>
                <dd>
                  {review.patch.id} · v{review.patch.version}
                </dd>
              </div>
              <div>
                <dt>Base</dt>
                <dd>
                  <code>{review.patch.base_revision}</code>
                </dd>
              </div>
              <div>
                <dt>Hash</dt>
                <dd>
                  <code>{review.patch.patch_hash}</code>
                </dd>
              </div>
              <div>
                <dt>Scope</dt>
                <dd>{review.patch.changed_files.join(', ')}</dd>
              </div>
            </dl>
          )}
          {review && !unchanged && (
            <p className="error-notice" role="alert">
              Candidate or evidence changed while this dialog was open. Cancel and review the
              current candidate.
            </p>
          )}
          {action !== 'apply' && (
            <label>
              Review comment (optional)
              <textarea
                rows={3}
                aria-invalid={!!form.formState.errors.comment}
                aria-describedby={form.formState.errors.comment ? commentErrorId : undefined}
                {...form.register('comment')}
              />
              {form.formState.errors.comment && (
                <span id={commentErrorId} className="error-text" role="alert">
                  {form.formState.errors.comment.message}
                </span>
              )}
            </label>
          )}
          <div className="dialog-actions">
            <button
              type="button"
              className="button"
              disabled={mutation.isPending}
              onClick={closeReview}
            >
              Cancel
            </button>
            <button
              type="submit"
              className={`button ${action === 'reject' ? 'danger' : 'primary'}`}
              disabled={mutation.isPending || !unchanged}
            >
              {mutation.isPending ? (
                <Busy />
              ) : action === 'apply' ? (
                isDemo ? (
                  'Confirm simulated apply'
                ) : (
                  'Confirm local apply'
                )
              ) : action === 'reject' ? (
                'Confirm rejection'
              ) : (
                'Confirm approval'
              )}
            </button>
          </div>
          {mutation.isPending && (
            <p className="notice" role="status">
              {isDemo
                ? 'Processing simulated workflow. No code is executed.'
                : 'Submitting the request. Verification is reported separately by the backend.'}
            </p>
          )}
        </form>
      </Dialog>
    </>
  );
}
