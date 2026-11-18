# SENTINEL AI — Frontend-First UI/UX and Integration Specification

> Implementation plan for Codex in VS Code. Build a real navigable, accessible frontend NOW; backend comes LATER. Use `BACKEND_ARCHITECTURE.md` as the single source of API and safety constraints. Current screens use **explicitly labeled simulated data** via a mock API adapter, not a fake operational backend.

## 1. Product goals
Make an incident-repair workflow understandable to a first-time user in seconds. The UI should feel polished, friendly and professional without technical clutter. Every navigation item opens a useful route; every enabled action has a visible result. Advanced evidence is progressively disclosed rather than filling the default screen. Keep the six-agent workflow visible and human approval unmistakable.

## 2. Reference screenshot: design direction
Use uploaded screenshot as **visual inspiration**, not a pixel-for-pixel requirement: bright off-white background, fixed light sidebar, dark navy headings, blue primary accent, teal/green success accents, soft shadows, rounded cards, clear whitespace, outlined icons, six agent cards in a 3×2 desktop grid, horizontal workflow illustration at top. Top status pill and small accent gradients are acceptable. Improve usability: readable text size, consistent spacing, visible focus rings, keyboard access, real responsive mobile layout, accessible contrast. Avoid overcrowding or excessive gradients.

## 3. Frontend stack
- React 18+ with TypeScript (strict), Vite, Tailwind CSS.
- React Router for real nested routes and deep links.
- TanStack Query for server/mock data fetching, caching, invalidation and polling.
- React Hook Form + Zod for forms and validation.
- Lucide React icons, Framer Motion/Motion for subtle animations (respect reduced motion).
- Recharts for optional simple dashboard trends; no charts without meaningful data.
- Vitest + React Testing Library + MSW (or equivalent typed mock adapter), Playwright for end-to-end journeys.
- Use CSS design tokens and reusable components, not hardcoded repeated styles.

## 4. Suggested frontend tree
```text
frontend/
  public/{logo.svg,illustrations/}
  src/
    app/{App.tsx,router.tsx,providers.tsx}
    layouts/{AppShell.tsx,Sidebar.tsx,Topbar.tsx,MobileNav.tsx}
    pages/{DashboardPage.tsx,ApplicationsPage.tsx,ApplicationDetailPage.tsx,IncidentsPage.tsx,IncidentDetailPage.tsx,AgentsPage.tsx,AgentDetailPage.tsx,RepairTestingPage.tsx,ApprovalRecoveryPage.tsx,IncidentHistoryPage.tsx,SettingsPage.tsx,NotFoundPage.tsx}
    components/{ui/,workflow/,agents/,incidents/,patches/,charts/,feedback/}
    contracts/{types.ts,schemas.ts,api-contract.md}
    api/{client.ts,interfaces.ts,realAdapter.ts,mockAdapter.ts,queryKeys.ts}
    mocks/{fixtures.ts,scenarios.ts,handlers.ts}
    hooks/{useIncidents.ts,useAgents.ts,useApplications.ts,useDashboard.ts}
    lib/{format.ts,status.ts,permissions.ts,accessibility.ts}
    styles/{globals.css,tokens.css}
    tests/{unit/,integration/,e2e/}
  .env.example
  README.md
```

## 5. Route map — EVERY sidebar item must work
| Sidebar item | Route | Minimum useful content and actions |
|---|---|---|
| Dashboard | `/dashboard` | 4 concise KPI cards, recent incidents, workflow summary, active agent count, latest activity, links to details |
| Applications | `/applications` | search/filter demo apps, status, monitoring indicator, open detail, start/stop monitoring in mock mode with confirmation |
| Application detail | `/applications/:id` | name, configured revision, recent incidents, monitoring status, supported sample errors |
| Incidents | `/incidents` | searchable/filterable paginated table/cards, severity, status, app, detected time, open incident |
| Incident detail | `/incidents/:id` | header, status/stage, timeline, evidence, diagnosis, patch candidate, validation, approval status, verification, report link; tabs/accordions |
| AI Agents | `/agents` | workflow banner and 6 cards (Manager, Monitoring, Diagnosis, Repair, Testing, Reporting), statuses and last activity |
| Agent detail | `/agents/:type` | purpose, inputs/outputs, recent runs, supported actions and status explanations; no fictional controls |
| Repair & Testing | `/repair-testing` | candidate queue, diff viewer, validation check list, outcome labels, links to incidents; NO direct unapproved apply |
| Approval & Recovery | `/approval-recovery` | review queue, exact candidate/hash/base, diff, tests, approve/reject buttons, approved candidate apply action, verification/restore status |
| Incident History | `/history` | timeline of closed/resolved/rejected/unresolved incidents; report access, filters |
| Settings | `/settings` | theme, reduced-motion preference, polling interval, demo-mode indicator, safe monitoring preferences; backend-owned settings clearly distinguished |
| Not found | `*` | friendly explanation + Dashboard link |

Navigation must support direct URL refresh, browser back/forward, active states, and mobile drawer close on navigation. Sidebar labels match screenshot: Dashboard, Applications, Incidents, AI Agents, Repair & Testing, Approval & Recovery, Incident History, Settings.

## 6. Page-specific interaction details
### Dashboard
- KPI cards: total incidents, open incidents, awaiting approval, resolved (always derived from current data).
- A simple `How SENTINEL AI works` row: Detect -> Analyze -> Diagnose -> Propose Fix -> Test -> Human Approval -> Local Verify -> Report.
- Recent incidents: click row to open detail; filter chips link to Incidents route.
- Agent overview: click an agent to open detail.
- Show `Demo data` label when mock mode is active; no claim of live operations.

### AI Agents (closest to screenshot)
- Page heading `AI Agents`, one-line explanation, aggregate status derived from six agent records; never hardcode `All Agents Operational`.
- Workflow stepper icons and arrows; horizontally scroll on narrow viewports with accessible labels.
- Six cards in this order: Manager, Monitoring, Diagnosis, Repair, Testing, Reporting.
- Each card: name/icon, true state (`idle`, `running`, `completed`, `error`, `offline`), short responsibility, current task or `No active task`, recent activity or `No recent activity`, `View details` link.
- Cards are accessible buttons/links, with hover lift (2–4 px) and keyboard focus ring; status not conveyed by color alone.
- Use screenshot palette: navy, royal blue, teal, pale aqua, purple. Preserve consistent card heights without truncating important content.

### Incidents and incident detail
- Table on desktop, stacked cards on mobile. Filter by app/severity/status; search error type/ID; pagination with empty results message.
- Detail: stage stepper, incident summary, source log snippet (redacted), diagnosis evidence with file/line/revision, patch diff in monospace, validation checks with statuses, decision and verification, report.
- Never enable Approve before required validation passes. Show disabled reason and offer link to tests.
- Show explicit `Needs manual review` for unsupported or uncertain diagnosis.

### Repair & Testing
- Candidate cards show version, base revision, changed files, patch hash (short visual + full copy), validation status and last run.
- Diff viewer with line numbers, added/removed lines, horizontal overflow and copy. Accessible plain-text alternative.
- Display checks with passed/failed/error/timeout distinctly; include duration and expandable evidence.
- `Review for approval` navigates to Approval & Recovery; no magical `Fix now` button.

### Approval & Recovery
- Strong human-review emphasis: exact patch version, candidate ID, hash, base revision, evidence, tests.
- `Approve candidate` opens confirmation dialog summarizing scope and clarifying this only authorizes a local demo patch.
- `Reject candidate` allows optional comment and confirmation.
- `Apply approved patch to local demo` is a SEPARATE confirmed action, enabled only when backend/mock contract says `can_apply`.
- Show `Applying`, `Verifying`, `Resolved`, `Restore needed`, `Unresolved`, `Rejected` states with audit timeline.
- On 409 stale candidate, close dialog, refetch, show clear notice and require review of new candidate.

### Settings
- Local UI settings persisted in localStorage: light/dark/system theme, motion preference, optional density and polling preference.
- Backend settings, if added later, use typed GET/PATCH and validation; do not store secrets or pretend to configure nonexistent integrations.

## 7. Design system
| Token | Recommendation |
|---|---|
| Background | `#F7F9FC` |
| Surface | `#FFFFFF` |
| Primary text | `#10172F` |
| Secondary text | `#526078` |
| Primary blue | `#1261D8` |
| Teal | `#0F9E91` |
| Purple | `#7C3AED` |
| Border | `#E3EAF3` |
| Success | `#13834B` |
| Warning | `#9A6700` |
| Danger | `#C03535` |
| Radii | 12–16px cards; 10px buttons; pill for status |
| Spacing | 4/8/12/16/24/32px scale |
| Typography | Inter or system sans, 16px body, 14px secondary minimum where practical |

Use clear color contrast (WCAG AA), no tiny gray-on-gray body text, icon+text labels, restrained shadow. Desktop sidebar approx 240–260px; content max-width 1440px; responsive breakpoints around 640/1024/1280px. Cards: 3 columns on wide desktop, 2 tablet, 1 mobile. Sticky top bar on mobile if useful.

## 8. Animations and floating controls
- Page transition: subtle 120–200ms opacity/translate, not distracting.
- Cards: hover elevation and small translate; workflow nodes can softly pulse **only when truly running**.
- Status changes: brief icon/label transition; skeletons while fetching; progress for known test counts only.
- Floating action button (FAB) bottom right: `Quick actions` opens a small labeled menu with `View incidents`, `Review approvals`, `Open help`; never triggers a repair without explicit confirmation. Hide/collapse near dialogs and on small screens to avoid blocking content.
- Optional floating `Back to top` on long pages.
- Toasts for success/error, accessible `aria-live`; no autoplaying confetti, excessive motion or fake streaming activity.
- Respect `prefers-reduced-motion` and user setting; all functionality works without animations.

## 9. Contract-first API integration — MOST IMPORTANT
Define `SentinelApi` interface and two implementations: `MockSentinelApi` and `HttpSentinelApi`. Components consume only hooks -> interface, never import mock fixtures or call fetch directly.

```ts
export interface SentinelApi {
  getDashboardSummary(): Promise<ApiResponse<DashboardSummary>>;
  listApplications(): Promise<ApiResponse<Application[]>>;
  getApplication(id: string): Promise<ApiResponse<Application>>;
  listIncidents(filters?: IncidentFilters): Promise<ApiResponse<Paginated<Incident>>>;
  getIncident(id: string): Promise<ApiResponse<IncidentDetail>>;
  getIncidentEvents(id: string): Promise<ApiResponse<IncidentEvent[]>>;
  listAgents(): Promise<ApiResponse<AgentSummary[]>>;
  getAgent(type: AgentType): Promise<ApiResponse<AgentDetail>>;
  listPatches(incidentId: string): Promise<ApiResponse<PatchCandidate[]>>;
  getPatch(candidateId: string): Promise<ApiResponse<PatchCandidate>>;
  getValidation(candidateId: string): Promise<ApiResponse<ValidationResult>>;
  decide(incidentId: string, body: ApprovalRequest): Promise<ApiResponse<ApprovalDecision>>;
  applyApprovedPatch(incidentId: string, body: ApplyRequest): Promise<ApiResponse<ApplicationAttempt>>;
  getReport(incidentId: string): Promise<ApiResponse<IncidentReport>>;
  getSettings(): Promise<ApiResponse<SafeBackendSettings>>;
  updateSettings(body: Partial<SafeBackendSettings>): Promise<ApiResponse<SafeBackendSettings>>;
}
```

Use `VITE_DATA_SOURCE=mock|api` and `VITE_API_BASE_URL=http://localhost:8000/api/v1`; `src/api/client.ts` selects adapter once. **Never scatter environment checks across components.** `mock` must be the default until backend is implemented. Both adapters return identical shapes and error codes; mock mutation changes a shared in-memory state store and notifies query invalidation so UI actually updates.

### Canonical shared types
```ts
type AgentType = 'manager'|'monitoring'|'diagnosis'|'repair'|'testing'|'reporting';
type AgentStatus = 'idle'|'running'|'completed'|'error'|'offline';
type Severity = 'low'|'medium'|'high'|'critical';
type CheckStatus = 'passed'|'failed'|'error'|'timeout'|'not_run';
type Decision = 'approve'|'reject';
type RunState = 'detected'|'diagnosing'|'generating_patch'|'validating'|'revision_requested'|'awaiting_approval'|'approved'|'applying'|'verifying'|'restoring'|'resolved'|'rejected'|'manual_review'|'unresolved'|'error'|'reported';
interface ApiResponse<T> { data:T; meta:{request_id:string; schema_version:'1.0'} }
interface ApiError { error:{code:string;message:string;details:Record<string,unknown>};meta:{request_id:string;schema_version:'1.0'} }
interface ApprovalRequest {candidate_id:string;patch_hash:string;base_revision:string;decision:Decision;comment?:string}
interface ApplyRequest {candidate_id:string;patch_hash:string;base_revision:string}
```

Define full `Application`, `Incident`, `IncidentDetail`, `AgentSummary`, `AgentDetail`, `IncidentEvent`, `PatchCandidate`, `ValidationResult`, `ApprovalDecision`, `ApplicationAttempt`, `IncidentReport`, `DashboardSummary`, `SafeBackendSettings` and pagination types in `src/contracts/types.ts` following backend document fields. Use Zod schemas for API response validation at development boundaries. Use snake_case for API properties; UI labels can be humanized.

### Endpoint mapping
| Frontend call | Backend endpoint |
|---|---|
| getDashboardSummary | GET `/dashboard/summary` |
| listApplications/getApplication | GET `/applications`, `/applications/:id` |
| listIncidents/getIncident/getIncidentEvents | GET `/incidents`, `/incidents/:id`, `/incidents/:id/events` |
| listAgents/getAgent | GET `/agents`, `/agents/:type` |
| listPatches/getPatch/getValidation | GET `/incidents/:id/patches`, `/patches/:id`, `/patches/:id/validation` |
| decide | POST `/incidents/:id/decision` |
| applyApprovedPatch | POST `/incidents/:id/apply` |
| getReport | GET `/incidents/:id/report` |
| getSettings/updateSettings | GET/PATCH `/settings` |

Implement monitoring start/stop via additional typed methods mapping to backend document endpoints. Build GET `/health` check for API mode and show `Backend unavailable` rather than `Operational` when disconnected. In mock mode, show a persistent but unobtrusive `Demo mode — simulated data` indicator.

## 10. Mock scenarios must demonstrate real navigation and state
Seed at least these linked fixtures, with one coherent ID across screens:
1. `inc_001`: supported registration null-value error, `awaiting_approval`, diagnosis with revision-bound source citation, candidate `patch_001`, validation `passed`, full review path.
2. `inc_002`: tests `failed`, retry/revision path, approval unavailable.
3. `inc_003`: unsupported log, `manual_review`, no invented root cause.
4. `inc_004`: rejected patch, unchanged demo, report marked rejected.
5. `inc_005`: verified resolved incident with final report.
6. `inc_006`: stale candidate scenario returning 409; display safe conflict handling.

For `inc_001`, Approve updates decision and enables Apply; Apply transitions through a clearly **simulated** verification result and produces report/history updates. Reject updates state and report without application. No mock action executes code, modifies the real filesystem, or calls an LLM. Mock delays may simulate loading, but statuses must reflect deterministic mock state. Reset demo data action in Settings with confirmation.

## 11. UX states for EVERY page
- Loading: skeleton cards/table rows.
- Empty: helpful message + meaningful navigation, not blank space.
- Error: friendly text, retry action, diagnostic detail expandable; preserve current filter/input.
- Offline/backend unavailable: clear banner in API mode; never switch silently to mock.
- Unauthorized: sign-in/access-required state, no hidden security bypass.
- No permission: disabled controls with explanation.
- Success: confirmation toast and refreshed query data.
- Conflict: candidate changed, invalidate queries and require fresh review.
- Long text: line wrap/scroll for logs and diffs; copy controls with feedback.

## 12. Accessibility and responsiveness
- Keyboard navigation for sidebar, cards, dropdowns, tabs, dialogs and floating actions; Escape closes overlays, focus returns to trigger.
- Proper headings, landmark regions, labels, visible focus rings, ARIA status announcements.
- Dialog focus trap; buttons have descriptive accessible names; icons are decorative when adjacent to text.
- Do not communicate status by color alone. Tooltips never hold essential information.
- Touch targets ~44px; test 360px mobile, 768px tablet, 1440px desktop.
- Tables have mobile card alternative, workflow horizontally scrolls without breaking, no horizontal page overflow.
- All animations disabled/reduced under user or OS reduced-motion preference.

## 13. Authentication and approval UI boundary
Frontend may show demo local developer identity in mock mode; do not claim that it is secure auth. In real mode, identity comes from backend session. The UI never decides whether a patch is actually safe; backend provides action flags and independently validates candidate ID/hash/base, tests and identity. Display approvals as human decisions, not automated agent actions. A successful validation is NOT an approval; an approval is NOT an application.

## 14. Suggested Codex implementation phases (frontend only)
**Phase 0 — Foundation:** Read both MD files; initialize Vite React TS strict, Tailwind, routing, tokens, lint/test tools, env examples. No backend server.

**Phase 1 — Contract and mock layer:** Define complete shared types, `SentinelApi`, error handling, deterministic linked fixtures, mock and HTTP adapters, TanStack Query hooks; write contract tests before complex UI.

**Phase 2 — Shell and navigation:** Sidebar/topbar/mobile nav, logo, active states, all route placeholders with useful headings and working links, theme settings.

**Phase 3 — Main pages:** Dashboard, Applications, Incidents, AI Agents matching screenshot's visual language. Every card/row opens real detail route.

**Phase 4 — Detailed workflow:** Incident detail/timeline, evidence citations, patch diff, validation results, Approval & Recovery, reports and history; safe mock approve/reject/apply state transitions.

**Phase 5 — Polish:** FAB quick actions, tasteful motion, loading/empty/error states, accessibility, mobile layouts, keyboard support, reduced-motion.

**Phase 6 — Verification:** Unit, integration and E2E tests, responsive screenshots, manual checklist; produce backend handoff mapping endpoints/types/fixtures.

## 15. Definition of done (frontend)
- Every sidebar item navigates to meaningful content; direct URL refresh works.
- Every enabled button has an actual interaction or route; no dead controls.
- Agent cards show six logical agents with truthful mock statuses.
- One full mock scenario: incident -> diagnosis -> diff -> tests -> human approval -> separate apply -> simulated verification -> report.
- Reject, failed tests, manual review and stale candidate paths also work.
- No approval before passing required tests; no apply before approval.
- Mock vs real data mode is explicit and visible.
- Frontend uses only typed API adapter/hooks; swapping `VITE_DATA_SOURCE=api` requires no component rewrites.
- 360px/768px/1440px layouts work; keyboard and reduced-motion supported.
- Tests pass, no console errors, clear README startup instructions.

## 16. Codex operating instructions
1. Read BOTH `FRONTEND_SPECIFICATION.md` and `BACKEND_ARCHITECTURE.md` before writing code.
2. Build **frontend only** now. Do not create FastAPI routes, databases, workers or real patch execution yet.
3. Follow the uploaded screenshot's overall design, but improve legibility, responsiveness and accessibility.
4. Keep six agent names, team ownership and approval gates aligned with the backend blueprint.
5. Create a real page for every sidebar option; never use placeholder buttons that do nothing.
6. Implement typed API contracts and mock/HTTP adapter boundary FIRST.
7. Simulated data must be visibly identified; never claim real agents are running.
8. Keep source code modular, clean and simple. Prefer small reusable components and understandable naming.
9. At the end of each phase, run typecheck, lint and tests; fix failures before proceeding.
10. When backend development starts, implement the documented endpoints/contracts, then switch only the adapter configuration. Document any contract change on both sides.

## 17. VS Code / Codex first instruction
Copy/paste this into Codex after placing both Markdown files at project root:

> Read `FRONTEND_SPECIFICATION.md` and `BACKEND_ARCHITECTURE.md` completely. We are building the SENTINEL AI **frontend only** now, using React + TypeScript + Vite + Tailwind. Follow the uploaded reference UI as a visual direction. Implement Phase 0 and Phase 1 first: strict TS project setup, routing foundation, complete shared API types, `SentinelApi` interface, deterministic mock adapter, HTTP adapter, query hooks, env config and contract tests. Do not build the backend yet. Make sure every future sidebar page and button can use these same contracts. Label mock data clearly. After finishing, run checks and summarize files changed, tests and next steps. Do not skip ahead to fake backend behavior.

## Implemented frontend contract addendum (2026-11-17)
The frontend-only implementation uses `frontend/src/contracts/schemas.ts` as its executable wire contract. See `frontend/src/contracts/api-contract.md` for endpoint mapping and `frontend/docs/ADR-001-frontend-wire-projections.md` for embedded sanitized evidence/diff/report projections, pagination, the `search` query extension and cookie/CSRF convention. Both adapters use these same shapes. The failed-test fixture exposes bounded revision-required status; candidate regeneration remains a future Manager responsibility, without a fictional UI execution control. Mock decisions are in-memory; UI preferences persist locally. No backend implementation has been added.

## Audit contract clarification (2026-11-17)
See `frontend/docs/ADR-002-audit-contract-clarifications.md`. Incident lists, history and queues use optional typed `scope` and `sort` filters before pagination; the UI retains visited opaque cursors without arithmetic. The original six linked fixtures are preserved, with `inc_007` added for simulated failed verification/restoration/unresolved outcome. Confirmations freeze reviewed candidate and validation evidence; changing evidence requires fresh review. Runtime UTC and shared validation-error handling enforce existing requirements. No backend is implemented.
