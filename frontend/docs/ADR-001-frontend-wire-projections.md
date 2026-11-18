# ADR-001: frozen frontend detail projections

Status: frontend contract decision; confirm with the FastAPI team before implementation.

The architecture specifies artifact references and endpoint responsibilities, but not complete detail responses. These explicit projections are frozen in `src/contracts/schemas.ts` to avoid component rewrites later.

1. `IncidentDetail` extends the incident with redacted `source_log`, nullable diagnosis/validation/decision/application_attempt/verification/report, patch candidates, and `can_approve`, `can_reject`, `can_apply`, `permission_reason`. Missing evidence stays null.
2. Source evidence includes a sanitized `excerpt`; patches include readable unified `diff`; validation checks include readable sanitized `evidence`. Artifact IDs remain attached. The backend may resolve its artifact store into these projections; the browser never reads repository paths.
3. Reports include readable `summary`, `limitations`, outcome, version and artifact reference. Verification includes checks and `monitoring_observation`. These are projections of persisted facts, not another workflow authority.
4. Applications add `supported_errors` and healthy/degraded/offline presentation statuses. Agent details include owner, responsibility, inputs/outputs and recent executions. Dashboard counts derive from current records.
5. Incident list adds `search` across ID, error type and message. Pagination returns `items`, `total`, `next_cursor`. This is an explicit extension to the blueprint's list query.
6. Session transport assumes a `csrf_token` cookie and `X-CSRF-Token` header. The future backend owns establishment and verification. No frontend login bypass or invented session endpoint exists.
7. Mock reset is outside `SentinelApi`, a mock-only capability selected by `client.ts`. No fictional reset endpoint is called. UI preferences persist locally; backend preferences display read-only although the typed PATCH adapter is implemented.

No execution capability was added. Backend implementation must honor these projections or update this ADR, both blueprint addenda, adapters and contract tests together.
