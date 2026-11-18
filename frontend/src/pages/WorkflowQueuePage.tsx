import { useSearchParams, Link } from 'react-router-dom';
import { ArrowUpRight, ClipboardCheck, ShieldCheck } from 'lucide-react';
import { useIncident, useIncidents } from '../hooks/queries';
import { Badge, Empty, Heading, Panel, QueryState } from '../components/ui';
import { PatchReview } from '../components/patches';
import { ReviewActions } from '../components/ReviewActions';
import { Outcome } from '../components/Outcome';
import { Pagination } from '../components/Pagination';
import { filterParams } from '../lib/pagination';
function CandidateDetail({ id, approval }: { id: string; approval: boolean }) {
  const q = useIncident(id),
    i = q.data?.data;
  return (
    <QueryState query={q}>
      {i && (
        <>
          <div className="queue-detail-heading">
            <div>
              <span className="eyebrow">{i.id.toUpperCase()}</span>
              <h2>{i.message}</h2>
            </div>
            <Link className="text-link" to={`/incidents/${i.id}`}>
              Full incident <ArrowUpRight size={15} />
            </Link>
          </div>
          {i.patches.length ? (
            <PatchReview patch={i.patches.at(-1)!} validation={i.validation} />
          ) : (
            <Panel>
              <Empty message="No candidate available." />
            </Panel>
          )}
          {approval ? (
            <>
              <div className="spaced">
                <ReviewActions key={i.id} incident={i} />
              </div>
              <div className="spaced">
                <Outcome incident={i} />
              </div>
            </>
          ) : (
            <div className="notice inline-notice">
              <ShieldCheck size={20} />
              <div>
                <strong>Ready for a human decision?</strong>
                <p>Review the candidate and validation evidence in Approval & Recovery.</p>
              </div>
              <Link className="button primary" to={`/approval-recovery?incident=${i.id}`}>
                Review for approval <ArrowUpRight size={14} />
              </Link>
            </div>
          )}
        </>
      )}
    </QueryState>
  );
}
export function WorkflowQueuePage({ approval = false }: { approval?: boolean }) {
  const [params, setParams] = useSearchParams(),
    pending = approval && params.get('view') === 'pending';
  const q = useIncidents({
    limit: 5,
    cursor: params.get('cursor') || undefined,
    scope: pending ? 'pending' : 'candidates',
    sort: 'detected_desc',
  });
  const items = q.data?.data.items || [],
    selected = params.get('incident') || items[0]?.id;
  return (
    <>
      <Heading
        title={approval ? 'Approval & Recovery' : 'Repair & Testing'}
        description={
          approval
            ? 'The human checkpoint. Review the exact candidate, make a decision, and separately authorize a local apply.'
            : 'Focused patches. Visible evidence. Explore each candidate and its isolated validation results.'
        }
      />
      {approval && (
        <div className="review-banner">
          <span>
            <ClipboardCheck size={25} />
          </span>
          <div>
            <strong>Your approval is always required.</strong>
            <p>
              Tests inform your decision. Only an approved, unchanged candidate can be applied to
              the local sample.
            </p>
          </div>
          <span className="review-banner-tag">HUMAN IN THE LOOP</span>
        </div>
      )}
      <QueryState query={q}>
        {approval && (
          <div className="filters">
            <select
              aria-label="Review queue"
              value={pending ? 'pending' : 'all'}
              onChange={(e) =>
                setParams(
                  filterParams(params, 'view', e.target.value === 'pending' ? 'pending' : ''),
                )
              }
            >
              <option value="all">All candidates</option>
              <option value="pending">Pending review & recovery</option>
            </select>
          </div>
        )}
        <div className="queue-layout">
          <Panel title="Candidate queue" className="queue-sidebar">
            {items.map((i) => (
              <button
                key={i.id}
                className={`queue-item ${selected === i.id ? 'selected' : ''}`}
                aria-current={selected === i.id ? 'true' : undefined}
                onClick={() =>
                  setParams((p) => {
                    p.set('incident', i.id);
                    return p;
                  })
                }
              >
                <small>{i.id}</small>
                <strong>{i.message}</strong>
                <Badge value={i.status} />
              </button>
            ))}
            {!items.length && <Empty />}
            <Pagination
              nextCursor={q.data?.data.next_cursor}
              total={q.data?.data.total || 0}
              busy={q.isFetching}
            />
          </Panel>
          <div className="queue-body">
            {selected ? (
              <CandidateDetail key={selected} id={selected} approval={approval} />
            ) : (
              <Empty message="No candidates to review." />
            )}
          </div>
        </div>
      </QueryState>
    </>
  );
}
