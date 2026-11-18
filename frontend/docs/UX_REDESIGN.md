# SENTINEL AI — product experience redesign

## Landing background atmosphere

Added a landing-only signal-field background based on Taste's preserve/refine workflow and Uizze's polish guidance. Soft blue/teal fields, a masked edge grid and slowly drifting contour shapes give the existing colored cards a surrounding visual system. Text retains quieter central space and existing surfaces remain opaque. The Figma connector was inspected; no Figma source or artifact was used for this code-native CSS effect.

`LandingAtmosphere.tsx` owns pause/resume and page-visibility suspension. `landing-atmosphere.css` keeps the fixed decorative plane noninteractive and below public navigation/content, animates transforms only, reduces layers on mobile, and disables ambient movement for OS/saved reduced motion. It disappears on non-landing routes. Background controls do not change agent-flow or workflow-playback preferences.

Validation: 42 unit/component/contract tests, typecheck, ESLint, production build and 14 targeted browser checks passed. Checks cover pause/resume, click-through, route removal, reduced-motion mobile width, preserved card routes, existing learning journeys and public light/dark axe scans. Finished desktop/mobile screenshots were inspected after entrance and theme transitions settled and retained as `screenshots/atmosphere-*`.

## Embedded product video, 17 November 2026

Replaced the static demo-preview card with a real 94.25-second narrated agent and workspace tour. The thirteen chapters explain all six roles, the separate human decision/application/verification steps, and navigation through Dashboard, Applications, Incidents, Repair & Testing, Approval & Recovery, History, Settings, Documentation and the introduction/demo entry points. The tour uses actual frontend captures and consistently identifies sample data as simulated.

`ProductTourVideo.tsx` provides native playback/fullscreen controls, English WebVTT captions, chapter seeking, an always-available transcript and the existing interactive-demo link. It never autoplays. Media readiness is synchronized through metadata/data/can-play events so cached media and caption events cannot leave chapter controls disabled. The mobile layout and failure path retain access to the transcript. API adapters, schemas, approval gates and backend behavior were untouched.

The public MP4 is H.264/AAC, 1280×720, about 7.2 MB, with fast-start metadata. Source captures, narration, editable HyperFrames scenes, script, storyboard, timing, review and reproduction scripts live under `media/sentinel-tour` at the project root. Windows Microsoft Zira provides local speech synthesis; captions use utterance-level timing measured from generated audio. The full-resolution render is retained there separately.

Checks: production build, typecheck, lint and all 42 unit/component/contract tests passed. Existing public interactions, motion, responsive and light/dark axe checks passed; focused tests additionally verified actual playback, chapter seeks, thirteen caption cues, transcript content and unavailable-media fallback. HyperFrames check passed with no lint, runtime, contrast, audio or craft errors; informational scene-overlap notices correspond to intended dissolves. All chapter visuals were inspected through individual frames/contact sheets. The audio stream was measured for duration and level, not listened to. Vitest now excludes nested dependency/tool-cache files so cached video tooling is not treated as frontend tests.

## Premium landing refinement, 17 November 2026

Applied the Taste preserve-and-refine workflow to the existing frontend. The public presentation now has a detached navigation surface, a shorter two-line desktop hero, nested preview framing, rounded actions with animated arrow feedback, varied feature surfaces, and lighter agent/workspace listings. Existing routes, anchors, navigation labels, demo branches and onboarding behavior remain available. Public display typography uses the installed Bahnschrift/Segoe UI Variable system stack without third-party font requests.

`LandingMotion.tsx` centralizes public scroll reveals and OS/saved reduced-motion handling. Feature cards reveal and lift on hover; agent explanations enter with a restrained stagger. `LandingWorkflow.tsx` adds explicit play/pause/replay, manual selection, timed handoffs, visibility-aware scheduling and a pause at human review. Animation changes explanatory state only. Local application and verification are now distinct in the public eight-stage explanation, matching the workspace. Six agent roles and human approval remain separate concepts.

The demo invitation uses an actual captured sample dashboard, lazy-loaded from `public/images/dashboard-preview.png`, and focuses on the working walkthrough rather than an absent video. Its simulation disclosure and transcript remain. Public visual rules live in `styles/landing-premium.css`; backend adapters, schemas, payloads, safety checks and authorization assumptions were not changed.

Validation: typecheck, ESLint, all 42 unit/component/contract tests and production build passed. All 15 existing workspace/HTTP browser checks passed. After fixing playback visibility and step-number contrast, all 10 public checks passed, including two new animation/reduced-motion cases. A final four-check responsive/axe rerun passed after compacting the 320px navigation. Desktop, mobile and dark screenshots were visually inspected; retained hero captures are `screenshots/premium-hero-1440.png` and `screenshots/premium-hero-320.png`. These are Chromium and automated axe checks, not full accessibility or performance certification.

## Original UX problems

Visitors previously entered an operational workspace without an explanation of the product. Technical terms, candidate hashes and validation details appeared before first-time users understood the workflow. There was no public introduction, guided learning simulation, video fallback or resumable administrator introduction.

The existing tested application was extended, not rebuilt. Its routes, API interfaces, fixtures, ownership, state values and safety gates remain intact.

## New navigation structure

- `/`: public product site with top navigation, product explanation, workflow, agents, demo preview, workspace previews, FAQ and final calls to action.
- `/demo`: isolated ten-step learning simulation with Previous, Next, Restart and Exit.
- `/onboarding`: six-step administrator introduction with browser-local progress, Back, Next, Skip, resume and restart. No authentication or application registration is fabricated.
- `/docs`: readable in-app documentation with working links to the relevant features.
- Existing workspace routes remain unchanged, starting at `/dashboard`. Public navigation links to the workspace; workspace help links back to the product introduction and documentation.

Public pages and workspace share design tokens, theme preferences, buttons and icons but use distinct top-navigation and sidebar layouts. Existing shortcut destinations are retained alongside product help.

## Landing-page architecture

`PublicShell` supplies navigation, theme switching, footer and floating help shortcuts. Lazy-loaded `LandingPage` uses frontend-owned explanatory content in `content/product.ts`. `ProductVisual` is an original HTML/CSS concept illustration, explicitly labeled as a preview rather than live monitoring. No external images, brands, testimonials or operational statistics were invented.

The seven clickable workflow stages show responsibility, required information, output and administrator actions. The Manager coordinates throughout; human approval is not represented as an agent. The six role cards expand to technical descriptions without live statuses.

The media section explicitly says no video is available. It has a static preview, an accessible transcript and a link to the interactive demo. It has no fake player, duration or playback button. Repository reference images and video files were absent, so visual work follows an original composition rather than copying a reference.

## Onboarding flow

Welcome → six roles → local sample → incident evidence → approval boundaries → dashboard. Progress is saved under `sentinel.onboarding`, validated on read and safely ignored if storage is corrupt or unavailable. Next and Back save progress; Skip and completion mark the introduction done. Restart resets progress. The dashboard offers a first-time introduction, a resume link or a repeat tour according to saved state.

The introduction does not automatically redirect existing deep links, interrupt review dialogs or alter sample monitoring. Existing workspace browser tests remain valid. Onboarding is an educational preference, not identity or authorization.

## Interactive demo behavior

`api/learningClient.ts` creates a dedicated `MockSentinelApi` behind the existing `SentinelApi` interface. `useLearningDemo` owns this isolated instance and its query/mutation cache. It always uses simulated data, even when the main workspace is configured for HTTP. Public components do not import fixtures or call fetch.

The story covers sample error → detection → cited diagnosis → candidate → isolated checks → evidence review → approve/reject → separate application → verification → report. Next is blocked until a decision, and again until separate application on the approved branch. Reject skips application and verification and opens the rejection report. Previous revisits the recorded state; Restart creates a fresh isolated adapter. The demo never modifies workspace decisions, a real repository or an application, and never calls an LLM.

Existing candidate/hash/base revision matching, nonempty passing evidence, separate application and verification gates are reused rather than reimplemented as optimistic UI success. A unit test verifies isolation from the workspace and network.

## Workspace simplification

The dashboard now starts with application health, an understandable next-step invitation and access to the introduction. Existing derived incident KPIs, pending approvals, recent incidents, agent summaries and workflow remain available. No extra charts or fabricated activity feeds were added.

Candidate IDs, full hashes and revision metadata move into a named expandable technical section on Repair & Testing and incident review. The exact diff and validation results remain visible; the confirmation dialog still presents the frozen candidate identity. Existing page headings, explanations, filters, pagination, reports and disabled reasons are preserved.

## Design system and accessibility

Navy headings, blue primary actions, neutral surfaces and restrained teal/purple accents build on existing tokens. The hero uses a small gradient glow and a brief entrance; cards and buttons have modest hover feedback. Layouts collapse to stacked cards and a concise top bar at 320px. The decorative hero glow is clipped locally to prevent page overflow while workflow stages remain horizontally scrollable.

Both light and dark themes share the same preferences. Existing OS/user reduced-motion rules disable transitions. Native FAQ and role accordions provide keyboard interaction. The workflow exposes pressed state and a live explanation; tours have named progress indicators and explicit disabled-action hints. Existing accessible modal focus traps, errors and notifications remain intact. Public skip navigation targets a focusable main landmark. Floating help uses the existing keyboard/light-dismiss popover and links to introduction, process, docs and FAQ.

## Backend compatibility

No API endpoint, response schema, status, permission field or authentication assumption changed. No backend was built. Workspace components still consume the same hooks and adapter interface. The new explanatory content and onboarding are frontend-owned; the isolated learning adapter implements the existing interface. No new FastAPI requirements are introduced.

The existing HTTP-mode suite continues to test actual HTTP adapter requests using intercepted responses. It does not establish live backend functionality. The future backend must independently enforce authentication, permissions, CSRF, idempotency, current revision, approval and patch application safety.

## Validation and screenshots

Final actual results: TypeScript passed, ESLint passed, production build passed, all 42 unit/component/contract tests passed, and all 23 browser tests passed. All 15 existing workspace/API tests were retained and passed. The 8 added browser tests cover landing navigation, interactive workflow, role expansion, FAQ, media fallback, both learning-demo branches, restart/exit, onboarding completion/skip/resume, public theme switching and responsive layouts. Axe found no violations under the scanned WCAG A/AA rules in light/dark public and workspace views. These automated checks do not establish full accessibility conformance.

Screenshots are retained under `docs/screenshots/redesign-*`: landing desktop/mobile, dashboard desktop/mobile, interactive demo desktop/mobile, onboarding desktop/mobile and the dark landing page. Selected screenshots were visually inspected. Public axe checks run in light and dark themes; the existing main-page accessibility checks remain in place.

## Remaining limitations

- There are no source reference images or actual demo video. The static preview intentionally cannot play media.
- Learning progress is memory-only and resets when leaving/restarting the demo. Onboarding and appearance persist only when browser storage is available.
- The isolated learning scenario demonstrates a passing supported case or rejection; failed tests, unsupported logs, stale candidates and failed recovery remain working examples in the workspace.
- No live authentication, application registration, monitoring, repair execution or production recovery exists. All learning activity is simulated.
- Browser QA uses Chromium and automated axe rules; manual screen-reader, real touch-device and Firefox/WebKit validation remain follow-up work.
