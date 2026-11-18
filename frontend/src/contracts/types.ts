import type { z } from 'zod';
import type * as S from './schemas';
export type AgentType = z.infer<typeof S.agentTypeSchema>;
export type RunState = z.infer<typeof S.runStateSchema>;
export type Severity = z.infer<typeof S.severitySchema>;
export type CheckStatus = z.infer<typeof S.checkStatusSchema>;
export type AgentStatus = AgentSummary['status'];
export type Decision = ApprovalRequest['decision'];
export interface ApiResponse<T> {
  data: T;
  meta: { request_id: string; schema_version: '1.0' };
}
export type ApiError = z.infer<typeof S.apiErrorSchema>;
export type Application = z.infer<typeof S.applicationSchema>;
export type Incident = z.infer<typeof S.incidentSchema>;
export type IncidentDetail = z.infer<typeof S.incidentDetailSchema>;
export type Diagnosis = z.infer<typeof S.diagnosisSchema>;
export type PatchCandidate = z.infer<typeof S.patchSchema>;
export type ValidationResult = z.infer<typeof S.validationSchema>;
export type ApprovalRequest = z.infer<typeof S.approvalRequestSchema>;
export type ApplyRequest = z.infer<typeof S.applyRequestSchema>;
export type ApprovalDecision = z.infer<typeof S.decisionSchema>;
export type ApplicationAttempt = z.infer<typeof S.attemptSchema>;
export type VerificationResult = z.infer<typeof S.verificationSchema>;
export type IncidentReport = z.infer<typeof S.reportSchema>;
export type IncidentEvent = z.infer<typeof S.eventSchema>;
export type AgentExecution = z.infer<typeof S.executionSchema>;
export type AgentSummary = z.infer<typeof S.agentSchema>;
export type AgentDetail = z.infer<typeof S.agentDetailSchema>;
export type DashboardSummary = z.infer<typeof S.summarySchema>;
export type SafeBackendSettings = z.infer<typeof S.settingsSchema>;
export interface Paginated<T> {
  items: T[];
  next_cursor: string | null;
  total: number;
}
export type IncidentFilters = z.infer<typeof S.incidentFiltersSchema>;
