# task_backend_testing.md — Backend Testing (Agent Task Spec)

> Target executor: Antigravity coding agent. Run this task AFTER `task_backend_src.md` is
> complete and approved. Authoritative schema source: `instructions/Contract.md`.

## A. Testing Objective

Verify Backend is a reliable, correct integration boundary:
`Frontend ↔ Backend ↔ (RAG / AI Agent Orchestration / ML Core / Avatar & Voice)`.
Tests confirm Backend's own logic (routing, state machine, persistence, auth, contract
shaping) — not the correctness of already-tested module internals (RAG: implemented/tested;
Orchestration: 27 tests; ML Core: 20 tests; Avatar/Voice: implemented/tested).

## B. Mandatory Workflow

1. Inspect the implemented Backend source (from `task_backend_src.md`) and re-confirm current
   `instructions/Contract.md` shapes plus each integrated module's actual public interface.
2. Produce a concrete Backend testing plan: test file layout, what's mocked vs. real, list of
   scenarios mapped to Section E below, and any gaps/open questions.
3. **STOP** and present the plan for human approval before generating test files.
4. After approval, generate tests incrementally (unit layer first, then integration, then the
   mocked E2E flow).
5. Run tests incrementally per layer, not all at once at the end — fix as you go.
6. Fix only Backend defects revealed by these tests. If a test reveals a genuine contract
   mismatch or defect in another module's public interface, stop, document it precisely, and
   request approval before touching that module (per `03_Rules.md`).
7. Document final verification results (Section H) in the appropriate Backend
   progress/status doc — do not fabricate a "passed" status for anything not actually run.

## C. Test Structure

Organize under `modules/backend/tests/` (`unit/`, `integration/`) consistent with
`08_Folder_Structure.md`'s per-module `tests/` pattern. Cover:

- **schemas/** — Contract.md shape round-trip validation (serialize/deserialize) for every
  request/response/event type Backend produces or consumes.
- **auth/** — session-token issuance, verification, rejection of invalid/missing/expired tokens.
- **state/** — session state-machine transitions: valid transitions succeed, invalid ones are
  rejected without mutating state.
- **persistence/repositories/** — CRUD correctness for sessions, learner_profiles,
  assessment_reports, uploaded_documents metadata, rendered_segments metadata; storage adapter
  get/put/delete behavior.
- **api/** — one test module per REST endpoint (Section E items 1–6).
- **ws/** — WebSocket event handling: valid event → correct transition + correct forwarded
  payload; invalid event → structured error, no transition.
- **integrations/** — one test module per module adapter (rag/orchestration/ml_core/
  avatar_voice), asserting Backend calls the module's public interface with correctly-shaped
  input and correctly maps its output into Contract.md shapes.
- **e2e_mocked/** — one full mocked happy-path teaching session test (Section E item 15).

## D. Mocking Strategy (CRITICAL)

Backend tests must run with **no** live LLM APIs, external TTS/video APIs, external vector DB
services, network access, or large model downloads.

- Mock each of `rag`, `ai_agent_orchestration`, `ml_core`, `avatar_voice` at their **public
  interface boundary** (the same interface Backend's `integrations/` adapters call), returning
  Contract.md-shaped fixtures. Do not mock at a lower internal level — that would test
  Backend against an interface it doesn't actually use.
- Preserve the real interface signatures (inspect each module's actual public entrypoint first)
  so mocks don't silently drift from what the modules actually expose.
- For persistence, use the real repository implementation against SQLite/in-memory (whatever
  `task_backend_src.md` Section H settled on) rather than mocking persistence — this is
  Backend's own logic and should be tested for real.
- For the storage adapter (file bytes), use a temp-directory-backed real implementation, not
  mocked, unless it becomes impractical.

## E. Critical Scenarios (minimum required coverage)

1. Session creation — `POST /sessions` returns valid `session_id` + token, persisted.
2. Topic ingestion — `POST /sessions/{id}/topic` accepts valid `TopicRequest`, rejects malformed.
3. Upload ingestion — `POST /sessions/{id}/upload` happy path (mocked RAG parse success) and
   failure path (mocked RAG parse failure → document status=failed, structured error).
4. Lesson planning — `POST /sessions/{id}/plan` calls mocked Planner, returns valid `LessonPlan`,
   persists it, transitions state to `PLANNED`.
5. Learner profile retrieval — `GET /learners/{id}/profile` happy path + 404 for unknown learner.
6. Report retrieval — `GET /learners/{id}/report/{lesson_id}` happy path + 404 for unknown report.
7. Valid WebSocket session flow — connect, drive through
   `EXPLAINING → AWAITING_ANSWER → EVALUATING → ADAPTING(ALLOW) → EXPLAINING`, all module calls
   mocked, correct events forwarded at each step.
8. Invalid WebSocket event — malformed/unknown event type rejected with structured error, no
   state change.
9. Invalid state transition — e.g. `StudentResponse` sent while not `AWAITING_ANSWER` → rejected.
10. Answer → evaluation → adaptation flow — `StudentResponse` in → mocked `EvaluationResult` →
    mocked `AdaptationDecision` (cover ALLOW, MODIFY, REGENERATE, and HUMAN branches separately).
11. Disconnect/reconnect/resume — if implemented per `task_backend_src.md`: disconnect mid-lesson,
    reconnect, confirm resumed state matches persisted `current_state`/`lesson_id`/`node_id`. If
    not implemented (deferred to P1/P2 and not completed), mark this test as skipped/deferred
    rather than fabricating a pass.
12. Module failure propagation — mocked module raises/times out → Backend returns/forwards a
    structured error, does not crash, does not fabricate a fake success result.
13. Authentication/session rejection — missing/invalid token rejected on REST and WS.
14. Persistence of session state — state machine transitions are actually durable (re-read from
    the repository after a transition, not just held in memory).
15. Complete mocked happy-path teaching journey — session create → topic → plan → WS loop through
    multiple nodes with at least one ALLOW and one MODIFY/REGENERATE → assessing → COMPLETE →
    `AssessmentReport` persisted and retrievable via REST.

## F. Contract Tests

Add explicit tests asserting Backend's request/response/event payloads match
`instructions/Contract.md` field-for-field (required fields present, correct types/enums, no
undocumented extra fields relied upon by Backend logic) for every schema Backend touches:
`UploadRequest`, `TopicRequest`, `LearnerConstraints`, `ParsedDocument` (consumed), `LessonPlan`,
`TeachingSegment` (consumed), `RenderedVideoSegment` (consumed), `InteractionEvent`,
`StudentResponse`, `EvaluationResult` (consumed), `AdaptationDecision`, `AssessmentReport`,
`LearnerProfile`. Also assert each `integrations/` adapter calls the actual public interface
signature discovered during inspection — not a guessed one.

## G. Verification Commands

Provide exact commands (adapt to actual repo layout discovered during inspection):

- Backend suite only: `pytest modules/backend/tests/ -v`
- Existing module suites (confirm they still pass untouched — do not rewrite them):
  `pytest modules/ai_agent_orchestration/tests/ -v` (expect 27 passing)
  `pytest modules/ml_core/tests/ -v` (expect 20 passing)
  `pytest modules/rag/tests/ -v`
  `pytest modules/avatar_voice/tests/ -v`
- Combined regression: `pytest tests/ modules/ -v` or repo's existing
  `run_all_diagnostics.py` wrapper if present (check `scripts/`).
- Do not add/modify tests inside other modules' `tests/` directories — Backend testing must not
  duplicate or rewrite already-passing module test suites.

## H. Final Acceptance Criteria

Backend testing/implementation is complete for this task when:

- FastAPI app starts successfully with no import/startup errors.
- All P0 REST endpoints (Section E items 1, 2, 4) pass their tests.
- WS teaching loop (item 7) passes for the ALLOW path; MODIFY/REGENERATE/HUMAN covered at least
  by unit-level adaptation-branch tests even if full WS integration for them is P1.
- Session state is demonstrably server-authoritative and persisted (item 14).
- Every module call goes through the module's public interface, verified by contract tests
  (Section F) — no direct LLM/vector DB/TTS calls anywhere in Backend code.
- Session state persists sufficiently to support the demo; reconnect/resume tested if built,
  explicitly marked deferred if not.
- No test requires a live external service, network access, or model download.
- Existing RAG / AI Agent Orchestration (27) / ML Core (20) / Avatar-Voice test suites still
  pass unmodified after Backend integration.
- Final results reported honestly against commands in Section G — any skipped/deferred/failing
  item stated explicitly, never marked as passed without having been run.
