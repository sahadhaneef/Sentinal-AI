import type * as T from '../contracts/types';
export interface SentinelApi {
  getHealth(): Promise<T.ApiResponse<{ status: 'ok' | 'degraded'; version: string }>>;
  getDashboardSummary(): Promise<T.ApiResponse<T.DashboardSummary>>;
  listApplications(): Promise<T.ApiResponse<T.Application[]>>;
  getApplication(id: string): Promise<T.ApiResponse<T.Application>>;
  setMonitoring(id: string, enabled: boolean): Promise<T.ApiResponse<T.Application>>;
  listIncidents(filters?: T.IncidentFilters): Promise<T.ApiResponse<T.Paginated<T.Incident>>>;
  getIncident(id: string): Promise<T.ApiResponse<T.IncidentDetail>>;
  getIncidentEvents(id: string): Promise<T.ApiResponse<T.IncidentEvent[]>>;
  listAgents(): Promise<T.ApiResponse<T.AgentSummary[]>>;
  getAgent(type: T.AgentType): Promise<T.ApiResponse<T.AgentDetail>>;
  listPatches(incidentId: string): Promise<T.ApiResponse<T.PatchCandidate[]>>;
  getPatch(candidateId: string): Promise<T.ApiResponse<T.PatchCandidate>>;
  getValidation(candidateId: string): Promise<T.ApiResponse<T.ValidationResult>>;
  decide(incidentId: string, body: T.ApprovalRequest): Promise<T.ApiResponse<T.ApprovalDecision>>;
  applyApprovedPatch(
    incidentId: string,
    body: T.ApplyRequest,
  ): Promise<T.ApiResponse<T.ApplicationAttempt>>;
  getReport(incidentId: string): Promise<T.ApiResponse<T.IncidentReport>>;
  getSettings(): Promise<T.ApiResponse<T.SafeBackendSettings>>;
  updateSettings(
    body: Partial<T.SafeBackendSettings>,
  ): Promise<T.ApiResponse<T.SafeBackendSettings>>;
}
