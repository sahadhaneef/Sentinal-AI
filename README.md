# SENTINEL AI

A frontend prototype for understanding application incidents, reviewing proposed fixes, and keeping administrators in control of changes.

The React and TypeScript application includes a public landing page, animated globe background, guided onboarding, interactive incident demo, and an administrator workspace. Mock mode is the default. The FastAPI backend now provides Phase 3 database-backed REST reads, safe errors and operator-only intake. The six agents and workflow mutations remain deferred. See [backend setup](backend/README.md) and the [frontend–backend contract](backend/docs/FRONTEND_BACKEND_CONTRACT.md).

## Run locally

Install Node.js 24 LTS, then run:

```sh
cd frontend
npm ci
npm run dev
```

Open the local URL printed by Vite, normally http://127.0.0.1:5173.

## Validate and build

```sh
cd frontend
npm run check
npm run build
```

Browser tests use Playwright. See [frontend/README.md](frontend/README.md) for setup, API configuration, and deployment details.

## Project contents

- `frontend/`: application source, contracts, tests, documentation, and published demo media.
- `backend/`: FastAPI REST APIs, domain storage, Alembic migrations, services, repositories and tests.
- `media/sentinel-tour/`: editable source and narration for the product tour.
- `FRONTEND_SPECIFICATION.md`: frontend specification.
- `BACKEND_ARCHITECTURE.md`: planned backend architecture.

The demo uses simulated data. It does not modify production applications or execute real agents.
