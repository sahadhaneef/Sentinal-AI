# D4B repository boundaries and isolated execution

Date: 2026-11-25. Branch: `Diagno-Agent`. Starting HEAD:
`67d89d1e7bb7b4d3524fc7d6d54cf99efe6d6899`. D4B is local and uncommitted;
commit/push requires explicit review. No integration branch, Manager registration,
shared migration, operational database copy or other agent implementation is added.

## Decisions and limits of approval

The user's D4B request relays Delvin's agreement **in principle** on:

- Manager-owned async SQLAlchemy operational persistence, workflow state, execution
  records, cancellation and retries; Diagnosis owns retrieval, evidence and reasoning.
- Typed Diagnosis results without independent Manager workflow/audit persistence.
- Independently isolated blocking work, an overall 120-second stage deadline,
  default 30-second configurable LLM timeout, cooperative cancellation and controlled
  worker termination when cooperation fails.
- At most one Manager-owned retry, only for explicitly transient failures and
  within the same overall execution deadline. Diagnosis performs no workflow retry.

This does not approve canonical tables, migrations, repository field mappings,
revision attestation, log-selection rules, provenance storage, attempt identity,
error-code mapping or runtime registration. Those remain joint integration work.

## Read-only Manager/database review

Refreshed `origin/manager-backend` and inspected commit
`b74f09aad6c649a44d3efbfdc301c65e5a3b0631` using fetch/show, without checkout,
execution or modification. Sources: `app/db/models.py`, `app/db/session.py`,
`app/agents/registry.py`, `app/services/manager.py`, `alembic/env.py` and both
Manager migration files. Diagnosis sources include existing models, Alembic
revisions, Store/transaction, context/source/evidence/cache repositories and D0–D4A
reports. The local D5 report is preserved, not bundled into D4B.

| Area | Manager inspected implementation | Diagnosis standalone implementation | Minimum reconciliation still needed |
| --- | --- | --- | --- |
| Sessions | AsyncSession/async_sessionmaker, expire_on_commit=false | Synchronous Engine/Store with short transaction contexts and detached values | Select canonical async repositories; worker receives serializable data/configuration, never Manager's live sessions/connections |
| Workflow/run IDs | IncidentRun/incident_runs; Incident.active_run_id | WorkflowRun/workflow_runs with incident/application/revision linkage | Agree the authoritative run identity and execution admission mapping; do not copy runs between tables |
| Applications/incidents | Application and Incident revision defaults HEAD; Incident.source_log inline | Registered RepositoryRevision/ApplicationRevision and linked monitoring event/log artifacts | Bind an immutable revision/snapshot and agreed selected log before execution |
| Source/index | CodeIndexEntry.index_ref; no equivalent normalized revision records found | Scoped CodeIndexEntry.artifact_id/index_metadata, manifest/full-file/excerpt hashes and derived vector cache | Map exact immutable source/evidence custody through approved repositories; retain persistent retrieval data |
| Artifacts/evidence | Artifact inline content, Diagnosis.evidence_json | Validated filesystem artifact metadata, normalized EvidenceReference | Agree safe artifact resolution and provenance retention; remove synthesized missing-ID/excerpt fallbacks for actual outputs |
| Results/audit | Manager creates Diagnosis, AgentExecution, IncidentEvent and lifecycle transitions | D2/D3 return data; optional AuditEvent recorder only if explicitly invoked | Manager owns final atomic writes; integrated execution never enables optional recorder |
| Migrations | 2dbc2c39ef2d initial upgrade/downgrade are no-ops; edb3328a710f adds only idempotency_records | 0001_foundation then explicit 0002_domain with constrained domain tables | Different histories and models cannot be interchanged; jointly approve a canonical upgrade/data-preservation plan |

Manager's Alembic env points at its metadata but does not make its empty initial
migration create the domain schema. This is a static finding, not a claim that
Manager's database was migrated or tested. No Manager migrations ran against any
Diagnosis database. No migration was edited or stamped.

Smallest proposed canonical-storage work: (1) agree the authoritative existing
models/IDs; (2) implement approved read ports over those records without mirrored
incident/run data; (3) represent immutable revision/source/provenance metadata in
approved artifact/record fields, with a separately reviewed additive migration
only if required; (4) let Manager own the single diagnosis/execution transaction,
idempotency, final active-attempt/cancellation checks, rollback and restart tests.
Current Manager code reads/transitions before awaiting the agent and commits
afterward; Delvin must review transaction lifetime so no operational transaction
remains open across inference. Diagnosis context/artifact/cache transactions close
before reasoning.

## Repository abstraction

`app/agents/diagnosis/repositories.py` defines ORM-independent typed read ports:

| Boundary | Interface / standalone implementation |
| --- | --- |
| Incident observations, exact run scope, selected linked redacted log | ContextReader.load -> immutable IncidentContext; existing DiagnosisContextRepository, injected through D2/D3 constructors |
| Registered revision | RevisionReader.revision -> immutable RegisteredRevision; existing SourceCatalog now returns that detached value rather than an ORM object |
| Source permission/run linkage | SourceReader.context/bind; existing SourceCatalog |
| Immutable snapshot, actual file/excerpt hashes and citation resolution | SnapshotReader.resolve; existing EvidenceStore authoritative resolver |
| Scoped redacted log artifact | LogReader.stack_log; existing EvidenceStore and ArtifactReader |
| Snapshot/citation plus log access | EvidenceReader combines those two existing responsibilities |
| Persistent code-index collection/vectors | CodeIndexReader; StandaloneIndexReader projects existing VectorCache rows into IndexedSnapshot values |

Incident/run/log selection stays one atomic context read so splitting lookups
cannot accidentally remove linkage checks. Execution admission/cancellation state
remains Manager-owned; no invented AgentExecution lookup contract is introduced.
Snapshot resolution likewise verifies manifest, source, excerpt, hash and line
range together. Dynamic resolved metadata retains the existing dictionary contract
and is validated by D1/D2/D3 evidence DTOs and resolver checks.

RetrievalRepositories injects source/evidence/index readers into CodeRag. The
existing persistent index writer, reserve/publish behavior, cache identity and
standalone indexing API remain intact. QualityRag carries the injected readers
and execution control forward; no second retrieval implementation is created.
Final Manager-backed repositories await field/schema approval. These ports do
not magically convert AsyncSession to Engine or reconcile incompatible schemas.

## Worker architecture and Windows lifecycle

`execution/worker.py` implements a bounded controller using Python 3.12
`multiprocessing.get_context("spawn")`, with a module-level child entry point.
Default concurrency 1, hard configuration ceiling 2; pending invocations default 4,
maximum 16. Use **one controller per event loop/application lifespan** and close it
with `aclose()` or async context management. Independent controllers/processes
need an application-level aggregate admission limit; this library is not a global
multi-server scheduler.

Each invocation gets a fresh child process. Parent-side supervision runs in a
bounded-per-controller executor thread; actual FastEmbed, repository reads,
retrieval and synchronous reasoning run in the child, never on the event loop.
The supervisor thread is not a substitute thread-based inference worker.

Only validated JSON request/deadline data, trusted picklable initialization
configuration and a multiprocessing cancellation event cross the boundary.
StandaloneFactory contains validated local configuration JSON and excludes
operator credentials; it creates/disposes its own engine and service in the
child. It requires an existing file database and enables SQLite query_only for
operational connections. It never runs migrations, builds a replacement database,
indexes source automatically or enables OutcomeRecorder. Manager request fields
cannot select a Python factory/module or arbitrary database/source path.

The child writes a maximum 262144-byte typed outcome into a private temporary
result file. The parent reads it only after process exit, validates the complete
QualityResult, citations/provenance and incident/run/application/revision binding,
then rechecks the deadline on the event loop before accepting it. Reading after
exit avoids partial pipe-frame reads blocking cancellation supervision. Temporary
files are cleaned, exited children joined and handles closed. Spawn startup
failure, nonzero exit/crash, missing/oversized/malformed output and scope violations
fail closed without raw exceptions or source/log text in error strings.

Trade-off: fresh processes provide reliable native-work isolation, connection
ownership and kill/reap semantics, with no persistent idle models or pool recovery
state. They pay Python/model initialization costs per invocation and lose warm
model reuse. A reusable pool could reduce cold cost but requires an approved
memory/lifecycle/recovery policy. No latency or memory benchmark for actual BGE+
Ollama worker execution is claimed from synthetic providers. On the previously
observed 16 GB machine, start with one worker; limit applies to each controller.

Python script entry points must use the normal `if __name__ == "__main__"` guard;
imports must not start processes. The library adds no FastAPI/Manager registration.

## Deadlines and cancellation

Manager supplies an **absolute system monotonic deadline**; the controller caps
it at now+120 seconds. Queue waiting, spawn, initialization, retrieval, reasoning,
validation and normal shutdown consume that same budget. Retrying with a newly
created 120-second budget is forbidden; Manager must carry the original deadline
into its single eligible retry. Wall-clock timestamps are not interchangeable
with this local-process monotonic contract; a future remote worker would need a
different approved budget transport.

ExecutionControl checkpoints run before initialization/context, revision checks,
retrieval, each bounded citation/member/vector/ranking operation, before/after LLM,
before evidence validation and before return. Cancellation/deadline control flow
inherits BaseException so broad Exception handlers in providers/retrieval cannot
silently turn it into a normal manual-review response. Socket timeout stays
configured 30 seconds by default, capped by the remaining stage budget. It is a
socket-operation timeout, not a claim that every server-side request is stopped
after exactly 30 seconds. The parent supervisor enforces overall stage expiry even
when synchronous native/network code does not return to a checkpoint.

On cancellation or expiry the supervisor signals cooperation, waits a configurable
grace (default 0.5 seconds), terminates if needed, then kills if necessary and reaps
the process. Slots are retained through cleanup, including repeated cancellation.
Cleanup can finish beyond the execution deadline; no late quality result is
accepted. OS process creation/termination and final reaping are not hard real-time
guarantees, and do not provide protection against an OS/process-host failure.
Caller cancellation propagates as asyncio.CancelledError after cleanup; it does
not fabricate a completed workflow result or persist cancellation state.

Killing a Python worker **does not cancel inference already running inside the
Ollama server**. Manager must still check the authoritative active run, invocation,
revision, cancellation and deadline immediately before its final commit.

## Error and retry classification

`execution/errors.py` adds internal FailureKind/ExecutionFailure. Retry eligibility
is derived from the kind and cannot be supplied as a boolean override.

| Internal classification | Eligibility |
| --- | --- |
| Explicit provider HTTP 429/500/502/503/504, temporary connection/DNS failures, provider timeout | Potentially eligible for Manager's one retry, only with remaining budget |
| Disabled provider, missing/model/configuration HTTP errors, redirect policy | No retry |
| Invalid request/context/revision/artifact, insufficient/conflicting evidence, invalid citation | No retry |
| Invalid provider JSON/schema/envelope or unknown provider failure | No retry |
| Cancellation, overall stage expiry, startup/crash/malformed process result, capacity rejection | No automatic retry |

Existing DiagnosisRequest 1.0, DiagnosisResult and public ManagerOutcome shapes are
unchanged. Existing LLM_UNAVAILABLE remains the public compatibility code while
the worker retains the more precise internal provider classification separately.
Rich QualityResult includes hypotheses/facts, source hashes, verified citations,
uncertainty/confidence, provider/fallback flags and retrieval provenance. Manager
must agree a provenance sink and process-only error-string mapping rather than
silently extending AgentOutput. See the updated Manager handoff for the mapping
and outstanding acceptance criteria. No Diagnosis workflow retry is implemented.

## Verification

Focused D4B tests passed **39 tests in 45.77 seconds** using real Windows spawn
processes and clearly named test-only encoder/reasoner factories. Cases cover
repository injection, existing scoped revisions/logs/citations, query-only domain
writes, JSON round trips, startup failure/crash, malformed responses, cooperative
retrieval/reasoning cancellation, forced termination, repeated cancellation,
event-loop heartbeat, queue expiry/capacity, 120-second cap without waiting 120
seconds, no automatic retry, parent-side late-result rejection, rich metadata and
source/row-count preservation. Small controlled deadlines are used for failure
tests. These are not actual Manager runtime or live LLM integration tests.

The final consistency regression requires retrieval, reasoning and quality checks
to share one ExecutionControl; mismatched explicit controls are rejected rather
than silently leaving inner operations outside the requested budget.

Final validation (Python 3.12.16, existing 100-character Ruff configuration):

| Command/check | Actual result |
| --- | --- |
| `python -m ruff check .` | Passed, no configuration changes or suppressions |
| `python -m ruff format --check .` | Passed;155 files already formatted |
| `python -m pytest` | **343 passed in 167.43 seconds**, no failures or skips |
| D4B cases within final full suite | **40 passed**, including real spawn lifecycle checks and the final control-consistency regression |
| Focused unchanged browser/HTTP regression command | **5 passed in 47.58 seconds** |
| Live Ollama availability probe | Command and standard user install absent, configured loopback endpoint unavailable, provider disabled/model unset; live inference unverified |

The preceding 342-test full run passed 341 and hit the existing 10-second persisted-
dashboard page.goto timeout (184.15 seconds total). The unchanged focused browser
checks passed, then the full suite passed after the consistency regression was
added. No existing test, timing limit, migration, frontend or shared API was
weakened. Early development also caught a missing Collection writer import; it
was restored, preserving standalone index publication rather than changing tests.

Preservation: a 388-file SHA-256 manifest, dirty-work archive and integrity-checked
SQLite backup were captured under ignored `.tools/branch-safety/d4b-ff85eb29/`.
Only the five intended existing Diagnosis Python files and the two integration
documents changed among those files. The real database, all seven frontend edits,
D0–D3 reports, shared models/migrations and the existing uncommitted D5 report
remain unchanged. New D4B Python/tests/report files are separate local source.

HEAD remains `67d89d1e7bb7b4d3524fc7d6d54cf99efe6d6899` on `Diagno-Agent`.
Nothing is staged, committed or pushed for D4B. Local and remote main remain
`2eae39468f34a694f39b110d4aef6caff8b591a1`; Manager remains at the inspected
`b74f09aad6c649a44d3efbfdc301c65e5a3b0631`. No branch merge, rebase, reset,
force push or combined integration branch occurred.

## Remaining acceptance work for Delvin / D4C

D4B is ready for review; **D4C runtime registration is not ready**. Jointly approve
the canonical database/migration and repository field mappings, revision/snapshot
custody, sanitized log selection, provenance/artifact retention, attempt identity,
deadline transport and safe error-string mappings. Then implement Manager-backed
ports and wire one bounded controller into the agreed lifespan/admission model.
Manager must own the final single transaction and late-result/idempotency checks.

Exercise actual Manager plus Diagnosis against the agreed stores: normal/review
results, invalid scope/citations, cancellation and forced stop, one eligible retry
within the original deadline, duplicate invocation, rollback and persistence after
restart. Isolated fixture tests do not replace this joint runtime evidence. Live
Ollama reasoning remains a separate unverified prerequisite for model-quality
claims; no installation, model download or accuracy metric was fabricated.

## D4B source inventory

Paths are relative to backend/. The separate pre-existing D5 report is excluded.

| Action | Paths |
| --- | --- |
| Added read ports/adapters | app/agents/diagnosis/repositories.py |
| Added isolated execution package | app/agents/diagnosis/execution/__init__.py, control.py, errors.py, standalone.py, worker.py |
| Added tests | tests/diagnosis/execution/__init__.py, conftest.py, helpers.py, test_errors.py, test_repositories.py, test_worker.py |
| Added verification | docs/DIAGNOSIS_D4B_VERIFICATION.md |
| Modified retrieval | app/agents/diagnosis/code_rag/catalog.py, service.py |
| Modified reasoning | app/agents/diagnosis/reasoning/providers.py, service.py |
| Modified quality gateway | app/agents/diagnosis/quality/service.py |
| Updated integration documents | docs/DIAGNOSIS_D4_INTEGRATION_PLAN.md, docs/DIAGNOSIS_MANAGER_HANDOFF.md |

Twenty intended Diagnosis-owned source/test/document files; no new dependency,
configuration file, shared table or migration is introduced.

## Publication review — 2026-11-25

The subsequent D4B finalization request explicitly authorizes committing and
pushing the 20 reviewed files with message
`feat(diagnosis): implement D4B repository abstraction and isolated workers`.
Earlier local/uncommitted statements describe the initial implementation review,
not a restriction on this separately authorized publication.

Fresh required checks passed: Ruff lint, Ruff formatting (155 files), and the
complete backend suite, **343 passed in 151.89 seconds**, with no failures/skips.
The 40 D4B cases and all existing browser/HTTP, migration, schema and API regression
checks are included in that successful run. No implementation or existing test
changed during publication review. Source hashes and workflow-write guards remain
asserted in the isolated worker tests. No actual Manager registration is inferred.

A new 401-file preservation manifest, dirty-work archive and integrity-checked
SQLite backup were captured under ignored `.tools/branch-safety/`. Only intended
D4B source, tests and these integration documents are commit candidates. Frontend
edits, real databases, credentials, environment files, weights, caches, generated
files and the separate existing D5 readiness report are excluded.

The new D5A check found an installed local Ollama executable and a responding API,
but an empty model inventory. Provider defaults remain disabled with no selected
model. Model download/evaluation approval was requested separately; no D5 outcome
is bundled into this D4B implementation commit. D4C shared-schema and runtime
acceptance decisions remain pending exactly as described above.
