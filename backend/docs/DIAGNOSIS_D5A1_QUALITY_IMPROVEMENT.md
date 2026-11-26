# D5A.1 quality evaluation

On `Diagno-Agent` at `ee4e6516`, the original nine fixtures improved from
**7/9 to 8/9 status matches**. Manual inspection found **one clean causal
diagnosis among two live responses**, up from zero in the D5A baseline.
The seven expected reviews still exited before inference. The original division
case still requested review. These are counts for small synthetic sets.

The revised prompt separates application inputs from the message format,
asks for a concise operation-and-operand explanation with citations, and
requires evidence for alternatives. The quality check flags prompt framing
presented as the cause and zero-numerator claims tied to simple cited
division. The checks cover these narrow patterns and do not prove arbitrary
causal claims. Existing evidence, manual-review, and runtime safeguards remain
in effect. The original D5A report and data remain separate.

The evaluation used Ollama 0.40.18, the installed `qwen2.5-coder:3b` tag
(digest prefix `f72c60cabf62`), real pinned BGE embeddings, fallback disabled,
the 30-second socket timeout and one isolated worker per case with a 120-second
stage budget. The stand-alone evaluator and worker pass both covered the
original nine and the predefined three-case
[holdout](../fixtures/diagnosis-quality-holdout.json). Reports, runner and raw
responses are retained locally under ignored `.tools/d5a1-live/`.

| Case | Worker outcome | Evidence and causal assessment |
| --- | --- | --- |
| Original missing key | Completed | Correctly connects the missing name key to the cited profile lookup. D5A instead discussed the prompt envelope. |
| Original division | Manual review | Cites the division and repeats the exception, but fails to identify the denominator. The unsupported numerator hypothesis from D5A is absent. |
| Unsupported key | Manual review | Reported failure is unsupported by the cited safe lookup. |
| Contradictory exception | Manual review | Error types conflict. |
| Missing stack file | Manual review | Stack file could not be resolved. |
| Unassessed language | Manual review | Language policy stopped inference. |
| Malformed source | Manual review | Source context was incomplete. |
| Malformed trace | Manual review | Trace could not be parsed. |
| No source | Manual review | Evidence was insufficient. |
| Holdout region | Completed | Correctly identifies the missing region key. Its uncertainty speculates about a typo or configuration file without evidence. |
| Holdout capacity | Completed | Correctly identifies zero capacity as the divisor. Its uncertainty field was merely “medium” and needs clearer explanation. |
| Holdout default lookup | Manual review | Safe lookup does not support the reported missing-key cause. |

Holdout status agreement was **3/3**. Both positive holdouts had the expected
causal hypothesis, with the uncertainty limitations above. No unsupported
causal hypothesis was accepted in these runs. All four returned citations
verified, and all 12 worker cases met the stage deadline. The runner verified
unchanged fixture source and database row counts and reaped every worker.

Cold smoke after requesting model unload took **9.032 s**, including **8.554 s**
of API-reported loading time. It used a short schema and is a cold initialization
observation, not a cold diagnosis benchmark. Subsequent already-loaded model
calls in the worker took **3.390 s** and **3.094 s** for the two originals,
versus **22.438 s** and **8.672 s** in D5A. The two holdout calls took
**3.235 s** and **3.390 s**. The earlier D5A cold and socket timeouts remain
recorded. Host conditions and output lengths varied, so the comparison cannot
isolate a prompt effect. Across 79 resource samples, minimum available RAM was
3.09 GiB and peak reported GPU allocation was 2,155 MiB.

Separate probes reported a provider timeout at the 0.1-second socket setting,
578 ms cancellation cleanup with no remaining child, and stage expiry for a
250 ms stage probe (766 ms including cleanup). Ollama-side termination cannot
be inferred from worker cancellation.

Keep this model for further local review. The original division miss and weak
uncertainty text keep it short of the D5A.1 targets. Next, evaluate additional
operand and exception families, validate the meaning of uncertainty fields,
and repeat cold diagnosis timing under the original limits.

D5A.1 inventory: `reasoning/providers.py`, `quality/evidence.py`,
`tests/diagnosis/quality/test_quality.py`,
`tests/diagnosis/reasoning/test_local_provider.py`, the holdout fixture, and
this report.
The D4C trust proposal and its existing code and tests remain a separate scope.

The initial full regression run returned 376 passes and one failure. The
transport test matched wording from the previous system prompt. Its assertion
now checks the revised embedded-instruction rejection and explicit separation
of message format from runtime input. JSON schema and tool checks are retained.

The full rerun passed **377 tests in 137.29 seconds**, including 32 D4C adapter
tests, both new quality cases, and browser/HTTP integration regressions. Ruff
lint and formatting passed.

A matched follow-up ran the same indexed missing-key diagnosis with model
residency checked through Ollama before each request. Both attempts completed
with the cited profile lookup. The cold provider call took **10.484 s** and
the already-loaded call took **3.657 s**. End-to-end times were **20.234 s**
and **32.531 s**, respectively. Embedding initialization was **2.078 s**
cold and **7.860 s** warm, so the provider speedup did not translate to a
whole-worker speedup in this single pair. Raw timing data is in
`.tools/d5a1-live/temperature-comparison.json` and its two timing files.
