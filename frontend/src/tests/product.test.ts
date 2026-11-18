import { afterEach, expect, it, vi } from 'vitest';
import { readOnboarding } from '../pages/OnboardingPage';
import { createLearningApi } from '../api/learningClient';
import { MockSentinelApi } from '../api/mockAdapter';
afterEach(() => {
  localStorage.clear();
  vi.unstubAllGlobals();
});
it('resumes valid onboarding progress and safely ignores corrupt browser storage', () => {
  localStorage.setItem('sentinel.onboarding', JSON.stringify({ step: 3, done: false }));
  expect(readOnboarding()).toEqual({ step: 3, done: false });
  localStorage.setItem('sentinel.onboarding', 'not json');
  expect(readOnboarding()).toEqual({ step: 0, done: false });
  localStorage.setItem('sentinel.onboarding', JSON.stringify({ step: 999, done: true }));
  expect(readOnboarding().step).toBe(0);
});
it('keeps learning decisions isolated from the workspace and network', async () => {
  const fetch = vi.fn();
  vi.stubGlobal('fetch', fetch);
  const learning = createLearningApi(),
    workspace = new MockSentinelApi(0);
  const candidate = (await learning.getIncident('inc_001')).data.patches[0];
  const body = {
    candidate_id: candidate.id,
    patch_hash: candidate.patch_hash,
    base_revision: candidate.base_revision,
  };
  await learning.decide('inc_001', { ...body, decision: 'approve' });
  await learning.applyApprovedPatch('inc_001', body);
  expect((await learning.getIncident('inc_001')).data.status).toBe('resolved');
  expect((await workspace.getIncident('inc_001')).data.status).toBe('awaiting_approval');
  expect((await createLearningApi().getIncident('inc_001')).data.decision).toBeNull();
  expect(fetch).not.toHaveBeenCalled();
});
