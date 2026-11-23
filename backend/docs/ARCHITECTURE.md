# Backend architecture and phase boundary

Phase 3 update: routes now validate explicit Pydantic projections and delegate to
injected read/intake services and repositories in function-scoped transactions.
See `PHASE_3_API.md` for implemented routes, local read policy, operator capability,
artifact projections and deferred controls. The foundation description below is
historical where it says only health is advertised.

## Implemented

`app.main.create_app(settings)` is an injectable application factory. The default environment is loopback-only local development. No FastAPI application is instantiated as an import side effect. Uvicorn uses `app.main:create_app --factory`.

Request chain: credentialed exact-origin CORS → pure ASGI request context/safe failure boundary → FastAPI routes and typed error handlers. Health returns the frontend's envelope. Unknown endpoints and methods retain meaningful non-2xx statuses. Framework validation returns sanitized field locations/types; exception messages, raw inputs and tracebacks are not returned. OpenAPI advertises only health.

Lifespan creates an SQLite engine, verifies connectivity, and disposes it on shutdown. Each session dependency creates its own SQLAlchemy Session; no process-global session. SQLite connections enable foreign keys. SQLAlchemy models register 28 domain tables. Alembic owns the baseline and additive domain migration; no runtime `create_all()` or automatic migrations. Transactions and repositories live below future API/services; see `DATABASE_ARCHITECTURE.md`.

Structured request logs are UTC JSON, with server-generated UUID correlation IDs. No request body, cookies, authorization, raw URL/query or arbitrary exception text is logged. Start Uvicorn with `--no-access-log` to avoid a second unsanitized URL logger.

## Current tree

```
app/
  main.py                 factory and lifespan
  core/                   config, errors, logging, request context
  api/routes/health.py    /api/v1/health
  api/dependencies/       dependency namespace for later auth/domain services
  schemas/                common envelopes and health only
  db/                     Base, engine, session and validated storage types
  models/                 relational domain tables and enums
  repositories/           transaction boundary and persistence operations
alembic/                  baseline, domain revision and migration runner
tests/                    unit, security, contracts, integration, database
scripts/                  actual frontend-adapter HTTP probe
```

## Explicitly deferred

Phase 2 storage is implemented; no workflow behavior is implied. Phase 3 onward: authenticated read/write APIs, session/CSRF/roles, normalized log intake, Manager state machine, retrieval, LLM abstraction, patch candidates, restricted runner, human gates, controlled application, verification and reporting. No provider SDK or API key is necessary in this foundation. No agent statuses or repair results are fabricated.

Team ownership remains: Delvin — Manager/shared orchestration/integration; Sahad — Diagnosis/Code RAG; Yadhulakshmi — Repair; Neha — Monitoring/Reporting; Sravan — Testing/local verification. Later modules should accept validated Pydantic handoffs through typed service protocols, not call each other's HTTP routes or read mutable frontend state. The frozen endpoint/detail projections are in the contract document.

The existing React/Motion frontend, routes, mock adapter and isolated learning demo are unchanged. Domain persistence does not imply domain API or agent behavior has been delivered. This is not a production deployment design or security certification.
