# Diagnosis D2 — reasoning service verification

Date: 2026-11-23. Branch: `Diagno-Agent`.

## Published prerequisite and D0/D1

The user separately approved publishing the previously untracked Phase 3
foundation before D0/D1. The reviewed commits are:

- `7932767ebbefb5f93302d25947e1b9e1e19f7894` —
  `feat(backend): publish preserved Phase 3 foundation` (103 files).
- `b9d1c0b24514849990977fdad3cfec47518ae116` —
  `feat(diagnosis): implement D0 architecture and D1 Code RAG` (28 files).

Both were pushed with `git push origin Diagno-Agent`. A subsequent
`git ls-remote --heads origin Diagno-Agent main main-Frontend` reported the exact
D0/D1 commit as `refs/heads/Diagno-Agent`. `main` remained
`2eae39468f34a694f39b110d4aef6caff8b591a1`. No merge, reset, force-push, or update
to an integration branch occurred. The existing frontend edits were excluded.

D0/D1 includes the 17 Python package/source files under `backend/app/agents/`,
seven files under `backend/tests/diagnosis/`, the optional requirements input/lock,
and the two D0/D1 reports. Its complete file inventory is in
`DIAGNOSIS_D1_VERIFICATION.md` and the commit's file listing. Model weights, real
environment files, databases, caches, tooling and generated runtime data were not
staged. The credential scan's only hits in the prerequisite were deliberately
invalid credential-shaped strings in existing configuration/redaction tests.

Immediately before committing, the full backend suite passed **209 tests in
77.31 seconds**, Ruff lint passed, and Ruff format reported 113 files formatted.
All staged file paths and Git content hashes were compared with the reviewed
allowlists. The original 108 protected working-copy hashes matched throughout.

## D2 scope and architecture

`DiagnosisService.diagnose(DiagnosisRequest)` is an internal, synchronous typed
interface for a future Manager adapter. D2 is deliberately separate from REST
routes and persistence until Manager's final contract is agreed.

The service:

1. Revalidates the mock Manager request, including exact revision and required
   incident/run identifiers. It rejects controls in supplied observation text.
2. Reads existing incident/run records through `transaction`/`Store`, checking
   incident, run, application and revision linkage before any model call.
3. Uses the stored incident error type/message. Conflicting caller-supplied
   observations require manual review instead of overriding recorded facts.
4. Reads an optional existing redacted, hash-checked log only if it is linked to
   this exact incident. Without an explicit trace/ref, it selects a bounded,
   deterministic linked log. Inline traces and stored logs are bounded to 16000
   characters. NUL, oversized, unreadable and non-frame trace material fail safely.
5. Calls D1's hybrid retrieval with the bound context, at most five source chunks,
   and verifies citations against the actual immutable manifest/source/excerpts.
6. Sends bounded sanitized observations and verified evidence to an injected
   reasoning provider as an untrusted JSON data envelope, separate from system
   instructions. There are no model tools, execution APIs or repair operations.
7. Validates the model's structured draft and requires every hypothesis to cite
   only supplied evidence IDs. The model cannot supply new paths/line ranges.
8. Resolves the source citations again after the model call, detecting provider-time
   artifact changes before returning findings. Invalid references discard the draft.
9. Returns explicit observations, hypotheses and uncertainty, or an insufficient-
   evidence/manual-review outcome. No inferred diagnosis is treated as proven cause.

The service does not create/update `Diagnosis`, `EvidenceReference`,
`AgentExecution`, workflow transitions, artifacts, or application files. Integration
tests compare all domain table row counts before/after successful reasoning.
Existing REST APIs, schemas, migrations and frontend behavior are unchanged.
New D2 files remain local and uncommitted; the user authorized publishing D0/D1,
not an automatic D2 commit or merge.

## Files added for D2

All paths are relative to `backend/`:

| Path | Purpose |
| --- | --- |
| `app/agents/diagnosis/reasoning/__init__.py` | Internal reasoning package boundary |
| `app/agents/diagnosis/reasoning/contracts.py` | Mock Manager request, draft, facts, hypotheses, typed result |
| `app/agents/diagnosis/reasoning/config.py` | Optional provider settings with loopback validation |
| `app/agents/diagnosis/reasoning/providers.py` | Protocol, disabled default, bounded Ollama HTTP adapter |
| `app/agents/diagnosis/reasoning/repository.py` | Read-only incident/run/log context repository |
| `app/agents/diagnosis/reasoning/service.py` | Retrieval, reasoning, citation validation and review policy |
| `tests/diagnosis/reasoning/__init__.py` | Isolated reasoning test package |
| `tests/diagnosis/reasoning/conftest.py` | Mock Manager fixtures, migrated domain data, test-only reasoner |
| `tests/diagnosis/reasoning/test_service.py` | Success, evidence/revision/error/fallback/compatibility tests |
| `tests/diagnosis/reasoning/test_local_provider.py` | Real loopback HTTP transport with synthetic model responses |
| `docs/DIAGNOSIS_D2_VERIFICATION.md` | Decisions, setup, validation and Manager handoff |

No D0/D1 implementation or protected foundation file was changed for D2.
No additional runtime dependency or migration is required.

## Result contract and review policy

The internal result retains the existing Diagnosis field names:
`incident_id`, `run_id`, `status`, `hypothesis`, `confidence_label`, `uncertainty`,
`suggested_direction`, and `evidence`. Status remains `completed` or `manual_review`.

Internal additions are `schema_version`, `application_id`, `input_revision`,
`stage`, UTC `created_at`, `outcome`, `hypotheses`, `facts`, `provider`,
`used_test_fallback`, and structured `error`. The evidence list keeps D1's rich
metadata, including evidence IDs and content/source hashes. `to_public()` is an
explicit, tested projection to the unchanged public Diagnosis DTO; nothing
automatically registers or persists that projection.

Each hypothesis contains a statement, selected evidence IDs and its own
uncertainty. Facts are service-generated observations of actual source ranges and
verified stack membership, not free-form assertions made by the LLM. The aggregate
hypothesis starts with “Possible causes”. Every successful response includes the
mandatory limitation that execution, tests and recovery have not been verified.
Unverified model confidence is capped at `medium`; review/fallback findings are
`low`. Confidence is qualitative and is not a calibrated probability.

- No usable source: `status=manual_review`, `outcome=insufficient_evidence`;
  no model call and no invented hypothesis.
- Context/revision/log conflict: manual review before any model call.
- Provider failure/invalid JSON, unknown citations or unsafe draft: manual review;
  no silent synthetic production answer.
- Partial D1 retrieval or model-requested review: findings remain explicitly
  manual-review results, even if a plausible hypothesis was produced.
- Model output cannot introduce citation paths/lines; unknown IDs, duplicates,
  missing uncertainty, extra schema fields, secret-shaped output and fenced code/
  patch markers are rejected. Natural-language plausibility still needs human
  review; matching a citation does not establish causal correctness.

## Provider configuration and transport

The default provider is **disabled**, returning manual review when reasoning is
requested. The included real adapter targets an explicitly configured local
Ollama model. Its `/api/chat` request uses a JSON schema in `format`, `stream=false`
and temperature zero, as described in the
[official structured-output API example](https://ollama.com/blog/structured-outputs).
There is no API key, hosted provider SDK, model download, model pull, or execution
capability in this module.

`DiagnosisSettings` reads process `SENTINEL_DIAGNOSIS_*` variables, not the shared
strict backend `.env`. Example, after installing/starting a local model separately:

```powershell
$env:SENTINEL_DIAGNOSIS_PROVIDER = "ollama"
$env:SENTINEL_DIAGNOSIS_MODEL = "your-already-installed-local-model"
$env:SENTINEL_DIAGNOSIS_BASE_URL = "http://127.0.0.1:11434"
$env:SENTINEL_DIAGNOSIS_TIMEOUT_SECONDS = "30"
```

Only explicit HTTP loopback literals (`127.0.0.1` or `::1`) and ports are accepted.
Credentials, arbitrary hosts, paths, query strings, fragments, redirects and
environment proxies are rejected/disabled. Responses are bounded to 65536 bytes
by default; incomplete responses, tool calls, invalid envelopes and non-JSON
drafts fail closed. Socket timeout is bounded/configurable, and no automatic
retry is performed. The operator must select a genuinely installed local model
and trusted local daemon; an alias/server configuration is not cryptographic
proof of where that daemon performs inference. Known `-cloud` tags are rejected.

A configurable `ReasoningProvider` can be injected for future adapters. The
deterministic fixture implementation exists only in tests. Supplying a
`test_fallback` additionally requires both `Settings.environment="test"` and
`DiagnosisSettings.allow_test_fallback=True`. Fallback use is explicitly recorded,
always manual review/low confidence, and cannot masquerade as real LLM success.

## Mock Manager invocation

The incident and run below must already exist and agree with the exact revision.
Manager remains responsible for creating them; D2 does not invent an execution.

```python
from app.agents.diagnosis.code_rag.service import CodeRag
from app.agents.diagnosis.reasoning.contracts import DiagnosisRequest
from app.agents.diagnosis.reasoning.service import DiagnosisService
from app.core.config import Settings
from app.db.session import create_database_engine

settings = Settings()
engine = create_database_engine(settings)
try:
    rag = CodeRag(engine, settings)
    service = DiagnosisService(engine, settings, rag)
    result = service.diagnose(
        DiagnosisRequest(
            schema_version="1.0",
            incident_id="existing_incident_id",
            run_id="existing_run_id",
            application_id="existing_application_id",
            repository_revision="registered_exact_revision",
        )
    )
finally:
    engine.dispose()
```

The automated tests use this same boundary with mock Manager requests, real
migrated incident/run records and actual D1 indexing/retrieval. The HTTP integration
tests exercise the real adapter against a synthetic Ollama-compatible server;
they do **not** represent real LLM inference or a reasoning-quality benchmark.

## Actual validation results

Before publishing D0/D1: Ruff lint/format passed and 209 backend tests passed.
D2 focused validation: **39 passed in 13.76 seconds** before the final richer
citation serialization assertion was added. The full final run includes that
assertion and all existing tests:

| Check | Actual result |
| --- | --- |
| `python -m ruff check .` | Passed; no rule/config changes or new suppressions |
| `python -m ruff format --check .` | Passed; 124 files formatted, including documentation examples |
| `python -m pytest` | **248 passed in 87.72 seconds**; no failures or skips |
| D2 cases in final suite | **39 passed**, including eight synthetic-server HTTP cases |
| Existing backend/API/contract/migration/browser probes | Passed within the full suite |
| Live LLM inference | Not run: no local server/model available |
| D0/D1 remote publication | Verified remote tip equals `b9d1c0b24514849990977fdad3cfec47518ae116` |

The 39 D2 cases cover successful source-supported diagnosis, exact scope/run
conflicts, insufficient source, malformed/oversized/NUL logs, conflicting supplied
observations, invalid/invented citations, invalid/secret/code-shaped drafts,
provider failures, deterministic fallback repeatability/test-only gating,
post-provider artifact tampering, forged retrieval metadata, partial retrieval,
request validation, public DTO compatibility, unchanged database row counts,
real HTTP request/schema construction, redirects, HTTP failures, oversized/
incomplete/tool-call responses and disabled-by-default behavior.

No Ollama executable was found on PATH, and a connection check to
`127.0.0.1:11434` reported unavailable. **Live LLM reasoning has not been verified.**
No model was downloaded or started. Real D1 semantic embeddings were verified in
the previous milestone; deterministic D2 reasoning tests are not evidence of a
live LLM's diagnostic accuracy.

Standalone frontend lint/build/unit/full-browser suites were not rerun because
D2 changes no frontend/shared public schema. Existing live frontend integration
tests remain in the backend suite. No existing tests were removed or weakened.

## Manager integration decisions still needed

1. Finalize the request/result envelope and versioning. Existing public fields
   `hypothesis`/`suggested_direction` remain intact; proposed `root_cause` or
   `suggested_fix` names are not silently introduced into REST contracts.
2. Confirm who freezes/attests each exact source revision and registers/indexes
   its immutable snapshot. D1's operator-bound seal is not Git attestation.
3. Confirm inline traces versus incident-linked artifact references, log selection
   when many monitoring events are linked, and support for structured non-stack logs.
4. Define worker scheduling, time budgets, cancellation and duplicate invocation
   behavior. The current synchronous service does not manage workflow transitions.
5. Define authorization, audit ownership and persistence of Diagnosis,
   EvidenceReference and AgentExecution together. D2 deliberately does not write
   these records until their lifecycle/Manager contract is approved.
6. Confirm how partial retrieval, model review requests and insufficient evidence
   map to Manager stage outcomes and administrator review. Confirm whether to
   expose the explicit compatible public projection later.
7. Select and evaluate a real local model on representative labeled incidents,
   including irrelevant evidence, prompt injection and alternative causes.

D2's internal reasoning implementation and mock-provider integration are ready
for review. Live model quality, final Manager integration and persistence remain
unverified/deferred. D2 has not been committed, pushed, or merged into any branch.

## D2 publication review — 2026-11-24

The current request authorizes a separate D2 commit and push to `Diagno-Agent`.
Only this report and the ten existing reasoning source/test files belong in that
commit. D3 additions are excluded. Original reports above describe their run dates.

Fresh inspection found no Ollama executable on PATH or in its standard per-user/
Program Files locations. Diagnosis settings are `provider=disabled`, model unset,
and `http://127.0.0.1:11434/api/tags` is inaccessible. No live model was substituted
with a test fixture. Root-cause correctness, contradictory evidence handling and
unsupported-claim rates from actual LLM inference remain unmeasured.

### Exact Windows setup for subsequent live verification

1. Download and run `OllamaSetup.exe` from the
   [official Windows download](https://ollama.com/download/windows), then open a
   new PowerShell terminal. The [Windows documentation](https://docs.ollama.com/windows)
   describes the native install and standard local endpoint.
2. Check `ollama --version` and `ollama list`. If the tray application is not serving
   the API, run `ollama serve` in a separate terminal; do not launch a second daemon
   over an already running server.
3. Select an installed local model explicitly. No model is hardcoded in Diagnosis:

```powershell
cd 'D:\projects\SENTINAL AI\backend'
ollama list
$env:SENTINEL_DIAGNOSIS_MODEL = Read-Host 'Enter the exact installed local model tag'
# If the chosen model is not installed, explicitly download it first:
# ollama pull $env:SENTINEL_DIAGNOSIS_MODEL
$env:SENTINEL_DIAGNOSIS_PROVIDER = 'ollama'
$env:SENTINEL_DIAGNOSIS_BASE_URL = 'http://127.0.0.1:11434'
Invoke-RestMethod 'http://127.0.0.1:11434/api/tags'
```

Keep these as process variables, not new entries in the strict shared backend
dotenv. Model installation is an operator action; no weights are stored in Git.
Run the D3 labeled evaluation command documented in `DIAGNOSIS_D3_VERIFICATION.md`
once the model and its D1 embedding dependency are available. It uses disposable
databases and source fixtures, never the existing application database.

The initial fresh 248-test run had 247 passes and one existing frontend browser
navigation timeout (`page.goto`, 10 seconds) in the persisted-data probe. No test
was changed or weakened. The final validation result is recorded after rerunning.

A second run also had 247 passes, with the same navigation timeout in the
unavailable-backend probe. The focused browser suite then passed **4 tests in
49.79 seconds**, and the unchanged full baseline passed **248 tests in 116.15
seconds**. Ruff lint/format passed. All 39 D2 cases passed in these runs. Live
inference remains unavailable as described above. The separately authorized D2
commit includes only the 11 D2 source/test/report files; D3 work is excluded.
