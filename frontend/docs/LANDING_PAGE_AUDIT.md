# Landing page audit and first improvement proposal

Date: 17 November 2026. Scope: incremental frontend development, beginning with an audit and proposal. No application code, routes, API contracts, or backend implementation changed in this pass.

## Existing foundation

- React 19, TypeScript and Vite; React Router with lazy page modules; TanStack Query for server data; Zod for executable contracts. Motion and Lucide are already installed. Tailwind is configured, while the current visual system primarily uses authored CSS.
- `src/app/App.tsx` separates `PublicShell` from `AppShell`. Public routes are `/`, `/demo`, `/onboarding`, `/docs`. Workspace routes include `/dashboard`, applications and application detail, incidents and incident detail, agents and agent detail, `/repair-testing`, `/approval-recovery`, `/history`, and `/settings`.
- Shared components include buttons, headings, panels, badges, dialogs, query states, feedback, pagination, incident lists, workflow, patch evidence, and review actions. Retain these instead of introducing a second UI library.
- `tokens.css` supplies navy text, blue actions (#1261d8), neutral surfaces, semantic colors, and dark-theme overrides. The font stack is Inter, Segoe UI, Arial; Inter is not loaded in `index.html` or the inspected styles. Cards generally use 12–20px radii and buttons 8px. Preserve the wordmark and established palette; consolidate component sizing gradually.
- The landing page already has a split hero, four benefit cards, seven selectable process stages, six agent cards, a demo invitation, eight workspace links, FAQ, and closing actions.
- Onboarding is a six-step, browser-local introduction with resume, restart and skip. The ten-step demo has approve/reject branches and a separate application action. These are existing features to improve, not missing features to rebuild.
- `DashboardPage` already shows application health, introduction/resume access, four derived metrics, workflow, recent incidents, and agents. Its many competing entry points are a later simplification opportunity.

## Landing findings, in priority order

1. **The hero does not immediately explain the job.** “Your applications. Understood. Your decisions.” communicates tone, but makes a new administrator read the paragraph to discover incident diagnosis and repair review. The forced three-line heading dominates the screen; the adjacent concept panel prioritizes code over an administrator's next action.
2. **The process has inconsistent levels of detail.** `content/product.ts` presents seven stages and groups application/verification under “Recover.” `components/workflow.tsx` presents eight operational stages with separate Local apply and Verify. The demo uses ten learning steps. These are compatible concepts, but the page does not explain their relationship. The six agent roles must remain distinct from human approval and operational stages.
3. **The requested motion is only partly present.** `product.css` gives benefit/platform cards a 3px hover lift and the concept panel a brief entrance. Hero buttons have shared color feedback. The landing workflow changes text on click but does not animate handoffs or show agent coordination. Six static role cards do not demonstrate six agents working together.
4. **Repeated explanation makes the page slow to scan.** Benefits, process, team, demo, workspace links and FAQ reiterate similar ideas. Every workspace preview uses the same abstract thumbnail. This adds length without helping visitors distinguish destinations.
5. **The demo section discusses a missing asset.** “No video has been supplied” is an implementation explanation. The working interactive demo is the stronger product experience and should be presented on its own merits, with its simulation label and transcript preserved.
6. **The visual treatment needs hierarchy more than decoration.** Frequent uppercase labels, similar bordered cards, small supporting text and large gaps compete with the content. Retain the blue/navy identity while reducing repeated framing and making one useful action prominent per section.
7. **Small-screen workflow discovery needs attention.** Stage buttons have a 116px minimum width in a horizontal scroller. At narrow widths most steps are initially offscreen. Offer a readable vertical or wrapping presentation with the selected explanation nearby, preserving every stage and keyboard access.
8. **Public navigation needs focus verification.** `AppShell` moves focus on route changes; `PublicShell` has no equivalent route-focus effect. Demo/onboarding content changes also need manual keyboard and screen-reader checks. Existing skip links, native accordions, pressed states, visible focus, 44px shared button targets, and reduced-motion rules are useful foundations.

## First implementation slice

Direction: preserve the existing brand and components. Use a calm SaaS presentation with design variance 5/10, motion intensity 4/10, and visual density 3/10. Animate explanation and feedback, keeping operational evidence readable.

### 1. Make the first screen concrete

- Proposed heading: “Understand incidents. Review fixes with confidence.”
- Proposed supporting copy: “Six AI agents organize evidence and proposed fixes. You review each change and decide whether to apply it.”
- Keep the two existing destinations: introduction at `/onboarding` and interactive demo at `/demo`. Use consistent action labels across hero and closing section, with one visually dominant action per location.
- Keep a concise, visible statement that this is a simulated local prototype. Avoid implying real monitoring, account creation, application connection or production recovery.
- Refine the existing preview around incident, evidence, tests and the review checkpoint. Use recorded sample content or an accurately labeled captured workspace image. Do not turn a concept illustration into a claim of live status.

### 2. Add purposeful interaction to existing cards and buttons

- Add once-per-view feature entrances: approximately 16px translation, 250–400ms duration and 50–70ms stagger.
- Use a restrained 2–3px hover lift, clear border feedback, and a small CTA-arrow translation. Provide equivalent focus feedback for links/buttons; informational cards remain noninteractive articles.
- Use existing Motion and CSS. Restrict movement to transform/opacity, avoid `transition: all` for new work, and respect both OS reduced motion and the saved preference. No new animation dependency is needed.

### 3. Explain the six-agent workflow through one sample incident

- Show Manager as the coordinator for Monitoring, Diagnosis, Repair, Testing and Reporting. Human approval is a distinct checkpoint, never a seventh agent.
- Present the same eight operational concepts as the workspace: Detect, Diagnose, Propose fix, Test, Human approval, Local apply, Verify, Report. The demo's ten steps can remain teaching steps without becoming another operational model.
- Provide explicit Play, Pause, Replay and manual selection. Animation illustrates a scenario and never triggers API mutations. Pause at human review; proceeding through the illustration must be clearly distinguished from approving or applying a real candidate.
- Keep selected-stage text available without animation. Reduced motion defaults to manual/static presentation. Avoid automatically announcing each animation tick through the current live region.
- Retain `#how-it-works` and `#team`, with concise role explanations and existing technical details still available.

### 4. Strengthen the path into the existing demo

- Replace missing-video language with a purposeful preview of the interactive walkthrough and a clear `/demo` link. Preserve accessible transcript content.
- Give workspace links distinct descriptions and less repetitive imagery/framing. Retain every current destination and the existing anchor IDs.
- Keep substantive onboarding and dashboard changes for the next slice: contextual onboarding examples, focus handling between lessons, and an attention-first dashboard that retains all current metrics and queues.

## Compatibility boundaries

`SentinelApi` remains the data boundary; query hooks continue to mediate workspace data. `HttpSentinelApi` uses configurable `/api/v1`, snake_case payloads, schema-versioned envelopes, cookies, CSRF headers and mutation idempotency keys. Keep endpoint paths, schemas, filters, cursor handling, status values and error behavior intact.

Keep approval and application separate, preserve frozen review evidence and exact candidate/hash/base checks, and retain failed, rejected and unresolved outcomes. The learning demo continues to use its isolated mock adapter even in API mode. Public animation uses frontend-owned explanatory state, not simulated changes to workspace state. Backend authentication and execution remain future work.

## Verification plan and audit evidence

- Re-ran `npm run check`: type checking, ESLint and all 42 tests across six files passed.
- Reviewed current source and repository screenshots for desktop/mobile presentation; screenshots are supporting evidence, not proof of a current browser run.
- Re-ran the existing public Playwright suite with the repository's `.playwright` browser installation: all eight tests passed in 30.6 seconds. Coverage includes landing interactions, both demo branches, onboarding persistence, 320/768/1440px layouts, theme switching and public axe scans. The first attempts encountered sandbox socket restrictions and an unset browser-cache path; the completed run used local socket permission and `PLAYWRIGHT_BROWSERS_PATH` as documented in the README.
- During implementation, retain the existing demo approve/reject, separate application, restart/exit, onboarding resume/skip, and HTTP payload regressions. Update copy-specific assertions deliberately.
- Validate light/dark themes at 320, 360, 768, 1024 and 1440px, keyboard-only operation, touch targets, reduced motion, pause/replay, selected-stage visibility and absence of page overflow. Run public axe checks and manually inspect focus/announcements. Automated axe checks alone do not establish full accessibility conformance.
- The current HTML has a title, description and theme color, but no canonical or social-preview metadata. Preserve URLs; add production metadata only when a deployment origin and share image exist. No ranking or analytics data was available for this audit.

Suggested first-change files: `src/pages/LandingPage.tsx`, `src/components/ProductVisual.tsx`, `src/content/product.ts`, `src/styles/product.css`, and focused landing browser assertions. Keep shared token changes small because public pages, onboarding and dashboard reuse these styles.
