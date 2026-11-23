# Phase 2 verification — 2026-11-18

## Delivered

- 28 SQLAlchemy 2 domain tables, explicit relationships, UUID defaults, UTC types, validated metadata/artifact references, named checks, foreign keys, uniqueness and lookup/partial indexes.
- Additive `0002_domain` migration after the unchanged baseline; guarded populated downgrade and transactional SQLite DDL.
- Repository/store transaction boundary, bounded CRUD, immutable history fields, revision selection, candidate registration and concurrency-safe monitoring deduplication.
- 75 isolated database tests alongside all 31 existing backend tests. The original baseline migration acceptance test explicitly targets `0001_foundation`; new head-migration tests separately verify the domain schema, data preservation and recovery. Its original assertions are retained.
- Database architecture and updated setup, architecture, security and testing documentation.

## Actual commands and results

| Check | Result |
|---|---|
| `backend/.venv/Scripts/python.exe -m pytest -q` from backend | **106 passed**, 18.27 seconds on the final full run. Includes the actual TypeScript adapter against a live local Uvicorn process. |
| Ruff check | Passed. |
| Ruff format check | Passed, 65 files formatted. |
| `uv build --offline --wheel` using the locked local environment/cache | Passed; wheel generated under ignored `.tools/backend-dist/`. |
| Alembic upgrades/checks in isolated databases | Passed: fresh creation, baseline upgrade preserving unrelated data, empty downgrade/reapply, populated downgrade refusal, failed-upgrade DDL rollback, no schema drift. |
| SQLite integrity/FK checks | Passed in tests and the upgraded local database. |
| Domain persistence across engine and FastAPI lifespan restart | Passed; records and relationship reads survive both restarts. |
| `npm run check` from frontend | Passed: TypeScript, ESLint and **42 Vitest tests**. |
| `npm run build` from frontend | Passed. |
| Full `npx playwright test --workers=1` | **38 passed, 2 failed**, 8.4 minutes. All 40 existing browser tests ran. See unresolved checks below. |
| Frozen frontend contract source hashes | Passed within the backend suite; no frontend source, wire schema or adapter edits. |
| `git diff --check` | Passed. |

An earlier backend run while browsers were competing for resources passed 90 tests and timed out starting the live HTTP probe. A separate full rerun passed all 91 tests then present; after the remaining integrity tests were added, the final full run passed all 106. The existing HTTP startup deadline was not relaxed. An initial two-worker browser attempt was interrupted after timeouts; the complete sequential result above is the browser acceptance result, not a claim that the interrupted attempt passed.

## Local database migration

The existing `backend/artifacts/sentinel.db` was at `0001_foundation` with only the version table. SQLite's backup API saved a verified backup to `.tools/backups/sentinel-before-phase2-20261118T095515Z.db` before upgrade. It is now at `0002_domain` with 28 domain tables plus the version table. `PRAGMA integrity_check` returned `ok`, `PRAGMA foreign_key_check` returned no rows, and `alembic check` reported no new operations. No reset, data deletion or synthetic seed was performed. Database, backup, tooling and build outputs remain ignored by Git.

## Unresolved checks and boundaries

Two unchanged frontend browser tests timed out under the original 30-second deadline:

1. `frontend/tests/e2e/hero-motion.spec.ts:3`: automatic agent color flow, keyboard details and theme switching. The trace's final pending browser action was clicking **Toggle theme** after the light-theme card screenshot.
2. `frontend/tests/e2e/product-video.spec.ts:3`: playback/chapter seeking. Trace polling observed approximately 7.5 seconds where the chapter assertion required playback beyond 8 seconds; the test and context teardown timed out.

Failure contexts and traces are under `frontend/test-results/` in their named test directories. These frontend motion/media issues were not repaired or hidden in this database-only phase. Their cause has not been conclusively established. Workspace journeys, responsive checks, accessibility scans and all three intercepted HTTP-mode browser tests passed; intercepted browser responses are not live domain-backend integration evidence.

Domain endpoints, identity/session/role enforcement, legal workflow transitions, nonempty complete passed-check enforcement, real artifact byte validation and access control, the six agents, command execution, local patch application and restoration are future phases. Database constraints support those boundaries and do not replace authorization. Synthetic database test fixtures do not represent any real executed diagnosis, validation, repair or recovery.
