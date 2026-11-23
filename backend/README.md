# SENTINEL AI backend - Phase 3

Database-backed REST reads and explicit operator intake for the local prototype.
The existing frontend HTTP adapter consumes these responses without changing its
interfaces or Zod schemas. Mock mode and the isolated learning demo remain usable.
No AI agents, workflow decisions, generated-code execution, patch application or
restoration are implemented.

See [Phase 3 API contract](docs/PHASE_3_API.md),
[database architecture](docs/DATABASE_ARCHITECTURE.md) and
[verification](docs/PHASE_3_VERIFICATION.md).

## Run backend and frontend together

Use Python 3.12, Node.js 24 and the locked dependencies. In one terminal from the
project root, using an installed uv:

```powershell
cd backend
uv sync --locked
# Back up an existing database before upgrading; never reset it.
uv run alembic upgrade head
uv run uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000 --no-access-log
```

For this workspace's existing local installation, from the project root:

```powershell
& ./backend/.venv/Scripts/python.exe -m alembic -c backend/alembic.ini upgrade head
& ./backend/.venv/Scripts/python.exe -m uvicorn app.main:create_app --factory --app-dir backend --host 127.0.0.1 --port 8000 --no-access-log
```

In a second terminal:

```powershell
cd frontend
npm ci
$env:VITE_DATA_SOURCE = "api"
$env:VITE_API_BASE_URL = "http://127.0.0.1:8000/api/v1"
npm run dev
```

Open `http://127.0.0.1:5173/dashboard`. Empty databases render empty/zero states;
there is no implicit fixture seed. `/api/v1/docs` and `/api/v1/openapi.json` expose
implemented routes. `/api/v1/health` is process liveness, not agent readiness.

To return to interactive simulations, stop Vite, set
`$env:VITE_DATA_SOURCE = "mock"`, and run `npm run dev` again. Vite selects the
adapter at startup. The public `/demo` always has its own isolated simulation.
There is no automatic API-to-mock fallback.

## Local access and configuration

Copy `.env.example` to `backend/.env` only when customization is needed. Environment
variables start with `SENTINEL_`; paths resolve relative to backend unless absolute.

- `DATABASE_URL`: SQLite only, default `sqlite:///artifacts/sentinel.db`.
- `CORS_ORIGINS`: exact local frontend origins; localhost/127.0.0.1:5173 by default.
- `ARTIFACT_ROOT`: default `artifacts/content`, bounded metadata-backed text reads.
- `ARTIFACT_MAX_BYTES`: default 1048576; larger output is not silently truncated.
- `DEMO_ROOT`: default `demo_workspaces`; client registration cannot supply a path.
- `PERMITTED_WORKSPACES`: operator-owned JSON map described below.
- `OPERATOR_TOKEN`: optional independently generated secret of at least 32
  characters. Without configuration registration/ingestion are disabled.
- `ENVIRONMENT`: local/test; production is unsupported. `LOG_LEVEL`: INFO default.

This phase explicitly permits local read-only access without browser authentication.
It does not issue a session or claim role enforcement. Bind only to loopback and
use non-sensitive prototype records. Administrative authentication is deferred.
CORS is not authorization. No token belongs in a frontend variable or Git.

## Operator registration and ingestion

Prepare a real permitted sample directory at `DEMO_ROOT/<key>` and an existing
source snapshot below `ARTIFACT_ROOT`. Configure `PERMITTED_WORKSPACES`, for example:

```json
{"demo":{"name":"Local sample","description":"Designated prototype workspace","revision":"demo-v1","snapshot_key":"snapshots/demo-v1.zip","supported_errors":["KeyError"]}}
```

The snapshot must be real operator-prepared content, not a fabricated source
snapshot. Neither the API nor registration captures, runs or modifies source files.
Generate a token locally, for example with `python -c "import secrets; print(secrets.token_urlsafe(32))"`,
and configure it only on the server and your operator terminal. Registration uses:

```powershell
$headers = @{ Authorization = "Bearer $env:SENTINEL_OPERATOR_TOKEN" }
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/v1/applications -Headers $headers -ContentType application/json -Body '{"workspace_key":"demo"}'
```

Use the returned application ID and revision in the normalized POST `/incidents`
contract in OpenAPI. Supply a stable source event ID, canonical SHA-256 fingerprint,
severity, configured error type, sanitized message and UTC observation timestamp.
An optional log reference must already be registered, redacted and readable.
Repeated matching events deduplicate; no agent or run starts. Runtime database,
artifact and demo directories are ignored by Git. Registration duplicates conflict
rather than replace an application. The frontend remains read-only in HTTP mode;
workflow and control mutation calls return structured 501 responses.

## Validation

From backend:

```powershell
python -m ruff check .
python -m ruff format --check .
python -m pytest
python -m alembic check
```

Use the project's `.venv/Scripts/python.exe` if Python is not on PATH. Tests use
isolated databases. Live integration requires Node, installed frontend dependencies,
installed Chromium and permission to bind loopback sockets. Install Chromium with
`PLAYWRIGHT_BROWSERS_PATH` pointing at `frontend/.playwright`, then
`npx playwright install chromium` from frontend. Missing prerequisites fail the
checks rather than silently skipping them.

From frontend run `npm run check`, `npm run build` and the full Playwright suite
with the same browser path. Existing intercepted HTTP tests and actual live
FastAPI/browser checks are reported separately. All remaining Python work follows
[backend rules](AGENTS.md), including the existing 100-character Ruff line limit.

## Database safety and next phase

Alembic owns all schema changes. Startup never migrates or calls `create_all`.
The populated downgrade guard remains in place; back up before schema changes.
Phase 3 adds no schema revision or reset. The uniqueness comparison fix changes
migration drift detection only and is tested against a genuinely missing constraint.

Phase 4 can build authenticated services and Manager orchestration over the
existing repository/unit-of-work boundaries. Approval/rejection, runner isolation,
source confinement for execution, separate application confirmation and recovery
must be implemented and verified before enabling HTTP workflow mutations.
