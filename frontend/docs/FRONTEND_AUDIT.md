# SENTINEL AI — frontend audit

Audit date: 2026-11-17. Scope: improve the existing React/Vite frontend only. No backend, execution worker, database or LLM integration was created.

## 1. Existing implementation findings

Read both project blueprints and the frontend README, then inspected routing, all pages and shared components, preferences, TanStack Query hooks, adapters, schemas, linked fixtures, styles, configuration and tests. The starting implementation already had useful routes, strict types, a common API interface, six logical agents, separate approval/apply, visibly simulated data and responsive styling. These were retained.

The requested reference file `docs/reference/sentinel-ai-reference.png` is missing. Visual review uses the written design direction and generated browser screenshots, not an unseen image.

Baseline validation actually passed: TypeScript, ESLint, 18 Vitest checks, production build and 7 Playwright tests. Passing baseline tests did not cover the problems below.

## 2. Problems identified

- High: confirmation submission used the latest candidate rather than retaining what the reviewer first saw. A background refresh could change the candidate during review.
- High: mock apply did not recheck current application revision or all validation checks. An aggregate passed label could conceal empty, mismatched or failing evidence.
- Medium: history/open/candidate queues filtered a first page capped at 100 records. Older matching records could disappear. Previous-page logic subtracted numeric offsets from documented opaque cursor tokens.
- Medium: quick actions lacked focus placement and light-dismiss behavior; the mobile floating button covered candidate status content.
- Medium: native dialog behavior did not maintain the strict Tab loop required by the new browser regression. Pending submission dismissal needed an explicit policy.
- Medium: API-mode agent labels and apply messages described all activity as simulated, or claimed verification was completed immediately after an accepted request.
- Medium: the workflow omitted controlled local application as a distinct step. Failed verification/restoration had no sample fixture, and verification headings used success styling regardless of outcome.
- Medium: timestamp schemas accepted arbitrary strings, local validation errors differed between adapters, and corrupt polling preferences could produce an invalid refresh interval.
- Lower: small touch targets, narrow panel headers, short-window sidebar overflow, generic missing-item errors, missing empty agent states, and a content-region focus outline affected usability.
- Lower: the unified diff hunk count was inconsistent and seed hashes were placeholders rather than digests of the displayed content.

## 3. Changes completed

Preserved the existing architecture, routes, original six incident IDs, six agent roles and team ownership. Added frozen review snapshots, exact evidence checks, current-revision checks, shared validation errors, UTC validation and an optional seventh scenario. Approval, application, verification and final reporting remain separate concepts.

Incident filtering/sorting now occurs in adapters before pagination. UI cursor history stores opaque tokens in URL `from` parameters; it never decodes or subtracts cursors. Queues, history and open lists are paginated rather than silently capped. Search is debounced, and filters survive retry/back/refresh. The optional `scope` and `sort` additions are documented in ADR-002 and both blueprints.

Main files changed or added:

- `src/components/ReviewActions.tsx`, `src/lib/approval.ts`: frozen candidate/hash/base/diff/revision/validation snapshots, evidence links, consistency checks and mode-aware confirmations.
- `src/components/ui.tsx`, `QuickActions.tsx`, `Outcome.tsx`, `Pagination.tsx`, `incidents.tsx`, `workflow.tsx`: focus, shortcuts, outcome semantics, cursor controls, semantic lists and the complete workflow.
- `src/pages/*`, `src/layouts/AppShell.tsx`, `src/app/App.tsx`: page improvements, localized route loading, navigation focus, queue scopes and truthful data-mode text.
- `src/hooks/queries.ts`, `useDebouncedValue.ts`, `src/lib/preferences.ts`, `src/app/preferences.tsx`: centralized health access, polling/error behavior and resilient browser preferences.
- `src/api/mockAdapter.ts`, `realAdapter.ts`, `errors.ts`, `src/contracts/*`: boundary validation, exact mock gates, scopes/sorting and handoff documentation.
- `src/mocks/fixtures.ts`: preserved fixtures plus unresolved restoration evidence, valid diff hunk counts, actual content digests and current mutation report timestamps.
- `src/styles/polish.css`, `tokens.css`, `src/main.tsx`: theme-aware refinements and responsive layout.
- `src/tests/audit.test.ts`, `review.test.tsx`, existing contract tests, `tests/e2e/*`, `playwright.config.ts`, `tsconfig.json`: regression and HTTP-mode browser coverage.
- README, ADR-002, both blueprints and this audit; the package manifest/lock add the missing DOM peer for existing React Testing Library.

## 4. UI/UX improvements

- Dashboard: kept derived KPIs and navigation; fixed mode-dependent recovery wording, preserved the shell during lazy loading and clarified the eight-stage workflow.
- Applications: retained search, filters and confirmed monitoring; related records now link to the full paginated incident list. Application names come from API data rather than row literals.
- Incidents: scope and sort controls, debounced search, safe URL filters, opaque cursor Previous/Next, readable mobile lists and retained inputs during errors.
- AI Agents: kept six cards and ownership, added explicit empty states, improved tablet/laptop columns and made activity captions reflect mock/API mode.
- Repair & Testing: paginated candidate queue, exact content hashes/diffs and distinct failed/error/timeout labels; review links remain separate from application.
- Approval & Recovery: pending/all scopes, a stable selected incident, frozen confirmation evidence, disabled reasons, pending-dialog protection and truthful apply acceptance messages.
- History: backend-compatible closed filtering before pagination, correct unresolved outcome and report access.
- Settings: 320px stacked controls, safe stored-value fallback, session operation when storage is unavailable, clear backend-owned read-only settings and confirmed reset.

The light sidebar, navy headings, blue/teal/purple accents, rounded cards and six-card desktop grid are retained. Motion is limited to brief page, modal, menu, hover and press feedback, with reduced-motion support. Native popover shortcuts focus the first link, dismiss on Escape/outside click, and route to actual filtered pages. On narrow screens the button uses reserved header space to avoid covering patch controls.

## 5. Accessibility improvements

Semantic incident lists with explicit severity/status/time labels; named result pagination; visible keyboard focus on interactive controls; route focus; dialog Tab/Shift+Tab wrapping, Escape handling and trigger restoration; accessible comment errors; non-color status labels; expanded touch targets; and live loading/error/notification announcements. Failed verification is displayed as failed, with restore status and limitations.

Light/dark contrast and layouts were checked using axe and browser screenshots. Automated checks cover the main pages and incident evidence/report views. This is bounded automated coverage, not a claim of full accessibility certification.

## 6. Backend compatibility findings

`SentinelApi`, adapter selection and canonical envelopes remain intact. UI data access uses query hooks. No component imports a fixture or calls fetch. FastAPI connection still requires environment configuration and a backend that honors the frozen contract, not rewriting components.

ADR-002 specifies optional list scopes/sorting, filter-before-pagination and deterministic tie breaking. UTC validation and exact nonempty passing checks enforce existing requirements. The backend must independently enforce identity, permissions, idempotency, CSRF, current revision, exact patch and approved application. An accepted apply request never establishes recovery.

HTTP browser tests use intercepted responses through the actual HTTP adapter, including exact separate approval/apply payloads, CSRF/idempotency headers, loading, 403, 404, offline and retry. They do not prove a live backend or authentication is implemented.

## 7. Test results

Final actual results: TypeScript passed; ESLint passed; 40 Vitest tests across 5 files passed; production build passed; all 15 Playwright tests passed (12 mock and 3 HTTP). Browser QA includes 320/360/768/1024/1440px, all routes, light/dark axe scans, original safety scenarios, cursor/sort/history, unresolved reports, native shortcuts, dialog focus and HTTP mode. All page-error assertions passed. Axe found no violations for the selected WCAG A/AA rules in the scanned views. The focus-loop regression was fixed and its assertions retained. See `verification.md` for coverage and commands.

Measured final build entry: 236.30 kB minified / 74.50 kB gzip, compared with baseline 235.64 / 74.29 kB. Route splitting remains enabled, without a large-chunk warning. Review/report rendering is shared rather than importing an entire detail page into the queue. No new production framework was introduced. Responsive screenshots and two dark-theme views were manually inspected and retained under `screenshots/audit-*`.

## 8. Remaining limitations

- The reference image is absent; no pixel-match assessment is possible.
- No live FastAPI, session bootstrap, server authorization, CSRF enforcement, repository indexing, tests or patch execution exists. The future backend must implement the documented optional list queries.
- Mock state resets on reload and is isolated per browser document. The optional verification-failure fixture demonstrates recorded restoration, not a real restore operation.
- Candidate regeneration/retry dispatch remains owned by the future Manager; the UI accurately displays revision-required evidence without inventing a run control.
- Chromium automation and axe scans do not replace manual screen-reader, real-device or Firefox/WebKit validation. Native Popover/Dialog support requires current browsers.
- Cookies require matching hostnames and exact-origin credentialed CORS; real authentication integration remains unverified. Browser preferences cannot persist when storage is disabled.
