# Phase 3 REST contract and local access policy

This document supersedes the historical Phase 0/1 implementation-status notes in
`FRONTEND_BACKEND_CONTRACT.md`. The existing TypeScript interfaces, HTTP adapter,
Zod schemas, field names and enums remain unchanged. OpenAPI is available at
`/api/v1/openapi.json`; JSON responses retain the schema 1.0 envelope.

## Implemented endpoints

All paths below start with `/api/v1`.

| Method | Paths | Result |
|---|---|---|
| GET | `/health` | Process health; no claim of active workers. |
| GET | `/applications`, `/applications/{id}` | Frozen Application array/detail. |
| POST | `/applications` | Operator-only configured workspace registration, 201. |
| GET | `/applications/{id}/metadata` | Application, observation status/time, revision metadata, worker availability false. |
| GET | `/incidents` | Exact filter/scope/sort contract and opaque pagination. |
| POST | `/incidents` | Operator-only normalized observation intake/deduplication, 200 for first receipt or exact replay. |
| GET | `/incidents/{id}` | Frozen IncidentDetail with nullable missing results and permission flags false. |
| GET | `/incidents/{id}/events` | Recorded audit events in occurrence/ID order. |
| GET | `/incidents/{id}/runs` | Recorded attempts and ordered transitions; no run dispatch. |
| GET | `/incidents/{id}/diagnosis` | Recorded diagnosis with validated source excerpts. |
| GET | `/incidents/{id}/patches`, `/patches/{id}` | Candidates in ascending version order, exact recorded diffs. |
| GET | `/patches/{id}/validation` | Latest candidate/hash-bound result and recorded checks. |
| GET | `/incidents/{id}/verification` | Latest candidate's recorded attempt/verification. |
| GET | `/agents`, `/agents/{type}` | Six definitions plus persisted status/history; never-run agents are idle. |
| GET | `/dashboard/summary` | Frozen summary with queried counts and recorded agent statuses. |
| GET | `/dashboard/overview` | Additive application count, severity counts, recent incident activity/outcomes and frozen summary. |
| GET | `/reports`, `/reports/{id}` | Stored reports, no generation. |
| GET | `/incidents/{id}/reports`, `/incidents/{id}/report` | Report history/latest. Missing latest report is 404. |
| GET | `/artifacts/{id}` | Metadata only: ID/kind/hash/media type/byte count/redacted flag. Never a storage path or raw file download. |
| GET | `/settings` | Stored safe settings, or explicitly documented configuration defaults 5 seconds/2 revisions when absent. No row is silently seeded. |

Compatibility guard endpoints return **501 NOT_IMPLEMENTED** without changing any
record: POST incident `decision`, `apply`, `runs`; POST application monitoring
`start`/`stop`; PATCH `/settings`. Their existence is not workflow capability.
No agents, patch generation, execution, approval/rejection, application or rollback
mutations are implemented.

## Deliberate contract decisions

- The current browser has no agreed login/bootstrap API. Reads are explicitly
  unauthenticated **local prototype reads**, not production authorization. Bind
  only to loopback. This is a documented exception to the blueprint's future
  authenticated-read policy. Do not expose this server publicly or store sensitive
  production records in it. Full user/session/role/CSRF enforcement remains Phase 4+
  work; no fake current-user or session cookie is issued.
- Operator writes require `Authorization: Bearer <configured token>` matching
  `SENTINEL_OPERATOR_TOKEN` in constant time. Absent configuration disables intake
  (403); absent credentials yield 401; wrong credentials or any browser Origin
  yield 403. This is a narrow operator capability, not per-user authentication.
  No JSON actor ID or cookie grants authority. CORS remains exact-origin only.
- `Application.status` has no `unknown` wire value. Unobserved applications expose
  `offline`; metadata explicitly says `not_observed`, last observation null, and
  monitoring worker unavailable. Persisted monitoring preferences do not imply a
  running log reader. No health or execution status is fabricated from registration.
- SQLAlchemy audit rows can predate a run. The required wire `run_id` is the empty
  string for these events; no fictional run ID is created. Histories retain actors,
  payload metadata and occurrence timestamps.
- Snapshot references in the frozen ApplicationAttempt projection are artifact
  IDs, not filesystem paths. Current application revision is selected through
  `application_revisions`; active run IDs derive from nonterminal persisted runs.
- Missing optional results in incident detail are null/empty; standalone missing
  result endpoints return 404. A new candidate never inherits an older candidate's
  validation. All decision/application flags remain false with an accurate reason.
- A passed validation summary with no complete zero-exit passed check set returns
  409 EVIDENCE_INCOMPLETE. Resolved incident/report claims require a recorded resolved
  attempt, after revision, passed verification and nonempty passed checks with
  readable integrity-checked evidence. Incomplete claims are refused, not rewritten
  into invented success.

## Registration and ingestion

Registration JSON is strictly `{ "workspace_key": "demo" }`. The operator's
`SENTINEL_PERMITTED_WORKSPACES` maps that key to a name, description, revision,
snapshot key and supported error types. The directory must already exist at
`SENTINEL_DEMO_ROOT/<key>` without symlink/junction ancestors. A real prepared
snapshot must already exist below `SENTINEL_ARTIFACT_ROOT` at its configured key.
No client path, remote URL, command, actor or arbitrary metadata is accepted.
Registration reads only the prepared snapshot to register its size/hash, creates
application/revision/selection/audit metadata atomically, and leaves monitoring
disabled. A duplicate workspace conflicts (409); it never resets the existing app.

Ingestion JSON is the normalized observation contract published in OpenAPI:
`application_id`, `repository_revision`, `source_event_id`, canonical SHA-256
`fingerprint`, `severity`, `error_type`, bounded `message`, aware `occurred_at`,
optional `log_artifact_id`, and `classification` (`supported` by default or
`unsupported`). The application must belong to a configured permitted workspace.
Supported errors must match its configured list; unsupported classifications
create manual-review incidents. Common credential-shaped text is redacted before
persistence, with no request body logging. This is not a general log redaction
certification; callers must normalize and sanitize observations.

Repeated source IDs with identical normalized evidence return the original
incident. Different source IDs sharing an open fingerprint link to that incident.
Conflicting reuse of a source ID or source revision raises 409 and rolls back.
Each newly linked event gets one persisted audit entry; replay does not duplicate
it. No run is started. Idempotency-Key receipt/replay infrastructure remains
deferred; ingestion's actual idempotency is its persisted source-event identity.

## Pagination and search

All frozen scopes and status/severity/application filters intersect **before**
pagination. Defaults remain limit 10, scope all, detected_desc. Severity sorts
critical/high/medium/low, then detection time descending, then ID ascending;
detected_asc reverses only time order. Search is a literal Unicode-case-insensitive
substring of the ID/error-type/message projection, including field boundaries;
percent and underscore are literal characters. A deterministic SQLite `casefold`
function is registered on each connection.

Cursors encode an anchor ID, normalized query digest, result snapshot digest and
15-minute expiry under a process-local HMAC key. Tokens are opaque to clients.
Invalid/tampered/expired tokens, changed filters/limit, changed matching result
sets or a server restart return 422 VALIDATION_ERROR. Restart from the first page;
no offset or page-number reinterpretation. Repeated/unknown query parameters are
rejected. For this small prototype the repository obtains the filtered ordered
snapshot before bounded page projection. Larger datasets should move snapshot
versioning and continuation boundaries into a scalable database query.

## Artifact and transaction boundaries

Projected log/excerpt/diff/check/error text comes only from recorded redacted
UTF-8 artifacts. Reads validate portable relative keys, ancestor symlinks/junctions,
root confinement, a configured 1 MiB default bound, byte count and SHA-256. Common
secret patterns cause a 403 rather than rewriting an exact hashed diff. Missing,
tampered, oversized or unreadable bytes return 503 ARTIFACT_UNAVAILABLE. Metadata
lookup does not assert a blob is currently downloadable. There is no artifact
upload, arbitrary download, repository scan or command execution route.

Keep storage operator-owned; path checks are not a hostile concurrent-filesystem
sandbox or multi-tenant artifact authorization service.

Routes validate DTOs and call injected services; read queries and intake writes
use repositories in one request-scoped unit of work. Function-scoped yield
dependencies commit before sending success and roll back any failure. Structured
404/409/422/503 errors omit SQL, private paths and traceback details. Runtime
startup never creates tables or migrates. No Phase 3 schema migration is needed.

The migration checker now compares SQLite unique definitions by their column sets
because some existing Phase 2 composite constraints share generated names. This
does not drop or rename any constraint; a regression test proves a genuinely
missing unique constraint still produces schema drift.
