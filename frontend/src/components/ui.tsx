import { useEffect, useId, useRef, type ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { AlertCircle, ArrowRight, Check, Circle, Copy, LoaderCircle, X } from 'lucide-react';
import { label } from '../lib/format';
import { ApiClientError } from '../api/errors';

export function Badge({ value }: { value: string }) {
  const positive = ['passed', 'resolved', 'completed', 'healthy', 'approved'];
  const negative = [
    'error',
    'failed',
    'offline',
    'rejected',
    'critical',
    'stale',
    'timeout',
    'unresolved',
  ];
  return (
    <span
      className={`badge ${positive.includes(value) ? 'positive' : negative.includes(value) ? 'negative' : ['awaiting_approval', 'revision_requested', 'high', 'degraded', 'manual_review'].includes(value) ? 'warning' : 'neutral'}`}
    >
      {positive.includes(value) ? (
        <Check size={12} aria-hidden />
      ) : (
        <Circle size={8} fill="currentColor" aria-hidden />
      )}
      {label(value)}
    </span>
  );
}
export function Heading({
  eyebrow,
  title,
  description,
  action,
}: {
  eyebrow?: string;
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <div className="page-heading">
      <div>
        <div className="eyebrow">{eyebrow || 'YOUR INCIDENT WORKSPACE'}</div>
        <h1 tabIndex={-1}>{title}</h1>
        <p>{description}</p>
      </div>
      {action}
    </div>
  );
}
export function Panel({
  title,
  children,
  action,
  className = '',
}: {
  title?: string;
  children: ReactNode;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <section className={`panel ${className}`}>
      {title && (
        <div className="panel-heading">
          <h2>{title}</h2>
          {action}
        </div>
      )}
      {children}
    </section>
  );
}
export function Empty({ message = 'No results match your filters.' }: { message?: string }) {
  return (
    <div className="empty">
      <Circle size={28} aria-hidden />
      <h3>{message}</h3>
      <p>Try another filter, or explore the incident workspace.</p>
      <Link className="text-link" to="/incidents">
        View incidents <ArrowRight size={16} />
      </Link>
    </div>
  );
}
export function QueryState({
  query,
  children,
}: {
  query: { isPending: boolean; error: Error | null; refetch: () => unknown };
  children: ReactNode;
}) {
  if (query.isPending)
    return (
      <div role="status" aria-label="Loading content" className="skeleton-grid">
        {[1, 2, 3].map((i) => (
          <div className="skeleton" key={i} />
        ))}
        <span className="sr-only">Loading content</span>
      </div>
    );
  if (query.error)
    return (
      <div role="alert" className="error-state">
        <AlertCircle />
        <h2>
          {query.error instanceof ApiClientError && [401, 403].includes(query.error.status)
            ? 'Access required'
            : query.error instanceof ApiClientError && query.error.status === 404
              ? 'Item not found'
              : 'Unable to load this view'}
        </h2>
        <p>{query.error.message}</p>
        <button className="button" onClick={() => query.refetch()}>
          Retry
        </button>
        <details>
          <summary>Diagnostic details</summary>
          <code>
            {query.error instanceof ApiClientError
              ? `${query.error.code} · HTTP ${query.error.status || 'offline'}`
              : 'Request failed'}
          </code>
        </details>
      </div>
    );
  return children;
}
export function Dialog({
  open,
  title,
  children,
  onClose,
  dismissible = true,
}: {
  open: boolean;
  title: string;
  children: ReactNode;
  onClose: () => void;
  dismissible?: boolean;
}) {
  const ref = useRef<HTMLDialogElement>(null),
    opener = useRef<HTMLElement | null>(null),
    id = useId();
  useEffect(() => {
    const dialog = ref.current;
    if (open && !dialog?.open) {
      opener.current = document.activeElement as HTMLElement | null;
      dialog?.showModal();
    }
    if (!open && dialog?.open) {
      dialog.close();
      if (opener.current?.isConnected && !opener.current.matches(':disabled'))
        opener.current.focus();
      else document.getElementById('main')?.focus();
    }
  }, [open]);
  return (
    <dialog
      ref={ref}
      tabIndex={-1}
      aria-labelledby={id}
      onKeyDown={(event) => {
        if (event.key !== 'Tab') return;
        const dialog = event.currentTarget;
        const controls = Array.from(
          dialog.querySelectorAll<HTMLElement>(
            'button:not(:disabled), a[href], input:not(:disabled), select:not(:disabled), textarea:not(:disabled), [tabindex="0"]',
          ),
        ).filter((element) => element.getClientRects().length > 0);
        const first = controls[0],
          last = controls.at(-1);
        if (!first) {
          event.preventDefault();
          dialog.focus();
          return;
        }
        if (
          event.shiftKey &&
          (document.activeElement === first || document.activeElement === dialog)
        ) {
          event.preventDefault();
          last?.focus();
        } else if (
          !event.shiftKey &&
          (document.activeElement === last || document.activeElement === dialog)
        ) {
          event.preventDefault();
          first.focus();
        }
      }}
      onCancel={(event) => {
        event.preventDefault();
        if (dismissible) onClose();
      }}
    >
      <div className="dialog-heading">
        <h2 id={id}>{title}</h2>
        <button
          type="button"
          className="icon-button"
          aria-label="Close dialog"
          onClick={onClose}
          disabled={!dismissible}
        >
          <X />
        </button>
      </div>
      {children}
    </dialog>
  );
}
export function CopyButton({ value, notify }: { value: string; notify: (text: string) => void }) {
  return (
    <button
      className="button small"
      onClick={async () => {
        try {
          await navigator.clipboard.writeText(value);
          notify('Copied to clipboard.');
        } catch {
          notify('Clipboard unavailable. Select and copy the text manually.');
        }
      }}
    >
      <Copy size={15} aria-hidden /> Copy
    </button>
  );
}
export function Busy() {
  return (
    <span className="inline-flex items-center gap-2">
      <LoaderCircle className="spin" size={16} /> Working…
    </span>
  );
}
