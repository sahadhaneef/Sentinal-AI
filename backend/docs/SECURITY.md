# Prototype security boundaries

Phase 3 update: current access policy is documented in `PHASE_3_API.md`. Local prototype reads are unauthenticated; token-protected configured-workspace registration and normalized ingestion are the only enabled writes. All execution/control mutations return 501. Artifact text is confined, bounded and hash-checked. No user sessions or production authorization are claimed. Historical foundation boundaries follow.

## Foundation protections actually implemented

- Loopback startup instructions and exact loopback CORS origins; wildcard credentialed CORS is rejected by configuration.
- No administrative, ingestion, filesystem patching, provider, artifact download or execution routes. Unimplemented endpoints return 404.
- Typed health/error envelopes and server-generated request IDs; incoming IDs are not trusted.
- Request validation strips raw inputs and arbitrary validation messages from responses. Unexpected server errors return generic 500 envelopes with CORS/correlation headers.
- Application logs contain only safe, selected metadata; no raw URL, query, request body, cookies, exception traceback or arbitrary extras. Common secret-shaped strings are redacted defensively. Uvicorn access logging is disabled in the documented startup command.
- SQLite URL configuration is restricted to the local driver; foreign keys are enabled. No automatic domain-table creation.
- Local tooling, virtual environments, database/artifacts, credentials and `.env` files are ignored by Git. `.env.example` contains no real keys or passwords.

## Not implemented; do not claim production security

Storage for password hashes, roles, hashed sessions, idempotency and audits exists in Phase 2. Password verification, authenticated sessions, role authorization, CSRF establishment/verification, HTTP idempotency, automatic audit emission, rate limiting, source confinement, artifact authorization, sandboxed execution and controlled application remain later work. CORS and a demo identity do not grant authorization. Do not expose this foundation on a public interface or use its health response as proof those gates exist.

No untrusted generated code is executed. A temporary directory alone must never be treated as a sandbox when the Testing phase is implemented. Strongly restricted containers or an equivalent validated boundary are required; otherwise disable untrusted execution. Later patch application is only for a designated demo workspace, with exact approval/hash/revision checks and safe restoration that cannot overwrite unrelated changes.

OpenAPI/Swagger is intended for local development. Swagger UI uses FastAPI's default hosted UI assets; no provider secrets or server filesystem paths are present in the schema. Unlisted origins get no CORS permission; local non-browser clients can still call the public health endpoint.

The dependency lock is reproducible. FastAPI/Starlette are constrained to a compatible HTTPX test-client series. A single known third-party AnyIO legacy-alias deprecation is filtered in tests; application and other warnings remain errors. This is compatibility handling, not independent dependency/security certification.

## Phase 2 integrity boundaries

Composite foreign keys bind evidence to source revisions and approval/application metadata to exact candidates and hashes. Partial uniqueness prevents duplicate open incidents and competing active runs. Repositories restrict history mutation and roll back entire failed transactions. Artifact references are validated relative metadata; no files are read or applied. These constraints do not grant permissions, authorize artifact access, verify blob bytes, establish a complete passed check set, or enforce the legal workflow state machine. See `DATABASE_ARCHITECTURE.md`.
