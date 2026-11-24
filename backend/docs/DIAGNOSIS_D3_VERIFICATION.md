# Diagnosis D3 — evidence validation and quality

Date: 2026-11-24. Working branch: `Diagno-Agent`.

## Git scope and preserved work

D2 was reviewed and published separately as
`349926ef367380bf2ca3c070a443a2b00f8de0d5`, message
`feat(diagnosis): implement D2 evidence-bound reasoning`. Its 11 files contain
only the existing D2 reasoning package, D2 tests, and updated D2 report. Remote
`origin/Diagno-Agent` was verified at that exact SHA after the push. D3 was excluded.

The original D2 baseline passed 248 tests in 116.15 seconds before publication.
Two preceding baseline attempts each had 247 passes and an existing 10-second
browser navigation timeout in different modes. The focused unchanged browser
suite passed four tests. No test was disabled, weakened or given longer timeouts.

D3 remains local and uncommitted for review. No existing D0/D1/D2 implementation,
shared model, migration, REST API, frontend or other agent implementation was
changed for D3. The current code is additive under Diagnosis ownership.

Read-only inspection fetched `origin/manager-backend` at
`b74f09aad6c649a44d3efbfdc301c65e5a3b0631`, without checkout or merge. That remote
branch stayed unchanged. Local and remote `main` remained
`2eae39468f34a694f39b110d4aef6caff8b591a1`.

## Live model status

No Ollama executable was found on PATH or in standard local install locations.
Diagnosis is configured with `provider=disabled`, no model, and the loopback
`/api/tags` endpoint is inaccessible. No installation/model download was attempted.
The exact operator setup instructions and official Windows/CLI references are in
`DIAGNOSIS_D2_VERIFICATION.md` under the 2026-11-24 publication review.

After installing/starting Ollama and selecting the exact installed local model,
from `D:\projects\SENTINAL AI\backend`:

```powershell
$env:SENTINEL_DIAGNOSIS_PROVIDER = 'ollama'
$env:SENTINEL_DIAGNOSIS_MODEL = Read-Host 'Enter the exact installed local model tag'
$env:SENTINEL_DIAGNOSIS_BASE_URL = 'http://127.0.0.1:11434'
& '.venv/Scripts/python.exe' -m app.agents.diagnosis.quality.evaluate
```

This command is **live-only**: no deterministic reasoner is available in its
implementation. It checks the configured model appears in `/api/tags`, creates
isolated migrated storage, uses the existing real D1 encoder, and runs the labeled
dataset. Without configuration it actually returned
`{"status":"blocked","reason":"CONFIGURE_LOCAL_OLLAMA_MODEL"}` with nonzero
exit status. Missing installed models/daemon produce `LOCAL_MODEL_UNAVAILABLE`.
There is no hardcoded new model tag or fake successful inference.

Live root-cause correctness, hallucination behavior, contradiction handling,
latency and reasoning quality are **not verified**. Transport timeouts/malformed
responses are tested against synthetic local HTTP servers, not real model errors.

## Added components

Paths below are relative to `backend/`:

| Path | Responsibility |
| --- | --- |
| `app/agents/diagnosis/quality/__init__.py` | D3 package boundary |
| `quality/contracts.py` within that package | Quality issues, citation/retrieval provenance, checked result |
| `quality/evidence.py` | Citation/sufficiency/conflict/narrative quality policy |
| `quality/service.py` | Per-call D1-compatible gateway around unchanged D2 |
| `quality/recording.py` | Explicit optional audit event recorder |
| `quality/manager_adapter.py` | Pure Manager wire mapping, without registry/ORM changes |
| `quality/evaluate.py` | Labeled dataset runner and live-only CLI |
| `fixtures/diagnosis-quality.json` | Nine small labeled source/incident fixtures |
| `tests/diagnosis/quality/__init__.py`, `conftest.py` | Isolated tests reusing D2 scenarios |
| `tests/diagnosis/quality/test_quality.py` | Citation tampering, unsupported claims, provenance, audit and wire mapping |
| `tests/diagnosis/quality/test_evaluation.py` | Nine-case deterministic evaluation assertions |
| `tests/diagnosis/quality/test_transport.py` | Real loopback socket timeout integration test |
| `docs/DIAGNOSIS_D3_VERIFICATION.md` | This report |

The abbreviated `quality/*.py` rows refer to
`app/agents/diagnosis/quality/*.py`. No runtime dependency or infrastructure was added.

## Validation and quality decisions

`QualityDiagnosisService` wraps D2. A fresh `QualityRag` gateway is constructed per
invocation, so concurrent requests do not share provenance state. It reuses D1
retrieval, path matching and authoritative `EvidenceStore.resolve`; it does not
implement another embedding/index/source store. D2 still rechecks citations
before and after reasoning.

Before an LLM call, D3:

- Revalidates evidence DTO values and relative paths; rejects nonpositive/reversed
  ranges, changed path/symbol/content hashes, wrong source references or revisions.
  Actual file bytes, line slices and scope come from the existing D1 resolver.
- Detects different source manifest references in one requested revision.
- Recomputes exact line matches from parsed trace frames and indexed relative
  paths, rather than trusting a reported exact-match tier alone.
- Requires resolvable stack evidence when usable frames are provided. With no
  stack match, semantic-only evidence must reach the policy's 0.6 cosine threshold.
- Requires manual review when terminal log exception type conflicts with the
  recorded incident error type.
- For a quoted Python KeyError key, checks whether complete cited Python context
  contains that direct key subscript. Missing direct access means **unsupported
  interpretation**, not proof that the recorded incident is impossible. Incomplete
  syntax/context requires review. Source is parsed as data, never executed.
- Treats languages outside the currently evaluated Python policy as
  `LANGUAGE_NOT_EVALUATED`. D1's language support is preserved; D3 does not claim
  equivalent diagnosis quality for languages absent from its positive fixtures.

After D2 reasoning, D3 checks hypothesis statements, suggested direction and
uncertainty for narrative file/line references outside returned citations. This
also covers references to configuration formats absent from the indexed corpus.
It flags unsupported certainty or claims of running tests, applying patches, or
verifying recovery. Rejected findings are replaced with a low-confidence review
outcome and a specific action; they are not relabeled as confirmed facts.

These checks are conservative prototype rules, not a semantic truth engine.
AST presence does not prove a branch executed, Python types are not runtime
attestation, regex checks do not understand every natural-language reference,
and scores are not calibrated confidence. An LLM can cite genuine code while
forming a wrong causal hypothesis. Representative live/human evaluation remains
necessary; no accuracy percentage is claimed.

## Provenance and recording

`QualityResult` contains the unchanged internal D2 result, quality issues/actions,
verified evidence IDs and a retrieval provenance record: exact application/
revision, sanitized request hash, embedding profile, retrieval status/reason,
semantic-use flag, timestamp, real citation IDs, artifact/manifest references,
source hashes, rank and similarity. Early context failures explicitly say
`not_requested`; they do not invent a retrieval attempt.

Default diagnosis remains read-only. A caller may explicitly invoke
`OutcomeRecorder(engine).record(checked)` to insert a `diagnosis_quality_reviewed`
event in the **existing** AuditEvent table. It checks incident/run/application/
revision and provenance scope and uses the existing transaction/rollback boundary.
It stores outcome/reason codes and bounded provenance metadata, never raw query,
stack/log/source bodies, or a claimed confirmed cause. It creates no new schema,
workflow transition, Diagnosis or AgentExecution record. Optional recording is not
authorization: Manager must approve actor/audit ownership before wiring it in.

If needed, the caller can place the returned event ID into
`checked.audit_event_id`. Repeated invocations create separate historical events;
Manager still owns any desired invocation idempotency/retention policy.

## Labeled observations

Dataset: `fixtures/diagnosis-quality.json`. Expected status, expected source and
lexical hypothesis terms remain evaluator-only; the model receives only sanitized
incident context and retrieved evidence. The runner never executes source and
compares fixture source hashes before/after diagnosis.

A completed local evaluation used the **real pinned D1 BGE embeddings** and an
explicit `deterministic-quality-test-only` reasoner from tests. It made two
reasoner calls; seven cases stopped for review before reasoning. Observed results:

| Case | Observed status | Observation |
| --- | --- | --- |
| `missing_key` | completed | `app.py` retrieved; expected name/key terms present |
| `zero_division` | completed | `arithmetic.py` retrieved; expected zero/denominator terms present |
| `key_not_supported` | manual_review | `REPORTED_KEY_NOT_SUPPORTED` |
| `contradictory_exception` | manual_review | `CONFLICTING_ERROR_TYPES` |
| `missing_stack_file` | manual_review | `UNRESOLVED_STACK` |
| `unassessed_language` | manual_review | `LANGUAGE_NOT_EVALUATED` |
| `malformed_source` | manual_review | `SOURCE_CONTEXT_INCOMPLETE` |
| `malformed_trace` | manual_review | D2 `MALFORMED_LOG`, no retrieval invented |
| `no_source` | manual_review | `INSUFFICIENT_EVIDENCE` |

All nine source hashes remained unchanged. Expected files were retrieved for all
seven cases with a source target. These are retrieval/policy/test-reasoner
observations, **not live LLM root-cause correctness results**. Term matching is a
transparent small rubric, not an accuracy metric or proof of causation. Detailed
generated observations are kept under ignored `.tools/branch-safety/`, not Git.

## Inspected Manager compatibility

Inspected immutable commit: `b74f09aad6c649a44d3efbfdc301c65e5a3b0631` on
`manager-backend`. Primary sources: `backend/AGENT_INTEGRATION.md`,
`app/agents/registry.py`, `app/services/manager.py`, `app/workers/dispatcher.py`,
`app/db/models.py`, `app/db/session.py`, and `WORKFLOW_DOCUMENTATION.md` in that
branch. Inspection did not execute its code or import its database configuration.

| Topic | Manager implementation | Diagnosis boundary / decision |
| --- | --- | --- |
| Invocation | async `AgentProtocol.execute(AgentInput)` | Current service synchronous; wire mapping only, no automatic registration |
| Required fields | `incident_id`, `run_id`, `repository_revision`; `extra` defaults empty | All three required; `extra.application_id` also required by Diagnosis |
| Context fields | Stage populates `source_log`, `error_type`, `error_message`, `application_id` in `extra` | Maps source_log to inline stack_trace; error fields optional, checked against stored records |
| Optional artifact ref | Not populated by current stage | Adapter accepts explicit stack_trace_ref, requires exact incident linkage in D2 |
| Request version | AgentInput dataclass has no schema_version | Adapter produces internal 1.0; future shared version needs agreement |
| IDs | Incident and active IncidentRun IDs owned by Manager | No fabricated IDs; exact scope/run linkage required |
| Revision custody | Incident revision passed through; model default is `HEAD`; docs describe exact Git revision | Adapter rejects moving aliases; require registered immutable revision. D1 seal is not Git attestation |
| Logs | Inline `Incident.source_log` in Manager's DB | This branch uses linked artifact/event records. Selection/sanitization and corresponding records must be reconciled |
| Persistence | Manager inserts Diagnosis with evidence_json, records AgentExecution and transitions | D2/D3 return data; optional D3 audit is explicit. No duplicate diagnosis/execution ownership |
| Database | AsyncSession; IncidentRun/incident_runs and single app/db/models.py | This branch uses synchronous Engine/Store, workflow_runs, normalized revision/evidence tables; **not directly compatible** |
| Output | AgentOutput success/data/error/duration_ms; aliases accepted | Pure adapter returns exact common Diagnosis fields, actual artifact refs; no alias dependency |
| Status | completed -> generating_patch; manual_review -> manual_review | Normal quality reviews map to successful invocation with data.status=manual_review; infrastructure/context errors use success=false |
| Timeout/retry | Diagnosis uses asyncio.wait_for and agent timeout_seconds (default120); no automatic diagnosis retry seen | Local HTTP socket timeout default30; no retry. End-to-end deadline/cancellation/thread handoff and idempotency unresolved |
| Error envelope | AgentOutput.error is string; REST uses error(code,message,details) + meta(request_id) | Adapter uses stable sanitized error codes; does not replace either branch's REST errors |
| Evidence artifacts | Consumer persists seven evidence fields; missing IDs/excerpts have defaults | Diagnosis supplies real verified IDs/excerpts. Do not rely on consumer-created placeholder artifact IDs |
| Provenance | Current normalization drops extra retrieval metadata | Agree on audit/artifact retention before integrating D3 provenance |

`manager_adapter.py` implements only safe, pure `from_manager` / `to_manager`
mappings and tests against the inspected dataclass shape. It imports none of
Delvin's implementation and does not pretend the differing ORM/session models are
compatible. No runnable bridge, registry replacement, merge or migration is made.

## Validation results and remaining work

D2 review checks and publication passed as recorded above. Actual D3 validation:

| Check | Result |
| --- | --- |
| Ruff lint | Passed with unchanged configuration and no new suppressions |
| Ruff format check | Passed; 137 files formatted, including documentation examples |
| Initial focused D3 suite | 20 passed in 16.74 seconds before later regression additions |
| Final full backend suite | **273 passed in 132.13 seconds**, no failures/skips |
| D3 cases in final suite | **25 passed**; labeled dataset asserts all nine case observations |
| D2 cases in final suite | **39 passed**, including synthetic HTTP malformed-response tests |
| Existing API/contract/database/migration/live frontend integration checks | Passed within the final full suite |
| Real local socket timeout | Passed against deliberately delayed synthetic HTTP endpoint |
| Real embeddings + deterministic reasoning evaluation | Nine labeled observations as reported above; not live LLM inference |
| Live evaluator without model configuration | Failed closed with structured blocked status |
| Preservation | All original 108 protected hashes unchanged; starting frontend/database bytes unchanged |

The earlier 270-test run and a preceding 273-test run also passed. The final
run adds an assertion that rejected references are removed from uncertainty,
not merely marked as invalid. No real model timeout behavior is claimed without
live inference. Standalone frontend build/lint/unit suites were not rerun because
no frontend or shared public contract changed. No existing tests were weakened.

Fixture artifact references in generated observations belong to disposable
evaluation storage; they are not production records or inserts into the real DB.

Before integration, Delvin and Sahad must resolve the database/session model
handoff, revision attestation, log selection, schema versioning, cancellation and
retry behavior, audit/provenance persistence, and artifact custody. Select and run
the real local model using the live evaluator, then review causal findings and
unsupported claims case by case. D3 is not merged, committed or pushed by this task.

## D3 publication review and D4 preparation

The subsequent D3 publication request authorizes committing only these 14 D3
source, fixture, test and report files with the requested message. Earlier local/
uncommitted statements above describe the original D3 development handoff.

Fresh publication validation on 2026-11-24 passed Ruff lint, Ruff format checks
(137 files), and the full backend suite: **273 passed in 126.71 seconds**, with
no failures or skips. The 25 D3 and 39 D2 cases and existing live frontend/API/
migration regressions are included. No existing test or implementation changed.

All seven unrelated frontend edits are excluded. Preservation includes raw hashes
of 383 existing files, a local archive of the uncommitted work and an integrity-
checked SQLite backup under ignored `.tools/branch-safety/`. Databases, weights,
credentials, caches and backups are not commit candidates.

Manager inspection refreshed the same immutable commit `b74f09a` using fetch and
git show only. Current local model checks still found no executable, responding
endpoint or configured model. No live inference success is claimed. The separate
`DIAGNOSIS_D4_INTEGRATION_PLAN.md` records proposed integration changes and approval
gates; it is not part of the D3 commit or a runtime integration.
