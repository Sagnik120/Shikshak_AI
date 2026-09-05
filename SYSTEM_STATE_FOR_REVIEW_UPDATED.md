# SYSTEM STATE FOR REVIEW: SHIKSHAK AI (TECHNICAL AUDIT BRIEF)

> **Auditor Notice**: This document is an unsparing, literal, code-level audit of the **Shikshak AI** repository updated on 2026-09-05. It evaluates actual implemented source code in `src/` across all modules against existing documentation claims, hackathon specifications, and architectural blueprints.

---

## 0. Repo Map

### Directory Hierarchy (Root to Level 3)
```
Shikshak_AI/
├── 00B_SPEC_UPGRADES.md                  # Hackathon problem statement amendments
├── 00_ANTIGRAVITY_START_HERE.md          # Developer session bootstrap instructions
├── 01_PRD.md                             # High-level product requirements document
├── 02_Architecture.md                    # System architectural specification
├── 03_Rules.md                           # Coding rules and engineering discipline
├── 04_Phases.md                          # 10 sequential delivery phases
├── 05_Design.md                          # UI/UX and interaction design
├── 06_Memory.md                          # Living execution log across phases
├── 07_Test.md                            # Testing strategy and guidelines
├── 08_Folder_Structure.md                # Target directory layout spec
├── 09_Progress_Tracker.md                # Status checklist
├── 10_Git_Discipline.md                  # Commit and branch standards
├── 11_Token_Efficiency.md                # Context window optimization guide
├── new_phases.md                         # Stage 2 enhancements spec
├── pytest.ini                            # Pytest configuration (with --import-mode=importlib)
├── requirements.txt                      # Python dependencies
├── docs/                                 # Central documentation directory
│   ├── issues.md                         # Active: Master issues index
│   ├── issues_faced.md                   # Active: Detailed postmortems
│   └── progress.md                       # Active: Phase & requirement status tracker
├── instructions/                         # Root instructions and canonical contract
│   ├── Contract.md                       # CANONICAL Master Cross-Module Contract (§1–§14)
│   └── Overview.md                       # Project mission overview
├── scripts/                              # Verification & diagnostic utilities
│   ├── preflight_check.py                # Cross-platform preflight health check CLI
│   ├── run_avatar_voice_diagnostics.py   # Offline & online TTS/Avatar/Video test runner
│   └── run_rag_diagnostics.py            # End-to-end RAG ingestion and retrieval runner
├── tests/                                # Global test harness
│   ├── conftest.py                       # Global fixtures
│   ├── unit/                             # Unit tests for RAG & Avatar/Voice components
│   ├── integration/                      # Internal module pipeline integration tests
│   ├── eval/                             # Groundedness, recall/precision, and subject benchmarks
│   └── smoke/                            # Basic import and instantiation sanity checks
└── modules/                              # Domain modules
    ├── rag/                              # Ingestion, chunking, embeddings, vector search, reranking
    │   ├── docs/ (00_OVERALL_GAP_ANALYSIS.md, 01_rag_module_fix_plan.md, rag_detail.md)
    │   ├── instructions/ (contract.md, detail_plan.md, detailed_design.md, overview.md)
    │   ├── src/ (chunking/, embedding/, grounding/, indexing/, parsing/, retrieval/, models.py, service.py)
    │   └── tests/ (unit/, eval/, integration/)
    ├── avatar_voice/                     # Voice synthesis, 2D/neural avatar, visuals, compositing
    │   ├── docs/ (00_OVERALL_GAP_ANALYSIS.md, 02_avatar_voice_module_fix_plan.md, avatar_voice_detail.md)
    │   ├── instructions/ (contract.md, detail_plan.md, detailed_design_avatar_voice.md, overview.md)
    │   ├── src/ (avatar/, compositor/, tts/, visuals/, models.py, service.py)
    │   └── tests/ (unit/, eval/, integration/)
    ├── ml_core/                          # Student answer evaluation & misconception analysis
    │   ├── docs/ (ml_core_detail.md)
    │   ├── instructions/ (contract.md, detail_plan.md, overview.md)
    │   ├── src/ (evaluator.py, heuristics.py, misconceptions.py, service.py, models.py)
    │   └── tests/ (unit/, integration/)
    ├── ai_agent_orchestration/           # Multi-agent pedagogical brain (Planner, Explainer, Questioner, Adaptation, Assessor)
    │   ├── docs/ (ai_agent_orchestration_detail.md)
    │   ├── instructions/ (contract.md, detail_plan.md, overview.md)
    │   ├── src/
    │   │   ├── adapters/ (llm_adapter.py, gemini_adapter.py)
    │   │   ├── agents/ (base.py, planner.py, explainer.py, questioner.py, adaptation_controller.py, assessment.py)
    │   │   ├── schemas/ (lesson.py, teaching.py, interaction.py, assessment.py, evaluation.py)
    │   │   ├── state_machine/ (fsm.py, orchestrator.py, session.py)
    │   │   └── service.py (AIOperationService)
    │   └── tests/ (unit/, integration/)
    ├── backend/                          # FastAPI REST API, WebSocket duplex relay, persistence & DI container
    │   ├── docs/ (backend_detail.md)
    │   ├── instructions/ (contract.md, detail_plan.md, overview.md)
    │   ├── src/
    │   │   ├── api/ (rest.py, upload.py, ws.py, learners.py)
    │   │   ├── auth.py (HMAC-SHA256 session token generation & verification)
    │   │   ├── integrations/ (container.py - unifies RAG, Avatar, ML Core, and Orchestrator)
    │   │   ├── persistence/ (repositories.py, storage.py)
    │   │   ├── schemas.py (REST/WS request and response validation)
    │   │   └── app.py (FastAPI application factory)
    │   └── tests/ (unit/, integration/, e2e_mocked/)
    └── frontend/                         # Split-screen classroom web interface (Next phase)
        ├── docs/ (frontend_detail.md, frontend_design.md)
        ├── instructions/ (contract.md, detail_plan.md, overview.md)
        ├── src/ (.gitkeep)
        └── tests/ (.gitkeep)
```

### Module Purposes & Implementation Status

| Module Folder | Top-Level Purpose | Local Detail Doc Path | Implementation Status | Test Suite Status |
|---|---|---|:---:|:---:|
| `modules/rag` | Document ingestion (PDF, DOCX, PPTX, TXT), multilingual parsing (Hindi/Bengali), Indic subword token budgeting, hybrid BGE-M3 vector search, calibrated two-threshold reranking, and citation grounding. | `modules/rag/docs/rag_detail.md` | **100% Implemented** | **18/18 Passed** |
| `modules/avatar_voice` | Multimedia synthesis pipeline: Edge-TTS neural speech with W3C SSML cue prosody, 24 FPS 4-viseme 2D avatar, Tier-2 MuseTalk neural adapter, 6 visual renderers, progressive step timing with duration conservation, and dual-path FFmpeg compositor. | `modules/avatar_voice/docs/avatar_voice_detail.md` | **100% Implemented** | **24/24 Passed** |
| `modules/ml_core` | ML student evaluation, semantic similarity & MCQ exact match scoring, misconception taxonomy classifier, partial credit computation, and visual type heuristics. | `modules/ml_core/docs/ml_core_detail.md` | **100% Implemented** | **All Passed** |
| `modules/ai_agent_orchestration` | Multi-agent state machine coordinating 5 specialized agents (Planner, Explainer, Questioner, Adaptation Controller, Assessor), FSM teaching loop, and Gemini LLM adapter with SmartMock fallback. | `modules/ai_agent_orchestration/docs/ai_agent_orchestration_detail.md` | **100% Implemented** | **34/34 Passed** |
| `modules/backend` | FastAPI application serving REST endpoints, WebSocket `/ws/teach` bidirectional duplex relays, session authentication, session checkpointing, learner profiles, and DI container. | `modules/backend/docs/backend_detail.md` | **100% Implemented** | **31/31 Passed** |
| `modules/frontend` | Next.js / React web application with split-screen layout, subtitle bar, interactive question overlays, and live pedagogy audit feed. | `modules/frontend/docs/frontend_design.md` | Blueprint ready; UI in progress | Scaffolded |

---

## 1. The Master Contract Compliance

### 1.1 Canonical Contract File
Authoritative master contract: `instructions/Contract.md`.

### 1.2 Actual Implementation of Contracts §1–§14 in Source Code

All 14 cross-module contracts defined in `instructions/Contract.md` now have direct, 1-to-1 Pydantic model implementations in the codebase:

1. **`Contract §1: UploadRequest`**: Implemented in [`modules/backend/src/schemas.py`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/modules/backend/src/schemas.py) and consumed by `/api/v1/documents/upload`.
2. **`Contract §2: TopicRequest`**: Implemented in [`modules/backend/src/schemas.py`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/modules/backend/src/schemas.py) and consumed by `/api/v1/topic`.
3. **`Contract §3: LearnerConstraints`**: Implemented in [`modules/ai_agent_orchestration/src/schemas/lesson.py`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/modules/ai_agent_orchestration/src/schemas/lesson.py).
4. **`Contract §4: ParsedDocument`**: Implemented in [`modules/rag/src/models.py`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/modules/rag/src/models.py).
5. **`Contract §5: LessonPlan`**: Implemented in [`modules/ai_agent_orchestration/src/schemas/lesson.py`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/modules/ai_agent_orchestration/src/schemas/lesson.py).
6. **`Contract §6: TeachingSegment`**: Implemented in [`modules/ai_agent_orchestration/src/schemas/teaching.py`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/modules/ai_agent_orchestration/src/schemas/teaching.py) and consumed by `AvatarVoiceService`.
7. **`Contract §7: RenderedVideoSegment`**: Implemented in [`modules/avatar_voice/src/models.py`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/modules/avatar_voice/src/models.py).
8. **`Contract §8: InteractionEvent`**: Implemented in [`modules/ai_agent_orchestration/src/schemas/interaction.py`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/modules/ai_agent_orchestration/src/schemas/interaction.py).
9. **`Contract §9: StudentResponse`**: Implemented in [`modules/ai_agent_orchestration/src/schemas/interaction.py`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/modules/ai_agent_orchestration/src/schemas/interaction.py).
10. **`Contract §10: EvaluationResult`**: Implemented in [`modules/ai_agent_orchestration/src/schemas/evaluation.py`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/modules/ai_agent_orchestration/src/schemas/evaluation.py) and generated by `MLCoreService.evaluate_answer()`.
11. **`Contract §11: AdaptationDecision`**: Implemented in [`modules/ai_agent_orchestration/src/schemas/evaluation.py`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/modules/ai_agent_orchestration/src/schemas/evaluation.py) with actions `ALLOW`, `MODIFY`, `REGENERATE`, `HUMAN`.
12. **`Contract §12: AssessmentReport`**: Implemented in [`modules/ai_agent_orchestration/src/schemas/assessment.py`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/modules/ai_agent_orchestration/src/schemas/assessment.py).
13. **`Contract §13: LearnerProfile`**: Implemented in [`modules/ai_agent_orchestration/src/schemas/assessment.py`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/modules/ai_agent_orchestration/src/schemas/assessment.py) and persisted by `LearnerProfileRepository`.
14. **`Contract §14: LLMAdapter`**: Abstract base in [`modules/ai_agent_orchestration/src/adapters/llm_adapter.py`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/modules/ai_agent_orchestration/src/adapters/llm_adapter.py), implemented by `GeminiLLMAdapter` and `SmartMockLLMAdapter` in [`modules/ai_agent_orchestration/src/adapters/gemini_adapter.py`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/modules/ai_agent_orchestration/src/adapters/gemini_adapter.py).

---

## 2. End-to-End Data Flow

The end-to-end data flow is completely wired across backend and intelligence modules:

```
[Student / Client]
       │
       ├─ HTTP POST /api/v1/documents/upload ──> [RAGService.ingest_document] ──> ChromaDB
       │                                                                               │
       ├─ HTTP POST /api/v1/topic or /api/v1/plan ──> [PlannerAgent] ─────────────── RAG Chunks
       │                                                      │
       │                                                      ▼
       │                                              [LessonPlan]
       │                                                      │
       └─ WebSocket /ws/teach?token=... ──────────────────────┼────────────────────────┐
                                                              ▼                        │
                                                    [TeacherOrchestrator]              │
                                                              │                        │
                                      ┌───────────────────────┴───────────────────┐    │
                                      ▼                                           ▼    ▼
                              [TEACH / Explainer]                        [INTERACT / Questioner]
                                      │                                           │
                                      ▼                                           ▼
                             [TeachingSegment]                           [InteractionEvent]
                                      │                                           │
                                      ▼                                           │
                            [AvatarVoiceService]                                  │
                                      │                                           │
                                      ▼                                           │
                          [RenderedVideoSegment]                                  │
                                      │                                           │
                                      └───────────────────┬───────────────────────┘
                                                          ▼
                                            WebSocket sends payload to Client
                                                          │
                                                    Student Answers
                                                          │
                                                          ▼
                                            WebSocket receives StudentResponse
                                                          │
                                                          ▼
                                                [EVALUATE / MLCore]
                                    expected_concept=node.concept passed directly
                                                          │
                                                          ▼
                                                 [EvaluationResult]
                                                          │
                                                          ▼
                                                 [ADAPT / Controller]
                                                          │
                                                          ▼
                                                 [AdaptationDecision]
                                       (ALLOW / MODIFY / REGENERATE / ESCALATE)
                                                          │
                                                          ▼
                                        Session Checkpoint Persisted to Storage
```

---

## 3. Per-Module Status (Detailed)

### 3.1 `modules/rag`
- **Purpose**: Ingestion, structure detection (Devanagari & Bengali scripts), Indic subword token budgeting, hybrid BGE-M3 vector search, calibrated two-threshold cross-encoder reranking ($0.5001$ baseline vs $0.52$ citation), and citation grounding.
- **Status**: **100% Complete**.
- **Tests**: 18/18 passing in module suite; verified multi-domain grounding in root eval tests.

### 3.2 `modules/avatar_voice`
- **Purpose**: Voice synthesis (Edge-TTS with SSML prosody + fallback acoustic synthesizer), 24 FPS viseme avatar engine, Tier-2 MuseTalk neural avatar adapter with transparent fallback, 6 visual renderers, progressive derivation timing with duration conservation, and dual-path FFmpeg compositor.
- **Status**: **100% Complete**.
- **Tests**: 24/24 passing in module suite; 100+ passing tests across root test harness.

### 3.3 `modules/ml_core`
- **Purpose**: Student answer evaluation (`evaluate_answer`), misconception classification (`detect_misconception`), semantic distance calculation, partial credit assignment, and visual type heuristics.
- **Status**: **100% Complete**.
- **Public Interface**:
  ```python
  class MLCoreService:
      def __init__(self, llm_adapter: Optional[LLMAdapter] = None)
      def evaluate_answer(self, response: StudentResponse, expected_concept: str = "", grounding_text: Optional[str] = None, subject: str = "physics") -> EvaluationResult
      def detect_misconception(self, response: StudentResponse, concept: str, subject: str = "physics") -> Optional[str]
  ```

### 3.4 `modules/ai_agent_orchestration`
- **Purpose**: Pedagogical state machine coordinating `PlannerAgent`, `ExplainerAgent`, `QuestionerAgent`, `AdaptationController`, and `AssessmentAgent`.
- **Status**: **100% Complete**.
- **Public Interface**:
  ```python
  class TeacherOrchestrator:
      def __init__(self, planner, explainer, questioner, controller, assessor, rag_client, ml_core_client, avatar_client)
      def start_lesson(self, session_id: str, lesson_plan: LessonPlan) -> TeacherSession
      def step(self, session: TeacherSession, inputs: Optional[Dict[str, Any]] = None) -> TeacherStepResult
  ```
- **Tests**: **34/34 passing** (`modules/ai_agent_orchestration/tests/`).

### 3.5 `modules/backend`
- **Purpose**: FastAPI REST and WebSocket application, session management, token auth, document upload with RAG integration, learner profile CRUD, and session persistence.
- **Status**: **100% Complete**.
- **Public Interface**:
  - `POST /api/v1/session`
  - `POST /api/v1/topic`
  - `POST /api/v1/plan`
  - `POST /api/v1/documents/upload`
  - `GET /api/v1/learners/{learner_id}`
  - `GET /api/v1/learners/{learner_id}/assessments/{lesson_id}`
  - `WS /ws/teach?token=...`
- **Tests**: **31/31 passing** (`modules/backend/tests/`).

### 3.6 `modules/frontend`
- **Purpose**: Student learning room, video/canvas stage, interactive question modals, and pedagogical event audit logs.
- **Status**: **Blueprint Complete (`src/frontend/docs/frontend_design.md`)**; UI components in progress.

---

## 4. The Orchestration & LLM Layer Reality

1. **State Machine**: Governed by `TeacherOrchestrator` in `modules/ai_agent_orchestration/src/state_machine/orchestrator.py` executing deterministic transitions:
   `IDLE -> PLAN -> TEACH -> INTERACT -> EVALUATE -> ADAPT -> ASSESS -> COMPLETED`.
2. **Concept Grounding Verification**: During `TeacherState.EVALUATE`, the orchestrator extracts `concept = node.concept` from the active lesson node and explicitly passes it into `ml_core.evaluate_answer(student_response, expected_concept=concept)`.
3. **LLM Adapter Architecture**:
   - `GeminiLLMAdapter`: Uses `httpx` to communicate with Google Gemini 2.0 Flash REST API via `os.environ.get("GEMINI_API_KEY")`.
   - `SmartMockLLMAdapter`: Deterministic offline/CI fallback generating schema-compliant `LessonPlan`, `TeachingSegment`, `InteractionEvent`, and `AssessmentReport` payloads without crashes.
   - `get_llm_adapter()`: Clean factory injected into the backend container.
   - **Zero File Access Constraint**: `.env` is never opened or inspected by code or tests.

---

## 5. Verification & Test Suite Summary

Total system test execution across all modules:
```bash
pytest modules/rag/tests/ modules/ml_core/tests/ modules/avatar_voice/tests/ modules/ai_agent_orchestration/tests/ modules/backend/tests/ -v
```
**Result**: **127 passed, 0 failed in 27.77s**.

---

## 6. Mandatory Requirements Checklist (PS §17)

| # | Hackathon Mandatory Requirement | Implementation Status | Responsible Code / Verification |
|---|---|:---:|---|
| **1** | **Learning from uploaded material** | **DONE** | `modules/rag/src/service.py` (`ingest_document`) + `modules/backend/src/api/upload.py`. Ingests PDF/DOCX/PPTX/TXT, indexes to ChromaDB, retrieves chunks for grounded lesson generation. |
| **2** | **Topic-based teaching** | **DONE** | `modules/backend/src/api/rest.py` (`/api/v1/topic`) + `PlannerAgent.plan_from_topic()`. Generates full lesson plans from open-domain prompts. |
| **3** | **AI-generated lesson structure** | **DONE** | `modules/ai_agent_orchestration/src/agents/planner.py`. Generates multi-node `LessonPlan` with depths, time estimates, visual types, and checkpoints. |
| **4** | **Personalized teaching** | **DONE** | `LearnerConstraints` (beginner, intermediate, advanced; language; budget) is factored into lesson planning and retained in `LearnerProfile`. |
| **5** | **Human-like teaching interaction** | **DONE (Backend)** | `TeacherOrchestrator` executes two-way question/answer dialogue turns over WebSocket `/ws/teach`. |
| **6** | **Video-based AI Teacher presentation** | **DONE** | `modules/avatar_voice/src/compositor/ffmpeg_compositor.py` composites 1920x1080 canvas (70% visual, 30% avatar, bottom synced WebVTT captions). |
| **7** | **AI voice** | **DONE** | `modules/avatar_voice/src/tts/edge_tts_adapter.py` multilingual Edge-TTS with W3C SSML prosody + `FallbackTTSAdapter` acoustic waveform generator. |
| **8** | **Human-like AI avatar** | **DONE** | `modules/avatar_voice/src/avatar/viseme_avatar.py` 24 FPS 4-viseme 2D avatar engine + `MuseTalkAvatarAdapter` Tier 2 neural integration. |
| **9** | **Multilingual capability** | **DONE** | Devanagari & Bengali script extraction, Indic token budgeting, multilingual TTS voices (Hindi, Bengali, English). |
| **10** | **Student questioning & assessment** | **DONE** | `QuestionerAgent` generates checkpoint questions; `MLCoreService` evaluates answers; `AssessmentAgent` creates final `AssessmentReport`. |
| **11** | **Adaptive response to student performance** | **DONE** | `AdaptationController` triggers `ALLOW` on correct answers, `MODIFY` (remedial/partial credit), `REGENERATE` on repeated failures, and `HUMAN` on 3 consecutive errors. |
| **12** | **Working application/prototype** | **PARTIAL** | Backend, Orchestration, ML Core, RAG, and Video Synthesis are 100% complete with 127 passing tests. Frontend UI is next. |
