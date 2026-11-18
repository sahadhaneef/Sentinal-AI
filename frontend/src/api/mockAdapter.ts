import type * as T from '../contracts/types';
import type { SentinelApi } from './interfaces';
import { ApiClientError, notFound, parseRequest } from './errors';
import { createFixtures, makeReport } from '../mocks/fixtures';
import {
  approvalRequestSchema,
  applyRequestSchema,
  incidentFiltersSchema,
  settingsSchema,
} from '../contracts/schemas';
import { hasPassingValidation } from '../lib/approval';

export class MockSentinelApi implements SentinelApi {
  constructor(
    private latency = 160,
    private store = createFixtures(),
  ) {}
  resetDemo = async () => {
    this.store = createFixtures();
  };
  private async response<TData>(data: TData): Promise<T.ApiResponse<TData>> {
    const snapshot = structuredClone({
      data,
      meta: { request_id: crypto.randomUUID(), schema_version: '1.0' as const },
    });
    await new Promise((r) => setTimeout(r, this.latency));
    return snapshot;
  }
  private incident(id: string) {
    const item = this.store.incidents.find((i) => i.id === id);
    if (!item) throw notFound();
    return item;
  }
  private patch(id: string) {
    const item = this.store.incidents.flatMap((i) => i.patches).find((p) => p.id === id);
    if (!item) throw notFound();
    return item;
  }
  private event(i: T.IncidentDetail, state: T.RunState, message: string) {
    i.status = state;
    i.current_stage = state;
    this.store.events.push({
      id: crypto.randomUUID(),
      incident_id: i.id,
      run_id: i.active_run_id!,
      event_type: state,
      actor_type: state === 'approved' || state === 'rejected' ? 'human' : 'system',
      actor_id: state === 'approved' || state === 'rejected' ? 'demo_reviewer' : 'manager',
      payload: { message },
      occurred_at: new Date().toISOString(),
    });
    this.store.agents.find((a) => a.agent_type === 'manager')!.last_activity =
      `${i.id}: ${state.replaceAll('_', ' ')}.`;
    if (state === 'resolved' || state === 'rejected') {
      this.store.agents.find((a) => a.agent_type === 'reporting')!.last_activity =
        `Report generated for ${i.id}.`;
    }
  }
  private exact(i: T.IncidentDetail, b: T.ApplyRequest) {
    const p = i.patches.at(-1);
    if (!p) throw notFound();
    if (
      i.id === 'inc_006' ||
      p.id !== b.candidate_id ||
      p.patch_hash !== b.patch_hash ||
      p.base_revision !== b.base_revision ||
      p.base_revision !== i.repository_revision ||
      p.base_revision !==
        this.store.applications.find((a) => a.id === i.application_id)?.repository_revision ||
      p.status === 'stale'
    ) {
      p.status = 'stale';
      i.can_approve = false;
      i.can_apply = false;
      i.can_reject = false;
      i.permission_reason =
        'Candidate changed. Review the current revision before making a new decision.';
      throw new ApiClientError('CANDIDATE_STALE', i.permission_reason, 409);
    }
    return p;
  }
  getHealth = () => this.response({ status: 'ok' as const, version: 'mock-1.0' });
  getDashboardSummary = () =>
    this.response({
      total_incidents: this.store.incidents.length,
      open_incidents: this.store.incidents.filter(
        (i) => !['resolved', 'reported', 'rejected', 'unresolved'].includes(i.status),
      ).length,
      awaiting_approval: this.store.incidents.filter((i) => i.status === 'awaiting_approval')
        .length,
      resolved: this.store.incidents.filter((i) => i.status === 'resolved').length,
      active_agents: this.store.agents.filter((a) => a.status === 'running').length,
      current_runs: this.store.incidents.filter((i) =>
        ['applying', 'verifying', 'validating', 'diagnosing', 'generating_patch'].includes(
          i.status,
        ),
      ).length,
      agent_statuses: this.store.agents,
      last_updated: new Date().toISOString(),
    });
  listApplications = () => this.response(this.store.applications);
  getApplication = (id: string) => {
    const a = this.store.applications.find((a) => a.id === id);
    if (!a) throw notFound();
    return this.response(a);
  };
  setMonitoring = (id: string, enabled: boolean) => {
    const a = this.store.applications.find((a) => a.id === id);
    if (!a) throw notFound();
    a.monitoring_enabled = enabled;
    return this.response(a);
  };
  listIncidents = async (filters: T.IncidentFilters = {}) => {
    const f = parseRequest(incidentFiltersSchema, filters),
      closed = ['resolved', 'rejected', 'unresolved', 'reported'];
    const items = this.store.incidents.filter(
      (i) =>
        (!f.scope ||
          f.scope === 'all' ||
          (f.scope === 'closed'
            ? closed.includes(i.status)
            : f.scope === 'open'
              ? !closed.includes(i.status)
              : f.scope === 'candidates'
                ? i.patches.length > 0
                : i.patches.length > 0 &&
                  ['awaiting_approval', 'approved', 'applying', 'verifying', 'restoring'].includes(
                    i.status,
                  ))) &&
        (!f.status || i.status === f.status) &&
        (!f.severity || i.severity === f.severity) &&
        (!f.application_id || i.application_id === f.application_id) &&
        (!f.search ||
          `${i.id} ${i.error_type} ${i.message}`.toLowerCase().includes(f.search.toLowerCase())),
    );
    const severity = { critical: 4, high: 3, medium: 2, low: 1 };
    items.sort(
      (a, b) =>
        (f.sort === 'severity_desc' ? severity[b.severity] - severity[a.severity] : 0) ||
        (f.sort === 'detected_asc'
          ? a.detected_at.localeCompare(b.detected_at)
          : b.detected_at.localeCompare(a.detected_at)) ||
        a.id.localeCompare(b.id),
    );
    const offset = Math.max(0, Number(f.cursor) || 0),
      limit = f.limit ?? 10;
    return this.response({
      items: items.slice(offset, offset + limit),
      total: items.length,
      next_cursor: offset + limit < items.length ? String(offset + limit) : null,
    });
  };
  getIncident = (id: string) => this.response(this.incident(id));
  getIncidentEvents = (id: string) => {
    this.incident(id);
    return this.response(this.store.events.filter((e) => e.incident_id === id));
  };
  listAgents = () => this.response(this.store.agents);
  getAgent = (type: T.AgentType) => {
    const a = this.store.agents.find((a) => a.agent_type === type);
    if (!a) throw notFound();
    return this.response(a);
  };
  listPatches = (id: string) => this.response(this.incident(id).patches);
  getPatch = (id: string) => this.response(this.patch(id));
  getValidation = (id: string) => {
    const p = this.patch(id),
      v = this.incident(p.incident_id).validation;
    if (!v) throw notFound();
    return this.response(v);
  };
  decide = async (id: string, body: T.ApprovalRequest) => {
    const b = parseRequest(approvalRequestSchema, body),
      i = this.incident(id),
      p = this.exact(i, b);
    if (i.status !== 'awaiting_approval')
      throw new ApiClientError('CONFLICT', 'This candidate is no longer awaiting a decision.', 409);
    if (
      b.decision === 'approve' &&
      (!i.can_approve || p.status !== 'validated' || !hasPassingValidation(p, i.validation))
    )
      throw new ApiClientError(
        'TESTS_NOT_PASSED',
        'All required checks must pass before approval.',
        409,
      );
    if (b.decision === 'reject' && !i.can_reject)
      throw new ApiClientError(
        'FORBIDDEN',
        'This candidate cannot be rejected in its current state.',
        403,
      );
    i.decision = {
      ...b,
      id: crypto.randomUUID(),
      incident_id: id,
      actor_id: 'demo_reviewer',
      decided_at: new Date().toISOString(),
    };
    i.can_approve = false;
    i.can_reject = false;
    i.can_apply = b.decision === 'approve';
    p.status = b.decision === 'approve' ? 'approved' : 'rejected';
    this.event(
      i,
      b.decision === 'approve' ? 'approved' : 'rejected',
      b.comment || 'Human decision recorded in simulated state.',
    );
    if (b.decision === 'reject') i.report = makeReport(id, 'rejected', new Date().toISOString());
    return this.response(i.decision);
  };
  applyApprovedPatch = async (id: string, body: T.ApplyRequest) => {
    const b = parseRequest(applyRequestSchema, body),
      workspace = this.store,
      i = this.incident(id),
      p = this.exact(i, b);
    if (
      !i.can_apply ||
      i.status !== 'approved' ||
      i.decision?.decision !== 'approve' ||
      i.decision.patch_hash !== b.patch_hash ||
      i.decision.candidate_id !== b.candidate_id ||
      i.decision.base_revision !== b.base_revision
    )
      throw new ApiClientError(
        'APPROVAL_REQUIRED',
        'Approve this exact candidate before applying.',
        409,
      );
    if (p.status !== 'approved' || !hasPassingValidation(p, i.validation))
      throw new ApiClientError(
        'TESTS_NOT_PASSED',
        'Validation for this exact approved candidate must still pass.',
        409,
      );
    i.can_apply = false;
    const attempt: T.ApplicationAttempt = {
      id: crypto.randomUUID(),
      candidate_id: p.id,
      snapshot_ref: 'simulated_snapshot',
      before_revision: p.base_revision,
      after_revision: null,
      status: 'applying',
      applied_at: new Date().toISOString(),
      restore_status: 'not_needed',
    };
    i.application_attempt = attempt;
    this.event(i, 'applying', 'Simulating local application; no filesystem operations.');
    await new Promise((r) => setTimeout(r, this.latency * 4));
    if (workspace !== this.store)
      throw new ApiClientError(
        'CONFLICT',
        'Demo data was reset. Review the restored incident.',
        409,
      );
    attempt.status = 'verifying';
    this.event(i, 'verifying', 'Simulating reproduction, smoke checks and one observation cycle.');
    await new Promise((r) => setTimeout(r, this.latency * 4));
    if (workspace !== this.store)
      throw new ApiClientError(
        'CONFLICT',
        'Demo data was reset. Review the restored incident.',
        409,
      );
    attempt.status = 'resolved';
    attempt.after_revision = 'demo789';
    p.status = 'applied';
    i.resolved_at = new Date().toISOString();
    i.verification = {
      id: crypto.randomUUID(),
      application_attempt_id: attempt.id,
      candidate_id: p.id,
      status: 'passed',
      checks: i.validation!.checks,
      monitoring_observation: 'No recurrence in one simulated observation cycle.',
      evidence_artifact_id: 'simulated_verification',
    };
    this.event(i, 'resolved', 'Simulated verification passed. Report generated.');
    i.report = makeReport(id, 'resolved', new Date().toISOString());
    this.store.applications.find((a) => a.id === i.application_id)!.repository_revision =
      attempt.after_revision;
    return this.response(attempt);
  };
  getReport = (id: string) => {
    const r = this.incident(id).report;
    if (!r) throw notFound();
    return this.response(r);
  };
  getSettings = () => this.response(this.store.settings);
  updateSettings = async (b: Partial<T.SafeBackendSettings>) => {
    this.store.settings = parseRequest(settingsSchema, { ...this.store.settings, ...b });
    return this.response(this.store.settings);
  };
}
