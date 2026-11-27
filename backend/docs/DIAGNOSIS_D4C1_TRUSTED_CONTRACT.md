# D4C.1 trusted contract verification

Base commit: 132e81ff718c56dacd7d222d46c14a42df74ef36 (Diagno-Agent).

| Contract | Diagnosis implementation | Remaining dependency |
| --- | --- | --- |
| Invocation identity | Frozen context with the approved twelve fields. The supervisor retains its own serialized copy, constructs the worker request from it, awaits the result of that call, and checks the result scope. | Manager must supply authentic admission and worker instances. An atomic Manager acceptance operation must arbitrate duplicate admission handles, cancellation, supersession and persistence. |
| Invocation lifecycle | Single-use per supervisor object, active-state checks before dispatch and after return, and the earlier of the wall-clock and monotonic deadlines. D4B enforces its own cap and cleanup. | Manager must implement the authoritative current-state port and atomic final acceptance. The local check does not close a race between checking and accepting. |
| Revision registration | Frozen registered revision DTO and comparison of all four returned scope coordinates plus the immutable revision string. | Canonical revision lookup must be implemented by Manager. The local revision-reader signature is a Diagnosis port, pending wiring. |
| Manifest read | Reads only by authorized coordinates. Checks artifact ID, declared size, metadata digest, and independently hashes exact stored bytes against the registered lowercase SHA-256. | Manifest body schema and source-file read contract are unspecified. The helper returns verified bytes only. Schema, entries, per-file digest, and manifest-to-citation binding remain gated. |
| Artifact read | Compares all available scope coordinates to admission before reading and validates returned artifact ID, size and digest against an independently supplied expected SHA-256. | Manager must enforce artifact scope and provide authoritative digest metadata. The response DTO has no scope coordinates, so it cannot independently prove authorization or distinguish identical bytes returned from a foreign scope. |
| Compatibility | Existing public Diagnosis contracts, D4B process isolation, timeouts and retry classification remain intact. | The legacy local D4C binder accepts caller-supplied origin and digest assertions. Do not use it as a trusted production boundary. No real Manager registration was performed. |

The tests exercise tampered manifest bytes and metadata, missing registration,
revision and scope mismatches, artifact scope and size rejection, and two real
spawned-worker runs with active and invalidated admissions. Duplicate calls
on the same supervisor object are rejected. Completion across independent
admission handles, real Manager result acceptance, manifest schema rejection,
conflicting and missing file entries, and per-file integrity have not been
verified. Do not treat byte verification as approval to consume file entries.

The approved D5A evaluation and supervised-triage recommendation remain in
effect. The proposed human diagnosis review gate before Repair and D5B
acceptance checks remain pending. Windows browser navigation, the native Node
exit and diagnostic stderr decoding remain separate unresolved limitations.

## Proposed inventory

- app/agents/diagnosis/quality/trusted_contract.py
- tests/diagnosis/quality/test_trusted_contract.py
- docs/DIAGNOSIS_D4C1_TRUSTED_CONTRACT.md

The pre-existing unpublished adapter and its tests remain local and are excluded from the candidate. Manager docs, the frontend, published D5A reports and
shared migrations were outside this change.

## Actual verification

- Windows Ruff lint and format check passed (163 files).
- Windows focused pytest passed 45 tests in 40.17 seconds, including all
  21 D4B worker cases and 24 D4C.1 cases.
- Linux Docker Ruff lint and format passed (162 files). The full backend
  suite passed 409 tests in 136.23 seconds, including the live browser/API
  adapter and schema checks. The known D5A committed image was reused with
  only the two unpublished D4C code files and their two test files overlaid.
- No stage, commit, push, integration branch, shared migration, or Manager
  registration was performed. D4C.1 is verified to the supplied boundary
  contracts. Full acceptance remains open for the gaps above.

## Security review and publication boundary

The legacy alignment module has one result-binding entry point that accepts
unproven assertions. Its inputs include caller-constructed admission, origin
scope, revision registration, outcome, local cutoff, manifest reference and
manifest digest. Its DTO validators check shape and its binder compares these
values. Those checks provide correlation but cannot establish their origin.
A local regression demonstrates that mutually consistent assertions can yield
a bound result without any supervised invocation or independently read bytes.

Repository call-site inspection found only the local legacy tests calling the
binder. No tracked Manager registration or standalone entry point selected it.
The new module previously imported the legacy scope validator. It now uses
the published opaque-token validator and applies the same moving-alias
restriction itself. The dependency-complete publication candidate is the
three files listed above. Keep the legacy binder, its regression tests and
earlier D4C drafts local. Existing published standalone behavior and the
existing Manager wire projection remain outside these changes.

The trusted supervisor serializes admission independently of output and
constructs the worker request itself. It does not accept a supplied outcome,
origin, or manifest digest on its run call. It checks admission state and the
deadline before dispatch and after return, and rejects fallback or
side-effect-bearing quality output. This establishes local correlation and
single-use semantics within one trusted supervisor object. Manager must
control construction, worker selection, repository providers and
cross-supervisor atomic acceptance. The verifier functions have no fallback
reader. The supervisor result is an intermediate value and carries no proof
that Manager has verified its manifest, artifact scope or evidence entries.

## Questions for Delvin

1. What component mints and retains the admission, supervises worker selection,
   and supplies the trusted current-state check?
2. What atomic operation compares execution, attempt, invocation, deadline
   and cancellation with the active admission and persists acceptance exactly
   once, including retry and supersession races?
3. What is the versioned manifest body schema, including canonical file paths
   and duplicate-entry handling? What scoped source-file operation binds
   returned bytes to each verified manifest entry?
4. What independent registry provides an artifact's expected digest and
   admitted scope, how is it bound to the immutable read, and what byte
   limits and missing or unauthorized error semantics apply?
5. What canonical revision lookup and transaction/session boundary connects
   these ports to Manager while keeping live sessions out of child processes?

## Security-review verification

- Windows Ruff lint and formatting passed. The focused run passed 81 tests
  in 68.16 seconds, including 27 trusted-boundary, 33 legacy adapter and
  21 D4B worker tests. The legacy regression demonstrates a limitation
  of the excluded adapter, rather than production authorization.
- The Linux candidate passed Ruff lint and formatting and all 380 backend
  tests in 165.57 seconds. It ran from the published Docker image with only
  the new module and its test overlaid. Both legacy files were explicitly
  checked absent. All live browser/API and schema regressions passed.
- The three-file candidate is ready for partial publication review. Manager
  runtime registration, schema and per-file checks, artifact scope custody
  and atomic result acceptance remain outside this candidate.
