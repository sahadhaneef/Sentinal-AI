import { useSearchParams } from 'react-router-dom';
import { pageParams } from '../lib/pagination';
export function Pagination({
  nextCursor,
  total,
  busy = false,
}: {
  nextCursor?: string | null;
  total: number;
  busy?: boolean;
}) {
  const [params, setParams] = useSearchParams(),
    trail = params.getAll('from');
  return (
    <nav className="pagination" aria-label="Result pages">
      <span role="status">
        {params.has('cursor') && !trail.length ? 'Continuation' : `Page ${trail.length + 1}`} ·{' '}
        {total} total
      </span>
      <div>
        <button
          className="button small"
          disabled={!trail.length || busy}
          onClick={() => setParams(pageParams(params, 'previous'))}
        >
          Previous
        </button>
        <button
          className="button small"
          disabled={!nextCursor || busy}
          onClick={() => setParams(pageParams(params, 'next', nextCursor))}
        >
          Next
        </button>
      </div>
    </nav>
  );
}
