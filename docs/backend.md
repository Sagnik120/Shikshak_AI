# Backend API - Implementation Documentation

## 1. Module Purpose
The `backend` module serves as the primary integration tier connecting the stateless frontend to the stateful, intelligent orchestrators and ML components. It does not reinvent teaching logic; instead, it acts as a thin controller that persists session states, manages authentication, and drives the `AIOperationService` state machine via REST and WebSocket interfaces.

## 2. File Structure
```
modules/backend/src/
├── api/
│   ├── rest.py                 # FastAPI router for session init, topics, planning
│   └── ws.py                   # WebSocket endpoint for the live teaching loop
├── integrations/
│   └── container.py            # Dependency Injection for Orchestrator/Avatar/RAG
├── persistence/
│   ├── base.py                 # Abstract SessionRepository
│   └── in_memory.py            # MVP in-memory session persistence
├── schemas/
│   ├── contract.py             # Shared cross-module models (from Contract.md)
│   └── ws.py                   # WebSocket event payload schemas
├── state/
│   └── driver.py               # Adapts incoming WS/REST events to AIOperationService steps
├── auth.py                     # MVP static token generation/validation
├── config.py                   # Backend configuration
└── main.py                     # FastAPI application entrypoint
```

## 3. Actual Public Entrypoints

### REST Routes (`api/rest.py`)
- `POST /api/v1/sessions`: Initializes a new teaching session and returns a secure token.
- `POST /api/v1/sessions/{session_id}/topic`: Accepts a `TopicRequest` containing the subject and `LearnerConstraints`, storing it in the repository.
- `POST /api/v1/sessions/{session_id}/plan`: Drives the `TeacherState.UNDERSTAND` and `TeacherState.PLAN` steps of the AI Orchestrator to generate and return a `LessonPlan`.

### WebSocket Route (`api/ws.py`)
- `WS /api/v1/sessions/{session_id}/live`: The main interactive conduit.
  - Automatically executes the orchestration loop (`EXPLAIN` → `DEMONSTRATE` → `QUESTION` → `EVALUATE` → `ADAPT`).
  - Fetches the rendered `RenderedVideoSegment` from the Avatar service.
  - Pauses to wait for `student_response` from the frontend.
  - Pushes `interaction_event`, `evaluation_result`, and `adaptation_decision` payloads down the wire.
  - Concludes with an `AssessmentReport` at `TeacherState.DONE`.

## 4. Cross-Module Integrations
- **AI Agent Orchestration**: Driven entirely via `process_next_step()` inside `state/driver.py`. Backend respects the `TeacherState` enum strictly.
- **ML Core**: Backend does **not** call ML Core directly. `AIOperationService` internally owns the ML Core interactions for extraction and evaluation.
- **Avatar & Voice**: Backend polls `AvatarVoiceService.get_status(job_id)` during the `DEMONSTRATE` state to retrieve video URLs and subtitles for the frontend.
- **RAG**: Deferred to P1. The `POST /sessions/{id}/upload` route for ingesting PDFs/DOCXs into RAG is not yet implemented.

## 5. Persistence (`persistence/in_memory.py`)
Currently relies on a lightweight `InMemorySessionRepository` for rapid prototyping. It stores session tokens, topic data, and constraints in a basic dictionary.

## 6. Testing Reality
- **Unit Tests**: Coverage for token validation (`test_auth.py`), repository CRUD (`test_persistence.py`), and schema validation (`test_schemas.py`).
- **Integration Tests**: 
  - `test_rest_api.py`: Validates the correct state execution and error responses for the REST endpoints.
  - `test_ws_api.py`: Connects to the WebSocket loop and asserts the precise sequence of events sent to the client.
- **E2E Mocked Tests**: `test_teaching_session.py` provides the canonical mock-boundary proof that a full session works end-to-end when the orchestrator is stubbed.
- **Current Result**: 13/13 passing tests natively.

## 7. Deferred Functionality (P1/P2)
- **RAG Upload Route**: `POST /sessions/{id}/upload` is missing.
- **Learner Profile**: `GET /learners/{id}/profile` history endpoints are missing.
- **Persistent Storage**: Postgres DB replacement for the in-memory dictionary.
- **WebSocket Reconnection**: Session resume logic inside `ws.py` if the client disconnects mid-lesson.
- **Advanced Human Fallback**: Orchestration handles `TeacherState.HUMAN` gracefully, but Backend does not yet have an admin dashboard or escalation queue logic.
