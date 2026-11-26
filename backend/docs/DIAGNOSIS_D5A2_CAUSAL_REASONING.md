# D5A.2 causal reasoning and operand verification

## Baseline and diagnosis of the division miss

| Metric | D5A | D5A.1 | D5A.2 |
| --- | ---: | ---: | ---: |
| Original status agreement | 7/9 | 8/9 | 7/9 |
| Original positive cases completed | 0/2 | 1/2 | 0/2 |
| Original review cases kept in review | 7/7 | 7/7 | 7/7 |
| Existing holdout status agreement | — | 3/3 | 1/3 |
| Independent status agreement | — | — | 4/6 |

D5A.1 retrieved and verified the exact revision and matching division line,
`arithmetic.py:1–2`, containing `return numerator / denominator`. The raw
model statement repeated that division by zero occurred in `divide` but
omitted the responsible divisor. Its own uncertainty field requested review.
The citation passed and the assessment had no rejection issues. The immediate
operand was inferable from the exception and source, while the runtime
assignment that made it zero was unknown. The record establishes a model
response and review decision failure. It does not isolate prompt effects
from model limitations.

D5A.2 names the failing operation and expression in the prompt, explicitly
allows bounded immediate diagnoses with unknown upstream causes, and retains
evidence, uncertainty, and review requirements. For Python zero-divisor
claims, the quality policy checks the innermost stack frame against cited
source and requires exactly one matching division, floor-division, or modulo
operation with a named divisor and a claim linking that name to zero. Missing,
ambiguous, or mismatched operands cause review. Citation validation still
binds evidence to the correct revision, source path, excerpt and lines.
These checks are conservative. Complex divisor expressions and copied
exception text may require review, and there is no general proof of claims
about arbitrary runtime state. Existing key checks remain in place. Index
and attribute cases exercise the prompt and existing grounding controls.

## Live results

Ollama 0.40.18, qwen2.5-coder:3b Q4_K_M, real BGE small English v1.5
embeddings, fallback disabled. The socket timeout was 30 seconds and the
full worker stage deadline was 120 seconds. An in-process comparison agreed
with the first isolated run for every case. C = completed, R = manual review.
Times are milliseconds. The second and third trials are repeated worker
requests, so there are 22 scored executions across 18 cases.

| Case | Group | Expected → observed | Total | Startup | Embedding init | Retrieval excluding query embedding | Inference | Validation |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Missing key 1 | Original | C → R | 7282 | 1813 | 1594 | 46 | 3172 | 31 |
| Zero division 1 | Original | C → R | 6672 | 1594 | 1250 | 15 | 3187 | 47 |
| Unsupported key | Original | R → R | 3375 | 1532 | 1250 | 30 | — | 16 |
| Contradictory exception | Original | R → R | 3313 | 1469 | 1281 | 47 | — | 0 |
| Missing stack file | Original | R → R | 3375 | 1484 | 1313 | 30 | — | 16 |
| Unassessed language | Original | R → R | 3063 | 1453 | 1094 | 31 | — | 0 |
| Malformed source | Original | R → R | 3047 | 1407 | 1125 | 30 | — | 0 |
| Malformed trace | Original | R → R | 1969 | 1469 | — | 0 | — | 16 |
| No source | Original | R → R | 1906 | 1484 | — | 16 | — | 0 |
| Region lookup | Prior holdout | C → R | 6219 | 1532 | 1171 | 32 | 3000 | 15 |
| Capacity division | Prior holdout | C → R | 6594 | 1204 | 1031 | 31 | 3828 | 31 |
| Defaulted lookup | Prior holdout | R → R | 2781 | 1328 | 984 | 16 | — | 15 |
| Modulo | Independent | C → C | 5843 | 1187 | 1015 | 47 | 3125 | 31 |
| Header lookup | Independent | C → R | 6593 | 1250 | 1047 | 32 | 3766 | 31 |
| Invalid index | Independent | C → R | 6031 | 1265 | 1000 | 16 | 3250 | 16 |
| Null attribute receiver | Independent | C → C | 5703 | 1328 | 1016 | 47 | 2797 | 31 |
| Misleading operation | Independent | R → R | 6203 | 1218 | 1000 | 32 | 3516 | 30 |
| Ambiguous arithmetic | Independent | R → R | 6328 | 1250 | 1031 | 32 | 3547 | 16 |
| Missing key 2 | Original repeat | C → R | 5828 | 1234 | 1016 | 15 | 3000 | 16 |
| Zero division 2 | Original repeat | C → R | 5703 | 1297 | 1000 | 31 | 2922 | 15 |
| Missing key 3 | Original repeat | C → R | 5625 | 1219 | 1000 | 16 | 2922 | 32 |
| Zero division 3 | Original repeat | C → R | 5703 | 1203 | 1016 | 47 | 2953 | 16 |

All three key trials identified the missing `name` lookup. All three
division trials named `denominator` as zero. All six had verified citations
and no quality-policy rejection issues. The model still set
`needs_manual_review=true` in all six. The region, header and index cases
also returned plausible immediate causes with review requested. The
capacity case cited the correct operation but did not establish that its
divisor was zero in the hypothesis. The misleading case cited unrelated
division and the ambiguous case attributed the failure to one of two
divisions without distinguishing evidence. Both latter claims were downgraded
even though the model requested completion.

Across the 22 worker trials, 14/14 returned citations verified. The only
completed results were the modulo and null cases. Both supported the
immediate failure and no unsupported causal claim was observed in completed
results. All 22 workers met the deadline, were reaped, and left fixture
sources unchanged. Fixture database row counts matched before and after.
The separate short-timeout probes observed provider timeout, propagated
cancellation, and stage timeout with no deterministic fallback.

## Performance and local resource observations

Startup is request-to-factory entry. Embedding initialization occurs within
the measured stage and is included in query embedding timing. The retrieval
column subtracts the measured query embedding time from hybrid retrieval.
Validation covers D2 citation and D3 policy work. Durations are measured
independently and exclude some orchestration and shutdown overhead, so they
do not sum to total. A recorded zero can reflect measurement granularity.

The unloaded-model smoke took 5.984 seconds end to end, including 5.555
seconds reported by Ollama to load. The smoke was a short health request.
The scored workers ran after the model was loaded. A separate matched pair
on the same missing-key input verified model residency before each request.
Cold/warm totals were 10.062/6.359 seconds, provider times were
7.203/2.735 seconds, and embedding initialization took 1.016/1.000
seconds. Both correctly identified the lookup and requested review.
In D5A.1 the matched
cold/warm provider durations were 10.484/3.657 seconds and the embedding
initialization durations were 2.078/7.860 seconds. The 22 D5A.2 scored
workers initialized embeddings in 0.984–1.594 seconds where applicable.
The earlier 7.860 seconds did not recur. Each worker initializes its own
embedding runtime, so Ollama residency does not control that cost. These
measurements do not establish why that D5A.1 trial took longer.

The host had 16.89 GB total RAM and 4096 MiB GPU memory. Across 146 samples,
available host RAM ranged from 2.94 to 4.36 GB and reported GPU memory usage
peaked at 2155 MiB. These are sampled host measurements, without per-worker
attribution. No additional model was downloaded.

## Change inventory and readiness

- D4C remains on publication hold. Its adapter, adapter tests, contract review,
  integration plan and Manager handoff are separate. Delvin still needs to
  approve the trusted invocation and scoped manifest-reader interfaces.
- D5A and D5A.1 retain their evaluation reports. D5A.1 owns the existing holdout
  fixture and the preceding prompt, evidence and transport changes.
- D5A.2 adds this report and the independent fixture. Its incremental code spans
  the reasoning prompt, evidence policy and service, and focused quality and
  provider tests. Shared files contain changes from both evaluation phases.
  The raw local JSON and timing records are under the ignored
  `.tools/d5a2-live/` directory.

The current model is suitable for supervised prototype investigation. It
does not meet the completion consistency target. Keep manual review enabled.
The next experiment should use a fresh validation set to test clearer review
criteria for source-supported immediate causes, with a separate score for
operand correctness and final disposition.

## Automated verification and preservation

- Ruff lint passed. Ruff format check passed for all 159 Python files.
- Full backend pytest passed with 382 tests in 147.87 seconds, including
  the live frontend API, schema comparison, source baseline, and live
  frontend adapter regressions.
- The D5A.1 prompt transport assertions still verify that embedded
  instructions are ignored and envelope format is separate from runtime
  inputs. The focused tests also check the causal instructions and cover
  supported, wrong, missing and ambiguous divisor claims.
- Hashes matched the preservation manifest for 161 protected frontend,
  migration and database paths. The working branch and its tracking ref
  remained at `ee4e6516db0da14b821e678434e96bdd2c96f035`. Local `main`
  and its tracking ref remained at `2eae39468f34a694f39b110d4aef6caff8b591a1`.
  No commit or push was made.
