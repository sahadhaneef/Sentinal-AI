# SENTINEL AI frontend

Frontend-only implementation of the two project blueprints. There is no FastAPI server, database, agent execution, LLM request, filesystem patching or production recovery here.

## Start locally

Use Node.js 24 LTS. From the project root:

```powershell
cd frontend
npm.cmd ci --cache .npm-cache
npm.cmd run dev
```

Open http://127.0.0.1:5173. `/` is the public product website; `/dashboard` remains the workspace entry. Vite supports direct route refresh. A static production host must rewrite unknown application paths to `index.html`.

The reference image is absent at `docs/reference/sentinel-ai-reference.png`. The interface follows the written description: light sidebar, navy text, blue/teal/purple accents, a horizontal workflow and a responsive 3×2 agent grid. No claim of screenshot matching is made.

## Data modes

Mock mode is the default and is visibly labeled. Its state is shared in memory for one browser document. SPA navigation preserves decisions; a full reload or Settings → Reset demo data restores the seed. Only interface preferences persist in localStorage.

For the future backend, copy `.env.example` to `.env.local`, set `VITE_DATA_SOURCE=api`, set `VITE_API_BASE_URL`, and restart Vite. The frontend uses `HttpSentinelApi` with no component changes. It never silently falls back to mocks. API mode requires the future backend's authenticated session; the demo reviewer is not real authentication.

Environment variables:

- `VITE_DATA_SOURCE`: `mock` (default) or `api`. Selected once at startup; invalid values fail explicitly.
- `VITE_API_BASE_URL`: defaults to `http://localhost:8000/api/v1`; used only by the HTTP adapter.

For cookie/CSRF integration, use the same hostname for both services: open the frontend at `http://localhost:5173` with the default API hostname, or use `127.0.0.1` for both and update `VITE_API_BASE_URL`. Ports may differ. FastAPI must allow the exact frontend origin with credentials, establish the session, supply the CSRF convention and verify mutations. Mixed localhost/127.0.0.1 cookie behavior has not been established as an authentication scheme.

## Architecture

- `src/contracts/schemas.ts`: Zod wire schemas. `types.ts` derives strict TypeScript types.
- `src/api/interfaces.ts`: shared `SentinelApi` interface.
- `src/api/mockAdapter.ts`: linked scenarios and guarded simulated mutations.
- `src/api/realAdapter.ts`: the only network transport; envelopes, cookies, CSRF header, idempotency keys, timeout and validation.
- `src/api/client.ts`: selects the adapter once.
- `src/hooks/queries.ts`: query keys, fetching, polling, mutations and invalidation.
- `src/pages`, `src/components`, `src/layouts`: UI built on those hooks.
- `src/styles`: tokens, responsive layouts and reduced-motion rules.
- `src/lib/approval.ts`: evidence consistency checks for review controls; backend enforcement remains mandatory.
- `src/lib/pagination.ts`: opaque cursor history, persisted in the URL without arithmetic.

## Available routes

- `/`: public product website with clickable workflow, expandable roles, platform previews, FAQ and honest video fallback.
- `/demo`: isolated ten-step simulated learning journey; decisions never affect workspace data or call FastAPI.
- `/onboarding`: resumable six-step administrator introduction, with Skip and Restart and browser-local preferences.
- `/docs`: readable product documentation and links to workspace features.

- `/dashboard`: derived incident counts, recent incidents, agent summaries and workflow.
- `/applications`: searchable sample applications; `/applications/:id` has monitoring confirmation and related incidents.
- `/incidents`: server-filtered scopes, search, status/severity/application filters, sorting and cursor pagination.
- `/incidents/:id`: overview, cited diagnosis, patch/tests, timeline and report sections.
- `/agents`: six logical agents and the Manager-coordinated workflow; `/agents/:type` has responsibilities and executions.
- `/repair-testing`: paginated candidate queue, exact diffs and isolated check evidence.
- `/approval-recovery`: paginated review queue, optional pending scope, frozen confirmation evidence and separate Apply.
- `/history`: paginated closed/resolved/rejected/unresolved reports, with search and filters.
- `/settings`: appearance, reduced motion, polling, safe backend settings and confirmed demo reset.
- Unknown routes: useful not-found state. Deep links and browser back/forward work.

No page imports mock fixtures or uses fetch. Active incidents poll every 3–5 seconds, pause in hidden tabs, and stop at terminal states or request errors. Retryable queries use exponential backoff. Events poll only while the incident is active.

## Explore the scenarios

1. `/incidents/inc_001`: diagnosis → patch & tests → approve → separately apply → simulated verification → report. Dashboard counts and history update.
2. `/incidents/inc_002`: failed reproduction, revision required (attempt 1 of 2), approval disabled. New candidate generation belongs to the future Manager; this UI has no fictional generator control.
3. `/incidents/inc_003`: unsupported log, manual review, no fabricated diagnosis or candidate.
4. `/incidents/inc_004`: rejected candidate, report, unchanged demo.
5. `/incidents/inc_005`: resolved incident, verification and report.
6. `/incidents/inc_006`: approve to receive `CANDIDATE_STALE` (409). The dialog closes, data refreshes and further approval/application is disabled. Reset demo data to repeat.
7. `/incidents/inc_007?tab=report`: failed simulated verification, restored snapshot and an unresolved outcome. Restoring the sample does not mark the incident resolved.

Approval is exact-candidate/hash/base-specific and requires passing validation. It never applies a patch. Apply requires its own confirmation. Reject never applies anything. The future backend must independently enforce all gates.

Dialogs retain the candidate, source revision, diff and validation evidence shown when opened. Changed evidence blocks confirmation. Passing validation requires nonempty passed checks for the exact candidate/hash. Mock apply rechecks current revision and evidence. Mock diff hashes are actual SHA-256 digests of the seeded diff text; no patch is executed.

## Checks

```powershell
npm.cmd run check
npm.cmd run build
$env:PLAYWRIGHT_BROWSERS_PATH = "$PWD/.playwright"
npx.cmd playwright install chromium
npm.cmd run test:e2e
```

`check` runs strict typechecking (including browser test source), ESLint and Vitest. Browser projects use two frontend-only Vite previews on 5183 (mock) and 5184 (HTTP). HTTP project responses are intercepted by Playwright; it never starts a FastAPI server or calls a live backend. The development server remains on 5173.

Browser coverage includes workflow gates, routes, search/sort, opaque pagination, monitoring, settings/reset, dialog focus loops, keyboard dismissal/focus restoration, pending submission behavior, and 320/360/768/1024/1440px layouts. Axe scans cover main views in light/dark themes. All browser journeys assert no uncaught page errors. Screenshots are generated in `test-results`; reviewed audit screenshots are retained under `docs/screenshots`.

Format with `npx.cmd prettier --write src tests *.ts *.js *.json index.html`.

Before building FastAPI, read `src/contracts/api-contract.md`, `docs/ADR-001-frontend-wire-projections.md` and `docs/ADR-002-audit-contract-clarifications.md`. The audit adds optional incident `scope` and `sort` query fields to filter before pagination; no endpoint or response shape changed. Runtime timestamp validation enforces the existing UTC contract. Both project blueprints document this addition.

Known limits: mock decisions are memory-only; candidate regeneration belongs to the future Manager; identity, real network integration, server CSRF and execution safety remain unverified without FastAPI. Chromium automation and axe scans do not replace screen-reader, touch-device or cross-browser testing. Quick actions use native HTML Popover and Dialog APIs, requiring a current browser. If storage is disabled, UI preferences work for the current session but cannot persist.

Read `docs/FRONTEND_AUDIT.md` for findings, changed files, actual validation results and remaining limits.

Read `docs/UX_REDESIGN.md` for the public/workspace navigation split, isolated learning adapter, onboarding, progressive disclosure and redesign screenshots. The redesign introduces no new API contracts or backend requirements. No demo video or source reference images were supplied; the media preview opens the interactive demo rather than pretending to play video.
