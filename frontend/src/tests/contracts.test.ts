import { beforeEach, describe, expect, it } from 'vitest';
import { MockSentinelApi } from '../api/mockAdapter';
import * as S from '../contracts/schemas';
import type { ApplyRequest } from '../contracts/types';
let api: MockSentinelApi;
beforeEach(() => {
  api = new MockSentinelApi(0);
});
const candidate = async (id = 'inc_001'): Promise<ApplyRequest> => {
  const p = (await api.getIncident(id)).data.patches[0];
  return { candidate_id: p.id, patch_hash: p.patch_hash, base_revision: p.base_revision };
};
describe('frozen frontend contract and safety gates', () => {
  it('validates all linked fixtures against schemas', async () => {
    const list = (await api.listIncidents()).data;
    expect(list.items.map((i) => i.id)).toEqual(
      expect.arrayContaining([
        'inc_001',
        'inc_002',
        'inc_003',
        'inc_004',
        'inc_005',
        'inc_006',
        'inc_007',
      ]),
    );
    expect(list.items).toHaveLength(7);
    for (const i of list.items) {
      expect(S.incidentDetailSchema.safeParse((await api.getIncident(i.id)).data).success).toBe(
        true,
      );
      expect(
        S.eventSchema.array().safeParse((await api.getIncidentEvents(i.id)).data).success,
      ).toBe(true);
    }
    expect(S.agentDetailSchema.array().safeParse((await api.listAgents()).data).success).toBe(true);
  });
  it('requires approval, then independently applies and reports', async () => {
    const b = await candidate();
    await expect(api.applyApprovedPatch('inc_001', b)).rejects.toMatchObject({
      code: 'APPROVAL_REQUIRED',
    });
    await api.decide('inc_001', { ...b, decision: 'approve' });
    let i = (await api.getIncident('inc_001')).data;
    expect(i.can_apply).toBe(true);
    expect(i.verification).toBeNull();
    await api.applyApprovedPatch('inc_001', b);
    i = (await api.getIncident('inc_001')).data;
    expect(i.status).toBe('resolved');
    expect(i.verification?.status).toBe('passed');
    expect((await api.getReport(i.id)).data.outcome).toBe('resolved');
  });
  it('rejects without any application', async () => {
    await api.decide('inc_001', { ...(await candidate()), decision: 'reject' });
    const i = (await api.getIncident('inc_001')).data;
    expect(i.status).toBe('rejected');
    expect(i.application_attempt).toBeNull();
    expect(i.report?.outcome).toBe('rejected');
  });
  it('keeps seeded recovery evidence linked to the exact application attempt', async () => {
    const incident = (await api.getIncident('inc_005')).data;
    expect(incident.verification?.application_attempt_id).toBe(incident.application_attempt?.id);
    expect(incident.application_attempt?.candidate_id).toBe(incident.decision?.candidate_id);
    expect(incident.report?.outcome).toBe(incident.status);
  });
  it('never approves failed tests or invents manual-review evidence', async () => {
    await expect(
      api.decide('inc_002', { ...(await candidate('inc_002')), decision: 'approve' }),
    ).rejects.toMatchObject({ status: 409 });
    const i = (await api.getIncident('inc_003')).data;
    expect(i.diagnosis).toBeNull();
    expect(i.patches).toEqual([]);
    expect(i.can_approve).toBe(false);
  });
  it('invalidates stale candidates and tampered hashes', async () => {
    await expect(
      api.decide('inc_006', { ...(await candidate('inc_006')), decision: 'approve' }),
    ).rejects.toMatchObject({ code: 'CANDIDATE_STALE' });
    expect((await api.getIncident('inc_006')).data.can_approve).toBe(false);
    await expect(
      api.decide('inc_001', {
        ...(await candidate()),
        patch_hash: 'tampered',
        decision: 'approve',
      }),
    ).rejects.toMatchObject({ code: 'CANDIDATE_STALE' });
  });
  it('filters, paginates, updates monitoring and resets shared state', async () => {
    expect(
      (await api.listIncidents({ status: 'awaiting_approval', limit: 1 })).data.next_cursor,
    ).toBe('1');
    await api.setMonitoring('app_demo', false);
    expect((await api.getApplication('app_demo')).data.monitoring_enabled).toBe(false);
    await api.resetDemo();
    expect((await api.getApplication('app_demo')).data.monitoring_enabled).toBe(true);
  });
});
