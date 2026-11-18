import { z } from 'zod';

export const agentTypeSchema = z.enum([
  'manager',
  'monitoring',
  'diagnosis',
  'repair',
  'testing',
  'reporting',
]);
export const runStateSchema = z.enum([
  'detected',
  'diagnosing',
  'generating_patch',
  'validating',
  'revision_requested',
  'awaiting_approval',
  'approved',
  'applying',
  'verifying',
  'restoring',
  'resolved',
  'rejected',
  'manual_review',
  'unresolved',
  'error',
  'reported',
]);
export const severitySchema = z.enum(['low', 'medium', 'high', 'critical']);
export const incidentScopeSchema = z.enum(['all', 'open', 'closed', 'candidates', 'pending']);
export const incidentSortSchema = z.enum(['detected_desc', 'detected_asc', 'severity_desc']);
export const incidentFiltersSchema = z.object({
  status: runStateSchema.optional(),
  severity: severitySchema.optional(),
  application_id: z.string().optional(),
  cursor: z.string().optional(),
  limit: z.number().int().min(1).max(100).optional(),
  search: z.string().optional(),
  scope: incidentScopeSchema.optional(),
  sort: incidentSortSchema.optional(),
});
export const checkStatusSchema = z.enum(['passed', 'failed', 'error', 'timeout', 'not_run']);
export const metaSchema = z.object({ request_id: z.string(), schema_version: z.literal('1.0') });
export const envelope = <T extends z.ZodType>(data: T) => z.object({ data, meta: metaSchema });
export const apiErrorSchema = z.object({
  error: z.object({
    code: z.string(),
    message: z.string(),
    details: z.record(z.string(), z.unknown()),
  }),
  meta: metaSchema,
});
export const applicationSchema = z.object({
  id: z.string(),
  name: z.string(),
  description: z.string(),
  workspace_key: z.string(),
  repository_revision: z.string(),
  monitoring_enabled: z.boolean(),
  status: z.enum(['healthy', 'degraded', 'offline']),
  supported_errors: z.array(z.string()),
});
export const incidentSchema = z.object({
  id: z.string(),
  application_id: z.string(),
  source_event_id: z.string(),
  fingerprint: z.string(),
  severity: severitySchema,
  error_type: z.string(),
  message: z.string(),
  status: runStateSchema,
  current_stage: z.string(),
  repository_revision: z.string(),
  active_run_id: z.string().nullable(),
  detected_at: z.iso.datetime(),
  resolved_at: z.iso.datetime().nullable(),
});
export const evidenceSchema = z.object({
  file_path: z.string(),
  symbol: z.string(),
  start_line: z.number(),
  end_line: z.number(),
  repository_revision: z.string(),
  artifact_id: z.string(),
  excerpt: z.string(),
});
export const diagnosisSchema = z.object({
  incident_id: z.string(),
  run_id: z.string(),
  status: z.enum(['completed', 'manual_review']),
  hypothesis: z.string(),
  confidence_label: z.enum(['low', 'medium', 'high']),
  uncertainty: z.string(),
  suggested_direction: z.string(),
  evidence: z.array(evidenceSchema),
});
export const patchSchema = z.object({
  id: z.string(),
  incident_id: z.string(),
  run_id: z.string(),
  version: z.number(),
  base_revision: z.string(),
  patch_hash: z.string(),
  changed_files: z.array(z.string()),
  rationale: z.string(),
  diff_artifact_id: z.string(),
  status: z.enum(['proposed', 'validated', 'failed', 'stale', 'approved', 'rejected', 'applied']),
  diff: z.string(),
});
export const checkSchema = z.object({
  name: z.string(),
  status: checkStatusSchema,
  exit_code: z.number().nullable(),
  duration_ms: z.number(),
  evidence_artifact_id: z.string(),
  evidence: z.string(),
});
export const validationSchema = z.object({
  candidate_id: z.string(),
  patch_hash: z.string(),
  status: checkStatusSchema,
  checks: z.array(checkSchema),
  environment_id: z.string(),
  duration_ms: z.number(),
});
export const approvalRequestSchema = z.object({
  candidate_id: z.string(),
  patch_hash: z.string(),
  base_revision: z.string(),
  decision: z.enum(['approve', 'reject']),
  comment: z.string().max(2000).optional(),
});
export const applyRequestSchema = approvalRequestSchema.omit({ decision: true, comment: true });
export const decisionSchema = approvalRequestSchema.extend({
  id: z.string(),
  incident_id: z.string(),
  actor_id: z.string(),
  decided_at: z.iso.datetime(),
});
export const attemptSchema = z.object({
  id: z.string(),
  candidate_id: z.string(),
  snapshot_ref: z.string(),
  before_revision: z.string(),
  after_revision: z.string().nullable(),
  status: z.enum(['applying', 'verifying', 'resolved', 'unresolved']),
  applied_at: z.iso.datetime(),
  restore_status: z.enum(['not_needed', 'restored', 'manual_action']),
});
export const verificationSchema = z.object({
  id: z.string(),
  application_attempt_id: z.string(),
  candidate_id: z.string(),
  status: checkStatusSchema,
  checks: z.array(checkSchema),
  monitoring_observation: z.string(),
  evidence_artifact_id: z.string(),
});
export const reportSchema = z.object({
  id: z.string(),
  incident_id: z.string(),
  version: z.number(),
  outcome: runStateSchema,
  report_artifact_id: z.string(),
  summary: z.string(),
  limitations: z.array(z.string()),
  generated_at: z.iso.datetime(),
});
export const incidentDetailSchema = incidentSchema.extend({
  source_log: z.string(),
  diagnosis: diagnosisSchema.nullable(),
  patches: z.array(patchSchema),
  validation: validationSchema.nullable(),
  decision: decisionSchema.nullable(),
  application_attempt: attemptSchema.nullable(),
  verification: verificationSchema.nullable(),
  report: reportSchema.nullable(),
  can_approve: z.boolean(),
  can_reject: z.boolean(),
  can_apply: z.boolean(),
  permission_reason: z.string(),
});
export const eventSchema = z.object({
  id: z.string(),
  incident_id: z.string(),
  run_id: z.string(),
  event_type: z.string(),
  actor_type: z.enum(['agent', 'human', 'system']),
  actor_id: z.string(),
  payload: z.record(z.string(), z.unknown()),
  occurred_at: z.iso.datetime(),
});
export const executionSchema = z.object({
  schema_version: z.literal('1.0'),
  incident_id: z.string(),
  run_id: z.string(),
  stage: z.string(),
  agent_type: agentTypeSchema,
  status: z.enum(['idle', 'running', 'completed', 'error', 'offline']),
  created_at: z.iso.datetime(),
  input_revision: z.string(),
  error: z.string().nullable(),
});
export const agentSchema = z.object({
  agent_type: agentTypeSchema,
  name: z.string(),
  status: z.enum(['idle', 'running', 'completed', 'error', 'offline']),
  responsibility: z.string(),
  owner: z.string(),
  current_task: z.string().nullable(),
  last_activity: z.string().nullable(),
});
export const agentDetailSchema = agentSchema.extend({
  inputs: z.array(z.string()),
  outputs: z.array(z.string()),
  recent_runs: z.array(executionSchema),
});
export const summarySchema = z.object({
  total_incidents: z.number(),
  open_incidents: z.number(),
  awaiting_approval: z.number(),
  resolved: z.number(),
  active_agents: z.number(),
  current_runs: z.number(),
  agent_statuses: z.array(agentSchema),
  last_updated: z.iso.datetime(),
});
export const settingsSchema = z.object({
  monitoring_interval_seconds: z.number().int().min(3).max(60),
  max_candidate_revisions: z.number().int().min(0).max(2),
});
export const healthSchema = z.object({ status: z.enum(['ok', 'degraded']), version: z.string() });
export const paginated = <T extends z.ZodType>(item: T) =>
  z.object({ items: z.array(item), next_cursor: z.string().nullable(), total: z.number() });
