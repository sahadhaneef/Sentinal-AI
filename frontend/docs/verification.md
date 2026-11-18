# Verification notes

Latest product redesign: typecheck, lint and production build passed; 42 unit/component/contract tests and all 23 browser tests passed. The original 15 browser tests remain intact. New coverage includes landing workflow/FAQ/media fallback, isolated approve/reject learning journeys, restart/exit, onboarding resume/completion/skip, public themes and 320/768/1440px public routes. Existing workspace coverage still includes 320/360/768/1024/1440px. New screenshots use `screenshots/redesign-*`. See `UX_REDESIGN.md` for details. The audit results below are retained as history.

Final audit result (2026-11-17): typecheck and lint passed; 40 Vitest tests in 5 files passed; 15 Playwright tests passed (12 mock, 3 HTTP); production build passed with route splitting. Axe found no violations for the selected WCAG A/AA rules in the scanned light/dark views. All browser page-error assertions passed. Retained and manually inspected audit screenshots use the `screenshots/audit-*` prefix; older unprefixed images are the initial implementation baseline.

Original implementation order: foundation → contracts/mocks → shell/navigation → main pages → detailed workflow → polish → verification. Audit order: inspect existing code and baseline → UI/UX → interactions → typed API readiness → regression tests → documentation and screenshot review. Baseline passed 18 Vitest and 7 Playwright tests; expanded tests exposed regressions that were corrected without removing assertions.

Automated coverage includes strict TypeScript, ESLint hooks rules, wire fixture validation, mock safety gates, HTTP status/schema/offline behavior, the approve/separate-apply/report/history journey, rejection, failed validation, unsupported manual review, stale conflicts, all navigation routes, deep refresh, search, monitoring, preferences, reset and not-found.

Browser QA checks 320/360/768/1024/1440px layouts across main routes, overflow, screenshots, native quick-action focus/Escape/outside dismissal, dialog Tab loops/comment validation/pending submission, opaque cursor back/refresh, sorting and unresolved restoration reports. Axe scans cover Dashboard, Applications and detail, Incidents, incident patch/tests and unresolved report, AI Agents, Repair & Testing, Approval & Recovery, History and Settings in both themes.

HTTP mode is a separate frontend preview at 5184, with network responses intercepted in Playwright. Tests use the real HTTP adapter and check separate exact decision/apply payloads, CSRF/idempotency headers, accepted-apply wording, loading, 403/404, preserved filters on retry and visible mobile offline state. No FastAPI service is started. Mock preview uses 5183. Normal development remains 5173.

Commands executed successfully: `npm.cmd run check`, `npm.cmd run build`, and `npm.cmd run test:e2e` with `PLAYWRIGHT_BROWSERS_PATH` set to the local `.playwright` installation. Strict typechecking includes E2E source. Final browser suite: 15 passed in approximately 1.5 minutes. Final build entry: 236.30 kB / 74.50 kB gzip. The dependency installation audit reported zero vulnerabilities.

Reference styling follows the written specification because the source image was absent. Chromium automation does not establish cross-browser or screen-reader conformance. No real FastAPI connectivity, authentication, CSRF enforcement, agent behavior or recovery is claimed.
