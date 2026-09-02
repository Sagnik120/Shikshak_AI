# detail_plan.md — backend

## Goal
Own the API surface, session orchestration glue, auth, and persistent storage (`LearnerProfile`,
sessions, uploaded-doc references, rendered-video references). NOT where lesson/teaching logic
lives — that's `ai_agent_orchestration`; backend calls into it.

## Endpoints (REST)
- `POST /sessions` — create session, return `session_id`.
- `POST /sessions/{id}/upload` — accepts `UploadRequest`, streams to `rag` for parsing,
  returns `document_id` + parse status.
- `POST /sessions/{id}/topic` — accepts `TopicRequest`.
- `POST /sessions/{id}/plan` — triggers `ai_agent_orchestration` Planner, returns `LessonPlan`.
- `GET /learners/{id}/profile` — returns `LearnerProfile`.
- `GET /learners/{id}/report/{lesson_id}` — returns stored `AssessmentReport`.

## WebSocket
- `WS /sessions/{id}/live` — bidirectional channel carrying the event types defined in
  `instructions/Contract.md` (§6–11). Backend is a thin relay + state-machine driver that calls
  `ai_agent_orchestration` for each stage transition and `avatar_voice`/`ml_core`/`rag` as needed,
  then forwards results to the client.

## Session State Machine (server-authoritative)
`CREATED → INGESTING → PLANNED → EXPLAINING → AWAITING_ANSWER → EVALUATING → ADAPTING →
(loop to EXPLAINING or) → ASSESSING → COMPLETE`
Persist current state + `lesson_id` + `node_id` so a disconnect/reconnect can resume mid-lesson.

## Storage
- Postgres tables: `sessions`, `learner_profiles`, `assessment_reports`, `uploaded_documents`
  (metadata only — file bytes in object storage), `rendered_segments` (metadata; video bytes in
  object storage / local disk for hackathon demo).
- Object storage: local filesystem path for hackathon MVP (swap to S3-compatible later via an
  adapter — do not hardcode local paths into business logic).

## Auth
Lightweight: session token issued on `POST /sessions`, no full user-account system required for
MVP demo; `learner_id` can be a persisted anonymous/device ID unless real accounts are a
stretch goal.

## Cross-module calls
Backend never talks to an LLM/vector DB/TTS directly — it calls `ai_agent_orchestration`,
`rag`, `ml_core`, `avatar_voice` through their contract-defined interfaces so those modules stay
independently swappable/testable.
