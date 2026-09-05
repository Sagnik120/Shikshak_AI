# task_backend_src.md — Backend Source Implementation (Agent Task Spec)

> Target executor: Antigravity coding agent. This is an execution spec, not a tutorial.
> Authoritative schema source: `instructions/Contract.md`. Do not invent conflicting contracts.
> Time budget: ~1 day total for Backend + Frontend. Optimize ruthlessly for P0.

## A. Scope & Invariants

- Backend owns: FastAPI API surface, WebSocket session channel, session orchestration glue,
  lightweight auth/session token, persistence of session/learner/report/document/video
  *metadata*, server-authoritative teaching-session state machine, and integration calls into
  `rag`, `ai_agent_orchestration`, `ml_core`, `avatar_voice`.
- Backend does **not** own teaching/lesson intelligence. All planning, explanation, questioning,
  evaluation, and adaptation logic lives in `ai_agent_orchestration` / `ml_core`. Backend calls
  it; it never reimplements it.
- `instructions/Contract.md` is authoritative for every request/response/event shape. If a gap
  or ambiguity is found, do not invent a conflicting shape — flag it as an open question in the
  implementation plan (Step 2 below) rather than silently deciding.
- Existing modules (`rag`, `ai_agent_orchestration`, `ml_core`, `avatar_voice`) must remain
  independently testable and swappable. Backend integrates through each module's public
  interface only — never reaches into internals.
- Do not modify files outside `modules/backend/` (source, tests, instructions) unless an actual
  contract mismatch or integration defect is discovered in another module's public interface.
  If so: stop, document the defect precisely, and request approval before touching that module.
- No unrelated refactors, no speculative abstractions, no infra beyond what P0 requires.

## B. Repository Inspection (required before writing any code)

Claude has not inspected the live repository; this spec is derived from project docs only.
Antigravity MUST inspect the actual repo and reconcile before implementing:

- `instructions/Contract.md` — exact current schemas (may have evolved past what's summarized
  in `repo_summary.md`).
- `modules/backend/` — existing scaffold, `.gitkeep`, any stub files, `instructions/contract.md`
  and `instructions/detail_plan.md` for backend specifically.
- `modules/rag/src/` — actual public service entrypoint (e.g. a `RAGService` class/module),
  its method signatures, expected inputs/outputs vs. `ParsedDocument`.
- `modules/ai_agent_orchestration/src/` — public entrypoints for Planner, Explainer, Questioner,
  Adaptation Controller, Assessment Agent; how the FSM is invoked/stepped from outside.
- `modules/ml_core/src/` — public entrypoints for answer evaluation, misconception tagging,
  visual-type suggestion.
- `modules/avatar_voice/src/` — public entrypoint (e.g. `AvatarVoiceService`), how segment
  rendering is requested and how results (sync or async/queued) are returned.
- Root config: `pyproject.toml`/`requirements.txt`, `pytest.ini`/`pyproject` test config,
  `.gitignore` (confirm `.env` coverage), any existing logging setup, `10_Git_Discipline.md`,
  `11_Token_Efficiency.md`, `09_Progress_Tracker.md`.
- Existing error-handling/logging conventions used in already-implemented modules, to keep
  Backend stylistically consistent rather than introducing a new pattern.

## C. Mandatory Implementation Workflow

1. Inspect the repository per Section B.
2. Produce a concrete Backend implementation plan (file list, endpoint-by-endpoint behavior,
   integration call sites, persistence choice, open questions/contract gaps).
3. **STOP** and present the plan for human approval. Do not write source yet.
4. After approval, implement in phases (suggested order): (1) app skeleton + config + auth,
   (2) persistence layer, (3) REST endpoints, (4) module integration adapters, (5) WebSocket
   state-machine relay, (6) error handling pass, (7) source verification (Section L).
5. After each phase, verify it runs/imports cleanly before starting the next.
6. Update/generate only the Backend-relevant progress/status docs required by repo conventions
   (e.g. `09_Progress_Tracker.md` entry, `modules/backend/instructions/` notes) — no unrelated
   doc rewrites.
7. Keep all changes scoped to `modules/backend/` unless Section A's exception applies, and if it
   does, log it per `03_Rules.md` (propose change, log in `06_Memory.md`, wait for approval).

## D. Backend Source Folder Structure (adapt after inspection)

Practical MVP layout under `modules/backend/src/` — treat names as defaults, not mandates;
reconcile with any existing scaffold/conventions found in Section B:

```
src/
├── main.py                # FastAPI app factory, startup/shutdown, router mounting
├── config.py               # env-based settings (no hardcoded paths/secrets)
├── auth/                   # session-token issuance + verification dependency
├── api/                    # REST routers (sessions, upload, topic, plan, learners, reports)
├── ws/                     # WebSocket endpoint + event dispatch/state-machine driver
├── state/                  # session state machine definition + transition logic
├── persistence/            # repositories (sessions, learner_profiles, assessment_reports,
│                            #   uploaded_documents, rendered_segments) + storage adapter
├── integrations/           # thin adapters calling rag / ai_agent_orchestration / ml_core /
│                            #   avatar_voice public interfaces; contract (de)serialization
├── schemas/                # pydantic models mirroring Contract.md exactly
└── errors.py                # shared exception types + FastAPI error handlers
```

## E. REST API Implementation

For each endpoint, implement per this responsibility/contract mapping. Validate all
request/response bodies against `schemas/` models generated from Contract.md — do not invent
fields.

- **POST /sessions** — Creates session (`CREATED` state), issues session token (Section I).
  No module calls. Persist session row. Return `session_id` + token.
- **POST /sessions/{id}/upload** — Validates session + auth. Accepts `UploadRequest` (multipart
  per Contract §1). Persist `uploaded_documents` metadata (status=pending), store bytes to the
  storage adapter (Section H), call `rag` to parse → `ParsedDocument`. Transition session to
  `INGESTING` then back to a ready state on success. On parse failure: structured error, session
  state unchanged, document status=failed.
- **POST /sessions/{id}/topic** — Validates session + auth. Accepts `TopicRequest` (Contract §2).
  No RAG call required (topic-only path). Store constraints on session for the Planner call.
- **POST /sessions/{id}/plan** — Requires session in a state where either a `ParsedDocument` or
  topic is available. Calls `ai_agent_orchestration` Planner with the appropriate input, returns
  `LessonPlan` (Contract §5), persists it against the session, transitions state to `PLANNED`.
- **GET /learners/{id}/profile** — Auth-checked read from `learner_profiles` repository, shaped
  as `LearnerProfile` (Contract §13). 404 if absent.
- **GET /learners/{id}/report/{lesson_id}** — Auth-checked read from `assessment_reports`
  repository, shaped as `AssessmentReport` (Contract §12). 404 if absent.

For every endpoint specify in the implementation plan (Step 2 of Section C): validation rules,
auth requirement, module(s) invoked, persistence writes, and failure-mode responses (see
Section J).

## F. WebSocket Implementation (CRITICAL)

`WS /sessions/{id}/live` — Backend acts strictly as a **thin relay + server-authoritative
state-machine driver**, never as a source of teaching logic.

Responsibilities:
- Authenticate the connection (session token) before accepting.
- Receive events matching Contract.md §6–11 types (`TeachingSegment` triggers,
  `InteractionEvent`, `StudentResponse`, etc.) — derive exact wire event shapes from Contract.md
  as inspected in Section B; do not invent new event envelopes not implied by the contract.
  If Contract.md doesn't fully specify a WS envelope, propose a minimal wrapper (e.g.
  `{event_type, payload}`) in the implementation plan for approval rather than assuming.
- Validate every inbound event against its schema before acting; reject malformed events with a
  structured error event, no state change.
- Drive the session state machine, calling the appropriate module for each transition:

```
CREATED → INGESTING → PLANNED → EXPLAINING → AWAITING_ANSWER → EVALUATING → ADAPTING →
  (loop → EXPLAINING) or (→ ASSESSING) → COMPLETE
```

  - `PLANNED → EXPLAINING`: call `ai_agent_orchestration` Explainer for the next `LessonNode` →
    `TeachingSegment`; call `avatar_voice` to render → `RenderedVideoSegment`; forward to client.
  - `EXPLAINING → AWAITING_ANSWER`: call Questioner for `InteractionEvent` at checkpoint; forward
    to client; persist state.
  - `AWAITING_ANSWER → EVALUATING`: receive `StudentResponse` from client; call `ml_core`
    evaluator → `EvaluationResult`.
  - `EVALUATING → ADAPTING`: call Adaptation Controller → `AdaptationDecision`
    (ALLOW/MODIFY/REGENERATE/HUMAN); persist decision; forward to client (audit-log panel per
    `05_Design.md`).
  - `ADAPTING → EXPLAINING` (loop) or `→ ASSESSING`: on lesson completion, call Assessment Agent
    → `AssessmentReport`, persist, transition to `COMPLETE`.
  - `HUMAN` decisions: surface to client as a distinct event; do not auto-resolve.
- Persist `current_state`, `lesson_id`, `node_id` after every transition so a reconnect can
  resume mid-lesson (best-effort for MVP: on reconnect, look up persisted state and replay the
  minimal event needed to resync the client, not full history).
- Never call an LLM/vector DB/TTS/model directly from WS handling code — only through the
  `integrations/` adapters from Section G.

## G. Cross-Module Integration

Priority: this is the highest-risk area given the 1-day budget — get the call sites right early.

- **RAG**: called from upload ingestion (parse) and, if the actual `RAGService` interface
  requires it, from Planner/Explainer calls that need retrieval context — but only via
  `ai_agent_orchestration`'s existing interface if orchestration already wraps retrieval; do not
  duplicate retrieval-calling logic in Backend if orchestration already does it. Inspect first.
- **AI Agent Orchestration**: called for Planner, Explainer, Questioner, Adaptation Controller,
  Assessment Agent — one adapter function per stage, each translating Backend/session state into
  the module's actual function signature and back into Contract.md shapes.
- **ML Core**: called for answer evaluation / misconception tagging from the WS evaluation step;
  also usable for visual-type suggestion if orchestration doesn't already call it internally —
  confirm via inspection to avoid double-calling.
- **Avatar/Voice**: called to render each `TeachingSegment` → `RenderedVideoSegment`; confirm
  whether the real interface is sync or async/queued (repo_summary implies async enqueue) and
  adapt WS flow accordingly (may need a polling/callback step rather than a blocking call).

Hard rule: Backend must never call an LLM API, vector DB, or TTS provider directly, and never
reach into module internals — only the public service interfaces found in Section B. Inspect
each module's actual public entrypoint/signature before writing its adapter in
`integrations/`; do not assume signatures from this doc's prose.

## H. Persistence

MVP-safe persistence abstraction, repository-per-entity pattern:

- `sessions`, `learner_profiles`, `assessment_reports`, `uploaded_documents` (metadata only),
  `rendered_segments` (metadata only).
- File/video bytes: local filesystem for hackathon MVP, accessed only through a `StorageAdapter`
  interface (get/put/delete by key) — no raw paths scattered through business logic — so it can
  later be swapped for S3-compatible storage without touching call sites.
- If Postgres setup is impractical in the current environment (confirm during inspection),
  choose the simplest repository-consistent alternative (e.g. SQLite via the same ORM/ODM
  patterns, or an in-memory/JSON-file-backed repository) that preserves the same repository
  interfaces, so swapping to Postgres later is a implementation-only change. Do not overengineer
  migrations tooling for a 1-day hackathon.

## I. Authentication

Lightweight session-token auth only, per `detail_plan.md`:
- Token issued on `POST /sessions`, required on all subsequent REST calls and the WS handshake
  for that session.
- `learner_id` may be a persisted anonymous/device identifier; no full account system.
- No password/OAuth flows unless already scaffolded elsewhere — confirm during inspection before
  adding anything beyond token-per-session.

## J. Error Handling / Resilience

Define structured (not crashing) handling for:
- Invalid/unknown `session_id` or expired token → 401/404 with structured error body.
- Malformed REST or WS payload → 422 / structured WS error event, no state mutation.
- Downstream module failure (RAG/orchestration/ml_core/avatar_voice raises or times out) →
  catch, log with context, return/forward a structured error; do not silently swallow or fake a
  success result (per `03_Rules.md` rule 5 — never fabricate results).
- Upload failure (bad file type, parse failure) → document status=failed, structured error,
  session state unaffected.
- WebSocket disconnect → persist last known state; on reconnect, resume from persisted state.
- Invalid state transition attempted (e.g. answer submitted when not `AWAITING_ANSWER`) → reject
  with structured error, no transition.
- Missing lesson/node referenced by an event → structured 404-equivalent WS error.
- Avatar/voice render unavailable/failed → surface a structured error event to client rather
  than blocking the loop indefinitely; consider (if time allows) a text-only fallback path, but
  do not build this if it risks the P0 happy path (Section K).

## K. Demo-First Reliability (P0/P1/P2)

Given ~1 day remaining for Backend + Frontend combined:

**P0 (required for working demo):**
- `POST /sessions`, `POST /sessions/{id}/topic`, `POST /sessions/{id}/plan`.
- WS happy path: `PLANNED → EXPLAINING → AWAITING_ANSWER → EVALUATING → ADAPTING(ALLOW) →
  EXPLAINING → ... → ASSESSING → COMPLETE` for a topic-based (no-upload) lesson.
- One correct-answer path fully working end-to-end through all four modules.
- Basic session-token auth.
- In-memory or SQLite persistence sufficient to survive the demo session.

**P1 (important if time permits):**
- `POST /sessions/{id}/upload` + RAG-grounded lesson path.
- MODIFY/REGENERATE adaptation paths (not just ALLOW).
- WS reconnect/resume.
- `GET /learners/{id}/profile`, `GET /learners/{id}/report/{lesson_id}`.

**P2 (stretch/defer):**
- HUMAN decision UX beyond a basic surfaced event.
- S3-compatible storage swap.
- Postgres if SQLite/in-memory was used first.
- Rich error taxonomy beyond structured pass-through.

Do not let P1/P2 work delay P0. Build P0 fully working before touching P1.

## L. Source Verification Commands

After implementation, run (adapt exact paths/commands to what inspection reveals — these are
illustrative, not guaranteed to match the repo verbatim):

- Import/compile check: `python -c "import modules.backend.src.main"` or equivalent per actual
  package layout.
- FastAPI startup check: run the app with `uvicorn` (or repo's existing runner) and confirm no
  startup exceptions, e.g. `uvicorn modules.backend.src.main:app --port 8000` then a basic
  `curl http://localhost:8000/sessions -X POST`.
- WebSocket smoke test: a minimal script/client opening `WS /sessions/{id}/live`, sending one
  valid event, confirming a structured response.
- Relevant pytest command(s) once tests exist (see `task_backend_testing.md`) — do not run tests
  as part of this source task beyond a basic smoke pass; full testing is the separate task.

Report actual results of these commands in the phase verification (Section C step 5) — never
claim a check passed without having run it.
