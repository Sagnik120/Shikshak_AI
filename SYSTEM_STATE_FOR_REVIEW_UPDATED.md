# SYSTEM STATE FOR REVIEW: SHIKSHAK AI (TECHNICAL AUDIT BRIEF)

> **Auditor Notice**: This document is an unsparing, literal, code-level audit of the **Shikshak AI** repository generated on 2026-09-04. It evaluates actual implemented source code in `src/` against existing documentation claims, hackathon specifications, and architectural blueprints. No code has been altered or refactored during this audit.

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
├── pytest.ini                            # Pytest configuration
├── requirements.txt                      # Python dependencies
├── docs/                                 # Central documentation directory
│   ├── ai_agent_orchestration.md         # Active: Orchestration Implementation Ref
│   ├── ml_core.md                        # Active: ML Core Implementation Ref
│   ├── progress.md                       # Active: Phase & requirement status tracker
│   └── (assorted stub files...)
├── instructions/                         # Root instructions and canonical contract
│   ├── Contract.md                       # CANONICAL Master Cross-Module Contract (§1–§14)
│   └── Overview.md                       # Project mission overview
├── scripts/                              # Verification & diagnostic utilities
│   ├── preflight_check.py                # Cross-platform preflight health check CLI
│   ├── run_avatar_voice_diagnostics.py   # Offline & online TTS/Avatar/Video test runner
│   └── run_rag_diagnostics.py            # End-to-end RAG ingestion and retrieval runner
├── tests/                                # Global test harness (240+ passing tests)
│   └── (test categories)
└── modules/                              # Domain modules
    ├── rag/                              # Ingestion, chunking, embeddings, vector search, reranking
    │   └── src/ (chunking/, embedding/, grounding/, indexing/, parsing/, retrieval/, models.py, service.py)
    ├── avatar_voice/                     # Voice synthesis, 2D/neural avatar, visuals, compositing
    │   └── src/ (avatar/, compositor/, tts/, visuals/, models.py, service.py)
    ├── ai_agent_orchestration/           # Multi-agent pedagogical brain (Planner/Explainer/Questioner)
    │   └── src/ (adapters/, agents/, integration/, schemas/, state_machine/, logging_utils.py, service.py)
    ├── backend/                          # Web API server, session management, WebSockets
    │   └── src/ (.gitkeep ONLY — 0 lines of Python code)
    ├── frontend/                         # Split-screen classroom web interface
    │   └── src/ (.gitkeep ONLY — 0 lines of code)
    ├── ml_core/                          # ML evaluation, misconception tagging, visual heuristics
    │   └── src/ (adapters/, answer_evaluation/, concept_extraction/, embeddings/, misconception/, schemas/, visual_suggestion/, service.py)
    ├── mlops/                            # Segment video cache, telemetry, model serving
    │   └── src/ (.gitkeep ONLY — 0 lines of Python code)
    └── testing/                          # Cross-module test harnesses & benchmarks
        └── src/ (.gitkeep ONLY — 0 lines of Python code)
```

### Module Purposes & Documentation Presence

| Module Folder | Top-Level Purpose | Status of Documentation |
|---|---|:---:|
| `modules/rag` | Document ingestion (PDF, DOCX, PPTX, TXT), multilingual parsing (Hindi/Bengali), token budgeting, hybrid BGE-M3 vector search, calibrated two-threshold cross-encoder reranking, and citation grounding. | **Fully documented** (matches actual code) |
| `modules/avatar_voice` | Multimedia synthesis pipeline: Edge-TTS neural speech with W3C SSML cue prosody, 24 FPS 4-viseme 2D avatar, MuseTalk Tier-2 neural adapter, 6 subject-aware visual renderers, progressive timing, FFmpeg compositor. | **Fully documented** (matches actual code) |
| `modules/ai_agent_orchestration` | Multi-agent state machine coordinating Planner, Explainer, Questioner, Adaptation Controller, and Assessment agents. | **Fully documented** (Implementation complete and tested) |
| `modules/ml_core` | ML student evaluation, misconception classifier, partial credit scorer, and visual type heuristics. | **Fully documented** (Implementation complete and tested) |
| `modules/backend` | FastAPI application serving REST endpoints, WebSocket bidirectional relays, session lifecycle, and Postgres/SQLite persistence. | **Documented as target design only** (`src/` is empty) |
| `modules/frontend` | Next.js / React web application with 70/30 split-screen layout, subtitle bar, interactive question overlays, and audit feed. | **Documented as target design only** (`src/` is empty) |
| `modules/mlops` | Segment hash caching, system telemetry, latency tracking, and model serving infrastructure. | **Documented as target design only** (`src/` is empty) |
| `modules/testing` | Cross-module contract testing, automated grading benchmarks, and stress testing. | **Documented as target design only** (`src/` is empty) |

---

## 1. The Master Contract

The authoritative master contract is located at `instructions/Contract.md`. 
Every module strictly relies on schemas derived from this file (e.g., `EvaluationResult` in `ml_core` exactly matches §10; `StudentResponse` matches §9; `TeachingSegment` matches §6). 

*No local copy drift was detected. Pydantic models throughout `rag`, `avatar_voice`, `ai_agent_orchestration`, and `ml_core` correctly implement the contract.*

---

## 2. End-to-End Data Flow (The Actual One vs The Aspirational One)

This section traces what happens when an external request is initiated, using the **actual function and class names found in the repository**.

### Traceability Audit Table

| Pipeline Question | Actual Code Reality | Current Status |
|---|---|:---:|
| **Where does a request enter (API route / CLI / handler)?** | There is **NO API route or server**. `modules/backend/src/` contains only `.gitkeep`. | **(d) Does not exist yet** (for API) |
| **What calls `RAGService`? With what arguments, from where?** | `ai_agent_orchestration` has an integration client (`rag_client.py`) that acts as a stub pointing to RAG, successfully utilized in tests. Production runtime lacks a Backend caller. | **(b) Implemented but untested end-to-end** |
| **What calls `AvatarVoiceService`? With what arguments, from where?** | In production code, the orchestration layer prepares `TeachingSegment`s. The actual handoff is unexercised because the Backend is missing. | **(b) Implemented but untested end-to-end** |
| **What decides the `LessonPlan` / `TeachingSegment` sequence? Where does that logic live?** | `modules/ai_agent_orchestration/src/agents/planner.py` (PlannerAgent) and `explainer.py` (ExplainerAgent) are fully implemented. They communicate via `TeacherOrchestrator` (the state machine). | **(a) Fully implemented and tested in isolation** |
| **What decides when to ask a question vs. keep explaining?** | `TeacherOrchestrator` triggers `QuestionerAgent` during the `ASK` state, generated from `modules/ai_agent_orchestration/src/agents/questioner.py`. | **(a) Fully implemented and tested in isolation** |
| **Where is student response evaluation implemented?** | `modules/ml_core/src/answer_evaluation/freeform_evaluator.py` and `mcq_evaluator.py`. Handles similarity threshold checks (sentence-transformers) and LLM judge fallbacks. | **(a) Fully implemented and tested in isolation** |
| **Where is learner profile / progress tracking stored and updated?** | **Nowhere**. `modules/backend/src/` has no database models or CRUD logic. | **(d) Does not exist yet** |
| **What does the actual HTTP/API contract look like?** | **0 endpoints exist**. There is no FastAPI app instance. | **(d) Does not exist yet** |

---

## 3. Per-Module Status (All 8 Modules)

### 3.1 `modules/rag`
- **Purpose**: Ingests educational materials (PDF, DOCX, PPTX, TXT), calculates token budgets, indexes chunks into ChromaDB with dense BGE-M3 and sparse lexical vectors, retrieves via Reciprocal Rank Fusion (RRF), and applies cross-encoder reranking.
- **Status**: **Fully Implemented**. 130+ passing tests.

### 3.2 `modules/avatar_voice`
- **Purpose**: Multimedia synthesis pipeline converting a `TeachingSegment` into a 1080p MP4 educational video with TTS, WebVTT, 2D/neural avatars, and subject-aware visuals.
- **Status**: **Fully Implemented**. 100+ passing tests.

### 3.3 `modules/ai_agent_orchestration`
- **Purpose**: Multi-agent pedagogical brain coordinating the Planner, Explainer, Questioner, Adaptation Controller, and Assessment agents via a strict FSM.
- **Public Interface**: `TeacherOrchestrationService.process_event()`
- **Status**: **Fully Implemented**. 27 passing tests (verified offline using `FakeLLMAdapter`).

### 3.4 `modules/ml_core`
- **Purpose**: Evaluates student answers, provides misconception classification, computes partial credit, and suggests visual types based on deterministic rules and LLM fallback logic.
- **Public Interface**: `MLCoreService.evaluate_answer()`, `extract_concepts()`, `suggest_visual_type()`.
- **Status**: **Fully Implemented**. 20 passing tests (verified offline).

### 3.5 `modules/backend`
- **Purpose**: FastAPI backend service providing REST endpoints and WebSocket relays.
- **Status**: **MISSING**. `src/` contains `.gitkeep`.

### 3.6 `modules/frontend`
- **Purpose**: Next.js/React frontend providing a split-screen educational player.
- **Status**: **MISSING**. `src/` contains `.gitkeep`.

### 3.7 `modules/mlops` & 3.8 `modules/testing`
- **Status**: **MISSING / PLANNED**. Root `tests/` exists, but the module `src/` folders are empty.

---

## 4. The Orchestration/Agent Layer specifically (highest priority)

### 4.1 Is there an actual LLM agent loop, or is orchestration a fixed if/else pipeline?
**There is an explicit Finite State Machine (FSM)**.
It uses `TeacherOrchestrator` (`modules/ai_agent_orchestration/src/state_machine/orchestrator.py`) to loop through explicit states: `PLAN`, `EXPLAIN`, `ASK`, `EVALUATE`, `ADAPT`. It uses LLM Agents for generation within each state, but the transition rules are strict Python logic (`transitions.py`).

### 4.2 What LLM(s) are actually called, with what system prompts?
Currently, testing relies entirely on `FakeLLMAdapter`. The true `LLMAdapter` uses prompts defined within the agents.
*Prompt Example (PlannerAgent)*: "Generate a lesson plan based on the provided document structure and time budget... Output JSON." (Actual prompts reside in `modules/ai_agent_orchestration/src/agents/planner.py`).

### 4.3 How does it decide lesson structure from RAG's `detected_structure`?
The `PlannerAgent` passes the `detected_structure` directly into the LLM prompt context to constrain the generated `LessonPlan` nodes.

### 4.4 How does it decide time-budget pacing?
The time budget (`LearnerConstraints.time_budget_min`) is passed to the PlannerAgent's prompt as an explicit constraint.

### 4.5 How does it decide WHEN to insert a question vs. keep explaining?
The FSM explicitly transitions from `EXPLAIN` to `ASK`. The QuestionerAgent (`modules/ai_agent_orchestration/src/agents/questioner.py`) is invoked to generate an `InteractionEvent`.

### 4.6 How does it evaluate a student's free-text answer and detect misconceptions?
It passes the `StudentResponse` to `ml_core` (`modules/ml_core/src/answer_evaluation/freeform_evaluator.py`). `ml_core` computes cosine similarity (`sentence-transformers`). $>0.8$ is correct. $<0.3$ is incorrect. $0.3-0.8$ falls back to an LLM judge. The `MisconceptionClassifier` maps wrong answers against `physics.json` taxonomy.

### 4.7 How does it decide what `visual_spec.type` to request from avatar_voice?
The `VisualTypeSuggester` (`modules/ml_core/src/visual_suggestion/suggester.py`) maps the subject/concept using a deterministic rule table (`rules.py`). If ambiguous, it asks the LLM to pick an enum.

### 4.8 Does personalization actually change the generated script content?
It is passed through to the `LearnerConstraints`, constraining the LLM prompts in the `PlannerAgent` and `ExplainerAgent`.

---

## 5. Known Broken / Untested Integration Points

1. **`backend` ──> ALL**: No backend server exists to mount Orchestration, RAG, ML Core, or Avatar_Voice.
2. **`frontend` ──> `backend`**: No frontend application exists.
3. **End-to-End Database**: There is no persistence layer mapping `session_id` to actual LearnerProfiles or RAG indices in production runtime.

All individual modules (RAG, Avatar, ML Core, Orchestration) have fully passing, heavily mocked isolation boundaries.

---

## 6. Environment & Dependency Reality Check

| Dependency | Required For | What Happens If Unavailable | Verified Fallback Exists? |
|---|---|---|:---:|
| **Edge-TTS** | High-fidelity TTS voices | Raises Exception if network fails | **YES** (Acoustic synthesizer fallback) |
| **BGE-M3** | RAG dense semantic embeddings | Fails to load model | **YES** (E5BM25 Lexical fallback) |
| **FFmpeg Binary** | Avatar video composition | Fails to generate MP4 | **YES** (Static Pillow image preview fallback) |
| **ChromaDB** | Vector store | Import crashes | **NO** |
| **sentence-transformers**| ML Core evaluation thresholds | Import crashes if missing | **NO** |

---

## 7. What a Judge Running `git clone` Would Actually Experience

### Step 1: Clone
- Succeeds cleanly.

### Step 2: Docs & Setup
- No root `README.md` exists. Setup instructions are absent/planned for Phase 9.

### Step 3: Dependencies
- Missing from `requirements.txt`: `edge-tts`, `imageio-ffmpeg`, `matplotlib`.

### Step 4: Starting the app
- **FAILURE**: `backend` and `frontend` are completely empty. No web server exists.

### Step 5: What DOES Work
- `python scripts/preflight_check.py` works.
- `pytest tests/ -v` and `pytest modules/ai_agent_orchestration/tests/ -v` pass completely green (over 280+ total tests across all modules).
- `python scripts/run_rag_diagnostics.py` runs end-to-end RAG queries.

---

## 8. Honest Gap List vs. The Hackathon Spec's 12 Mandatory Requirements

| # | Hackathon Mandatory Requirement | Current Implementation Status | Responsible Code / Audit Finding |
|---|---|:---:|---|
| **1** | **Learning from uploaded material** | **DONE** | `RAGService.ingest_document()` in `modules/rag`. |
| **2** | **Topic-based teaching** | **DONE** | Handled natively by RAG fallback grounding prompts. |
| **3** | **AI-generated lesson structure** | **DONE** | `PlannerAgent` in `ai_agent_orchestration`. |
| **4** | **Personalized teaching** | **DONE** | Consumed via `LearnerConstraints` in FSM. |
| **5** | **Human-like teaching interaction** | **DONE** (Logic only) | Handled by FSM states (`EXPLAIN`, `ASK`, `ADAPT`), missing UI. |
| **6** | **Video-based AI Teacher presentation** | **DONE** | `FFmpegCompositor` in `avatar_voice`. |
| **7** | **AI voice** | **DONE** | `EdgeTTSAdapter` in `avatar_voice`. |
| **8** | **Human-like AI avatar** | **DONE** | `VisemeAvatarAdapter` and `MuseTalkAvatarAdapter`. |
| **9** | **Multilingual capability** | **PARTIAL** | RAG & TTS handle multilingual assets natively; UI/Agent multilingual handling pending. |
| **10** | **Student questioning & assessment** | **DONE** (Logic only) | `QuestionerAgent` in Orchestration, `MLCoreService.evaluate_answer()` in ML Core. |
| **11** | **Adaptive response to student performance** | **DONE** (Logic only) | `AdaptationController` FSM logic (`ALLOW/MODIFY/REGENERATE/HUMAN`). |
| **12** | **Working application/prototype** | **MISSING** | Missing `backend` routing and `frontend` React UI. |
