import { beforeAll, beforeEach, afterEach, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, cleanup } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { ReviewActions } from '../components/ReviewActions';
import { QueryState } from '../components/ui';
import { ApiClientError } from '../api/errors';
import { createFixtures } from '../mocks/fixtures';
const { mutateAsync, notify } = vi.hoisted(() => ({ mutateAsync: vi.fn(), notify: vi.fn() }));
vi.mock('../hooks/queries', () => ({
  useWorkflowMutation: () => ({ isPending: false, mutateAsync }),
}));
vi.mock('../components/feedback', () => ({ useNotify: () => notify }));
beforeAll(() => {
  HTMLDialogElement.prototype.showModal = function () {
    this.open = true;
  };
  HTMLDialogElement.prototype.close = function () {
    this.open = false;
  };
});
beforeEach(() => vi.clearAllMocks());
afterEach(cleanup);
it('freezes reviewed evidence and blocks a changed candidate rather than approving it', async () => {
  const incident = createFixtures().incidents[0];
  const view = render(
    <MemoryRouter>
      <ReviewActions incident={incident} />
    </MemoryRouter>,
  );
  fireEvent.click(screen.getByRole('button', { name: 'Approve candidate' }));
  expect(screen.getByRole('dialog')).toHaveTextContent('patch_001');
  const changed = structuredClone(incident);
  changed.patches[0].id = 'patch_replaced';
  changed.patches[0].patch_hash = 'changed-hash';
  view.rerender(
    <MemoryRouter>
      <ReviewActions incident={changed} />
    </MemoryRouter>,
  );
  expect(screen.getByRole('dialog')).toHaveTextContent('patch_001');
  expect(screen.getByRole('dialog')).not.toHaveTextContent('patch_replaced');
  expect(screen.getByRole('button', { name: 'Confirm approval' })).toBeDisabled();
  fireEvent.submit(screen.getByRole('dialog').querySelector('form')!);
  await screen.findByText(/Review required: Candidate, revision or validation changed/);
  expect(mutateAsync).not.toHaveBeenCalled();
});
it('requires re-review when validation evidence changes without changing the patch', () => {
  const incident = createFixtures().incidents[0];
  const view = render(
    <MemoryRouter>
      <ReviewActions incident={incident} />
    </MemoryRouter>,
  );
  fireEvent.click(screen.getByRole('button', { name: 'Approve candidate' }));
  const changed = structuredClone(incident);
  changed.validation!.checks[0].evidence = 'A newer execution replaced this evidence.';
  view.rerender(
    <MemoryRouter>
      <ReviewActions incident={changed} />
    </MemoryRouter>,
  );
  expect(screen.getByRole('button', { name: 'Confirm approval' })).toBeDisabled();
  expect(screen.getByRole('alert')).toHaveTextContent('Candidate or evidence changed');
});
it('does not enable approval for contradictory permission and failed evidence', () => {
  const incident = createFixtures().incidents[0];
  incident.validation!.checks[0].status = 'failed';
  render(
    <MemoryRouter>
      <ReviewActions incident={incident} />
    </MemoryRouter>,
  );
  expect(screen.getByRole('button', { name: 'Approve candidate' })).toBeDisabled();
  expect(screen.getByText(/Passing validation for this exact candidate is required/)).toBeVisible();
});
it('announces loading and exposes a recoverable access error with a real retry', () => {
  const refetch = vi.fn();
  const view = render(
    <QueryState query={{ isPending: true, error: null, refetch }}>
      <p>Loaded evidence</p>
    </QueryState>,
  );
  expect(screen.getByRole('status')).toHaveAccessibleName('Loading content');
  expect(screen.queryByText('Loaded evidence')).not.toBeInTheDocument();
  view.rerender(
    <QueryState
      query={{
        isPending: false,
        error: new ApiClientError('FORBIDDEN', 'You do not have access to this incident.', 403),
        refetch,
      }}
    >
      <p>Loaded evidence</p>
    </QueryState>,
  );
  expect(screen.getByRole('alert')).toHaveTextContent('Access required');
  fireEvent.click(screen.getByRole('button', { name: 'Retry' }));
  expect(refetch).toHaveBeenCalledOnce();
});
