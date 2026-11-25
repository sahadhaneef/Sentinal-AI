# Diagnosis to Manager handoff

Prepared 2026-11-24. Diagnosis branch: `Diagno-Agent`; inspected Manager commit:
`b74f09aad6c649a44d3efbfdc301c65e5a3b0631`. Scope: D4A adapter preparation.
Updated 2026-11-25 for D4B. The user's D4B request relays Delvin's agreement in
principle on ownership, isolation, deadlines, cancellation and retry policies.
**Concrete repository field mappings, canonical schema and migrations are not
approved. Do not register the agent or merge branches on this basis.** Full evidence and gate
details: [D4 integration plan](DIAGNOSIS_D4_INTEGRATION_PLAN.md).

## Observed contracts (implemented compatibility, not team approval)

Manager uses dataclasses `AgentInput` and `AgentOutput` from
`app/agents/registry.py`. Diagnosis accepts the input as a dataclass or dictionary:

```json
{
  "incident_id": "existing_incident_id",
  "run_id": "existing_run_id",
  "repository_revision": "registered_revision",
  "extra": {
    "application_id": "existing_application_id",
    "source_log": "sanitized selected trace",
    "error_type": "KeyError",
    "error_message": "Missing profile name",
    "stack_trace_ref": null
  }
}
```

All four scope fields are required by Diagnosis. `extra` defaults to empty in
Manager, which is insufficient for Diagnosis. IDs use the existing portable
identifier contract (1–64 characters). Revision is a portable token (1–128);
HEAD/main/master/latest are rejected, but syntax alone cannot attest immutability.
`source_log`, `error_type`, `error_message` default to empty and are bounded at
16000/200/2000 characters. `stack_trace_ref` is optional and must resolve to an
incident-linked artifact. Unknown input/extra fields are rejected. Manager today
passes the four context fields but does not supply `stack_trace_ref`.

`from_manager` produces internal `DiagnosisRequest(schema_version="1.0")` and
maps `source_log` to `stack_trace`. Stored incident/run observations are validated;
caller-provided text is not allowed to silently override authoritative context.

Output shape is unchanged:

```json
{
  "success": true,
  "data": {
    "status": "completed",
    "hypothesis": "A source-supported possible cause, not a confirmed fact.",
    "confidence_label": "medium",
    "uncertainty": "Runtime input remains unobserved.",
    "suggested_direction": "Review the cited input contract.",
    "evidence": []
  },
  "error": null,
  "duration_ms": 0
}
```

This illustrates field names only; a real completed result requires verified,
nonempty evidence and hypotheses. Each evidence entry contains `file_path`,
`symbol`, inclusive positive `start_line`/`end_line`, `repository_revision`, real
`artifact_id`, and `excerpt`. Public status is `completed` or `manual_review`;
confidence is low/medium/high. Incident/run IDs remain in the input context.
Internal facts, hypothesis evidence IDs, quality reasons and retrieval provenance
are retained in `QualityResult`, not added to the public data projection.

## Ownership direction agreed in principle; concrete mappings pending

| Topic | Observed difference | Proposed agreement / required owner decision |
| --- | --- | --- |
| Revision custody | Manager defaults can be HEAD; Diagnosis requires registered sealed source | Delvin captures and binds exact application/run/revision/snapshot; Sahad verifies scope and source hashes. Agree how Git identity is attested |
| Logs | Inline Manager source_log versus linked events/artifacts in Diagnosis | Agree one selected event/log, sanitization owner, size policy and inline/artifact precedence. Diagnosis redaction/control checks are additional defenses, not the complete sanitization contract |
| Result persistence | Manager inserts Diagnosis/AgentExecution and transitions; Diagnosis defaults read-only | Manager ownership agreed in principle. Keep optional OutcomeRecorder disabled; agree canonical record mappings, idempotency and provenance retention |
| Evidence custody | Manager stores evidence_json and can synthesize missing IDs/excerpts | Preserve actual artifact identity and hashes; Delvin removes fallback placeholders for real outputs and defines artifact access/retention |
| Database/session | Manager AsyncSession/incident_runs; Diagnosis Engine/Store/workflow_runs, normalized revisions/evidence | Choose one canonical model/repository boundary. No mirrored operational database, copied incident rows, cross-thread AsyncSession or competing migrations |
| Timeout/cancellation | Manager wait_for default120 seconds; synchronous Diagnosis HTTP timeout default 30 seconds | Overall120 seconds and Manager deadline authority agreed in principle. D4B implements bounded spawn workers, cooperative checkpoints and termination; final active-invocation rejection remains Manager-owned |
| Retries | Adapter has none; LLM_UNAVAILABLE covers permanent and transient conditions | Manager owns at most one retry, only explicitly transient and within the same stage deadline. D4B returns internal classification; public error-envelope mapping, backoff and attempt identity remain pending |

No transaction should remain open across inference. Matching table names do not
make these branches' schemas compatible. D1's private vector cache is derived
retrieval data; it does not own workflow state. Any shared migration needs separate
team review before implementation.

## Existing outcome mappings

| Diagnosis outcome | Adapter output | Inspected Manager behavior |
| --- | --- | --- |
| Supported hypothesis | success=true, data.status=completed | Persists diagnosis/execution; transitions to generating_patch |
| Insufficient/conflicting evidence, unsupported language, model review, invalid model citations/claims | success=true, data.status=manual_review | Persists review diagnosis; transitions to manual_review |
| LLM_UNAVAILABLE, TEST_FALLBACK_FAILED, CONTEXT_UNAVAILABLE, CONTEXT_SCOPE_MISMATCH, INCIDENT_INPUT_CONFLICT, LOG_SCOPE_MISMATCH | success=false, data={}, error=code | Records execution error and transitions to manual_review |
| Invalid adapter request/result | Fixed safe exception at async boundary | Manager currently catches Exception and records its string; agree final error taxonomy |
| Cancellation | CancelledError propagates; no fabricated outcome | Final cancellation persistence and late-result rejection remain Delvin's responsibility |

Manager currently records execution completed for success=true/manual_review.
Confirm whether that means completed invocation rather than confirmed diagnosis.
No new status, retryable flag or shared error envelope is silently introduced.

## Adapter invocation examples

Existing isolated synchronous service usage (not inside Manager's event loop):

```python
from time import monotonic
from typing import Any

from app.agents.diagnosis.quality.manager_adapter import ManagerOutcome, from_manager, to_manager
from app.agents.diagnosis.quality.service import QualityDiagnosisService


def map_existing_service(
    service: QualityDiagnosisService, payload: dict[str, Any]
) -> ManagerOutcome:
    """Illustrate mapping with an already initialized, isolated service."""
    started = monotonic()
    request = from_manager(payload)
    checked = service.diagnose(request)
    return to_manager(checked, duration_ms=int((monotonic() - started) * 1000))
```

The unregistered async seam can be tested using a prepared, validated fixture:

```python
from typing import Any
from unittest.mock import AsyncMock

from app.agents.diagnosis.quality.contracts import QualityResult
from app.agents.diagnosis.quality.manager_adapter import ManagerOutcome
from app.agents.diagnosis.quality.manager_invocation import invoke_manager_request


async def map_test_fixture(payload: dict[str, Any], checked: QualityResult) -> ManagerOutcome:
    """Translate a prepared test result without registering a real agent."""
    callback = AsyncMock(return_value=checked)
    return await invoke_manager_request(payload, callback)
```

These are usage illustrations, not a production bridge. The seam requires an
async function, protects request correlation, checks result/provenance consistency,
sanitizes failures, measures duration, and propagates cooperative cancellation.
It rejects passing synchronous `QualityDiagnosisService.diagnose` directly.
It does not select a worker/session/deadline or convert to Manager's own
AgentOutput instance. Do not introduce an unbounded thread wrapper as a shortcut.

## Delvin actions and runtime acceptance

1. Finalize remaining revision/log rules, canonical schema and field mappings,
   provenance sink, concrete cancellation/attempt persistence and status/error
   mappings. D4B records the ownership direction relayed by the user; it does not
   infer approval of these remaining implementation contracts.
2. Agree shared-context repository integration, artifact access and provenance
   retention; remove placeholder evidence fallbacks for actual Diagnosis outputs.
3. Specify invocation/attempt identity, bounded retries and final active-run,
   revision, deadline and source-integrity checks before a single result commit.
4. Demonstrate real Manager-to-Diagnosis execution with agreed repositories:
   success, review, invalid revision, corrupt citations, timeout/cancellation,
   duplicate request, rollback and restart must produce asserted persisted states.
5. Verify no source writes or competing diagnosis/workflow records, and preserve
   public APIs/frontend contracts. Cooperative mocks alone are insufficient.
6. Review real-model fixture observations separately from deterministic tests;
   then explicitly approve registration and any combined integration branch.

D4A provides 30 compatibility tests within the backend regression suite. D4C
runtime integration is blocked on the decisions above. D5 model setup/evaluation
can proceed independently after operator-approved local installation/download;
live inference remains unverified.

## D4B implementation boundary

See `DIAGNOSIS_D4B_VERIFICATION.md`. Typed read interfaces now cover atomic
incident/run/log context, registered revisions, snapshot/citation resolution and
persistent code-index access. Existing standalone repositories implement them;
Manager-backed implementations await the canonical schema contract.

`IsolatedDiagnosisWorker` is an unregistered Diagnosis-owned controller: use one
instance per event loop/lifespan and close it with `aclose()` or async context
management. `diagnose_from_manager(payload, worker, deadline=absolute_monotonic)`
preserves the D4A input mapper and returns an internal `WorkerOutcome`, including
full `QualityResult` metadata and an optional `ExecutionFailure`. No HTTP route or
registry hook is added. The same absolute deadline must be reused for Manager's
single eligible retry; passing a fresh deadline would violate Manager's contract.

For a returned quality result, `to_manager(outcome.quality, duration_ms)` remains
the existing public projection. Persist rich hypotheses/facts, source hashes,
provider/fallback metadata, query/embedding provenance and quality reasons via an
agreed Manager-owned sink before discarding internal metadata. The seven-field
public evidence projection is insufficient to retain all provenance by itself.

For failures, Manager must inspect `outcome.failure.kind` and its derived
`retry_eligible` property before deciding its one bounded retry. Only transient
provider HTTP errors, temporary network failures and provider timeouts qualify;
unknown failures, configuration, revisions, artifacts, citations and insufficient
or conflicting evidence do not. Existing quality failures still map through
`to_manager` (for example LLM_UNAVAILABLE); new process-only failures require an
agreed safe AgentOutput.error string mapping. No new fields are inserted into the
existing AgentOutput, DiagnosisRequest 1.0 or DiagnosisResult contracts.

Cancellation propagates as asyncio.CancelledError after test-owned worker reaping.
The controller may forcibly terminate uncooperative native work; this does not
cancel inference already running inside the Ollama server. Manager still owns
final deadline/cancellation/attempt checks, persistence and state transitions.
