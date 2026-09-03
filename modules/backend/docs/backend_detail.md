# Backend Module — Comprehensive Architectural & Technical Detail

> **Module Identifier**: `backend`  
> **Repository Path**: `modules/backend/`  
> **Primary Role**: Central API Gateway, WebSocket Session Relay & Persistent State Manager  
> **Status**: **SCAFFOLDED & CONTRACT-LOCKED** (Ready for FastAPI implementation)  
> **Key Contracts**: Contract §1 (`UploadRequest`), Contract §2 (`TopicRequest`), Contract §3 (`LearnerConstraints`), Contract §7 (`RenderedVideoSegment`), Contract §8 (`InteractionEvent`), Contract §9 (`StudentResponse`), Contract §11 (`AdaptationDecision`), Contract §12 (`AssessmentReport`), Contract §13 (`LearnerProfile`)

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
  - **REST API**: Handles session creation, file uploads, curriculum plan queries, and learner profile retrieval.
  - **WebSocket Relay (`/sessions/{id}/live`)**: Provides a bidirectional, full-duplex communication channel between the client browser and the AI Teacher state machine.
- **Server-Authoritative State Management**:
  Tracks session lifecycle transitions:
  `CREATED -> INGESTING -> PLANNED -> EXPLAINING -> AWAITING_ANSWER -> EVALUATING -> ADAPTING -> ASSESSING -> COMPLETE`.
  Every state transition is persisted alongside the active `session_id`, `lesson_id`, and `node_id`. If a student refreshes their browser or loses connection, the WebSocket reconnects and resumes mid-lesson seamlessly.
- **Microservice Decoupling**:
  The backend never directly invokes external LLMs, vector databases, or TTS APIs. It interacts exclusively with other modules via contract facades (`RAGService`, `AvatarVoiceService`, `TeacherOrchestrationService`, `MLCoreService`).
- **Data Persistence Architecture**:
  - Relational tables (`PostgreSQL` / `SQLite` for local development):
    - `sessions`: Session ID, status, timestamps, active node pointers.
    - `learner_profiles`: Learner ID, historical reports, concept mastery lists.
    - `assessment_reports`: Final quiz outcomes and recommendations.
    - `uploaded_documents`: Document metadata, MIME types, file sizes, storage paths.
    - `rendered_segments`: Video file metadata, durations, WebVTT caption paths.
  - Blob / File Storage: Local filesystem directory (`storage/`) for hackathon prototype, swappable to AWS S3 / MinIO via storage adapters.

---

## 3. What is Implemented Till Now (Current Status)

| Subsystem | Specification & Status | Status |
|---|---|---|
| **Contract Schemas** | Authoritative schemas defined in `instructions/Contract.md` for all REST payloads and WebSocket frames. | **Contract-Locked & Verified** |
| **Module Specifications** | `instructions/overview.md`, `instructions/detail_plan.md`, `instructions/contract.md` defining all REST routes and WebSocket event formats. | **Complete** |
| **Directory Skeleton** | `src/` and `tests/` (`unit/`, `integration/`, `e2e/`) partitioned and prepared. | **Scaffolded** |
| **FastAPI App & Routers** | Router files (`sessions.py`, `upload.py`, `profile.py`, `ws_live.py`) scheduled for implementation. | **Next Immediate Sprint** |
| **Database Models** | SQLAlchemy / SQLModel table definitions matching Contract §12 and §13. | **Next Immediate Sprint** |

---

## 4. Full File Structure

```
modules/backend/
├── docs/
│   └── backend_detail.md                       # This authoritative documentation file
├── instructions/
│   ├── contract.md                             # Authoritative cross-module contract definitions
│   ├── detail_plan.md                          # Endpoint specifications and session state machine rules
│   └── overview.md                             # High-level module summary
├── src/
│   ├── .gitkeep                                # Active source directory
│   ├── __init__.py                             # (Target architecture) Package exports
│   ├── api/                                    # (Target architecture)
│   │   ├── deps.py                             # Dependency injection (DB sessions, service instances)
│   │   ├── routers/                            # REST & WebSocket route handlers
│   │   │   ├── learners.py                     # GET /learners/{id}/profile, GET reports
│   │   │   ├── sessions.py                     # POST /sessions, /sessions/{id}/plan
│   │   │   ├── upload.py                       # POST /sessions/{id}/upload, /topic
│   │   │   └── ws_live.py                      # WS /sessions/{id}/live bidirectional relay
│   ├── core/                                   # (Target architecture)
│   │   ├── config.py                           # App settings, environment variables, CORS policies
│   │   └── state_machine.py                    # Server-authoritative session state coordinator
│   ├── db/                                     # (Target architecture)
│   │   ├── database.py                         # Async database engine & session maker
│   │   └── models.py                           # SQLAlchemy models for sessions, profiles, and reports
│   ├── main.py                                 # (Target architecture) FastAPI app entry point
│   └── services/                               # (Target architecture)
│       └── session_manager.py                  # In-memory connection pool & active WS manager
└── tests/
    ├── e2e/
    │   └── .gitkeep                            # Full HTTP + WebSocket client test scenarios
    ├── integration/
    │   └── .gitkeep                            # Integration tests with RAG and AvatarVoice services
    └── unit/
        └── .gitkeep                            # Route validation and state transition unit tests
```

---

## 5. Detailed File Logic (Planned & Authoritative Architecture)

### Target Files in `src/`
- **`src/main.py`**:
  - Initializes FastAPI application with CORS middleware (allowing local frontend dev server `http://localhost:3000`).
  - Registers API routers under `/api/v1` and establishes startup/shutdown hooks for database connections.
- **`src/api/routers/sessions.py`**:
  - `POST /sessions`: Creates a new anonymous session record and returns a unique `session_id`.
  - `POST /sessions/{id}/topic`: Receives `TopicRequest` (Contract §2) with topic string and `LearnerConstraints`, storing constraints in the session record.
  - `POST /sessions/{id}/plan`: Calls `ai_agent_orchestration.PlannerAgent` and returns the generated `LessonPlan` (Contract §5).
- **`src/api/routers/upload.py`**:
  - `POST /sessions/{id}/upload`: Receives multipart file stream matching `UploadRequest` (Contract §1). Passes binary stream to `RAGService.ingest_document()`, persists metadata, and returns `document_id` and parse summary.
- **`src/api/routers/learners.py`**:
  - `GET /learners/{id}/profile`: Fetches and returns `LearnerProfile` (Contract §13), including strong/weak concepts and history.
  - `GET /learners/{id}/report/{lesson_id}`: Retrieves stored `AssessmentReport` (Contract §12).
- **`src/api/routers/ws_live.py`**:
  - Manages active client WebSocket connections at `/sessions/{id}/live`.
  - Listens for client actions: `StudentResponse` (Contract §9), `language_switch`, `pause`, `resume`.
  - Pushes server events: `TeachingSegment`, `RenderedVideoSegment` (Contract §7), `InteractionEvent` (Contract §8), and `AdaptationDecision` (Contract §11).
- **`src/core/state_machine.py`**:
  - Authoritative session driver. When a stage finishes (e.g. video rendering completes), automatically triggers the next state transition and notifies the WebSocket manager.
- **`src/db/models.py`**:
  - `SessionModel`: UUID primary key, active state, timestamps, linked `learner_id`.
  - `LearnerProfileModel`: JSON columns storing concept mastery maps and learning history.
  - `AssessmentReportModel`: Foreign key to session and learner, percentage score, JSON arrays for recommendations.

---

## 6. How the Module Works (Execution Flow & Runtime Lifecycle)

```
[Student Frontend]                                    [Backend Gateway]                            [Internal Services]
         |                                                    |                                             |
         | --- 1. POST /sessions ---------------------------> |                                             |
         | <--- Returns session_id -------------------------- |                                             |
         |                                                    |                                             |
         | --- 2. POST /sessions/{id}/upload (File) --------> | --- Passes file bytes --------------------> [RAG Module]
         |                                                    | <--- Returns ParsedDocument (Contract §4) - |
         | <--- Returns document_id + status ---------------- |                                             |
         |                                                    |                                             |
         | --- 3. Connect WS /sessions/{id}/live -----------> | [SessionManager accepts connection]         |
         |                                                    |                                             |
         | --- 4. POST /sessions/{id}/plan -----------------> | --- Triggers PlannerAgent ----------------> [AI Orchestration]
         | <--- Returns LessonPlan (Contract §5) ------------ | <--- Returns LessonPlan ------------------- |
         |                                                    |                                             |
         |                                                    | === BEGIN INTERACTIVE TEACHING LOOP ===     |
         |                                                    |                                             |
         |                                                    | --- Requests TeachingSegment -------------> [AI Orchestration]
         |                                                    | <--- Returns TeachingSegment (Contract §6) - |
         |                                                    |                                             |
         |                                                    | --- Dispatches to Video Synthesizer ------> [Avatar / Voice]
         |                                                    | <--- Returns RenderedVideoSegment (§7) ---- |
         |                                                    |                                             |
         | <=== PUSH WS: RenderedVideoSegment =============== |                                             |
         |      (Frontend plays 1080p lesson video)           |                                             |
         |                                                    |                                             |
         | <=== PUSH WS: InteractionEvent (Contract §8) ===== | --- Generates Question -------------------> [AI Orchestration]
         |      (Frontend displays question card)             |                                             |
         |                                                    |                                             |
         | ===> SEND WS: StudentResponse (Contract §9) ====== | --- Evaluates Answer ---------------------> [ML Core]
         |                                                    | <--- Returns EvaluationResult (§10) ------- |
         |                                                    |                                             |
         |                                                    | --- Triggers Adaptation Decision ---------> [AI Orchestration]
         |                                                    | <--- Returns AdaptationDecision (§11) ----- |
         |                                                    |                                             |
         | <=== PUSH WS: AdaptationDecision (ALLOW/MODIFY) == | (Pushed to UI live audit log)               |
         |                                                    |                                             |
         |                                                    | === LESSON FINISHED ===                     |
         | <=== PUSH WS: AssessmentReport (Contract §12) ==== | --- Persists to LearnerProfile (§13) -----> [Database Store]
```

---

## 7. Cross-Module Connections & Contract Integration

| Direction | Connected Module | Contract Reference | Protocol / Data Shape |
|---|---|---|---|
| **Inbound** | `frontend` | **Contracts §1, §2, §3, §9** | Client sends REST requests and pushes WebSocket response frames. |
| **Outbound** | `frontend` | **Contracts §5, §7, §8, §11, §12** | Backend responds via REST and streams live WebSocket events. |
| **Outbound** | `rag` | **Contract §1, §4** | Streams raw uploaded file bytes to `RAGService.ingest_document()`. |
| **Outbound** | `ai_agent_orchestration` | **Contracts §5, §6, §8, §11, §12** | Invokes Planner, Explainer, Questioner, Adaptation Controller, and Assessment agents. |
| **Outbound** | `avatar_voice` | **Contracts §6, §7** | Calls `AvatarVoiceService.render_segment()` to synthesize video. |
| **Outbound** | `ml_core` | **Contracts §9, §10** | Relays student answers to `MLCoreService.evaluate_answer()`. |
| **Internal** | Database | **Contracts §12, §13** | Stores and queries `LearnerProfile` and `AssessmentReport` records. |

---

## 8. Full System Overview (Module-Wise Context)

In the complete 8-stage Shikshak AI teaching loop:
`Understand -> Plan -> Explain -> Demonstrate -> Question -> Evaluate -> Adapt -> Continue`

The **`backend`** module acts as the physical highway and state ledger:
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
