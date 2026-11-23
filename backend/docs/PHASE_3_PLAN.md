# Phase 3 implementation checklist

Inspection: backend rules, both specifications, frozen contract, database design,
Phase 2 results, README, SQLAlchemy models/repositories/migrations/tests, frontend
Zod schemas/types, both adapters, query hooks, routes and browser/API tests.

## Contract decisions before implementation

- Existing adapter methods and wire enums remain authoritative and unchanged.
  New registration/ingestion/history/report/artifact metadata endpoints are
  additive; their previously unfrozen payloads will be published in OpenAPI.
- No application `unknown` enum exists. Keep `offline` for unobserved/inactive
  applications; additive application metadata distinguishes `not_observed` from
  persisted observations. No monitoring worker runs in this phase.
- No browser login/bootstrap contract exists. Phase 3 provides explicitly local,
  read-only prototype access; full user/session/role authorization stays deferred.
  Operator registration/ingestion require an explicitly configured secret bearer
  token, never a JSON actor ID or a frontend credential. No cookie-auth mutations.
- Registration accepts only a configured workspace key. Directory, revision,
  snapshot artifact key and supported errors are operator-owned configuration.
  Snapshot bytes must already exist in confined artifact storage; registration
  does not scan repositories, execute commands or start monitoring.
- Artifact text projections required by Zod must come from bounded, redacted,
  hash-verified UTF-8 files under the artifact root. Missing/unavailable evidence
  yields a structured error, never invented text or successful validation.
- Incident cursors are opaque, signed, filter-bound and short-lived. Changes to
  the matching result snapshot invalidate continuation with 422; no silent page
  reinterpretation. Ties follow the frozen timestamp/ID rules.
- Existing decision/apply/monitoring/settings-write adapter calls receive 501
  NOT_IMPLEMENTED with an accurate message. Incident permission flags stay false.
  Mock interactions remain fully functional.
- Existing Phase 1 tests that assert domain paths are absent must evolve to assert
  the actual published Phase 3 paths and explicitly unavailable mutations. Keep
  health/error checks and expand live adapter probes rather than remove coverage.

## Implementation

- [x] Pydantic request/response models and DI service/transaction boundary.
- [x] Repository queries: deterministic incident filtering, aggregates, histories.
- [x] Safe artifact projections and configured-workspace registration/ingestion.
- [x] Application, dashboard, incident, agent, candidate, evidence/report reads.
- [x] Explicit HTTP-mode unavailability and preserved mock behavior.
- [x] Live Zod/HTTP and browser integration with isolated persisted fixtures.
- [x] Investigate original animation/theme and video timeouts; fix causes.
- [x] Complete backend/frontend suites, lint/format/build and migration checks.
- [x] Updated contract/setup and PHASE_3_VERIFICATION.md with actual results.
