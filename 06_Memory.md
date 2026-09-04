# 06_Memory.md — Living Memory Log (append-only)

> Format per entry:
> ```
> ### [Phase X] <short title> — <date>
> - Status: <NOT STARTED | IN PROGRESS | STABLE | BLOCKED>
> - Built: ...
> - Tested: ...
> - Stubbed/remaining: ...
> - Deviations/notes: ...
> - Next immediate step: ...
> ```

### [Phase 0] Setup & RAG Scaffolding
- Status: STABLE (RAG schemas, ParsedDocument, PDF chunking, chunk/fusion retrieval complete)
- Built: RAG module schemas and contract alignment. Fixed contract drift (2026-09-04) where `ParsedDocument.warnings` leaked into serialized outputs. Fixed Windows access violation regression (2026-09-04) during `CrossEncoder` model materialization by explicitly setting `TOKENIZERS_PARALLELISM=false` and `OMP_NUM_THREADS=1`.
- Tested: Python/pytest skeleton in place. 17/17 RAG tests passing.
- Stubbed/remaining: Actual model embeddings. Offline verification overrides these with Fake/Mock endpoints.
- Deviations/notes: none.
- Next immediate step: Phase 1 Ingestion.

### [Phase 4] Avatar, Voice & Video Synthesis — 2026-09-02
- Status: STABLE
- Built: Contract §6 (`TeachingSegment`) and §7 (`RenderedVideoSegment`) schemas, `TTSAdapter` (Contract §14) with Edge-TTS multilingual neural voices (`hi-IN-SwaraNeural`, `en-IN-NeerjaNeural`, `en-US-AriaNeural`) and offline acoustic fallback, word-level timestamp extraction and WebVTT caption generator, `AvatarAdapter` (Contract §14) with Viseme-driven 2D animated teacher avatar at 24 FPS with transparent RGBA frames and cue-reactive poses (`neutral`, `emphasis`, `questioning`), 6 specialized subject-aware visual renderers (`equation`, `graph`, `diagram`, `code`, `timeline`, `map`), `FFmpegCompositor` (1920x1080 canvas with 70% visual viewport, 30% top-right avatar PiP, bottom captions), and thread-safe async queue in `AvatarVoiceService`.
- Tested: 10 unit test suites in `modules/avatar_voice/tests/` and root `tests/`, covering multilingual voice resolution, fallback audio waveforms, viseme RMS energy modulation, 24 FPS frame counts, LaTeX font auto-scaling, code syntax highlighting, async job queue polling, and subject-awareness visual distinctness evaluation.
- Stubbed/remaining: Tier 2 Wav2Lip neural checkpoint integration (skeleton adapter built).
- Deviations/notes: Pure Python fallback acoustic generator and Pillow canvas compositor implemented to guarantee 100% test suite reliability across offline and non-GPU environments.
- Next immediate step: Connect `ai_agent_orchestration` and `backend` to `AvatarVoiceService.render_segment()`.

### [Phase 5 & 6] AI Agent Orchestration — 2026-09-04
- Status: STABLE
- Built: FSM (`TeacherOrchestrator`), `PlannerAgent`, `ExplainerAgent`, `QuestionerAgent`, `AssessmentAgent`, and `AdaptationController`.
- Tested: 27 unit and integration tests passing offline (`tests/unit/` and `tests/integration/`).
- Stubbed/remaining: `ml_core` evaluator is mocked.
- Deviations/notes: Adapted failure threshold to strictly match 1st fail -> MODIFY, 2nd fail -> REGENERATE, 3rd fail -> HUMAN.
- Next immediate step: ML Core implementation.

### [Phase 6] ML Core — 2026-09-04
- Status: STABLE (Source and Testing complete)
- Built: `EvaluationResult` schemas, `LLMAdapter` facade, deterministic MCQ Exact match evaluator, Hybrid Freeform evaluator using `sentence-transformers` for pre-filter thresholds with LLM judge fallback, Physics misconception taxonomy and classifier, deterministic Visual Type suggester. 20 isolated unit/integration tests with robust `FakeLLMAdapter` and `mock.patch` injection.
- Tested: Python import smoke check passed. 20 tests executed and verified locally (20 passed in 0.19s). Confirmed backwards-compatible with 27/27 Orchestrator unit tests.
- Stubbed/remaining: None.
- Deviations/notes: No file parsing is duplicated; ML Core solely acts on `rag` module chunks. Model downloads bypassed in tests via `mock.patch`.
- Next immediate step: Backend/Frontend integration.

### [Phase 7] Backend Integration (P0) — 2026-09-04
- Status: STABLE (P0 Source & Testing complete)
- Built: FastAPI app, `/sessions` REST routes for topic-based learning, WS `/sessions/{id}/live` driver mapping to `AIOperationService` state machine, in-memory repositories. 13 unit/integration tests fully covering P0 flows.
- Tested: 13/13 passing in 0.11s using `TestClient` and `websocket_connect` with `Mock` boundaries at `AIOperationService`.
- Stubbed/remaining: P1 (RAG upload integration, Postgres storage), P2 (advanced HUMAN intervention).
- Deviations/notes: No logic duplicated in Backend. Acts purely as a thin relay/FSM-driver feeding the orchestrator.
- Next immediate step: Backend testing phase (`task_backend_testing.md`).
