import { afterEach, describe, expect, it, vi } from 'vitest';
import { MockSentinelApi } from '../api/mockAdapter';
import { HttpSentinelApi } from '../api/realAdapter';
import { createFixtures } from '../mocks/fixtures';
import { incidentDetailSchema } from '../contracts/schemas';
import { pageParams, filterParams } from '../lib/pagination';
import { readPreferences, defaultPreferences } from '../lib/preferences';
import { createHash } from 'node:crypto';

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
  vi.useRealTimers();
  localStorage.clear();
});
const setup = () => {
  const seed = createFixtures(),
    api = new MockSentinelApi(0, seed),
    incident = seed.incidents[0],
    patch = incident.patches[0];
  return {
    seed,
    api,
    incident,
    body: {
      candidate_id: patch.id,
      patch_hash: patch.patch_hash,
      base_revision: patch.base_revision,
    },
  };
};
describe('audit safety regressions', () => {
  it('binds seeded content hashes to the actual unified diff', () => {
    for (const incident of createFixtures().incidents)
      for (const patch of incident.patches)
        expect(patch.patch_hash).toBe(
          'sha256:' + createHash('sha256').update(patch.diff).digest('hex'),
        );
  });
  it.each([
    'empty',
    'failed',
    'timeout',
    'error',
    'not_run',
    'candidate_mismatch',
    'hash_mismatch',
  ])('blocks %s validation even with can_approve=true', async (mode) => {
    const { api, incident, body } = setup();
    if (mode === 'empty') incident.validation!.checks = [];
    else if (mode === 'candidate_mismatch') incident.validation!.candidate_id = 'other';
    else if (mode === 'hash_mismatch') incident.validation!.patch_hash = 'other';
    else incident.validation!.checks[0].status = mode as 'failed';
    await expect(api.decide(incident.id, { ...body, decision: 'approve' })).rejects.toMatchObject({
      code: 'TESTS_NOT_PASSED',
    });
    expect(incident.decision).toBeNull();
    expect(incident.application_attempt).toBeNull();
  });
  it('invalidates approval when the application revision changes', async () => {
    const { api, seed, incident, body } = setup();
    await api.decide(incident.id, { ...body, decision: 'approve' });
    seed.applications[0].repository_revision = 'changed';
    await expect(api.applyApprovedPatch(incident.id, body)).rejects.toMatchObject({
      code: 'CANDIDATE_STALE',
    });
    expect(incident.can_apply).toBe(false);
    expect(incident.application_attempt).toBeNull();
  });
  it('rechecks tests after approval before any application', async () => {
    const { api, incident, body } = setup();
    await api.decide(incident.id, { ...body, decision: 'approve' });
    incident.validation!.checks[0].status = 'failed';
    await expect(api.applyApprovedPatch(incident.id, body)).rejects.toMatchObject({
      code: 'TESTS_NOT_PASSED',
    });
    expect(incident.application_attempt).toBeNull();
  });
  it('shows a failed verification, restoration and unresolved report without claiming success', async () => {
    const incident = (await new MockSentinelApi(0).getIncident('inc_007')).data;
    expect(incidentDetailSchema.safeParse(incident).success).toBe(true);
    expect(incident.status).toBe('unresolved');
    expect(incident.verification?.status).toBe('failed');
    expect(incident.application_attempt?.restore_status).toBe('restored');
    expect(incident.report?.summary).toContain('remains unresolved');
    expect(incident.can_apply).toBe(false);
  });
  it('filters and sorts before pagination, including records beyond the old 100-record cap', async () => {
    const { seed } = setup();
    seed.incidents = Array.from({ length: 125 }, (_, index) => ({
      ...structuredClone(seed.incidents[0]),
      id: `test_${index}`,
      status: index === 124 ? ('resolved' as const) : ('awaiting_approval' as const),
      detected_at: new Date(Date.UTC(2026, 10, 17, 0, index)).toISOString(),
    }));
    const api = new MockSentinelApi(0, seed);
    expect((await api.listIncidents({ scope: 'closed', limit: 5 })).data.items[0].id).toBe(
      'test_124',
    );
    const page = (await api.listIncidents({ scope: 'open', sort: 'detected_asc', limit: 5 })).data;
    expect(page.items[0].id).toBe('test_0');
    expect(page.total).toBe(124);
    expect(
      (
        await api.listIncidents({
          scope: 'open',
          cursor: page.next_cursor!,
          sort: 'detected_asc',
          limit: 5,
        })
      ).data.items[0].id,
    ).toBe('test_5');
  });
  it('handles opaque cursor tokens with previous navigation and direct refresh', () => {
    const first = new URLSearchParams('sort=detected_asc');
    const second = pageParams(first, 'next', 'eyJpZCI6MTIzfQ==');
    expect(second.get('cursor')).toBe('eyJpZCI6MTIzfQ==');
    const third = pageParams(second, 'next', 'cursor:another');
    expect(pageParams(third, 'previous').toString()).toBe(second.toString());
    expect(pageParams(second, 'previous').toString()).toBe(first.toString());
    expect(filterParams(third, 'status', 'resolved').has('cursor')).toBe(false);
    expect(filterParams(third, 'status', 'resolved').has('from')).toBe(false);
  });
  it('sanitizes invalid stored preferences and survives disabled storage', () => {
    localStorage.setItem('sentinel.polling', '0');
    localStorage.setItem('sentinel.theme', 'broken');
    expect(readPreferences()).toEqual(defaultPreferences);
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new DOMException('Disabled');
    });
    expect(readPreferences()).toEqual(defaultPreferences);
  });
  it('normalizes validation errors in both adapters before network access', async () => {
    const fetch = vi.fn();
    vi.stubGlobal('fetch', fetch);
    for (const api of [new MockSentinelApi(0), new HttpSentinelApi('/api/v1')])
      await expect(api.updateSettings({ monitoring_interval_seconds: 0 })).rejects.toMatchObject({
        code: 'VALIDATION_ERROR',
        status: 422,
      });
    expect(fetch).not.toHaveBeenCalled();
  });
  it('exposes a real request timeout distinctly from offline', async () => {
    vi.useFakeTimers();
    vi.stubGlobal(
      'fetch',
      vi.fn(
        (_url, init) =>
          new Promise((_resolve, reject) => {
            init.signal.addEventListener('abort', () =>
              reject(new DOMException('Aborted', 'AbortError')),
            );
          }),
      ),
    );
    const pending = expect(new HttpSentinelApi('/api/v1').getHealth()).rejects.toMatchObject({
      code: 'TIMEOUT',
    });
    await vi.advanceTimersByTimeAsync(12001);
    await pending;
  });
});
