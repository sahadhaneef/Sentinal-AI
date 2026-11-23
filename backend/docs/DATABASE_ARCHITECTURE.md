# Phase 2 database architecture

Phase 3 update: database-backed read APIs and explicit operator intake now use this architecture; see `PHASE_3_API.md`. The phase boundary statements below describe the original Phase 2 delivery. No agents or execution are implemented.

Implemented 2026-11-18. SQLite and SQLAlchemy 2 persist domain records; Alembic owns schema changes. This phase adds no domain HTTP routes, authentication service, agents, runner, patch application, or filesystem artifact access. The frontend contracts and mock mode remain unchanged.

## Storage conventions

All 28 tables use a stable string primary key, UUID v4 by default, plus schema version `1.0` and created/updated UTC timestamps. Short existing opaque identifiers remain representable for future imports; new records generate UUIDs. Aware Python timestamps are required, normalized to UTC for SQLite storage, and returned as aware UTC values. Raw SQL writers must also use UTC. SQLAlchemy updates maintain `updated_at`; there is no database trigger for out-of-band SQL updates.

Status enums store the frontend's string values, with SQL CHECK constraints and ORM validation. Repository revision/workspace tokens use a portable allowlist. Hashes use `sha256:` followed by 64 lowercase hex characters. Small JSON metadata is capped at 16 KiB through typed persistence; changed files contain 1–100 distinct validated relative paths. SQLite does not enforce VARCHAR lengths or typed JSON bounds by itself; explicit CHECK constraints enforce selected security and integrity bounds, while future request schemas must validate the complete wire payload.

Logs, source snapshots/excerpts, diffs, result output and reports belong in external artifacts. `artifacts` stores only a relative storage key, kind, media type, byte count, SHA-256 digest and redaction flag. Relative-key validation rejects absolute paths, drives, backslashes, traversal, secret paths and malformed segments. Registration does not read files or verify bytes: future artifact storage must enforce its root, symlink confinement, redaction, authorization and byte/hash verification. Metadata is not proof that a blob exists.

## Tables and relationships

| Tables | Purpose and relationships |
|---|---|
| `users`, `roles`, `user_roles` | Case-insensitive unique usernames; admin/developer/reviewer/viewer roles; unique membership pairs. Memberships cascade on parent deletion; referenced historical actors restrict user deletion. No passwords are seeded. |
| `auth_sessions` | Unique hashed token, user FK, expiry after creation and optional revocation. Session issuance, cookie handling and authorization are deferred. |
| `applications` | Unique validated workspace key, health state and monitoring settings. No arbitrary repository URL or filesystem path. |
| `repository_revisions` | Immutable revision token and snapshot artifact, unique within an application. |
| `application_revisions` | One current selection per application; composite FK prevents selecting another application's revision without circular FKs. |
| `artifacts` | Unique relative storage key and bounded, validated external artifact metadata. |
| `monitoring_events` | Unique `(application_id, source_event_id)`, fingerprint, source revision, classification and optional log artifact. |
| `incidents` | Application/revision-bound issue, initial source event, severity, status and timestamps. Partial unique index limits an application/fingerprint to one open incident. |
| `incident_monitoring_events` | Links repeated events to their incident. A monitoring event has at most one link; composite FKs require the same application and source revision. |
| `workflow_runs` | Incident attempt, source revision, lifecycle state and timing; unique attempt number, one nonterminal run per incident. |
| `stage_transitions` | Ordered append-only transition history; unique `(run_id, sequence)`, distinct from/to states and optional human actor. |
| `agent_executions` | One of six logical agent types, run/revision scope, status, timings and external output/error evidence. These are records, not running agents. |
| `code_index_entries` | Revision-bound source location, symbol, line range, content digest and source artifact; no embedded source snapshot. |
| `diagnoses` | One result per run, bounded explanation, uncertainty and confidence. |
| `evidence_references` | Diagnosis-to-code-location citations with composite FKs preventing cross-application/revision evidence. |
| `patch_candidates` | Immutable versioned candidate metadata: base revision, digest, external diff, changed paths and predecessor. Unique incident/version. A revision creates a new candidate ID. |
| `validation_results`, `validation_checks` | Exact candidate/hash-bound summary and named individual checks, exit codes, duration and output references. |
| `approval_decisions` | One immutable decision per candidate, human actor, exact hash/base revision, optional comment and validation binding. Approval requires a passed validation summary for that exact candidate/hash. Rejection needs no passed result. |
| `application_attempts` | Metadata for a future separately confirmed local attempt; exact approving decision, candidate, hash, before revision and snapshot required. No application behavior exists. |
| `verification_results`, `verification_checks` | Exact attempt/candidate-bound post-application observations and individual checks. |
| `incident_reports` | Versioned, terminal-outcome incident reports with external report artifact and bounded summary/limitations. |
| `audit_events` | Append-only scoped human/system/agent metadata with optional external details; run/incident/application must agree. Human events require a user. |
| `backend_settings` | Singleton record for bounded monitoring interval and candidate revision limit. |
| `idempotency_records` | Unique user/operation/key with request digest, status and external response reference. HTTP replay behavior is deferred. |

ORM relationships are explicit and read-only (`viewonly=True`). Writes supply foreign keys through repositories; reads can traverse relationships inside the transaction. This avoids accidental ORM cascade writes or deletion of history. Foreign keys use RESTRICT except role memberships. History is retained even after a user or application stops being active.

## Constraints and indexes

- Foreign keys are enabled on **every** SQLite connection, including migrations. Python 3.12 `autocommit=False` provides real transactional DDL; PRAGMA setup temporarily enables autocommit and restores it.
- Partial uniqueness on incidents excludes only `resolved`, `rejected`, `unresolved`, `reported`, matching the frontend's open-incident meaning. `manual_review` and `error` still require attention.
- Run terminal states additionally include `manual_review` and `error`. A partial unique incident index prevents duplicate active runs. A separate application index limits runs in `applying`/`verifying`/`restoring`. Application-attempt metadata similarly allows one applying/verifying attempt per application.
- These two application locks are per table; a future Manager transaction must coordinate the matching run and attempt. They are not a distributed execution lock or permission check.
- Composite candidate/validation/approval/application FKs prevent swapped hashes, base revisions, rejected decisions or mismatched candidates. A passed individual check requires an actual zero exit code.
- A future service must still require a nonempty complete passed check set, current source revision, valid role/session, legal state transition and separate confirmation. SQL constraints cannot establish those permissions or execute the workflow.
- Unique keys cover usernames, role names, sessions, workspace selections, revisions, source event IDs, candidate/report versions, checks, decisions and idempotency scope.
- Named lookup indexes cover application/status/detection time; application/fingerprint; incident event links; run/agent type; incident/candidate version; candidate validation creation; attempt verification creation; incident report generation; audit application/incident occurrence time; session user. Composite unique keys also serve their leading-column lookups. Exact definitions are frozen in `0002_domain_domain_persistence.py`.

## Repository and transaction architecture

Use `app.repositories.transaction(engine)` as the caller's unit of work:

```python
from app.models import User
from app.repositories import transaction

with transaction(engine) as store:
    user = store.users.add(User(username="reviewer", display_name="Reviewer"))
    # Commit occurs only when the entire block succeeds.
```

The store exposes typed application, incident and patch repositories plus `records(Model)` for the other tables. Generic CRUD has bounded pagination, validates lookup IDs, restricts mutable fields and refuses historical deletion. Specialized repositories remain selected through `records(Model)`. Candidate registration verifies diff kind/hash and sequential predecessor versions. Application selection checks scope. Direct session access is available for future service queries; trusted callers must not bypass these invariants.

`record_monitoring_event(MonitoringInput(...))` accepts sanitized, already-normalized data. SQLite atomic inserts with conflict targets deduplicate source IDs and open fingerprints. Exact replays return the original incident, including after closure. New events with the same open fingerprint link to the existing incident. A new event after closure can create a new incident. Reusing an event ID with changed evidence, or matching an active fingerprint across conflicting source revisions/errors, raises a conflict and rolls back. No run or agent is dispatched. Concurrent writers are tested with separate connections.

Transactions commit once, roll back on any exception and close the session. Constraint errors become sanitized `Conflict`; malformed bound values become `InvalidRecord`; SQLite busy/unavailable errors become `StorageUnavailable`; missing IDs produce `NotFound`; prohibited history changes produce `ImmutableRecord`. There is no hidden retry or partial commit. A future service can retry the **whole** transaction on temporary storage contention, subject to its idempotency policy. Exceptions must leave the block; callers should not swallow a flush error and continue using its failed session.

## Migration and recovery

From `backend/` with the locked environment installed:

```powershell
uv run alembic current
# Back up the existing database with SQLite's backup API before upgrading.
uv run alembic upgrade head
uv run alembic check
```

`0001_foundation` remains the empty baseline. Additive `0002_domain` creates 28 tables and their indexes/constraints; it neither deletes nor seeds existing data. Application startup never migrates or calls `create_all`. Backups and SQLite files stay ignored by Git. Stop writers before a schema change and retain a verified backup; future structural changes need new reviewed revisions. Autogeneration ignores unmanaged reflected tables rather than proposing their deletion; it still checks managed tables for schema drift.

An empty database can downgrade to `0001_foundation` and re-upgrade. The domain downgrade refuses **any populated domain table** before dropping anything; offline downgrade is also refused. A deliberate destructive reset is not provided. For populated rollback, stop writers and restore a verified backup under explicit operator control. Tests verify upgrade with unrelated preexisting data, transactional rollback on a table-name collision, empty reapplication, populated refusal, FK integrity and process-lifespan persistence.

## Frontend projections and six-agent integration

No existing Zod, API adapter, route or DTO was changed. HTTP schemas remain health/envelope only. Later serializers must project domain records into the frozen contract: current revision from `application_revisions`; active run from the run partial uniqueness rule; inline code/diff/result excerpts only through authorized artifact reads; validation/check collections from child rows; wire dates as UTC ISO-8601. Database rows must never be returned directly as public API responses.

| Future owner | Persistence integration |
|---|---|
| Manager | Transactional run/stage/execution metadata, audit events, decision gates and separately confirmed attempt records. |
| Monitoring | Normalized event registration and deduplicated incident linkage; no duplicate workflow dispatch. |
| Diagnosis | Revision-bound code locations, diagnosis and evidence references, external result artifact. |
| Repair | New immutable candidate version and diff artifact metadata; no edit to an approved candidate. |
| Testing | Candidate/hash-bound validation, per-check evidence, then exact-attempt verification records. |
| Reporting | Terminal outcome, immutable versioned report and audit metadata. |

No test fixture is live operational evidence. All synthetic graph records exist only in isolated temporary databases. Agent logic, provider access, artifact bytes, authentication/authorization, the legal transition service, command execution, local application and restoration remain future work.
