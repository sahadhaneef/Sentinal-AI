# Frontend contract 1.0 — FastAPI handoff

Executable wire shapes live in `schemas.ts`; `types.ts` derives their TypeScript types. Both adapters implement `../api/interfaces.ts`. The backend blueprint governs execution and authorization. No backend is implemented.

URLs below are relative to configurable `/api/v1`. Properties are snake_case. Responses: `{data, meta: {request_id, schema_version: '1.0'}}`. Errors: `{error: {code, message, details}, meta}`. Timestamps are UTC ISO 8601. Mock IDs follow blueprint examples; future UUIDs are accepted as strings.

## Endpoint mapping

- `GET /health` → `getHealth` → `healthSchema`.
- `GET /dashboard/summary` → `getDashboardSummary` → `summarySchema`.
- `GET /applications` → `listApplications` → array of `applicationSchema`.
- `GET /applications/{id}` → `getApplication` → `applicationSchema`.
- `POST /applications/{id}/monitoring/start` or `/stop` → `setMonitoring` → `applicationSchema`.
- `GET /incidents` → `listIncidents` → `paginated(incidentSchema)`. Query: status, severity, application_id, cursor, limit, search, optional scope and sort. See ADR-002 for scope membership and sorting. Filter and sort before pagination. Cursor is opaque to UI; mock uses offsets internally.
- `GET /incidents/{id}` → `getIncident` → `incidentDetailSchema`.
- `GET /incidents/{id}/events` → `getIncidentEvents` → array of `eventSchema`.
- `GET /agents` → `listAgents` → array of `agentSchema` in Manager, Monitoring, Diagnosis, Repair, Testing, Reporting order.
- `GET /agents/{agent_type}` → `getAgent` → `agentDetailSchema`.
- `GET /incidents/{id}/patches` → `listPatches` → array of `patchSchema`.
- `GET /patches/{candidate_id}` → `getPatch` → `patchSchema`.
- `GET /patches/{candidate_id}/validation` → `getValidation` → `validationSchema`.
- `POST /incidents/{id}/decision` → `decide` → `decisionSchema`. Input: `approvalRequestSchema`.
- `POST /incidents/{id}/apply` → `applyApprovedPatch` → `attemptSchema`. Input: `applyRequestSchema`.
- `GET /incidents/{id}/report` → `getReport` → `reportSchema`.
- `GET /settings` → `getSettings` → `settingsSchema`.
- `PATCH /settings` → `updateSettings` → `settingsSchema`. Input: partial allowlisted settings. The current page displays backend settings read-only.

Related evidence is loaded as a detail projection. Standalone patch/validation/report methods also exist for future targeted queries. Projections and the search query addition are specified in ADR-001.

## Mutation and session rules

HTTP requests send session cookies, a fresh `Idempotency-Key` per mutation submission, and `X-CSRF-Token` from the non-HttpOnly `csrf_token` cookie when supplied. The future server must establish and verify the session and CSRF cookie, configure exact-origin credentialed CORS, and derive actors from the session. This convention is not working frontend authentication. Never trust the demo reviewer as identity.

Automatic mutation retries are disabled. If introduced, retain the same idempotency key across one operation's retries. Backend mutations must enforce identity, permissions, exact candidate ID/hash/base, passing validation and current workspace revision. Server-provided `can_approve`, `can_reject`, `can_apply`, `permission_reason` are UX hints, not authorization.

Approve records a decision only. Apply is separate. On 409, close the confirmation, invalidate queries and require fresh review. The stale fixture remains blocked until reset. API apply should return an attempt and expose applying/verifying/terminal state via subsequent incident reads. Mock apply awaits a short deterministic simulation and executes no commands. Reports retain the actual terminal outcome.

## Errors and fixtures

401/403 request access; 404 means missing item; 409 requires fresh review; 422 is validation failure. Network failure is `OFFLINE`, abort is `TIMEOUT`, malformed success is `INVALID_RESPONSE`. API mode never falls back to mocks. Raw traces are never rendered.

Fixtures: `../mocks/fixtures.ts`, `app_demo`, preserved `inc_001`–`inc_006` plus optional unresolved `inc_007`, `patch_001`, revision `abc123`. Contract tests check wire schemas and workflow gates; HTTP tests check transport and errors; browser tests check journeys, responsive layout and accessibility. Carry these fixtures and invariants into backend tests.

The audit requires nonempty recorded checks, all passed with exit code zero and exact candidate/hash association. Approval dialogs freeze the reviewed evidence and refuse changed snapshots. These are defense-in-depth UX/mock behaviors; real authorization and execution must remain server-owned. UI-only `from` cursor-history parameters are never sent to FastAPI. See `../../docs/ADR-002-audit-contract-clarifications.md`.
