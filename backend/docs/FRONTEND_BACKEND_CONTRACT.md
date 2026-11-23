# Frontend–backend contract 1.0

## Phase 3 implementation status

Database-backed read endpoints and operator-only registration/ingestion are now implemented. See [Phase 3 API contract](PHASE_3_API.md) for the current endpoint matrix, new intake payloads, local read-access exception, artifact handling and cursor rules. That document supersedes historical implementation-status and planned-authentication statements below; the frozen frontend schemas and adapter remain unchanged. Approval/application/monitoring/settings mutations return structured 501 errors and are not operational.

Phase 0 inspection: 2026-11-18. Starting authority: `frontend/src/contracts/schemas.ts`, `types.ts`, `api/interfaces.ts`, `api/realAdapter.ts`, ADR-001 and ADR-002. The two root specifications, frontend README, audit, UX redesign, mock adapter, query hooks, routes, review gates, and unit/browser tests were inspected. This document freezes the integration decisions before backend implementation.

## Scope and discrepancy decisions

1. The architecture is a blueprint, not an existing server. Only `GET /api/v1/health` is implemented in Phase 1. Other domain endpoints below are reserved contracts, **not working functionality**. Unimplemented URLs return a real 404 error, never simulated success.
2. Blueprint examples omit detail projection fields; the actual Zod schemas require sanitized `excerpt`, unified `diff`, check `evidence`, report `summary`/`limitations`, nested incident results and permission flags. Preserve all of them (ADR-001). Artifact IDs remain attached; projected text does not replace authoritative artifact storage.
3. The master prompt's `repairing`, `diagnosis_completed`, `validation_failed`, and `verification_failed` are not wire run states. Preserve `generating_patch`, `revision_requested`, and the other existing states. Represent failed validation through check status; failed verification is represented through failed checks and an unresolved/error outcome, with restoration events. Do not add enum values without a coordinated contract revision.
4. Real IDs may be UUID strings, but frontend/mock IDs such as `app_demo` and `inc_001` are valid opaque strings. Do not require UUID-form IDs in transport schemas. Hash/revision strings are also opaque on the wire; enforce SHA-256 integrity and exact revision binding in later business services.
5. `search`, `scope` and `sort` are existing additions to the original blueprint, not new backend inventions. Implement their exact semantics before connecting queues/history (ADR-002).
6. No login/session bootstrap endpoint or current-user schema exists in the frontend. Cookie transport is defined; authentication APIs and an actual sign-in UI must be specified together in a later phase. Do not trust `demo_reviewer` or invent working authentication in Phase 1.
7. The master prompt describes ingestion, registration, run control, verification, report lists/history and artifact downloads beyond the current adapter. These are planned below; their payloads remain **unfrozen**, not implied by broad prose.
8. Old frontend README/audit/UX notes describe a frontend-only delivery and obsolete visual/video states. Their historical test counts and claims of no backend are dated context, not current acceptance results. Phase 1 adds a health service only; keep mock mode and the isolated learning adapter unchanged. No UI or wire schema changes are needed.

## Transport

Base: `/api/v1`; default HTTP adapter base URL `http://localhost:8000/api/v1`, configured with `VITE_API_BASE_URL`. `VITE_DATA_SOURCE=mock` remains default; `api` selects `HttpSentinelApi` once. No silent API-to-mock fallback. Public `/demo` always uses its own isolated learning mock, even in API mode.

Successful JSON: `{ "data": T, "meta": { "request_id": string, "schema_version": "1.0" } }`.
Errors: `{ "error": { "code": string, "message": string, "details": object }, "meta": { "request_id": string, "schema_version": "1.0" } }`.
Arrays and pagination are inside `data`. Fields use snake_case. Metadata version is independent of backend package version (`0.1.0`). Phase 1 generates server UUID request IDs and returns `X-Request-ID`; an incoming request ID is not trusted. Phase 1 does not implement domain reads or writes.

All documented timestamps are UTC RFC 3339 strings ending in `Z`, e.g. `2026-11-18T12:00:00.000Z`; no naive/local timestamps. `z.iso.datetime()` enforces UTC for timestamp fields; `AgentSummary.last_activity` is an exception: the current schema permits a nullable **display string**, and the mock uses descriptive activity text. Do not interpret it as a timestamp. `current_task` is also nullable text.

GET requests: `Accept: application/json`, `credentials: include`. Mutations add `Idempotency-Key` (UUID), JSON content type when there is a body, and `X-CSRF-Token` decoded from the non-HttpOnly `csrf_token` cookie if present. The future session cookie must be HttpOnly; actors come from the server session. Same hostname on frontend/backend is required for the current cookie-reading convention. Exact credentialed CORS origins, no wildcard. CORS is not authentication.

The adapter aborts at 12 seconds. Long workflows must enqueue durable work and return an actual persisted attempt/run promptly; subsequent reads show progress. Automatic mutation retries are disabled. The client currently generates a new idempotency key per submission, so future transport retries must retain the original key. Server idempotency must bind identity, method, path and canonical body; conflicting reuse must fail, not replay a different operation.

## Frozen adapter endpoints

All success statuses below are 200 for the current call shape; future asynchronous writes may use 202 with the **same documented data type**. No response body for these methods may be replaced by 204. Authentication requirements describe the target backend, not a Phase 1 implementation.

| Method and path | Adapter method | Request | `data` response | Phase / target authorization |
|---|---|---|---|---|
| GET `/health` | getHealth | none | Health | Phase 1; public liveness |
| GET `/dashboard/summary` | getDashboardSummary | none | DashboardSummary | planned; authenticated read |
| GET `/applications` | listApplications | none | Application[] | planned; authenticated read |
| GET `/applications/{id}` | getApplication | opaque path ID | Application | planned; authenticated read |
| POST `/applications/{id}/monitoring/start` | setMonitoring(id,true) | no body | Application | planned; authorized mutation + CSRF/idempotency |
| POST `/applications/{id}/monitoring/stop` | setMonitoring(id,false) | no body | Application | same |
| GET `/incidents` | listIncidents | filters below | Paginated<Incident> | planned; authenticated read |
| GET `/incidents/{id}` | getIncident | path ID | IncidentDetail | planned; authenticated read |
| GET `/incidents/{id}/events` | getIncidentEvents | path ID | IncidentEvent[] | planned; authenticated read |
| GET `/agents` | listAgents | none | AgentSummary[] | planned; authenticated read |
| GET `/agents/{agent_type}` | getAgent | AgentType | AgentDetail | planned; authenticated read |
| GET `/incidents/{id}/patches` | listPatches | path ID | PatchCandidate[] | planned; authenticated read |
| GET `/patches/{candidate_id}` | getPatch | path ID | PatchCandidate | planned; authenticated read |
| GET `/patches/{candidate_id}/validation` | getValidation | path ID | ValidationResult | planned; authenticated read |
| POST `/incidents/{id}/decision` | decide | ApprovalRequest | ApprovalDecision | planned; reviewer permission + exact evidence gates |
| POST `/incidents/{id}/apply` | applyApprovedPatch | ApplyRequest | ApplicationAttempt | planned; apply permission + separate approval/application gates |
| GET `/incidents/{id}/report` | getReport | path ID | IncidentReport | planned; authenticated read; absent report = 404 |
| GET `/settings` | getSettings | none | SafeBackendSettings | planned; authenticated read |
| PATCH `/settings` | updateSettings | partial SafeBackendSettings only | SafeBackendSettings | planned; administrator permission + CSRF/idempotency |

Monitoring endpoints have no JSON body; do not require an empty object. IDs are URL encoded by the adapter. Unknown record IDs, absent candidates, validation or reports are 404, not null or invented data.

## Incident query, pagination and sorting

All optional query values are encoded strings; `limit` must parse as an integer 1–100. Defaults: `limit=10`, `scope=all`, `sort=detected_desc`. Fields:

| Parameter | Values / meaning |
|---|---|
| `status` | one RunState |
| `severity` | one Severity |
| `application_id` | opaque application ID |
| `cursor` | opaque continuation token; null in response means no next page |
| `limit` | 1–100, integer |
| `search` | case-insensitive substring across incident ID, error_type and message |
| `scope` | all, open, closed, candidates, pending |
| `sort` | detected_desc, detected_asc, severity_desc |

Closed = `resolved`, `rejected`, `unresolved`, `reported`. Open = their complement (includes manual_review/error). Candidates = incidents with at least one patch. Pending = incidents with a patch and state in `awaiting_approval`, `approved`, `applying`, `verifying`, `restoring`. All filters intersect. Filter and sort **before** pagination. Severity order critical > high > medium > low; timestamp descending then ID ascending breaks ties. `detected_asc` reverses only timestamp order. `total` counts all matching rows, not this page. `items` contains only Incident summaries. `next_cursor: string|null`. The numeric offset used in mocks is not a backend cursor requirement; the UI stores visited opaque tokens and never decodes them. `from` in UI URLs is browser history only and must not be required by the API. Invalid, stale or filter-mismatched cursor semantics must be specified when persistence is implemented (proposed 422 VALIDATION_ERROR); do not silently reinterpret tokens.

## All wire enums

- AgentType: manager, monitoring, diagnosis, repair, testing, reporting (six roles, in that display order).
- Agent/execution status: idle, running, completed, error, offline.
- RunState: detected, diagnosing, generating_patch, validating, revision_requested, awaiting_approval, approved, applying, verifying, restoring, resolved, rejected, manual_review, unresolved, error, reported.
- Severity: low, medium, high, critical.
- CheckStatus: passed, failed, error, timeout, not_run.
- Application status: healthy, degraded, offline.
- Diagnosis status: completed, manual_review. Confidence: low, medium, high.
- Patch status: proposed, validated, failed, stale, approved, rejected, applied.
- Decision: approve, reject.
- ApplicationAttempt status: applying, verifying, resolved, unresolved. Restore status: not_needed, restored, manual_action.
- Actor type: agent, human, system.
- Health status: ok, degraded.
- IncidentScope and IncidentSort: values in query table above.

## Complete data shapes

Notation: `s` string, `n` number, `b` boolean, `utc` UTC timestamp, `T[]` array. `T|null` is a **required nullable field**; `?` alone means optional. All fields below are required unless marked `?`. JSON objects retain these exact names. Wire numbers are not automatically positive integers unless the Zod schema imposes that constraint; future service invariants may be stricter, but must not change transport shapes.

- **Health**: `status: ok|degraded`, `version:s` (backend release string).
- **Application**: `id:s`, `name:s`, `description:s`, `workspace_key:s` (public configured key, never an absolute local path), `repository_revision:s`, `monitoring_enabled:b`, `status:ApplicationStatus`, `supported_errors:s[]`.
- **Incident**: `id:s`, `application_id:s`, `source_event_id:s`, `fingerprint:s`, `severity:Severity`, `error_type:s`, `message:s` (sanitized), `status:RunState`, `current_stage:s`, `repository_revision:s`, `active_run_id:s|null`, `detected_at:utc`, `resolved_at:utc|null`.
- **Evidence**: `file_path:s` (allowlisted relative path), `symbol:s`, `start_line:n`, `end_line:n`, `repository_revision:s`, `artifact_id:s`, `excerpt:s` (sanitized source projection).
- **Diagnosis**: `incident_id:s`, `run_id:s`, `status:DiagnosisStatus`, `hypothesis:s`, `confidence_label:Confidence`, `uncertainty:s`, `suggested_direction:s`, `evidence:Evidence[]`.
- **PatchCandidate**: `id:s`, `incident_id:s`, `run_id:s`, `version:n`, `base_revision:s`, `patch_hash:s`, `changed_files:s[]`, `rationale:s`, `diff_artifact_id:s`, `status:PatchStatus`, `diff:s` (exact unified diff corresponding to the hash).
- **Check**: `name:s`, `status:CheckStatus`, `exit_code:n|null`, `duration_ms:n`, `evidence_artifact_id:s`, `evidence:s` (sanitized captured result; not inferred).
- **ValidationResult**: `candidate_id:s`, `patch_hash:s`, `status:CheckStatus`, `checks:Check[]`, `environment_id:s`, `duration_ms:n`.
- **ApprovalRequest**: `candidate_id:s`, `patch_hash:s`, `base_revision:s`, `decision:approve|reject`, `comment?:s` (maximum 2000 characters). No actor field is accepted as identity.
- **ApplyRequest**: `candidate_id:s`, `patch_hash:s`, `base_revision:s`. No decision/comment fields.
- **ApprovalDecision**: ApprovalRequest plus `id:s`, `incident_id:s`, `actor_id:s` (server derived), `decided_at:utc`.
- **ApplicationAttempt**: `id:s`, `candidate_id:s`, `snapshot_ref:s`, `before_revision:s`, `after_revision:s|null`, `status:AttemptStatus`, `applied_at:utc`, `restore_status:RestoreStatus`.
- **VerificationResult**: `id:s`, `application_attempt_id:s`, `candidate_id:s`, `status:CheckStatus`, `checks:Check[]`, `monitoring_observation:s`, `evidence_artifact_id:s`.
- **IncidentReport**: `id:s`, `incident_id:s`, `version:n`, `outcome:RunState`, `report_artifact_id:s`, `summary:s`, `limitations:s[]`, `generated_at:utc`.
- **IncidentDetail**: all Incident fields plus `source_log:s` (redacted); `diagnosis:Diagnosis|null`; `patches:PatchCandidate[]`; `validation:ValidationResult|null`; `decision:ApprovalDecision|null`; `application_attempt:ApplicationAttempt|null`; `verification:VerificationResult|null`; `report:IncidentReport|null`; `can_approve:b`, `can_reject:b`, `can_apply:b`, `permission_reason:s`. Absence of evidence remains null/empty, not fabricated.
- **IncidentEvent**: `id:s`, `incident_id:s`, `run_id:s`, `event_type:s`, `actor_type:agent|human|system`, `actor_id:s`, `payload:Record<string,unknown>`, `occurred_at:utc`.
- **AgentExecution**: `schema_version:'1.0'`, `incident_id:s`, `run_id:s`, `stage:s`, `agent_type:AgentType`, `status:AgentStatus`, `created_at:utc`, `input_revision:s`, `error:s|null` (sanitized).
- **AgentSummary**: `agent_type:AgentType`, `name:s`, `status:AgentStatus`, `responsibility:s`, `owner:s`, `current_task:s|null`, `last_activity:s|null` (display text, not necessarily UTC).
- **AgentDetail**: AgentSummary plus `inputs:s[]`, `outputs:s[]`, `recent_runs:AgentExecution[]`.
- **DashboardSummary**: `total_incidents:n`, `open_incidents:n`, `awaiting_approval:n`, `resolved:n`, `active_agents:n`, `current_runs:n`, `agent_statuses:AgentSummary[]`, `last_updated:utc`. Counts derive from persisted facts; active_agents counts genuinely running agents, not the constant six.
- **SafeBackendSettings**: `monitoring_interval_seconds:integer[3,60]`, `max_candidate_revisions:integer[0,2]`. PATCH accepts only optional versions of these two fields. No secrets/provider keys.
- **Paginated<T>**: `items:T[]`, `next_cursor:s|null`, `total:n`.

## Errors and HTTP statuses

| Code | HTTP | Meaning |
|---|---|---|
| VALIDATION_ERROR | 422 | malformed request/filter/body; sanitized field locations only |
| UNAUTHENTICATED | 401 | authenticated session required (future auth) |
| FORBIDDEN | 403 | role, permission or CSRF check failed (future auth) |
| NOT_FOUND | 404 | missing resource or unimplemented endpoint |
| METHOD_NOT_ALLOWED | 405 | unsupported method; preserve Allow header |
| CONFLICT | 409 | invalid/duplicate state transition or conflicting operation |
| CANDIDATE_STALE | 409 | ID/hash/base/current revision/evidence mismatch |
| APPROVAL_REQUIRED | 409 | no exact approved decision for application |
| TESTS_NOT_PASSED | 409 | missing, mismatched, nonempty/all-passed requirement not met |
| UNSUPPORTED_FAILURE | 422 | unsupported ingestion/diagnosis input |
| RATE_LIMITED | 429 | later configured resource/rate limit |
| INTERNAL_ERROR | 500 | generic server failure; never a traceback or secret |
| HTTP_ERROR | other 4xx/5xx | safe fallback for framework HTTP failures |

The frontend schema accepts string codes. Phase 1 exercises 404/405/422/500 and custom typed errors; auth, workflow and rate-limit codes above are reserved requirements, not implemented gates. Client-only codes `OFFLINE`, `TIMEOUT`, `INVALID_RESPONSE`, `HTTP_ERROR`, `VALIDATION_ERROR` can be produced before a successful server response. A failed operation must not return 200. Missing reports are 404. CORS preflight is an HTTP protocol response, not a domain JSON result.

## State, approval and recovery contract

Proposed service transitions, retaining current wire values:

```
detected -> diagnosing -> generating_patch -> validating
diagnosing -> manual_review | error
validating -> awaiting_approval | revision_requested | error
revision_requested -> generating_patch (bounded retries) | unresolved
awaiting_approval -> approved | rejected
approved -> applying -> verifying
verifying -> resolved | restoring | unresolved | error
restoring -> unresolved | error
terminal outcome -> reported (only if the report retains the actual outcome)
```

These are a later Manager implementation requirement, not a Phase 1 state machine. Never report success from animation or enqueue acceptance. `resolved` requires actual post-application evidence; restoration does not resolve the original incident. Preserve rejection, failed-verification and unresolved outcomes in reports. UI terminal polling states: resolved, reported, rejected, unresolved, manual_review, error. Active detail polls at the stored 3–5 second preference; events at 4 seconds. Queries stop on errors/hidden tabs and retry network/5xx at most twice with exponential backoff. Health polls every 30 seconds in API mode.

For approval: authenticated authorized reviewer; exact incident/candidate/hash/base; candidate validated; current source/application revision matches; validation belongs to that candidate/hash; at least one recorded check; every required check passed with exit code zero. No changed evidence after review. Reject cannot apply. Approval records only the decision. Apply independently checks all approval/validation/revision gates and clean allowlisted workspace, snapshots reversibly, then applies only that patch. Concurrent conflicts must be prevented by transactions/locking in later phases. `can_*` booleans are UI hints, never authority. Each revision gets a new candidate ID, new validation and fresh approval.

## Planned additions (not yet frozen or implemented)

Architecture-reserved paths: POST `/incidents` (normalized ingestion); POST/GET `/incidents/{id}/runs`; GET `/incidents/{id}/diagnosis`; GET `/incidents/{id}/verification`; GET `/incidents/{id}/reports`; GET `/artifacts/{id}`; GET `/events?cursor=`. The actual adapter does not call these. Registration and login/logout/current-user paths have **no agreed implementation path or payload** yet. Specify request models, roles, artifact content types, pagination, and session lifecycle when their phases begin. Do not add fictional success routes in this foundation.

## Acceptance evidence

Existing frontend contract tests exercise seven mock scenarios, exact evidence gates, scopes/sorting, opaque cursor handling and separate approve/apply. Existing HTTP browser tests intercept responses and therefore do not prove a running backend. Phase 1 adds an actual Uvicorn health/error smoke check through the unchanged `HttpSentinelApi` and Zod schemas; it does not claim full UI integration. Foundation OpenAPI publishes only implemented operations. Later domain phases must add live end-to-end cases and keep this document synchronized.
