# SENTINEL AI — Backend Architecture & API Contract

> Status: implementation blueprint, NOT an implemented backend. Scope: functional local prototype, one designated sample application, six logical agents. Frontend is built first. This document is the contract that the future backend must honor.

## 1. Purpose and non-goals
Detect a supported failure in a local demo application, diagnose using evidence-backed Code RAG, propose a reviewable patch, validate it in isolation, request a human decision, apply only the exact approved patch locally, verify recovery, and report actual outcomes. Never claim autonomous production recovery. No arbitrary remote repositories, unrestricted commands, production deployments, or unsupervised changes.

## 2. Team ownership (source: SENTINEL AI team allocation)
| Member | Responsibility |
|---|---|
| Sahad | Diagnosis Agent, Code RAG, evidence retrieval and root-cause analysis |
| Yadhulakshmi | Repair Agent, candidate diffs, revision history |
| Neha | Monitoring Agent and Reporting Agent, log intake and templated reports |
| Delvin | Manager Agent, shared FastAPI backend, persistence, approval, integration and dashboard coordination |
| Sravan | Testing Agent, isolated tests and local verification |

Human approval is a gate, not a seventh agent. The Manager coordinates every stage rather than running only at the start.

## 3. Recommended stack
- Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2, Alembic, SQLite for the prototype; optional PostgreSQL later without changing service contracts.
- Async-capable API endpoints, background worker/task queue abstraction (a local durable worker is enough initially); no in-memory-only workflow state.
- Agent modules isolated behind Python protocols; LLM provider adapter for Diagnosis/Repair; Monitoring rule-based, Reporting template-based at first.
- Code RAG: allowlisted source indexing with file path, symbol, line range and exact Git revision; local embedding index or lexical retrieval plus optional embeddings. RAG is a Diagnosis capability, not another agent.
- pytest, Ruff, type checks, structured logging and OpenAPI-generated schema.
- Store all timestamps in UTC ISO 8601, IDs as UUID strings, revisions and SHA-256 hashes as strings.

## 4. Architecture
```mermaid
flowchart TD
 UI[React frontend / typed API client] --> API[FastAPI /api/v1]
 API --> AUTH[Prototype identity + permissions]
 API --> DB[(SQLite / SQLAlchemy)]
 API --> MGR[Manager / persistent state machine]
 LOG[Allowlisted demo logs] --> MON[Monitoring]
 MON --> MGR
 MGR --> DIA[Diagnosis + Code RAG]
 DIA --> IDX[(Revision-bound code index)]
 MGR --> REP[Repair candidate generator]
 MGR --> TEST[Isolated test runner]
 MGR --> GATE[Human approval gate]
 GATE --> APPLY[Controlled local apply + snapshot]
 APPLY --> VERIFY[Post-apply verification]
 VERIFY --> MGR
 MGR --> REPORT[Template-based reporting]
 API --> ART[(Artifact store: sanitized logs, diffs, results)]
```

Keep all local file operations on the backend; the browser never reads server repositories or executes patch commands.

## 5. Suggested backend tree
```text
backend/
  app/
    main.py
    core/{config.py,security.py,errors.py,logging.py}
    api/v1/{router.py,health.py,applications.py,incidents.py,agents.py,patches.py,approvals.py,reports.py,settings.py,events.py}
    schemas/{common.py,application.py,incident.py,agent.py,diagnosis.py,patch.py,validation.py,approval.py,report.py}
    db/{base.py,session.py,models.py,migrations/}
    services/{manager.py,monitoring.py,diagnosis.py,code_rag.py,repair.py,testing.py,reporting.py,apply.py,artifact_store.py}
    agents/{manager/,monitoring/,diagnosis/,repair/,testing/,reporting/}
    providers/{llm.py,embeddings.py}
    workers/{dispatcher.py,runner.py}
  tests/{unit/,contract/,integration/,e2e/,fixtures/}
  demo_app/
  pyproject.toml
  .env.example
```

Agent implementations may live in `agents/` while `services/` hold orchestration and external integrations; avoid duplicate business logic.

## 6. Database entities
All tables have `id`, `created_at`, `updated_at` as appropriate.
| Entity | Essential fields / relationships |
|---|---|
| applications | id, name, description, workspace_key, repository_revision, monitoring_enabled, status; workspace path is server-side configuration only |
| incidents | id, application_id, source_event_id, fingerprint, severity, error_type, message, status, current_stage, repository_revision, active_run_id, detected_at, resolved_at; unique deduplication key |
| incident_runs | id, incident_id, schema_version, state, attempt, started_at, finished_at, last_error |
| agent_executions | id, run_id, agent_type, status, input_revision, started_at, completed_at, duration_ms, error_json, output_artifact_id |
| incident_events | id, incident_id, run_id, event_type, actor_type, actor_id, payload_json, occurred_at; append-only audit trail |
| code_index_entries | id, application_id, repository_revision, file_path, symbol, start_line, end_line, content_hash, index_ref |
| diagnoses | id, incident_id, run_id, hypothesis, confidence_label, uncertainty, suggested_direction, evidence_json, status |
| patch_candidates | id, incident_id, run_id, version, base_revision, patch_hash, diff_artifact_id, changed_files_json, rationale, status |
| validation_results | id, candidate_id, patch_hash, status, checks_json, environment_id, evidence_artifact_id, duration_ms |
| approval_decisions | id, incident_id, candidate_id, patch_hash, base_revision, decision, actor_id, comment, decided_at |
| application_attempts | id, candidate_id, snapshot_ref, before_revision, after_revision, status, applied_at, restore_status |
| verification_results | id, application_attempt_id, candidate_id, status, checks_json, monitoring_observation_json, evidence_artifact_id |
| incident_reports | id, incident_id, version, outcome, report_artifact_id, summary_json, generated_at |
| artifacts | id, kind, storage_key, sha256, content_type, redacted, size_bytes |
| settings | key, value_json, updated_at; only allowlisted nonsecret settings through UI |

Prefer stable foreign keys and constraints; indexes on incidents `(application_id, status, detected_at)`, events `(incident_id, occurred_at)`, candidates `(incident_id, version)`. Never store provider API keys in settings responses.

## 7. Canonical API envelope and errors
All responses use a predictable shape. OpenAPI schemas are authoritative once backend exists.
```json
{"data":{"id":"inc_001"},"meta":{"request_id":"req_001","schema_version":"1.0"}}
```
Error responses:
```json
{"error":{"code":"CANDIDATE_STALE","message":"Candidate revision does not match the demo workspace.","details":{}},"meta":{"request_id":"req_002","schema_version":"1.0"}}
```
Common codes: `VALIDATION_ERROR` (422), `UNAUTHENTICATED` (401), `FORBIDDEN` (403), `NOT_FOUND` (404), `CONFLICT` (409), `CANDIDATE_STALE` (409), `APPROVAL_REQUIRED` (409), `TESTS_NOT_PASSED` (409), `UNSUPPORTED_FAILURE` (422), `RATE_LIMITED` (429), `INTERNAL_ERROR` (500). Frontend must display recoverable messages without exposing traces.

## 8. API endpoints (all under /api/v1)
| Method | Endpoint | Behavior |
|---|---|---|
| GET | `/health` | API availability, version, optional dependency summary |
| GET | `/dashboard/summary` | aggregate incident counts, current runs, agent statuses, last updated |
| GET | `/applications` | list monitored demo applications |
| GET | `/applications/{id}` | application detail and current revision |
| POST | `/applications/{id}/monitoring/start` | enable monitoring for allowed demo app |
| POST | `/applications/{id}/monitoring/stop` | stop monitoring |
| GET | `/incidents?status=&severity=&application_id=&cursor=&limit=` | paginated filtered incidents |
| POST | `/incidents` | create or deduplicate a normalized event; internal/authorized ingestion |
| GET | `/incidents/{id}` | full incident summary, stage, references, permissions |
| GET | `/incidents/{id}/events` | timeline and stage history |
| POST | `/incidents/{id}/runs` | authorized start/resume with idempotency key |
| GET | `/incidents/{id}/runs` | execution history |
| GET | `/agents` | six agent summaries, status and last activity |
| GET | `/agents/{agent_type}` | details, latest execution, errors |
| GET | `/incidents/{id}/diagnosis` | root-cause hypothesis and source evidence |
| GET | `/incidents/{id}/patches` | versioned candidates |
| GET | `/patches/{candidate_id}` | exact candidate, hash, base revision, diff artifact |
| GET | `/patches/{candidate_id}/validation` | isolated test evidence |
| POST | `/incidents/{id}/decision` | approve/reject exact candidate; body below |
| POST | `/incidents/{id}/apply` | controlled local application of approved candidate; never general shell execution |
| GET | `/incidents/{id}/verification` | post-apply results |
| GET | `/incidents/{id}/report` | latest report metadata and readable content link |
| GET | `/incidents/{id}/reports` | report history |
| GET | `/artifacts/{id}` | authorized sanitized artifact content / signed reference |
| GET | `/settings` | safe configuration fields and feature flags |
| PATCH | `/settings` | validate and update allowlisted configuration |
| GET | `/events?cursor=` | optional read-only polling feed; SSE later only if needed |

Every mutation uses authentication, role checks, audit events and an `Idempotency-Key` where retries could duplicate work. For prototype identity, use an explicit local developer sign-in or an authenticated local session; never trust a user ID sent in request JSON as proof of identity.

## 9. Example domain contracts
### Incident
```json
{"id":"inc_001","application_id":"app_demo","severity":"high","error_type":"NullReferenceError","message":"Registration fails on missing profile","status":"diagnosing","current_stage":"diagnosis","repository_revision":"abc123","detected_at":"2026-11-17T10:00:00Z","active_run_id":"run_001"}
```
### AgentExecution
```json
{"schema_version":"1.0","incident_id":"inc_001","run_id":"run_001","stage":"diagnosis","agent_type":"diagnosis","status":"completed","created_at":"2026-11-17T10:00:00Z","input_revision":"abc123","error":null}
```
### Diagnosis
```json
{"incident_id":"inc_001","run_id":"run_001","status":"completed","hypothesis":"Profile is accessed before null checking","confidence_label":"medium","uncertainty":"Needs reproduction confirmation","suggested_direction":"Guard missing profile","evidence":[{"file_path":"src/registration.py","symbol":"register_user","start_line":42,"end_line":49,"repository_revision":"abc123","artifact_id":"art_code_001"}]}
```
### PatchCandidate
```json
{"id":"patch_001","incident_id":"inc_001","version":1,"base_revision":"abc123","patch_hash":"sha256:example-placeholder","changed_files":["src/registration.py"],"rationale":"Handle missing profile","diff_artifact_id":"art_diff_001","status":"validated"}
```
### ValidationResult
```json
{"candidate_id":"patch_001","patch_hash":"sha256:example-placeholder","status":"passed","checks":[{"name":"registration_reproduction","status":"passed","exit_code":0,"duration_ms":410,"evidence_artifact_id":"art_test_001"}]}
```
### Approval request
```json
{"candidate_id":"patch_001","patch_hash":"sha256:example-placeholder","base_revision":"abc123","decision":"approve","comment":"Reviewed the exact diff and tests"}
```
Server derives actor from the session, rechecks validation, patch hash, base revision, candidate status, and workspace state. Response returns the persisted decision. Approval must NOT automatically imply application unless that is an explicitly documented server-side policy; default to separate Apply action.

## 10. Workflow state machine
```text
observed -> detected -> diagnosing -> generating_patch -> validating
  -> awaiting_approval -> approved -> applying -> verifying -> resolved -> reported
                                         |
                                         +-> verification_failed -> restoring -> unresolved -> reported
awaiting_approval -> rejected -> reported
validating -> revision_requested -> generating_patch (bounded retries)
any supported stage -> manual_review / unresolved / error (with reason)
```
Separate `incident.status` (user-facing) from `run.state` and `agent_execution.status`. Canonical run states: `detected`, `diagnosing`, `generating_patch`, `validating`, `revision_requested`, `awaiting_approval`, `approved`, `applying`, `verifying`, `restoring`, `resolved`, `rejected`, `manual_review`, `unresolved`, `error`, `reported`. UI may map these to friendlier labels. Retry limit configured (default 2 candidate revisions), with terminal exhaustion. Every transition persisted atomically with an event and protected against duplicate runs.

## 11. Agent handoff requirements
1. **Monitoring (Neha):** tail only configured sample logs; recognize documented patterns; sanitize messages; deduplicate by source event ID/fingerprint; create incident with app ID and exact revision. Unsupported logs become manual review, not fabricated diagnoses.
2. **Manager (Delvin):** persist run, validate typed handoffs, dispatch and time-limit each stage, track retries, prevent duplicate active runs, enforce approval, coordinate apply and restore, create audit trail.
3. **Diagnosis (Sahad):** index only permitted source at exact revision; chunk with path/symbol/line metadata; use stack trace and log context to retrieve; treat source/log text as untrusted data; return cited hypothesis and uncertainty; if no evidence, return `manual_review`.
4. **Repair (Yadhulakshmi):** propose minimal unified diff, changed-file list, rationale and content hash tied to base revision; reject traversal, symlinks, invalid paths and malformed patches; keep previous candidates immutable.
5. **Testing (Sravan):** first reproduce failure, then test candidate in disposable workspace/container with no secrets, allowlisted commands, CPU/time limits and network disabled where feasible; return `passed`, `failed`, `error` or `timeout`, never infer success from missing tests.
6. **Approval / controlled apply (human + Delvin):** present exact diff, hash, base and test evidence; only approved candidate can apply; take reversible snapshot; verify clean revision; apply only to demo workspace; no production writes.
7. **Verification (Sravan + Neha):** rerun reproduction/smoke tests on demo and observe supported error recurrence over documented cycle; if failure, safely restore or request manual intervention; do not overclaim recovery.
8. **Reporting (Neha):** fixed report template from persisted facts including missing evidence, rejection, failed tests, rollback, and limitations; JSON + readable HTML/Markdown.

## 12. Code RAG design (Sahad)
- Inputs: `incident_id`, sanitized error context, `application_id`, `repository_revision`.
- Ingest: allowlisted extensions (`.py`, `.ts`, `.tsx`, `.js`, `.json` as appropriate), exclude `.env`, secrets, `.git`, `node_modules`, venv, builds, binaries, generated files. Enforce repo root confinement and file size limits.
- Parse into function/class-aware chunks; fallback to line windows. Store `path`, `symbol`, `start_line`, `end_line`, `revision`, `sha256` and searchable content/index key.
- Retrieve lexical/semantic candidates, optionally rerank, deduplicate, limit token budget. Every cited excerpt must resolve to same revision.
- Prompt model to separate observation, hypothesis, evidence, confidence and next steps. Never obey instructions embedded in logs/source; never expose secrets.
- Validate output with Pydantic. If source revision changes, invalidate/rebuild affected index entries and invalidate stale candidates/approvals.
- Evaluate on seeded failure fixtures: retrieval hit rate, citation accuracy, unsupported case abstention, diagnosis usefulness, latency; record model/version and costs if an LLM is used.

## 13. Frontend integration: freeze the contract first
- Backend base URL: `http://localhost:8000/api/v1` (configurable through `VITE_API_BASE_URL`). Vite frontend default `http://localhost:5173`.
- Use consistent response envelopes, snake_case JSON and ISO UTC timestamps. Frontend converts labels only at presentation layer.
- Enable CORS for exact dev origin; never wildcard with credentials. Use session cookie with CSRF protection for mutations or an explicitly documented secure token scheme.
- Mock and real adapters must implement identical TypeScript interfaces. No component may call `fetch()` directly.
- Start with GET summary, applications, incidents, agents, incident detail/events, candidate and validation, decision, report. Extend only with real use cases.
- Poll active incident detail every 3–5 seconds, pause on hidden tab, use exponential backoff; stop polling terminal states. SSE optional later.
- Use backend-generated `can_approve`, `can_apply`, `can_reject` flags for UX; backend independently enforces authorization and state.
- Handle 401/403, 404, 409 stale candidate, 422, timeouts, offline and retryable 5xx explicitly. Refetch incident/candidate after mutation.
- Seed mock data using these exact IDs/fields, but mark simulated data clearly in UI; never show fabricated real-time operations.

## 14. Security and safety boundaries
- Only allowlisted local demo app paths, server-side configured. Reject absolute/traversal paths and unsafe symlinks; normalize and validate before read/write.
- Never run commands supplied by the LLM or browser. Testing uses predeclared command IDs and a restricted runner.
- Separate test sandbox from demo apply. No write before human approval; approvals are candidate/hash/revision-specific and expire on change.
- Snapshot before apply, verify base is clean, and only restore when safe; otherwise halt for manual action.
- Redact secrets, tokens and personal data in logs/artifacts. Limit file uploads, log size and artifact reads; require auth for artifacts.
- All mutations audited. Never trust frontend disabled buttons for security.

## 15. Backend development order (AFTER frontend)
1. Adopt the frontend's frozen `contracts/` OpenAPI/TypeScript fixtures and resolve any differences explicitly.
2. Implement FastAPI app, Pydantic schemas, DB migrations, health, read endpoints and deterministic seed data.
3. Connect frontend real adapter; verify read-only routes and error states.
4. Implement Monitoring + incident ingestion/deduplication + Manager state machine.
5. Implement Code RAG + Diagnosis with evidence-backed/no-evidence fixtures.
6. Implement Repair + versioned patch + isolated Testing.
7. Implement approval enforcement + controlled apply/restore + verification.
8. Implement Reporting and audit/history; full end-to-end tests.

## 16. Required backend tests and acceptance
- Schema contract tests against frontend fixtures/OpenAPI.
- Idempotent incident ingestion and duplicate run protection.
- Unsupported failure yields manual review.
- RAG citations match exact revision; no-evidence abstention.
- Malformed diff/path traversal/symlink rejected.
- Failed/timeout test never enables approval.
- Reject leaves demo unchanged; stale candidate/hash/base returns 409.
- Approval does not bypass human identity/permissions.
- Approved candidate applied only to allowed demo; snapshot recorded.
- Failed verification restores safely or requests manual action.
- Every final report agrees with persisted history; no unrun test marked passed.
- One complete seeded demo: detect -> diagnose -> repair -> test -> approve -> apply -> verify -> report.

## 17. Instructions for Codex
Read this file AND `FRONTEND_SPECIFICATION.md` before changes. Frontend-first means **do not implement the backend yet** unless explicitly requested. Preserve schemas, route names, state names, approval safety and six-agent responsibilities. When implementing backend later, first compare existing frontend `src/contracts` and `src/api` to this document; avoid changing API shape without updating both sides and contract tests. Document every deviation in an ADR. Prototype scope only.

## Frontend contract handoff addendum (2026-11-17)
The frontend-only implementation freezes executable wire schemas in `frontend/src/contracts/schemas.ts` and endpoint mapping in `frontend/src/contracts/api-contract.md`. Before building FastAPI, review `frontend/docs/ADR-001-frontend-wire-projections.md`: it specifies embedded sanitized evidence/diff/report projections, pagination, a `search` list-query extension, and the cookie/CSRF transport convention. Preserve candidate/hash/base approval gates and separate Apply. No backend implementation has been added.

## Audit contract clarification (2026-11-17)
See `frontend/docs/ADR-002-audit-contract-clarifications.md`. GET `/incidents` adds optional `scope=all|open|closed|candidates|pending` and `sort=detected_desc|detected_asc|severity_desc`; filter/sort before pagination and return opaque cursors. Existing envelopes, required fields and workflow statuses are unchanged. UTC timestamps are runtime-validated; approval/apply must independently recheck nonempty passing checks, exact candidate/hash/base and current workspace revision. The audited frontend freezes confirmation evidence and includes `inc_007` for simulated failed verification and restoration. No backend is implemented.
