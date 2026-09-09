# contract.md — backend (Module-Local Contract Specification)

This document formalizes how the `backend` module consumes, implements, and produces schemas defined in the root `instructions/Contract.md`, as well as internal data transfer models specific to `backend`.

---

## 1. Cross-Module Contract Interfaces

### 1.1 Inbound Interfaces (Client & Frontend &rarr; Backend)
- **Contract §1: `UploadRequest`**:
  ```python
  class UploadRequest(BaseModel):
      file_bytes: bytes
      filename: str
      mime_type: str
      constraints: LearnerConstraints
  ```
- **Contract §2: `TopicRequest`**:
  ```python
  class TopicRequest(BaseModel):
      topic: str
      constraints: LearnerConstraints
  ```
- **Contract §3: `LearnerConstraints`**:
  ```python
  class LearnerConstraints(BaseModel):
      level: Literal["beginner", "intermediate", "advanced"] = "beginner"
      language: str = "en"
      time_budget_min: int = Field(default=15, ge=5, le=60)
  ```
- **Contract §9: `StudentResponse`**:
  ```python
  class StudentResponse(BaseModel):
      node_id: str
      raw_answer: str
      response_type: str
      response_time_sec: float
  ```

### 1.2 Outbound Interfaces (Backend &rarr; Client / AI Modules)
- **Contract §5: `LessonPlan`**: Emitted upon `/sessions/{id}/plan` and WebSocket `curriculum_loaded`.
- **Contract §6: `TeachingSegment`**: Dispatched during EXPLAIN state.
- **Contract §7: `RenderedVideoSegment`**: Relayed from AvatarVoiceService.
- **Contract §8: `InteractionEvent`**: Dispatched during QUESTION state.
- **Contract §10: `EvaluationResult`**: Relayed from MLCoreService.
- **Contract §11: `AdaptationDecision`**: Emitted during ADAPT state (`ALLOW`, `MODIFY`, `REGENERATE`, `HUMAN`).
- **Contract §12: `AssessmentReport`**: Emitted during ASSESS state.
- **Contract §13: `LearnerProfile`**: Retrieved via `GET /learners/{id}/profile`.

---

## 2. WebSocket Relay Frame Contract (`src/schemas/ws.py`)

All real-time messages transmitted over `/sessions/{id}/live` adhere to:
```python
class WSMessage(BaseModel):
    event_type: str
    payload: Dict[str, Any]
    error: Optional[str] = None
```

### Supported Event Types:
| `event_type` | Emitted By | Description |
|---|---|---|
| `curriculum_loaded` | Server | Transmits full `LessonPlan` to initialize student curriculum view |
| `ai_state` | Server | Broadcasts active stage (`TEACH`, `DEMONSTRATE`, `QUESTION`, `EVALUATE`, `ADAPT`) |
| `explanation_chunk`| Server | Real-time text chunk for captions and blackboard stage |
| `question_prompt` | Server | Emits interactive question (`mcq`, `short_answer`) |
| `evaluation_result`| Server | Transmits grading score, partial credit, and misconception diagnosis |
| `adaptation_decision`| Server | Announces pedagogical remedy path |
| `lesson_plan_update`| Server | Broadcasts modified or regenerated lesson nodes |
| `error` | Server | Transmits error details or unauthorized notices |
| `ack` | Server | Acknowledges receipt of client action frames |

---

## 3. Web Testbed REST API Contract (Port 8005)

| Endpoint | Method | Input Model | Output Model | Description |
|---|---|---|---|---|
| `/api/test/status` | `GET` | None | `Dict[str, Any]` | Health, uptime, active sessions, and gateway status |
| `/api/test/sessions` | `POST` | None | `TestSessionResponse` | Creates isolated test session and auth token |
| `/api/test/topic` | `POST` | `TestTopicRequest` | `Dict[str, Any]` | Sets session topic and learner constraints |
| `/api/test/upload` | `POST` | Multipart Form | `Dict[str, Any]` | Uploads test document and parses via RAG |
| `/api/test/plan` | `POST` | `TestPlanRequest` | `Dict[str, Any]` | Triggers SessionDriver curriculum plan generation |
| `/api/test/learners/{id}/profile`| `GET` | Path param | `Dict[str, Any]` | Retrieves learner profile from repository |
| `/api/test/ws/{session_id}` | `WS` | `WSMessage` | `WSMessage` | Real-time bidirectional WebSocket relay |
| `/api/test/logs` | `GET` | Query `category` | `List[Dict[str, Any]]` | Lists categorized test logs |
| `/api/test/logs/{cat}/{fn}` | `GET` | Path params | Log content (JSON/text) | Inspects structured trace file |
