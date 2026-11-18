import { useId, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { Activity, Bot, CircleHelp, ClipboardCheck, Command, FileClock, X } from 'lucide-react';

export function QuickActions({
  onHelp,
  publicHelp = false,
}: {
  onHelp: () => void;
  publicHelp?: boolean;
}) {
  const id = useId();
  const popover = useRef<HTMLDivElement>(null);
  const [open, setOpen] = useState(false);
  const close = () => popover.current?.hidePopover();
  return (
    <div className="quick-actions">
      <div
        id={id}
        ref={popover}
        popover="auto"
        className="quick-menu quick-popover"
        onToggle={(event) => {
          const expanded = event.newState === 'open';
          setOpen(expanded);
          if (expanded) popover.current?.querySelector('a')?.focus();
        }}
      >
        <strong id={`${id}-title`}>Quick actions</strong>
        <nav aria-labelledby={`${id}-title`}>
          {!publicHelp && (
            <>
              <Link to="/incidents?view=open" onClick={close}>
                View active incidents <Activity size={16} aria-hidden />
              </Link>
              <Link to="/agents#workflow" onClick={close}>
                AI agent workflow <Bot size={16} aria-hidden />
              </Link>
              <Link to="/approval-recovery?view=pending" onClick={close}>
                Review pending approvals <ClipboardCheck size={16} aria-hidden />
              </Link>
              <Link to="/history" onClick={close}>
                Recent reports <FileClock size={16} aria-hidden />
              </Link>
              <button
                onClick={() => {
                  close();
                  onHelp();
                }}
              >
                Open help <CircleHelp size={16} aria-hidden />
              </button>
            </>
          )}
          <Link to="/onboarding" onClick={close}>
            Start product tour <CircleHelp size={16} aria-hidden />
          </Link>
          <Link to="/#how-it-works" onClick={close}>
            Learn how it works
          </Link>
          <Link to="/docs" onClick={close}>
            Open documentation
          </Link>
          <Link to="/#faq" onClick={close}>
            Frequently asked questions
          </Link>
        </nav>
      </div>
      <button
        className="fab"
        aria-label="Quick actions"
        aria-expanded={open}
        aria-controls={id}
        popoverTarget={id}
      >
        {open ? <X aria-hidden /> : <Command size={22} aria-hidden />}
      </button>
    </div>
  );
}
