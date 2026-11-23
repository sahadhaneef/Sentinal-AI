# Phase 3 verification

## Delivered scope

Database-backed REST reads and explicit configured-operator intake are implemented.
OpenAPI publishes 27 paths with 31 operations: 23 GET operations (including health),
two enabled intake POST operations, and six explicit 501 compatibility guards.
The full endpoint matrix and request/security decisions are in `PHASE_3_API.md`.

Implemented read views cover applications/revisions/observation metadata,
dashboard aggregates, incident search/filter/sort/opaque pagination, incident
details/audit/run transitions, six agent definitions and recorded executions,
revision-bound diagnosis, candidates/diffs/validation, existing decisions and
application/verification records, stored reports, artifact metadata and safe
settings. Registration and normalized ingestion create metadata only.

Routes use Pydantic v2 DTOs and injected services; SQL queries and intake
persistence use repositories inside request-scoped transactions. Errors use the
existing safe envelope. No domain tables were reset or implicitly seeded, and no
new schema migration is needed. SQLite's unique-constraint drift comparison was
corrected to compare definitions by columns; a regression test demonstrates that
a genuinely missing unique constraint is still detected.

## Frontend compatibility and discrepancies

All six locked frontend contract/interface/adapter/ADR source hashes remain
unchanged. No TypeScript schema or adapter method was changed to accommodate a
backend mismatch. Actual adapter requests are compiled with Vite and parsed by
the existing Zod validators against a running local Uvicorn process, for both
empty and persisted databases. This checks field names, nullability, wire enums,
UTC dates, nested evidence, check results, IDs, pagination and real error responses.
The existing OpenAPI acceptance test now checks the exact Phase 3 route set and
typed unavailable-operation error schema; the original health/error assertions
remain in place.

The application status enum has no unknown member: unobserved applications retain
offline and expose `not_observed` metadata. Pre-run audit events use an empty
required wire run ID, not a fictional workflow. Missing candidate results do not
inherit evidence from earlier candidates. A stored resolved claim without complete
readable passed verification evidence is refused with EVIDENCE_INCOMPLETE.

There is no browser login/bootstrap contract. This local phase explicitly permits
unauthenticated read access and separately protects intake with a configured bearer
capability; it does not claim user/session/role authorization. This temporary
exception to the complete blueprint is documented before implementation in
`PHASE_3_PLAN.md` and in `PHASE_3_API.md`. Browser profiles accurately say read-only
access. Monitoring controls are disabled in API mode; decision/apply hints are
false, and direct mutation calls return structured 501. Mock simulations remain
interactive. No API-to-mock fallback was introduced.

New real-browser probes navigate the existing frontend over actual FastAPI HTTP
responses without interception: eight populated workspace views, empty application/
incident/dashboard views, and a genuinely unavailable backend with no fake data.
The existing frontend Playwright HTTP project still intercepts its own fixtures;
its results are separate from these live probes.

## Test coverage added

47 Phase 3 checks extend the 106 existing backend checks. Coverage includes:

- Empty and persisted responses; list/detail/report/history/agent projections.
- Permitted registration, rejected paths/extra fields, operator authentication,
  unsupported mutations and missing records.
- Idempotent ingestion, duplicate fingerprints, audit replay behavior and initial
  detected/manual-review state without run dispatch.
- Intersecting scopes/filters, deterministic ordering, literal Unicode search,
  invalid/repeated parameters, opaque cursors, tampering, expiry, filter/snapshot
  changes and server restart invalidation.
- Queried counts, recorded agent activity, pending queues, candidate versions,
  absent validation, evidence integrity/redaction/size/missing-file errors and
  refusal of unsupported resolved claims. Missing unrelated log/error artifacts do not break agent summaries or standalone verification reads; the specific views requiring those bytes still return errors.
- Real adapter parsing and real browser populated/empty/unavailable states.
- Migration drift detection of a physically missing unique constraint.

All fixture records are explicitly synthetic and isolated in temporary databases.
No fixture record is described as an executed diagnosis, test, repair or recovery.

## Browser timeout investigation

Before fixes, the isolated agent-card test passed in 18.7 seconds, while the video
test reproduced its original 30-second timeout and context teardown stall. This
did not establish a broken theme selector. Inspection found the full-screen
procedural shader continued rendering during media playback and rebuilt its WebGL
program whenever its running flag changed. Seeking was asserted from currentTime
before decoded future frames were ready.

The first full rerun passed 38/40 and exposed a paused-seeking stall plus a scroll-story/context timeout. The trace showed seeking never completed before playback began, so playback-only priority was insufficient. A renderer probe confirmed ANGLE SwiftShader. The final changes suspend/resume the decorative shader during seeking as well as playback, without rebuilding its program, and bound software raster work to 512 by 336 pixels at 10 frames per second. Wall-clock animation speed is retained; hardware rendering, themes, ordinary foreground motion and reduced-motion behavior are preserved. The video test now waits for seeking to finish
and HAVE_FUTURE_DATA, and additionally asserts shader pause/resume. All original
duration/playback/chapter/caption/transcript assertions remain. No timeouts were
increased and no tests were disabled. Both affected tests passed together after
the fixes (7.2 and 7.7 seconds; total run 22.8 seconds). The expanded stress rerun passed all six cases (the agent, video and scroll scenarios twice) in 36.3 seconds, with case times 3.6-5.5 seconds. Resource contention is the supported explanation for intermittent theme/scroll delays, not a separately proven selector regression.

## Actual validation results

- Final full backend suite: **153 passed** in 60.83 seconds after all source changes.
- OpenAPI schema assertions, including typed 501 errors: passed within the final full suite.
- Ruff lint: passed. Ruff formatting check: passed, 87 Python files.
- Alembic model/schema drift check on the existing local database: passed.
- Backend wheel build: passed using the locked local environment/cache.
- Frontend TypeScript and ESLint: passed.
- Frontend Vitest: **42 passed**, six files.
- Frontend production build: passed.
- Final complete existing Playwright suite: **40 passed** in 4.9 minutes (`npx playwright test --workers=1`).
- Final Git whitespace check: passed.

## Limits and Phase 4 readiness

No agents, LLM calls, log reader, workflow state machine, generated-code runner,
approval/rejection, local patch application or restoration is implemented. HTTP
control writes stay unavailable. Full user sessions, role authorization, CSRF,
general HTTP idempotency, per-user artifact access and hostile-filesystem sandboxing
remain future work. Reads are for a loopback-only non-sensitive prototype.

Artifacts must be prepared and registered by the operator; there is no upload or
raw download route. Missing bytes are errors, not fabricated excerpts. Pagination
uses an in-memory filtered snapshot suitable for this prototype; scaling it is
deferred. Cursors intentionally expire on server restart. Safe settings defaults
are configuration values, not live measurements. Agent statuses are recorded state,
not independent process heartbeats.

Phase 4 can build authenticated services and Manager transitions on the preserved
repository/unit-of-work boundaries and frozen transport. Execution controls must
remain disabled until their separate safety services and tests exist.

All mandatory Phase 3 checks passed on the final source. The earlier browser failures are recorded above; no browser failure remains unresolved. The deferred capabilities listed above were intentionally not enabled.
