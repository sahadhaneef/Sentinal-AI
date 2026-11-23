# Backend acceptance tests

Phase 3 adds REST intake/read/error tests and actual frontend-adapter/browser
probes against isolated persisted databases, including empty and unavailable
backend states. These browser probes require installed Chromium and never
intercept API responses. Existing frontend Playwright HTTP fixtures remain
separate evidence. See `PHASE_3_VERIFICATION.md` for final commands and results.

Run from `backend/` after `uv sync --locked` and `npm ci` in `frontend/`:

```
uv run ruff check .
uv run ruff format --check .
uv run pytest
```

Coverage:

- Health success uses the existing JSON envelope, correct schema version and server correlation header; distinct requests get distinct IDs.
- Only implemented routes appear in OpenAPI. Missing domain/admin routes return structured 404, never fake successful data or sessions.
- Unsupported methods retain 405 and Allow; request validation retains 422 without echoing sensitive inputs; typed conflicts remain 409.
- Unexpected exceptions produce safe 500 responses with request IDs and exact-origin CORS. No exception text, private paths or request bodies are returned.
- Configuration rejects wildcard, nonlocal, credential-bearing or malformed origins and unsupported database backends/environments.
- Logging is JSON/UTC, redacts common secret patterns and omits arbitrary extras.
- SQLite lifespan/restart, foreign-key enforcement and actual Alembic upgrade/downgrade/reapply. The original Phase 1 baseline checks still target the baseline; separate Phase 2 tests verify the populated domain schema.
- Async HTTPX ASGI integration and the real unchanged TypeScript HTTP adapter/Zod running against an actual local Uvicorn process. The latter is marked `integration` and requires Node/frontend dependencies and loopback sockets. It validates health and real errors, not full UI functionality or authentication.

Tests isolate databases in temporary directories/in-memory engines and terminate only their own spawned server. The live adapter probe builds JavaScript in memory without modifying frontend source or writing generated bundles into the repository. No credentials or LLM services are needed.

Existing frontend `npm run check` and `npm run build` must still pass. Existing Playwright HTTP tests intercept their server responses; they are not relabeled as live backend evidence. Phase 2 now tests domain persistence, duplicate monitoring events, exact approval bindings, invalid statuses/foreign keys, uniqueness, transaction rollback, metadata bounds, concurrent ingestion, migration atomicity, downgrade refusal and persistent records across application restarts. Operational repair journeys, stale workspace checks, authorization, runner timeouts and recovery execution remain future work.

Historical Phase 0/1 results are in `PHASE_0_1_VERIFICATION.md`. Current Phase 2 results and unresolved checks are recorded separately in `PHASE_2_VERIFICATION.md`. No synthetic database record represents an executed agent, test runner or recovery.

Final Phase 3 results: 153 backend tests, 42 frontend unit tests and all 40 frontend browser tests passed. Ruff lint/format, frontend typecheck/lint/build, backend wheel and Alembic checks passed. See `PHASE_3_VERIFICATION.md` for actual commands, live-versus-intercepted evidence, browser investigation and limits.
