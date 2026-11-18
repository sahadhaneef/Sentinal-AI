import { z } from 'zod';
import * as S from '../contracts/schemas';
import type * as T from '../contracts/types';
import type { SentinelApi } from './interfaces';
import { ApiClientError, parseRequest } from './errors';

export class HttpSentinelApi implements SentinelApi {
  constructor(private baseUrl: string) {}
  private async request<Schema extends z.ZodType>(
    path: string,
    schema: Schema,
    method = 'GET',
    body?: unknown,
  ): Promise<T.ApiResponse<z.infer<Schema>>> {
    const controller = new AbortController(),
      timer = setTimeout(() => controller.abort(), 12000);
    try {
      const csrf = document.cookie
        .split('; ')
        .find((c) => c.startsWith('csrf_token='))
        ?.slice(11);
      const response = await fetch(`${this.baseUrl.replace(/\/$/, '')}${path}`, {
        method,
        credentials: 'include',
        signal: controller.signal,
        headers: {
          Accept: 'application/json',
          ...(body ? { 'Content-Type': 'application/json' } : {}),
          ...(method !== 'GET'
            ? {
                'Idempotency-Key': crypto.randomUUID(),
                ...(csrf ? { 'X-CSRF-Token': decodeURIComponent(csrf) } : {}),
              }
            : {}),
        },
        body: body ? JSON.stringify(body) : undefined,
      });
      let raw: unknown;
      try {
        raw = await response.json();
      } catch (error) {
        if (controller.signal.aborted) throw error;
        throw new ApiClientError(
          'INVALID_RESPONSE',
          'The server returned an unreadable response. Try again.',
          response.ok ? 502 : response.status,
        );
      }
      if (!response.ok) {
        const parsed = S.apiErrorSchema.safeParse(raw);
        if (parsed.success)
          throw new ApiClientError(
            parsed.data.error.code,
            parsed.data.error.message,
            response.status,
            parsed.data.error.details,
          );
        throw new ApiClientError(
          'HTTP_ERROR',
          'The server could not complete this request.',
          response.status,
        );
      }
      const parsed = S.envelope(schema).safeParse(raw);
      if (!parsed.success)
        throw new ApiClientError(
          'INVALID_RESPONSE',
          'The API response does not match the agreed contract.',
          502,
        );
      return { data: schema.parse((raw as { data: unknown }).data), meta: parsed.data.meta };
    } catch (error) {
      if (error instanceof ApiClientError) throw error;
      throw new ApiClientError(
        controller.signal.aborted ? 'TIMEOUT' : 'OFFLINE',
        controller.signal.aborted
          ? 'The request timed out. Try again.'
          : 'Backend unavailable. Check the connection and retry.',
      );
    } finally {
      clearTimeout(timer);
    }
  }
  getHealth = () => this.request('/health', S.healthSchema);
  getDashboardSummary = () => this.request('/dashboard/summary', S.summarySchema);
  listApplications = () => this.request('/applications', z.array(S.applicationSchema));
  getApplication = (id: string) =>
    this.request(`/applications/${encodeURIComponent(id)}`, S.applicationSchema);
  setMonitoring = (id: string, enabled: boolean) =>
    this.request(
      `/applications/${encodeURIComponent(id)}/monitoring/${enabled ? 'start' : 'stop'}`,
      S.applicationSchema,
      'POST',
    );
  listIncidents = async (f: T.IncidentFilters = {}) => {
    const params = new URLSearchParams();
    Object.entries(parseRequest(S.incidentFiltersSchema, f)).forEach(([k, v]) => {
      if (v !== undefined && v !== '') params.set(k, String(v));
    });
    return this.request(`/incidents?${params}`, S.paginated(S.incidentSchema));
  };
  getIncident = (id: string) =>
    this.request(`/incidents/${encodeURIComponent(id)}`, S.incidentDetailSchema);
  getIncidentEvents = (id: string) =>
    this.request(`/incidents/${encodeURIComponent(id)}/events`, z.array(S.eventSchema));
  listAgents = () => this.request('/agents', z.array(S.agentSchema));
  getAgent = (type: T.AgentType) =>
    this.request(`/agents/${encodeURIComponent(type)}`, S.agentDetailSchema);
  listPatches = (id: string) =>
    this.request(`/incidents/${encodeURIComponent(id)}/patches`, z.array(S.patchSchema));
  getPatch = (id: string) => this.request(`/patches/${encodeURIComponent(id)}`, S.patchSchema);
  getValidation = (id: string) =>
    this.request(`/patches/${encodeURIComponent(id)}/validation`, S.validationSchema);
  decide = async (id: string, b: T.ApprovalRequest) =>
    this.request(
      `/incidents/${encodeURIComponent(id)}/decision`,
      S.decisionSchema,
      'POST',
      parseRequest(S.approvalRequestSchema, b),
    );
  applyApprovedPatch = async (id: string, b: T.ApplyRequest) =>
    this.request(
      `/incidents/${encodeURIComponent(id)}/apply`,
      S.attemptSchema,
      'POST',
      parseRequest(S.applyRequestSchema, b),
    );
  getReport = (id: string) =>
    this.request(`/incidents/${encodeURIComponent(id)}/report`, S.reportSchema);
  getSettings = () => this.request('/settings', S.settingsSchema);
  updateSettings = async (b: Partial<T.SafeBackendSettings>) =>
    this.request(
      '/settings',
      S.settingsSchema,
      'PATCH',
      parseRequest(S.settingsSchema.partial(), b),
    );
}
