# Backend Module — Comprehensive Architectural & Technical Detail

> **Module Identifier**: `backend`  
> **Repository Path**: `modules/backend/`  
> **Primary Role**: Central API Gateway, WebSocket Session Relay & Persistent State Manager  
> **Status**: **IMPLEMENTED & VERIFIED** (Production API server on Port 8000; isolated diagnostic testbed active on Port 8005)  
> **Key Contracts**: Contract §1 (`UploadRequest`), Contract §2 (`TopicRequest`), Contract §3 (`LearnerConstraints`), Contract §5 (`LessonPlan`), Contract §6 (`TeachingSegment`), Contract §7 (`RenderedVideoSegment`), Contract §8 (`InteractionEvent`), Contract §9 (`StudentResponse`), Contract §10 (`EvaluationResult`), Contract §11 (`AdaptationDecision`), Contract §12 (`AssessmentReport`), Contract §13 (`LearnerProfile`)

---

## 1. The Task (In Simple Language)

Imagine a school's central administrative office and classroom intercom system. When a student enters the school:
1. **Registers the student**: Takes their books or syllabus (upload), notes down how much time they have (e.g. 20 minutes) and their preferred language (e.g. Hindi), and opens a new session.
2. **Connects the student to the teacher**: Calls the curriculum planner, hands the book to the research team (RAG), and brings the lesson plan to the classroom.
3. **Maintains the live intercom**: During the lesson, as the teacher speaks and asks questions, the intercom relays video and audio directly to the student's desk. When the student speaks or clicks an answer, the intercom relays the answer to the grading evaluator.
4. **Keeps student permanent records**: Saves past quizzes, concepts mastered, and weak spots in a permanent file folder (Learner Profile) so future classes start from where the student left off.

The **`backend`** module is this exact central coordination engine for Shikshak AI. It does not decide *how* to teach (that is `ai_agent_orchestration`), nor does it render videos (that is `avatar_voice`). Instead, it connects the frontend web application to all AI and ML microservices over high-speed REST endpoints and a real-time WebSocket connection.

---

## 2. Technical Details & Architecture

The backend is designed as an asynchronous, high-throughput service built on **FastAPI**:

- **Dual-Protocol Gateway**:
  - **REST API (`src/api/rest.py`)**: Handles session creation, topic constraints, file uploads with RAG ingestion, curriculum plan generation, and learner profile retrieval.
  - **WebSocket Relay (`src/api/ws.py` at `/sessions/{id}/live`)**: Provides a bidirectional, full-duplex communication channel between the client browser and the AI Teacher state machine.
- **Server-Authoritative State Management (`src/state/driver.py`)**:
  Tracks session lifecycle transitions:
  `CREATED -> INGESTING -> PLANNED -> EXPLAINING -> AWAITING_ANSWER -> EVALUATING -> ADAPTING -> ASSESSING -> COMPLETE`.
  Every state transition is persisted in `SessionRepository` alongside the active `session_id`, `lesson_id`, and `node_id`. If a student refreshes their browser or loses connection, the WebSocket reconnects and resumes mid-lesson seamlessly.
- **Microservice Container Gateway (`src/integrations/container.py`)**:
  The backend never directly invokes external LLMs, vector databases, or TTS APIs. It interacts exclusively with other modules via contract facades (`RAGService`, `AvatarVoiceService`, `TeacherOrchestrator`, `MLCoreService`).
- **Data Persistence Architecture (`src/persistence/in_memory.py`)**:
  - `SessionRepository`: Tracks session tokens, active topics, learner constraints, document contexts, and state checkpoints.
  - `DocumentRepository`: Tracks uploaded document metadata, filenames, MIME types, file sizes, and parsing status (`ready`/`failed`).
  - `LearnerRepository`: Stores learner mastery profiles, strengths, weaknesses, and learning paths.
  - `ReportRepository`: Stores final quiz assessment reports.
  - `StorageAdapter`: Filesystem-backed binary object storage adapter (`storage.py`).

---

## 3. What is Implemented Till Now (Current Status)

| Subsystem | Specification & Status | Status |
|---|---|---|
| **Contract Schemas** | Authoritative schemas defined in `instructions/Contract.md` for all REST payloads and WebSocket frames. | **Contract-Locked & Verified** |
| **REST Router** | `src/api/rest.py` exposing `/sessions`, `/topic`, `/upload`, `/plan`, `/learners`. | **Fully Implemented & Verified** |
| **WebSocket Relay** | `src/api/ws.py` managing live full-duplex event loop (`curriculum_loaded`, `ai_state`, `explanation_chunk`, `question_prompt`, `evaluation_result`). | **Fully Implemented & Verified** |
| **Persistence Repositories** | `src/persistence/in_memory.py` providing in-memory session, document, learner, and report storage. | **Fully Implemented & Verified** |
| **State Machine Driver** | `src/state/driver.py` bridging `SessionRepository` and `TeacherOrchestrator`. | **Fully Implemented & Verified** |
| **Service Decoupling** | `src/integrations/container.py` encapsulating all microservice gateways. | **Fully Implemented & Verified** |
| **Web Testbed Studio** | Standalone FastAPI diagnostic service on **Port 8005** with pure light professional UI and hierarchical logging. | **Fully Implemented & Verified** |
| **Test Suite** | Comprehensive pytest suite across unit, integration, and web testbed server (8 passing tests). | **100% Passing (8/8 in testbed suite)** |

---

## 4. Full File Structure

```
modules/backend/
├── docs/
│   └── backend_detail.md                       # This authoritative documentation file
├── instructions/
│   ├── contract.md                             # Authoritative cross-module contract definitions
│   ├── detail_plan.md                          # Endpoint specifications and session state machine rules
│   ├── overview.md                             # High-level module summary
│   ├── task_backend_src.md                     # Source engineering task specifications
│   └── task_backend_testing.md                 # Testing strategy and integration scenarios
├── src/
│   ├── api/
│   │   ├── rest.py                             # REST route handlers (/sessions, /upload, /topic, /plan)
│   │   └── ws.py                               # WebSocket relay handler (/sessions/{id}/live)
│   ├── auth.py                                 # Session token generation and validation
│   ├── config.py                               # Settings and CORS configuration
│   ├── integrations/
│   │   └── container.py                        # Service container bridging all microservices
│   ├── main.py                                 # Production FastAPI application entrypoint (Port 8000)
│   ├── persistence/
│   │   ├── base.py                             # Abstract repository base classes
│   │   ├── in_memory.py                        # Concrete in-memory repositories
│   │   └── storage.py                          # Filesystem binary storage adapter
│   ├── schemas/
│   │   ├── contract.py                         # Contract-conforming Pydantic models
│   │   └── ws.py                               # WSMessage framing schema
│   └── state/
│       └── driver.py                           # SessionDriver orchestrating TeacherState
└── tests/
    ├── e2e/                                    # End-to-end user journey tests
    ├── e2e_mocked/                             # Mocked journey tests
    ├── integration/                            # Microservice boundary tests
    ├── unit/                                   # Pytest unit tests (sessions, auth, persistence)
    │   └── test_backend_web_test_server.py     # Automated unit tests for Port 8005 testbed
    └── web_test/                               # Standalone Web Diagnostic Testbed (Port 8005)
        ├── logger.py                           # Hierarchical trace and hallucination logger
        ├── server.py                           # FastAPI testbed application
        ├── logs/                               # Categorized test trace output directory
        │   ├── avatar_relay/                   # Avatar voice and video request traces
        │   ├── errors/                         # Validation, crash, and hallucination traces
        │   ├── orchestration/                  # State transition and lesson plan traces
        │   ├── rag_relay/                      # Document upload and structure extraction traces
        │   ├── sessions/                       # Session creation and auth token traces
        │   ├── telemetry/                      # Health probes and performance metrics
        │   └── websocket/                      # Live WebSocket frame exchange traces
        └── static/                             # Pure light professional frontend
            ├── css/
            │   └── style.css                   # Crisp light theme styling (NO dark mode)
            ├── js/
            │   └── app.js                      # Diagnostic studio interactive logic
            └── index.html                      # 5-tab diagnostic workbench
```

---

## 5. Detailed File Logic (Authoritative Codebase Implementation)

### `src/main.py`
- Production application entrypoint listening on Port 8000.
- Mounts `rest_router` and `ws_router` under both `/api/v1` and root for client compatibility.
- Exposes `GET /health` returning `{"status": "ok"}`.
- Mounts student frontend static assets from `modules/frontend/src/`.

### `src/api/rest.py`
- Implements core HTTP routes:
  - `POST /sessions`: Issues a new hex session ID and cryptographically random token.
  - `POST /sessions/{id}/topic`: Saves topic title and `LearnerConstraints` (level, language, time budget).
  - `POST /sessions/{id}/upload`: Accepts multipart document bytes, stores in `storage_adapter`, and delegates to `RAGService.ingest_document()`.
  - `POST /sessions/{id}/plan`: Dispatches `UNDERSTAND` and `PLAN` steps through `SessionDriver` to generate `LessonPlan`.
  - `GET /learners/{id}/profile`: Queries learner mastery records.
  - `GET /learners/{id}/report/{lesson_id}`: Retrieves stored `AssessmentReport`.

### `src/api/ws.py`
- Implements WebSocket endpoint at `/sessions/{id}/live`:
  - Enforces bearer token verification via `verify_ws_token`.
  - Handles reconnection logic: checks `SessionRepository` for stored state and resumes mid-lesson.
  - Loops across the 8 teaching stages: broadcasts `curriculum_loaded`, `ai_state`, `explanation_chunk`, `question_prompt`, `evaluation_result`, and `adaptation_decision`.
  - Dispatches visual specifications and avatar cues to `avatar_service`.

### `src/persistence/in_memory.py`
- Thread-safe repository implementations:
  - `session_repo`: Map of session IDs to metadata, tokens, topics, constraints, document IDs, and current state checkpoints.
  - `document_repo`: Map of document IDs to filenames, MIME types, file paths, and parsing status.
  - `learner_repo`: Map of learner IDs to `LearnerProfile` objects.
  - `report_repo`: Map of session IDs to `AssessmentReport` objects.
  - `storage_adapter`: Disk-backed `put` and `get` operations writing to a local `storage/` directory.

### `src/state/driver.py`
- `SessionDriver(session_id)`:
  - Binds the session to `services["teacher_orchestrator"]`.
  - Translates high-level step requests into `TeacherOrchestrator.process_next_step()`.

---

## 6. How the Module Works (Execution Flow & Runtime Lifecycle)

```
[Student Frontend]                                    [Backend Gateway]                            [Internal Services]
         |                                                    |                                             |
         | --- 1. POST /sessions ---------------------------> |                                             |
         | <--- Returns session_id + token ------------------ |                                             |
         |                                                    |                                             |
         | --- 2. POST /sessions/{id}/upload (File) --------> | --- Passes file bytes --------------------> [RAG Module]
         |                                                    | <--- Returns ParsedDocument (Contract §4) - |
         | <--- Returns document_id + structure ------------- |                                             |
         |                                                    |                                             |
         | --- 3. Connect WS /sessions/{id}/live -----------> | [SessionManager accepts connection]         |
         |                                                    |                                             |
         | --- 4. POST /sessions/{id}/plan -----------------> | --- Triggers SessionDriver.step() --------> [AI Orchestration]
         | <--- Returns LessonPlan (Contract §5) ------------ | <--- Returns LessonPlan ------------------- |
         |                                                    |                                             |
         |                                                    | === BEGIN INTERACTIVE TEACHING LOOP ===     |
         |                                                    |                                             |
         | <=== PUSH WS: curriculum_loaded ================== |                                             |
         | <=== PUSH WS: ai_state (TEACH) =================== |                                             |
         | <=== PUSH WS: explanation_chunk ================== |                                             |
         | <=== PUSH WS: question_prompt (Contract §8) ====== |                                             |
         |                                                    |                                             |
         | ===> SEND WS: StudentResponse (Contract §9) ====== | --- Evaluates Answer ---------------------> [ML Core]
         |                                                    | <--- Returns EvaluationResult (§10) ------- |
         |                                                    |                                             |
         | <=== PUSH WS: evaluation_result ================== |                                             |
         | <=== PUSH WS: adaptation_decision (ALLOW/MODIFY) = | (Relayed from Adaptation Controller)        |
         |                                                    |                                             |
         |                                                    | === LESSON COMPLETE ===                     |
         | <=== PUSH WS: assessment_report (Contract §12) === | --- Persists to LearnerProfile (§13) -----> [Database Store]
```

---

## 7. Cross-Module Connections & Contract Integration

| Direction | Connected Module | Contract Reference | Protocol / Data Shape |
|---|---|---|---|
| **Inbound** | `frontend` | **Contracts §1, §2, §3, §9** | Client sends REST requests and pushes WebSocket response frames. |
| **Outbound** | `frontend` | **Contracts §5, §6, §7, §8, §10, §11, §12** | Backend responds via REST and streams live WebSocket events. |
| **Outbound** | `rag` | **Contract §1, §4** | Streams raw uploaded file bytes to `RAGService.ingest_document()`. |
| **Outbound** | `ai_agent_orchestration` | **Contracts §5, §6, §8, §11, §12** | Invokes Planner, Explainer, Questioner, Adaptation Controller, and Assessment agents. |
| **Outbound** | `avatar_voice` | **Contracts §6, §7** | Calls `AvatarVoiceService.render_segment()` to synthesize video. |
| **Outbound** | `ml_core` | **Contracts §9, §10** | Relays student answers to `MLCoreService.evaluate_answer()`. |
| **Internal** | Persistence | **Contracts §12, §13** | Stores and queries `LearnerProfile` and `AssessmentReport` records. |

---

## 8. Full System Overview (Module-Wise Context)

In the complete 8-stage Shikshak AI teaching loop:
`Understand -> Plan -> Explain -> Demonstrate -> Question -> Evaluate -> Adapt -> Continue`

The **`backend`** module acts as the central physical highway and state ledger:
- It receives student inputs from **Frontend**.
- It triggers **Understand** in **RAG**.
- It triggers **Plan** in **AI Orchestration**.
- It routes generated segments to **avatar_voice** for **Explain & Demonstrate**.
- It routes checkpoint questions to **Frontend** for **Question**.
- It routes responses to **ml_core** and **AI Orchestration** for **Evaluate & Adapt**.
- It saves final assessment reports to persist student mastery over time.

---

## 9. Critical Notes for Any LLM Agent Working on This Module

> [!IMPORTANT]
> **Strict Guardrails for LLM Agents:**
> 1. **Do Not Embed AI Logic in Backend**: The backend is strictly an API gateway and session coordinator. Never put prompt engineering, LLM calls, or RAG embeddings inside backend routes. Always call the dedicated modules (`ai_agent_orchestration`, `rag`, `ml_core`, `avatar_voice`).
> 2. **WebSocket State Invariant**: The server must be the single source of truth for the lesson state. The frontend must never dictate which node to play next; the backend state machine drives node sequencing based on `AdaptationDecision`.
> 3. **Mid-Lesson Language Switching**: When a client sends a `"language_switch"` control event over WebSocket, do **not** wipe the session or restart the lesson. Update `LearnerConstraints.language` in the active session and continue from the current `node_id`.
> 4. **Graceful Disconnection Handling**: Always wrap WebSocket message loops in `try...except WebSocketDisconnect` blocks. Mark the session as `PAUSED` and preserve all pointers so the student can resume upon reconnecting.

---

## 10. Interactive Web Testbed & Hierarchical Traceability Engine (Port 8005)

To allow comprehensive user testing without modifying the production backend on Port 8000, `backend` features a dedicated standalone testbed:

### 10.1 Dedicated Server Configuration
- **Server File**: `modules/backend/tests/web_test/server.py`
- **Network Port**: **`8005`** (Completely isolated from production Port 8000, Orchestration Port 8001, RAG Port 8002, ML Core Port 8003, Avatar Port 8004)
- **Start Command**:
  ```bash
  ./.venv/bin/python modules/backend/tests/web_test/server.py
  ```
- **Web UI URL**: `http://localhost:8005/`

### 10.2 Hierarchical Logging Engine (`logger.py`)
Every operation executed via the testbed generates dual log files:
1. A structured JSON manifest (`.json`) containing parsed request payloads, responses, latency, calling `.py` file, and calling function.
2. A human-readable execution transcript (`.log`) formatted for quick visual inspection.

Logs are cleanly organized into 7 dedicated categories:
- `logs/sessions/`: Session creation, bearer token issuance, topic and constraint updates.
- `logs/websocket/`: Live WebSocket frame relays (`curriculum_loaded`, `ai_state`, `explanation_chunk`, `question_prompt`, `evaluation_result`).
- `logs/orchestration/`: `TeacherState` transitions, SessionDriver steps, and generated lesson plans.
- `logs/rag_relay/`: Multipart document ingestion and detected chapter/term structures.
- `logs/avatar_relay/`: TeachingSegment rendering requests and visual specifications.
- `logs/telemetry/`: Latency metrics, health probes, and active connection counts.
- `logs/errors/`: Exceptions, 401/422 validation errors, and hallucination warnings.

### 10.3 Hallucination Detection & Source Traceability
To ensure complete debugging transparency and catch any hallucinating prompt or function:
- Every log record explicitly captures `calling_file` (e.g., `modules/backend/src/api/rest.py`, `ws.py`, `driver.py`) and `calling_function` (e.g., `create_session`, `upload_document`, `websocket_endpoint`).
- If an operation returns out-of-spec schemas or invalid frames, the logger flags `is_hallucination_suspect: True` and records the trace in `logs/errors/`.

### 10.4 Pure Light Professional Frontend
- **Design Aesthetic**: Crisp white `#ffffff` cards on a soft slate `#f8fafc` surface with slate-200 borders and vibrant indigo/emerald accents.
- **Strict Prohibition**: Strictly no dark mode or dark background surfaces.
- **Features**:
  - 5 dedicated workspaces: **Session & Auth Manager**, **Document Ingestion & RAG Relay**, **Curriculum Planner & State Driver**, **Live WebSocket Stream Simulator**, and **Structured Log Explorer**.
  - One-click topic presets for Physics, Mathematics, Biology, and Computer Science.
  - Interactive WebSocket terminal showing real-time bidirectional frame deliveries with color-coded badges.
