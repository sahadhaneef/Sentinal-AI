# D5A live evaluation

The November 25, 2026 live run matched **7 of 9 fixture status labels**. Both
cases expected to complete returned manual review. The worker received and
validated two real model responses, and both contained unsupported claims.
See [live results](#approved-live-run--2026-11-25). Earlier readiness checks
below are historical.

## Historical readiness

Observed 2026-11-24 on `Diagno-Agent`. **Live inference blocked; no accuracy or
live-model latency measurements exist.** No Ollama installer, model download,
provider reconfiguration or Manager registration was performed.

## Actual local checks

| Check | Observation |
| --- | --- |
| Ollama command / standard Windows executable locations | Not found on PATH, LocalAppData/Programs/Ollama or Program Files/Ollama |
| Existing configured loopback `/api/tags` | Unavailable; installed model inventory could not be obtained |
| DiagnosisSettings | provider=disabled, model empty, base_url=http://127.0.0.1:11434, timeout_seconds=30, max_response_bytes=65536, allow_test_fallback=false |
| Existing live-only evaluator | Exit **2**, `{"status":"blocked","reason":"CONFIGURE_LOCAL_OLLAMA_MODEL"}`; no substitute provider used |
| RAM | 16,888,320,000 bytes installed (15.73 GiB); approximately 3.03 GiB free at inspection, variable with application load |
| CPU | Windows reports Intel Core i5-11400H at 2.70 GHz, 2 exposed cores / 4 logical processors |
| GPU | RTX 3050 Laptop GPU, 4096 MiB total, 3962 MiB free at inspection; driver 621.24; Intel UHD also present |
| D1 embedding prerequisite | FastEmbed 0.9.1 / ONNX Runtime 1.32.0 installed; all pinned BGE weight/tokenizer checksums verified offline |

The hardware observations are not throughput benchmarks. A local model installation
outside the inspected locations is not ruled out; the configured API still cannot
provide a usable model. Embedding readiness does not imply LLM readiness.

## Recommended first model and Windows setup

For this 4 GiB GPU, start evaluation with **qwen2.5-coder:3b** rather than a larger
default tag. The official catalog lists its Q4_K_M weights at approximately 1.9 GB.
This is a hardware-sizing recommendation, not verified diagnostic performance or
a guarantee that weights plus context/runtime fit GPU memory. Free system RAM is
currently limited; close memory-heavy applications before measuring. If memory
remains insufficient, the smaller 1.5b variant is a fallback candidate requiring
its own evaluation. Do not change the architecture's configurable model design.
[Official model catalog](https://ollama.com/library/qwen2.5-coder:3b),
[available sizes](https://ollama.com/library/qwen2.5-coder).

1. Download `OllamaSetup.exe` from the
   [official Windows download](https://ollama.com/download/windows), run it and
   reopen PowerShell. Installation is an operator step, not performed here.
2. Start Ollama from the Start menu; its tray application normally serves the API.
   Use `ollama serve` in a separate terminal only if no server is running.
   [Official Windows instructions](https://docs.ollama.com/windows).
3. Inspect available tags. **Only after explicit approval**, download the selected
   model if it is absent. The following pull line is deliberately commented:

```powershell
ollama --version
ollama ls
Invoke-RestMethod 'http://127.0.0.1:11434/api/tags'
# After approval only, if not already installed:
# ollama pull qwen2.5-coder:3b
```

4. Configure process variables in the same terminal. Do not add these keys to the
   shared strict `.env`, change provider defaults or enable test fallback:

```powershell
cd 'D:\projects\SENTINAL AI\backend'
$env:SENTINEL_DIAGNOSIS_PROVIDER = 'ollama'
$env:SENTINEL_DIAGNOSIS_MODEL = 'qwen2.5-coder:3b'
$env:SENTINEL_DIAGNOSIS_BASE_URL = 'http://127.0.0.1:11434'
$env:SENTINEL_DIAGNOSIS_ALLOW_TEST_FALLBACK = 'false'
$env:SENTINEL_DIAGNOSIS_TIMEOUT_SECONDS = '30'
$installed = Invoke-RestMethod 'http://127.0.0.1:11434/api/tags'
if ($env:SENTINEL_DIAGNOSIS_MODEL -notin @($installed.models.name)) {
    throw 'The selected model is not installed; obtain approval before downloading it.'
}
& '.venv/Scripts/python.exe' -m app.agents.diagnosis.quality.evaluate
if ($LASTEXITCODE -ne 0) { throw 'Live evaluation did not complete; inspect the reason.' }
```

The model tag must exactly match `/api/tags`. Record the installed digest, Ollama
version, settings and available resources with each run for reproducibility.
The adapter already uses nonstreaming `/api/chat` with a JSON schema, temperature 0,
bounded response bytes, no tools, redirects, proxying, downloads or automatic
retries. [Ollama structured-output contract](https://docs.ollama.com/capabilities/structured-outputs).

The evaluator creates disposable migrated fixture storage, uses the real pinned
embedding provider and the selected Ollama provider, and never executes application
source. Retain generated reports under ignored `.tools/branch-safety/`, not in Git.
The existing optional embedding setup is in `DIAGNOSIS_D1_VERIFICATION.md`; its
download commands are not needed for the currently checksum-verified installation.

## Evaluation rubric and honest reporting

Reuse `backend/fixtures/diagnosis-quality.json` and the existing evaluator. There
are nine labeled cases: missing key, zero division, unsupported key hypothesis,
contradictory exception, unresolved stack file, unassessed language, malformed
source, malformed trace and no source. Seven may stop before invoking the LLM;
do not count these as successful live-model reasoning calls. Report actual calls.

| Requested measure | Evidence to record once available | Current live result |
| --- | --- | --- |
| Root-cause correctness | Human review of source-supported hypotheses against labels, including uncertainty; keyword matches alone are insufficient | Not measured |
| Citation accuracy | Exact revision, path, inclusive range, excerpt/hash and artifact resolution; list any rejected citations | Not measured |
| Retrieval relevance | Per-case retrieved files and evidence compared with expected target; inspect distractors | Not measured with live inference |
| Unsupported claims | Review assertions of certainty, unprovided files/ranges or executed tests/repairs; retain quality codes | Not measured |
| Manual-review correctness | Expected/observed status and reason for each insufficient/conflicting/malformed case | Not measured with live inference |
| Latency | Existing elapsed_ms is whole diagnosis time, not isolated provider latency. Record cold/warm runs and actual provider calls separately | Not measured |
| Timeout behavior | Controlled slow-server test is synthetic; separately observe actual configured-model deadline failures and review outcomes | No real-model timeout observation |
| Malformed responses | Existing synthetic HTTP tests exercise malformed JSON/schema/envelopes; record actual malformed live responses if observed | No real malformed-model response observation |

Do not deliberately damage a real model server or pretend synthetic transport
fault injection measures model quality. Full pytest covers bounded HTTP timeout,
malformed replies and deterministic evidence/review policies independently.
If the normal evaluator completes, inspect individual results: a zero exit code
does not prove all labels match or establish a causal accuracy percentage.

## Readiness and approvals

D5 preparation is ready; live evaluation awaits Ollama installation, explicit
model-download approval (unless a suitable installed model becomes available),
an exact configured tag and a reachable local server. No large download is
authorized by this report. D4C remains separately blocked on Delvin's six contract
decisions in `DIAGNOSIS_MANAGER_HANDOFF.md`. Model installation cannot resolve
database/session, artifact custody, workflow or cancellation ownership gaps.

Fresh deterministic/regression validation during this finalization passed Ruff
lint, Ruff format (142 files), and the full **303-test suite in 84.21 seconds**,
including all 30 D4 checks and synthetic HTTP timeout/malformed-response cases.
The focused browser/HTTP regression run passed five tests in 50.98 seconds.
Three earlier full runs each had one existing browser/startup timing failure;
the unchanged full suite passed after the user freed memory. These results do
not replace any unmeasured live-inference entry in the table above.

D4A was separately published as `67d89d1e7bb7b4d3524fc7d6d54cf99efe6d6899`
with message `feat(diagnosis): add D4 manager integration preparation`; the remote
`Diagno-Agent` SHA was verified after push. Its five files contain only the adapter,
async helper, integration tests, D4 plan and Manager handoff. This D5 readiness
report remains a separate local, uncommitted deliverable. No D5 inference result
or shared integration approval is implied by that D4A publication.

## D5A finalization and current readiness — 2026-11-25

D4B was reviewed and published separately as
`ee4e6516db0da14b821e678434e96bdd2c96f035`, message
`feat(diagnosis): implement D4B repository abstraction and isolated workers`.
Remote origin/Diagno-Agent was verified at that exact SHA. Its 20 source/test/
integration-document paths exclude this D5 report. Fresh Ruff lint/format passed
(155 files); the full backend suite passed 343 tests in 151.89 seconds, including
40 D4B cases and the existing browser/HTTP, API and database/migration regressions.
Those are deterministic/regression results, not live-model reasoning results.

### Current local observations

- Ollama executable exists at the standard per-user install path; this terminal's
  PATH has not picked it up. No software installation was performed by this task.
- CLI and local /api/version both report 0.40.18. The configured loopback API is
  accessible. /api/tags and /api/ps both return empty model lists.
- Recommended model remains qwen2.5-coder:3b, approximately 1.9 GB of weights. It is
  not installed. Explicit operator approval for download and local evaluation was
  requested; it has not been granted in this session. No pull was attempted.
- Persistent defaults remain provider=disabled, empty model, loopback port 11434,
  socket timeout 30 seconds and allow_test_fallback=false. No real .env or global
  user configuration was changed.
- An isolated process-variable preflight selected provider=ollama and the named
  model with fallback disabled, then ran the existing live-only evaluator. It
  returned `{"status":"blocked","reason":"LOCAL_MODEL_UNAVAILABLE"}`, exit 2.
  No model request, inference, deterministic substitute or download occurred.
- Windows reports 16492500 KiB visible RAM (about 15.73 GiB), with 5498724 KiB free
  (about 5.24 GiB) at inspection. NVIDIA reports RTX 3050 Laptop GPU, 4096 MiB total,
  3962 MiB free and driver 621.24. These are readiness snapshots, not during-inference
  measurements. Free space: C=48529149952 bytes and D=213477511168 bytes.

### Nine-case evaluation status

Use the unchanged dataset and rubric above. The table records non-execution,
not an invented prediction or a failed-model accuracy score.

| Case | Existing expected status | Actual D5A observation |
| --- | --- | --- |
| missing_key | completed | Not run; model absent / approval pending |
| zero_division | completed | Not run; model absent / approval pending |
| key_not_supported | manual_review | Not run; model absent / approval pending |
| contradictory_exception | manual_review | Not run; model absent / approval pending |
| missing_stack_file | manual_review | Not run; model absent / approval pending |
| unassessed_language | manual_review | Not run; model absent / approval pending |
| malformed_source | manual_review | Not run; model absent / approval pending |
| malformed_trace | manual_review | Not run; model absent / approval pending |
| no_source | manual_review | Not run; model absent / approval pending |

Root-cause correctness, evidence relevance, citation validity, unsupported claims,
structured-response validity and manual-review correctness are **unmeasured with
live inference**. There is no denominator of completed live predictions from which
an accuracy percentage could be calculated. The nine labels and their policy-only
cases must not be described as nine successful model calls.

Worker startup, embedding initialization, LLM latency, cold/warm loading and
inference-time RAM/VRAM remain unmeasured in D5A. Existing D4B tests demonstrate
120-second stage-cap handling with short controlled deadlines, cancellation,
forced termination, reaping and late-result rejection using explicitly synthetic
providers; they do not establish live server performance. Killing a Diagnosis
worker does not necessarily cancel work already executing in the Ollama server.

### Next approved step and reproducible configuration

No reinstall is needed. After explicit download approval, use the installed CLI
from PowerShell; its path can be used even before reopening the terminal:

```powershell
$ollamaExecutable = "$env:LOCALAPPDATA/Programs/Ollama/ollama.exe"
& $ollamaExecutable --version
# Execute only after approval:
# & $ollamaExecutable pull qwen2.5-coder:3b
Invoke-RestMethod 'http://127.0.0.1:11434/api/tags'
```

Once that exact installed tag is verified, use the existing process-variable
configuration and evaluator command documented above with provider=ollama,
model=qwen2.5-coder:3b, loopback endpoint, fallback=false and default socket timeout 30.
Keep the worker stage budget 120 and one-worker default. Record model digest,
actual per-case findings, citation checks and component/resource timings; do not
increase limits merely to get success. Keep generated data outside Git and use
isolated fixture storage, not the real application database.

D4C still requires joint approval of canonical schema and migrations, repository
mappings, immutable revision/snapshot custody, log/artifact access, result/evidence
persistence, execution identity and final late-result acceptance. No speculative
Manager repositories, registration, shared migration or integration branch was
created. This D5 report remains a separate local, uncommitted deliverable.

## Approved live run — 2026-11-25

Before download, the existing Ollama model directory was on C:, with 45.17 GiB
free. D: had 198.82 GiB free. Ollama 0.40.18 installed the single approved tag
`qwen2.5-coder:3b`. Its API reported 1,929,912,626 bytes of weights and metadata,
Q4_K_M quantization, and digest
`f72c60cabf6237b07f6e632b2c48d533cef25eda2efbd34bed21c5e9c01e6225`.

The evaluation used process environment settings for the model tag, Ollama
provider, `http://127.0.0.1:11434`, 30-second socket timeout, and
`SENTINEL_DIAGNOSIS_ALLOW_TEST_FALLBACK=false`. Stage deadlines used the existing
120-second monotonic budget. Both runs used the pinned 384-dimensional BGE
encoder and the unchanged nine labeled cases. The existing evaluator ran first.
The same prepared fixture data then ran through one D4B spawned worker at a time,
using the existing provider and service with timing instrumentation. The JSON
observations, source-bound evidence, runner and resource samples are under ignored
`.tools/d5a-live-257a792e/`.

The initial API smoke request hit the 30-second limit. Ollama logged that the
client disconnected during model warmup and that it aborted loading. The two
reasoning calls in the existing evaluator each hit the socket timeout at about
30.02 seconds and returned `LLM_UNAVAILABLE`. In the separate worker run, both
reasoning calls returned real responses through Ollama and passed the existing
response checks. The runs used identical limits, and the difference has not been
isolated to a single cause.

| Case | Expected | Existing evaluator | Worker observation | Worker elapsed | Ollama call |
| --- | --- | --- | --- | ---: | ---: |
| `missing_key` | Complete | Review, provider timeout | Model requested review. It identified `name` as missing but attributed the key to the prompt envelope instead of the `profile` input. `app.py:1–2` resolved. | 26.484 s | 22.438 s |
| `zero_division` | Complete | Review, provider timeout | Model requested review. It identified a zero denominator but also incorrectly proposed a zero numerator as a cause. `arithmetic.py:1–2` resolved. | 12.218 s | 8.672 s |
| `key_not_supported` | Review | Review | `REPORTED_KEY_NOT_SUPPORTED` | 3.547 s | — |
| `contradictory_exception` | Review | Review | `CONFLICTING_ERROR_TYPES` | 3.625 s | — |
| `missing_stack_file` | Review | Review | `UNRESOLVED_STACK` | 3.047 s | — |
| `unassessed_language` | Review | Review | `LANGUAGE_NOT_EVALUATED` | 3.125 s | — |
| `malformed_source` | Review | Review | `SOURCE_CONTEXT_INCOMPLETE` | 3.062 s | — |
| `malformed_trace` | Review | Review | `MALFORMED_LOG` | 1.687 s | — |
| `no_source` | Review | Review | `INSUFFICIENT_EVIDENCE`, with `UNRESOLVED_STACK` also recorded | 1.766 s | — |

Live worker results matched **7/9 status labels (77.8%)**. All **7/7 expected
reviews** were routed to review before inference. Neither of the **two cases
expected to complete** did so. Human review found the expected missing key and
zero-denominator observations somewhere in **2/2** responses. Using a stricter
rubric that requires the cause to be correctly grounded and free of unsupported
alternatives, **0/2** were clean diagnoses. Both contained unsupported or incorrect
claims. No claims of completed repairs or executed tests were observed. These
counts describe this fixture set, which supplied only two live model responses.

Both live worker responses passed structured validation. All **7/7** labeled source
files were retrieved where a file label existed. All **7/7** provenance references
and **2/2** returned citations independently resolved against the sealed source
revision and matching content. A valid source reference can still accompany a
false causal claim, as the zero-numerator hypothesis demonstrates. All nine
results matched `fixture-v1`, all source digests and all 28 fixture database
table row counts stayed unchanged, and no result used test fallback.

### Performance and cancellation

- Worker startup to factory entry took **1.343–1.984 s**. Native embedding
  initialization took **1.141–1.485 s** across seven workers that loaded the
  encoder. The standalone evaluator initialized the encoder in 2.422 s.
- The two successful Ollama calls averaged **15.555 s**. Across all nine
  worker cases, median elapsed time was **3.125 s**, with a maximum of
  **26.484 s**. All nine returned before 120 seconds and were reaped.
- The host had 15.73 GiB physical RAM and an RTX 3050 Laptop GPU with 4 GiB
  VRAM. Across 117 system samples, available RAM fell from about **5.26 GiB**
  at run start to **4.26 GiB** at its lowest sampled value. Peak reported GPU
  allocation was **2,155 MiB**, and minimum free VRAM was **1,808 MiB**.
  These are system samples and may miss peaks between readings.
- A separate probe with a 0.1-second socket timeout returned `provider_timeout`
  after 110 ms in the provider, with `LLM_UNAVAILABLE` and manual review. A
  separate 250 ms stage probe rejected the result and terminated the worker.
  The call returned after 750 ms including termination grace and cleanup.
  Neither probe changed the normal evaluation limits.
- Cancellation requested at entry to the real provider phase propagated after
  **532 ms** with no active Diagnosis child left. Ollama still listed the model
  as loaded. Server-side cancellation of token generation was not established.

### Recommended improvements

1. Add direct checks that each hypothesis is supported by its cited lines. Cover
   prompt-envelope echoes, a zero numerator cited as a division-by-zero cause,
   and the distinction between an observed exception and inferred runtime input.
2. Test a prompt asking for the strongest supported hypothesis first and for
   alternatives only when evidence supports them. Track correct review decisions
   alongside correct completions to catch regressions in cautious behavior.
3. Benchmark cold and already-loaded inference separately under the same limits.
   Test a readiness or model preload step before admitting diagnosis work, and
   compare a shorter response budget. The initial timeout occurred during warmup.
4. Expand the labeled positive cases before deciding model readiness. D4C still
   needs joint decisions on canonical schema and migrations, revision/log/artifact
   custody, persistence, and final execution acceptance.

### Regression checks and workspace verification

On November 26, Ruff lint and formatting passed across the backend (155 files)
and the local measurement runner. The first full pytest run with a retained
summary returned **342 passed and 1 failed in 179.38 s**. The persisted-dashboard
browser check hit its existing 10-second navigation timeout. The Diagnosis,
worker, and HTTP transport checks passed in that run. The prior session's final
pytest output was unavailable when work resumed.
The unchanged full-suite retry passed **343 tests in 178.00 s**, including the
persisted-dashboard check. Both logs are retained in `.tools/d5a-live-257a792e/`.

Branch `Diagno-Agent` remains at `ee4e6516db0da14b821e678434e96bdd2c96f035`.
The 401-file preservation check found only this report changed. Existing frontend
edits, the shared SQLite database, and migrations matched their pre-run hashes.
The `main` and `manager-backend` refs matched their starting values. The report
and ignored local evaluation artifacts remain uncommitted.
