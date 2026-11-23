# Phase 0 / Phase 1 verification — 2026-11-18

Completed scope: inspect/freeze the current frontend contract, document differences, and verify a real FastAPI foundation. No later domain phase was started. No frontend source, adapter, schema, default data mode, or UI component was changed.

## Actual results

- Python 3.12.16 installed in the ignored workspace-local `.tools/python` directory. uv 0.13.9 and backend dependencies are local; Python was not registered system-wide.
- Locked environment created successfully in `backend/.venv` with `backend/uv.lock`.
- Ruff check: passed. Ruff format check: 35 Python files already formatted.
- Backend pytest: **31 passed** in the final run.
- The unchanged TypeScript `HttpSentinelApi` and Zod accepted actual health/error responses from a spawned Uvicorn process. This is a live HTTP probe, not intercepted fetch or a fixture-backed API.
- Migration tests upgraded, downgraded, and reapplied the baseline on isolated databases. Local `alembic upgrade head` succeeded; `alembic current` returned `0001_foundation (head)`.
- Frontend `npm run check`: typecheck, ESLint and **42 tests passed**.
- Frontend production build: passed. Frontend source/contract files retained their prior content; the backend's normalized SHA-256 manifest checks for coordinated contract drift.
- `git diff --check`: passed. Local tools, virtual environment and database are ignored by Git.

Windows sandbox note: the first in-process HTTP test attempt could not proceed with event-loop sockets restricted. It was stopped and rerun with local socket permission; all final HTTP tests passed. The actual live probe terminates its own temporary Uvicorn process. No persistent backend server is left running by the test suite.

## Deliverables

The complete endpoint/query/type/error/state inventory and discrepancy resolutions are in `FRONTEND_BACKEND_CONTRACT.md`. Runtime modules provide health, envelopes, request context, structured logging, safe exceptions/CORS, SQLite engine/session lifecycle and Alembic scaffolding. Setup and limitations are in `../README.md`, `ARCHITECTURE.md`, `SECURITY.md` and `TESTING.md`.

## Remaining boundary

Only `/api/v1/health` is implemented as an application API. Domain models/records, authentication, sessions/CSRF/roles, agents, retrieval/LLM providers, candidate testing, approvals, application, verification, reporting and full frontend-to-backend workspace journeys remain later phases. Unavailable operations return 404; no successful execution, identity, recovery or persistence of incidents is claimed. Keep the frontend in mock mode until the relevant domain endpoints exist.
