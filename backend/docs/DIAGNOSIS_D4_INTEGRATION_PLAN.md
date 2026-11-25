# Diagnosis D4 integration plan

Prepared 2026-11-24 on `Diagno-Agent`. Status: ready for joint contract review;
**not approved for runtime registration**. This document proposes changes; it
does not implement Manager orchestration, Repair, Testing, database migrations,
or a second operational database.

Current update (2026-11-25): the D4B request relays Delvin's agreement in principle
on Manager-owned async persistence/workflows/retries/cancellation, Diagnosis-owned
retrieval/evidence/reasoning, isolated workers, an overall 120-second stage budget,
default 30-second LLM timeout and at most one Manager-owned transient retry within
that budget. Schema, migration strategy and concrete repository mappings remain
pending joint approval. Earlier all-pending statements below are the D4A review
history; see the D4B section and verification report for the current boundary.

## Verified baseline and inspection

D3 is committed as `e2600aa6a267a4415cdbb449921096640df6f4b5`, with the requested
message `feat(diagnosis): add D3 evidence validation and manager wire adapter`.
All 14 intended D3 files were reviewed and staged explicitly. The full backend
suite passed **273 tests in 126.71 seconds**, including 25 D3 and 39 D2 cases.
Ruff lint and formatting passed. The commit was pushed only to
`origin/Diagno-Agent`; a subsequent remote query returned that exact SHA.

Manager was inspected using `git fetch --no-tags origin manager-backend` and
`git show`, without checkout, merge, imports, server startup or execution of its
agents. Its inspected and remote-verified tip remains
`b74f09aad6c649a44d3efbfdc301c65e5a3b0631`. Local and remote `main` remain
`2eae39468f34a694f39b110d4aef6caff8b591a1`.

Primary evidence is pinned to that Manager commit:

- [Agent protocol and registry](https://github.com/sahadhaneef/Sentinal-AI/blob/b74f09aad6c649a44d3efbfdc301c65e5a3b0631/backend/app/agents/registry.py)
- [Diagnosis stage, persistence and state transitions](https://github.com/sahadhaneef/Sentinal-AI/blob/b74f09aad6c649a44d3efbfdc301c65e5a3b0631/backend/app/services/manager.py)
- [Async dispatcher](https://github.com/sahadhaneef/Sentinal-AI/blob/b74f09aad6c649a44d3efbfdc301c65e5a3b0631/backend/app/workers/dispatcher.py)
- [Database models](https://github.com/sahadhaneef/Sentinal-AI/blob/b74f09aad6c649a44d3efbfdc301c65e5a3b0631/backend/app/db/models.py)
- [Session factory](https://github.com/sahadhaneef/Sentinal-AI/blob/b74f09aad6c649a44d3efbfdc301c65e5a3b0631/backend/app/db/session.py)
- [Documented handoff](https://github.com/sahadhaneef/Sentinal-AI/blob/b74f09aad6c649a44d3efbfdc301c65e5a3b0631/backend/AGENT_INTEGRATION.md)

Diagnosis evidence: the existing `reasoning/contracts.py`, `reasoning/repository.py`,
`reasoning/service.py`, `quality/manager_adapter.py`, `quality/service.py`,
`quality/recording.py`, D1 source/artifact repositories and D0–D3 reports. Existing
frontend edits, databases and protected files were preserved. The D4 plan is a
separate local document, excluded from the D3 commit.

## Actual wire compatibility

### Contract review status and exact fields

No shared contract decisions have been confirmed by Delvin in this chat. The
following are observed compatible shapes, **not an approved integration agreement**.
The Manager tip was refreshed read-only on 2026-11-24 and still equals `b74f09a`.

| Boundary | Required fields | Optional/default fields and restrictions |
| --- | --- | --- |
| Manager input | `incident_id`, `run_id`, `repository_revision`, `extra.application_id` | Manager's dataclass defaults `extra` to `{}`, but Diagnosis requires its application ID; IDs use the existing <=64-character portable identifier contract |
| Error context inside extra | None | `source_log=""` <=16000 characters, `error_type=""` <=200, `error_message=""` <=2000; optional `stack_trace_ref` is an existing incident-linked artifact identifier, not a filesystem path |
| Revision | Portable token <=128 characters | D3 rejects HEAD/main/master/latest; other branch names cannot be distinguished from opaque revision IDs by syntax. Authoritative registration and snapshot custody remain required |
| Manager output | `success`, `data`, `error`, `duration_ms` | Existing DTO defaults data to `{}` and error to null; nonnegative elapsed milliseconds. No retryable flag, new status, schema version or provenance field is added to this envelope |
| Success data | `status`, `hypothesis`, `confidence_label`, `uncertainty`, `suggested_direction`, `evidence` | Exact existing public projection; incident/run IDs stay in Manager input context; internal hypotheses, facts, outcome and provider metadata are not inserted into data |
| Evidence entry | `file_path`, `symbol`, `start_line`, `end_line`, `repository_revision`, `artifact_id`, `excerpt` | Inclusive positive line range; real scoped artifact reference. Consumer-created placeholder references do not establish source integrity |

Unknown input/extra fields are rejected rather than silently accepted. The
existing Diagnosis text validator redacts known secret patterns and rejects
unsupported control characters; this does not establish a comprehensive shared
log-sanitization policy. Manager currently supplies inline logs and does not pass
`stack_trace_ref`. No new request fields are proposed in code.

| Aspect | Manager today | Diagnosis today | Smallest proposed adjustment |
| --- | --- | --- | --- |
| Invocation | async `execute(AgentInput)` | synchronous `QualityDiagnosisService.diagnose` | Add an async wrapper only after agreeing on worker/session/cancellation ownership |
| Input | incident_id, run_id, repository_revision, extra dict | Required incident_id, run_id, application_id, exact revision; internal schema_version=1.0 | Keep the envelope; require extra.application_id explicitly and document version negotiation |
| Error context | Stage passes source_log, error_type, error_message, application_id in extra | Adapter maps source_log to stack_trace; stored incident observations are authoritative | Keep field names; supply one agreed sanitized log selection and reject conflicting observations |
| Artifact input | Current diagnosis stage supplies inline source_log | Optional stack_trace_ref is supported and incident-linked | Agree on artifact-first or explicit inline fallback; do not silently concatenate unrelated logs |
| Output | AgentOutput(success, data, error string, duration_ms) | Pure to_manager maps common Diagnosis fields, validated evidence and safe failure codes | Reuse the mapper; convert its DTO into Manager's own AgentOutput at the final boundary |
| Normal result | data.status=completed | Completed reasoning, with hypotheses and uncertainty | Preserve completed as stage completion, not confirmation of cause or recovery |
| Review result | success=true with data.status=manual_review pauses workflow | Quality/sufficiency reviews map to this form | Preserve review as a valid outcome, not a repair-ready result |
| Technical failure | success=false, records execution error, transitions to manual_review | Infrastructure/context failures produce sanitized error codes | Agree which codes are retryable; keep raw exceptions/logs out of AgentOutput.error |
| Evidence | Manager normalizes seven public fields into evidence_json | Mapper supplies file_path, symbol, inclusive lines, revision, actual artifact_id and excerpt | Reject missing/unverifiable references instead of using consumer-created placeholder IDs/excerpts |
| Extra provenance | Stage currently discards additional citation/ranking metadata | D3 returns query hash, embedding profile, snapshots, hashes, ranks and review codes | Persist a metadata-only provenance artifact or agreed audit payload, keeping the public response shape |

The existing adapter is **wire mapping only**. It neither registers an agent nor
makes the two ORM/session layouts compatible. Manager's alias support for
root_cause/suggested_fix/affected_files is unnecessary: Diagnosis keeps the
existing hypothesis/suggested_direction/evidence names.

## Six approval gates (D4A review snapshot)

At D4A review all gates were **pending agreement**. The D4B direction above
supersedes ownership/deadline/retry proposals, but does not approve concrete
database fields or migrations. Recommendations below retain their review history.

| Gate | Observed incompatibility | Proposed decision and owners | Acceptance evidence before registration |
| --- | --- | --- | --- |
| 1. Revision custody | Manager Application/Incident default to HEAD and pass the incident revision; D1 requires a registered immutable revision/manifest, but opaque revision tokens are not Git attestation | Delvin owns capture/registration and source access policy; Sahad consumes the exact binding. Resolve moving refs before a run and bind an immutable snapshot plus digest to the run | Wrong revision, changed/deleted source and late worktree edits cannot change existing citations or start reasoning under a different revision |
| 2. Logs | Manager stores inline Incident.source_log; Diagnosis reads incident-linked redacted artifacts or explicit inline traces. Its current fallback selects a bounded deterministic linked log, not an agreed production selector | Delvin and Sahad agree on one event/log reference, sanitization owner, maximum size and fallback rules. Prefer an explicit incident-linked redacted artifact ID plus hash; do not assume CORS or a redacted flag proves content is safe | Foreign-incident refs, conflicting inline/artifact content, credentials, malformed/oversized logs and multiple linked events yield deterministic review outcomes |
| 3. Persistence | Manager creates Diagnosis, AgentExecution and transitions. Diagnosis defaults read-only; its optional recorder writes this branch's AuditEvent, whereas Manager uses IncidentEvent | Manager is the sole owner of final diagnosis/execution/workflow commits. Agree on an audit/provenance sink; leave OutcomeRecorder disabled in the integrated worker until then | One invocation yields one accepted result/execution; failures roll back; review evidence/provenance survives restart without duplicate records |
| 4. Cancellation/timeouts | Manager wraps execute with wait_for, default120 seconds; Diagnosis is synchronous with a default 30-second HTTP socket timeout and no retry | Delvin owns the overall monotonic deadline and cancellation token; Sahad honors the remaining budget. Choose a bounded worker or compatible async transport. Do not run blocking inference on the event loop or pass an AsyncSession across threads | Cancellation during retrieval/inference cannot persist a late result or advance the workflow; worker resources remain bounded; network timeout is distinguished from invalid evidence |
| 5. Status/error semantics | Manager treats success=false as an execution error and manual review; success=true/manual_review persists a review diagnosis. Its normal path records execution completed even for review | Agree on the code-to-outcome matrix below, retry eligibility and execution status semantics without adding workflow states silently | Completed, insufficient evidence, contradiction, model-requested review, provider outage, malformed response, invalid context and cancellation each have asserted state transitions |
| 6. Database/session approach | Manager uses AsyncSession, incident_runs, inline source_log, evidence_json and CodeIndexEntry.index_ref. Diagnosis uses Engine/Store, workflow_runs, registered revisions, artifact_id/index_metadata and normalized evidence references | Choose one canonical shared operational database/model set jointly. Recommended first step is small repository interfaces over the agreed model, not copying incident/run rows into another database. Any required additive migration is a separately reviewed shared change | Context, revisions and artifact citations resolve from the same authoritative records; existing data and API behavior survive an upgrade without resets or shadow copies |

## Persistence details that prevent direct registration

Manager already has Artifact and CodeIndexEntry models, but their fields differ.
Artifact includes inline `content`; CodeIndexEntry has `index_ref` instead of
this branch's `artifact_id`/`index_metadata`. The inspected Manager model module
has no equivalent normalized RepositoryRevision/ApplicationRevision or
EvidenceReference definitions. Matching table names do not make the schemas
interchangeable. Do not point this branch's migrations/metadata at that database.

Minimal proposed approach after gate 6 approval:

1. Agree on the canonical application, run, revision/snapshot and artifact records
   and their identifiers. Keep one source of truth for operational state.
2. Introduce narrow injected context/source/evidence repository interfaces within
   Diagnosis, keeping ingestion, chunking, embedding and quality rules reusable.
   Map through the agreed shared repositories; do not mirror Manager's data into
   this branch's database just to satisfy current constructors.
3. Determine whether revision/source manifest metadata can be represented safely
   by existing shared artifacts, including scope and hash enforcement. If not,
   agree on a minimal additive migration before implementing it. No migration or
   schema reconciliation is performed in this task.
4. Preserve hashes and real artifact identity across the handoff. Manager's
   evidence normalizer currently defaults missing IDs to art_code_<incident> and
   missing excerpts to descriptive text. Propose replacing those fallbacks with
   fail-closed validation for real Diagnosis outputs; Delvin owns that change.
5. Reuse an agreed existing output_artifact_id/audit hook for metadata-only D3
   provenance. The current diagnosis stage does not supply output_artifact_id to
   its execution recorder. Do not add a second competing diagnosis/audit writer.

D1's existing vector cache is derived retrieval data, not a second authoritative
incident/run database. Agree on its location, rebuild behavior and retention;
do not create another operational database or an unapproved synchronization job.
Do not copy the real SQLite database, credentials or model weights into Git.

## Lifecycle and error proposal

Keep existing public statuses. The following mapping needs Delvin's confirmation:

| Outcome | Agent envelope | Manager behavior |
| --- | --- | --- |
| Source-supported hypothesis with adequate evidence | success=true, status=completed | Persist the hypothesis and real evidence, then use the existing next-stage transition |
| Insufficient/conflicting evidence, unsupported language, model-requested review | success=true, status=manual_review | Persist a review outcome and reason; do not enter patch generation |
| Provider unavailable/socket timeout or invalid incident/run scope | success=false, safe error code | Record a technical/context failure and pause for review; any retry is explicit and bounded |
| Invalid model JSON/citations or unsupported execution claims | Current mapper returns a completed invocation with a manual-review data result | Confirm whether to retain this policy or classify selected cases as technical errors; never advance to repair |
| Manager deadline or cancellation | No accepted late result | Manager owns cancellation/status persistence and discards output if the invocation is no longer active |

asyncio cancellation of a thread wrapper does not stop its synchronous native
inference automatically. Agree on worker lifetime and late-result rejection,
not just a larger wait_for timeout. Disable persistence inside the worker; after
it returns, Manager must recheck active run, exact revision, invocation identity,
deadline/cancellation and evidence integrity before committing. Do not hold an
operational database transaction across network inference.

Agree on idempotency for (run, diagnosis stage, exact revision, invocation/attempt).
Do not assume an input parameter or an in-memory task map makes repeated stage
calls idempotent. Reuse existing shared idempotency support if suitable; any new
constraint requires an approved migration. Diagnosis must not retry by creating
new workflow runs or silently choosing a newer source revision.

## Isolated D4 adapter preparation (local review work)

Only Diagnosis-owned files changed; no shared schema, route, registry, Manager
code, session factory or workflow is modified.

- `quality/manager_adapter.py` retains D3 function signatures and wire fields.
  Before projection it revalidates mutable DTOs, checks result/provenance scope,
  rejects duplicate or missing evidence, compares returned citation metadata with
  D3 provenance and verified IDs, validates portable references/digest syntax,
  checks line ranges and hypothesis/fact references, and rejects contradictory
  completion/review envelopes. These are structural handoff checks; they do not
  reread source bytes or replace D1/D3 source resolution and its trust boundary.
- `quality/manager_invocation.py` adds an unregistered internal test seam accepting
  an explicitly async callback. It validates input, copies the request to protect
  correlation, checks returned incident/run/application/revision, measures duration,
  and projects through the existing mapper. Raw callback exceptions and validation
  details are replaced with fixed safe exception messages. It creates no tasks,
  workers, retries, records, sessions or transitions.
- Cooperative `CancelledError` propagates. A callback returning after suppressing
  cancellation is rejected while the task's cancellation request remains pending.
  The caller owns deadlines. This does not preempt native/synchronous inference,
  prevent a callback from blocking the event loop, or replace Manager's final
  active-run/attempt/deadline check. The existing synchronous service is explicitly
  rejected by this async seam; a production worker remains an unresolved gate.
- Existing `LLM_UNAVAILABLE` mapping is preserved. That code covers disabled
  providers and other failures as well as potentially transient outages. It cannot
  safely be declared universally retryable. No automatic retry or new classification
  is implemented until owners agree on error taxonomy and bounded retry policy.
- `tests/diagnosis/quality/test_manager_integration.py` uses the actual inspected
  dataclass shape and async mocks plus existing isolated D1/D2/D3 fixtures. It tests
  translation, missing/invalid revisions, insufficient evidence, provider failures,
  scope mismatches, citation tampering, cancellation, caller timeout, sanitized
  exceptions, unchanged source bytes and unchanged diagnosis/audit/run row counts.
  It does not execute Manager or prove shared-database/runtime integration.

This seam returns the existing Diagnosis-owned `ManagerOutcome`, not an imported
Manager `AgentOutput` instance. Final conversion/registration belongs to the approved
runtime boundary. Result provenance remains internal and no optional audit recorder
is enabled automatically. Source integrity must be checked again at an agreed final
acceptance boundary if storage can change between reasoning and persistence.

## Proposed D4 implementation order after agreement

1. Record decisions and a pinned Manager/Diagnosis contract version for all six
   gates. Name the persistence, artifact and cancellation owners.
2. Implement the agreed repository ports and fixture-backed shared-context tests
   on the authorized branch. Retain current public Diagnosis DTO projection.
3. Connect the isolated async seam to the agreed bounded worker/session approach
   with no source writes, worker-side persistence or registry side effects. Verify
   real cancellation and late-result guards beyond cooperative mock callbacks.
4. Exercise one integration fixture through actual agreed context/evidence stores,
   pure wire mapping, reasoning and Manager-owned persistence. Verify rollback,
   duplicate invocation, restart, wrong revision and review transitions.
5. Run real local-model evaluation and inspect findings individually. Confirm
   citations, relevance, uncertainty and unsupported claims rather than inventing
   an accuracy percentage from lexical checks.
6. Only after approval, let Delvin register the real agent in the shared registry.
   Re-run backend/frontend contract checks with protected application files hashed
   before/after. No Repair/Testing implementation belongs to this work.

## Live LLM readiness and exact setup

Most recent readiness check (the preceding D3 publication/D4 planning task):
no Ollama executable on PATH or in standard install
locations, local `/api/tags` inaccessible, provider disabled and model unset.
Live inference has **not passed**; this adapter task does not claim a new live-model
evaluation. Synthetic HTTP tests and deterministic reasoning
coverage do not establish real-model diagnostic accuracy.

Install `OllamaSetup.exe` from the [official Windows download](https://ollama.com/download/windows),
then open a new terminal. The [Windows instructions](https://docs.ollama.com/windows)
describe the native background service. Use `ollama serve` in a separate terminal
only if the tray application is not already serving the local API. CLI commands
are documented in the [official reference](https://docs.ollama.com/cli).

```powershell
cd 'D:\projects\SENTINAL AI\backend'
ollama --version
ollama ls
$env:SENTINEL_DIAGNOSIS_MODEL = Read-Host 'Enter the exact local model tag to evaluate'
# Only if that chosen model is not installed, explicitly download it:
# ollama pull $env:SENTINEL_DIAGNOSIS_MODEL
$env:SENTINEL_DIAGNOSIS_PROVIDER = 'ollama'
$env:SENTINEL_DIAGNOSIS_BASE_URL = 'http://127.0.0.1:11434'
$env:SENTINEL_DIAGNOSIS_ALLOW_TEST_FALLBACK = 'false'
Invoke-RestMethod 'http://127.0.0.1:11434/api/tags'
& '.venv/Scripts/python.exe' -m app.agents.diagnosis.quality.evaluate
if ($LASTEXITCODE -ne 0) { throw 'Live evaluation did not complete; inspect the reported reason' }
```

Use process variables rather than adding Diagnosis keys to the strict shared
dotenv. The evaluator requires the exact installed model tag shown by /api/tags;
no new model is hardcoded in the architecture. Its existing D1 dependency/weights
setup is documented in `DIAGNOSIS_D1_VERIFICATION.md`; `uv sync` alone does not
install the optional semantic encoder lock. The evaluator uses disposable fixture
storage, not the real application database. Keep generated reports and weights
outside Git. A completed call still requires human review of per-case results;
it is not a guarantee of causal correctness.

## Readiness conclusion

### D4 validation performed on 2026-11-24

Commands ran from `backend/` with `.venv/Scripts/python.exe` (Python 3.12.16):

| Check | Actual final result |
| --- | --- |
| `python -m ruff check .` | Passed; no lint suppressions added |
| `python -m ruff format --check .` | Passed; 140 files already formatted |
| `python -m pytest` | **303 passed in 124.74 seconds**, no failures or skips |
| D4 Manager-compatible adapter cases | **30 passed** within that full run |
| Existing D2/D3 and regression coverage | All retained and passing within that full run, including API/frontend, database/migration and HTTP transport checks |

An earlier full run passed 300 tests before the last three new cases were
collected. The additional focused run initially exposed an incorrect new test
assumption: editing the live worktree should not invalidate an already sealed
snapshot. That test now asserts the intended invariant: citations keep the exact
sealed source and Diagnosis leaves the later worktree edits untouched. No existing
test was weakened and no implementation was changed to accommodate that expectation.

Preservation verification compared SHA-256 hashes for 384 pre-existing files.
Only the intended adapter and this pre-existing local plan changed; the two new
Python files are the invocation helper and D4 tests. All seven dirty frontend
files, the real database and other protected files remain unchanged. A local dirty
work archive and integrity-checked SQLite backup remain ignored under
`.tools/branch-safety/`. No database reset or shared migration occurred.

Branch remains `Diagno-Agent`, tracking `origin/Diagno-Agent` with HEAD
`e2600aa6a267a4415cdbb449921096640df6f4b5`. No D4 files are staged, committed
or pushed. Remote reference verification returned that same Diagnosis SHA,
`main=2eae39468f34a694f39b110d4aef6caff8b591a1` and
`manager-backend=b74f09aad6c649a44d3efbfdc301c65e5a3b0631`; local main is
unchanged. Manager inspection used fetch/show only, without executing or modifying
its code. Mock/cooperative invocation tests do not establish real Manager runtime,
shared persistence, native worker cancellation or live LLM readiness.

D3 is published. D4 isolated adapter preparation is local and uncommitted;
**contract discussion and review can start now**. Runtime integration/registration is **not ready**
until the six gates are agreed, canonical storage/session wiring is reconciled,
and a real configured model is evaluated. Delvin must confirm the six ownership
decisions, replace evidence placeholder fallbacks, specify final acceptance and
idempotency rules, and select the canonical database/session approach before
registration. This task changes no shared schema, registry, agent lifecycle or
application source. No D4 commit or push is performed without explicit review.

## D4A publication finalization — 2026-11-24

The subsequent D4A finalization request explicitly authorizes publishing the
reviewed adapter, async helper, 30 tests, this plan and the new
`DIAGNOSIS_MANAGER_HANDOFF.md`. Earlier local/uncommitted statements above describe
the original preparation handoff and are superseded by this publication review.
This authorization does not approve any shared runtime contract or registration.

Fresh final validation: Ruff lint passed, Ruff format check passed (142 files),
and **303 tests passed in 84.21 seconds**, with no failures or skips. The full run
includes the 30 D4 cases and existing API, browser, HTTP, database and migration
regressions. The focused browser/HTTP regression command also passed **5 tests in
50.98 seconds**. No test, timeout limit, production implementation or lint setting
was changed during finalization.

Three preceding full runs each passed 302 tests and failed one existing timing
check: empty-dashboard navigation at 10 seconds (172.26-second run), HTTP server
readiness at 15 seconds (234.14-second run), then empty-dashboard navigation again
(200.61-second run). Windows had approximately 2 GiB free RAM during investigation;
after the user freed memory, the unchanged complete suite passed. Resource pressure
is a plausible explanation, not a proven root cause. These intermittent timing
failures remain a regression-environment limitation and are not hidden or disabled.

The five intended publication paths were reviewed, including a credential-pattern
scan with no hits. Existing frontend edits, real databases, environment files,
weights, caches, tooling and backups are excluded. A new 386-file preservation
manifest, dirty-work archive and integrity-checked SQLite backup remain ignored
under `.tools/branch-safety/`.

The Manager handoff distinguishes observed compatibility from all six pending
agreements and includes invocation examples and acceptance criteria. The separate
local D5 readiness report records actual hardware and provider checks, setup and
evaluation instructions; it is not part of this D4A implementation commit. Ollama
was not found at the inspected locations, the configured endpoint is unavailable,
and the live-only evaluator exited 2 with CONFIGURE_LOCAL_OLLAMA_MODEL. No model
download, live inference, Manager registration or cross-branch integration is
claimed. D4C remains blocked on team decisions; D5 live execution awaits setup
and explicit approval for any model download.

## D4B implementation — 2026-11-25

Implemented only the Diagnosis side of the direction supplied in the D4B request.
Read ports and standalone adapters preserve the persistent Code RAG index; a
spawn-per-invocation worker executes blocking native work outside the event loop,
with bounded concurrency/queue, checkpoints, deadline supervision, forced-stop
fallback and full typed results. Classification is internal and no retries are
performed by Diagnosis. Operational database access in the standalone worker is
query-only; optional audit recording is disabled.

Manager's latest inspected commit is still
`b74f09aad6c649a44d3efbfdc301c65e5a3b0631`. Its initial Alembic revision is empty,
and its next revision creates idempotency_records; this is not equivalent to this
branch's explicit 0002_domain migration. Do not run or stamp either migration
history onto the other's operational database. No shared migration changed.

The exact model differences, smallest proposed canonical-database reconciliation,
interfaces, execution trade-offs, actual checks and remaining acceptance work are
in `DIAGNOSIS_D4B_VERIFICATION.md`. Manager code remains read-only and unregistered.
D4B is local and must undergo explicit review before any commit/push. The separate
D5 readiness report is preserved byte-for-byte and is not bundled into this work.
