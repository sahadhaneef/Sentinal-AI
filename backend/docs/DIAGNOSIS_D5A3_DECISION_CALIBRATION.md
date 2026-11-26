# D5A.3 diagnosis decision calibration

## Why D5A.2 routed the original cases to review

The retained D5A.2 worker records contain six valid replies for the two original
positive cases. Each cited the failing source line, named the missing key or
zero divisor, and set `needs_manual_review=true`. The assessments contained no
rejection codes, and neither fallback nor partial retrieval forced review. The
provider's review flag determined the disposition. The input provenance was
unknown, which was legitimate uncertainty. The available observations supported
the immediate failure. The records do not reveal why the model chose the flag or
prove prompt ambiguity as a cause.

## Decision policy

The Ollama prompt now gives an explicit condition for each value of
`needs_manual_review`. Completion requires a specific immediate cause tied to
the observed exception and cited failing operation, consistent evidence, and a
concrete investigation step grounded in that cause. The model must record any
unknown upstream origin separately. A grounded investigation step can check the
failing input or invariant. It conveys no authorization to generate or apply a
repair. Missing or conflicting evidence, ambiguous operations or operands,
unverifiable citations, and lack of a supported direction require review.

The public schemas, result mapping, worker deadline, fallback, and evidence
validators are unchanged. The service still respects an explicit model review
and validates the presence and safety of the direction. That validator cannot
establish that every natural-language direction is semantically justified, so
the evaluation inspects direction and causal claims separately.

## Evaluation design

The nine originals, three D5A.1 holdouts and six D5A.2 cases were carried forward
unchanged. The six fresh fixtures were labeled before calling the model:

| Case | Predefined disposition | Reason |
| --- | --- | --- |
| Unknown upstream origin | Complete | The stack line and exception identify the zero divisor; the caller origin is unknown. |
| Upstream assignment | Complete | The preceding local assignment establishes why the named divisor is zero. |
| Unknown operand value origin | Review | The expression uses a dynamic lookup; the failing key and value provenance are absent and the named-divisor rule is conservative. |
| Misleading arithmetic | Review | The reported stack line is subtraction and the division is unreachable. |
| Conflicting lookup | Review | The exception names a different key from the failing line. |
| No supported direction | Review | The trace stops at an opaque callback. The source neither localizes the failure inside it nor supports a specific fix. |

All scored worker trials use Ollama 0.40.18, the installed
`qwen2.5-coder:3b`, real pinned BGE embeddings, a 30-second socket timeout,
a 120-second stage budget, and disabled fallback. The two original positive
cases have three scored worker trials each. A separately reported matched
cold/warm pair measures residency effects on the same missing-key input.

## Separation and publication

- D5A.3 adds the decision prompt refinement, its transport assertions, three
  service contract cases, the fresh fixture, and this report. Prior D5A.1 and
  D5A.2 also changed the prompt and transport file.
- A reviewed D5 publication can separate the live baseline report from the
  cumulative standalone quality changes, fixtures, tests and verification
  reports. Stage shared prompt and test hunks by phase only if a valid phase
  snapshot is available. Keep generated evaluation data outside Git.
- D4C has its own adapter, tests and contract documents. Publication still
  requires approval of trusted supervised invocation identity and the scoped
  manifest reader. Preserve the separate migration and atomic result acceptance
  decisions for Manager. No joint branch, commit or push was created.

## Live results

| Worker metric over distinct cases | D5A | D5A.1 | D5A.2 | D5A.3 |
| --- | ---: | ---: | ---: | ---: |
| Original status agreement | 7/9 | 8/9 | 7/9 | 9/9 |
| Completed original positives | 0/2 | 1/2 | 0/2 | 2/2 |
| Original expected reviews | 7/7 | 7/7 | 7/7 | 7/7 |
| D5A.1 holdout status agreement | — | 3/3 | 1/3 | 2/3 |
| D5A.2 set status agreement | — | — | 4/6 | 5/6 |
| D5A.3 fresh status agreement | — | — | — | 5/6 |

Status agreement was 21/24 distinct cases and 25/28 scored worker trials.
The separate in-process evaluator matched all first worker dispositions
and called Ollama 15 times. Skipped prechecks are not model responses.

The table records all scored isolated requests in order. Measurements are in
milliseconds. C = completed and R = manual review. Retrieval subtracts
query embedding time from the hybrid retrieval duration, so the columns do
not sum to total. Validation includes D2 citation verification and D3 quality
policy. Dashes indicate unmeasured or skipped work.

| Case | Label → result | Total | Startup | Embed init | Retrieval | Inference | Validation |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| missing_key | C → C | 6484 | 1500 | 1125 | 16 | 3312 | 32 |
| zero_division | C → C | 5843 | 1297 | 1125 | 30 | 2734 | 16 |
| key_not_supported | R → R | 3593 | 1547 | 1469 | 47 | — | 15 |
| contradictory_exception | R → R | 3407 | 1688 | 1094 | 15 | — | 15 |
| missing_stack_file | R → R | 3578 | 1782 | 1218 | 32 | — | 16 |
| unassessed_language | R → R | 3109 | 1234 | 1282 | 15 | — | 16 |
| malformed_source | R → R | 3813 | 2063 | 1219 | 31 | — | 15 |
| malformed_trace | R → R | 1890 | 1390 | — | 0 | — | 0 |
| no_source | R → R | 2281 | 1906 | — | 16 | — | 0 |
| holdout_region | C → C | 6140 | 1422 | 1203 | 31 | 2953 | 31 |
| holdout_capacity | C → R | 5968 | 1421 | 1063 | 47 | 2844 | 31 |
| holdout_default | R → R | 3406 | 1562 | 1328 | 16 | — | 15 |
| ind_modulo | C → C | 5813 | 1594 | 1079 | 31 | 2610 | 30 |
| ind_lookup | C → R | 6203 | 1344 | 1046 | 32 | 3297 | 31 |
| ind_index | C → C | 5921 | 1281 | 1031 | 31 | 3062 | 47 |
| ind_null | C → C | 5656 | 1328 | 1063 | 30 | 2734 | 32 |
| ind_mislead | R → R | 7250 | 1453 | 1562 | 31 | 3531 | 32 |
| ind_ambiguous | R → R | 6484 | 1672 | 1078 | 31 | 3234 | 16 |
| cal_unknown_origin | C → C | 6204 | 1282 | 1078 | 15 | 3328 | 15 |
| cal_upstream | C → R | 6594 | 1672 | 1218 | 47 | 3094 | 47 |
| cal_unknown_operand | R → R | 6297 | 1344 | 1281 | 15 | 3078 | 47 |
| cal_misleading | R → R | 5891 | 1312 | 1078 | 31 | 2984 | 16 |
| cal_conflict | R → R | 3281 | 1312 | 1281 | 16 | — | 16 |
| cal_no_direction | R → R | 6562 | 1703 | 1188 | 15 | 3140 | 16 |
| missing_key repeat 2 | C → C | 6328 | 1547 | 1094 | 31 | 3156 | 31 |
| zero_division repeat 2 | C → C | 5313 | 1250 | 1032 | 31 | 2515 | 32 |
| missing_key repeat 3 | C → C | 6297 | 1578 | 1125 | 16 | 3031 | 47 |
| zero_division repeat 3 | C → C | 5500 | 1266 | 1125 | 16 | 2609 | 48 |

### Causal and disposition review

- All 14 labeled review cases stayed in review. The previous misleading
  and ambiguous arithmetic claims again failed operand validation. The fresh
  dynamic divisor and misleading arithmetic claims also failed validation.
  The conflicting key was rejected before inference. The opaque callback
  drew review from the model because its implementation was absent.
- Three scored positive trials went to review. The header case correctly
  identified the missing key, gave a reasonable investigation step, and still
  set the model review flag. The capacity case both requested review and
  failed the narrow check because it inserted “parameter in the fill
  function” between the responsible name and “is zero.” Its immediate cause
  was semantically supported. The local assignment case omitted zero from
  its hypothesis and speculated that the cited initialized variable might
  be uninitialized. The quality gate correctly rejected that draft. Across scored and timing
  workers, there were three clear model-only unnecessary reviews (header
  lookup and both timing trials), one model-plus-validator review despite a
  supported immediate cause (capacity), and one justified review of a draft
  that failed to express the available cause (local assignment).
- In all 14 scored positive trials, the draft and cited failing line
  together identified the operation and responsible operand, receiver or key.
  The model's immediate causal explanation was supported in 12/14 positive
  trials. The local assignment lacked a supported causal statement and the
  index case overclaimed upper-bound polarity. Of 11 completed worker trials,
  10 had a supported immediate hypothesis. This count does not imply fully
  calibrated uncertainty or overall diagnostic accuracy.
- One completed result contained an unsupported specific causal claim.
  The index exception and source support an out-of-range `position`, but
  cannot establish that `position >= len(queue)`. A sufficiently negative
  index also fits. The verified citation did not prevent this overclaim.
- Uncertainty remained a weakness. The three scored division responses
  called the divisor's exact value unknown while asserting it was zero.
  The fresh unknown-origin case had the same mismatch for `samples`.
  Modulo and null responses restated immediate conditions instead of identifying
  remaining upstream uncertainty. The scored missing-key drafts suggested
  generic upstream possibilities without establishing any of them. The two
  matched timing trials stated the unknown origin more clearly and both
  unnecessarily requested review. Including these separately run observations,
  missing key completed 3/5 times, division completed 3/3, and completion
  totaled 6/8 across both originals.
- All 19 scored returned citations resolved and verified against the exact
  revision. All 28 scored workers met deadline, were reaped, and left fixture
  sources and fixture database row counts unchanged. No scored run returned
  a provider timeout, stage timeout, or worker-process failure. No fallback
  was used. Separate fault probes classified provider timeout and stage
  expiry and propagated cancellation. These probes are outside status scores.

### Matched cold and warm missing-key performance

| Measure | D5A.2 cold | D5A.2 warm | D5A.3 cold | D5A.3 warm |
| --- | ---: | ---: | ---: | ---: |
| End to end, seconds | 10.062 | 6.359 | 9.938 | 5.375 |
| Inference, seconds | 7.203 | 2.735 | 7.016 | 2.500 |
| Embedding initialization, seconds | 1.016 | 1.000 | 1.031 | 1.047 |
| Disposition | Review | Review | Review | Review |

Across scored workers, startup took 1.234–2.063 seconds, embedding init
1.031–1.562 seconds when measured, and active inference 2.515–3.531 seconds.
Retrieval outside embedding took up to 47 ms and measured validation up to
48 ms. Total latency was 1.890–7.250 seconds.

Ollama residency was checked before each timed request. The cold API smoke
was successful at 5.593 seconds and is separate from the matched diagnosis.
Across 191 sampled measurements, host RAM availability was 3.37–4.89 GB and
reported GPU allocation peaked at 2155 MiB. No other model was downloaded.
Raw output, timings and source checks are retained under ignored
`.tools/d5a3-live/`.

## Prototype recommendation

Use the installed model for supervised triage, even when it returns
`completed`. The observed review variability, unsupported bound inference
and contradictory uncertainty make automatic routing to repair unsuitable.
This closes the planned standalone calibration cycle. Reassess the evidence
and completion contract with Manager and Repair owners before exposing
completed results as a workflow gate.

## Automated verification

Ruff lint passed and Ruff format check passed for all 161 Python files.
Full backend pytest passed **385 tests in 145.24 seconds**, including the
new decision contract cases and existing live frontend/API, schema comparison,
source baseline, and frontend adapter regressions. The focused coverage proves
that unknown upstream cause can coexist with an accepted completed result, an
explicit model review still takes effect, and missing direction still triggers
review. Existing unsupported-claim, ambiguous evidence, invalid citation,
transport and deadline tests passed.

The workspace remained on `Diagno-Agent` at
`ee4e6516db0da14b821e678434e96bdd2c96f035`, matching its local tracking ref.
Hashes matched the preservation manifest for all 161 checked frontend,
database and migration paths. Local `main`, its tracking ref, and the tracked
`manager-backend` ref stayed at their prior SHAs.

## Operator observations from raw Ollama

The operator separately tried the installed `qwen2.5-coder:3b` model in
Ollama. They observed a correct missing-dictionary-key explanation, speculative
causes when evidence was thin, a division-by-zero explanation despite a nonzero
denominator, incorrect assumptions about list index bounds, and susceptibility
to instructions in application logs. These observations did not exercise the
complete Diagnosis Agent. They do not establish a pipeline failure or change
any scored D5A.3 results above. Retain this model for supervised triage and
require human diagnosis review before routing to Repair.

## D5B integration acceptance requirements

| Area | Existing coverage | Acceptance coverage still needed |
| --- | --- | --- |
| Misleading evidence | The operand policy tests wrong, missing and ambiguous divisors and a cited non-division line. Scored isolated cases also exercised misleading and ambiguous arithmetic. | Exercise contradictory runtime operand observations through the authorized log reader, worker and result boundary. A verified source citation must not allow a diagnosis that claims zero when the trusted runtime observation establishes a nonzero divisor. |
| Contradictory claims | The labeled evaluator tests conflicting exception types. Quality tests reject unsupported certainty and invalid narrative citations, including in uncertainty. | Exercise a draft whose supported finding and uncertainty contradict each other. Include index failures where the source and trace do not establish which bound was exceeded. Assert that an unsupported specific cause cannot qualify for repair routing. |
| Untrusted content | The synthetic HTTP test checks the system instruction to ignore embedded instructions, schema-bound replies, no declared tools and rejection of tool-call replies. The quality service rejects claims about the prompt envelope, invented citations and purported execution. | Exercise untrusted log and source content through the full worker and Manager acceptance path. Test both controlled provider replies and the configured live model. Verify that embedded instructions supply no execution authority, cannot substitute for source evidence and cannot trigger repair. Record model behavior and pipeline disposition separately. |
| Human review | Standalone tests preserve explicit model review and validate diagnosis shape. | Jointly approve and test the human diagnosis review gate before Repair, independent of model completion. Keep this separate from D4C trusted invocation and scoped manifest-reader approvals. |

D5B acceptance coverage is proposed for integration. No new reasoning phase,
model changes or Manager workflow changes were made during publication review.
