# detail_plan.md — backend

## Goal
Own the API surface, session orchestration glue, auth, and persistent storage (`LearnerProfile`, sessions, uploaded document references, rendered video references).
Acts as the central coordination engine and communication bridge connecting the client frontend to the AI microservices (`ai_agent_orchestration`, `rag`, `ml_core`, `avatar_voice`).

---

## 1. Production Architecture & Implemented Components

### 1.1 REST API Surface (`src/api/rest.py`)
- **`POST /sessions`**: Creates high-entropy session IDs and generates bearer session auth tokens.
- **`POST /sessions/{id}/topic`**: Accepts `TopicRequest` (topic title, learner constraints such as level, language, and time budget) and saves to session repository.
- **`POST /sessions/{id}/upload`**: Multipart file upload endpoint. Saves bytes into `StorageAdapter`, updates `DocumentRepository`, streams bytes to `RAGService.ingest_document`, and attaches detected chapters and key terms to the session.
- **`POST /sessions/{id}/plan`**: Triggers `SessionDriver.step(TeacherState.UNDERSTAND)` followed by `SessionDriver.step(TeacherState.PLAN)`, returning Contract §5 `LessonPlan`.
- **`GET /learners/{id}/profile`**: Returns Contract §13 `LearnerProfile` (history, strong concepts, weak concepts, current learning path, preferred language, and level).
- **`GET /learners/{id}/report/{lesson_id}`**: Retrieves stored Contract §12 `AssessmentReport`.

### 1.2 WebSocket Live Relay (`src/api/ws.py`)
- **`WS /sessions/{id}/live`**: High-speed, bidirectional full-duplex communication channel:
  - Validates session token via `verify_ws_token`.
  - Resumes from persisted state checkpoints if reconnecting mid-lesson.
  - Streams `curriculum_loaded` event with full `LessonPlan`.
  - Loops over `SessionDriver` state machine emitting `ai_state`, `explanation_chunk`, `question_prompt`, `evaluation_result`, and `adaptation_decision`.
  - Dispatches visual specifications and multimedia cues to `AvatarVoiceService`.

### 1.3 Persistence Layer (`src/persistence/in_memory.py`)
- **`SessionRepository`**: Tracks session tokens, active topics, learner constraints, document contexts, and state checkpoints.
- **`DocumentRepository`**: Tracks uploaded document metadata, filenames, MIME types, file sizes, and parsing status (`ready`/`failed`).
- **`LearnerRepository`**: Stores learner mastery profiles, strengths, weaknesses, and learning paths.
- **`ReportRepository`**: Stores final quiz assessment reports.
- **`StorageAdapter`**: Filesystem-backed binary object storage adapter.

### 1.4 State Machine Driver (`src/state/driver.py`)
- Coordinates transitions across `TeacherState`:
  `CREATED -> INGESTING -> PLANNED -> EXPLAINING -> AWAITING_ANSWER -> EVALUATING -> ADAPTING -> ASSESSING -> COMPLETE`.
- Interfaces directly with `TeacherOrchestrator` in `ai_agent_orchestration`.

### 1.5 Microservice Container Gateway (`src/integrations/container.py`)
- Decouples the backend from direct LLM, TTS, or vector DB calls.
- Encapsulates instances of:
  - `rag_service` (`RAGService`)
  - `avatar_voice_service` (`AvatarVoiceService`)
  - `teacher_orchestrator` (`TeacherOrchestrator`)
  - `ml_core_service` (`MLCoreService`)

---

## 2. Interactive Web Testbed & Isolated Diagnostic Environment

### 2.1 Dedicated Testbed Server (`tests/web_test/server.py`)
- **Port Allocation**: Runs on **Port 8005** (leaving Port 8000 production backend completely untouched).
- **FastAPI Endpoints**:
  - `GET /`: Serves the light professional diagnostic studio.
  - `GET /api/test/status`: Health check, active session count, persistence repository metrics, and gateway status.
  - `POST /api/test/sessions`: Tests session creation and token issuance.
  - `POST /api/test/topic`: Tests topic and learner constraints submission.
  - `POST /api/test/upload`: Tests multipart document upload and RAG structure detection.
  - `POST /api/test/plan`: Tests curriculum plan generation via SessionDriver.
  - `GET /api/test/learners/{id}/profile`: Tests learner profile queries.
  - `WS /api/test/ws/{session_id}`: Live WebSocket simulator testing bidirectional frame exchanges.
  - `GET /api/test/logs`: Lists categorized test logs.
  - `GET /api/test/logs/{category}/{filename}`: Retrieves raw JSON or formatted text execution log.

### 2.2 Hierarchical Logging & Hallucination Traceability (`tests/web_test/logger.py`)
- **Category-Partitioned Log Directory**:
  ```
  modules/backend/tests/web_test/logs/
  ├── sessions/      # Dual .json and .log files for session creation and auth
  ├── websocket/     # Dual .json and .log files for live WebSocket frame relays
  ├── orchestration/ # Dual .json and .log files for state transitions and lesson plans
  ├── rag_relay/     # Dual .json and .log files for document upload and RAG ingestion
  ├── avatar_relay/  # Dual .json and .log files for multimedia segment requests
  ├── telemetry/     # Dual .json and .log files for health checks and latency probes
  └── errors/        # Unhandled exceptions, validation errors, and hallucination alerts
  ```
- **Traceability Metadata Per Log Entry**:
  - `timestamp_iso`: Exact execution timestamp in UTC/ISO-8601.
  - `calling_file`: Exact Python source file (e.g., `modules/backend/src/api/rest.py`, `ws.py`, `driver.py`).
  - `calling_function`: Exact function invoked (e.g., `create_session`, `upload_document`, `websocket_endpoint`).
  - `execution_latency_ms`: Real-time execution duration in milliseconds.
  - `input_payload`: Raw input parameters provided by the user.
  - `output_payload`: Complete result emitted by the module.
  - `is_hallucination_suspect`: Flag triggered if outputs contain malformed frames, out-of-spec schemas, or unexpected states.

### 2.3 Pure Light Professional UI (`tests/web_test/static/`)
- **Visual Design Rules**:
  - **Strict Light Theme**: Clean white background (`#ffffff`), soft slate page surface (`#f8fafc`), crisp borders (`#e2e8f0`).
  - **No Dark Mode**: Absolutely zero dark background surfaces or low-contrast dark themes.
  - **Typography**: Clean modern sans-serif typography (`Inter`, `system-ui`).
  - **Interactive Presets**: One-click test cases for Physics, Mathematics, Biology, and Computer Science.
  - **Live WebSocket Terminal**: Real-time message feed showing inbound client actions and outbound server events.

---

## 3. Verification & Testing Standards
1. **Unit Testing**: Route validation and persistence layer testing in `modules/backend/tests/unit/`.
2. **Integration Testing**: Boundary validation and WebSocket state machine testing in `modules/backend/tests/integration/`.
3. **Web Test Server Testing**: Dedicated automated pytest suite in `modules/backend/tests/unit/test_backend_web_test_server.py`.
4. **Git Hygiene**: Runtime `*.log` and `*.json` test logs excluded via `.gitignore`; subdirectories preserved via `.gitkeep`.
