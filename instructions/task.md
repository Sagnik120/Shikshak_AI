# Shikshak AI — Prototype Improvements Task Plan

> No repo access. Source of truth: `README.md`, `repo_summary.md`, `Contract.md`, `01_PRD`, `02_Architecture`, `04_Phases`, `08_Folder_Structure`, `Rules_Design_Test_Details`, `current_overall_status`, both architecture diagrams, and 9 screenshots (landing, dashboard, new-lesson, my-lessons, progress, classroom video, classroom checkpoint w/ "From your material" panel). Where exact files/functions are unknown, this plan says "Antigravity should inspect…" rather than naming code. Antigravity has repo access and makes all file-level decisions itself, subject to approval where noted.

## 1. Objective
Implement three demo-critical improvements in the existing Shikshak AI hackathon prototype — mentor escalation with email notification, a visibly clear adaptation/escalation UI, and higher-quality teaching video — with minimal, reversible changes that reuse the existing FSM (`UNDERSTAND→PLAN→EXPLAIN→DEMONSTRATE→QUESTION→EVALUATE→ADAPT→CONTINUE/HUMAN`), contracts, WebSocket events, and modules (`backend`, `rag`, `ai_agent_orchestration`, `ml_core`, `avatar_voice`, `mlops`). Must respect the <512 MB runtime footprint on the deployed free-tier environment (per README, live at `shikshak-ai.onrender.com`).

## 2. Current-State Understanding
- **FSM & adaptation:** `Adaptation Controller` (Zone 3/`ai_agent_orchestration`) already implements ALLOW/MODIFY/REGENERATE/HUMAN on evaluation results from `ml_core`'s MCQ/Freeform evaluators + Misconception Taxonomy Engine. This works per README and status doc; only its visibility is weak.
- **Auth/security:** JWT access + rotating refresh tokens, bcrypt, OTP email verification, rate limiting are implemented (`backend`, Zone 1/2). An SMTP path for OTP email already exists — `dev_otp` is the fallback when SMTP is unconfigured (per README §"Configure environment variables"). This is the reusable channel for mentor emails.
- **Persistence:** SQLite WAL via SQLAlchemy; diagrammed tables include `users`, `lessons`, `interactions`, `reports`, `learner_profiles`, `otp_codes`, `refresh_tokens`, `documents`, `lesson_nodes`, `lesson_events` — no `mentors` table is shown, so one is likely new.
- **RAG grounding is real:** screenshot 7 (checkpoint + "FROM YOUR MATERIAL") shows retrieved document text displayed with the question — citation/grounding-to-frontend already has at least one working carrier.
- **Video pipeline (Zone 4 `avatar_voice`):** Edge-TTS → Viseme/WebVTT aligner → board renderers (Equation/Graph/Diagram/Code/Takeaway, via LaTeX/Matplotlib/Graphviz/Pygments) → FFmpeg 1080p 24 FPS compositor. Screenshot 5 shows a real teaching video (3:42) with a generic-looking "Concept Architecture & Process Flow" board — supports the diagram-fallback concern from the architecture, and confirms only one board type is shown per segment for a long duration (transition/pacing gap).
- **Frontend:** Vanilla JS SPA, 15 screens (per README), WebSocket-driven classroom (`classroom.html`). Curriculum sidebar already marks nodes "Being taught now" / "Has a checkpoint" — a state-labeling pattern to extend for MODIFY/REGENERATE/HUMAN, not invent fresh.
- **Deployment:** Render free tier (per README badge) — the source of the <512 MB constraint; Docker/Docker Compose noted in Zone 5.

## 3. Improvement Areas

### 3.1 Human Escalation & Mentor Notification
- **Current state:** FSM reaches `HUMAN` on persistent failure (diagrammed as state 9, "Persistent Fail" from ADAPT). Per the task brief, this currently only signals "human needed" — no mentor identity, no email.
- **Desired state:** Each student has one predefined mentor (name, email, identifier) stored persistently at account creation or shortly after. On `HUMAN` escalation, backend resolves the student's mentor and sends one email with: student info, lesson/topic, concept, checkpoint question, student's incorrect answer, misconception/evaluation info, consecutive-failure count, escalation reason, session info.
- **Survey findings:**
  - Minimum viable data model: one `mentors` (or reuse-adjacent) table/columns — `mentor_name`, `mentor_email`, optional `mentor_id`/`relation` — associated 1:1 with a student row, likely via a FK on `users`/`learner_profiles` or a small join table. Antigravity should inspect `backend`'s SQLAlchemy models to pick the least invasive shape (new table vs. added columns on the existing user/profile model).
  - Assignment point: simplest is at signup/account-creation flow (already produces a `users` row) — a fixed/default mentor or a mentor field on the signup form, whichever the existing signup handler most cheaply supports. Antigravity should inspect the auth/account creation endpoint(s) under `/api/auth`, `/api/account`.
  - Email integration: reuse the existing SMTP client used for OTP (per README, SMTP config already exists with a documented no-config fallback). Do not build a new mailer. If SMTP is unconfigured, log the intended email content server-side (mirroring the `dev_otp` fallback pattern) instead of failing the FSM transition — escalation must never block the student's session.
  - Content boundaries: never include other students' data, auth secrets/tokens, or full document contents — only the specific question/answer/concept/lesson context needed to act.
  - Duplicate prevention: gate sending on the FSM's own transition-into-`HUMAN` event firing once per lesson/session (or per node), not on every retry/reconnect; a simple "already escalated for this session/node" check (in-memory or a boolean/timestamp column) is sufficient for a hackathon — do not build a dedup/queue service.
  - Failure isolation: email send must be best-effort/non-blocking (e.g., fire-and-forget with try/except and a log line) so a mail failure never breaks the teaching flow or the WebSocket response to the student.
- **Recommended approach:** (1) small persistent mentor association per student (new minimal table or columns — Antigravity decides after inspecting models); (2) a single email-composition + send function triggered from the existing `HUMAN` transition point in the Adaptation Controller/FSM, reusing the existing SMTP client; (3) unconfigured-SMTP fallback = log only; (4) in-session/in-lesson idempotency flag to prevent duplicate emails.

### 3.2 Adaptation/Regeneration/Human-Escalation UX
- **Current state:** MODIFY → REGENERATE → HUMAN backend logic works; frontend shows this only via "small text/loading indicators" (per task brief) — not corroborated by a screenshot since none was captured mid-adaptation, but consistent with the plain WebSocket-driven UI seen elsewhere (e.g., the understated node-status labels in screenshot 6).
- **Desired state:** Distinct, unmistakable UI per transition: MODIFY → "Let's try another explanation" + clear loading state; REGENERATE → "Let's rethink this topic and create a new explanation" + lesson-regeneration indicator; HUMAN → "Your mentor has been notified" + escalation indicator. Must read backend FSM state, not invent local state.
- **Survey findings:**
  - A single reusable "adaptation status" UI component (banner/card/toast, driven by one WebSocket-delivered state enum) is the right shape — avoids duplicated markup/logic across screens and guarantees the UI can't drift from backend truth. Antigravity should inspect the existing WebSocket message types/handlers in the frontend (likely in a `classroom`-related JS file) to find the current event for adaptation decisions and extend/consume it rather than adding a parallel channel.
  - The component must map 1:1 to backend-emitted adaptation-decision values already defined in `Contract.md`/FSM (ALLOW/MODIFY/REGENERATE/HUMAN) — no new client-side inference of "wrongness streaks."
  - Loading/success/failure/timeout: show the status immediately on receiving the WS event; clear it once the next teaching content (or the mentor-notice) arrives; on a timeout/no-response, fall back to a neutral "still working" state rather than silently hanging — reuse whatever generic loading/error pattern the frontend already has (e.g., the "Waiting for RAG retrieval…"-style state seen in the existing Grounding panel) instead of inventing a new one.
  - Duplicate-message prevention: key the banner off the WS event/lesson-node id so a reconnect or resend doesn't stack duplicate banners.
  - Must not expose internal details (e.g., raw misconception taxonomy codes, prompt text) — student-facing copy only, per the three example messages given.
- **Recommended approach:** One small reusable frontend component driven entirely by the existing (or minimally extended) WebSocket adaptation-decision event; three fixed copy/state mappings (MODIFY/REGENERATE/HUMAN); dedupe by event/node id; graceful timeout fallback reusing existing loading-state patterns.

### 3.3 Multimodal Teaching Video Quality
- **Current state:** Avatar (viseme lip-sync) + narration + visual board, composited via FFmpeg (Zone 4). Screenshot 5 shows a single generic-looking board ("Concept Architecture & Process Flow") held for a multi-minute segment — consistent with the brief's concern about boards overstaying and not always being topic-specific.
- **Desired state:** More teacher-like avatar presentation (framing/gesture within a lightweight budget), topic-relevant and better-structured visual boards (equations, diagrams, graphs, key points, examples as appropriate to subject), and boards/segments that change over time rather than one static board per long segment — all within <512 MB additional runtime footprint, no new heavyweight models, no new external paid APIs.
- **Survey findings (per required dimensions):**
  - **Avatar:** The existing avatar is a rendered/composited asset (not a generative video model), so headroom exists for cheap procedural improvements: better PiP framing/cropping, and rule-based, keyframe/sprite-driven gestures (e.g., pre-authored gesture frames triggered by simple heuristics like "equation on screen → point" ) rather than any learned motion model. A true generative photoreal/gesture model is out of scope — likely >512 MB and/or requires GPU/external API, contradicting the hard constraint. Antigravity should inspect existing avatar assets/renderer config to see what frame/asset variety already exists before proposing new assets.
  - **Visual boards:** The existing renderer set (LaTeX equation, Matplotlib graph, Graphviz diagram, Pygments code, takeaway/summary cards) already covers the needed board types per the architecture diagram — the fix is deliberate *board-type selection per subject/content* and layout/typography polish, not a new rendering engine. Antigravity should inspect how `visual_type`/board selection currently maps content to a renderer and identify why a generic flowchart-style board appeared for what should likely have been an equation/diagram board.
  - **Slide transitions/pacing:** The existing compositor already produces a single continuous 1080p stream per segment; introducing multiple shorter visual "beats" within one teaching segment (concept → example → summary, timed to narration/VTT alignment) is achievable by having the Explainer/board-selection step emit more than one board per segment (reusing the existing WebVTT-based audio/viseme timing already in the pipeline) rather than building a new animation/transition system. This is the most technically involved of the three areas — plan for it as the async fallback if time runs short.
  - **Video-generation model alternatives:** Given the <512 MB constraint, explicit external generative avatar/video models (e.g., diffusion-based talking-head models) are not viable — they typically require GB-scale weights and/or GPU inference and/or a paid external API, none of which fit "offline, CPU-friendly, no new heavyweight deps." No such model is recommended; improvements come from better use of the existing renderer/compositor and content selection.
- **Recommended approach:** (1) fix visual-type/board selection so boards match subject content (equation for physics/math laws, diagram/graph where appropriate) using only existing renderers; (2) typography/layout polish within existing renderer templates; (3) lightweight avatar framing/gesture polish using existing assets only; (4) if time allows, multiple boards per segment timed via existing VTT alignment for a "concept→example→summary" feel. No new models, no new external APIs, no rewrite of the compositor.

## 4. Prioritized Task Breakdown

| ID | Task | Priority | Impact | Complexity | Risk | Dependencies | Expected Result |
|---|---|---|---|---|---|---|---|
| T1 | Inspect repo: user/auth models, FSM adaptation/HUMAN transition point, existing SMTP client, WS event types, board/visual-type selection logic | P0 | High (unblocks all) | Low | Low | None | Findings report before any edit |
| T2 | Add minimal persistent student→mentor association (name, email, identifier) | P0 | High | Low–Med | Low | T1 | Mentor resolvable per student |
| T3 | Wire mentor-notification email into existing `HUMAN` FSM transition, reusing SMTP client, with idempotency + non-blocking failure + unconfigured-SMTP log fallback | P0 | High | Med | Med (touches FSM) | T2, T1 | Real email (or logged content) with full educational context on escalation |
| T4 | Add reusable frontend adaptation-status component (MODIFY/REGENERATE/HUMAN copy + loading/timeout states) driven by existing/extended WS event | P0 | High | Low–Med | Low | T1 | Judge sees clear, backend-accurate adaptation messaging within seconds |
| T5 | Fix visual-type/board selection so board content matches subject/topic using existing renderers only | P1 | High | Med | Med | T1 | No more generic/mismatched boards |
| T6 | Typography/layout polish on existing board renderer templates | P1 | Med | Low | Low | T1 | More polished, readable boards |
| T7 | Lightweight avatar framing/gesture polish using existing assets | P2 | Med | Low–Med | Low | T1 | More teacher-like presentation, no new deps |
| T8 | Multiple boards per teaching segment (concept→example→summary), timed via existing VTT alignment | P2 | Med–High | High | Med (touches compositor) | T1, T5 | Boards change during a segment instead of one static board |
| T9 | Update relevant module docs to reflect new mentor table/field and any new WS event field | P1 | Low | Low | Low | T2, T3, T4 | Docs stay accurate |

## 5. Recommended Implementation Order
1. **T1** (read-only investigation across `backend` models, FSM/adaptation code, SMTP client, frontend WS handling, board-selection logic) — produces a short findings note and confirms/adjusts every assumption above before any edit.
2. **T2 → T3** (mentor data model, then email wiring) — these are sequential and together deliver Improvement 1 end-to-end.
3. **T4** (adaptation UI) can proceed in parallel with T2/T3 once T1 confirms the WS event shape, since it consumes but does not modify backend FSM logic (only possibly needs one new/extended WS field, coordinated with T3's escalation event).
4. **T5 → T6** (board selection correctness, then polish) before **T7** (avatar) and **T8** (multi-board segments), since T8 depends on T5 already picking correct board content.
5. **T9** (docs) last, after implementation is stable.

If time is constrained, complete P0 items (T1–T4) fully before touching any P1/P2 video-quality items; a working mentor-escalation + clear-UX demo is higher value than partial video polish.

## 6. Scope Boundaries
Do NOT attempt:
- A general-purpose mentor/tutoring management platform (multi-mentor routing, mentor dashboards, ticketing).
- A new notification/event bus or message queue for escalation.
- Any new generative avatar or talking-head video model, GPU-based or API-based.
- A full rewrite of the FFmpeg compositor or the board-rendering architecture.
- A new frontend framework or full frontend rewrite; extend the existing Vanilla JS SPA only.
- New database engines or infra beyond the existing SQLite/SQLAlchemy setup.
- Broad, unrelated refactors of FSM, RAG, or ML Core modules.
- Any change that pushes runtime memory meaningfully above the current footprint (avoid large model/dependency additions).
- Live Gemini calls, `.env` access, or Git operations by the agent (see §9).

## 7. Acceptance Criteria
- **Mentor escalation:** A student with an assigned mentor who triggers `HUMAN` escalation results in one email (or one logged equivalent if SMTP is unconfigured) containing student, lesson/topic, concept, checkpoint question, incorrect answer, misconception info, failure count, and escalation reason. No duplicate emails on retry/reconnect. Escalation never blocks or errors the student-facing session.
- **Adaptation UX:** On a first wrong answer, the student sees a MODIFY-specific message and loading indicator; on a second consecutive wrong answer, a REGENERATE-specific message and indicator; on persistent failure, a HUMAN-specific "mentor notified" message — each driven by an actual backend WS event, not client-side guessing. No stuck/ambiguous "small text" states remain.
- **Video quality:** A generated teaching video's board(s) are topically relevant to the segment's subject (no generic/mismatched board as in the observed "Concept Architecture & Process Flow" case) and readable; if T8 is completed, at least one segment shows more than one board over its duration, timed to narration. Avatar presentation is visibly cleaner (framing/gesture) without exceeding the <512 MB footprint.

## 8. Human Validation
To be performed by the human via `http://localhost:8000` (or the deployed Render URL) after each phase — Antigravity must not attempt live LLM/TTS calls itself.

| # | Scenario | Steps | Expected |
|---|---|---|---|
| H1 | Mentor email on escalation | Sign up/use a test student with an assigned mentor; answer a checkpoint incorrectly 3× consecutively to force HUMAN | Mentor's inbox (or server log if SMTP unconfigured) shows one message with the full context list from §3.1; no duplicate on page refresh/reconnect |
| H2 | Adaptation UI — MODIFY | Answer a checkpoint incorrectly once | "Let's try another explanation" + visible loading state appears, then new explanation loads |
| H3 | Adaptation UI — REGENERATE | Answer incorrectly a second consecutive time | "Let's rethink this topic…" + regeneration indicator appears, then lesson continues |
| H4 | Adaptation UI — HUMAN | Answer incorrectly a third consecutive time | "Your mentor has been notified" + escalation indicator; session does not hang or error |
| H5 | Video board relevance | Generate/watch a lesson on a concept with a formula (e.g., Newton's Laws) | Board shown matches the concept (equation/diagram), not a generic/mismatched board |
| H6 | Video board pacing (if T8 done) | Watch one full teaching segment | Board changes at least once during the segment, in sync with narration |
| H7 | Regression | Run a full lesson end-to-end (plan → teach → checkpoint → correct answer → completion) | No functional regression vs. current working behavior; no console/WS errors |

## 9. Implementation-Agent Instructions
- Inspect the actual repository first (models, FSM/adaptation code, SMTP client, WS handlers, board/visual-type selection) before writing any plan or code; do not assume file names beyond what this document or `Contract.md`/module docs establish.
- Treat `Contract.md` as authoritative; preserve all existing public contracts (LessonPlan, LessonNode, TeachingSegment, InteractionEvent, StudentResponse, EvaluationResult, AdaptationDecision, AssessmentReport, and any WS event schemas) unless a change is genuinely required.
- If a contract or schema change is required (e.g., a new WS field for escalation status, a new `mentors` table/columns), explicitly identify it, explain why, list affected modules, and get human approval before implementing — do not implement silently.
- Do not duplicate FSM/adaptation logic, mentor-resolution logic, or RAG logic in the frontend; the frontend only renders backend-delivered state.
- Preserve the explicit FSM architecture; do not collapse it into a single LLM prompt or ad hoc logic.
- Reuse existing cross-module contracts/events (SMTP client, WS channel, board renderers) rather than building parallel systems.
- Avoid unrelated refactoring; make the smallest patch that satisfies each task.
- Security: never read, print, or modify `.env`; never expose or inspect the Gemini API key or SMTP credentials; never call Gemini or any external AI API; do not perform live LLM/TTS/email-send testing — mark anything requiring a live run as `HUMAN LIVE TEST REQUIRED` and let the human execute §8.
- Token/time efficiency: inspect only relevant files first, avoid repository-wide scans, avoid rereading unchanged files, avoid unnecessary commands, make minimal patches, keep status updates concise, and maintain/update a task checklist mirroring §4 as work completes.
- No Git operations unless explicitly requested by the human.
- Update relevant module documentation (not README/architecture diagrams) after implementation to reflect any new mentor table/field or WS event addition, per §9's own instruction and §6's boundary against creating new docs.

## 10. Deferred / Future Improvements
- Full mentor-management platform (multiple mentors, reassignment UI, mentor-side dashboard/inbox).
- Escalation via SMS/push notifications or any channel beyond email.
- Generative/AI-driven avatar video (talking-head diffusion models, GPU-hosted avatar services) or any paid external avatar/video API.
- Full slide-transition/animation engine (fades, complex motion) beyond simple multi-board-per-segment timing.
- Subject-specific rendering engines beyond the existing renderer set (e.g., dedicated chemistry/biology diagram generators).
- General notification/event infrastructure (queues, pub/sub) for escalation dedup — current session/node-level flag is sufficient.
- Any new database engine, vector store, or infra beyond current SQLite/Chroma setup.
